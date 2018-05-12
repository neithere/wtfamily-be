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

import etl.translators as s


def as_xml(el):
    return etree.tostring(el, encoding='unicode', pretty_print=True)


def trim(value):
    lines = value.strip().split('\n')
    unindented_lines = (re.sub('^    ', '', x) for x in lines)
    return '\n'.join(unindented_lines) + '\n'


def test_n_tags_to_one_key():
    xml = trim('''
    <brain-specialist>
      <doctor-greeting>Hello</doctor-greeting>
      <doctor-name>Dr. Gumby</doctor-name>
    </brain-specialist>
    ''')

    data = {
        # two tags in XML → one native struct
        'doctor': {
            'greeting': 'Hello',
            'name': 'Dr. Gumby',
        },
    }

    class DoctorContributor(s.TagTranslatorContributor):
        @classmethod
        def to_xml(cls, data):
            greeting_el = etree.Element('doctor-greeting')
            greeting_el.text = data['doctor']['greeting']

            name_el = etree.Element('doctor-name')
            name_el.text = data['doctor']['name']

            return [greeting_el, name_el]

        @classmethod
        def from_xml(cls, el):
            greeting = name = None

            for child_el in el.getchildren():
                if child_el.tag == 'doctor-greeting':
                    greeting = child_el.text
                if child_el.tag == 'doctor-name':
                    name = child_el.text

            return {
                'doctor': {
                    'greeting': greeting,
                    'name': name,
                }
            }

    class BrainSpecialistConverter(s.TagTranslator):
        CONTRIBUTORS = DoctorContributor,

    converter = BrainSpecialistConverter()

    # data → XML
    assert as_xml(converter.to_xml('brain-specialist', data, {})) == xml

    # XML → data
    assert converter.from_xml(etree.fromstring(xml)) == data


def test_one_tag_to_n_keys():
    xml = trim('''
    <gumby-patient>
      <complaint>
        <subj>brain</subj>
        <verb>hurts</verb>
      </complaint>
    </gumby-patient>
    ''')

    data = {
        # one tag in XML → two native keys
        'complaint_subj': 'brain',
        'complaint_verb': 'hurts',
    }

    class GumbyPatientContributor(s.TagTranslatorContributor):
        @classmethod
        def to_xml(cls, data):
            subj_el = etree.Element('subj')
            subj_el.text = data['complaint_subj']

            verb_el = etree.Element('verb')
            verb_el.text = data['complaint_verb']

            complaint_el = etree.Element('complaint')
            complaint_el.append(subj_el)
            complaint_el.append(verb_el)

            return [complaint_el]

        @classmethod
        def from_xml(cls, el):
            subj = verb = None

            for child_el in el.getchildren():
                if child_el.tag == 'complaint':
                    for grandchild_el in child_el.getchildren():
                        if grandchild_el.tag == 'subj':
                            subj = grandchild_el.text
                        if grandchild_el.tag == 'verb':
                            verb = grandchild_el.text

            return {
                'complaint_subj': subj,
                'complaint_verb': verb,
            }

    class GumbyPatientConverter(s.TagTranslator):
        CONTRIBUTORS = GumbyPatientContributor,

    converter = GumbyPatientConverter()

    # data → XML
    assert as_xml(converter.to_xml('gumby-patient', data, {})) == xml

    # XML → data
    assert converter.from_xml(etree.fromstring(xml)) == data
