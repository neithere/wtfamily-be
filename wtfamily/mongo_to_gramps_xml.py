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
from lxml import etree
import sys

from models import (Entity, Person, Family, Event, Citation, Source, Place,
                    Repository, MediaObject, Note)

WTFAMILY_APP_NAME = 'WTFamily'
GRAMPS_XML_VERSION_TUPLE = (1, 7, 1) # version for Gramps 4.2
GRAMPS_XML_VERSION = '.'.join(str(i) for i in GRAMPS_XML_VERSION_TUPLE)
GRAMPS_URL_HOMEPAGE = "http://gramps-project.org/"


def _reject_to_serialize_dict_as_attr(value):
    raise ValueError('Deep structures must be serialized '
                     'as tags, not attributes: {}'.format(value))


ATTR_VALUE_NORMALIZERS_BY_TYPE = {
    str: str,
    int: str,
    bool: lambda x: str(int(x)),
    datetime.datetime: lambda x: str(int(x.timestamp())),
    dict: _reject_to_serialize_dict_as_attr,
    list: _reject_to_serialize_dict_as_attr
}


def export_to_xml(db):
    declaration = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE database PUBLIC "-//Gramps//DTD Gramps XML %s//EN"\n'
        '"%sxml/%s/grampsxml.dtd">\n'
        % (GRAMPS_XML_VERSION, GRAMPS_URL_HOMEPAGE, GRAMPS_XML_VERSION))

    tree_el = build_xml(db)

    yield declaration
    yield etree.tostring(tree_el, encoding='unicode')


def build_xml(db):
    tree_el = etree.Element('database', {
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
        Place: ('places', 'placeobj', PlaceSerializer),
        MediaObject: ('objects', 'object', MediaObjectSerializer),
        Repository: ('repositories', 'repository', RepositorySerializer),
        Note: ('notes', 'note', NoteSerializer),
        # TODO: Tag: ('tags', 'tag', TagSerializer),
        Citation: ('citations', 'citation', CitationSerializer),
        # TODO: Bookmark: ('bookmarks', 'bookmark', BookmarkSerializer),
        # TODO: NameMap: ('namemaps', 'map', NameMapSerializer),
        # TODO: NameFormat: ('name-formats', 'format', NameFormatSerializer),
    }

    # Gather the mappings of IDs to internal Gramps IDs ("handles").
    # This requires a full iteration over all potentially referenced entities
    # before we try exporting them.
    id_to_handle = {}
    for model in models:
        collection = model._get_collection()
        for x in collection.find({}, projection=['id', 'handle']):
            id_to_handle[x['id']] = x['handle']

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
            item_serializer = ItemSerializer(item_tag, item._data, id_to_handle)
            item_el = item_serializer.make_xml()
            group_el.append(item_el)

    return tree_el


def normalize_attr_value(value):
    if value is None:
        return ''

    value_type = type(value)
    normalizer = ATTR_VALUE_NORMALIZERS_BY_TYPE.get(value_type)

    if normalizer:
        return normalizer(value)
    else:
        raise ValueError('Normalizer not found for {} attribute "{}"'
                         .format(type(value).__name__, value))


class BaseTagSerializer:
    TAGS = {}
    ATTRS = ()
    AS_TEXT = False
    TEXT_FROM = None

    def __init__(self, tag, data, id_to_handle):
        if self.TAGS and self.AS_TEXT:
            # This is not necessarily so, but very unlikely, especially given
            # the GrampsXML DTD.
            raise ValueError('TAGS and AS_TEXT are mutually exclusive.')

        self.tag = tag
        self.data = data
        self.id_to_handle = id_to_handle

    def make_xml(self):
        data = self.data

        elem = etree.Element(self.tag)

        for attr in self.ATTRS:
            value = data.get(attr)

            if value is not None:
                elem.attrib[attr] = normalize_attr_value(value)

        extra_attrs = self.make_extra_attrs(data)
        if extra_attrs:
            elem.attrib.update(extra_attrs)


        for subtag, Subserializer in self.TAGS.items():
            # NOTE: subtag == key, but may be different
            values = data.get(subtag)

            # TODO: check for required tags
            if values is None:
                continue

            if not isinstance(values, list):
                values = [values]

            for value in values:
                subserializer = Subserializer(subtag, value, self.id_to_handle)
                subelem = subserializer.make_xml()
                elem.append(subelem)

        if self.AS_TEXT:
            text_value = self._make_text_value(data)
        elif self.TEXT_FROM:
            text_value = self._make_text_value(data.get(self.TEXT_FROM))
        else:
            text_value = None

        if text_value:
            elem.text = text_value

        return elem

    def make_extra_attrs(self, data):
        return None

    def _make_text_value(self, value):
        if not isinstance(value, str):
            raise ValueError('{}: expected string, got {}: {!r}'
                             .format(self.tag, type(value), value))
        return value


class TextTagSerializer(BaseTagSerializer):
    """
    Generates a ``<foo>some text</foo>`` element.
    """
    AS_TEXT = True


class EnumTagSerializer(TextTagSerializer):
    """
    Generates a ``<foo>some text</foo>`` element where `some text` belongs
    to a pre-defined set of values.
    """
    ALLOWED_VALUES = []

    def _prepare_value(self, value):
        if value not in self.ALLOWED_VALUES:
            raise ValueError('{}: expected one of {}, got "{}"'
                             .format(self.ALLOWED_VALUES, value))

        return value


class PersonGenderTagSerializer(EnumTagSerializer):
    ALLOWED_VALUES = 'M', 'F', 'U'


class PersonSurnameTagSerializer(BaseTagSerializer):
    """
    This tag is weirdly named in GrampsXML.  In fact it's any name other
    than first name or nickname, including patronymic and so on.

    <!ELEMENT surname    (#PCDATA)>
    <!-- (Unknown|Inherited|Given|Taken|Patronymic|Matronymic|Feudal|
    Pseudonym|Patrilineal|Matrilineal|Occupation|Location) -->
    <!ATTLIST surname
            prefix      CDATA #IMPLIED
            prim        (1|0) #IMPLIED
            derivation  CDATA #IMPLIED
            connector   CDATA #IMPLIED
    >
    """
    # TODO: enum attr "derivation"
    ATTRS = 'prefix', 'prim', 'derivation', 'connector'
    TEXT_FROM = 'text'


class RefTagSerializer(BaseTagSerializer):
    """
    Generates ``<foo hlink="foo" />`` elements.
    """
    def make_extra_attrs(self, data):
        if not isinstance(data, dict):
            raise ValueError('Expected dict, got "{}"'.format(data))

        pk = data['id']

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

        if not isinstance(handle, str):
            raise ValueError('handle: expected string, got {}: "{}"'
                             .format(type(handle), handle))

        return {
            'hlink': handle,
        }


class AttributeTagSerializer(BaseTagSerializer):
    ATTRS = 'priv', 'type', 'value'


class GreedyDictTagSerializer(BaseTagSerializer):
    """
    Generates ``<foo a="1" b="2" />`` elements, mapping *all* keys from a list
    of dicts to element attributes.
    """
    def make_xml(self):
        raw_value = self.data

        if not isinstance(raw_value, dict):
            raise ValueError('Expected dict, got "{}"'.format(raw_value))

        value = dict((k, normalize_attr_value(v))
                     for k, v in raw_value.items())

        return etree.Element(self.tag, value)


# TODO: transform (WTFamily has a different inner structure)
class DateValTagSerializer(GreedyDictTagSerializer):
    pass


class EventRefTagSerializer(RefTagSerializer):
    ATTRS = 'role',


class MediaObjectRefTagSerializer(RefTagSerializer):
    TAGS = {
        'region': GreedyDictTagSerializer,
    }


class AddressTagSerializer(BaseTagSerializer):
    """
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
    # TODO: this is generic enough to make any ModelSerializer subclass of TagSerializer
    TAGS = {
        # TODO: 'dateval': DateValExtractor(key='date'),
        'dateval': DateValTagSerializer,

        'street': TextTagSerializer,
        'locality': TextTagSerializer,
        'city': TextTagSerializer,
        'county': TextTagSerializer,
        'state': TextTagSerializer,
        'country': TextTagSerializer,
        'postal': TextTagSerializer,
        'phone': TextTagSerializer,
        'noteref': RefTagSerializer,
        'citationref': RefTagSerializer,
    }


class LocationTagSerializer(GreedyDictTagSerializer):
    """
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
    pass


class PlaceNameTagSerializer(BaseTagSerializer):
    """
    <!ELEMENT pname (daterange|datespan|dateval|datestr)?>

    <!ATTLIST pname
            lang CDATA #IMPLIED
            value CDATA #REQUIRED
    >
    """
    TAGS = {
        'daterange': GreedyDictTagSerializer,
        'datespan': GreedyDictTagSerializer,
        'dateval': GreedyDictTagSerializer,
        'datestr': GreedyDictTagSerializer,
    }
    ATTRS = 'lang', 'value'


class PersonNameTagSerializer(BaseTagSerializer):
    """
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
    """
    # TODO: bool attrs, etc.
    ATTRS = BaseTagSerializer.ATTRS + ('alt', 'type', 'sort', 'display')
    TAGS = {
        'first': TextTagSerializer,
        'call': TextTagSerializer,
        'suffix': TextTagSerializer,
        'title': TextTagSerializer,
        'nick': TextTagSerializer,
        'familynick': TextTagSerializer,
        'group': TextTagSerializer,
        'surname': PersonSurnameTagSerializer,
    }


class GenericModelObjectSerializer:
    TAGS = {}

    STRING_ATTRS = 'id', 'handle'
    BOOL_ATTRS = 'priv',
    TIMESTAMP_ATTRS = 'change',

    def __init__(self, tag, obj, id_to_handle):
        self.tag = tag
        self.obj = obj
        self.id_to_handle = id_to_handle

    def make_xml(self):
        attrs = self.make_attrs()
        el = etree.Element(self.tag, **attrs)
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
        for key, Serializer in self.TAGS.items():
            # NOTE: key == tag, but somewhere it may differ(?)
            tag = key

            if key not in self.obj:
                continue

            values = self.obj.get(key)

            # Some tags can only be present once (DTD: `father?`),
            # they are internally represented as dictionaries.
            # Some tags are 0..n/1..n (DTD: `childref*`, `pname+`),
            # those will be lists of dictionaries.
            # Here we temporarily represent all of them as lists.
            if not isinstance(values, list):
                values = [values]

            for value in values:
                serializer = Serializer(tag, value, self.id_to_handle)

                yield serializer.make_xml()

    def _set_string(self, target, key, required=False):
        value = self.obj.get(key)
        if required or value:
            target[key] = str(value or '')

    def _set_timestamp(self, target, key, required=False):
        value = self.obj.get(key)
        if required or value:
            target[key] = str(int(value.timestamp())) if value else ''

    def _set_bool(self, target, key, required=False):
        value = self.obj.get(key)
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

    """
    TAGS = {
        'gender': PersonGenderTagSerializer,
        'name': PersonNameTagSerializer,
        'eventref': EventRefTagSerializer,
        #'lds_ord': ... - WTF?
        'objref': MediaObjectRefTagSerializer,
        'address': AddressTagSerializer,
        'attribute': AttributeTagSerializer,
        'url': GreedyDictTagSerializer,
        'childof': RefTagSerializer,
        'parentin': RefTagSerializer,
        'personref': RefTagSerializer,
        'citationref': RefTagSerializer,
        'tagref': RefTagSerializer,
    }


class FamilySerializer(GenericModelObjectSerializer):
    """
    <!ELEMENT families (family)*>

    <!ELEMENT family (rel?, father?, mother?, eventref*, lds_ord*, objref*,
                      childref*, attribute*, noteref*, citationref*, tagref*)>

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
    TAGS = {
        'rel': GreedyDictTagSerializer,
        'father': RefTagSerializer,
        'mother': RefTagSerializer,
        'eventref': EventRefTagSerializer,
        'objref': MediaObjectRefTagSerializer,
        'childref': RefTagSerializer,
        'attribute': AttributeTagSerializer,
        'noteref': RefTagSerializer,
        'citationref': RefTagSerializer,
        'tagref': RefTagSerializer,
    }


class EventSerializer(GenericModelObjectSerializer):
    """
    <!ELEMENT events (event)*>

    <!ELEMENT event (type?, (daterange|datespan|dateval|datestr)?, place?, cause?,
                     description?, attribute*, noteref*, citationref*, objref*,
                     tagref*)>
    """
    TAGS = {
        'type': TextTagSerializer,
        'description': TextTagSerializer,
        'place': RefTagSerializer,
        'citationref': RefTagSerializer,
        'noteref': RefTagSerializer,
        'objref': MediaObjectRefTagSerializer,
        'tagref': RefTagSerializer,
    }

    # TODO
    # (daterange | datespan | dateval | datestr)?,
    # \attribute*,


class SourceSerializer(GenericModelObjectSerializer):
    """
    <!ELEMENT sources (source)*>
    <!ELEMENT source (stitle?, sauthor?, spubinfo?, sabbrev?,
                      noteref*, objref*, srcattribute*, reporef*, tagref*)>
    <!ELEMENT stitle   (#PCDATA)>
    <!ELEMENT sauthor  (#PCDATA)>
    <!ELEMENT spubinfo (#PCDATA)>
    <!ELEMENT sabbrev  (#PCDATA)>
    """
    # TODO


class PlaceSerializer(GenericModelObjectSerializer):
    """
    <!ELEMENT placeobj (ptitle?, pname+, code?, coord?, placeref*, location*,
                        objref*, url*, noteref*, citationref*, tagref*)>

    <!ELEMENT ptitle (#PCDATA)>
    <!ELEMENT code (#PCDATA)>

    <!ELEMENT coord EMPTY>
    <!ATTLIST coord
            long CDATA #REQUIRED
            lat  CDATA #REQUIRED
    >

    <!ELEMENT location EMPTY>
    """
    STRING_ATTRS = GenericModelObjectSerializer.STRING_ATTRS + ('type',)
    TAGS = {
        'pname': PlaceNameTagSerializer,
        'ptitle': TextTagSerializer,
        'code': TextTagSerializer,
        'coord': GreedyDictTagSerializer,
        'placeref': RefTagSerializer,
        'location': LocationTagSerializer,
        'objref': MediaObjectRefTagSerializer,
        'url': GreedyDictTagSerializer,
        'noteref': RefTagSerializer,
        'citationref': RefTagSerializer,
        'tagref': RefTagSerializer,
    }


class MediaObjectSerializer(GenericModelObjectSerializer):
    """
    <!ELEMENT object (file, attribute*, noteref*,
                     (daterange|datespan|dateval|datestr)?, citationref*, tagref*)>

    <!ELEMENT file EMPTY>
    <!ATTLIST file
            src         CDATA #REQUIRED
            mime        CDATA #REQUIRED
            checksum    CDATA #IMPLIED
            description CDATA #REQUIRED
    >
    """
    # TODO
    TAGS = {
        'file': GreedyDictTagSerializer,
    }


class RepositorySerializer(GenericModelObjectSerializer):
    TAGS = {
        'rname': TextTagSerializer,
        'type': TextTagSerializer,
        'noteref': RefTagSerializer,
        'tagref': RefTagSerializer,
        'url': GreedyDictTagSerializer,
        'address': AddressTagSerializer,
    }


class NoteSerializer(GenericModelObjectSerializer):
    TAGS = {
        'text': TextTagSerializer,
        'tagref': RefTagSerializer,
        'style': GreedyDictTagSerializer,
        'range': GreedyDictTagSerializer,
    }

    BOOL_ATTRS = GenericModelObjectSerializer.BOOL_ATTRS + ('format',)
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
#    # NOTE: some common attribs are *NOT* inherited (id, priv, etc.)
#    STRING_ATTRS = 'color',


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
