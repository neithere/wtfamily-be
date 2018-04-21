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

import etl.serializers as m


def as_xml(el):
    return etree.tostring(el, encoding='unicode', pretty_print=True)


def trim(value):
    #return value.replace('\n', '').replace('  ', '').strip)
    lines = value.strip().split('\n')
    unindented_lines = (re.sub('^    ', '', x) for x in lines)
    return '\n'.join(unindented_lines) + '\n'


def test_nested_attributes():
    class MyTagSerializer(m.TagSerializer):
        ATTRS = 'foo',

    data = {
        'foo': {
            'hello': 123
        }
    }

    with pytest.raises(ValueError) as excinfo:
        MyTagSerializer().to_xml('mytag', data, {})

    err_msg = 'Deep structures must be serialized as tags, not attributes'
    assert err_msg in str(excinfo.value)


def test_list_attributes():
    class MyTagSerializer(m.TagSerializer):
        ATTRS = 'foo',

    data = {
        'foo': ['hello']
    }

    with pytest.raises(ValueError) as excinfo:
        MyTagSerializer().to_xml('mytag', data, {})

    err_msg = 'Deep structures must be serialized as tags, not attributes'
    assert err_msg in str(excinfo.value)


def test_base_tag_serializer_composition():
    class MyTagSerializer(m.TagSerializer):
        ATTRS = 'greeting', 'name'
        TAGS = {
            'foo': m.TextTagSerializer,
            'bar': m.GreedyDictTagSerializer,
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

    el = MyTagSerializer().to_xml('mytag', data, {})

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

    el = m.GreedyDictTagSerializer().to_xml('mytag', data, {})

    assert expected == as_xml(el)


def test_quantifier_validator_one():
    def serialize(data):
        m.tag_serializer_factory(tags={
            'foo': m.One(m.TextTagSerializer),
        })().to_xml('mytag', data, {})

    # no values
    with pytest.raises(ValueError) as excinfo:
        serialize({})
    assert 'Expected one value for TextTagSerializer, got 0' in str(excinfo)

    # one value
    serialize({'foo': 'bar'})

    # one value (just wrapped in a list)
    serialize({'foo': ['bar']})

    # more than one value
    with pytest.raises(ValueError) as excinfo:
        serialize({'foo': ['bar', 'quux']})
    assert 'Expected one value for TextTagSerializer, got 2' in str(excinfo)


def test_quantifier_validator_maybe_one():
    def serialize(data):
        m.tag_serializer_factory(tags={
            'foo': m.MaybeOne(m.TextTagSerializer),
        })().to_xml('mytag', data, {})

    # no values
    serialize({})

    # one value
    serialize({'foo': 'bar'})

    # one value (just wrapped in a list)
    serialize({'foo': ['bar']})

    # more than one value
    with pytest.raises(ValueError) as excinfo:
        serialize({'foo': ['bar', 'quux']})
    assert 'Expected 0..1 values for TextTagSerializer, got 2' in str(excinfo)


def test_quantifier_validator_one_or_more():
    def serialize(data):
        m.tag_serializer_factory(tags={
            'foo': m.OneOrMore(m.TextTagSerializer),
        })().to_xml('mytag', data, {})

    # no values
    with pytest.raises(ValueError) as excinfo:
        serialize({})
    assert 'Expected 1..n values for TextTagSerializer, got 0' in str(excinfo)

    # one value
    serialize({'foo': 'bar'})

    # one value (just wrapped in a list)
    serialize({'foo': ['bar']})

    # more than one value
    serialize({'foo': ['bar', 'quux']})


def test_quantifier_validator_maybe_many():
    def serialize(data):
        m.tag_serializer_factory(tags={
            'foo': m.MaybeMany(m.TextTagSerializer),
        })().to_xml('mytag', data, {})

    # no values
    serialize({})

    # one value
    serialize({'foo': 'bar'})

    # one value (just wrapped in a list)
    serialize({'foo': ['bar']})

    # more than one value
    serialize({'foo': ['bar', 'quux']})


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

    el = m.PersonNameTagSerializer().to_xml('name', data, {})

    assert expected == as_xml(el)


def test_entity_person():
    data = {
        '_id': '5ad2227f87b0bd4a75c53730',
	'handle': '_cdeb90490341f84abadc55e8d91',
	'change': datetime.datetime(2016, 12, 22, 20, 19, 17),
	'id': 'auz_dawid_16xx',
	'gender': 'M',
	'name' : [
            {
                'type': 'Birth Name',
                'first': 'Давид',
                'surname': [
                    {
                        'prim': True,
                        'derivation': 'Patronymic',
                        'text': 'Янович'
                    },
                    {
                        'derivation': 'Inherited',
                        'text': 'Авжбикович'
                    }
                ],
                'citationref': [
                    { 'id': 'C0053' }
                ]
            },
            {
                'alt': True,
                'type': 'Also Known As',
                'first': 'Dovydas',
                'surname': [
                    { 'text': 'Aušbikavičius' }
                ],
                'citationref': [
                    { 'id': 'C0029' }
                ]
            },
            {
                'alt': True,
                'type': 'Birth Name',
                'first': 'Давид',
                'surname': [
                    { 'text': 'Аужбикович' }
                ],
                'citationref': [
                    { 'id': 'C0039' }
                ]
            },
            {
                'alt': True,
                'type': 'Birth Name',
                'first': 'Dawid',
                'surname': [
                    { 'text': 'Auzbikowicz' }
                ],
                'citationref': [
                    { 'id': 'metryka-p127' }
                ]
            }
	],
	'eventref': [
            { 'role': 'Primary', 'id': 'E0330' },
            { 'role': 'Primary', 'id': 'E0318' },
            { 'role': 'Primary', 'id': 'E1202' },
            { 'role': 'Primary', 'id': 'E1203' },
	],
	'childof': [
            { 'id': 'F0091' },
            { 'id': 'F0091a' }
	],
	'parentin': [
            { 'id': 'F0092' },
            { 'id': 'F0092a' }
	],
	'objref': [
            {
                'id': 'something_scanned',
                'region': [
                    {
                        'corner1_x': '48',
                        'corner1_y': '22',
                        'corner2_x': '68',
                        'corner2_y': '54'
                    }
                ],
            },
        ],
        'address': [
            {
                'dateval': [
                    { 'val': '1690' }
                ],

                # XXX wait what... shouldn't those be single-value fields..?
                # check DTD. it's about import though, not export.
                'city': [ 'Аужбики' ],
                'state': [ 'Поюрский повет' ],
                'country': [ 'Самогитское княжество' ],

                'citationref': [
                    { 'id': 'metryka-p127' }
                ]
            },
        ]
    }
    ids_in_fixture = (
        'auz_dawid_16xx', 'E0330', 'E0318', 'E1202', 'E1203', 'C0053', 'C0029',
        'C0039', 'F0091', 'F0091a', 'F0092', 'F0092a', 'something_scanned',
        'metryka-p127'
    )
    id_to_handle = dict((k, 'handle-' + k) for k in ids_in_fixture)

    expected = trim('''
    <my-person id="auz_dawid_16xx" handle="_cdeb90490341f84abadc55e8d91" change="1482434357">
      <gender>M</gender>
      <name type="Birth Name">
        <first>Давид</first>
        <surname prim="1" derivation="Patronymic">Янович</surname>
        <surname derivation="Inherited">Авжбикович</surname>
        <citationref hlink="handle-C0053"/>
      </name>
      <name alt="1" type="Also Known As">
        <first>Dovydas</first>
        <surname>Aušbikavičius</surname>
        <citationref hlink="handle-C0029"/>
      </name>
      <name alt="1" type="Birth Name">
        <first>Давид</first>
        <surname>Аужбикович</surname>
        <citationref hlink="handle-C0039"/>
      </name>
      <name alt="1" type="Birth Name">
        <first>Dawid</first>
        <surname>Auzbikowicz</surname>
        <citationref hlink="handle-metryka-p127"/>
      </name>
      <eventref role="Primary" hlink="handle-E0330"/>
      <eventref role="Primary" hlink="handle-E0318"/>
      <eventref role="Primary" hlink="handle-E1202"/>
      <eventref role="Primary" hlink="handle-E1203"/>
      <objref hlink="handle-something_scanned">
        <region corner1_x="48" corner1_y="22" corner2_x="68" corner2_y="54"/>
      </objref>
      <address>
        <dateval val="1690"/>
        <city>Аужбики</city>
        <state>Поюрский повет</state>
        <country>Самогитское княжество</country>
        <citationref hlink="handle-metryka-p127"/>
      </address>
      <childof hlink="handle-F0091"/>
      <childof hlink="handle-F0091a"/>
      <parentin hlink="handle-F0092"/>
      <parentin hlink="handle-F0092a"/>
    </my-person>
    ''')

    el = m.PersonSerializer().to_xml('my-person', data, id_to_handle)
    serialized = as_xml(el)

    assert expected == serialized
