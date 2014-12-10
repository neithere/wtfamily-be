#!/usr/bin/env python

from flask import (
    Flask,
    abort, render_template,
)

import show_people as _dbi


GRAMPS_XML_PATH = 'data.gramps'


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
    object_list = Family.find()
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
            if conditions:
                for k, v in conditions.items():
                    if not isinstance(v, list):
                        v = [v]
                    if k in p and p[k] in v:
                        yield cls(p)
                        break
            else:
                yield cls(p)

    @classmethod
    def find_one(cls, conditions=None):
        for p in cls.find(conditions):
            return p

    @property
    def id(self):
        return self._data['@id']


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
        return _dbi._format_name(self._data['name'])

    @property
    def events(self):
        try:
            hlinks = _extract_hlinks(self._data['eventref'])
        except KeyError:
            return []
        return Event.find({'@handle': hlinks})

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


class Event(Entity):
    category_pl = 'events'
    category_sg = 'event'
    sort_key = lambda item: item.get('dateval', {}).get('@val', '')

    def __repr__(self):
        #return 'Event {}'.format(self._data)
        return 'Event {0.date} {0.type} {0.summary} {0.place}'.format(self)

    @property
    def type(self):
        return self._data['type']

    @property
    def date(self):
        return _dbi._format_dateval(self._data.get('dateval'))

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


class Place(Entity):
    category_pl = 'places'
    category_sg = 'placeobj'

    def __repr__(self):
        return '{0.title}'.format(self)

    @property
    def title(self):
        return self._data.get('ptitle')


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


if __name__ == '__main__':
    app.run(debug=True)
