# -*- mode: python; coding: utf-8 -*-
from __future__ import print_function

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import csv
import logging
import os.path


class PhotoDB:
    def __init__(self, config):

        self._db_file = config.db_file()
        self._output_dir = config.output_dir()
        self._file_mode = config.output_chmod()
        self._hashes = {}
        self.load()

    def load(self, merge=False, filename=None):
        """
        loads an existing DB

        If 'merge' is True, the values of previously loaded DBs (if any)
        are kept.
        If the path of a file is passed in 'filename', then
        """

        if filename is None:
            filename = self._db_file

        if not merge:
            self._hashes = {}
        try:
            logging.info("----------")
            logging.info("DB Loading %s", filename)
            with open(filename, 'r', encoding='utf-8') as f_in:
                dbreader = csv.reader(f_in, delimiter=',')
                try:
                    _ = next(dbreader)  # names
                except StopIteration:
                    logging.info("DB was empty")
                    return

                for file_dir, file_name, file_type, hash in dbreader:
                    self._hashes[hash] = {'dir': file_dir,
                                          'name': file_name,
                                          'type': file_type}
            logging.info("DB Load finished, %d entries", len(self._hashes))
        except IOError as e:
            if e.errno == 2:
                logging.debug(
                    "DB file %s doesn't exist yet, it will get created",
                    self._db_file)
            else:
                logging.error("Error opening DB file %s", self._db_file)
                raise

    def write(self):

        try:
            os.remove(self._db_file + ".bak")
        except OSError:
            pass

        try:
            os.rename(self._db_file, self._db_file + ".bak")
        except OSError:
            pass

        with open(self._db_file, 'w', encoding='utf-8') as f_out:

            dbwriter = csv.writer(f_out, delimiter=',')
            dbwriter.writerow(['directory', 'filename', 'type', 'md5'])

            for hash in self._hashes.keys():
                file_dir, file_name, file_type = (
                    self._hashes[hash]['dir'],
                    self._hashes[hash]['name'],
                    self._hashes[hash]['type'])

                dbwriter.writerow([file_dir, file_name, file_type, hash])

    def add_to_db(self, file_dir, file_name, media_file):
        try:
            hash = media_file.hash()
        except IOError as e:
            logging.error("IOError %s trying to hash %s", e,
                          media_file.get_path())
            return False

        file_type = media_file.type()

        # remove output dir path + '/'
        file_dir = file_dir[len(self._output_dir) + 1:]
        self._hashes[hash] = {'dir': file_dir,
                              'name': file_name,
                              'type': file_type}

        logging.info("indexed %s/%s %s %s", file_dir, file_name,
                     file_type, hash)
        return True

    def is_duplicate(self, media_file):
        """
        checks if the given file has been already sorted
        returns True if so, False if not
        """
        hash = media_file.hash()

        if hash in self._hashes:

            filename_data = self._hashes[hash]
            filename2 = self._output_dir + "/" + \
                filename_data['dir'] + '/' + filename_data['name']

            if not media_file.is_equal_to(filename2):
                logging.critical("MD5 hash collision for two different files,"
                                 "handled as dupe: %s %s",
                                 media_file.get_path(), filename2)

            logging.info("%s was detected as duplicate with %s",
                         media_file.get_path(), filename2)

            return True
        return False
