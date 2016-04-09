#!/usr/bin/env python
#
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

    command_tree = {
        None: webapp.commands,
        'etl': etl.commands,
        'db': storage.commands,
        'debug': debug.commands,
    }
    for namespace, commands in command_tree.items():
        cli.add_commands(commands, namespace=namespace)

    cli.dispatch()


if __name__ == '__main__':
    main()
