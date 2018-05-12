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
Extract, Transform, Load: Translators
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

    # tag translators
    TagTranslatorContributor,
    TagTranslator,
    TextTagTranslator,
    EnumTagTranslator,

    # functions
    tag_translator_factory,
    _debug
)


def _get_child(el, child_tag):
    for child_el in el.getchildren():
        if child_el.tag == child_tag:
            return child_el


def _dict_from_keys(src_data, verbatim_keys, renamed_keys=None):
    data = {}

    for k in verbatim_keys:
        data[k] = src_data.get(k)

    if renamed_keys:
        for k, new_name in renamed_keys.items():
            data[new_name] = src_data.get(k)

    return data


def _filter_dict(**kwargs):
    data = {}
    for k in kwargs:
        v = kwargs[k]
        if v:
            data[k] = v
    return data


class DateContributor(TagTranslatorContributor):
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

    <!ELEMENT datespan EMPTY>
    <!ATTLIST datespan
            start     CDATA                  #REQUIRED
            stop      CDATA                  #REQUIRED
            quality   (estimated|calculated) #IMPLIED
            cformat   CDATA                  #IMPLIED
            dualdated (0|1)                  #IMPLIED
            newyear   CDATA                  #IMPLIED
    >

    <!ELEMENT dateval EMPTY>
    <!ATTLIST dateval
            val       CDATA                  #REQUIRED
            type      (before|after|about)   #IMPLIED
            quality   (estimated|calculated) #IMPLIED
            cformat   CDATA                  #IMPLIED
            dualdated (0|1)                  #IMPLIED
            newyear   CDATA                  #IMPLIED
    >

    <!ELEMENT datestr EMPTY>
    <!ATTLIST datestr val CDATA #REQUIRED>
    """
    TAG_NAMES = 'datestr', 'dateval', 'daterange', 'datespan'

    # TODO:
    # - cformat
    # - dualdated
    # - newyear

    MOD_TEXTONLY = 'textonly'
    MOD_RANGE = 'range'
    MOD_SPAN = 'span'

    @classmethod
    def from_xml(cls, el):
        datestr_el = _get_child(el, 'datestr')
        dateval_el = _get_child(el, 'dateval')
        daterange_el = _get_child(el, 'daterange')
        datespan_el = _get_child(el, 'datespan')

        # can't say just `foo or bar` because Element.__bool__ is deprecated :(
        elems = datestr_el, dateval_el, daterange_el, datespan_el
        present_els = [x for x in elems if x is not None]

        # we expect exactly one or none
        # TODO: container should be able to also require exactly one
        try:
            present_el = present_els[0]
        except IndexError as e:
            return {}

        date = _dict_from_keys(present_el.attrib,
                               verbatim_keys=['start', 'stop', 'quality'],
                               renamed_keys={'val': 'value'})

        if datestr_el is not None:
            modifier = cls.MOD_TEXTONLY
        elif daterange_el is not None:
            modifier = cls.MOD_RANGE
        elif datespan_el is not None:
            modifier = cls.MOD_SPAN
        else:
            modifier = present_el.get('type')

        date = _filter_dict(modifier=modifier, **date)

        return {
            'date': date,
        }

    @classmethod
    def to_xml(cls, data):
        date_data = data.get('date')
        if not date_data:
            return []

        kwargs = _dict_from_keys(date_data,
                                 verbatim_keys=('quality', 'start', 'stop'),
                                 renamed_keys={'value': 'val'})

        modifier = date_data.get('modifier')

        if modifier == cls.MOD_RANGE:
            tag = 'daterange'
        elif modifier == cls.MOD_SPAN:
            tag = 'datespan'
        elif modifier == cls.MOD_TEXTONLY:
            tag = 'datestr'
        else:
            tag = 'dateval'
            kwargs['type'] = modifier

        kwargs = _filter_dict(**kwargs)
        return [etree.Element(tag, **kwargs)]


class UrlTagTranslator(TagTranslator):
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


class PersonGenderTagTranslator(EnumTagTranslator):
    ALLOWED_VALUES = 'M', 'F', 'U'


class PersonSurnameTagTranslator(TagTranslator):
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


class RefTagTranslator(TagTranslator):
    """
    Parses/generates ``<foo hlink="foo" />`` elements.

    The `hlink` attribute contains "handle", the internal Gramps ID.
    WTFamily preserves it but relies on the public ID.
    We use a global ID-to-handle mapping to convert them back.
    """
    ATTRS = {
        'hlink': str,
    }

    def post_normalize_attrs(self, attrs, handle_to_id):
        """
        Normalizes GrampsXML → WTFamily, replaces `hlink` with `id` in refs.
        """
        if not isinstance(attrs, dict):
            raise ValueError('Expected dict, got "{}"'.format(attrs))

        _attrs = attrs.copy()

        try:
            handle = _attrs.pop('hlink')
        except KeyError as e:
            _debug(_attrs)
            raise e

        item_id = handle_to_id[handle]

        if not isinstance(item_id, str):
            raise ValueError('ID: expected string, got {}: "{}"'
                             .format(type(item_id), item_id))

        return dict(_attrs, id=item_id)

    def pre_serialize_attrs(self, data, id_to_handle):
        """
        Serializes WTFamily → GrampsXML, replaces `id` with `hlink` in refs.
        """
        if not isinstance(data, dict):
            raise ValueError('Expected dict, got "{}"'.format(data))

        attrs = super(RefTagTranslator, self).pre_serialize_attrs(data,
                                                                  id_to_handle)

        try:
            pk = data['id']
        except KeyError as e:
            _debug(data, attrs)
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

        return dict(attrs, hlink=handle)


class AttributeTagTranslator(TagTranslator):
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
        'citationref': MaybeMany(RefTagTranslator),
        'noteref': MaybeMany(RefTagTranslator),
    }


class EventRefTagTranslator(RefTagTranslator):
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
        'attribute': MaybeMany(AttributeTagTranslator),
        'noteref': MaybeMany(RefTagTranslator),
    }


class MediaObjectRefTagTranslator(RefTagTranslator):
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
        'region': MaybeOne(tag_translator_factory(attrs={
            'corner1_x': int,
            'corner1_y': int,
            'corner2_x': int,
            'corner2_y': int,
        })),
    }


class ChildRefTagTranslator(RefTagTranslator):
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
        'citationref': MaybeMany(RefTagTranslator),
        'noteref': MaybeMany(RefTagTranslator),
    }


#class DateRangeTagTranslator(TagTranslator):
#    """
#    <!ELEMENT daterange EMPTY>
#    <!ATTLIST daterange
#            start     CDATA                  #REQUIRED
#            stop      CDATA                  #REQUIRED
#            quality   (estimated|calculated) #IMPLIED
#            cformat   CDATA                  #IMPLIED
#            dualdated (0|1)                  #IMPLIED
#            newyear   CDATA                  #IMPLIED
#    >
#    """
#    ATTRS = {
#        'start': str,
#        'stop': str,
#        'quality': str,  # TODO: enum
#        'cformat': str,
#        'dualdated': bool,
#        'newyear': str,
#    }
#
#
#class DateSpanTagTranslator(TagTranslator):
#    """
#    <!ELEMENT datespan EMPTY>
#    <!ATTLIST datespan
#            start     CDATA                  #REQUIRED
#            stop      CDATA                  #REQUIRED
#            quality   (estimated|calculated) #IMPLIED
#            cformat   CDATA                  #IMPLIED
#            dualdated (0|1)                  #IMPLIED
#            newyear   CDATA                  #IMPLIED
#    >
#    """
#    ATTRS = {
#        'start': str,
#        'stop': str,
#        'quality': str,  # TODO: enum
#        'cformat': str,
#        'dualdated': bool,
#        'newyear': str,
#    }
#
#
## TODO: transform (WTFamily has a different inner structure)
#class DateValTagTranslator(TagTranslator):
#    """
#    <!ELEMENT dateval EMPTY>
#    <!ATTLIST dateval
#            val       CDATA                  #REQUIRED
#            type      (before|after|about)   #IMPLIED
#            quality   (estimated|calculated) #IMPLIED
#            cformat   CDATA                  #IMPLIED
#            dualdated (0|1)                  #IMPLIED
#            newyear   CDATA                  #IMPLIED
#    >
#    """
#    ATTRS = {
#        'val': str,
#        'type': str,  # TODO: enum
#        'quality': str,  # TODO: enum
#        'cformat': str,
#        'dualdated': bool,
#        'newyear': str,
#    }
#
#
#class DateStrTagTranslator(TagTranslator):
#    """
#    <!ELEMENT datestr EMPTY>
#    <!ATTLIST datestr val CDATA #REQUIRED>
#    """
#
#    # ignored during serialization
#    ONLY_NORMALIZE = True
#
#    # XXX this works, but inside tag scope → useless (we need cross-tag scope)
#    KEY = 'date'
#
#    ATTRS = {
#        'val': str,
#    }
#
#    def post_normalize_attrs(self, data, *args):
#        val = data.pop('val')
#        return {
#            # TODO: use constants from models
#            'modifier': 'textonly',
#            'value': val
#        }
#
#    def pre_serialize_attrs(self, data, *args):
#        print('pre_serialize_attrs', data)
#        return {
#            'foo': 123,
#        }


class AddressTagTranslator(TagTranslator):
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
    TAGS = {
        ## TODO: MaybeOne(EitherOf(...))
        ## TODO: 'dateval': DateValExtractor(key='date'),
        #'daterange': MaybeOne(DateRangeTagTranslator),
        #'datespan': MaybeOne(DateSpanTagTranslator),
        #'dateval': MaybeOne(DateValTagTranslator),
        #'datestr': MaybeOne(DateStrTagTranslator),

        'street': MaybeOne(TextTagTranslator),
        'locality': MaybeOne(TextTagTranslator),
        'city': MaybeOne(TextTagTranslator),
        'county': MaybeOne(TextTagTranslator),
        'state': MaybeOne(TextTagTranslator),
        'country': MaybeOne(TextTagTranslator),
        'postal': MaybeOne(TextTagTranslator),
        'phone': MaybeOne(TextTagTranslator),

        'noteref': MaybeMany(RefTagTranslator),
        'citationref': MaybeMany(RefTagTranslator),
    }
    CONTRIBUTORS = DateContributor,


class LocationTagTranslator(TagTranslator):
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


class PlaceNameTagTranslator(TagTranslator):
    """
    <!ELEMENT pname (daterange|datespan|dateval|datestr)?>

    <!ATTLIST pname
            lang CDATA #IMPLIED
            value CDATA #REQUIRED
    >
    """
    TAGS = {
        ## TODO: MaybeOne(EitherOf(...))
        #'daterange': MaybeOne(DateRangeTagTranslator),
        #'datespan': MaybeOne(DateSpanTagTranslator),
        #'dateval': MaybeOne(DateValTagTranslator),
        #'datestr': MaybeOne(DateStrTagTranslator),
    }
    ATTRS = 'lang', 'value'
    CONTRIBUTORS = DateContributor,


class PersonNameTagTranslator(TagTranslator):
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
        'first': MaybeOne(TextTagTranslator),
        'call': MaybeOne(TextTagTranslator),
        'surname': MaybeMany(PersonSurnameTagTranslator),
        'suffix': MaybeOne(TextTagTranslator),
        'title': MaybeOne(TextTagTranslator),
        'nick': MaybeOne(TextTagTranslator),
        'familynick': MaybeOne(TextTagTranslator),
        'group': MaybeOne(TextTagTranslator),

        ## TODO: MaybeOne(EitherOf(...))
        #'daterange': MaybeOne(DateRangeTagTranslator),
        #'datespan': MaybeOne(DateSpanTagTranslator),
        #'dateval': MaybeOne(DateValTagTranslator),
        #'datestr': MaybeOne(DateStrTagTranslator),

        'noteref': MaybeMany(RefTagTranslator),
        'citationref': MaybeMany(RefTagTranslator),
    }
    CONTRIBUTORS = DateContributor,


class PersonRefTagTranslator(RefTagTranslator):
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
        'citationref': MaybeMany(RefTagTranslator),
        'noteref': MaybeMany(RefTagTranslator),
    }


class PersonTranslator(TagTranslator):
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
        'gender': One(PersonGenderTagTranslator),
        'name': MaybeMany(PersonNameTagTranslator),
        'eventref': MaybeMany(EventRefTagTranslator),
        #'lds_ord': ... - WTF?
        'objref': MaybeMany(MediaObjectRefTagTranslator),
        'address': MaybeMany(AddressTagTranslator),
        'attribute': MaybeMany(AttributeTagTranslator),
        'url': MaybeMany(UrlTagTranslator),
        'childof': MaybeMany(RefTagTranslator),
        'parentin': MaybeMany(RefTagTranslator),
        'personref': MaybeMany(PersonRefTagTranslator),
        'noteref': MaybeMany(RefTagTranslator),
        'citationref': MaybeMany(RefTagTranslator),
        'tagref': MaybeMany(RefTagTranslator),
    }


class FamilyTranslator(TagTranslator):
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
        'rel': MaybeOne(tag_translator_factory(attrs=['type'])),
        'father': MaybeOne(RefTagTranslator),
        'mother': MaybeOne(RefTagTranslator),
        'eventref': MaybeMany(EventRefTagTranslator),
        'objref': MaybeMany(MediaObjectRefTagTranslator),
        'childref': MaybeMany(ChildRefTagTranslator),
        'attribute': MaybeMany(AttributeTagTranslator),
        'noteref': MaybeMany(RefTagTranslator),
        'citationref': MaybeMany(RefTagTranslator),
        'tagref': MaybeMany(RefTagTranslator),
    }


class EventTranslator(TagTranslator):
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
        'type': MaybeOne(TextTagTranslator),

        ## TODO: MaybeOne(EitherOf(...))
        ## (daterange | datespan | dateval | datestr)?,
        #'daterange': MaybeOne(DateRangeTagTranslator),
        #'datespan': MaybeOne(DateSpanTagTranslator),
        #'dateval': MaybeOne(DateValTagTranslator),
        #'datestr': MaybeOne(DateStrTagTranslator),

        'place': MaybeOne(RefTagTranslator),
        'cause': MaybeOne(TextTagTranslator),
        'description': MaybeOne(TextTagTranslator),
        'attribute': MaybeMany(AttributeTagTranslator),
        'noteref': MaybeMany(RefTagTranslator),
        'citationref': MaybeMany(RefTagTranslator),
        'objref': MaybeMany(MediaObjectRefTagTranslator),
        'tagref': MaybeMany(RefTagTranslator),
    }
    CONTRIBUTORS = DateContributor,


class SourceTranslator(TagTranslator):
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
        'stitle': MaybeOne(TextTagTranslator),
        'sauthor': MaybeOne(TextTagTranslator),
        'spubinfo': MaybeOne(TextTagTranslator),
        'sabbrev': MaybeOne(TextTagTranslator),
        'noteref': MaybeMany(RefTagTranslator),
        'objref': MaybeMany(MediaObjectRefTagTranslator),
        'srcattribute': MaybeMany(tag_translator_factory(attrs=('priv', 'type',
                                                                'value'))),
        'reporef': MaybeMany(RefTagTranslator),
        'tagref': MaybeMany(RefTagTranslator),
    }


class PlaceCoordTagTranslator(TagTranslator):
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


class PlaceTranslator(TagTranslator):
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
        'ptitle': MaybeOne(TextTagTranslator),
        'pname': OneOrMore(PlaceNameTagTranslator),
        'code': MaybeOne(TextTagTranslator),
        'coord': MaybeOne(PlaceCoordTagTranslator),
        'placeref': MaybeMany(RefTagTranslator),
        'location': MaybeMany(LocationTagTranslator),
        'objref': MaybeMany(MediaObjectRefTagTranslator),
        'url': MaybeMany(UrlTagTranslator),
        'noteref': MaybeMany(RefTagTranslator),
        'citationref': MaybeMany(RefTagTranslator),
        'tagref': MaybeMany(RefTagTranslator),
    }


class MediaObjectTranslator(TagTranslator):
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
        'file': One(tag_translator_factory(
            attrs=('src', 'mime', 'checksum', 'description'))),
        'attribute': MaybeMany(AttributeTagTranslator),
        'noteref': MaybeMany(RefTagTranslator),

        ## TODO: MaybeOne(EitherOf(...))
        #'daterange': MaybeOne(DateRangeTagTranslator),
        #'datespan': MaybeOne(DateSpanTagTranslator),
        #'dateval': MaybeOne(DateValTagTranslator),
        #'datestr': MaybeOne(DateStrTagTranslator),

        'citationref': MaybeMany(RefTagTranslator),
        'tagref': MaybeMany(RefTagTranslator),
    }
    CONTRIBUTORS = DateContributor,


class RepositoryTranslator(TagTranslator):
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
        'rname': One(TextTagTranslator),
        'type': One(TextTagTranslator),
        'address': MaybeMany(AddressTagTranslator),
        'url': MaybeMany(UrlTagTranslator),
        'noteref': MaybeMany(RefTagTranslator),
        'tagref': MaybeMany(RefTagTranslator),
    }


class NoteStyleTranslator(TagTranslator):
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


class NoteTranslator(TagTranslator):
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
        'text': One(TextTagTranslator),
        'tagref': MaybeMany(RefTagTranslator),
        'style': MaybeMany(NoteStyleTranslator),
    }


#class TagObjectTranslator(TagTranslator):
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


class CitationTranslator(TagTranslator):
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
        ## TODO: MaybeOne(EitherOf(...))
        #'daterange': MaybeOne(DateRangeTagTranslator),
        #'datespan': MaybeOne(DateSpanTagTranslator),
        #'dateval': MaybeOne(DateValTagTranslator),
        #'datestr': MaybeOne(DateStrTagTranslator),

        'page': MaybeOne(TextTagTranslator),
        'confidence': One(TextTagTranslator),
        'noteref': MaybeMany(RefTagTranslator),
        'objref': MaybeMany(MediaObjectRefTagTranslator),
        'srcattribute': MaybeMany(AttributeTagTranslator),
        'sourceref': One(RefTagTranslator),
        'tagref': MaybeMany(RefTagTranslator),
    }
    CONTRIBUTORS = DateContributor,


class BookmarkTranslator(TagTranslator):
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


class NameMapTranslator(TagTranslator):
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


class NameFormatTranslator(TagTranslator):
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
