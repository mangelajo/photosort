# -*- mode: python; coding: utf-8 -*-
from __future__ import print_function

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import fcntl
import logging
import os
import time

from photosort import media


class WalkForMedia:
    """
        A simple class to walk for JPEGs over a root dir
    """

    def __init__(self, rootdir, ignores=[], extensions=[]):
        self._rootdir = rootdir
        self._ignores = ignores
        self._extensions = extensions
        self._fs_time_skew = self._fs_timeskew_to(rootdir)

    def _fs_timeskew_to(self, rootdir):
        """
        discover the remote filesystem time skew with local datetime
        this could be handled by ntp syncing all nodes, but we
        can't have a guarantee on this
        """
        f_name = os.path.join(rootdir, ".timesync")
        with open(f_name, 'w') as f:
            f.write("touch!")

        ct1 = os.path.getmtime(f_name)
        ct2 = os.path.getctime(f_name)

        os.remove(f_name)  # cleanup the file

        # it can differ from windows to UN*X
        ct = max(ct1, ct2)

        now = time.mktime(time.gmtime())

        return ct - now  # remote-local

    def _modification_lapse(self, filename):
        """
        return the lapse from last file modification (in seconds)
        """
        ct1 = os.path.getmtime(filename)
        ct2 = os.path.getctime(filename)

        # it can differ from windows to UN*X
        ct = max(ct1, ct2)

        now = time.mktime(time.gmtime())

        return now - ct + self._fs_time_skew

    def _file_is_growing(self, filename):
        size1 = os.path.getsize(filename)
        time.sleep(2)
        size2 = os.path.getsize(filename)

        if size2 > size1:
            logging.debug("%s size1<2 = %d<%d", filename, size1, size2)

        return size2 > size1

    def _file_is_empty(self, filename):
        return os.path.getsize(filename) == 0

    def _file_is_locked(self, filename):
        try:
            with open(filename, 'r') as file:
                fcntl.flock(file.fileno(), fcntl.LOCK_EX)
                fcntl.flock(file.fileno(), fcntl.LOCK_UN)
        except IOError as e:
            logging.debug("%s seems to be locked or gone (%s)", filename, e)
            return True
        return False  # we were able to lock/unlock, so nobody must be writing

    def _file_is_ready(self, filename):
        # we have a bunch of extra checks to avoid files
        # that are yet incomplete from being moved around

        if self._file_is_locked(filename):
            logging.debug("file %s not ready because it's locked", filename)
            return False

        # skip files that were modified in the last 30 seconds

        mod_lapse = self._modification_lapse(filename)

        if mod_lapse < 30:
            logging.debug("file %s not ready because modification "
                          "lapse is %d, it's probably copying yet",
                          filename, mod_lapse)
            return False

        # skip growing or empty files

        # skip this check, as it's a major slowdown, and lapse seems to work
        # if self._file_is_growing(filename):
        #     logging.debug("file %s not ready because it's growing"
        #                  % filename )
        #     return False

        if self._file_is_empty(filename):
            logging.debug("file %s not ready because it's empty", filename)
            return False

        return True

    def find_media(self):

        if not os.path.isdir(self._rootdir):
            logging.error("%s does not exists or it's not mounted, "
                         "cannot find media", self._rootdir)
            return

        if os.path.split(self._rootdir)[-1].startswith('.'):
            logging.info("%s is a hidden directory => ignoring", self._rootdir)
            return

        if self._rootdir in self._ignores:
            logging.info("%s in the list to be ignored => ignoring",
                         self._rootdir)
            return

        for root, subFolders, files in os.walk(self._rootdir):

            subFolders[:] = [
                sf for sf in subFolders
                if not sf.startswith('.') and sf not in self._ignores]

            for file in files:

                file_path = os.path.join(root, file)

                # skip mac osx AppleDouble files (it puts a ._ in front of the
                # name) to keep extra information

                if file.startswith('.'):
                    continue

                media_file = media.MediaFile.build_for(file_path)
                file_type = media_file.type()

                if file_type != 'unknown':
                    if self._file_is_ready(file_path):
                        yield [root, file]
