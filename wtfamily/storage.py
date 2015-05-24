import os

import argh
from confu import Configurable
import yaml


class Storage(Configurable):
    needs = {
        'path': str,
    }

    def init(self):
        print('Storage.init...')
        if os.path.exists(self.path):
            with open(self.path) as f:
                self._data = yaml.load(f)
        else:
            # TODO: create dir(s) after we begin storing entities in separate files
            self._data = {}
        print('/ Storage.init')

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
        if entity_type not in self._data:
            self._data[entity_type] = {}
        assert upsert or pk not in self._data[entity_type], (pk, item)
        self._data[entity_type][pk] = item

    def commit(self):
        print('Storage.commit...')
        with open(self.path, 'w') as f:
            yaml.dump(self._data, f, allow_unicode=True, default_flow_style=False)
        print('/ Storage.commit')
