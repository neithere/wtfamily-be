#!/usr/bin/env python

import re

from flask import (
    Flask,
    abort, render_template,
)

import show_people as _dbi


GRAMPS_XML_PATH = 'data.gramps'

EVENT_TYPE_BIRTH = 'Birth'


app = Flask(__name__)

db = _dbi._parse_gramps_file(GRAMPS_XML_PATH)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/event/')
def event_index():
    object_list = Event.find()
    return render_template('event_list.html', object_list=object_list)


@app.route('/event/<obj_id>')
def event_detail(obj_id):
    obj = Event.find_one({'@id': obj_id})
    if not obj:
        abort(404)
    return render_template('event_detail.html', obj=obj)


@app.route('/family/')
def family_index():
    def _sort_key(item):
        # This is a very naïve sorting method.
        # We sort families by father's birth year; if it's missing, then
        # by mother's.  This does not take into account actual marriage dates,
        # so if the second wife was older than the first one, the second family
        # goes first.  The general idea is to roughly sort the families and
        # have older people appear before younger ones.
        if item.father and item.father.birth:
            return str(item.father.birth.year)
        if item.mother and item.mother.birth:
            return str(item.mother.birth.year)
        return ''
    object_list = sorted(Family.find(), key=_sort_key)
    return render_template('family_list.html', object_list=object_list)


@app.route('/family/<obj_id>')
def family_detail(obj_id):
    obj = Family.find_one({'@id': obj_id})
    if not obj:
        abort(404)
    return render_template('family_detail.html', obj=obj)


@app.route('/person/')
def person_index():
    object_list = Person.find()
    object_list = sorted(object_list, key=lambda x: x.name)
    return render_template('person_list.html', object_list=object_list)


@app.route('/person/<obj_id>')
def person_detail(obj_id):
    obj = Person.find_one({'@id': obj_id})
    if not obj:
        abort(404)
    return render_template('person_detail.html', obj=obj, db=db)


@app.route('/place/')
def place_index():
    object_list = Place.find()
    return render_template('place_list.html', object_list=object_list)


@app.route('/place/<obj_id>')
def place_detail(obj_id):
    obj = Place.find_one({'@id': obj_id})
    if not obj:
        abort(404)
    return render_template('place_detail.html', obj=obj, db=db)


@app.route('/map/heat')
def map_heatmap():
    events = Event.find()
    return render_template('map_heatmap.html', events=events)


@app.route('/map/circles')
def map_circles():
    places = [p for p in Place.find() if list(p.events)]
    return render_template('map_circles.html', places=places)


@app.route('/map/circles/integrated')
def map_circles_integrated():
    places = [p for p in Place.find() if list(p.events)]
    return render_template('map_circles_integrated.html', places=places)


class Entity:
    category_pl = NotImplemented
    category_sg = NotImplemented
    sort_key = None

    def __init__(self, data):
        self._data = data

    @classmethod
    def find(cls, conditions=None):
        items = db[cls.category_pl][cls.category_sg]
        if cls.sort_key:
            items = sorted(items, key=cls.sort_key)
        for p in items:
            if not conditions:
                yield cls(p)
                continue
            for k, v in conditions.items():
                if not isinstance(v, list):
                    v = [v]
                if k in p and p[k] in v:
                    yield cls(p)
                    break

    @classmethod
    def find_one(cls, conditions=None):
        for p in cls.find(conditions):
            return p

    @classmethod
    def find_by_event_ref(cls, hlink):
        # anything except Event can reference to an Event
        for obj in cls.find():
            refs = obj._data.get('eventref')
            if not refs:
                continue
            if hlink in _extract_hlinks(refs):
                yield obj

    @property
    def id(self):
        return self._data['@id']

    @property
    def handle(self):
        return self._data['@handle']


class Family(Entity):
    category_pl = 'families'
    category_sg = 'family'

    def __repr__(self):
        return '{} + {}'.format(self.father or '?',
                                self.mother or '?')

    def _get_participant(self, key):
        try:
            hlink = self._data[key]['@hlink']
        except KeyError:
            return None
        else:
            return Person.find_one({'@handle': hlink})

    @property
    def father(self):
        return self._get_participant('father')

    @property
    def mother(self):
        return self._get_participant('mother')

    @property
    def children(self):
        try:
            hlinks = _extract_hlinks(self._data['childref'])
        except KeyError:
            return []
        return Person.find({'@handle': hlinks})

    @property
    def events(self):
        try:
            hlinks = _extract_hlinks(self._data['eventref'])
        except KeyError:
            return []
        return Event.find({'@handle': hlinks})


class Person(Entity):
    category_pl = 'people'
    category_sg = 'person'

    def __repr__(self):
        #return 'Person {} {}'.format(self.name, self._data)
        return '{}'.format(self.name)

    @property
    def name(self):
        return _dbi._format_names(self._data['name'])[0]

    @property
    def names(self):
        return _dbi._format_names(self._data['name'])

    @property
    def events(self):
        try:
            hlinks = _extract_hlinks(self._data['eventref'])
        except KeyError:
            return []
        return Event.find({'@handle': hlinks})

    @property
    def attributes(self):
        try:
            attribs = self._data['attribute']
        except KeyError:
            return []
        attribs = _dbi._ensure_list(attribs)
        return attribs

    def get_parent_families(self):
        try:
            hlinks = _extract_hlinks(self._data['childof'])
        except KeyError:
            return []
        return Family.find({'@handle': hlinks})

    def get_families(self):
        try:
            hlinks = _extract_hlinks(self._data['parentin'])
        except KeyError:
            return []
        return Family.find({'@handle': hlinks})

    @property
    def birth(self):
        for event in self.events:
            if event.type == EVENT_TYPE_BIRTH:
                return event.date


class Event(Entity):
    category_pl = 'events'
    category_sg = 'event'
    sort_key = lambda item: (
        item.get('dateval', {}).get('@val', '') or
        item.get('daterange', {}).get('@start', '')
    )

    def __repr__(self):
        #return 'Event {}'.format(self._data)
        return 'Event {0.date} {0.type} {0.summary} {0.place}'.format(self)

    @property
    def type(self):
        return self._data['type']

    @property
    def date(self):
        return DateRepresenter(**self._data)

    @property
    def summary(self):
        return self._data.get('description', '')

    @property
    def place(self):
        try:
            hlinks = _extract_hlinks(self._data['place'])
        except KeyError:
            return
        return Place.find_one({'@handle': hlinks})

    @property
    def people(self):
        return Person.find_by_event_ref(self.handle)

    @property
    def families(self):
        return Family.find_by_event_ref(self.handle)


class Place(Entity):
    category_pl = 'places'
    category_sg = 'placeobj'

    def __repr__(self):
        return '{0.title}'.format(self)

    @property
    def name(self):
        return self._data.get('@name')

    @property
    def title(self):
        return self._data.get('ptitle')

    @property
    def alt_name(self):
        return _dbi._ensure_list(self._data.get('alt_name', []))

    @property
    def coords(self):
        coords = self._data.get('coord')
        if not coords:
            return
        return {
            'lat': _normalize_coords_to_pure_degrees(coords['@lat']),
            'lng': _normalize_coords_to_pure_degrees(coords['@long']),
        }

    @property
    def parent_places(self):
        try:
            hlinks = _extract_hlinks(self._data['placeref'])
        except KeyError:
            return
        return Place.find({'@handle': hlinks})

    @property
    def nested_places(self):
        #print( {'placeref': {'@hlink': self.handle}})
        for place in Place.find():
            if 'placeref' not in place._data:
                continue
            if self.handle in _extract_hlinks(place._data.get('placeref', [])):
                yield place

    @property
    def events(self):
        hlinks = []
        nested_to_see = [self]
        while nested_to_see:
            place = nested_to_see.pop()
            hlinks.append(place.handle)
            nested_to_see.extend(place.nested_places)

        for event in Event.find():
            if event.place and event.place.handle in hlinks:
                yield event


def _extract_hlinks(ref):
    if isinstance(ref, str):
        # 'foo'
        ref = {'@hlink': ref}
    if isinstance(ref, dict):
        # {'@hlink': 'foo'}
        ref = [ref]

    # [{'@hlink': 'foo'}]
    assert isinstance(ref, list)

    return [x['@hlink'] for x in ref]


def _format_date(obj_data):
    return str(DateRepresenter(**obj_data))


def _normalize_coords_to_pure_degrees(coords):
    if isinstance(coords, float):
        return coords
    assert isinstance(coords, str)
    parts = [float(x) for x in re.findall('([0-9\.]+)', coords)]
    pure_degrees = parts.pop(0)
    if parts:
        # minutes
        pure_degrees += (parts.pop(0) / 60)
    if parts:
        # seconds
        pure_degrees += (parts.pop(0) / 60*60)
    assert not parts, (coords, pure_degrees, parts)
    if 'S' in coords or 'W' in coords:
        pure_degrees = -pure_degrees
    return pure_degrees


class DateRepresenter:
    def __init__(self, dateval=None, daterange=None, **kwargs):
        self.dateval = dateval
        self.daterange = daterange

    def __str__(self):
        if self.dateval:
            node = self.dateval
            val = node['@val']
        elif self.daterange:
            node = self.daterange
            val = '{}—{}'.format(
                node.get('@start'),
                node.get('@stop'),
            )
        else:
            return '?'

        vals = [
            node.get('@quality'),
            node.get('@type'),
            val,
        ]
        return ' '.join([x for x in vals if x])

    @property
    def year(self):
        "Returns earliest known year as string"
        if self.dateval:
            return self.dateval['@val']
        elif self.daterange:
            return self.daterange['@start']
        else:
            return ''


if __name__ == '__main__':
    app.run(debug=True)
