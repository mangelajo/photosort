# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"


import exceptions

import hashlib
import os


def md5hashfile(self, filename, hasher=hashlib.md5(), blocksize=65536):
    with open(filename, 'rb') as afile:
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)


class WalkForMedia:
    """
        A simple class to walk for JPEGs over a root dir
    """
    def __init__(self, rootdir, ignores=[], extensions=[]):
        self._rootdir = rootdir
        self._ignores = ignores
        self._extensions = extensions

        return hasher

    def _guess_file_type(self, extension):
        if extension in ('jpeg', 'jpg'):
            return 'picture'
        if extension in ('mpeg', 'mpg', 'mov'):
            return 'movie'
        return 'unknown'

    def find_media(self):

        if not os.path.isdir(self._rootdir):
            raise exceptions.DirError(
                self._rootdir,
                "Does not exists or it's not mounted, cannot find media")

        for root, subFolders, files in os.walk(self._rootdir):

            # if last directory starts with "." ignore it (.thumbnails, etc...)
            if root.split('/')[-1].startswith('.'):
                continue

            # check if we have directories to ignore
            skip = False
            for ignore in self._ignores:
                if root.startswith(ignore):
                    skip = True

            if skip:
                continue

            for file in files:

                extension = file.lower().split('.')[-1]

                file_type = self._guess_file_type(extension)

                if file_type != 'unknown' or extension in self._extensions:

                    file_path = os.path.join(root, file)
                    md5_hash = md5hashfile(file_path).hexdigest()
                    yield [root, file, file_type, md5_hash]
