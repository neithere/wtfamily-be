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
    import code

    # local
    import models

    conf = _get_config()
    storage = Storage(conf['storage'])

    # monkey-patch to avoid flask.g
    models.Entity._get_root_storage = lambda: storage

    namespace = {
        'storage': storage,
        'models': models,
    }

    import rlcompleter
    import readline
    readline.set_completer(rlcompleter.Completer(namespace).complete)
    readline.parse_and_bind("tab:complete")

    banner = '{} interactive shell'.format(APP_NAME)
    code.interact(banner=banner, local=namespace)


if __name__ == '__main__':
    main()
