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
import atexit
import code
import importlib
import os

from confu import Configurable

# local
import models
import storage


APP_NAME = 'WTFamily'
RELEVANT_MODULES = (
    models,
    storage,
)


class WTFamilyDebug(Configurable):
    needs = {
        'storage': storage.Storage,
        'storage_conf': dict,
    }

    @property
    def commands(self):
        return [self.shell]

    def shell(self):
        namespace = {}

        def _reload_relevant_modules_but_keep_storage():
            _reload_relevant_modules(keep_storage=True)

        def _reload_relevant_modules(keep_storage=False):
            try:
                storage_obj = models.Entity._get_root_storage()
            except RuntimeError:    # flask.g?
                storage_obj = None

            for m in RELEVANT_MODULES:
                print('reloading', m, '...')
                importlib.reload(m)

            if not (storage_obj or keep_storage):
                storage_obj = self.storage

            # monkey-patch to avoid flask.g
            models.Entity._get_root_storage = lambda: storage_obj

            for m in RELEVANT_MODULES:
                for k, v in m.__dict__.items():
                    if isinstance(v, type) and v.__module__ == m.__name__:
                        namespace[k] = v

        _reload_relevant_modules()

        namespace.update({
            's': models.Entity._get_root_storage,
            'm': models,
            'r': _reload_relevant_modules_but_keep_storage,
            'reload': _reload_relevant_modules_but_keep_storage,
            'reload_full': _reload_relevant_modules,
        })

        print('Locals:', ', '.join(namespace))

        try:
            import readline
        except ImportError:
            readline = None
        if readline:
            import rlcompleter
            readline.set_completer(rlcompleter.Completer(namespace).complete)
            readline.parse_and_bind("tab:complete")

            # XXX hacky/debuggish
            history_file = os.path.expanduser('~/.local/share/wtfamily/shell-history.log')
            history_file_dir = os.path.dirname(history_file)
            if not os.path.exists(history_file_dir):
                os.makedirs(history_file_dir)
            atexit.register(lambda: readline.write_history_file(history_file))
            if os.path.exists(history_file):
                readline.read_history_file(history_file)

        banner = '{} interactive shell'.format(APP_NAME)
        code.interact(banner=banner, local=namespace)
