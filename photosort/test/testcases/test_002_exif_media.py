# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import os
import shutil
import stat

from photosort.test import test as test_main
from photosort import test
from photosort import media

TEST_DIR_FMT = '%(year)d/%(year)04d_%(month)02d_%(day)02d'
TEST_FILE_FMT = "%(year)04d%(month)02d%(day)02d%(hour)02d" \
                "%(minute)02d%(second)02d_"


class TestExifMedia(test.TestCase):

    def setUp(self):
        super().setUp()
        self.img1 = self.get_data_path('media1/img1.jpg')
        self.img1dup = self.get_data_path('media1/img1_dup.jpg')
        self.mov_exif = self.get_data_path('media2/mov_exif.m4v')
        self.photo = media.MediaFile.build_for(self.img1)
        self.movie = media.MediaFile.build_for(self.mov_exif)

    def test_hash_creation(self):
        expected_hash = "a35de42abad366d0f6232a4abd0404c8 " \
            "- 2013-08-24 13:05:52"
        self.assertEqual(self.photo.hash(), expected_hash)

        # check for hasher non being re-started
        same_photo = media.MediaFile.build_for(self.img1)
        self.assertEqual(same_photo.hash(), expected_hash)

    def test_datetime(self):
        self.assertEqual(str(self.photo.datetime()), "2013-08-24 13:05:52")
        self.assertEqual(str(self.movie.datetime()),
                         "2020-06-18 07:50:31")

    def test_equal_checking(self):
        self.assertTrue(self.photo.is_equal_to(self.img1dup))

    def test_datatime_dir(self):
        dir_fmt = '%(year)d/%(year)04d_%(month)02d_%(day)02d'
        dir_str = self.photo.calculate_datetime(dir_fmt)
        self.assertEqual(dir_str, "2013/2013_08_24")

    def test_exif_date_parsing(self):
        formats = ["2020:03:08 21:51:41+01:00",
                   "2020:03:08 21:51:41-01:00",
                   "2020:03:08 21:51:41+0100",
                   "2020:03:08 21:51:41-0100",
                   "2020:03:08 21:51:41"]

        for format in formats:
            dt = media.MediaFile.parse_exif_datetime(format)
            self.assertEqual(dt.year, 2020)

    def test_get_filename(self):
        self.assertEqual(self.photo.get_filename(), 'img1.jpg')

    def test_rename(self):
        tmpfile = self._temp_dir + '/' + self.photo.get_filename()
        tmpfile_renamed = self._temp_dir + '/R' + self.photo.get_filename()
        tmpfile_mode = 0o666

        shutil.copy(self.photo.get_path(), tmpfile)

        photo_t = media.MediaFile.build_for(tmpfile)

        photo_t.rename_as(tmpfile_renamed, tmpfile_mode)
        self.assertTrue(self.photo.is_equal_to(tmpfile_renamed))

        file_mode = os.stat(tmpfile_renamed)[stat.ST_MODE] & 0o777
        self.assertEqual(file_mode, tmpfile_mode)

    def test_move_to_directory(self):
        tmpfile = self._temp_dir + '/' + self.photo.get_filename()

        shutil.copy(self.photo.get_path(), tmpfile)
        photo_t = media.MediaFile.build_for(tmpfile)

        shutil.rmtree(self._temp_dir + '/2013', ignore_errors=True)
        photo_t.move_to_directory_with_date(self._temp_dir, TEST_DIR_FMT)

        self.assertTrue(self.photo.is_equal_to(
            self._temp_dir + '/2013/2013_08_24/img1.jpg'))

        shutil.copy(self.photo.get_path(), tmpfile)
        photo_t = media.MediaFile.build_for(tmpfile)

        shutil.rmtree(self._temp_dir + '/2013', ignore_errors=True)
        photo_t.move_to_directory_with_date(self._temp_dir, TEST_DIR_FMT,
                                            TEST_FILE_FMT)

        self.assertTrue(self.photo.is_equal_to(
            self._temp_dir + '/2013/2013_08_24/20130824130552_img1.jpg'))

    def test_move_to_existing_directory_pattern(self):
        tmpfile = self._temp_dir + '/' + self.photo.get_filename()

        shutil.copy(self.photo.get_path(), tmpfile)
        photo_t = media.MediaFile.build_for(tmpfile)

        shutil.rmtree(self._temp_dir + '/2013', ignore_errors=True)

        default_dir = photo_t.locate_output_directory(self._temp_dir,
                                                      TEST_DIR_FMT)
        default_dir_tagged = default_dir + "_tagged_with_something"
        os.makedirs(default_dir_tagged)
        # after renaming an existing directory, it should figure out and
        # use that one destination
        self.assertEqual(default_dir_tagged,
                         photo_t.locate_output_directory(self._temp_dir,
                                                         TEST_DIR_FMT))

        photo_t.move_to_directory_with_date(self._temp_dir, TEST_DIR_FMT)

        self.assertTrue(self.photo.is_equal_to(
            self._temp_dir + '/2013/2013_08_24_tagged_with_something/img1.jpg')
        )

    def test_move_to_existing_directory_pattern_file_fmt(self):

        tmpfile = self._temp_dir + '/' + self.photo.get_filename()
        shutil.copy(self.photo.get_path(), tmpfile)
        photo_t = media.MediaFile.build_for(tmpfile)

        default_dir = photo_t.locate_output_directory(self._temp_dir,
                                                      TEST_DIR_FMT)
        default_dir_tagged = default_dir + "_tagged_with_something"
        os.makedirs(default_dir_tagged)
        photo_t.move_to_directory_with_date(self._temp_dir, TEST_DIR_FMT,
                                            TEST_FILE_FMT)

        file_path = os.path.join(self._temp_dir,
                                 '2013',
                                 '2013_08_24_tagged_with_something',
                                 '20130824130552_img1.jpg')
        self.assertTrue(self.photo.is_equal_to(file_path))


if __name__ == '__main__':
    test_main.main()
