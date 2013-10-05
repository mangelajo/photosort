# -*- mode: python; coding: utf-8 -*-
from __future__ import print_function


__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import csv
import logging
import os.path


import walk
import media

class PhotoDB:
    def __init__(self, config):

        self._db_file = config.db_file()
        self._output_dir = config.output_dir()
        self._duplicates_dir = config.duplicates_dir()
        self._dir_pattern = config.dir_pattern()
        self._inputs = (config.sources()[source]['dir']
                        for source in config.sources().keys())
        self._file_mode = config.output_chmod()
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
        except IOError as e:
            logging.error("Error opening db file %s" % self._db_file)
            if e.errno!=2:
                raise

    def write(self):

        try:
            os.remove(self._db_file+".bak")
        except:
            pass

        try:
            os.rename(self._db_file, self._db_file+".bak",self._file_mode)
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

    def _add_to_db(self, file_dir, file_name, media_file):
        try:
            hash = media_file.hash()
        except IOError as e:
            logging.error("IOError %s trying to hash %s" %
                          (e,media_file.get_path()))
            return False

        file_type = media_file.type()

        # remove output dir path + '/'
        file_dir = file_dir[len(self._output_dir) + 1:]
        self._hashes[hash] = {'dir': file_dir,
                              'name': file_name,
                              'type': file_type}

        logging.info("indexed %s/%s %s %s" % (file_dir,
                                              file_name,
                                              file_type,
                                              hash))
        return True


    def rebuild(self):
        """
            rebuilds the database using the output directory
        """
        walker = walk.WalkForMedia(self._output_dir, ignores=self._inputs)

        for file_dir, file_name in walker.find_media():

            try:
                media_file = media.MediaFile.build_for(
                                os.path.join(file_dir, file_name)
                             )

                self._add_to_db(file_dir, file_name, media_file)
            except:
                logging.critical("Unexpected error: %s" % (sys.exc_info()[0]))
        self.write()

    def is_duplicate(self, media_file):

        hash = media_file.hash()

        if hash in self._hashes:

            filename_data = self._hashes[hash]
            filename2 = self._output_dir + "/" + filename_data['dir']+'/'+filename_data['name']

            if not media_file.is_equal_to(filename2):
                logging.critical("MD5 hash collision for two different files,"
                                 "handled as dupe: %s %s", media_file.get_path(), filename2)

            logging.info("%s was detected as duplicate with %s" % (media_file.get_path(), filename2) )

            return True
        return False



    def add_file(self, filename):

        media_file = media.MediaFile.build_for(filename)

        if self.is_duplicate(media_file):

            file = media_file.get_filename()
            duplicates_path = os.path.join(self._duplicates_dir,file)

            logging.info(" moving to duplicates: %s" %
                         duplicates_path)

            media_file.rename_as(duplicates_path,self._file_mode)

        else:
            if media_file.move_to_directory_with_date(self._output_dir,
                                                 self._dir_pattern,
                                                 self._file_mode):
                self._add_to_db(media_file.get_directory(), media_file.get_filename(), media_file)
                self.write()
