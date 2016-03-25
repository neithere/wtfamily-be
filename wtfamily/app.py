#!/usr/bin/env python

import os

import argh
from monk import validate
import yaml

from storage import Storage
from web import WTFamilyWebApp
from etl import WTFamilyETL


APP_NAME = 'WTFamily'
ENV_CONFIG_VAR = 'WTFAMILY_CONFIG'


def _get_config():
    conf_file_path = os.getenv(ENV_CONFIG_VAR, 'conf.yaml')
    with open(conf_file_path) as f:
        conf = yaml.load(f)

    validate({
        'storage': dict,
        'etl': dict,
        'web': dict,
    }, conf)

    return conf


def main():
    cli = argh.ArghParser()

    conf = _get_config()

    storage = Storage(conf['storage'])
    webapp = WTFamilyWebApp(conf['web'], {'storage': storage})
    etl = WTFamilyETL(conf['etl'], {'storage': storage})

    import place_to_event_algo_test
    algotest = place_to_event_algo_test.AlgoTest({'storage': storage})

    command_tree = {
        None: webapp.commands,
        'etl': etl.commands,
        'db': storage.commands,
        'algotest': algotest.commands,
        'debug': [shell],
    }
    for namespace, commands in command_tree.items():
        cli.add_commands(commands, namespace=namespace)

    cli.dispatch()


def shell():
    import atexit
    import code
    import importlib

    # local
    import models
    import storage

    RELEVANT_MODULES = (
        models,
        storage,
    )

    conf = _get_config()
    storage = Storage(conf['storage'])

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
            storage_obj = Storage(conf['storage'])

        # monkey-patch to avoid flask.g
        models.Entity._get_root_storage = lambda: storage_obj

    _reload_relevant_modules()

    namespace = {
        's': models.Entity._get_root_storage,
        'm': models,
        'r': _reload_relevant_modules_but_keep_storage,
        'reload': _reload_relevant_modules_but_keep_storage,
        'reload_full': _reload_relevant_modules,
    }

    for m in RELEVANT_MODULES:
        for k, v in m.__dict__.items():
            if isinstance(v, type) and v.__module__ == m.__name__:
                namespace[k] = v

    print('Locals:', list(namespace))


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


if __name__ == '__main__':
    main()
