# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import hashlib
import sys

class MediaFile:

    def __init__(self, filename):
        self._filename = filename
        self._file_type = MediaFile.guess_file_type(filename)

    @staticmethod
    def guess_file_type(filename):

        extension = filename.lower().split('.')[-1]
        if extension in ('jpeg', 'jpg'):
            return 'photo'
        if extension in ('mpeg', 'mpg', 'mov'):
            return 'movie'
        return 'unknown'

    @staticmethod
    def build_for(filename):

        file_type = MediaFile.guess_file_type(filename)
        if file_type is 'photo':
            import photo
            return photo.Photo(filename)
        else:
            return MediaFile(filename)


    def hash(self, hasher=hashlib.md5(), blocksize=65536):

        with open(self._filename, 'rb') as afile:
            buf = afile.read(blocksize)
            while len(buf) > 0:
                hasher.update(buf)
                buf = afile.read(blocksize)
            return hasher.hexdigest()

    def datetime(self):

        ct = os.path.getctime(self._filename)
        return datetime.datetime.fromtimestamp(ct)

    def __str__(self):
        s = "[Media file hash=%s]" % (self.hash())
        return s

    def is_equal_to(self,filename):
        try:
            return filecmp.cmp(self._filename, filename, shallow=True)
        except IOError:
            return False
    def type(self):
        return self._file_type

if __name__ == "__main__":
    file = MediaFile.build_for(sys.argv[1])
    print(file)