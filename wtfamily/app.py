#!/usr/bin/env python

import os

import argh
from monk import validate
import yaml

from web import WTFamilyWebApp


if __name__ == '__main__':
    cli = argh.ArghParser()

    CONF_FILE = os.getenv('WTFAMILY_CONFIG', 'conf.yaml')
    with open(CONF_FILE) as f:
        conf = yaml.load(f)

    validate({
        'web': dict,
    }, conf)

    webapp = WTFamilyWebApp(conf['web'])

    command_tree = {
        None: webapp.commands,
    }
    for namespace, commands in command_tree.items():
        cli.add_commands(commands, namespace=namespace)

    cli.dispatch()
