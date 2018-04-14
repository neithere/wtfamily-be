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
import datetime
# NOTE: *not* the built-in library because it lacks pretty_print
from lxml import etree
import pytest
import re

import mongo_to_gramps_xml


def as_xml(el):
    return etree.tostring(el, encoding='unicode', pretty_print=True)


def trim(value):
    #return value.replace('\n', '').replace('  ', '').strip)
    lines = value.strip().split('\n')
    unindented_lines = (re.sub('^    ', '', x) for x in lines)
    return '\n'.join(unindented_lines) + '\n'


def test_nested_attributes():
    class MyTagSerializer(mongo_to_gramps_xml.BaseTagSerializer):
        ATTRS = 'foo',

    data = {
        'foo': {
            'hello': 123
        }
    }

    with pytest.raises(ValueError) as excinfo:
        MyTagSerializer('mytag', data, {}).make_xml()

    err_msg = 'Deep structures must be serialized as tags, not attributes'
    assert err_msg in str(excinfo.value)


def test_list_attributes():
    class MyTagSerializer(mongo_to_gramps_xml.BaseTagSerializer):
        ATTRS = 'foo',

    data = {
        'foo': ['hello']
    }

    with pytest.raises(ValueError) as excinfo:
        MyTagSerializer('mytag', data, {}).make_xml()

    err_msg = 'Deep structures must be serialized as tags, not attributes'
    assert err_msg in str(excinfo.value)


def test_base_tag_serializer_composition():
    class MyTagSerializer(mongo_to_gramps_xml.BaseTagSerializer):
        ATTRS = 'greeting', 'name'
        TAGS = {
            'foo': mongo_to_gramps_xml.TextTagSerializer,
            'bar': mongo_to_gramps_xml.GreedyDictTagSerializer,
        }

    data = {
        'greeting': 'Hello',
        'name': 'Patsy',
        'foo': ['Albatross!', 'Holy Grail'],
        'bar': {
            'one': 1,
            'two': 2,
        },
    }
    expected = trim('''
    <mytag greeting="Hello" name="Patsy">
      <foo>Albatross!</foo>
      <foo>Holy Grail</foo>
      <bar one="1" two="2"/>
    </mytag>
    ''')

    el = MyTagSerializer('mytag', data, {}).make_xml()

    assert expected == as_xml(el)


def test_greedy_dict():
    data = {
        'foo': 'hello',
        'bar': 123,
        'quux': True,
        'quuz': False,
        'quix': None
    }
    expected = '<mytag bar="123" foo="hello" quix="" quux="1" quuz="0"/>\n'

    el = mongo_to_gramps_xml.GreedyDictTagSerializer('mytag', data, {}).make_xml()

    assert expected == as_xml(el)


def test_person_name():
    data = {
        "type": "Birth Name",
        "first": "Иван",
        "surname": [
            # patronymic
            {
                "prim": True,
                "derivation": "Patronymic",
                "text": "Петрович"
            },
            # last name
            {
                "text": "Сидоров"
            }
        ]
    }

    expected = trim('''
    <name type="Birth Name">
      <first>Иван</first>
      <surname prim="1" derivation="Patronymic">Петрович</surname>
      <surname>Сидоров</surname>
    </name>
    ''')

    el = mongo_to_gramps_xml.PersonNameTagSerializer('name', data, {}).make_xml()

    assert expected == as_xml(el)
