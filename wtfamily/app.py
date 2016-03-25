#!/usr/bin/env python

import os

import argh
from monk import validate
import yaml

from storage import Storage
from web import WTFamilyWebApp
from etl import WTFamilyETL
from debug import WTFamilyDebug


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
    debug = WTFamilyDebug({
        'storage': storage,
        'storage_conf': conf['storage'],
    })

    import place_to_event_algo_test
    algotest = place_to_event_algo_test.AlgoTest({'storage': storage})

    command_tree = {
        None: webapp.commands,
        'etl': etl.commands,
        'db': storage.commands,
        'algotest': algotest.commands,
        'debug': debug.commands,
    }
    for namespace, commands in command_tree.items():
        cli.add_commands(commands, namespace=namespace)

    cli.dispatch()


if __name__ == '__main__':
    main()
