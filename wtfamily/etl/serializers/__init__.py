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


from .generic import (
    # cardinality
    One,
    OneOrMore,
    MaybeOne,
    MaybeMany,

    # tag serializers
    TagSerializer,
    TextTagSerializer,
    EnumTagSerializer,

    # functions
    tag_serializer_factory,
    _debug
)


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
    ATTRS = {
        'prefix': str,
        'prim': bool,
        'derivation': str,
        'connector': str,
    }
    TEXT_UNDER_KEY = 'text'


class RefTagSerializer(TagSerializer):
    """
    Parses/generates ``<foo hlink="foo" />`` elements.

    The `hlink` attribute contains "handle", the internal Gramps ID.
    WTFamily preserves it but relies on the public ID.
    We use a global ID-to-handle mapping to convert them back.
    """
    ATTRS = {
        'hlink': str,
    }

    def normalize_extra_attrs(self, data, handle_to_id):
        """
        Normalizes GrampsXML → WTFamily, replaces `hlink` with `id` in refs.
        """
        if not isinstance(data, dict):
            raise ValueError('Expected dict, got "{}"'.format(data))

        try:
            handle = data['hlink']
        except KeyError as e:
            _debug(data)
            raise e

        item_id = handle_to_id[handle]

        if not isinstance(item_id, str):
            raise ValueError('ID: expected string, got {}: "{}"'
                             .format(type(item_id), item_id))

        return {
            'id': item_id,
        }

    def serialize_extra_attrs(self, data, id_to_handle):
        """
        Serializes WTFamily → GrampsXML, replaces `id` with `hlink` in refs.
        """
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
    """
    <!ELEMENT attribute (citationref*, noteref*)>
    <!ATTLIST attribute
            priv    (0|1)   #IMPLIED
            type    CDATA   #REQUIRED
            value   CDATA   #REQUIRED
    >
    """
    ATTRS = {
        'priv': bool,
        'type': str,
        'value': str,
    }
    TAGS = {
        'citationref': MaybeMany(RefTagSerializer),
        'noteref': MaybeMany(RefTagSerializer),
    }


class EventRefTagSerializer(RefTagSerializer):
    """
    <!ELEMENT eventref (attribute*, noteref*)>
    <!ATTLIST eventref
            hlink IDREF #REQUIRED
            priv  (0|1) #IMPLIED
            role  CDATA #IMPLIED
    >
    """
    ATTRS = {
        'hlink': str,
        'role': str,
    }
    TAGS = {
        'attribute': MaybeMany(AttributeTagSerializer),
        'noteref': MaybeMany(RefTagSerializer),
    }


class MediaObjectRefTagSerializer(RefTagSerializer):
    """
    <!ELEMENT objref (region?, attribute*, citationref*, noteref*)>
    <!ATTLIST objref
            hlink IDREF #REQUIRED
            priv (0|1)  #IMPLIED
    >
    """
    ATTRS = {
        'hlink': str,
    }
    TAGS = {
        'region': MaybeOne(tag_serializer_factory(attrs={
            'corner1_x': int,
            'corner1_y': int,
            'corner2_x': int,
            'corner2_y': int,
        })),
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


class DateRangeTagSerializer(TagSerializer):
    """
    <!ELEMENT daterange EMPTY>
    <!ATTLIST daterange
            start     CDATA                  #REQUIRED
            stop      CDATA                  #REQUIRED
            quality   (estimated|calculated) #IMPLIED
            cformat   CDATA                  #IMPLIED
            dualdated (0|1)                  #IMPLIED
            newyear   CDATA                  #IMPLIED
    >
    """
    ATTRS = {
        'start': str,
        'stop': str,
        'quality': str,  # TODO: enum
        'cformat': str,
        'dualdated': bool,
        'newyear': str,
    }


class DateSpanTagSerializer(TagSerializer):
    """
    <!ELEMENT datespan EMPTY>
    <!ATTLIST datespan
            start     CDATA                  #REQUIRED
            stop      CDATA                  #REQUIRED
            quality   (estimated|calculated) #IMPLIED
            cformat   CDATA                  #IMPLIED
            dualdated (0|1)                  #IMPLIED
            newyear   CDATA                  #IMPLIED
    >
    """
    ATTRS = {
        'start': str,
        'stop': str,
        'quality': str,  # TODO: enum
        'cformat': str,
        'dualdated': bool,
        'newyear': str,
    }


# TODO: transform (WTFamily has a different inner structure)
class DateValTagSerializer(TagSerializer):
    """
    <!ELEMENT dateval EMPTY>
    <!ATTLIST dateval
            val       CDATA                  #REQUIRED
            type      (before|after|about)   #IMPLIED
            quality   (estimated|calculated) #IMPLIED
            cformat   CDATA                  #IMPLIED
            dualdated (0|1)                  #IMPLIED
            newyear   CDATA                  #IMPLIED
    >
    """
    ATTRS = {
        'val': str,
        'type': str,  # TODO: enum
        'quality': str,  # TODO: enum
        'cformat': str,
        'dualdated': bool,
        'newyear': str,
    }


class DateStrTagSerializer(TagSerializer):
    """
    <!ELEMENT datestr EMPTY>
    <!ATTLIST datestr val CDATA #REQUIRED>
    """
    ATTRS = {
        'val': str,
    }
    #TEXT_UNDER_ATTR = 'val'


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
        # TODO: MaybeOne(EitherOf(...))
        # TODO: 'dateval': DateValExtractor(key='date'),
        'daterange': MaybeOne(DateRangeTagSerializer),
        'datespan': MaybeOne(DateSpanTagSerializer),
        'dateval': MaybeOne(DateValTagSerializer),
        'datestr': MaybeOne(DateStrTagSerializer),

        'street': MaybeOne(TextTagSerializer),
        'locality': MaybeOne(TextTagSerializer),
        'city': MaybeOne(TextTagSerializer),
        'county': MaybeOne(TextTagSerializer),
        'state': MaybeOne(TextTagSerializer),
        'country': MaybeOne(TextTagSerializer),
        'postal': MaybeOne(TextTagSerializer),
        'phone': MaybeOne(TextTagSerializer),

        'noteref': MaybeMany(RefTagSerializer),
        'citationref': MaybeMany(RefTagSerializer),
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
        # TODO: MaybeOne(EitherOf(...))
        'daterange': MaybeOne(DateRangeTagSerializer),
        'datespan': MaybeOne(DateSpanTagSerializer),
        'dateval': MaybeOne(DateValTagSerializer),
        'datestr': MaybeOne(DateStrTagSerializer),
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
    ATTRS = {
        'id': str,
        'handle': str,
        'priv': bool,
        'change': datetime.datetime,
        'alt': bool,
        'type': str,
        'sort': str,
        'display': str,
    }
    TAGS = {
        'first': MaybeOne(TextTagSerializer),
        'call': MaybeOne(TextTagSerializer),
        'surname': MaybeMany(PersonSurnameTagSerializer),
        'suffix': MaybeOne(TextTagSerializer),
        'title': MaybeOne(TextTagSerializer),
        'nick': MaybeOne(TextTagSerializer),
        'familynick': MaybeOne(TextTagSerializer),
        'group': MaybeOne(TextTagSerializer),

        # TODO: MaybeOne(EitherOf(...))
        'daterange': MaybeOne(DateRangeTagSerializer),
        'datespan': MaybeOne(DateSpanTagSerializer),
        'dateval': MaybeOne(DateValTagSerializer),
        'datestr': MaybeOne(DateStrTagSerializer),

        'noteref': MaybeMany(RefTagSerializer),
        'citationref': MaybeMany(RefTagSerializer),
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
    ATTRS = {
        'hlink': str,
        'priv': bool,
        'rel': str,
    }
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

    ATTRS = {
        'id': str,
        'handle': str,
        'priv': bool,
        'change': datetime.datetime,
    }
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
        'noteref': MaybeMany(RefTagSerializer),
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
    ATTRS = {
        'id': str,
        'handle': str,
        'priv': bool,
        'change': datetime.datetime,
    }
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
    ATTRS = {
        'id': str,
        'handle': str,
        'priv': bool,
        'change': datetime.datetime,
    }
    TAGS = {
        'type': MaybeOne(TextTagSerializer),

        # TODO: MaybeOne(EitherOf(...))
        # (daterange | datespan | dateval | datestr)?,
        'daterange': MaybeOne(DateRangeTagSerializer),
        'datespan': MaybeOne(DateSpanTagSerializer),
        'dateval': MaybeOne(DateValTagSerializer),
        'datestr': MaybeOne(DateStrTagSerializer),

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
    ATTRS = {
        'id': str,
        'handle': str,
        'priv': bool,
        'change': datetime.datetime,
    }
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


class PlaceCoordTagSerializer(TagSerializer):
    """
    <!ELEMENT coord EMPTY>
    <!ATTLIST coord
            long CDATA #REQUIRED
            lat  CDATA #REQUIRED
    >
    """
    ATTRS = {
        'long': str,
        'lat': str,
    }


class PlaceSerializer(TagSerializer):
    """
    <!ELEMENT placeobj (ptitle?, pname+, code?, coord?, placeref*, location*,
                        objref*, url*, noteref*, citationref*, tagref*)>

    <!ELEMENT ptitle (#PCDATA)>
    <!ELEMENT code (#PCDATA)>

    <!ELEMENT location EMPTY>
    """
    ATTRS = {
        'id': str,
        'handle': str,
        'priv': bool,
        'change': datetime.datetime,
        'type': str,
    }
    TAGS = {
        'ptitle': MaybeOne(TextTagSerializer),
        'pname': OneOrMore(PlaceNameTagSerializer),
        'code': MaybeOne(TextTagSerializer),
        'coord': MaybeOne(PlaceCoordTagSerializer),
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
    ATTRS = {
        'id': str,
        'handle': str,
        'priv': bool,
        'change': datetime.datetime,
    }
    TAGS = {
        'file': One(tag_serializer_factory(
            attrs=('src', 'mime', 'checksum', 'description'))),
        'attribute': MaybeMany(AttributeTagSerializer),
        'noteref': MaybeMany(RefTagSerializer),

        # TODO: MaybeOne(EitherOf(...))
        'daterange': MaybeOne(DateRangeTagSerializer),
        'datespan': MaybeOne(DateSpanTagSerializer),
        'dateval': MaybeOne(DateValTagSerializer),
        'datestr': MaybeOne(DateStrTagSerializer),

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
    ATTRS = {
        'id': str,
        'handle': str,
        'priv': bool,
        'change': datetime.datetime,
    }
    TAGS = {
        'rname': One(TextTagSerializer),
        'type': One(TextTagSerializer),
        'address': MaybeMany(AddressTagSerializer),
        'url': MaybeMany(UrlTagSerializer),
        'noteref': MaybeMany(RefTagSerializer),
        'tagref': MaybeMany(RefTagSerializer),
    }


class NoteStyleSerializer(TagSerializer):
    """
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
    ATTRS = {
        'name': str,
        'value': str,
    }
    TAGS = {
        'range': OneOrMore({
            'attrs': {
                'start': int,
                'end': int,
            }
        })
    }


class NoteSerializer(TagSerializer):
    """
    <!ELEMENT note (text, style*, tagref*)>
    <!ATTLIST note
            id        CDATA #IMPLIED
            handle    ID    #REQUIRED
            priv      (0|1) #IMPLIED
            change    CDATA #REQUIRED
            format    (0|1) #IMPLIED
            type      CDATA #REQUIRED
    >
    """
    ATTRS = {
        'id': str,
        'handle': str,
        'priv': bool,
        'change': datetime.datetime,
        'type': str,
        'format': bool,
    }
    TAGS = {
        'text': One(TextTagSerializer),
        'tagref': MaybeMany(RefTagSerializer),
        'style': MaybeMany(NoteStyleSerializer),
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
    ATTRS = {
        'id': str,
        'handle': str,
        'priv': bool,
        'change': datetime.datetime,
    }
    TAGS = {
        # TODO: MaybeOne(EitherOf(...))
        'daterange': MaybeOne(DateRangeTagSerializer),
        'datespan': MaybeOne(DateSpanTagSerializer),
        'dateval': MaybeOne(DateValTagSerializer),
        'datestr': MaybeOne(DateStrTagSerializer),

        'page': MaybeOne(TextTagSerializer),
        'confidence': One(TextTagSerializer),
        'noteref': MaybeMany(RefTagSerializer),
        'objref': MaybeMany(MediaObjectRefTagSerializer),
        'srcattribute': MaybeMany(AttributeTagSerializer),
        'sourceref': One(RefTagSerializer),
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
    ATTRS = {
        'target': str,  # TODO: enum
        'hlink': str,
    }


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
    ATTRS = {
        'type': str,
        'key': str,
        'value': str,
    }


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
    ATTRS = {
        'number': str,
        'name': str,
        'fmt_str': str,
        'active': bool,
    }
