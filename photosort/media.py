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


class MediaFile:

    def __init__(self, filename):
        self._filename = filename
        self._file_type = MediaFile.guess_file_type(filename)
        self._hash = None

    @staticmethod
    def guess_file_type(filename):

        extension = filename.lower().split('.')[-1]
        if extension in (
                'jpeg', 'jpg', 'cr2', 'raw', 'png', 'arw', 'thm', 'orf'):
            return 'photo'
        if extension in ('m4v','mpeg', 'mpg', 'mov', 'mp4', 'avi'):
            return 'movie'
        return 'unknown'

    @staticmethod
    def build_for(filename):

        file_type = MediaFile.guess_file_type(filename)
        if file_type == 'photo':
            from photosort import \
                photo  # delayed import to avoid circular dependencies
            return photo.Photo(filename)
        else:
            return MediaFile(filename)

    def get_filename(self):
        return os.path.basename(self._filename)

    def get_directory(self):
        return os.path.dirname(self._filename)

    def get_path(self):
        return self._filename

    def hash(self, hasher=None, blocksize=65536):
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

    def datetime(self):

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

        out_dir = self.locate_output_directory(directory, dir_format)

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
