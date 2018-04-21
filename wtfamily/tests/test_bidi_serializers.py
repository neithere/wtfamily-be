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

import mongo_to_gramps_xml as m


def as_xml(el):
    return etree.tostring(el, encoding='unicode', pretty_print=True)


def trim(value):
    lines = value.strip().split('\n')
    unindented_lines = (re.sub('^    ', '', x) for x in lines)
    return '\n'.join(unindented_lines) + '\n'


def test_basic_text():
    class CafeSerializer(m.TagSerializer):
        ATTRS = 'place',
        TAGS = {
            'visitor': m.MaybeOne(m.TextTagSerializer),
            'dish': m.OneOrMore(m.TextTagSerializer),
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
    class PlaceSerializer(m.TagSerializer):
        ATTRS = 'name',

    class DishSerializer(m.TagSerializer):
        ATTRS = 'base',
        TEXT_UNDER_KEY = 'text'

    class CafeSerializer(m.TagSerializer):
        TAGS = {
            'place': m.One(PlaceSerializer),
            'dish': m.OneOrMore(DishSerializer),
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
    class CafeSerializer(m.TagSerializer):
        TAGS = {
            'visitor': m.OneOrMore(m.TextTagSerializer)
        }

    data = {
        'visitors': [
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
