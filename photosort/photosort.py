# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import argparse
import logging
import os
import sys
import time
import traceback

from photosort import config
from photosort import media
from photosort import photodb
from photosort import walk

VERSION = "2020.1.2"


class PhotoSort:

    def __init__(self, config_filename, log_level):

        self._config = config.Config(config_filename)
        self._setup_logging(log_level)
        self._photodb = photodb.PhotoDB(self._config)
        self._duplicates_dir = self._config.duplicates_dir()
        self._dir_pattern = self._config.dir_pattern()
        self._file_prefix = self._config.file_prefix()
        self._inputs = (self._config.sources()[source]['dir']
                        for source in self._config.sources().keys())
        self._file_mode = self._config.output_chmod()

    def _setup_logging(self, log_level):
        if self._config.log_file():
            logging.basicConfig(filename=self._config.log_file(),
                                level=log_level)
        else:
            logging.basicConfig(stream=sys.stderr,
                                level=log_level)

    def _sync_source(self, src_dir):
        try:
            walker = walk.WalkForMedia(src_dir)
        except IOError:
            logging.error("Unable to walk dir %s", src_dir)
            return

        for file_dir, file_name in walker.find_media():
            file_path = os.path.join(file_dir, file_name)
            media_file = media.MediaFile.build_for(file_path)
            if self._photodb.is_duplicate(media_file):
                file = media_file.get_filename()
                duplicates_path = os.path.join(self._duplicates_dir, file)

                logging.info("moving to duplicates: %s", duplicates_path)

                media_file.rename_as(duplicates_path, self._file_mode)
            else:
                if media_file.move_to_directory_with_date(
                        self._photodb._output_dir,
                        self._dir_pattern,
                        self._file_prefix,
                        self._file_mode):
                    self._photodb.add_to_db(
                        media_file.get_directory(), media_file.get_filename(),
                        media_file)
        self._photodb.write()

    def rebuild_db(self):
        """
        registers in the DB the media files already existing in the
        target directory to be able to detect duplicates and avoid
        overwritting
        """
        walker = walk.WalkForMedia(
            self._config.output_dir(), ignores=self._inputs)
        for file_dir, file_name in walker.find_media():
            try:
                file_path = os.path.join(file_dir, file_name)
                media_file = media.MediaFile.build_for(file_path)
                self._photodb.add_to_db(file_dir, file_name, media_file)
            except Exception:
                logging.critical("Unexpected error: %s", sys.exc_info()[0])
        self._photodb.write()

    def sync(self):
        """
        ensures that the media files of the input directories are sorted
        """
        for source, value in self._config.sources().items():
            self._sync_source(value['dir'])

    def monitor(self):
        """
        regularly (10s at the time of this writting)
        ensures that the media files of the input directories are sorted
        """
        while True:
            self.sync()
            time.sleep(10)

    @staticmethod
    def version():
        print("photosort version %s" % VERSION)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('op', action="store",
                        choices=['sync', 'rebuilddb', 'monitor', "version"],
                        help="Operation")

    group = parser.add_argument_group('Common parameters')
    group.add_argument('--config', action="store",
                       help="Customized configuration file",
                       default='/etc/photosort.yml')
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
        elif ns.op == "version":
            photo_sort.version()
        else:
            print("Unknown operation: %s" % ns.op)
    except Exception:
        logging.critical("Unexpected error: %s", sys.exc_info()[0])
        logging.critical(traceback.format_exc())


if __name__ == "__main__":
    main()
