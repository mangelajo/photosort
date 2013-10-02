# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"


import exceptions

import os
import logging

from media import MediaFile


class WalkForMedia:
    """
        A simple class to walk for JPEGs over a root dir
    """
    def __init__(self, rootdir, ignores=[], extensions=[]):
        self._rootdir = rootdir
        self._ignores = ignores
        self._extensions = extensions

    def find_media(self):

        if not os.path.isdir(self._rootdir):
            raise exceptions.DirError(
                self._rootdir,
                "Does not exists or it's not mounted, cannot find media")

        for root, subFolders, files in os.walk(self._rootdir):

            # if last directory starts with "." ignore it (.thumbnails, etc...)
            if os.path.split(root)[-1].startswith('.'):
                continue

            # check if we have directories to ignore
            skip = False
            for ignore in self._ignores:
                if root.startswith(ignore):
                    skip = True

            if skip:
                continue

            for file in files:

                file_path = os.path.join(root, file)
                media_file = MediaFile.build_for(file_path)
                file_type = media_file.type()

                if file_type != 'unknown':
                    logging.debug("hashing: %s/%s" % (root, file))
                    yield [root, file]
