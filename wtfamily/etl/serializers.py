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
Extract, Transform, Load: Serializers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

GrampsXML (`lxml.Element`) to WTFamily (native Python data structures).
"""
import datetime
from lxml import etree


def _debug(*args):
    sys.stderr.write(' '.join(str(x) for x in args) + '\n')


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


class AbstractTagCardinality:
    SINGLE_VALUE = False

    def __init__(self, serializer_class):
        self.serializer_class = serializer_class

    def __call__(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__,
                                self.serializer_class.__name__)

    def validate_values(self, values):
        try:
            self._validate_values(values)
        except ValueError as e:
            msg = 'Expected {} for {.__name__}, got {}'.format(
                e, self.serializer_class, len(values))
            raise ValueError(msg) from None

    def _validate_values(self, values):
        raise NotImplementedError


class One(AbstractTagCardinality):
    SINGLE_VALUE = True

    def _validate_values(self, values):
        if len(values) != 1:
            raise ValueError('one value')


class MaybeOne(AbstractTagCardinality):
    SINGLE_VALUE = True

    def _validate_values(self, values):
        if len(values) > 1:
            raise ValueError('0..1 values')


class OneOrMore(AbstractTagCardinality):
    def _validate_values(self, values):
        if len(values) < 1:
            raise ValueError('1..n values')


class MaybeMany(AbstractTagCardinality):
    def _validate_values(self, values):
        # zero is fine, one is fine, many are fine, chill out, man
        pass


def tag_serializer_factory(tags=None, attrs=None, as_text=False, text_from=None):

    class AdHocTagSerializer(TagSerializer):
        TAGS = tags or {}
        ATTRS = attrs or ()
        AS_TEXT = as_text
        TEXT_UNDER_KEY = text_from

    return AdHocTagSerializer


class TagSerializer:
    TAGS = {}
    ATTRS = ()
    AS_TEXT = False
    TEXT_UNDER_KEY = None

    def __init__(self):
        if self.TAGS and self.AS_TEXT:
            # This is not necessarily so, but very unlikely, especially given
            # the GrampsXML DTD.
            raise ValueError('TAGS and AS_TEXT are mutually exclusive.')

    def from_xml(self, el):
        data = {}

        for attr in el.attrib:
            if attr not in self.ATTRS:
                _debug('{}: unexpected attr {}'.format(el.tag, attr))

                continue

            data[attr] = el.get(attr)

        if self.AS_TEXT:
            return el.text

        if self.TEXT_UNDER_KEY:
            data[self.TEXT_UNDER_KEY] = el.text

        for nested_el in el:
            nested_tag = nested_el.tag

            if nested_tag not in self.TAGS:
                _debug('{}: unexpected nested tag {}'.format(el.tag, nested_tag))

                continue

            Serializer = self.TAGS[nested_tag]

            is_list = True
            if isinstance(Serializer, AbstractTagCardinality):
                if Serializer.SINGLE_VALUE:
                    is_list = False

            value = Serializer().from_xml(nested_el)

            if is_list:
                data.setdefault(nested_tag, []).append(value)
            else:
                data[nested_tag] = value

        return data

    def to_xml(self, tag, data, id_to_handle):
        elem = etree.Element(tag)

        for attr in self.ATTRS:
            value = data.get(attr)

            if value is not None:
                elem.set(attr, normalize_attr_value(value))

        extra_attrs = self.make_extra_attrs(data, id_to_handle)
        if extra_attrs:
            for key in sorted(extra_attrs):
                elem.set(key, extra_attrs[key])

        for nested_tag, Serializer in self.TAGS.items():

            # NOTE: subtag == key, but may be different
            values = data.get(nested_tag)

            if values is None:
                values = []
            elif not isinstance(values, list):
                values = [values]

            if isinstance(Serializer, AbstractTagCardinality):
                Serializer.validate_values(values)

            for value in values:
                serializer = Serializer()
                nested_elem = serializer.to_xml(nested_tag, value, id_to_handle)
                elem.append(nested_elem)

        try:
            if self.AS_TEXT:
                text_value = self._make_text_value(data)
            elif self.TEXT_UNDER_KEY:
                text_value = self._make_text_value(data.get(self.TEXT_UNDER_KEY))
            else:
                text_value = None
        except Exception as e:
            raise type(e)('{}: {}'.format(tag, e))

        if text_value:
            elem.text = text_value

        return elem

    def make_extra_attrs(self, data, id_to_handle):
        return None

    def _make_text_value(self, value):
        if not isinstance(value, str):
            raise ValueError('expected string, got {}: {!r}'
                             .format(type(value), value))
        return value


class TextTagSerializer(TagSerializer):
    """
    Generates a ``<foo>some text</foo>`` element.
    """
    AS_TEXT = True

    def from_xml(self, el):
        return el.text


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


class UrlTagSerializer(TagSerializer):
    """
    <!ELEMENT url EMPTY>
    <!ATTLIST url
            priv        (0|1) #IMPLIED
            type        CDATA #IMPLIED
            href        CDATA #REQUIRED
            description CDATA #IMPLIED
    >
    """
    ATTRS = 'priv', 'type', 'href', 'description'


class PersonGenderTagSerializer(EnumTagSerializer):
    ALLOWED_VALUES = 'M', 'F', 'U'


class PersonSurnameTagSerializer(TagSerializer):
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
    TEXT_UNDER_KEY = 'text'


class RefTagSerializer(TagSerializer):
    """
    Generates ``<foo hlink="foo" />`` elements.
    """
    def make_extra_attrs(self, data, id_to_handle):
        if not isinstance(data, dict):
            raise ValueError('Expected dict, got "{}"'.format(data))

        try:
            pk = data['id']
        except KeyError as e:
            _debug(data)
            raise e

        # `hlink` contains "handle", the internal Gramps ID.
        # WTFamily preserves it but relies on the public ID.
        # We use a global ID-to-handle mapping to convert them back.
        #
        # FIXME this won't work for newly added items.  Options:
        # - generate a "handle" now
        # - generate it always internally
        # - use ObjectId
        # - use public ID
        handle = id_to_handle[pk]

        if not isinstance(handle, str):
            raise ValueError('handle: expected string, got {}: "{}"'
                             .format(type(handle), handle))

        return {
            'hlink': handle,
        }


class AttributeTagSerializer(TagSerializer):
    ATTRS = 'priv', 'type', 'value'


class GreedyDictTagSerializer(TagSerializer):
    """
    Generates ``<foo a="1" b="2" />`` elements, mapping *all* keys from a list
    of dicts to element attributes.
    """
    def to_xml(self, tag, data, id_to_handle):
        if not isinstance(data, dict):
            raise ValueError('Expected dict, got "{}"'.format(data))

        value = dict((k, normalize_attr_value(v))
                     for k, v in data.items())

        return etree.Element(tag, value)


# TODO: transform (WTFamily has a different inner structure)
class DateValTagSerializer(GreedyDictTagSerializer):
    pass


class EventRefTagSerializer(RefTagSerializer):
    ATTRS = 'role',


class MediaObjectRefTagSerializer(RefTagSerializer):
    TAGS = {
        'region': MaybeOne(GreedyDictTagSerializer),
    }


class ChildRefTagSerializer(RefTagSerializer):
    """
    <!-- (None|Birth|Adopted|Stepchild|Sponsored|Foster|Other|Unknown) -->
    <!ELEMENT childref (citationref*,noteref*)>
    <!ATTLIST childref
            hlink IDREF #REQUIRED
            priv  (0|1) #IMPLIED
            mrel  CDATA #IMPLIED
            frel  CDATA #IMPLIED
    >
    """
    # NOTE: both `mrel` and `frel` are ENUMs, see DTD.
    ATTRS = 'hlink', 'priv', 'mrel', 'frel'
    TAGS = {
        'citationref': MaybeMany(RefTagSerializer),
        'noteref': MaybeMany(RefTagSerializer),
    }


class AddressTagSerializer(TagSerializer):
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


class LocationTagSerializer(TagSerializer):
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
    ATTRS = ('street', 'locality', 'city', 'parish', 'county', 'state',
             'country', 'postal', 'phone')


class PlaceNameTagSerializer(TagSerializer):
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


class PersonNameTagSerializer(TagSerializer):
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
    ATTRS = 'id', 'handle', 'priv', 'change', 'alt', 'type', 'sort', 'display'
    TAGS = {
        'first': TextTagSerializer,
        'call': TextTagSerializer,
        'surname': PersonSurnameTagSerializer,
        'suffix': TextTagSerializer,
        'title': TextTagSerializer,
        'nick': TextTagSerializer,
        'familynick': TextTagSerializer,
        'group': TextTagSerializer,
        # TODO: date tags
        'noteref': RefTagSerializer,
        'citationref': RefTagSerializer,
    }


class PersonRefTagSerializer(RefTagSerializer):
    """
    <!ELEMENT personref (citationref*, noteref*)>
    <!ATTLIST personref
            hlink IDREF #REQUIRED
            priv  (0|1) #IMPLIED
            rel   CDATA #REQUIRED
    >
    """
    ATTRS = 'hlink', 'priv', 'rel'
    TAGS = {
        'citationref': MaybeMany(RefTagSerializer),
        'noteref': MaybeMany(RefTagSerializer),
    }


class PersonSerializer(TagSerializer):
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
    """
    # TODO: "default" and "home" attrs on the *list* (the `people` tag)

    ATTRS = 'id', 'handle', 'priv', 'change'
    TAGS = {
        'gender': One(PersonGenderTagSerializer),
        'name': MaybeMany(PersonNameTagSerializer),
        'eventref': MaybeMany(EventRefTagSerializer),
        #'lds_ord': ... - WTF?
        'objref': MaybeMany(MediaObjectRefTagSerializer),
        'address': MaybeMany(AddressTagSerializer),
        'attribute': MaybeMany(AttributeTagSerializer),
        'url': MaybeMany(UrlTagSerializer),
        'childof': MaybeMany(RefTagSerializer),
        'parentin': MaybeMany(RefTagSerializer),
        'personref': MaybeMany(PersonRefTagSerializer),
        'citationref': MaybeMany(RefTagSerializer),
        'tagref': MaybeMany(RefTagSerializer),
    }


class FamilySerializer(TagSerializer):
    """
    <!ELEMENT families (family)*>

    <!ELEMENT family (rel?, father?, mother?, eventref*, lds_ord*, objref*,
                      childref*, attribute*, noteref*, citationref*, tagref*)>

    <!ELEMENT father EMPTY>
    <!ATTLIST father hlink IDREF #REQUIRED>

    <!ELEMENT mother EMPTY>
    <!ATTLIST mother hlink IDREF #REQUIRED>

    <!ELEMENT type (#PCDATA)>

    <!ELEMENT rel EMPTY>
    <!ATTLIST rel type CDATA #REQUIRED>
    """
    ATTRS = 'id', 'handle', 'priv', 'change'
    TAGS = {
        'rel': MaybeOne(tag_serializer_factory(attrs=['type'])),
        'father': MaybeOne(RefTagSerializer),
        'mother': MaybeOne(RefTagSerializer),
        'eventref': MaybeMany(EventRefTagSerializer),
        'objref': MaybeMany(MediaObjectRefTagSerializer),
        'childref': MaybeMany(ChildRefTagSerializer),
        'attribute': MaybeMany(AttributeTagSerializer),
        'noteref': MaybeMany(RefTagSerializer),
        'citationref': MaybeMany(RefTagSerializer),
        'tagref': MaybeMany(RefTagSerializer),
    }


class EventSerializer(TagSerializer):
    """
    <!ELEMENT events (event)*>

    <!ELEMENT event (type?, (daterange|datespan|dateval|datestr)?, place?, cause?,
                     description?, attribute*, noteref*, citationref*, objref*,
                     tagref*)>
    """
    ATTRS = 'id', 'handle', 'priv', 'change'
    TAGS = {
        'type': MaybeOne(TextTagSerializer),

        # TODO
        # (daterange | datespan | dateval | datestr)?,

        'place': MaybeOne(RefTagSerializer),
        'cause': MaybeOne(TextTagSerializer),
        'description': MaybeOne(TextTagSerializer),
        'attribute': MaybeMany(AttributeTagSerializer),
        'noteref': MaybeMany(RefTagSerializer),
        'citationref': MaybeMany(RefTagSerializer),
        'objref': MaybeMany(MediaObjectRefTagSerializer),
        'tagref': MaybeMany(RefTagSerializer),
    }


class SourceSerializer(TagSerializer):
    """
    <!ELEMENT sources (source)*>
    <!ELEMENT source (stitle?, sauthor?, spubinfo?, sabbrev?,
                      noteref*, objref*, srcattribute*, reporef*, tagref*)>
    <!ELEMENT stitle   (#PCDATA)>
    <!ELEMENT sauthor  (#PCDATA)>
    <!ELEMENT spubinfo (#PCDATA)>
    <!ELEMENT sabbrev  (#PCDATA)>
    """
    ATTRS = 'id', 'handle', 'priv', 'change'
    TAGS = {
        'stitle': MaybeOne(TextTagSerializer),
        'sauthor': MaybeOne(TextTagSerializer),
        'spubinfo': MaybeOne(TextTagSerializer),
        'sabbrev': MaybeOne(TextTagSerializer),
        'noteref': MaybeMany(RefTagSerializer),
        'objref': MaybeMany(MediaObjectRefTagSerializer),
        'srcattribute': MaybeMany(tag_serializer_factory(attrs=('priv', 'type',
                                                                'value'))),
        'reporef': MaybeMany(RefTagSerializer),
        'tagref': MaybeMany(RefTagSerializer),
    }


class PlaceSerializer(TagSerializer):
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
    ATTRS = 'id', 'handle', 'priv', 'change', 'type'
    TAGS = {
        'ptitle': MaybeOne(TextTagSerializer),
        'pname': OneOrMore(PlaceNameTagSerializer),
        'code': MaybeOne(TextTagSerializer),
        'coord': MaybeOne(GreedyDictTagSerializer),
        'placeref': MaybeMany(RefTagSerializer),
        'location': MaybeMany(LocationTagSerializer),
        'objref': MaybeMany(MediaObjectRefTagSerializer),
        'url': MaybeMany(UrlTagSerializer),
        'noteref': MaybeMany(RefTagSerializer),
        'citationref': MaybeMany(RefTagSerializer),
        'tagref': MaybeMany(RefTagSerializer),
    }


class MediaObjectSerializer(TagSerializer):
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
    ATTRS = 'id', 'handle', 'priv', 'change'
    TAGS = {
        'file': One(tag_serializer_factory(
            attrs=('src', 'mime', 'checksum', 'description'))),
        'attribute': MaybeMany(AttributeTagSerializer),
        'noteref': MaybeMany(RefTagSerializer),

        # TODO: datetime tags

        'citationref': MaybeMany(RefTagSerializer),
        'tagref': MaybeMany(RefTagSerializer),
    }


class RepositorySerializer(TagSerializer):
    """
    <!ELEMENT repositories (repository)*>

    <!ELEMENT repository (rname, type, address*, url*, noteref*, tagref*)>
    <!ATTLIST repository
            id        CDATA #IMPLIED
            handle    ID    #REQUIRED
            priv      (0|1) #IMPLIED
            change    CDATA #REQUIRED
    >

    <!ELEMENT rname   (#PCDATA)>
    """
    ATTRS = 'id', 'handle', 'priv', 'change'
    TAGS = {
        'rname': One(TextTagSerializer),
        'type': One(TextTagSerializer),
        'address': MaybeMany(AddressTagSerializer),
        'url': MaybeMany(UrlTagSerializer),
        'noteref': MaybeMany(RefTagSerializer),
        'tagref': MaybeMany(RefTagSerializer),
    }


class NoteSerializer(TagSerializer):
    ATTRS = 'id', 'handle', 'priv', 'change', 'type', 'format'
    TAGS = {
        'text': TextTagSerializer,
        'tagref': RefTagSerializer,
        'style': tag_serializer_factory(
            attrs=('name', 'value'),
            tags={
                'range': GreedyDictTagSerializer
            }
        )
    }


#class TagObjectSerializer(TagSerializer):
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
#    ATTRS = 'handle', 'name', 'color', 'priority', 'change'


class CitationSerializer(TagSerializer):
    """
    <!ELEMENT citation ((daterange|datespan|dateval|datestr)?, page?, confidence,
                        noteref*, objref*, srcattribute*, sourceref, tagref*)>
    <!ATTLIST citation
            id        CDATA #IMPLIED
            handle    ID    #REQUIRED
            priv      (0|1) #IMPLIED
            change    CDATA #REQUIRED >
    """
    ATTRS = 'id', 'handle', 'priv', 'change'
    TAGS = {
        # TODO: date tags
        'page': MaybeOne(TextTagSerializer),
        'confidence': One(TextTagSerializer),
        'noteref': MaybeMany(RefTagSerializer),
        'objref': MaybeMany(MediaObjectRefTagSerializer),
        'srcattribute': MaybeMany(RefTagSerializer),
        'sourceref': One(tag_serializer_factory(
            attrs=('priv', 'type', 'value'))),
        'tagref': MaybeMany(RefTagSerializer),
    }


class BookmarkSerializer(TagSerializer):
    """
    <!ELEMENT bookmarks (bookmark)*>
    <!ELEMENT bookmark EMPTY>
    <!ATTLIST bookmark
            target (person|family|event|source|citation|place|media|repository|
                    note) #REQUIRED
            hlink  IDREF #REQUIRED
    >
    """
    ATTRS = 'target', 'hlink'


class NameMapSerializer(TagSerializer):
    """
    <!ELEMENT namemaps (map)*>
    <!ELEMENT map EMPTY>
    <!ATTLIST map
            type  CDATA #REQUIRED
            key   CDATA #REQUIRED
            value CDATA #REQUIRED
    >
    """
    ATTRS = 'type', 'key', 'value'


class NameFormatSerializer(TagSerializer):
    """
    <!ELEMENT name-formats (format)*>
    <!ELEMENT format EMPTY>
    <!ATTLIST format
            number  CDATA #REQUIRED
            name    CDATA #REQUIRED
            fmt_str CDATA #REQUIRED
            active  (0|1) #IMPLIED
    >
    """
    ATTRS = 'number', 'name', 'fmt_str', 'active'


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
