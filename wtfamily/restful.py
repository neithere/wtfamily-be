#    WTFamily is a genealogical software.
#
#    Copyright © 2014—2016  Andrey Mikhaylenko
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
from time import time

from confu import Configurable
from flask import Blueprint, abort, jsonify, request, render_template

from models import (
    Person,
    Event,
    Family,
    Place,
    Source,
    Citation,
    #NameMap,
    #MediaObject,
)
from storage import Storage


class RESTfulService(Configurable):
    needs = {
        'storage': Storage,
        'debug': False,
    }

    def make_blueprint(self):
        blueprint = Blueprint('restful_service', __name__)
        mapping = {
            Person: ('people', self._list_provider_person),
            Event: ('events', None),
            Family: ('families', None),
            Place: ('places', None),
            Source: ('sources', None),
            Citation: ('citations', None),
        }
        for model, settings in mapping.items():
            slug, retrieve_data = settings
            url_list = '/{}/'.format(slug)
            url_detail = '/{}/<string:id>'.format(slug)
            handler_list = functools.partial(self._list, model, retrieve_data)
            handler_list.__name__ = '{}_list'.format(slug)
            handler_detail = functools.partial(self._detail, model)
            handler_detail.__name__ = '{}_detail'.format(slug)
            blueprint.route(url_list, methods=['GET'])(handler_list)
            blueprint.route(url_detail, methods=['GET'])(handler_detail)
        return blueprint

    def _list(self, model, list_provider):
        before = time()

        if not list_provider:
            list_provider = self._list_provider_generic

        obj_list = list_provider(model)

        pure_data_items = [self._prep_obj(obj) for obj in obj_list]
        resp = jsonify(pure_data_items)

        after = time()

        print('Generated JSON for', model, 'list in', (after - before), 'sec')
        print('JSON response for', model, 'is', len(resp.response[0]), 'bytes')

        return resp

    def _detail(self, model, id):
        before = time()
        try:
            obj = model.get(id)
        except model.ObjectNotFound:
            abort(404)
        resp = jsonify(self._prep_obj(obj))
        after = time()
        print('Generated JSON for', model, 'detail in', (after - before), 'sec')
        return resp

    def _prep_obj(self, obj):
        protect = not self.debug
        return dict(obj.get_public_data(protect=protect), id=obj.id)


    def _list_provider_generic(self, model):
        only_these_raw = request.values.get('ids', '')
        only_these_ids = [x for x in only_these_raw.split(',') if x]

        if only_these_ids:
            #print('only these ids:', only_these_ids)
            return model.find({'id': only_these_ids})
        else:
            return model.find()

    def _list_provider_person(self, model):
        assert model == Person

        relatives_of_id = request.values.get('relatives_of')

        if relatives_of_id:
            #print('relatives of', relatives_of_id)
            central_person = model.get(relatives_of_id)
            return central_person.related_people
        else:
            #print('unfiltered')
            return self._list_provider_generic(model)


class RESTfulApp(Configurable):
    needs = {
        'storage': Storage,
        'debug': False,
    }

    def make_blueprint(self):
        blueprint = Blueprint('restful_app', __name__)
        blueprint.route('/', methods=['GET'])(self.index)
        return blueprint

    def index(self):
        return render_template('restful_app.html')
