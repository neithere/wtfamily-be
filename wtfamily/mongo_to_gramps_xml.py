#!/usr/bin/env python
#
#    WTFamily is a genealogical software.
#
#    Copyright © 2014—2018  Andrey Mikhaylenko
#
#    This file is part of WTFamily.
#
#    WTFamily is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    WTFamily is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with WTFamily.  If not, see <http://gnu.org/licenses/>.
"""
Experimental converter of WTFamily MongoDB data to compressed Gramps XML.

Caveats
=======

ID, handle, ObjectID
--------------------

- ObjectID is MongoDB-specific, no place for it in GrampsXML.
- Handle is Gramps-specific, incompatible with ObjectID.
- ID is universal.  Probably intended for portability?

We can probably ditch both handles and ObjectIDs and rely on IDs.
Handles can be maintained solely for (almost) idempotent import/export.

BTW, Gramps' GEDCOM export uses IDs and nothing else.
"""
import datetime
import xml.etree.ElementTree as et
import sys

from models import (Entity, Person, Family, Event, Citation, Source, Place,
                    Repository, MediaObject, Note)

WTFAMILY_APP_NAME = 'WTFamily'
GRAMPS_XML_VERSION_TUPLE = (1, 7, 1) # version for Gramps 4.2
GRAMPS_XML_VERSION = '.'.join(str(i) for i in GRAMPS_XML_VERSION_TUPLE)
GRAMPS_URL_HOMEPAGE = "http://gramps-project.org/"


def export_to_xml(db):
    declaration = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE database PUBLIC "-//Gramps//DTD Gramps XML %s//EN"\n'
        '"%sxml/%s/grampsxml.dtd">\n'
        % (GRAMPS_XML_VERSION, GRAMPS_URL_HOMEPAGE, GRAMPS_XML_VERSION))

    tree_el = build_xml(db)

    yield declaration
    yield et.tostring(tree_el, encoding='unicode')

def build_xml(db):
    tree_el = et.Element('database', {
        'xmlns': '{}xml/{}/'.format(GRAMPS_URL_HOMEPAGE, GRAMPS_XML_VERSION)
    })

    header = make_header_element()
    tree_el.append(header)

    # monkey-patch to avoid the Flask app context/globals nonsense
    Entity._get_database = lambda: db

    # TODO: also Tag?
    models = (Person, Family, Event, Citation, Source, Place, Repository,
              MediaObject, Note)
    model_to_tag = {
        Event: ('events', 'event', EventObjectSerializer),
        Note: ('notes', 'note', NoteObjectSerializer),
    }

    # Gather the mappings of IDs to internal Gramps IDs ("handles").
    # This requires a full iteration over all potentially referenced entities
    # before we try exporting them.
    id_to_handle = {}
    for model in models:
        for x in model._get_collection().find({}, projection=['id', 'handle']):
            id_to_handle[x['id']] = x['handle']

    # Now that we have the full mapping, proceed to export record by record.
    for model in models:

        # XXX debug stuff, remove once all serializers are ready.
        if model not in model_to_tag:
            sys.stderr.write('ERROR: Model {.__name__} has no serializer '
                             'defined.\n'.format(model))
            continue

        group_tag, item_tag, ItemSerializer = model_to_tag[model]

        group_el = et.SubElement(tree_el, group_tag)

        items = model.find()
        items = list(items)[:100]  # XXX DEBUG
        for item in items:
            item_serializer = ItemSerializer(item_tag, item, id_to_handle)
            item_el = item_serializer.make_xml()
            group_el.append(item_el)

    return tree_el

class GenericModelObjectSerializer:
    TEXT_TAGS = []
    REF_TAGS = []

    STRING_ATTRS = 'id', 'handle'
    BOOL_ATTRS = 'priv',
    TIMESTAMP_ATTRS = 'change',

    def __init__(self, tag, obj, id_to_handle):
        self.tag = tag
        self.obj = obj
        self.id_to_handle = id_to_handle

        import sys
        sys.stderr.write(str(obj._data) + "\n")

    def make_xml(self):
        el = et.Element(self.tag)
        el.attrib = self.make_attrs()
        for child_el in self.make_child_elements():
            if child_el is not None:
                el.append(child_el)
        return el

    def make_attrs(self):
        attrs = {}

        for name in self.STRING_ATTRS:
            self._set_string(attrs, name)

        for name in self.BOOL_ATTRS:
            self._set_bool(attrs, name)

        for name in self.TIMESTAMP_ATTRS:
            self._set_timestamp(attrs, name)

        return attrs

    def make_child_elements(self):
        for tag in self.TEXT_TAGS:
            yield self._make_child_text_elem(tag)

        for tag in self.REF_TAGS:
            for child_el in self._make_child_ref_elems(tag):
                yield child_el

    def _make_child_text_elem(self, key):
        """
        Returns a ``<foo>some text</foo>`` element.
        """
        # NOTE: key == tag, but somewhere it may differ(?)
        tag = key
        value = self.obj._data.get(key)
        if value:
            el = et.Element(tag)
            el.text = value
            return el

    def _make_child_ref_elems(self, key):
        """
        Generates ``<foo hlink="foo" />`` elements.
        """
        # NOTE: key == tag, but somewhere it may differ(?)
        tag = key
        items = self.obj._data.get(key) or []
        for item in items:
            pk = item['id']

            # `hlink` contains "handle", the internal Gramps ID.
            # WTFamily preserves it but relies on the public ID.
            # We use a global ID-to-handle mapping to convert them back.
            #
            # FIXME this won't work for newly added items.  Options:
            # - generate a "handle" now
            # - generate it always internally
            # - use ObjectId
            # - use public ID
            handle = self.id_to_handle[pk]

            yield et.Element(tag, {
                'hlink': handle,
            })

    def _set_string(self, target, key, required=False):
        value = self.obj._data.get(key)
        if required or value:
            target[key] = str(value or '')

    def _set_timestamp(self, target, key, required=False):
        value = self.obj._data.get(key)
        if required or value:
            target[key] = str(int(value.timestamp())) if value else ''

    def _set_bool(self, target, key, required=False):
        value = self.obj._data.get(key)
        if required or value is not None:
            # booleans are represented as numbers in XML attrs
            target[key] = str(int(value))


class EventObjectSerializer(GenericModelObjectSerializer):
    TEXT_TAGS = 'type', 'description'
    REF_TAGS = 'place', 'citationref', 'noteref', 'objref', 'tagref'

    # TODO
    # (daterange | datespan | dateval | datestr)?,
    # \attribute*,


class NoteObjectSerializer(GenericModelObjectSerializer):
    """
    Limitations:

    - styles are ignored
    """
    TEXT_TAGS = 'text',

    BOOL_ATTRS = 'format',
    STRING_ATTRS = GenericModelObjectSerializer.STRING_ATTRS + ('type',)


def make_header_element():
    today = str(datetime.date.today())

    header_el = et.Element('header')

    et.SubElement(header_el, 'created', date=today, version=GRAMPS_XML_VERSION)

    researcher_el = make_researcher_element()
    header_el.append(researcher_el)

    # this one is WTFamily-specific, not in GrampsXML DTD
    et.SubElement(header_el, 'generator').attrib['name'] = WTFAMILY_APP_NAME

    return header_el

def make_researcher_element():
    # TODO: add a collection to store researcher metadata.
    # Currently we ignore this stuff when importing from Gramps.

    researcher_el = et.Element('researcher')

    fields = ('name', 'addr', 'locality', 'city', 'state', 'country', 'postal',
              'phone', 'email')
    for field in fields:
        tag = 'res{}'.format(field)

        el = et.Element(tag)
        el.append(et.Comment(' TODO: researcher {} '.format(field)))
        researcher_el.append(el)

    return researcher_el
