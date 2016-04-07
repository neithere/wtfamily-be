#    WTFamily is a genealogical software.
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
import pytest
from xml.etree import ElementTree

import gramps_xml_to_yaml


FIXTURE_EMPTY_STRING = ''
FIXTURE_EMPTY_TREE = '<xml></xml>'
FIXTURE_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE database PUBLIC "-//Gramps//DTD Gramps XML 1.7.1//EN"
"http://gramps-project.org/xml/1.7.1/grampsxml.dtd">
<database xmlns="http://gramps-project.org/xml/1.7.1/">
  <header>
    <created date="2016-03-27" version="4.2.2"/>
    <mediapath>/tmp/gramps_media</mediapath>
  </header>
  {}
</database>
'''


def test_empty_file():
    with pytest.raises(ElementTree.ParseError):
        ElementTree.fromstring(FIXTURE_EMPTY_STRING)


def test_empty_tree():
    xml_root = ElementTree.fromstring(FIXTURE_EMPTY_TREE)
    results = gramps_xml_to_yaml.transform(xml_root)
    results = list(results)
    expected = []
    assert expected == results


def test_note():
    fixture = FIXTURE_TEMPLATE.format('''
      <notes>
        <note handle="_cddae8db682509900d8c4a0717b" change="1414625582" id="N0000" type="Source text">
          <text>P. Salomon Jakubowicz z Aużbików dym\nP. Augustyn Auzbikowicz z tejże dym</text>
        </note>
        <note handle="_ce686c5c01a728667eb09a861b0" change="1418424311" id="N0075" type="Citation">
          <text>Учительница Валентина Ксаверьевна Аузбиковичъ</text>
          <style name="bold">
            <range start="0" end="10"/>
            <range start="175" end="208"/>
          </style>
        </note>
      </notes>
    ''')
    xml_root = ElementTree.fromstring(fixture)
    results = gramps_xml_to_yaml.transform(xml_root)
    results = list(results)
    expected = [
        (
            'notes',
            'N0000',
            {
                'id': 'N0000',
                'handle': '_cddae8db682509900d8c4a0717b',
                'text': 'P. Salomon Jakubowicz z Aużbików dym\n'
                        'P. Augustyn Auzbikowicz z tejże dym',
                'type': 'Source text',
                'change': datetime.datetime(2014, 10, 29, 23, 33, 2),
            },
        ),
        (
            'notes',
            'N0075',
            {
                'change': datetime.datetime(2014, 12, 12, 22, 45, 11),
            'handle': '_ce686c5c01a728667eb09a861b0',
            'id': 'N0075',
            'style': [
                {
                    'name': 'bold',
                    'range': [
                        {'end': '10', 'start': '0'},
                        {'end': '208', 'start': '175'}
                    ]
                }
            ],
            'text': 'Учительница Валентина Ксаверьевна Аузбиковичъ',
            'type': 'Citation',
            }
        ),
    ]
    assert expected == results


def test_event_simple():
    fixture = FIXTURE_TEMPLATE.format('''
      <events>
        <event handle="_ce256047ba8422bdb7afcf17f0c" change="1447556305" id="E0284">
          <type>Education</type>
          <datespan start="1882-08-19" stop="1886-06-15"/>
          <description>Витебская женская гимназия</description>
        </event>
      </events>
    ''')
    xml_root = ElementTree.fromstring(fixture)
    results = gramps_xml_to_yaml.transform(xml_root)
    results = list(results)
    expected = [
        (
            'events',
            'E0284',
            {
                'id': 'E0284',
                'handle': '_ce256047ba8422bdb7afcf17f0c',
                'type': 'Education',
                'date': {
                    'modifier': 'span',
                    'value': {'start': '1882-08-19', 'stop': '1886-06-15'},
                },
                'description': 'Витебская женская гимназия',
                'change': datetime.datetime(2015, 11, 15, 2, 58, 25),
            },
         )
    ]
    assert expected == results


def test_event_with_refs():
    """
    References are resolved.  Hlinks (internal IDs specific to Gramps)
    are converted to permanent IDs.
    """
    fixture = FIXTURE_TEMPLATE.format('''
      <places>
        <placeobj handle="_ce255ff558060243e85c7afafdd" change="1416946456" id="P0094" type="City">
          <ptitle>Витебск</ptitle>
          <pname value="Витебск"/>
          <coord long="30.166667" lat="55.183333"/>
        </placeobj>
      </places>
      <events>
        <event handle="_ce256047ba8422bdb7afcf17f0c" change="1447556305" id="E0284">
          <type>Education</type>
          <datespan start="1882-08-19" stop="1886-06-15"/>
          <place hlink="_ce255ff558060243e85c7afafdd"/>
          <description>Витебская женская гимназия</description>
          <citationref hlink="_ce686c6f00d129987dfd2557a69"/>
          <citationref hlink="_d2a5a5f906a63c6daa03719fa9e"/>
        </event>
      </events>
      <citations>
        <citation handle="_ce686c6f00d129987dfd2557a69" change="1418424441" id="C0084">
          <dateval val="1888"/>
          <page>На 1888 год, с.98</page>
          <confidence>2</confidence>
        </citation>
        <citation handle="_d2a5a5f906a63c6daa03719fa9e" change="1447556536" id="C0239">
          <dateval val="1888"/>
          <page>(n/a)</page>
          <confidence>2</confidence>
        </citation>
      </citations>
    ''')
    xml_root = ElementTree.fromstring(fixture)
    results = gramps_xml_to_yaml.transform(xml_root)
    results = list(results)
    expected = [
        (
            'events',
            'E0284',
            {
                'id': 'E0284',
                'handle': '_ce256047ba8422bdb7afcf17f0c',
                'type': 'Education',
                'date': {
                    'modifier': 'span',
                    'value': {'start': '1882-08-19', 'stop': '1886-06-15'},
                },
                'description': 'Витебская женская гимназия',
                'change': datetime.datetime(2015, 11, 15, 2, 58, 25),
                'place': [
                    {'id': 'P0094'},
                ],
                'citationref': [
                    {'id': 'C0084'},
                    {'id': 'C0239'},
                ],
            },
        ),
        (
            'places',
            'P0094',
            {
                'change': datetime.datetime(2014, 11, 25, 20, 14, 16),
                'coord': {'lat': '55.183333', 'long': '30.166667'},
                'handle': '_ce255ff558060243e85c7afafdd',
                'id': 'P0094',
                'pname': [{'value': 'Витебск'}],
                'ptitle': 'Витебск',
                'type': 'City'
            }
        ),
        (
            'citations',
            'C0084',
            {
                'change': datetime.datetime(2014, 12, 12, 22, 47, 21),
                'confidence': '2',
                'date': {'value': '1888'},
                'handle': '_ce686c6f00d129987dfd2557a69',
                'id': 'C0084',
                'page': 'На 1888 год, с.98'
            }
        ),
        (
            'citations',
            'C0239',
            {
                'change': datetime.datetime(2015, 11, 15, 3, 2, 16),
                'confidence': '2',
                'date': {'value': '1888'},
                'handle': '_d2a5a5f906a63c6daa03719fa9e',
                'id': 'C0239',
                'page': '(n/a)'
            }
        ),
    ]
    assert expected == results


def test_event_with_more_refs():
    """
    References are resolved.  Hlinks (internal IDs specific to Gramps)
    are converted to permanent IDs.
    """
    fixture = FIXTURE_TEMPLATE.format('''
      <sources>
        <source handle="_ce6851e9dc2741cfb6fe03a119a" change="1434907653" id="membook_vitebsk">
          <stitle>Памятная книжка Витебской губернии</stitle>
          <sabbrev>ПК Витеб. губ.</sabbrev>
        </source>
      </sources>
      <places>
        <placeobj handle="_ce255ff558060243e85c7afafdd" change="1416946456" id="P0094" type="City">
          <ptitle>Витебск</ptitle>
          <pname value="Витебск"/>
          <coord long="30.166667" lat="55.183333"/>
        </placeobj>
      </places>
      <events>
        <event handle="_ce256047ba8422bdb7afcf17f0c" change="1447556305" id="E0284">
          <type>Education</type>
          <datespan start="1882-08-19" stop="1886-06-15"/>
          <place hlink="_ce255ff558060243e85c7afafdd"/>
          <description>Витебская женская гимназия</description>
          <citationref hlink="_ce686c6f00d129987dfd2557a69"/>
        </event>
      </events>
      <citations>
        <citation handle="_ce686c6f00d129987dfd2557a69" change="1418424441" id="C0084">
          <dateval val="1888"/>
          <page>На 1888 год, с.98</page>
          <confidence>2</confidence>
          <noteref hlink="_ce686c5c01a728667eb09a861b0"/>
          <objref hlink="_ce686b5cd8173717f5a3b935e61">
           <region corner1_x="4" corner1_y="23" corner2_x="100" corner2_y="36"/>
          </objref>
          <sourceref hlink="_ce6851e9dc2741cfb6fe03a119a"/>
        </citation>
      </citations>
      <objects>
        <object handle="_ce686b5cd8173717f5a3b935e61" change="1425242618" id="O0052">
          <file src="pamjatnaja-knizhka/vitebskaja/1888/p98.png" mime="image/png" checksum="48e78c814eb61ac1eef97b4bfdf69fb5" description="p98"/>
        </object>
      </objects>
      <notes>
        <note handle="_ce686c5c01a728667eb09a861b0" change="1418424311" id="N0075" type="Citation">
          <text>Учительница Валентина Ксаверьевна Аузбиковичъ</text>
        </note>
      </notes>

    ''')
    xml_root = ElementTree.fromstring(fixture)
    results = gramps_xml_to_yaml.transform(xml_root)
    results = list(results)
    expected = [
        (
            'sources',
            'membook_vitebsk',
            {
                'id': 'membook_vitebsk',
                'handle': '_ce6851e9dc2741cfb6fe03a119a',
                'stitle': 'Памятная книжка Витебской губернии',
                'sabbrev': 'ПК Витеб. губ.',
                'change': datetime.datetime(2015, 6, 21, 17, 27, 33),
            }
        ),
        (
            'events',
            'E0284',
            {
                'id': 'E0284',
                'handle': '_ce256047ba8422bdb7afcf17f0c',
                'type': 'Education',
                'date': {
                    'modifier': 'span',
                    'value': {
                        'start': '1882-08-19',
                        'stop': '1886-06-15',
                    },
                },
                'description': 'Витебская женская гимназия',
                'change': datetime.datetime(2015, 11, 15, 2, 58, 25),
                'place': [
                    {
                        'id': 'P0094',
                    },
                ],
                'citationref': [
                    {
                        'id': 'C0084',
                    },
                ],
            },
        ),
        (
            'places',
            'P0094',
            {
                'id': 'P0094',
                'handle': '_ce255ff558060243e85c7afafdd',
                'ptitle': 'Витебск',
                'type': 'City',
                'pname': [
                    {
                        'value': 'Витебск',
                    },
                ],
                'coord': {'lat': '55.183333', 'long': '30.166667'},
                'change': datetime.datetime(2014, 11, 25, 20, 14, 16),
            }
        ),
        (
            'objects',
            'O0052',
            {
                'id': 'O0052',
                'handle': '_ce686b5cd8173717f5a3b935e61',
                'file': {
                    'checksum': '48e78c814eb61ac1eef97b4bfdf69fb5',
                    'description': 'p98',
                    'mime': 'image/png',
                    'src': 'pamjatnaja-knizhka/vitebskaja/1888/p98.png'
                },
                'change': datetime.datetime(2015, 3, 1, 20, 43, 38),
            },
        ),
        (
            'notes',
            'N0075',
            {
                'id': 'N0075',
                'handle': '_ce686c5c01a728667eb09a861b0',
                'text': 'Учительница Валентина Ксаверьевна Аузбиковичъ',
                'type': 'Citation',
                'change': datetime.datetime(2014, 12, 12, 22, 45, 11),
            },
        ),
        (
            'citations',
            'C0084',
            {
                'id': 'C0084',
                'handle': '_ce686c6f00d129987dfd2557a69',
                'confidence': '2',
                'date': {
                    'value': '1888'
                },
                'page': 'На 1888 год, с.98',
                'sourceref': {
                    'id': 'membook_vitebsk'
                },
                'noteref': [
                    {
                        'id': 'N0075'
                    },
                ],
                'objref': [
                    {
                        'id': 'O0052',
                        'region': [
                            {
                                'corner1_x': '4',
                                'corner1_y': '23',
                                'corner2_x': '100',
                                'corner2_y': '36'
                            }
                        ]
                    }
                ],
                'change': datetime.datetime(2014, 12, 12, 22, 47, 21),
            }
        ),
    ]
    print('expected', expected)
    print('actual', results)
    assert expected == results

def test_person():
    fixture = FIXTURE_TEMPLATE.format('''
    <people>
      <person handle="_cdeb90490341f84abadc55e8d91" change="1449969693" id="auz_dawid_16xx">
        <gender>M</gender>
        <name type="Birth Name">
          <first>Dawid</first>
          <surname>Auzbikowicz</surname>
          <citationref hlink="_cddaedd03665299d651197a0fe6"/>
        </name>
        <name alt="1" type="Also Known As">
          <first>Dovydas</first>
          <surname>Aušbikavičius</surname>
          <citationref hlink="_cdeb94216051f214c757700c346"/>
        </name>
        <name alt="1" type="Birth Name">
          <first>Давид</first>
          <surname>Аужбикович</surname>
          <citationref hlink="_ce1cdbe42fe524f207c999d4eb1"/>
        </name>
        <name alt="1" type="Birth Name">
          <first>Давид</first>
          <surname prim="0" derivation="Patronymic">Янович</surname>
          <surname derivation="Inherited">Авжбикович</surname>
          <citationref hlink="_ce35c88075632b9af0ee2dd0d12"/>
        </name>
        <eventref hlink="_ce35c891d5765c1d82d4a5956e0" role="Primary"/>
        <childof hlink="_ce1cdf318723d6ab165ed97cdec"/>
        <parentin hlink="_ce1ce08bf4d326669280e0a18ea"/>
      </person>
    </people>
    <families>
      <family handle="_ce1cdf318723d6ab165ed97cdec" change="1416396371" id="F0091">
        <rel type="Unknown"/>
        <childref hlink="_cdeb90490341f84abadc55e8d91"/>
      </family>
      <family handle="_ce1ce08bf4d326669280e0a18ea" change="1416396433" id="F0092">
        <rel type="Unknown"/>
        <father hlink="_cdeb90490341f84abadc55e8d91"/>
      </family>
    </families>
    <events>
      <event handle="_ce35c891d5765c1d82d4a5956e0" change="1417065430" id="E0318">
        <type>Property</type>
        <dateval val="1677-10-02"/>
        <description>Давид купил часть имения Авжбиково (включая Андрунишки, Петринишки, Кайсютвишки) у браты Соломона и его жены Анны</description>
        <citationref hlink="_ce35c88075632b9af0ee2dd0d12"/>
      </event>
    </events>
    <citations>
      <citation handle="_ce35c88075632b9af0ee2dd0d12" change="1417066939" id="C0053">
        <dateval val="1677-10-02"/>
        <page>Листы 28—29об.</page>
        <confidence>2</confidence>
      </citation>
    </citations>
    ''')
    xml_root = ElementTree.fromstring(fixture)
    results = gramps_xml_to_yaml.transform(xml_root)
    results = list(results)
    expected = [
        (
            'events',
            'E0318',
            {
                'change': datetime.datetime(2014, 11, 27, 5, 17, 10),
                'citationref': [
                    {
                        'id': 'C0053'
                    }
                ],
                'date': {
                    'value': '1677-10-02'
                },
                'description': 'Давид купил часть имения Авжбиково (включая Андрунишки, '
                'Петринишки, Кайсютвишки) у браты Соломона и его жены Анны',
                'handle': '_ce35c891d5765c1d82d4a5956e0',
                'id': 'E0318',
                'type': 'Property'
            }
        ),
        (
            'people',
            'auz_dawid_16xx',
            {
                'id': 'auz_dawid_16xx',
                'handle': '_cdeb90490341f84abadc55e8d91',
                'gender': 'M',
                'eventref': [
                    { 'id': 'E0318', 'role': 'Primary' }
                ],
                'childof': [
                    { 'id': 'F0091' }
                ],
                'parentin': [
                    { 'id': 'F0092' }
                ],
                'name': [
                    {
                        'type': 'Birth Name',
                        'first': 'Dawid',
                        'surname': [
                            { 'text': 'Auzbikowicz' }
                        ],
                        'citationref': [
                            { 'hlink': '_cddaedd03665299d651197a0fe6' }
                        ],
                    },
                    {
                        'type': 'Also Known As',
                        'alt': True,
                        'first': 'Dovydas',
                        'surname': [
                            { 'text': 'Aušbikavičius' }
                        ],
                        'citationref': [
                            { 'hlink': '_cdeb94216051f214c757700c346' }
                        ],
                    },
                    {
                        'type': 'Birth Name',
                        'alt': True,
                        'first': 'Давид',
                        'surname': [
                            { 'text': 'Аужбикович' }
                        ],
                        'citationref': [
                            { 'hlink': '_ce1cdbe42fe524f207c999d4eb1' }
                        ],
                    },
                    {
                        'type': 'Birth Name',
                        'alt': True,
                        'first': 'Давид',
                        'surname': [
                            {
                                'prim': True,
                                'derivation': 'Patronymic',
                                'text': 'Янович',
                            },
                            {
                                'derivation': 'Inherited',
                                'text': 'Авжбикович',
                            }
                        ],
                        'citationref': [
                            { 'hlink': '_ce35c88075632b9af0ee2dd0d12' }
                        ],
                    }
                ],
                'change': datetime.datetime(2015, 12, 13, 1, 21, 33),
            }
        ),
        (
            'families',
            'F0091',
            {
                'id': 'F0091',
                'handle': '_ce1cdf318723d6ab165ed97cdec',
                'childref': [
                    { 'id': 'auz_dawid_16xx' }
                ],
                'rel': [
                    { 'type': 'Unknown' }
                ],
                'change': datetime.datetime(2014, 11, 19, 11, 26, 11),
            }
        ),
        (
            'families',
            'F0092',
            {
                'id': 'F0092',
                'handle': '_ce1ce08bf4d326669280e0a18ea',
                'father': {
                    'id': 'auz_dawid_16xx'
                },
                'rel': [
                    { 'type': 'Unknown' }
                ],
                'change': datetime.datetime(2014, 11, 19, 11, 27, 13),
            }
        ),
        (
            'citations',
            'C0053',
            {
                'id': 'C0053',
                'handle': '_ce35c88075632b9af0ee2dd0d12',
                'confidence': '2',
                'date': { 'value': '1677-10-02' },
                'page': 'Листы 28—29об.',
                'change': datetime.datetime(2014, 11, 27, 5, 42, 19),
            }
        )

    ]
    assert expected == results
