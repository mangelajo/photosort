# -*- mode: python; coding: utf-8 -*-
from __future__ import print_function

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

from PIL import Image
from PIL.ExifTags import TAGS

#import exifread
import datetime
import os.path
import sys
import time

import media


class Photo(media.MediaFile):

    def __init__(self, filename):
        media.MediaFile.__init__(self, filename)
        self.__exif_data = None

    #def _exif_data(self):
    #    if self.__exif_data is None:
    #        with open(self._filename, 'r') as f:
    #            self.__exif_data = exifread.process_file(f)
    #
    #    return self.__exif_data

    def _exif_data(self):
        """Returns a dictionary from the exif data of an
         PIL Image item. """
        self.__exif_data = {}
        image = Image.open(self._filename)
        info = image._getexif()
        if info:
            for tag, value in info.items():
                decoded = TAGS.get(tag, tag)
                self.__exif_data[decoded] = value

        return self.__exif_data

    def _exif_datetime(self):

        try:
            exif_datetime_str = self._exif_data()['DateTimeDigitized']
            return datetime.datetime.strptime(str(exif_datetime_str),
                                              '%Y:%m:%d %H:%M:%S')
        except KeyError:
            return None
        except IOError as e:

            if str(e) == "not enough data":
                return None
            if str(e) == "cannot identify image file":
                return None
            else:
                raise
        except ValueError:
            return None  # time data '0000:00:00 00:00:00'

    def datetime(self):
        dt = self._exif_datetime()
        if dt is None:
            dt = MediaFile.datetime()

        return dt

    def hash(self):
        media_hash = media.MediaFile.hash(self)
        exif_datetime = self._exif_datetime()

        if exif_datetime is not None:
            media_hash += " - " + str(exif_datetime)

        return media_hash

    def __str__(self):
        s = "[Photo file hash=%s]" % (self.hash())
        return s


if __name__ == "__main__":
    photo = Photo(sys.argv[1])
    print(photo)
