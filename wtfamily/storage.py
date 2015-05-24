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
    def __init__(self, basedir, entity_name, sync_on_demand=True):
        #self.basedir = basedir
        #self.name = entity_name
        self.path = os.path.join(basedir, entity_name + YAML_EXTENSION)

        self._items = None
        if not sync_on_demand:
            self._ensure_data_ready()

    def _ensure_data_ready(self):
        # sync on demand
        if self._items is None:
            self._load_data()

    def _load_data(self):
        print('  * EntityStorage loading from {} ...'.format(self.path))
        if os.path.exists(self.path):
            with open(self.path) as f:
                self._items = yaml.load(f)
        else:
            # TODO: create dir(s) after we begin storing entities in separate files
            self._items = {}

    def add(self, pk, data, upsert=False, commit=True):
        self._ensure_data_ready()
        assert upsert or pk not in self._items, (pk, data)
        self._items[pk] = data

    def commit(self):
        print('  * EntityStorage commit to {} ...'.format(self.path))
        self._ensure_data_ready()
        with open(self.path, 'w') as f:
            yaml.dump(self._items, f, allow_unicode=True, default_flow_style=False)

    def find_and_adapt_to_legacy(self):
        self._ensure_data_ready()
        return self._items.values()
