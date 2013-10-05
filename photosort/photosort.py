# -*- mode: python; coding: utf-8 -*-


__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import argparse
import logging
import traceback

import sys
import time
import photodb
import config
import walk
import os

class PhotoSort:

    def __init__(self, config_filename, log_level):

        self._config = config.Config(config_filename)
        logging.basicConfig(filename=self._config.log_file(), level=log_level)
        self._photodb = photodb.PhotoDB(self._config)

    def _sync_source(self,src_dir):
        walker = walk.WalkForMedia(src_dir)
        for file_dir,file_name in walker.find_media():
            file_path = os.path.join(file_dir,file_name)
            self._photodb.add_file(file_path)

    def sync(self):
        for source,value in self._config.sources().items():
            self._sync_source(value['dir'])

    def rebuild_db(self):
        self._photodb.rebuild()

    def monitor(self):
        while True:
            self.sync()
            time.sleep(10)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('op', action="store",
                        choices=['sync', 'rebuilddb', 'monitor'],
                        help="Operation")

    group = parser.add_argument_group('Common parameters')
    group.add_argument('--config', action="store",
                       help="Customized configuration file",
                       default='config.yml')
    group.add_argument('--debug',
                       action="store_true",
                       help="Enable debugging")
    ns = parser.parse_args()

    log_level = logging.INFO
    if ns.debug:
        log_level = logging.DEBUG
    photo_sort = PhotoSort(ns.config, log_level)

    try:
        if ns.op == "sync":
            photo_sort.sync()

        elif ns.op == "rebuilddb":
            photo_sort.rebuild_db()

        elif ns.op == "monitor":
            photo_sort.monitor()
        else:
            print("Unknown operation: %s" % ns.op)
    except:
        logging.critical("Unexpected error: %s" % (sys.exc_info()[0]))
        logging.critical(traceback.format_exc())

