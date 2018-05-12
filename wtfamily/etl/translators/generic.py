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
Extract, Transform, Load: Generic Translators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Mapping of XML to native Python data.
"""
import datetime
import sys

from lxml import etree


def _debug(*args):
    sys.stderr.write(' '.join(str(x) for x in args) + '\n')


def _reject_to_serialize_deep_struct_as_attr(value):
    raise ValueError('Deep structures must be serialized '
                     'as tags, not attributes: {}'.format(value))


# from Python to XML
ATTR_VALUE_SERIALIZERS_BY_TYPE = {
    str: str,
    int: str,
    bool: lambda x: str(int(x)),
    datetime.datetime: lambda x: str(int(x.timestamp())),
    dict: _reject_to_serialize_deep_struct_as_attr,
    list: _reject_to_serialize_deep_struct_as_attr,
}

# from XML to Python
# (requires explicit type declaration)
ATTR_VALUE_NORMALIZERS_BY_TYPE = {
    None: str,  # default
    str: str,
    int: int,
    bool: lambda x: bool(int(x)),
    datetime.datetime: lambda x: datetime.datetime.fromtimestamp(int(x)),
    dict: _reject_to_serialize_deep_struct_as_attr,
    list: _reject_to_serialize_deep_struct_as_attr,
}


def serialize_attr_value(value):
    """
    Converts given value from a Python type to string for XML.
    """
    if value is None:
        return ''

    value_type = type(value)
    serializer = ATTR_VALUE_SERIALIZERS_BY_TYPE.get(value_type)

    if serializer:
        return serializer(value)
    else:
        raise ValueError('Serializer not found for {} attribute "{}"'
                         .format(type(value).__name__, value))


def normalize_attr_value(value, target_type=None):
    """
    Converts given value from XML (string) to a Python type.
    """
    if value is None:
        return ''

    normalizer = ATTR_VALUE_NORMALIZERS_BY_TYPE.get(target_type)

    if normalizer:
        return normalizer(value)
    else:
        raise ValueError('Normalizer not found for {} attribute "{}" ({})'
                         .format(type(value).__name__, value, target_type))


class AbstractTagCardinality:
    SINGLE_VALUE = False

    def __init__(self, translator_class):
        if isinstance(translator_class, dict):
            translator_class = tag_translator_factory(**translator_class)

        self.translator_class = translator_class

    def __call__(self, *args, **kwargs):
        return self.translator_class(*args, **kwargs)

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__,
                                self.translator_class.__name__)

    def validate_values(self, values):
        try:
            self._validate_values(values)
        except ValueError as e:
            msg = 'Expected {} for {.__name__}, got {}'.format(
                e, self.translator_class, len(values))
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


class TagTranslatorContributor:
    TAG_NAMES = ()


def tag_translator_factory(tags=None, attrs=None, contributors=None,
                           as_text=False):

    class AdHocTagTranslator(TagTranslator):
        TAGS = tags or {}
        ATTRS = attrs or ()
        AS_TEXT = as_text
        CONTRIBUTORS = contributors or ()

    return AdHocTagTranslator


# TODO: rename to TagTranslator?
class TagTranslator:
    TAGS = {}
    ATTRS = ()
    AS_TEXT = False
    TEXT_UNDER_KEY = None
    CONTRIBUTORS = ()

    def __init__(self):
        if self.TAGS and self.AS_TEXT:
            # This is not necessarily so, but very unlikely, especially given
            # the GrampsXML DTD.
            raise ValueError('TAGS and AS_TEXT are mutually exclusive.')

    @property
    def expected_tags(self):
        return list(self.TAGS.keys()) + [c.TAG_NAMES for c in self.CONTRIBUTORS]

    def from_xml(self, el, handle_to_id=None):
        data = {}
        attrs = {}

        for attr in el.attrib:
            if attr not in self.ATTRS:
                _debug('{}: unexpected attr {}'.format(el.tag, attr))

                continue

            target_type = None
            if isinstance(self.ATTRS, dict):
                target_type = self.ATTRS[attr]

            value = el.get(attr)
            attrs[attr] = normalize_attr_value(value, target_type)

        try:
            attrs = self.post_normalize_attrs(attrs, handle_to_id)
        except Exception as e:
            print('{}: failed to normalize extra attrs'.format(el.tag))
            raise e

        data.update(attrs)

        if self.AS_TEXT:
            return el.text

        if self.TEXT_UNDER_KEY:
            data[self.TEXT_UNDER_KEY] = el.text

        for nested_el in el:
            # Use the local name instead of the qualified one,
            # i.e. "{http://gramps-project.org/xml/1.7.1/}name" → "name"
            nested_tag = etree.QName(nested_el.tag).localname

            if nested_tag not in self.expected_tags:
                _debug('{}: unexpected nested tag {}'.format(el.tag, nested_tag))

                continue

            Translator = self.TAGS[nested_tag]
            translator = Translator()

            is_list = True
            if isinstance(Translator, AbstractTagCardinality):
                if Translator.SINGLE_VALUE:
                    is_list = False

            #key = translator.KEY or nested_tag
            key = nested_tag
            value = translator.from_xml(nested_el, handle_to_id=handle_to_id)

            if is_list:
                data.setdefault(key, []).append(value)
            else:
               data[key] = value

        # let custom classes contribute to our data
        for Contributor in self.CONTRIBUTORS:
            contributed_data = Contributor.from_xml(el)
            data.update(contributed_data)

        return data

    def to_xml(self, tag, data, id_to_handle):
        el = etree.Element(tag)

        attrs = self.pre_serialize_attrs(data, id_to_handle)

        for attr in sorted(attrs):
            value = attrs[attr]

            if value is not None:
                el.set(attr, serialize_attr_value(value))

        for nested_tag, Translator in self.TAGS.items():

            # NOTE: subtag == key, but may be different
            values = data.get(nested_tag)

            if values is None:
                values = []
            elif not isinstance(values, list):
                values = [values]

            if isinstance(Translator, AbstractTagCardinality):
                Translator.validate_values(values)

            for value in values:
                translator = Translator()
                nested_el = translator.to_xml(nested_tag, value, id_to_handle)
                el.append(nested_el)

        try:
            if self.AS_TEXT:
                text_value = self._make_text_value(data)
            elif self.TEXT_UNDER_KEY:
                text_value = self._make_text_value(data.get(self.TEXT_UNDER_KEY))
            else:
                text_value = None
        except Exception as e:
            raise type(e)('{}: {}'.format(tag, e))

        # let custom classes contribute to our element
        for Contributor in self.CONTRIBUTORS:
            contributed_elems = Contributor.to_xml(data)
            for contributed_el in contributed_elems:
                if contributed_el is not None:
                    el.append(contributed_el)

        if text_value:
            el.text = text_value

        return el

    def post_normalize_attrs(self, attrs, handle_to_id):
        """
        Post-processes normalized tag attributes.

        :param attrs: Attributes extracted so far (using self.ATTRS).
        """
        return attrs

    def pre_serialize_attrs(self, data, id_to_handle):
        """
        Pre-processes attributes for the serialized tag.  Returns the
        attributes dictionary.  Can be used to add and remove attributes.

        :param data: The source data dictionary.
        """
        attrs = {}

        for attr in self.ATTRS:
            attrs[attr] = data.get(attr)

        return attrs

    def _make_text_value(self, value):
        if not isinstance(value, str):
            raise ValueError('expected string, got {}: {!r}'
                             .format(type(value), value))
        return value


class TextTagTranslator(TagTranslator):
    """
    Generates a ``<foo>some text</foo>`` element.
    """
    AS_TEXT = True

    def from_xml(self, el, handle_to_id=None):
        return el.text


class EnumTagTranslator(TextTagTranslator):
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


class GreedyDictTagTranslator(TagTranslator):
    """
    Generates ``<foo a="1" b="2" />`` elements, mapping *all* keys from a list
    of dicts to element attributes.
    """
    def to_xml(self, tag, data, id_to_handle):
        if not isinstance(data, dict):
            raise ValueError('Expected dict, got "{}"'.format(data))

        value = dict((k, serialize_attr_value(v))
                     for k, v in data.items())

        return etree.Element(tag, value)
