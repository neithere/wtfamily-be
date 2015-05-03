#!/usr/bin/env python

from collections import OrderedDict
import gzip
import pprint

import argh
import xmltodict


'''
OrderedDict([
    ('@type', 'Birth Name'),
    ('first', 'Мария'),
    ('surname', [
        OrderedDict([
            ('@derivation', 'Inherited'),
            ('#text', 'Аузбикович')
        ]),
        OrderedDict([
            ('@prim', '0'),
            ('@derivation', 'Patronymic'),
            ('#text', 'Ксаверьевна')
        ])
    ])
])
'''




def TEST__etree(path):
    from xml.etree.elementtree import ElementTree
    tree = ElementTree(path)
    for x in tree.findall('person'):
        print(x)


def _format_names(name_node):
    if not isinstance(name_node, list):
        name_node = [name_node]
    return [_format_name(n) for n in name_node]


def _get_name_parts(name_node):

    #print('---')
    #import pprint
    #pprint.pprint(name_node)
    #print('---')

    first = name_node.get('first', '?')
    primary_surnames = []
    patronymic = []
    nonpatronymic = []

    surname_spec = name_node.get('surname', '?')

    if isinstance(surname_spec, str):
        #primary_surnames.append(surname_spec)
        surname_spec = [
            {
                '#text': surname_spec,
            }
        ]

    if isinstance(surname_spec, dict):
        surname_spec = [surname_spec]

    for surname in surname_spec:
        #print('surname:', surname)
        if isinstance(surname, str):
            surname = {
                '#text': surname,
            }
        derivation = surname.get('@derivation')
        is_primary = surname.get('@prim') != '0'
        text = surname.get('#text', '???')
        if derivation == 'Patronymic':
            patronymic.append(text)
        elif is_primary:
            primary_surnames.append(text)
        else:
            nonpatronymic.append(text)

    return first, primary_surnames, patronymic, nonpatronymic


def _format_name(name_node):
    #template = '{primary} ({nonpatronymic}), {first} {patronymic}'
    template = '{first} {patronymic} {primary} ({nonpatronymic})'

    first, primary_surnames, patronymic, nonpatronymic = _get_name_parts(name_node)

    ' '.join(primary_surnames)
    ' '.join(patronymic)
    ' '.join(nonpatronymic)
    return template.format(
        first = first,
        primary = ' '.join(primary_surnames),
        patronymic = ' '.join(patronymic),
        nonpatronymic = ' '.join(nonpatronymic),
    ).replace(' ()', '').strip()


def _parse_gramps_file(path, ):
    def _postprocessor(path, key, value):
        # simplify data by ignoring dict order
        if isinstance(value, OrderedDict):
            value = dict(value)
        return key, value

    with gzip.GzipFile(path) as f:
        tree = xmltodict.parse(f, postprocessor=_postprocessor)
    return tree['database']


def main(path):
    db = _parse_gramps_file(path)

    people = db['people']['person']
    events = db['events']['event']
    families = db['families']['family']
    print(len(people), 'people')
    print(len(events), 'events')
    print(len(families), 'families')
    print('---')

    for person in people:
        #print('')
        name = ' AKA '.join(_format_names(person['name']))
        #print('------------------')
        print(person['@id'], person['gender'], name)
        #pprint.pprint(person)
        if 'childof' in person:
            parents = _find_people(db, 'parentin', person['childof'])
            print('  Parents:', ' + '.join(_format_names(p['name'])[0] for p in parents))
        if 'eventref' in person:
            for event in _find_events(db, person['eventref']):
                #pprint.pprint(event)
                places = ', '.join(x['ptitle'] for x in _find_places(db, event.get('place')))
                print('  {type_}: {date} {summary} @{place}'.format(
                          date=_format_dateval(event.get('dateval')) or '(when?)',
                          type_=event['type'],
                          summary=event.get('description', ''),
                          place=places or 'where?'))
        #families = db['families']['family']
#        pprint.pprint(family)


def _find_people(db, key, searched_values):
    searched_values = _ensure_list(searched_values)
    searched_hlinks = [value['@hlink'] for value in searched_values]
    for person in db['people']['person']:
        if key not in person:
            continue
        elems = _ensure_list(person[key])
        # {..., 'parentin': {'@hlink': '_ce35d5cb4ea5a05e4aceed3a3fa'}}
        hlinks = [elem['@hlink'] for elem in elems]
        if any(h in searched_hlinks for h in hlinks):
            yield person


def _find_by_handle(db, category_pl, category_sg, hlinks):
    if not hlinks:
        return
    searched_values = _ensure_list(hlinks)
    searched_hlinks = [value['@hlink'] for value in searched_values]
    for event in db[category_pl][category_sg]:
        #pprint.pprint(event)
        if event['@handle'] in searched_hlinks:
            yield event

def _find_events(db, searched_values):
    return _find_by_handle(db, 'events', 'event', searched_values)

def _find_places(db, searched_values):
    return _find_by_handle(db, 'places', 'placeobj', searched_values)


def _ensure_list(item):
    if isinstance(item, list):
        return item
    else:
        return [item]


def _format_dateval(dateval):
    if not dateval:
        return
    if '@val' in dateval:
        val = dateval['@val']
    elif 'daterange' in dateval:
        assert 0, dateval
        val = '{}—{}'.format(
            dateval['daterange'].get('@start'),
            dateval['daterange'].get('@stop')
        )
    else:
        val = '?'
    vals = [
        dateval.get('@quality'),
        dateval.get('@type'),
        val,
    ]
    return ' '.join([x for x in vals if x])


if __name__ == '__main__':
    argh.dispatch_command(main)
