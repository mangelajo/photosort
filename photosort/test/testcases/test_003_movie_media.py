# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import os
import shutil
import stat
import time

import photosort.test as test
from photosort import media


class TestMovieMedia(test.TestCase):

    def setUp(self):
        super(TestMovieMedia, self).setUp()
        self.mov1 = self.get_data_path('media2/mov1.mp4')
        self.mov1dup = self.get_data_path('media2/mov1_dup.mp4')
        self.mov1_mtime = os.path.getmtime(self.mov1)
        self.movie = media.MediaFile.build_for(self.mov1)

    def test_hash_creation(self):
        expected_hash = "d41d8cd98f00b204e9800998ecf8427e"
        self.assertEqual(self.movie.hash(), expected_hash)

        # check for hasher non being re-started
        same_movie = media.MediaFile.build_for(self.mov1)
        self.assertEqual(same_movie.hash(), expected_hash)

    def test_datetime(self):
        mtime = time.localtime(self.mov1_mtime)
        expected_datetime = time.strftime(
            "%Y-%m-%d %H:%M:%S", mtime)  # it must come from exif data

        self.assertIn(expected_datetime, str(self.movie.datetime()))

    def test_equal_checking(self):
        self.assertTrue(self.movie.is_equal_to(self.mov1dup))

    def test_datatime_dir(self):
        mtime = time.localtime(self.mov1_mtime)
        year = "%d" % mtime[0]
        month = "%02d" % mtime[1]
        day = "%02d" % mtime[2]

        dir_fmt = '%(year)d/%(year)04d_%(month)02d_%(day)02d'
        dir_str = self.movie.calculate_datetime(dir_fmt)
        expected_dir = os.path.join(year, year + '_' + month + '_' + day)
        self.assertEqual(dir_str, expected_dir)

    def test_get_filename(self):
        self.assertEqual(self.movie.get_filename(), 'mov1.mp4')

    def test_rename(self):

        tmpfile = self._temp_dir + '/' + self.movie.get_filename()
        tmpfile_renamed = self._temp_dir + '/R' + self.movie.get_filename()
        tmpfile_mode = 0o666

        shutil.copy(self.movie.get_path(), tmpfile)

        movie_t = media.MediaFile.build_for(tmpfile)

        movie_t.rename_as(tmpfile_renamed, tmpfile_mode)
        self.assertTrue(self.movie.is_equal_to(tmpfile_renamed))

        file_mode = os.stat(tmpfile_renamed)[stat.ST_MODE] & 0o777
        self.assertEqual(file_mode, tmpfile_mode)

    def test_move_to_directory(self):
        tmpfile = self._temp_dir + '/' + self.movie.get_filename()
        dir_fmt = '%(year)d/%(year)04d_%(month)02d_%(day)02d'
        file_fmt = "%(year)04d%(month)02d%(day)02d%(hour)02" \
            "d%(minute)02d%(second)02d_"

        shutil.copy(self.movie.get_path(), tmpfile)
        mov_mtime = os.path.getmtime(tmpfile)
        mtime = time.localtime(mov_mtime)
        year = "%d" % mtime[0]
        month = "%02d" % mtime[1]
        day = "%02d" % mtime[2]
        hour = "%02d" % mtime[3]
        minute = "%02d" % mtime[4]
        second = "%02d" % mtime[5]
        movie_t = media.MediaFile.build_for(tmpfile)

        shutil.rmtree(self._temp_dir + '/' + year, ignore_errors=True)
        movie_t.move_to_directory_with_date(self._temp_dir, dir_fmt)

        expected_filename = os.path.join(
            self._temp_dir, year, year + '_' + month + '_' + day, 'mov1.mp4')
        self.assertTrue(self.movie.is_equal_to(expected_filename))

        shutil.copy(self.movie.get_path(), tmpfile)
        mov_mtime = os.path.getmtime(tmpfile)
        mtime = time.localtime(mov_mtime)
        year = "%d" % mtime[0]
        month = "%02d" % mtime[1]
        day = "%02d" % mtime[2]
        hour = "%02d" % mtime[3]
        minute = "%02d" % mtime[4]
        second = "%02d" % mtime[5]
        movie_t = media.MediaFile.build_for(tmpfile)

        shutil.rmtree(self._temp_dir + '/' + year, ignore_errors=True)
        movie_t.move_to_directory_with_date(self._temp_dir, dir_fmt, file_fmt)

        expected_filename = os.path.join(
            self._temp_dir, year, year + '_' + month + '_' + day,
            year + month + day + hour + minute + second + '_mov1.mp4')
        self.assertTrue(self.movie.is_equal_to(expected_filename))


if __name__ == '__main__':
    test.test.main()
