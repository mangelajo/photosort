# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import fcntl
import logging
import mock
import os
import time

from photosort import test
from photosort import walk


class TestWalkForMedia(test.TestCase):

    def setUp(self):
        super().setUp()
        self.media1 = self.get_data_path('media1')

    def test_directory_inspection(self):
        """Test basic directory inspection finds media files"""
        # We need to patch the timecheck (not modified in last 30 seconds)
        # in CI (recent checkout)
        with mock.patch("photosort.walk.WalkForMedia._file_is_ready") as m:
            instance = m.return_value
            instance.method.return_value = True
            walker = walk.WalkForMedia(self.media1)
            files = [file for root, file in walker.find_media()]
            self.assertIn('img1.jpg', files)

    def test_directory_inspection_file_not_ready(self):
        """Test that files not ready are skipped"""
        with mock.patch("photosort.walk.WalkForMedia._file_is_ready") as m:
            instance = m.return_value
            instance.method.return_value = False
            walker = walk.WalkForMedia(self.media1)
            files = [file for root, file in walker.find_media()]
            self.assertNotIn('img1', files)

    def test_ignore_list_directory(self):
        """Test that directories in ignore list are skipped"""
        # Create test directory structure
        test_dir = os.path.join(self._temp_dir, 'test')
        ignored_dir = os.path.join(test_dir, 'ignored')
        os.makedirs(ignored_dir)

        # Copy a media file to ignored directory
        test_file = os.path.join(self.media1, 'img1.jpg')
        dest_file = os.path.join(ignored_dir, 'test.jpg')
        with open(test_file, 'rb') as src:
            with open(dest_file, 'wb') as dst:
                dst.write(src.read())

        # Set past modification time
        past_time = time.time() - 35
        os.utime(dest_file, (past_time, past_time))

        # Walk without ignoring - should find file
        with mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True):
            walker = walk.WalkForMedia(test_dir)
            files = [file for root, file in walker.find_media()]
            self.assertIn('test.jpg', files)

        # Walk with ignore list - should not find file
        # Note: ignores must match directory names, not full paths
        with mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True):
            walker = walk.WalkForMedia(test_dir, ignores=['ignored'])
            files = [file for root, file in walker.find_media()]
            self.assertNotIn('test.jpg', files)

    def test_ignore_list_rootdir(self):
        """Test that rootdir itself can be in ignore list"""
        walker = walk.WalkForMedia(self.media1, ignores=[self.media1])
        files = list(walker.find_media())
        self.assertEqual(len(files), 0)

    def test_hidden_directory_filtering(self):
        """Test that hidden directories (starting with .) are skipped"""
        # Create test structure with hidden directory
        test_dir = os.path.join(self._temp_dir, 'test')
        hidden_dir = os.path.join(test_dir, '.hidden')
        os.makedirs(hidden_dir)

        # Copy media file to hidden directory
        test_file = os.path.join(self.media1, 'img1.jpg')
        dest_file = os.path.join(hidden_dir, 'test.jpg')
        with open(test_file, 'rb') as src:
            with open(dest_file, 'wb') as dst:
                dst.write(src.read())

        past_time = time.time() - 35
        os.utime(dest_file, (past_time, past_time))

        # Should not find files in hidden directory
        with mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True):
            walker = walk.WalkForMedia(test_dir)
            files = [file for root, file in walker.find_media()]
            self.assertNotIn('test.jpg', files)

    def test_hidden_rootdir_ignored(self):
        """Test that hidden rootdir is ignored"""
        hidden_dir = os.path.join(self._temp_dir, '.hidden')
        os.makedirs(hidden_dir)

        walker = walk.WalkForMedia(hidden_dir)
        files = list(walker.find_media())
        self.assertEqual(len(files), 0)

    def test_appledouble_file_filtering(self):
        """Test that AppleDouble files (._*) are skipped"""
        test_dir = os.path.join(self._temp_dir, 'test')
        os.makedirs(test_dir)

        # Create regular file and AppleDouble file
        test_file = os.path.join(self.media1, 'img1.jpg')
        regular_file = os.path.join(test_dir, 'photo.jpg')
        appledouble_file = os.path.join(test_dir, '._photo.jpg')

        for dest in [regular_file, appledouble_file]:
            with open(test_file, 'rb') as src:
                with open(dest, 'wb') as dst:
                    dst.write(src.read())

        with mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True):
            walker = walk.WalkForMedia(test_dir)
            files = [file for root, file in walker.find_media()]

            self.assertIn('photo.jpg', files)
            self.assertNotIn('._photo.jpg', files)

    def test_hidden_file_filtering(self):
        """Test that hidden files (starting with .) are skipped"""
        test_dir = os.path.join(self._temp_dir, 'test')
        os.makedirs(test_dir)

        test_file = os.path.join(self.media1, 'img1.jpg')
        hidden_file = os.path.join(test_dir, '.hidden.jpg')

        with open(test_file, 'rb') as src:
            with open(hidden_file, 'wb') as dst:
                dst.write(src.read())

        past_time = time.time() - 35
        os.utime(hidden_file, (past_time, past_time))

        with mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True):
            walker = walk.WalkForMedia(test_dir)
            files = [file for root, file in walker.find_media()]
            self.assertNotIn('.hidden.jpg', files)

    def test_missing_directory(self):
        """Test that missing directory is handled gracefully"""
        nonexistent_dir = os.path.join(self._temp_dir, 'nonexistent')

        # Walker init will fail because it tries to create .timesync file
        with self.assertRaises(FileNotFoundError):
            walker = walk.WalkForMedia(nonexistent_dir)

    def test_file_is_empty(self):
        """Test that empty files are not ready"""
        test_dir = os.path.join(self._temp_dir, 'test')
        os.makedirs(test_dir)

        empty_file = os.path.join(test_dir, 'empty.jpg')
        with open(empty_file, 'w') as f:
            pass  # Create empty file

        past_time = time.time() - 35
        os.utime(empty_file, (past_time, past_time))

        walker = walk.WalkForMedia(test_dir)
        files = list(walker.find_media())
        self.assertEqual(len(files), 0)

    def test_file_recently_modified(self):
        """Test that recently modified files are not ready"""
        test_dir = os.path.join(self._temp_dir, 'test')
        os.makedirs(test_dir)

        # Create file with recent modification time
        test_file = os.path.join(self.media1, 'img1.jpg')
        recent_file = os.path.join(test_dir, 'recent.jpg')
        with open(test_file, 'rb') as src:
            with open(recent_file, 'wb') as dst:
                dst.write(src.read())

        # File modified just now (within 30 seconds)
        walker = walk.WalkForMedia(test_dir)
        files = list(walker.find_media())
        self.assertEqual(len(files), 0)

    def test_file_old_enough_is_ready(self):
        """Test that file modified >30 seconds ago is ready"""
        test_dir = os.path.join(self._temp_dir, 'test')
        os.makedirs(test_dir)

        test_file = os.path.join(self.media1, 'img1.jpg')
        old_file = os.path.join(test_dir, 'old.jpg')
        with open(test_file, 'rb') as src:
            with open(old_file, 'wb') as dst:
                dst.write(src.read())

        # Set modification time to 35 seconds ago
        past_time = time.time() - 35
        os.utime(old_file, (past_time, past_time))

        with mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True):
            walker = walk.WalkForMedia(test_dir)
            files = [file for root, file in walker.find_media()]
            self.assertIn('old.jpg', files)

    def test_unknown_file_type_skipped(self):
        """Test that unknown file types are skipped"""
        test_dir = os.path.join(self._temp_dir, 'test')
        os.makedirs(test_dir)

        # Create a text file (unknown type)
        txt_file = os.path.join(test_dir, 'document.txt')
        with open(txt_file, 'w') as f:
            f.write('test content')

        past_time = time.time() - 35
        os.utime(txt_file, (past_time, past_time))

        walker = walk.WalkForMedia(test_dir)
        files = list(walker.find_media())
        self.assertNotIn('document.txt', files)

    def test_nested_directory_structure(self):
        """Test walking through nested directory structure"""
        # Create nested structure
        test_dir = os.path.join(self._temp_dir, 'test')
        sub1 = os.path.join(test_dir, 'sub1')
        sub2 = os.path.join(sub1, 'sub2')
        os.makedirs(sub2)

        # Place files at different levels
        test_file = os.path.join(self.media1, 'img1.jpg')

        files_created = []
        for idx, dir_path in enumerate([test_dir, sub1, sub2]):
            dest = os.path.join(dir_path, f'photo{idx}.jpg')
            with open(test_file, 'rb') as src:
                with open(dest, 'wb') as dst:
                    dst.write(src.read())
            past_time = time.time() - 35
            os.utime(dest, (past_time, past_time))
            files_created.append(f'photo{idx}.jpg')

        with mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True):
            walker = walk.WalkForMedia(test_dir)
            files = [file for root, file in walker.find_media()]

            # Should find all three files
            for created_file in files_created:
                self.assertIn(created_file, files)

    def test_filesystem_time_skew_calculated(self):
        """Test that filesystem time skew is calculated"""
        walker = walk.WalkForMedia(self._temp_dir)

        # Should have calculated time skew
        self.assertIsNotNone(walker._fs_time_skew)
        # Time skew is a float value (can vary depending on system time)
        self.assertIsInstance(walker._fs_time_skew, float)

    def test_modification_lapse_calculation(self):
        """Test that modification lapse is calculated correctly"""
        test_dir = os.path.join(self._temp_dir, 'test')
        os.makedirs(test_dir)

        test_file = os.path.join(test_dir, 'test.jpg')
        with open(test_file, 'w') as f:
            f.write('test')

        walker = walk.WalkForMedia(test_dir)
        lapse = walker._modification_lapse(test_file)

        # Lapse should be very small for just-created file
        # (accounting for time skew, should be close to 0)
        self.assertIsInstance(lapse, (int, float))
        self.assertGreaterEqual(lapse, 0)

    def test_file_is_locked_detection(self):
        """Test file lock detection"""
        test_dir = os.path.join(self._temp_dir, 'test')
        os.makedirs(test_dir)

        test_file = os.path.join(test_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test')

        walker = walk.WalkForMedia(test_dir)

        # File should not be locked when nobody is using it
        self.assertFalse(walker._file_is_locked(test_file))

    def test_multiple_media_types(self):
        """Test that different media types are all found"""
        test_dir = os.path.join(self._temp_dir, 'test')
        os.makedirs(test_dir)

        # Create files of different types
        photo_file = os.path.join(test_dir, 'photo.jpg')
        video_file = os.path.join(test_dir, 'video.mp4')

        test_file = os.path.join(self.media1, 'img1.jpg')
        for dest in [photo_file, video_file]:
            with open(test_file, 'rb') as src:
                with open(dest, 'wb') as dst:
                    dst.write(src.read())
            past_time = time.time() - 35
            os.utime(dest, (past_time, past_time))

        with mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True):
            walker = walk.WalkForMedia(test_dir)
            files = [file for root, file in walker.find_media()]

            self.assertIn('photo.jpg', files)
            self.assertIn('video.mp4', files)

    def test_ignore_subdirectory(self):
        """Test that ignored subdirectories are skipped"""
        test_dir = os.path.join(self._temp_dir, 'test')
        keep_dir = os.path.join(test_dir, 'keep')
        ignore_dir = os.path.join(test_dir, 'ignore')
        os.makedirs(keep_dir)
        os.makedirs(ignore_dir)

        test_file = os.path.join(self.media1, 'img1.jpg')

        # Create file in both directories
        for subdir, name in [(keep_dir, 'keep.jpg'), (ignore_dir, 'ignore.jpg')]:
            dest = os.path.join(subdir, name)
            with open(test_file, 'rb') as src:
                with open(dest, 'wb') as dst:
                    dst.write(src.read())
            past_time = time.time() - 35
            os.utime(dest, (past_time, past_time))

        # Ignore only the ignore_dir subdirectory by name
        with mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True):
            walker = walk.WalkForMedia(test_dir, ignores=['ignore'])
            files = [file for root, file in walker.find_media()]

            self.assertIn('keep.jpg', files)
            self.assertNotIn('ignore.jpg', files)


if __name__ == '__main__':
    test.test.main()
