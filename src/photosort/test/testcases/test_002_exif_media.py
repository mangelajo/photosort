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


    def test_all_photo_extensions(self):
        """Test that all supported photo extensions are recognized"""
        photo_extensions = ['heic', 'jpeg', 'jpg', 'cr2', 'raw', 'png',
                           'arw', 'thm', 'orf']

        for ext in photo_extensions:
            filename = f'test.{ext}'
            file_type = media.MediaFile.guess_file_type(filename)
            self.assertEqual(file_type, 'photo',
                           f'Extension {ext} should be recognized as photo')

    def test_all_video_extensions(self):
        """Test that all supported video extensions are recognized"""
        video_extensions = ['m4v', 'mpeg', 'mpg', 'mov', 'mp4', 'avi']

        for ext in video_extensions:
            filename = f'test.{ext}'
            file_type = media.MediaFile.guess_file_type(filename)
            self.assertEqual(file_type, 'movie',
                           f'Extension {ext} should be recognized as movie')

    def test_unknown_file_extension(self):
        """Test that unknown extensions are handled"""
        unknown_extensions = ['txt', 'pdf', 'doc', 'zip', 'exe', 'unknown']

        for ext in unknown_extensions:
            filename = f'test.{ext}'
            file_type = media.MediaFile.guess_file_type(filename)
            self.assertEqual(file_type, 'unknown',
                           f'Extension {ext} should be unknown')

    def test_case_insensitive_extensions(self):
        """Test that file extensions are case-insensitive"""
        test_cases = [
            ('test.JPG', 'photo'),
            ('test.JPEG', 'photo'),
            ('test.Mp4', 'movie'),
            ('test.AVI', 'movie'),
            ('test.PNG', 'photo'),
        ]

        for filename, expected_type in test_cases:
            file_type = media.MediaFile.guess_file_type(filename)
            self.assertEqual(file_type, expected_type,
                           f'{filename} should be {expected_type}')

    def test_exif_datetime_with_timezone(self):
        """Test parsing EXIF datetime with various timezone formats"""
        test_cases = [
            ("2020:03:08 21:51:41+01:00", 2020, 3, 8),
            ("2020:03:08 21:51:41-01:00", 2020, 3, 8),
            ("2020:03:08 21:51:41+0100", 2020, 3, 8),
            ("2020:03:08 21:51:41-0100", 2020, 3, 8),
        ]

        for datetime_str, year, month, day in test_cases:
            dt = media.MediaFile.parse_exif_datetime(datetime_str)
            self.assertIsNotNone(dt)
            self.assertEqual(dt.year, year)
            self.assertEqual(dt.month, month)
            self.assertEqual(dt.day, day)

    def test_exif_datetime_malformed(self):
        """Test handling of malformed EXIF datetime strings"""
        malformed_dates = [
            "not a date",
            "2020-03-08 21:51:41",  # Wrong separator
            "2020:13:32 25:61:61",  # Invalid values
            "",
            None,
        ]

        for bad_date in malformed_dates:
            if bad_date is None:
                continue
            # Should return None or raise ValueError, not crash
            try:
                result = media.MediaFile.parse_exif_datetime(bad_date)
                # If it returns, it should be None
                self.assertIsNone(result,
                                f'Bad date {bad_date} should return None')
            except ValueError:
                # ValueError is also acceptable
                pass

    def test_exif_zero_datetime(self):
        """Test handling of zero datetime (0000:00:00 00:00:00)"""
        # This is already handled in _exif_datetime method
        # Create a minimal test to verify behavior
        zero_datetime = "0000:00:00 00:00:00"

        # parse_exif_datetime will raise ValueError for this
        with self.assertRaises(ValueError):
            media.MediaFile.parse_exif_datetime(zero_datetime)

    def test_file_comparison_same_file(self):
        """Test comparing a file to itself"""
        self.assertTrue(self.photo.is_equal_to(self.img1))

    def test_file_comparison_different_files(self):
        """Test comparing different files"""
        self.assertFalse(self.photo.is_equal_to(self.mov_exif))

    def test_makedirs_f_single_level(self):
        """Test makedirs_f with single directory level"""
        test_dir = os.path.join(self._temp_dir, 'single')

        self.photo.makedirs_f(test_dir, 0o755)

        self.assertTrue(os.path.isdir(test_dir))
        # Check that directory has execute permission
        dir_stat = os.stat(test_dir)
        self.assertTrue(dir_stat.st_mode & stat.S_IXUSR)

    def test_makedirs_f_with_existing_parent(self):
        """Test makedirs_f creates directory when parent exists"""
        parent_dir = os.path.join(self._temp_dir, 'parent')
        os.makedirs(parent_dir)

        test_dir = os.path.join(parent_dir, 'child')
        self.photo.makedirs_f(test_dir, 0o755)

        self.assertTrue(os.path.isdir(test_dir))

    def test_makedirs_f_already_exists(self):
        """Test makedirs_f when directory already exists"""
        test_dir = os.path.join(self._temp_dir, 'existing')
        os.makedirs(test_dir)

        # Should not raise error
        self.photo.makedirs_f(test_dir, 0o755)

        self.assertTrue(os.path.isdir(test_dir))

    def test_rename_as_creates_parent_directory(self):
        """Test that rename_as creates parent directory (one level)"""
        tmpfile = os.path.join(self._temp_dir, 'source.jpg')
        shutil.copy(self.photo.get_path(), tmpfile)

        photo_t = media.MediaFile.build_for(tmpfile)

        # Rename to path with one missing level
        new_dir = os.path.join(self._temp_dir, 'newdir')
        new_path = os.path.join(new_dir, 'photo.jpg')
        result = photo_t.rename_as(new_path, 0o755)

        self.assertTrue(result)
        self.assertTrue(os.path.exists(new_path))
        self.assertFalse(os.path.exists(tmpfile))
        self.assertTrue(os.path.isdir(new_dir))

    def test_calculate_datetime_all_fields(self):
        """Test calculate_datetime with all available fields"""
        format_str = '%(year)04d-%(month)02d-%(day)02d_%(hour)02d:%(minute)02d:%(second)02d'
        result = self.photo.calculate_datetime(format_str)

        self.assertEqual(result, '2013-08-24_13:05:52')

    def test_calculate_datetime_partial_fields(self):
        """Test calculate_datetime with only some fields"""
        # Just year and month
        result = self.photo.calculate_datetime('%(year)04d-%(month)02d')
        self.assertEqual(result, '2013-08')

        # Just day
        result = self.photo.calculate_datetime('%(day)02d')
        self.assertEqual(result, '24')

    def test_locate_output_directory_nonexistent_parent(self):
        """Test locate_output_directory when parent directory doesn't exist"""
        nonexistent = os.path.join(self._temp_dir, 'nonexistent', 'parent')

        # Should return the default path even if parent doesn't exist
        result = self.photo.locate_output_directory(nonexistent, TEST_DIR_FMT)

        expected = os.path.join(nonexistent, '2013', '2013_08_24')
        self.assertEqual(result, expected)

    def test_hash_includes_exif_datetime(self):
        """Test that hash includes EXIF datetime for uniqueness"""
        # Photo with EXIF should have datetime in hash
        photo_hash = self.photo.hash()
        self.assertIn(' - ', photo_hash)
        self.assertIn('2013-08-24', photo_hash)

        # Movie with EXIF should also have datetime
        movie_hash = self.movie.hash()
        self.assertIn(' - ', movie_hash)
        self.assertIn('2020-06-18', movie_hash)

    def test_get_directory(self):
        """Test get_directory returns correct directory path"""
        directory = self.photo.get_directory()
        self.assertTrue(directory.endswith('media1'))

    def test_get_path(self):
        """Test get_path returns full file path"""
        path = self.photo.get_path()
        self.assertTrue(path.endswith('media1/img1.jpg'))
        self.assertEqual(path, self.img1)

    def test_file_type_property(self):
        """Test type() method returns correct file type"""
        self.assertEqual(self.photo.type(), 'photo')
        self.assertEqual(self.movie.type(), 'movie')

    def test_datetime_file_fallback(self):
        """Test datetime_file returns file system timestamp"""
        import datetime

        dt = self.photo.datetime_file()

        # Should be a datetime object
        self.assertIsInstance(dt, datetime.datetime)
        # Should be a reasonable date (after 2000, before now)
        self.assertGreater(dt.year, 2000)
        self.assertLessEqual(dt.year, datetime.datetime.now().year)

    def test_datetime_file_uses_oldest_timestamp(self):
        """Test that datetime_file() uses min(mtime, ctime)"""
        import datetime
        import time
        import tempfile

        # Create a test file in temp directory
        fd, test_file = tempfile.mkstemp(dir=self._temp_dir, suffix='.jpg')
        os.close(fd)

        # Get initial mtime and ctime
        stat1 = os.stat(test_file)
        initial_mtime = stat1.st_mtime
        initial_ctime = stat1.st_ctime

        # Sleep a bit to ensure time difference
        time.sleep(0.1)

        # Modify the file to update mtime (but not ctime on most systems)
        with open(test_file, 'w') as f:
            f.write("test data")

        # Create MediaFile and get datetime_file
        mf = media.MediaFile.build_for(test_file)
        dt = mf.datetime_file()

        # The datetime should be based on the minimum of mtime/ctime
        stat2 = os.stat(test_file)
        expected_timestamp = min(stat2.st_mtime, stat2.st_ctime)
        expected_dt = datetime.datetime.fromtimestamp(expected_timestamp)

        # They should be very close (within 1 second due to precision)
        time_diff = abs((dt - expected_dt).total_seconds())
        self.assertLess(time_diff, 1.0)

    def test_datetime_with_fallback_enabled_no_exif(self):
        """Test datetime() with fallback_to_file_date=True for file without EXIF"""
        import datetime
        import tempfile

        # Create a file without EXIF data
        fd, test_file = tempfile.mkstemp(dir=self._temp_dir, suffix='.jpg')
        with os.fdopen(fd, 'w') as f:
            f.write("fake image without exif")

        mf = media.MediaFile.build_for(test_file)

        # Without fallback, should raise UnknownDatetime
        with self.assertRaises(media.UnknownDatetime):
            mf.datetime(fallback_to_file_date=False)

        # With fallback, should return file timestamp
        dt = mf.datetime(fallback_to_file_date=True)
        self.assertIsInstance(dt, datetime.datetime)
        self.assertGreater(dt.year, 2000)

    def test_datetime_with_fallback_enabled_has_exif(self):
        """Test datetime() with fallback_to_file_date=True still uses EXIF when available"""
        # When EXIF is available, it should be used regardless of fallback setting
        dt_no_fallback = self.photo.datetime(fallback_to_file_date=False)
        dt_with_fallback = self.photo.datetime(fallback_to_file_date=True)

        # Both should return the same EXIF datetime
        self.assertEqual(dt_no_fallback, dt_with_fallback)
        self.assertEqual(str(dt_no_fallback), "2013-08-24 13:05:52")

    def test_datetime_fallback_default_parameter(self):
        """Test that fallback_to_file_date defaults to False"""
        import tempfile

        # Create a file without EXIF data
        fd, test_file = tempfile.mkstemp(dir=self._temp_dir, suffix='.jpg')
        with os.fdopen(fd, 'w') as f:
            f.write("fake image without exif")

        mf = media.MediaFile.build_for(test_file)

        # Default behavior (no parameter) should raise UnknownDatetime
        with self.assertRaises(media.UnknownDatetime):
            mf.datetime()


if __name__ == '__main__':
    test_main.main()
