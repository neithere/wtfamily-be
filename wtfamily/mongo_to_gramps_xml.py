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

See also:

* https://github.com/gramps-project/gramps/blob/master/gramps/plugins/importer/importxml.py
* https://github.com/gramps-project/gramps/blob/master/gramps/plugins/export/exportxml.py

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
# NOTE: not bundled with Python but separate library; it can pretty-print.
from lxml import etree
import sys

from models import (Entity, Person, Family, Event, Citation, Source, Place,
                    Repository, MediaObject, Note, Bookmark, NameMap,
                    NameFormat)

import etl.serializers as s


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
    yield etree.tostring(tree_el, encoding='unicode', pretty_print=True)


def build_xml(db):
    tree_el = etree.Element('database', {
        'xmlns': '{}xml/{}/'.format(GRAMPS_URL_HOMEPAGE, GRAMPS_XML_VERSION)
    })

    header = make_header_element()
    tree_el.append(header)

    # monkey-patch to avoid the Flask app context/globals nonsense
    Entity._get_database = lambda: db

    models = (Person, Family, Event, Citation, Source, Place, Repository,
              MediaObject, Note, Bookmark, NameMap, NameFormat)
    model_to_tag = {
        Person: ('people', 'person', s.PersonSerializer),
        Family: ('families', 'family', s.FamilySerializer),
        Event: ('events', 'event', s.EventSerializer),
        Source: ('sources', 'source', s.SourceSerializer),
        Place: ('places', 'placeobj', s.PlaceSerializer),
        MediaObject: ('objects', 'object', s.MediaObjectSerializer),
        Repository: ('repositories', 'repository', s.RepositorySerializer),
        Note: ('notes', 'note', s.NoteSerializer),
        # TODO: Tag: ('tags', 'tag', s.TagSerializer),
        Citation: ('citations', 'citation', s.CitationSerializer),
        Bookmark: ('bookmarks', 'bookmark', s.BookmarkSerializer),
        NameMap: ('namemaps', 'map', s.NameMapSerializer),
        NameFormat: ('name-formats', 'format', s.NameFormatSerializer),
    }

    # Gather the mappings of IDs to internal Gramps IDs ("handles").
    # This requires a full iteration over all potentially referenced entities
    # before we try exporting them.
    id_to_handle = {}
    for model in models:
        collection = model._get_collection()
        for item in collection.find({}, projection=['id', 'handle']):
            item_handle = item.get('handle')
            item_id = item.get('id')
            if item_handle and item_id:
                id_to_handle[item_id] = item_handle

    # Now that we have the full mapping, proceed to export record by record.
    for model in models:

        # XXX debug stuff, remove once all serializers are ready.
        if model not in model_to_tag:
            sys.stderr.write('ERROR: Model {.__name__} has no serializer '
                             'defined.\n'.format(model))
            continue

        group_tag, item_tag, ItemSerializer = model_to_tag[model]

        group_el = etree.SubElement(tree_el, group_tag)

        items = model.find()

        for item in items:
            item_serializer = ItemSerializer()
            item_el = item_serializer.to_xml(item_tag, item._data,
                                             id_to_handle)
            group_el.append(item_el)

    return tree_el


def make_header_element():
    today = str(datetime.date.today())

    header_el = etree.Element('header')

    etree.SubElement(header_el, 'created', date=today, version=GRAMPS_XML_VERSION)

    researcher_el = make_researcher_element()
    header_el.append(researcher_el)

    # this one is WTFamily-specific, not in GrampsXML DTD
    etree.SubElement(header_el, 'generator').attrib['name'] = WTFAMILY_APP_NAME

    return header_el


def make_researcher_element():
    # TODO: add a collection to store researcher metadata.
    # Currently we ignore this stuff when importing from Gramps.

    researcher_el = etree.Element('researcher')

    fields = ('name', 'addr', 'locality', 'city', 'state', 'country', 'postal',
              'phone', 'email')
    for field in fields:
        tag = 'res{}'.format(field)

        el = etree.Element(tag)
        el.append(etree.Comment(' TODO: researcher {} '.format(field)))
        researcher_el.append(el)

    return researcher_el
