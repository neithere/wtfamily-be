from collections import OrderedDict
import json
#import os

import babel.dates
from confu import Configurable
from flask import (
    Flask, abort, render_template, url_for, g, request,
)
#from werkzeug import LocalProxy

from models import (
    Person,
    Event,
    Family,
    Place,
    Source,
    Citation,
    NameMap,
    MediaObject,
)
from storage import Storage


class WTFamilyWebApp(Configurable):
    needs = {
        'storage': Storage,
        'debug': False,
    }

    @property
    def commands(self):
        return [self.run]

    def run(self):
        self.flask_app = Flask(__name__)

        @self.flask_app.before_request
        def _init():
            g.storage = self.storage

        self.flask_app.route('/')(home)
        self.flask_app.route('/event/')(event_list)
        self.flask_app.route('/event/<obj_id>')(event_detail)
        self.flask_app.route('/family/')(family_list)
        self.flask_app.route('/family/<obj_id>')(family_detail)
        self.flask_app.route('/person/')(person_list)
        self.flask_app.route('/person/<obj_id>')(person_detail)
        self.flask_app.route('/place/')(place_list)
        self.flask_app.route('/place/<obj_id>')(place_detail)
        self.flask_app.route('/source/')(source_list)
        self.flask_app.route('/source/<obj_id>')(source_detail)
        self.flask_app.route('/citation/')(citation_list)
        self.flask_app.route('/citation/<obj_id>')(citation_detail)
        self.flask_app.route('/media/')(media_list)
        self.flask_app.route('/media/<obj_id>')(media_detail)

        self.flask_app.route('/map/heat')(map_heatmap)
        self.flask_app.route('/map/circles')(map_circles)
        self.flask_app.route('/map/circles/integrated')(map_circles_integrated)
        self.flask_app.route('/map/places')(map_places)
        self.flask_app.route('/map/migrations/<person_ids>')(map_migrations)

        self.flask_app.route('/orgchart')(orgchart)
        self.flask_app.route('/orgchart/data')(orgchart_data)
        self.flask_app.route('/familytreejs')(familytreejs)
        self.flask_app.route('/familytree.json')(familytreejs_json)
        self.flask_app.route('/familytree-bp')(familytree_primitives)
        self.flask_app.route('/familytree-bp/data')(familytree_primitives_data)

        self.flask_app.template_filter('format_timedelta')(babel.dates.format_timedelta)

        self.flask_app.run(debug=self.debug)


#@app.route('/')
def home():
    return render_template('home.html')


#@app.route('/event/')
def event_list():
    object_list = Event.find()
    return render_template('event_list.html', object_list=object_list)


#@app.route('/event/<obj_id>')
def event_detail(obj_id):
    obj = Event.get(obj_id)
    if not obj:
        abort(404)
    return render_template('event_detail.html', obj=obj)


#@app.route('/family/')
def family_list():
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


#@app.route('/family/<obj_id>')
def family_detail(obj_id):
    obj = Family.get(obj_id)
    if not obj:
        abort(404)
    return render_template('family_detail.html', obj=obj)


#@app.route('/person/')
def person_list():
    object_list = Person.find()
    object_list = sorted(object_list, key=lambda x: x.name)
    return render_template('person_list.html', object_list=object_list)


#@app.route('/person/<obj_id>')
def person_detail(obj_id):
    obj = Person.get(obj_id)
    if not obj:
        abort(404)
    return render_template('person_detail.html', obj=obj)


#@app.route('/place/')
def place_list():
    object_list = (p for p in Place.find() if not p._data.get('placeref'))
    return render_template('place_list.html', object_list=object_list)


#@app.route('/place/<obj_id>')
def place_detail(obj_id):
    obj = Place.get(obj_id)
    if not obj:
        abort(404)
    return render_template('place_detail.html', obj=obj)


#@app.route('/source/')
def source_list():
    object_list = Source.find()
    return render_template('source_list.html', object_list=object_list)


#@app.route('/source/<obj_id>')
def source_detail(obj_id):
    obj = Source.get(obj_id)
    if not obj:
        abort(404)
    return render_template('source_detail.html', obj=obj)


#@app.route('/citation/')
def citation_list():
    object_list = Citation.find()
    by_source = {}
    for citation in object_list:
        by_source.setdefault(citation.source, []).append(citation)
    return render_template('citation_list.html', groups=by_source)


#@app.route('/citation/<obj_id>')
def citation_detail(obj_id):
    obj = Citation.get(obj_id)
    if not obj:
        abort(404)
    if not obj.source:
        # either the reference is broken or the source is marked as private
        # skipped on export
        abort(404)
    return render_template('citation_detail.html', obj=obj)


def media_list():
    object_list = MediaObject.find()
    return render_template('media_list.html', object_list=object_list)


def media_detail(obj_id):
    obj = MediaObject.get(obj_id)
    if not obj:
        abort(404)
    return render_template('media_detail.html', obj=obj)


#@app.route('/map/heat')
def map_heatmap():
    events = Event.find()
    return render_template('map_heatmap.html', events=events)


#@app.route('/map/circles')
def map_circles():
    places = [p for p in Place.find() if list(p.events)]
    return render_template('map_circles.html', places=places)


#@app.route('/map/circles/integrated')
def map_circles_integrated():
    places = [p for p in Place.find() if list(p.events)]
    return render_template('map_circles_integrated.html', places=places)


def map_places():
    places = [p for p in Place.find()]
    print('places gathered, rendering template...')
    return render_template('map_places.html', places=places)


def map_migrations(person_ids):
    person_ids = person_ids.split(',')
    people = list(Person.find_by_pks(person_ids))
    places = []
    seen = {}
    for person in people:
        # XXX do we need to have unique places? in fact, zero-length lines are OK, too
        for place in person.places:
            if place.id not in seen:
                places.append(place)
                seen[place.id] = True
    #places = [p for p in Place.find()]

    print(places)

    print('places gathered, rendering template...')
    return render_template('map_migrations.html', places=places, people=people)


#@app.route('/orgchart')
def orgchart():
    return render_template('tree_orgchart.html')


#@app.route('/orgchart/data')
def orgchart_data():
    def _prep_row(person):
        parent_families = list(person.get_parent_families())
        if parent_families:
            # XXX ideally we should link to all members of all families
            parent = parent_families[0].father or parent_families[0].mother
            parent_id = parent.id
        else:
            parent_id = None
        # TODO use url_for
        name_format = '<a name="id{id}"></a><a href="/person/{id}">{name}</a><br><small>{birth}<br>{death}</small>{spouses}'
        tooltip_format = '{birth}'
        birth_str = '☀{}'.format(person.birth) if person.birth else ''
        death_str = '✝{}'.format(person.death) if person.death else ''
        def _compress_life_str(s):
            return (s.replace('estimated ', 'cca')
                     .replace('calculated ', 'calc')
                     .replace('about ', '~')
                     .replace('before ', '<')
                     .replace('after ', '>'))
        birth_str = _compress_life_str(birth_str)
        death_str = _compress_life_str(death_str)

        spouses = []
        for f in person.get_families():
            for x in (f.father, f.mother):
                if x and x.id != person.id:
                    spouses.append(x)
        if spouses:
            # TODO use url_for
            spouses_str = ', '.join(
                '⚭ <a href="/person/{0.id}">{0.name}</a><a href="#id{0.id}">#</a>'.format(s) for s in spouses)
        else:
            spouses_str = ''

        formatted_name = name_format.format(
            id=person.id,
            name=person.name,
            birth=birth_str,
            death=death_str,
            spouses=spouses_str)
        tooltip = tooltip_format.format(birth=person.birth)
        return [
            {
                'v': person.id,
                'f': formatted_name,
            },
            parent_id,
            tooltip,
        ]
    return json.dumps([_prep_row(p) for p in Person.find()])


#@app.route('/familytreejs')
def familytreejs():
    data_script = '/static/js/familytree_ajax.js'
    print(list(NameMap.find()))
    return render_template('familytree.html', data_script=data_script)


#@app.route('/familytreejs.json')
def familytreejs_json():
    people = sorted(Person.find(), key=lambda p: p.group_name)
    def _prepare_item(person):
        print(person.group_name, person.name)
        url = url_for('person_detail', obj_id=person.id)

        # XXX orphans should be handled on frontend
        if not list(person.get_parent_families()) and not list(person.get_families()):
            return

        data = {
            'name': person.name,
            'parents': [p.id for p in person.get_parents()],
            'blurb': '{}—{}'.format(person.birth or '?', person.death or '?'),
        }

        return person.id, data

    pairs = map(_prepare_item, people)
    data = OrderedDict(p for p in pairs if p)
    return json.dumps(data)
#    return json.dumps({
***REMOVED******REMOVED******REMOVED***#    })


#@app.route('/familytree-bp')
def familytree_primitives():
    return render_template('familytree_primitives.html')


#@app.route('/familytree-bp/data')
def familytree_primitives_data():
    people = sorted(Person.find(), key=lambda p: p.group_name)
    filter_surnames = set(x for x in request.values.get('surname', '').lower().split(',') if x)

    # only find ancestors of given person
    ancestors, descendants = None, None
    ancestors_of = request.values.get('ancestors_of')
    if ancestors_of:
        central_person = Person.get(ancestors_of)
        ancestors = central_person.find_ancestors()

    descendants_of = request.values.get('descendants_of')
    if descendants_of:
        central_person = Person.get(descendants_of)
        descendants = central_person.find_descendants()

    if ancestors_of or descendants_of:
        people = set(list(ancestors or [])) | set(list(descendants or []))

    def _prepare_item(person):
        names_lowercase = (n.lower() for n in person.group_names)
        if filter_surnames:
            intersects = filter_surnames & set(names_lowercase)
            if not intersects:
                return

        # ethical reasons
        if person.death.year:
            tmpl = '{born} — {dead}'
        else:
            tmpl = '{born}'
        description = tmpl.format(born=person.birth.year_formatted or '?',
                                  dead=person.death.year_formatted or '?')
        return {
            'id': person.id,
            'title': person.name,
            'parents': [p.id for p in person.get_parents()],
            'spouses': [p.id for p in person.get_partners()],
            'description': description,
            'gender': person.gender,
        }
    prepared = (_prepare_item(p) for p in people)
    filtered = (p for p in prepared if p)
    return json.dumps(list(filtered))
