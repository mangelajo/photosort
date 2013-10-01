# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import argparse
import sys
import logging

import config
from photodb import *


class PhotoSort:

    def __init__(self, config_filename, log_level):

        self._config = config.Config(config_filename)
        logging.basicConfig(filename=self._config.log_file(), level=log_level)
        self._photodb = PhotoDB(self._config)

    def sync(self):
        pass

    def rebuild_db(self):
        self._photodb.rebuild()

    def daemonize(self):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('op', action="store",
                        choices=['sync', 'rebuilddb', 'daemon'],
                        help="Operation")

    group = parser.add_argument_group('Common parameters')
    group.add_argument('--config', action="store",
                       help="Customized configuration file",
                       default='config.yml')
    group.add_argument('--debug',
                       action="store_true",
                       help="Enable debugging")
    ns = parser.parse_args()

    log_level = logging.ERROR
    if ns.debug:
        log_level = logging.DEBUG
    photo_sort = PhotoSort(ns.config, log_level)

    if ns.op == "sync":
        photo_sort.sync()

    elif ns.op == "rebuilddb":
        photo_sort.rebuild_db()

    elif ns.op == "daemon":
        photo_short.daemonize()

if __name__ == "__main__":
    main()
