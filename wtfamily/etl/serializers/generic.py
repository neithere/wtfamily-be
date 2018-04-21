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
Extract, Transform, Load: Generic Serializers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Mapping of XML to native Python data.
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
