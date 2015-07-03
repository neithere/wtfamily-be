import os

import argh
from confu import Configurable
import yaml


YAML_EXTENSION = '.yaml'
ENTITIES = (
    'citations',
    'name-formats',
    'events',
    'people',
    'families',
    'sources',
    'places',
    'objects',
    'repositories',
    'notes',
    'bookmarks',
    'namemaps',
)


class Storage(Configurable):
    needs = {
        'path': str,
    }

    def init(self):
        self._entities = {}
        for entity_name in ENTITIES:
            self._entities[entity_name] = EntityStorage(self.path, entity_name)

    @property
    def commands(self):
        return [self.check_consistency]

    @argh.aliases('check')
    def check_consistency(self):
        # TODO:
        # for each entity
        #    for each object
        #        for each "...ref" field
        #            for each value
        #                does this ID exist?  warn if not.
        raise NotImplementedError

    def add(self, entity_type, pk, item, upsert=False, commit=True):
        if commit:
            raise NotImplementedError('Direct write is not yet supported')
        self._entities[entity_type].add(pk, item, upsert=upsert, commit=commit)

    def commit(self):
        print('* Storage.commit ...'.format(self.path))
        for entity_store in self._entities.values():
            entity_store.commit()


class EntityStorage:
    INDEXED_ATTRS = ('handle', 'place.hlink', 'placeref.hlink')

    def __init__(self, basedir, entity_name, sync_on_demand=True):
        #self.basedir = basedir
        #self.name = entity_name
        self.path = os.path.join(basedir, entity_name)

        self._items = None
        if not sync_on_demand:
            self._ensure_data_ready()

        self._init_index()

    def _ensure_data_ready(self):
        # sync on demand
        if self._items is None:
            self._load_data()

    def _ensure_dir(self):
        if not os.path.exists(self.path):
            os.mkdir(self.path)

    def _load_data(self):
        print('  * EntityStorage loading from {} ...'.format(self.path))
        self._ensure_dir()
        filenames = [f for f in os.listdir(self.path)
                        if f.endswith(YAML_EXTENSION)]
        if self._items is None:
            self._items = {}
        for fn in filenames:
            pk, _, _ = fn.rpartition(YAML_EXTENSION)
            filepath = os.path.join(self.path, fn)
            with open(filepath) as f:
                data = yaml.load(f)
            self._add_item_to_index(pk, data)
            self._items[pk] = data

    def _init_index(self):
        # attr to ID —  mainly for hlink, maybe something else
        self._index = {}
        for attr in self.INDEXED_ATTRS:
            self._index[attr] = {}

    def _add_item_to_index(self, pk, data):
        for key in self.INDEXED_ATTRS:

            separator = '.'
            if separator in key:
                value = _get_innermost_value(key, data, separator)
                if not value:
                    continue
            else:
                try:
                    value = data[key]
                except KeyError:
                    return    # XXX ?

            assert not isinstance(value, dict)
            if isinstance(value, list):
                values = value
            else:
                values = [value]

            for v in values:
                try:
                    self._index[key].setdefault(v, []).append(pk)
                except Exception as e:
                    print(e, key, v)
                    raise

    def _get_pks_by_index(self, key, values):
        if not isinstance(values, list):
            values = [values]

        try:
            known_values = self._index[key]
        except KeyError:
            return

        pks = []
        for v in values:
            try:
                pks.extend(known_values[v])
            except KeyError:
                pass

        return list(set(pks))


    def add(self, pk, data, upsert=False, commit=True):
        self._ensure_data_ready()
        assert upsert or pk not in self._items, (pk, data)
        self._items[pk] = data

    def commit(self):
        print('  * EntityStorage commit to {} ...'.format(self.path))
        self._ensure_data_ready()    # also implies _ensure_dir()
        for pk, data in self._items.items():
            fn = pk + YAML_EXTENSION
            filepath = os.path.join(self.path, fn)
            with open(filepath, 'w') as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    def find_and_adapt_to_legacy(self):
        self._ensure_data_ready()
        return self._items.values()

    def find_by_index(self, key, values):
        # NOTE: as we have all possible values there, we can do complex
        # comparison operations on them, too
        assert key in self.INDEXED_ATTRS
        if not isinstance(values, list):
            values = [values]
        for v in values:
            pks = self._get_pks_by_index(key, v)
            if not pks:
                continue
            for pk in pks:
                yield self._items[pk]


def _get_innermost_value(key, data, separator='.'):
    key_levels = key.split(separator)
    to_observe = [data]
    for key_level in key_levels:
        values = to_observe
        to_observe = []
        for value in values:

            if isinstance(value, list):
                subvalues = value
            else:
                subvalues = [value]

            for subvalue in subvalues:
                if key_level not in subvalue:
                    continue
                inner_value = subvalue[key_level]
                to_observe.append(inner_value)

    return to_observe
