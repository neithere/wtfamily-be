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
import functools
import itertools
from time import time

from confu import Configurable
from flask import Blueprint, abort, jsonify, request, render_template
from pymongo.database import Database

from models import (
    Person,
    Event,
    Family,
    Place,
    Source,
    Citation,
    Note,
    NameMap,
    #MediaObject,
)

ALLOW_ANY_HOST = True


def jsonify_with_cors(*args, **kwargs):
    resp = jsonify(*args, **kwargs)
    if ALLOW_ANY_HOST:
        resp.headers.add('Access-Control-Allow-Origin', '*')
    return resp


class GenericModelAdapter:
    @classmethod
    def provide_list(cls, model):
        only_these_raw = request.values.get('ids', '')
        only_these_ids = [x for x in only_these_raw.split(',') if x]
        by_query = request.values.get('q')

        if only_these_ids:
            return model.find({'id': {'$in': only_these_ids}})
        elif by_query:
            xs = model.find()
            # TODO: optimize: use class methods FooModel.find_matching()
            # (i.e. they'd know which fields to search with $or)
            return (p for p in xs if p.matches_query(by_query))
        else:
            return model.find()

    @classmethod
    def prepare_obj(cls, obj, protect=False):
        return dict(obj.get_public_data(protect=protect), id=obj.id)


class PersonModelAdapter(GenericModelAdapter):
    model = Person

    @classmethod
    def provide_list(cls, model):
        assert model == cls.model

        relatives_of_id = request.values.get('relatives_of')
        by_event_id = request.values.get('by_event')
        by_namegroup = request.values.get('by_namegroup')

        if relatives_of_id:
            central_person = model.get(relatives_of_id)
            return central_person.related_people
        elif by_event_id:
            return model.find_all_referencing(Event, by_event_id)
        elif by_namegroup:
            xs = super().provide_list(model)
            return (p for p in xs if p.group_name == by_namegroup)
        else:
            return super().provide_list(model)

    @classmethod
    def prepare_obj(cls, obj, protect=False):
        data = super().prepare_obj(obj, protect)

        # FIXME pass request values explicitly
        with_related_people_ids = bool(request.values.get('with_related_people_ids'))

        if with_related_people_ids:
            # FIXME privacy?
            data['parents'] = [x.id for x in obj.get_parents()]
            data['spouses'] = [x.id for x in obj.get_partners()]

        return data


class EventModelAdapter(GenericModelAdapter):
    model = Event

    @classmethod
    def provide_list(cls, model):
        assert model == cls.model

        place_id = request.values.get('place_id')
        citation_ids_raw = request.values.get('proven_by', '')
        citation_ids = [x for x in citation_ids_raw.split(',') if x]

        if place_id:
            return Event.find_all_referencing(Place, place_id)
        elif citation_ids:
            citations = Citation.find({'id': {'$in': citation_ids}})
            events_by_citation = [c.events for c in citations]
            chained = itertools.chain(*events_by_citation)
            return set(chained)
        else:
            return super().provide_list(model)


class CitationModelAdapter(GenericModelAdapter):
    model = Citation

    @classmethod
    def provide_list(cls, model):
        assert model == cls.model

        source_id = request.values.get('source')

        if source_id:
            return model.find_all_referencing(Source, source_id)
        else:
            return super().provide_list(model)


class NameGroupModelAdapter(GenericModelAdapter):
    model = NameMap

    @classmethod
    def provide_list(cls, model):
        "NameMap is pre-filtered by type=group_as"
        assert model == cls.model
        return model.find({'type': NameMap.TYPE_GROUP_AS})

    @classmethod
    def prepare_obj(cls, obj, protect=False):
        data = obj.get_public_data()
        data.pop('type')
        return data


class RESTfulService(Configurable):
    needs = {
        'mongo_db': Database,
        'debug': False,
    }

    def make_blueprint(self):
        blueprint = Blueprint('restful_service', __name__)

        mapping = {
            Person: ('people', PersonModelAdapter),
            Event: ('events', EventModelAdapter),
            Family: ('families', GenericModelAdapter),
            Place: ('places', GenericModelAdapter),
            Source: ('sources', GenericModelAdapter),
            Citation: ('citations', CitationModelAdapter),
            Note: ('notes', GenericModelAdapter),
            NameMap: ('namegroups', NameGroupModelAdapter),
        }

        for model, settings in mapping.items():
            slug, adapter = settings
            url_list = '/{}/'.format(slug)
            url_detail = '/{}/<string:id>'.format(slug)
            handler_list = functools.partial(self._list, model, adapter,
                                             self.debug)
            handler_list.__name__ = '{}_list'.format(slug)
            handler_detail = functools.partial(self._detail, model, adapter,
                                               self.debug)
            handler_detail.__name__ = '{}_detail'.format(slug)
            blueprint.route(url_list, methods=['GET'])(handler_list)
            blueprint.route(url_detail, methods=['GET'])(handler_detail)

        blueprint.route('/person_name_groups', methods=['GET'])(self.person_name_group_list)

        return blueprint

    def _list(self, model, adapter, debug):
        before = time()

        obj_list = adapter.provide_list(model)

        protect = not debug
        pure_data_items = [adapter.prepare_obj(obj, protect) for obj in obj_list]
        resp = jsonify_with_cors(pure_data_items)

        after = time()

        print('Generated JSON for', model.__name__, 'list in', (after - before), 'sec')
        print('JSON response for', model.__name__, 'is', len(resp.response[0]), 'bytes')

        return resp

    def _detail(self, model, adapter, debug, id):
        before = time()
        try:
            obj = model.get(id)
        except model.ObjectNotFound:
            abort(404)
        protect = not debug
        resp = jsonify_with_cors(adapter.prepare_obj(obj, protect))
        after = time()
        print('Generated JSON for', model, 'detail in', (after - before), 'sec')
        return resp

    @classmethod
    @functools.lru_cache()
    def person_name_group_list(cls):
        "Runs once, caches the response (already in JSON)"
        before = time()
        seen_group_names = {}
        for p in Person.find():
            group_name = p.group_name
            data = seen_group_names.setdefault(group_name, {})
            #data['count'] = data.get('count', 0) + 1
            data.setdefault('person_ids', []).append(p.id)
        group_names = [
            dict({'name': n}, **seen_group_names[n])
            for n in sorted(seen_group_names)]
        resp = jsonify_with_cors(group_names)
        after = time()
        print('Generated JSON for surname_list in', (after - before), 'sec')
        return resp


class RESTfulApp(Configurable):
    needs = {
        'mongo_db': Database,
        'debug': False,
    }

    def make_blueprint(self):
        blueprint = Blueprint('restful_app', __name__)
        blueprint.route('/', methods=['GET'])(self.index)
        return blueprint

    def index(self):
        return render_template('restful_app.html')
