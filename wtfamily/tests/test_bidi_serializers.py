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

# NOTE: *not* the built-in library because it lacks pretty_print
from lxml import etree
import re

import etl.serializers as s


def as_xml(el):
    return etree.tostring(el, encoding='unicode', pretty_print=True)


def trim(value):
    lines = value.strip('\n').split('\n')
    first_xml_line = [x for x in lines if x][0]

    base_indent = ''

    m = re.match('^\s+', first_xml_line)
    if m:
        base_indent = m.group()

    regex = re.compile('^{}'.format(base_indent))
    unindented_lines = (regex.sub('', x) for x in lines if x)
    return '\n'.join(unindented_lines).strip() + '\n'


def test_basic_text():
    class CafeSerializer(s.TagSerializer):
        ATTRS = {
            'place': str
        }
        TAGS = {
            'visitor': s.MaybeOne(s.TextTagSerializer),
            'dish': s.OneOrMore(s.TextTagSerializer),
        }

    data = {
        'place': 'Bromley',
        'visitor': 'Viking',
        'dish': ['spam', 'bacon', 'sausage', 'spam']
    }
    xml = trim('''
    <green-midget-cafe place="Bromley">
      <visitor>Viking</visitor>
      <dish>spam</dish>
      <dish>bacon</dish>
      <dish>sausage</dish>
      <dish>spam</dish>
    </green-midget-cafe>
    ''')

    serializer = CafeSerializer()

    # data → XML
    serialized_xml = as_xml(serializer.to_xml('green-midget-cafe', data, {}))
    assert serialized_xml == xml

    # XML → data
    deserialized_from_xml = serializer.from_xml(etree.fromstring(xml))
    assert deserialized_from_xml == data


def test_nested_text_under_key():
    class PlaceSerializer(s.TagSerializer):
        ATTRS = {
            'name': str
        }

    class DishSerializer(s.TagSerializer):
        ATTRS = {
            'base': str
        }
        TEXT_UNDER_KEY = 'text'

    class CafeSerializer(s.TagSerializer):
        TAGS = {
            'place': s.One(PlaceSerializer),
            'dish': s.OneOrMore(DishSerializer),
        }

    data = {
        'place': {
            'name': 'Bromley'
        },
        'dish': [
            {
                'base': 'bacon',
                'text': 'spam',
            },
            {
                'base': 'egg',
                'text': 'glorious spam!',
            }
        ]
    }
    xml = trim('''
    <green-midget-cafe>
      <place name="Bromley"/>
      <dish base="bacon">spam</dish>
      <dish base="egg">glorious spam!</dish>
    </green-midget-cafe>
    ''')

    serializer = CafeSerializer()

    # data → XML
    serialized_xml = as_xml(serializer.to_xml('green-midget-cafe', data, {}))
    assert serialized_xml == xml

    # XML → data
    deserialized_from_xml = serializer.from_xml(etree.fromstring(xml))
    assert deserialized_from_xml == data


def test_list_of_strings():
    class CafeSerializer(s.TagSerializer):
        TAGS = {
            'visitor': s.OneOrMore(s.TextTagSerializer)
        }

    data = {
        'visitor': [
            'Viking One',
            'Viking Two',
            'Mrs Bun',
            'Her Husband'
        ],
    }
    xml = trim('''
    <green-midget-cafe>
      <visitor>Viking One</visitor>
      <visitor>Viking Two</visitor>
      <visitor>Mrs Bun</visitor>
      <visitor>Her Husband</visitor>
    </green-midget-cafe>
    ''')

    serializer = CafeSerializer()

    # data → XML
    serialized_xml = as_xml(serializer.to_xml('green-midget-cafe', data, {}))
    assert serialized_xml == xml

    # XML → data
    deserialized_from_xml = serializer.from_xml(etree.fromstring(xml))
    assert deserialized_from_xml == data


class TestMappingMultipleTagsToOneKey:
    """
    GrampsXML keeps the date in one of a few tags; WTFamily uses a single key
    to keep the same information.
    """

    tag = 'my-tag'
    serializer = s.tag_serializer_factory(
        tags={
            # TODO: MaybeOne(EitherOf(...))
            #'daterange': s.MaybeOne(s.DateRangeTagSerializer),
            #'datespan': s.MaybeOne(s.DateSpanTagSerializer),
            #'dateval': s.MaybeOne(s.DateValTagSerializer),
            #'datestr': s.MaybeOne(s.DateStrTagSerializer),
        },
        contributors=(
            s.DateContributor,
        ))

    def _wrap_xml(self, xml_string):
        tmpl = trim('''
        <{tag}>
          {body}
        </{tag}>
        ''')
        return tmpl.format(tag=self.tag, body=xml_string.strip())

    def _to_xml(self, data):
        return as_xml(self.serializer().to_xml(self.tag, data, {}))

    def _from_xml(self, xml_string):
        return self.serializer().from_xml(etree.fromstring(xml_string), {})

    def test_datestr(self):
        xml = self._wrap_xml('<datestr val="в детстве"/>')
        data = {
            'date': {
                'value': 'в детстве',
                'modifier': 'textonly',
            }
        }

        # XML → data
        assert self._from_xml(xml) == data

        # data → XML
        assert self._to_xml(data) == xml

    def test_dateval(self):
        xml = self._wrap_xml('<dateval quality="calculated" type="about" val="1855"/>')
        data = {
            'date': {
                'value': '1855',
                'modifier': 'about',
                'quality': 'calculated',
            }
        }

        # data → XML
        assert self._to_xml(data) == xml

        # XML → data
        assert self._from_xml(xml) == data

    def test_daterange(self):
        xml = self._wrap_xml('<daterange quality="estimated" start="1790" stop="1810"/>')
        data = {
            'date': {
                'start': '1790',
                'stop': '1810',
                'quality': 'estimated',
                'modifier': 'range',
            }
        }

        # data → XML
        assert self._to_xml(data) == xml

        # XML → data
        assert self._from_xml(xml) == data

    def test_datespan(self):
        xml = self._wrap_xml('<datespan start="1864-07-13" stop="1864-08-07"/>')
        data = {
            'date': {
                'start': '1864-07-13',
                'stop': '1864-08-07',
                'modifier': 'span',
            }
        }

        # data → XML
        assert self._to_xml(data) == xml

        # XML → data
        assert self._from_xml(xml) == data
