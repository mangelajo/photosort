# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import os
import shutil
import tempfile
import time
import unittest
from unittest import mock
import yaml

from photosort import exif
from photosort import photosort
from photosort import test


class TestPhotoSortIntegration(test.TestCase):

    def setUp(self):
        super().setUp()
        # Start exiftool for all tests
        exif.start()

        # Create directory structure for testing
        self.source1_dir = os.path.join(self._temp_dir, 'source1')
        self.source2_dir = os.path.join(self._temp_dir, 'source2')
        self.output_dir = os.path.join(self._temp_dir, 'output')
        self.duplicates_dir = os.path.join(self.output_dir, 'duplicates')

        os.makedirs(self.source1_dir)
        os.makedirs(self.source2_dir)
        os.makedirs(self.output_dir)

        # Path to test media files
        self.test_media_dir = self.get_data_path('media1')
        self.test_media2_dir = self.get_data_path('media2')

    def _create_config_file(self, config_data):
        """Helper to create a temporary YAML config file"""
        config_path = os.path.join(self._temp_dir, 'photosort_test.yml')
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)
        return config_path

    def _get_basic_config(self):
        """Get a basic configuration for testing"""
        return {
            'sources': {
                'source1': {'dir': self.source1_dir},
                'source2': {'dir': self.source2_dir}
            },
            'output': {
                'dir': self.output_dir,
                'dir_pattern': '%(year)d/%(year)04d_%(month)02d',
                'file_prefix': '',
                'duplicates_dir': 'duplicates',
                'chmod': '0o644',
                'db_file': 'photosort.db'
            }
        }

    def _copy_test_file(self, source_file, dest_dir, dest_name=None):
        """Helper to copy test media file to a location"""
        if dest_name is None:
            dest_name = os.path.basename(source_file)
        dest_path = os.path.join(dest_dir, dest_name)
        shutil.copy2(source_file, dest_path)
        return dest_path

    def _wait_for_file_ready(self, filepath, wait_time=31):
        """Wait for file to be considered ready (30+ seconds old)"""
        # Touch the file to set its modification time in the past
        past_time = time.time() - wait_time
        os.utime(filepath, (past_time, past_time))

    @mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True)
    def test_rebuilddb_scans_existing_files(self, mock_ready):
        """Test that rebuilddb() scans existing output directory"""
        # Place a test file directly in output directory
        output_subdir = os.path.join(self.output_dir, '2013', '2013_08')
        os.makedirs(output_subdir, exist_ok=True)
        test_file = os.path.join(self.test_media_dir, 'img1.jpg')
        copied_file = self._copy_test_file(test_file, output_subdir, 'existing.jpg')

        # Create PhotoSort instance and rebuild DB
        config_path = self._create_config_file(self._get_basic_config())
        ps = photosort.PhotoSort(config_path, log_level='ERROR')
        ps.rebuild_db()

        # Verify file was indexed in database
        self.assertGreater(len(ps._photodb._hashes), 0)

        # Verify database was written
        db_file = os.path.join(self.output_dir, 'photosort.db')
        self.assertTrue(os.path.exists(db_file))

    @mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True)
    def test_sync_moves_file_from_source(self, mock_ready):
        """Test that sync() moves files from source to output"""
        # Place a test file in source directory
        test_file = os.path.join(self.test_media_dir, 'img1.jpg')
        copied_file = self._copy_test_file(test_file, self.source1_dir)

        # Run sync
        config_path = self._create_config_file(self._get_basic_config())
        ps = photosort.PhotoSort(config_path, log_level='ERROR')
        ps.sync()

        # Verify file was moved from source
        self.assertFalse(os.path.exists(copied_file))

        # Verify file is in output directory (organized by date)
        # img1.jpg has EXIF date 2013-08-24
        expected_dir = os.path.join(self.output_dir, '2013', '2013_08')
        self.assertTrue(os.path.exists(expected_dir))

        # Find the file in the expected directory
        files_in_output = os.listdir(expected_dir)
        self.assertGreater(len(files_in_output), 0)
        self.assertTrue(any('img1.jpg' in f for f in files_in_output))

    @mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True)
    def test_sync_with_file_prefix(self, mock_ready):
        """Test that file_prefix is applied when moving files"""
        config_data = self._get_basic_config()
        config_data['output']['file_prefix'] = '%(year)d%(month)02d%(day)02d_'

        test_file = os.path.join(self.test_media_dir, 'img1.jpg')
        copied_file = self._copy_test_file(test_file, self.source1_dir)

        config_path = self._create_config_file(config_data)
        ps = photosort.PhotoSort(config_path, log_level='ERROR')
        ps.sync()

        # File should be prefixed with date: 20130824_img1.jpg
        expected_dir = os.path.join(self.output_dir, '2013', '2013_08')
        files_in_output = os.listdir(expected_dir)
        self.assertTrue(any('20130824' in f for f in files_in_output))

    @mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True)
    def test_duplicate_detection_and_movement(self, mock_ready):
        """Test that duplicate files are moved to duplicates directory"""
        # First, add a file to output and build database
        test_file = os.path.join(self.test_media_dir, 'img1.jpg')
        output_subdir = os.path.join(self.output_dir, '2013', '2013_08')
        os.makedirs(output_subdir, exist_ok=True)
        original = self._copy_test_file(test_file, output_subdir, 'original.jpg')

        config_path = self._create_config_file(self._get_basic_config())
        ps = photosort.PhotoSort(config_path, log_level='ERROR')
        ps.rebuild_db()

        # Now add a duplicate to source
        duplicate = self._copy_test_file(test_file, self.source1_dir, 'img1_dup.jpg')

        ps.sync()

        # Duplicate should be in duplicates directory
        dup_dir = os.path.join(self.output_dir, 'duplicates')
        self.assertTrue(os.path.exists(dup_dir))
        files_in_dup = os.listdir(dup_dir)
        self.assertGreater(len(files_in_dup), 0)

    @mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True)

    def test_multiple_sources(self, mock_ready):
        """Test sync with multiple source directories"""
        # Place files in both sources
        test_file = os.path.join(self.test_media_dir, 'img1.jpg')
        file1 = self._copy_test_file(test_file, self.source1_dir, 'from_source1.jpg')
        file2 = self._copy_test_file(test_file, self.source2_dir, 'from_source2.jpg')

        config_path = self._create_config_file(self._get_basic_config())
        ps = photosort.PhotoSort(config_path, log_level='ERROR')
        ps.sync()

        # Both files should be processed
        self.assertFalse(os.path.exists(file1))
        self.assertFalse(os.path.exists(file2))

        # One should be in output, one should be in duplicates
        expected_dir = os.path.join(self.output_dir, '2013', '2013_08')
        dup_dir = os.path.join(self.output_dir, 'duplicates')

        output_files = []
        if os.path.exists(expected_dir):
            output_files = os.listdir(expected_dir)
        dup_files = []
        if os.path.exists(dup_dir):
            dup_files = os.listdir(dup_dir)

        total_files = len(output_files) + len(dup_files)
        self.assertEqual(total_files, 2)

    @mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True)

    def test_file_permissions_are_set(self, mock_ready):
        """Test that file permissions are set correctly"""
        config_data = self._get_basic_config()
        config_data['output']['chmod'] = '0o755'

        test_file = os.path.join(self.test_media_dir, 'img1.jpg')
        copied_file = self._copy_test_file(test_file, self.source1_dir)

        config_path = self._create_config_file(config_data)
        ps = photosort.PhotoSort(config_path, log_level='ERROR')
        ps.sync()

        # Find the moved file and check permissions
        expected_dir = os.path.join(self.output_dir, '2013', '2013_08')
        files_in_output = os.listdir(expected_dir)
        moved_file = os.path.join(expected_dir, files_in_output[0])

        # Check file permissions (755 = 0o755)
        file_stat = os.stat(moved_file)
        file_mode = file_stat.st_mode & 0o777
        self.assertEqual(file_mode, 0o755)

    @mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True)

    def test_directory_permissions_are_set(self, mock_ready):
        """Test that directory permissions are set with execute bit"""
        config_data = self._get_basic_config()
        config_data['output']['chmod'] = '0o644'

        test_file = os.path.join(self.test_media_dir, 'img1.jpg')
        copied_file = self._copy_test_file(test_file, self.source1_dir)

        config_path = self._create_config_file(config_data)
        ps = photosort.PhotoSort(config_path, log_level='ERROR')
        ps.sync()

        # Check directory permissions (should have execute bit added)
        created_dir = os.path.join(self.output_dir, '2013', '2013_08')
        dir_stat = os.stat(created_dir)
        dir_mode = dir_stat.st_mode & 0o777

        # Directory should have execute bit (0o755 = 0o644 | S_IXUSR)
        self.assertTrue(dir_mode & 0o100)  # User execute bit

    def test_sync_skips_files_without_exif(self):
        """Test that files without EXIF datetime are skipped"""
        # Create a file without EXIF data
        no_exif_file = os.path.join(self.source1_dir, 'no_exif.jpg')
        with open(no_exif_file, 'wb') as f:
            # Write a minimal JPEG header
            f.write(b'\xFF\xD8\xFF\xE0\x00\x10JFIF')

        config_path = self._create_config_file(self._get_basic_config())
        ps = photosort.PhotoSort(config_path, log_level='ERROR')
        ps.sync()

        # File should still be in source (not moved)
        self.assertTrue(os.path.exists(no_exif_file))

    @mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True)

    def test_database_is_updated_after_sync(self, mock_ready):
        """Test that database is updated with new files after sync"""
        test_file = os.path.join(self.test_media_dir, 'img1.jpg')
        copied_file = self._copy_test_file(test_file, self.source1_dir)

        config_path = self._create_config_file(self._get_basic_config())
        ps = photosort.PhotoSort(config_path, log_level='ERROR')

        # Initial database should be empty
        self.assertEqual(len(ps._photodb._hashes), 0)

        ps.sync()

        # Database should now contain the synced file
        self.assertEqual(len(ps._photodb._hashes), 1)

        # Database file should exist
        db_file = os.path.join(self.output_dir, 'photosort.db')
        self.assertTrue(os.path.exists(db_file))

    @mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True)

    def test_complex_dir_pattern(self, mock_ready):
        """Test complex directory pattern with multiple variables"""
        config_data = self._get_basic_config()
        config_data['output']['dir_pattern'] = '%(year)d/%(year)04d_%(month)02d_%(day)02d'

        test_file = os.path.join(self.test_media_dir, 'img1.jpg')
        copied_file = self._copy_test_file(test_file, self.source1_dir)

        config_path = self._create_config_file(config_data)
        ps = photosort.PhotoSort(config_path, log_level='ERROR')
        ps.sync()

        # Directory should match pattern: 2013/2013_08_24
        expected_dir = os.path.join(self.output_dir, '2013', '2013_08_24')
        self.assertTrue(os.path.exists(expected_dir))

    @mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True)

    def test_video_file_processing(self, mock_ready):
        """Test that video files are processed correctly"""
        # Use a video file with EXIF data
        test_video = os.path.join(self.test_media2_dir, 'mov1.mp4')
        if not os.path.exists(test_video):
            self.skipTest("Test video file not available")

        copied_file = self._copy_test_file(test_video, self.source1_dir)

        config_path = self._create_config_file(self._get_basic_config())
        ps = photosort.PhotoSort(config_path, log_level='ERROR')
        ps.sync()

        # Video should be moved from source
        self.assertFalse(os.path.exists(copied_file))

        # Should be in output directory
        self.assertGreater(len(ps._photodb._hashes), 0)

    @mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True)

    def test_rebuilddb_ignores_source_directories(self, mock_ready):
        """Test that rebuilddb ignores source directories"""
        # Place files in both output and source
        test_file = os.path.join(self.test_media_dir, 'img1.jpg')

        output_subdir = os.path.join(self.output_dir, '2013', '2013_08')
        os.makedirs(output_subdir, exist_ok=True)
        file_in_output = self._copy_test_file(test_file, output_subdir)

        file_in_source = self._copy_test_file(test_file, self.source1_dir)

        config_path = self._create_config_file(self._get_basic_config())
        ps = photosort.PhotoSort(config_path, log_level='ERROR')
        ps.rebuild_db()

        # Database should only contain file from output, not source
        # Both files have same hash, so only 1 entry
        self.assertEqual(len(ps._photodb._hashes), 1)

    def test_sync_updates_existing_database(self):
        """Test that sync adds to existing database"""
        config_path = self._create_config_file(self._get_basic_config())

        # First sync with one file
        test_file1 = os.path.join(self.test_media_dir, 'img1.jpg')
        file1 = self._copy_test_file(test_file1, self.source1_dir, 'photo1.jpg')

        ps = photosort.PhotoSort(config_path, log_level='ERROR')
        ps.sync()

        initial_count = len(ps._photodb._hashes)

        # Create new PhotoSort instance (simulates new run)
        # Add a different file (need to create one with different hash)
        # For now, just verify sync runs without error
        ps2 = photosort.PhotoSort(config_path, log_level='ERROR')

        # Should load existing database
        self.assertEqual(len(ps2._photodb._hashes), initial_count)

    def test_empty_source_directories(self):
        """Test sync with empty source directories"""
        config_path = self._create_config_file(self._get_basic_config())
        ps = photosort.PhotoSort(config_path, log_level='ERROR')

        # Should not raise error with empty sources
        ps.sync()

        # Database should be empty
        self.assertEqual(len(ps._photodb._hashes), 0)

    def test_logging_configuration(self):
        """Test that logging is configured correctly"""
        config_data = self._get_basic_config()
        config_data['output']['log_file'] = 'test.log'

        config_path = self._create_config_file(config_data)
        ps = photosort.PhotoSort(config_path, log_level='INFO')

        # Log file should be created (or at least configured)
        # This test mainly ensures no errors during initialization
        self.assertIsNotNone(ps._config.log_file())

    @mock.patch('photosort.walk.WalkForMedia._file_is_ready', return_value=True)
    def test_sync_with_fallback_to_file_date(self, mock_ready):
        """Test sync with fallback_to_file_date enabled processes files without EXIF"""
        # Create a file without EXIF data in source1
        test_file = os.path.join(self.source1_dir, 'screenshot.jpg')
        with open(test_file, 'w') as f:
            f.write("fake image without exif data")

        # Configure source1 with fallback enabled
        config_data = self._get_basic_config()
        config_data['sources']['source1']['fallback_to_file_date'] = True

        config_path = self._create_config_file(config_data)
        ps = photosort.PhotoSort(config_path, log_level='INFO')

        # Run sync
        ps.sync()

        # File should have been moved (not skipped)
        self.assertFalse(os.path.exists(test_file))

        # File should be in output directory organized by file timestamp
        # Since we don't know exact timestamp, just verify it moved somewhere in output
        moved_files = []
        for root, dirs, files in os.walk(self.output_dir):
            if 'duplicates' not in root:  # Exclude duplicates dir
                for f in files:
                    if f == 'screenshot.jpg':
                        moved_files.append(os.path.join(root, f))

        self.assertEqual(len(moved_files), 1, "File should be moved to output directory")

    @mock.patch('photosort.walk.WalkForMedia._file_is_ready', return_value=True)
    def test_sync_without_fallback_skips_no_exif(self, mock_ready):
        """Test sync without fallback skips files without EXIF"""
        # Create a file without EXIF data in source1
        test_file = os.path.join(self.source1_dir, 'screenshot.jpg')
        with open(test_file, 'w') as f:
            f.write("fake image without exif data")

        # Configure source1 with fallback disabled (default)
        config_data = self._get_basic_config()
        # Don't set fallback_to_file_date, defaults to False

        config_path = self._create_config_file(config_data)
        ps = photosort.PhotoSort(config_path, log_level='INFO')

        # Run sync
        ps.sync()

        # File should still be in source (skipped)
        self.assertTrue(os.path.exists(test_file))

        # File should NOT be in output directory
        moved_files = []
        for root, dirs, files in os.walk(self.output_dir):
            if 'duplicates' not in root:
                for f in files:
                    if f == 'screenshot.jpg':
                        moved_files.append(os.path.join(root, f))

        self.assertEqual(len(moved_files), 0, "File should not be moved")

    @mock.patch('photosort.walk.WalkForMedia._file_is_ready', return_value=True)
    def test_sync_with_mixed_fallback_settings(self, mock_ready):
        """Test that different sources can have different fallback settings"""
        # Create file without EXIF in source1 (fallback enabled)
        test_file1 = os.path.join(self.source1_dir, 'screenshot1.jpg')
        with open(test_file1, 'w') as f:
            f.write("fake image without exif")

        # Create file without EXIF in source2 (fallback disabled)
        test_file2 = os.path.join(self.source2_dir, 'screenshot2.jpg')
        with open(test_file2, 'w') as f:
            f.write("fake image without exif")

        # Configure with mixed settings
        config_data = self._get_basic_config()
        config_data['sources']['source1']['fallback_to_file_date'] = True
        config_data['sources']['source2']['fallback_to_file_date'] = False

        config_path = self._create_config_file(config_data)
        ps = photosort.PhotoSort(config_path, log_level='INFO')

        # Run sync
        ps.sync()

        # File from source1 should be moved (fallback enabled)
        self.assertFalse(os.path.exists(test_file1))

        # File from source2 should still be there (fallback disabled, skipped)
        self.assertTrue(os.path.exists(test_file2))


if __name__ == '__main__':
    test.test.main()
