# -*- mode: python; coding: utf-8 -*-
from __future__ import print_function

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"


import csv
import logging
import filecmp

import walk
from media import MediaFile


class PhotoDB:
    def __init__(self, config):

        self._db_file = config.db_file()
        self._output_dir = config.output_dir()
        self._inputs = (config.sources()[source]['dir']
                        for source in config.sources().keys())
        self._hashes = {}
        self.load()

    def load(self, merge=False, filename=None):

        if filename is None:
            filename = self._db_file

        if not merge:
            self._hashes = {}
        try:
            logging.info("DB Loading %s" % filename)
            with open(filename, 'r') as f_in:
                dbreader = csv.reader(f_in, delimiter=',')
                try:
                    names = dbreader.next()
                except StopIteration:
                    logging.info("DB was empty")
                    return

                for file_dir, file_name, file_type, hash in dbreader:
                    self._hashes[hash] = {'dir': file_dir,
                                              'name': file_name,
                                              'type': file_type}
            logging.info("DB Load finished, %d entries" % len(self._hashes))
        except IOError:
            logging.error("Error opening db file %s" % self._db_file)
            raise

    def write(self):

        try:
            os.remove(self._db_file+".bak")
        except:
            pass

        try:
            os.rename(self._db_file, self._db_file+".bak")
        except:
            pass

        with open(self._db_file, 'w') as f_out:

            dbwriter = csv.writer(f_out, delimiter=',')
            dbwriter.writerow(['directory', 'filename', 'type', 'md5'])

            for hash in self._hashes.keys():

                file_dir, file_name, file_type = (
                    self._hashes[hash]['dir'],
                    self._hashes[hash]['name'],
                    self._hashes[hash]['type'])

                dbwriter.writerow([file_dir, file_name, file_type, hash])

    def rebuild(self):
        """
            rebuilds the database using the output directory
        """
        walker = walk.WalkForMedia(self._output_dir, ignores=self._inputs)

        for file_dir, file_name, file_type, hash in walker.find_media():
            # remove output dir path + '/'
            file_dir = file_dir[len(self._output_dir)+1:]
            self._hashes[hash] = {'dir': file_dir,
                                      'name': file_name,
                                      'type': file_type}
            logging.info("indexed %s/%s %s %s" % (file_dir,
                                                  file_name,
                                                  file_type,
                                                  hash))

        self.write()

    def is_duplicate(self, photo):

        media_file = MediaFile.build_for(filename)
        hash = media_file.hash()

        if hash in self._hash:

            filename_data = self._hash[hash]
            filename2 = filename_data['dir']+'/'+filename_data['name']

            if media_file.is_equal_to(filename2):
                logging.critical("MD5 hash collision for two different files,"
                                 "handled as dupe: %s %s", filename, filename2)
            return True
        return False

    def add_file(self, filename):
        pass
