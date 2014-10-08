# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import photosort.test
from photosort import media
import shutil
import tempfile
import os
import stat

class TestPhotoMedia(photosort.test.TestCase):

    def setUp(self):
        self.img1 = self.get_data_path('media1/img1.jpg')
        self.img1dup = self.get_data_path('media1/img1_dup.jpg')
        self.photo = media.MediaFile.build_for(self.img1)
        
    def test_hash_creation(self):
        expected_hash = "a35de42abad366d0f6232a4abd0404c8 - 2013-08-24 13:05:52"
        self.assertEqual(self.photo.hash(),expected_hash)

        # check for hasher non being re-started
        same_photo = media.MediaFile.build_for(self.img1)
        self.assertEqual(same_photo.hash(),expected_hash)

    def test_datetime(self):
        expected_datetime = "2013-08-24 13:05:52" # it must come from exif data

        self.assertEqual(str(self.photo.datetime()),expected_datetime)

    def test_equal_checking(self):
        self.assertTrue(self.photo.is_equal_to(self.img1dup))

    def test_datatime_dir(self):
        dir_fmt = '%(year)d/%(year)04d_%(month)02d_%(day)02d'
        dir_str = self.photo.calculate_datetime(dir_fmt)
        self.assertEqual(dir_str,"2013/2013_08_24")

    def test_get_filename(self):
        self.assertEqual(self.photo.get_filename(),'img1.jpg')

    def test_rename(self):
        tmpdir = tempfile.gettempdir()
        tmpfile = tmpdir + '/' + self.photo.get_filename()
        tmpfile_renamed = tmpdir + '/R' + self.photo.get_filename()
        tmpfile_mode = 0o666

        shutil.copy(self.photo.get_path(), tmpfile)

        photo_t = media.MediaFile.build_for(tmpfile)

        photo_t.rename_as(tmpfile_renamed,tmpfile_mode)
        self.assertTrue(self.photo.is_equal_to(tmpfile_renamed))

        file_mode = os.stat(tmpfile_renamed)[stat.ST_MODE] & 0o777
        self.assertEqual(file_mode,tmpfile_mode)

    def test_move_to_directory(self):
        tmpdir = tempfile.gettempdir()
        tmpfile = tmpdir + '/' + self.photo.get_filename()
        dir_fmt = '%(year)d/%(year)04d_%(month)02d_%(day)02d'
        file_fmt = '%(year)04d%(month)02d%(day)02d%(hour)02d%(minute)02d%(second)02d_'

        shutil.copy(self.photo.get_path(), tmpfile)
        photo_t = media.MediaFile.build_for(tmpfile)

        shutil.rmtree(tmpdir+'/2013',ignore_errors=True)
        photo_t.move_to_directory_with_date(tmpdir,dir_fmt)

        self.assertTrue(self.photo.is_equal_to(tmpdir+'/2013/2013_08_24/img1.jpg'))

        shutil.copy(self.photo.get_path(), tmpfile)
        photo_t = media.MediaFile.build_for(tmpfile)

        shutil.rmtree(tmpdir+'/2013',ignore_errors=True)
        photo_t.move_to_directory_with_date(tmpdir,dir_fmt, file_fmt)

        self.assertTrue(self.photo.is_equal_to(tmpdir+'/2013/2013_08_24/20130824130552_img1.jpg'))

if __name__ == '__main__':
    unittest.main()
   
