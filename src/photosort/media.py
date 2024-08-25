# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import datetime
import filecmp
import hashlib
import logging
import os
import os.path
import shutil
import stat
import sys

from . import exif


class UnknownDatetime(Exception):
    pass


class MediaFile:

    def __init__(self, filename):
        self._filename = filename
        self._file_type = MediaFile.guess_file_type(filename)
        self._hash = None

    @staticmethod
    def guess_file_type(filename):
        extension = filename.lower().split('.')[-1]
        if extension in ('heic', 'jpeg', 'jpg', 'cr2', 'raw', 'png', 'arw',
                         'thm', 'orf'):
            return 'photo'
        elif extension in ('m4v', 'mpeg', 'mpg', 'mov', 'mp4', 'avi'):
            return 'movie'

        return 'unknown'

    @staticmethod
    def build_for(filename):
        return MediaFile(filename)

    def get_filename(self):
        return os.path.basename(self._filename)

    def get_directory(self):
        return os.path.dirname(self._filename)

    def get_path(self):
        return self._filename

    def md5_hash(self, hasher=None, blocksize=65536):
        if self._hash is not None:
            return self._hash

        if hasher is None:
            hasher = hashlib.md5()

        with open(self._filename, 'rb') as afile:
            buf = afile.read(blocksize)
            while len(buf) > 0:
                hasher.update(buf)
                buf = afile.read(blocksize)

            self._hash = hasher.hexdigest()
            return self._hash

    def _exif_data(self):
        """Returns a dictionary from the exif data of an image. """
        return exif.get_metadata(self._filename)

    def _exif_datetime(self):
        exif_datetime_str = ""

        exif_data = self._exif_data()

        for exif_tag in ['EXIF:DateTimeOriginal',
                         'EXIF:DateTimeDigitized',
                         'EXIF:CreateDate',
                         'XMP-exif:DateTimeDigitized',
                         'QuickTime:ContentCreateDate',
                         'QuickTime:CreationDate',
                         'QuickTime:CreateDate',
                         'MediaCreateDate',
                         'TrackCreateDate',
                         'CreateDate',
                         ]:
            try:
                exif_datetime_str = exif_data[exif_tag]
            except KeyError:
                continue
            except IOError as e:
                if str(e) == "not enough data":
                    return None
                if str(e) == "cannot identify image file":
                    return None
                else:
                    raise
            except ValueError:
                return None  # time data '0000:00:00 00:00:00'
            # only reached if the datetime information properly obtained
            logging.debug("photo date and time obtained from: %s", exif_tag)
            break

        if exif_datetime_str == '0000:00:00 00:00:00':
            return None

        if exif_datetime_str:
            return self.parse_exif_datetime(exif_datetime_str)
        else:
            logging.debug("EXIF tag not available for %s", self._filename)
            return None

    @staticmethod
    def parse_exif_datetime(exif_datetime_str):
        try:
            return datetime.datetime.strptime(str(exif_datetime_str),
                                              '%Y:%m:%d %H:%M:%S')
        except UnicodeEncodeError as e:
            if str(e).startswith("'ascii' codec can't encode character"):
                return None
            else:
                raise

        except ValueError:
            # if the string contains the timezone +0100 -0100 +01:00 -01:00
            # extension, strip the ':' and parse with %z
            if '+' in exif_datetime_str:
                parts = exif_datetime_str.split('+')
                parts[1] = parts[1].replace(":", "")
                exif_datetime_str = '+'.join(parts)
            if '-' in exif_datetime_str:
                parts = exif_datetime_str.split('-')
                parts[1] = parts[1].replace(":", "")
                exif_datetime_str = '-'.join(parts)
            return datetime.datetime.strptime(str(exif_datetime_str),
                                              '%Y:%m:%d %H:%M:%S%z')

    def datetime(self):
        dt = self._exif_datetime()
        logging.debug("date and time: %s", dt)
        if dt is None:
            raise UnknownDatetime()

        return dt

    def hash(self):
        """
        Builds an hexadecimal hash for a picture, extended with the
        EXIF date as a string, to prevent as much as possible from md5
        collisions
        """

        media_hash = self.md5_hash()
        exif_datetime = self._exif_datetime()

        if exif_datetime is not None:
            media_hash += " - " + str(exif_datetime)

        return media_hash

    def datetime_file(self):

        ct1 = os.path.getmtime(self._filename)
        ct2 = os.path.getctime(self._filename)

        ct = min(ct1, ct2)  # it can differ from windows to UN*X

        return datetime.datetime.fromtimestamp(ct)

    def __str__(self):

        s = "[%s file hash=%s date=%s]" % (
            self._file_type, self.hash(), self.datetime())
        return s

    def is_equal_to(self, filename):

        try:
            result = filecmp.cmp(self._filename, filename, shallow=True)
            return result
        except OSError:
            logging.info(
                "Comparing to %s, file didn't exist anymore, "
                "erased or moved?", filename)
            return False

    def type(self):
        return self._file_type

    def makedirs_f(self, path, mode):
        paths = os.path.split(path)

        total_path = ''
        for directory in paths:
            total_path = os.path.join(total_path, directory)
            if os.path.isdir(total_path):
                continue

            os.mkdir(total_path, mode | stat.S_IXUSR)

    def rename_as(self, new_filename, file_mode=0o774):

        try:
            self.makedirs_f(os.path.dirname(new_filename), file_mode)
        except OSError as e:
            logging.error("Unable to move: %s (%s)", new_filename, e)
            return False

        try:
            shutil.move(self._filename, new_filename)
            os.chmod(new_filename, file_mode)
        except OSError as e:
            logging.error("Unable to move: %s", e)
            return False

        return True

    def calculate_datetime(self, format):
        dt = self.datetime()
        data = {'year': dt.year, 'month': dt.month, 'day': dt.day,
                'hour': dt.hour, 'minute': dt.minute, 'second': dt.second}

        return format % data

    def locate_output_directory(self, directory, dir_format):
        default = os.path.join(directory, self.calculate_datetime(dir_format))
        parts = os.path.split(default)
        last_dir = parts[-1]
        top_dir = os.path.join(*parts[:-1])
        # try to figure out if a directory with the same pattern and a suffix
        # added by the user exists already (tagged directory support)
        try:
            for item in os.listdir(top_dir):
                file_path = os.path.join(top_dir, item)
                if os.path.isdir(file_path) and item.startswith(last_dir):
                    return file_path
        except FileNotFoundError:
            return default
        return default

    def move_to_directory_with_date(self, directory, dir_format,
                                    file_format='', file_mode=0o774):
        out_dir = None

        try:
            out_dir = self.locate_output_directory(directory, dir_format)
        except UnknownDatetime:
            logging.error("unknown datetime, skipping  %s", self._filename)
            return False

        try:
            os.mkdir(out_dir)
            os.chmod(out_dir, file_mode | stat.S_IXUSR)
        except OSError:
            pass  # it already exists

        if file_format != "":
            file_prefix = self.calculate_datetime(
                file_format) + self.get_filename()
        else:
            file_prefix = self.get_filename()
        new_filename = out_dir + "/" + file_prefix
        logging.info("moving %s to %s", self._filename, new_filename)

        if self.rename_as(new_filename, file_mode):
            self._filename = new_filename
            return True
        else:
            return False


if __name__ == "__main__":
    file = MediaFile.build_for(sys.argv[1])
    print(file)
