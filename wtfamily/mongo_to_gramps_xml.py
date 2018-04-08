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

    models = (Person, Family, Event, Citation, Source, Place, Repository,
              MediaObject, Note)
    model_to_tag = {
        Person: ('people', 'person', PersonSerializer),
        Family: ('families', 'family', FamilySerializer),
        Event: ('events', 'event', EventSerializer),
        Source: ('sources', 'source', SourceSerializer),
        Place: ('places', 'place', PlaceSerializer),
        MediaObject: ('objects', 'object', MediaObjectSerializer),
        Repository: ('repositories', 'repository', RepositorySerializer),
        Note: ('notes', 'note', NoteSerializer),
        # TODO: Tag: ('tags', 'tag', TagSerializer),
        Citation: ('citations', 'citation', CitationSerializer),
        # TODO: Bookmark: ('bookmarks', 'bookmark', BookmarkSerializer),
        # TODO: NameMap: ('namemaps', 'map', NameMapSerializer),
        # TODO: Bookmark: ('name-formats', 'format', NameFormatSerializer),
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


class PersonSerializer(GenericModelObjectSerializer):
    """
    <!ELEMENT people (person)*>
    <!ATTLIST people
            default CDATA #IMPLIED
            home    IDREF #IMPLIED
    >

    <!ELEMENT person (gender, name*, eventref*, lds_ord*,
                      objref*, address*, attribute*, url*, childof*,
                      parentin*, personref*, noteref*, citationref*, tagref*)>
    <!ATTLIST person
            id        CDATA #IMPLIED
            handle    ID    #REQUIRED
            priv      (0|1) #IMPLIED
            change    CDATA #REQUIRED
    >

    <!--
    GENDER has values of M, F, or U.
    -->
    <!ELEMENT gender  (#PCDATA)>

    <!ELEMENT name    (first?, call?, surname*, suffix?, title?, nick?, familynick?, group?,
                      (daterange|datespan|dateval|datestr)?, noteref*, citationref*)>
    <!-- (Unknown|Also Know As|Birth Name|Married Name|Other Name) -->
    <!ATTLIST name
            alt       (0|1) #IMPLIED
            type      CDATA #IMPLIED
            priv      (0|1) #IMPLIED
            sort      CDATA #IMPLIED
            display   CDATA #IMPLIED
    >

    <!ELEMENT first      (#PCDATA)>
    <!ELEMENT call       (#PCDATA)>
    <!ELEMENT suffix     (#PCDATA)>
    <!ELEMENT title      (#PCDATA)>
    <!ELEMENT nick       (#PCDATA)>
    <!ELEMENT familynick (#PCDATA)>
    <!ELEMENT group      (#PCDATA)>
    <!ELEMENT surname    (#PCDATA)>
    <!-- (Unknown|Inherited|Given|Taken|Patronymic|Matronymic|Feudal|
    Pseudonym|Patrilineal|Matrilineal|Occupation|Location) -->
    <!ATTLIST surname
            prefix      CDATA #IMPLIED
            prim        (1|0) #IMPLIED
            derivation  CDATA #IMPLIED
            connector   CDATA #IMPLIED
    >

    <!ELEMENT childof EMPTY>
    <!ATTLIST childof hlink IDREF  #REQUIRED
    >

    <!ELEMENT parentin EMPTY>
    <!ATTLIST parentin hlink IDREF #REQUIRED>

    <!ELEMENT personref (citationref*, noteref*)>
    <!ATTLIST personref
            hlink IDREF #REQUIRED
            priv  (0|1) #IMPLIED
            rel   CDATA #REQUIRED
    >

    <!ELEMENT address ((daterange|datespan|dateval|datestr)?, street?,
                                       locality?, city?, county?, state?, country?, postal?,
                                       phone?, noteref*,citationref*)>
    <!ATTLIST address priv (0|1) #IMPLIED>

    <!ELEMENT street   (#PCDATA)>
    <!ELEMENT locality (#PCDATA)>
    <!ELEMENT city     (#PCDATA)>
    <!ELEMENT county   (#PCDATA)>
    <!ELEMENT state    (#PCDATA)>
    <!ELEMENT country  (#PCDATA)>
    <!ELEMENT postal   (#PCDATA)>
    <!ELEMENT phone    (#PCDATA)>
    """
    # TODO


class FamilySerializer(GenericModelObjectSerializer):
    """
    <!ELEMENT families (family)*>

    <!ELEMENT family (rel?, father?, mother?, eventref*, lds_ord*, objref*,
                      childref*, attribute*, noteref*, citationref*, tagref*)>
    <!ATTLIST family
            id        CDATA #IMPLIED
            handle    ID    #REQUIRED
            priv      (0|1) #IMPLIED
            change    CDATA #REQUIRED
    >

    <!ELEMENT father EMPTY>
    <!ATTLIST father hlink IDREF #REQUIRED>

    <!ELEMENT mother EMPTY>
    <!ATTLIST mother hlink IDREF #REQUIRED>

    <!-- (None|Birth|Adopted|Stepchild|Sponsored|Foster|Other|Unknown) -->
    <!ELEMENT childref (citationref*,noteref*)>
    <!ATTLIST childref
            hlink IDREF #REQUIRED
            priv  (0|1) #IMPLIED
            mrel  CDATA #IMPLIED
            frel  CDATA #IMPLIED
    >

    <!ELEMENT type (#PCDATA)>

    <!ELEMENT rel EMPTY>
    <!ATTLIST rel type CDATA #REQUIRED>
    """
    # TODO


class EventSerializer(GenericModelObjectSerializer):
    """
    <!ELEMENT events (event)*>

    <!ELEMENT event (type?, (daterange|datespan|dateval|datestr)?, place?, cause?,
                     description?, attribute*, noteref*, citationref*, objref*,
                     tagref*)>
    <!ATTLIST event
            id        CDATA #IMPLIED
            handle    ID    #REQUIRED
            priv      (0|1) #IMPLIED
            change    CDATA #REQUIRED
    >
    """
    TEXT_TAGS = 'type', 'description'
    REF_TAGS = 'place', 'citationref', 'noteref', 'objref', 'tagref'

    # TODO
    # (daterange | datespan | dateval | datestr)?,
    # \attribute*,


class SourceSerializer(GenericModelObjectSerializer):
    """
    <!ELEMENT sources (source)*>
    <!ELEMENT source (stitle?, sauthor?, spubinfo?, sabbrev?,
                      noteref*, objref*, srcattribute*, reporef*, tagref*)>
    <!ATTLIST source
            id        CDATA #IMPLIED
            handle    ID    #REQUIRED
            priv      (0|1) #IMPLIED
            change    CDATA #REQUIRED
    >
    <!ELEMENT stitle   (#PCDATA)>
    <!ELEMENT sauthor  (#PCDATA)>
    <!ELEMENT spubinfo (#PCDATA)>
    <!ELEMENT sabbrev  (#PCDATA)>
    """
    # TODO


class PlaceSerializer(GenericModelObjectSerializer):
    """
    <!ELEMENT places (placeobj)*>

    <!ELEMENT placeobj (ptitle?, pname+, code?, coord?, placeref*, location*,
                        objref*, url*, noteref*, citationref*, tagref*)>
    <!ATTLIST placeobj
            id        CDATA #IMPLIED
            handle    ID    #REQUIRED
            priv      (0|1) #IMPLIED
            change    CDATA #REQUIRED
            type      CDATA #REQUIRED
    >

    <!ELEMENT pname (daterange|datespan|dateval|datestr)?>

    <!ATTLIST pname
            lang CDATA #IMPLIED
            value CDATA #REQUIRED
    >

    <!ELEMENT ptitle (#PCDATA)>
    <!ELEMENT code (#PCDATA)>

    <!ELEMENT coord EMPTY>
    <!ATTLIST coord
            long CDATA #REQUIRED
            lat  CDATA #REQUIRED
    >

    <!ELEMENT location EMPTY>
    <!ATTLIST location
            street   CDATA #IMPLIED
            locality CDATA #IMPLIED
            city     CDATA #IMPLIED
            parish   CDATA #IMPLIED
            county   CDATA #IMPLIED
            state    CDATA #IMPLIED
            country  CDATA #IMPLIED
            postal   CDATA #IMPLIED
            phone    CDATA #IMPLIED
    >
    """
    # TODO


class MediaObjectSerializer(GenericModelObjectSerializer):
    """
    <!ELEMENT object (file, attribute*, noteref*,
                     (daterange|datespan|dateval|datestr)?, citationref*, tagref*)>
    <!ATTLIST object
            id        CDATA #IMPLIED
            handle    ID    #REQUIRED
            priv      (0|1) #IMPLIED
            change    CDATA #REQUIRED
    >

    <!ELEMENT file EMPTY>
    <!ATTLIST file
            src         CDATA #REQUIRED
            mime        CDATA #REQUIRED
            checksum    CDATA #IMPLIED
            description CDATA #REQUIRED
    >
    """
    # TODO


class RepositorySerializer(GenericModelObjectSerializer):
    """
    <!ELEMENT repository (rname, type, address*, url*, noteref*, tagref*)>
    <!ATTLIST repository
            id        CDATA #IMPLIED
            handle    ID    #REQUIRED
            priv      (0|1) #IMPLIED
            change    CDATA #REQUIRED
    >

    <!ELEMENT rname   (#PCDATA)>
    """
    # TODO


class NoteSerializer(GenericModelObjectSerializer):
    """
    <!ELEMENT notes (note)*>

    <!ELEMENT note (text, style*, tagref*)>
    <!ATTLIST note
            id        CDATA #IMPLIED
            handle    ID    #REQUIRED
            priv      (0|1) #IMPLIED
            change    CDATA #REQUIRED
            format    (0|1) #IMPLIED
            type      CDATA #REQUIRED
    >

    <!ELEMENT text (#PCDATA)>

    <!ELEMENT style (range+)>
    <!ATTLIST style
            name    (bold|italic|underline|fontface|fontsize|
                    fontcolor|highlight|superscript|link) #REQUIRED
            value   CDATA #IMPLIED
    >

    <!ELEMENT range EMPTY>
    <!ATTLIST range
            start   CDATA #REQUIRED
            end     CDATA #REQUIRED
    >
    """
    # FIXME limitation: styles are ignored
    TEXT_TAGS = 'text',

    BOOL_ATTRS = 'format',
    STRING_ATTRS = GenericModelObjectSerializer.STRING_ATTRS + ('type',)


#class TagSerializer(GenericModelObjectSerializer):
#    """
#    <!ELEMENT tag EMPTY>
#    <!ATTLIST tag
#            handle    ID    #REQUIRED
#            name      CDATA #REQUIRED
#            color     CDATA #REQUIRED
#            priority  CDATA #REQUIRED
#            change    CDATA #REQUIRED
#    >
#    """
#    # TODO


class CitationSerializer(GenericModelObjectSerializer):
    """
    <!ELEMENT citation ((daterange|datespan|dateval|datestr)?, page?, confidence,
                        noteref*, objref*, srcattribute*, sourceref, tagref*)>
    <!ATTLIST citation
            id        CDATA #IMPLIED
            handle    ID    #REQUIRED
            priv      (0|1) #IMPLIED
            change    CDATA #REQUIRED >
    """
    # TODO


# TODO
"""
<!ELEMENT bookmarks (bookmark)*>
<!ELEMENT bookmark EMPTY>
<!ATTLIST bookmark
        target (person|family|event|source|citation|place|media|repository|
                note) #REQUIRED
        hlink  IDREF #REQUIRED
>

<!--    ************************************************************
NAME MAPS
-->
<!ELEMENT namemaps (map)*>
<!ELEMENT map EMPTY>
<!ATTLIST map
        type  CDATA #REQUIRED
        key   CDATA #REQUIRED
        value CDATA #REQUIRED
>

<!--    ************************************************************
NAME FORMATS
-->

<!ELEMENT name-formats (format)*>
<!ELEMENT format EMPTY>
<!ATTLIST format
        number  CDATA #REQUIRED
        name    CDATA #REQUIRED
        fmt_str CDATA #REQUIRED
        active  (0|1) #IMPLIED
>
"""

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
