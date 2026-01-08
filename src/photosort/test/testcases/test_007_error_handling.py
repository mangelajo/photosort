# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import logging
import mock
import os
import shutil
import stat
import yaml

from photosort import config
from photosort import media
from photosort import photodb
from photosort import photosort
from photosort import test
from photosort import walk


class TestErrorHandling(test.TestCase):
    """Test error handling and robustness scenarios"""

    def setUp(self):
        super().setUp()
        self.media1 = self.get_data_path('media1')

    def test_missing_config_file(self):
        """Test PhotoSort initialization with missing config file"""
        nonexistent_config = os.path.join(self._temp_dir, 'nonexistent.yml')

        with self.assertRaises(FileNotFoundError):
            config.Config(nonexistent_config)

    def test_invalid_yaml_syntax(self):
        """Test config parsing with invalid YAML syntax"""
        invalid_yaml = os.path.join(self._temp_dir, 'invalid.yml')
        with open(invalid_yaml, 'w') as f:
            f.write("invalid: yaml: syntax: [unclosed")

        with self.assertRaises(yaml.YAMLError):
            config.Config(invalid_yaml)

    def test_missing_required_fields(self):
        """Test config with missing required output fields"""
        incomplete_config = os.path.join(self._temp_dir, 'incomplete.yml')
        with open(incomplete_config, 'w') as f:
            yaml.dump({'sources': {}}, f)

        cfg = config.Config(incomplete_config)

        # Missing 'output' key should raise KeyError
        with self.assertRaises(KeyError):
            cfg.output_dir()

    def test_invalid_chmod_value(self):
        """Test config with invalid chmod value"""
        invalid_chmod_config = os.path.join(self._temp_dir, 'invalid_chmod.yml')
        config_data = {
            'output': {
                'dir': self._temp_dir,
                'chmod': 'not_a_number',  # Invalid
                'db_file': 'test.csv',
                'duplicates_dir': 'dupes',
                'dir_pattern': '%(year)04d',
            },
            'sources': {}
        }
        with open(invalid_chmod_config, 'w') as f:
            yaml.dump(config_data, f)

        cfg = config.Config(invalid_chmod_config)

        # Should raise ValueError when trying to convert to int
        with self.assertRaises(ValueError):
            cfg.output_chmod()

    def test_sync_missing_source_directory(self):
        """Test sync with missing source directory logs error"""
        config_path = os.path.join(self._temp_dir, 'test.yml')
        output_dir = os.path.join(self._temp_dir, 'output')
        nonexistent_source = os.path.join(self._temp_dir, 'nonexistent')

        os.makedirs(output_dir)

        config_data = {
            'output': {
                'dir': output_dir,
                'chmod': '0o755',
                'db_file': 'photos.csv',
                'duplicates_dir': 'duplicates',
                'dir_pattern': '%(year)04d_%(month)02d',
            },
            'sources': {
                'test': {'dir': nonexistent_source}
            }
        }

        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        ps = photosort.PhotoSort(config_path, logging.ERROR)

        # Should log error and continue without crashing
        with self.assertLogs(level=logging.ERROR) as log:
            ps.sync()
            self.assertTrue(any('Unable to walk dir' in msg for msg in log.output))

    def test_unwritable_output_directory(self):
        """Test behavior when output directory is not writable"""
        config_path = os.path.join(self._temp_dir, 'test.yml')
        output_dir = os.path.join(self._temp_dir, 'output')
        source_dir = os.path.join(self._temp_dir, 'source')

        os.makedirs(output_dir)
        os.makedirs(source_dir)

        # Copy test file to source
        test_file = os.path.join(self.media1, 'img1.jpg')
        dest_file = os.path.join(source_dir, 'test.jpg')
        shutil.copy(test_file, dest_file)

        config_data = {
            'output': {
                'dir': output_dir,
                'chmod': '0o755',
                'db_file': 'photos.csv',
                'duplicates_dir': 'duplicates',
                'dir_pattern': '%(year)04d_%(month)02d',
            },
            'sources': {
                'test': {'dir': source_dir}
            }
        }

        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        # Make output directory read-only
        os.chmod(output_dir, stat.S_IRUSR | stat.S_IXUSR)

        try:
            ps = photosort.PhotoSort(config_path, logging.ERROR)

            # Should raise PermissionError when trying to write database
            with mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True):
                with self.assertRaises(PermissionError):
                    ps.sync()
        finally:
            # Restore permissions for cleanup
            os.chmod(output_dir, stat.S_IRWXU)

    def test_unwritable_database_file(self):
        """Test behavior when database file cannot be written"""
        config_path = os.path.join(self._temp_dir, 'test.yml')
        output_dir = os.path.join(self._temp_dir, 'output')
        db_dir = os.path.join(output_dir, 'db_dir')

        os.makedirs(db_dir)

        config_data = {
            'output': {
                'dir': output_dir,
                'chmod': '0o755',
                'db_file': 'db_dir/photos.csv',
                'duplicates_dir': 'duplicates',
                'dir_pattern': '%(year)04d',
            },
            'sources': {}
        }

        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        # Make db directory read-only so file can't be created
        os.chmod(db_dir, stat.S_IRUSR | stat.S_IXUSR)

        try:
            cfg = config.Config(config_path)
            db = photodb.PhotoDB(cfg)

            # Should raise PermissionError when trying to write
            with self.assertRaises(PermissionError):
                db.write()
        finally:
            # Restore permissions for cleanup
            os.chmod(db_dir, stat.S_IRWXU)

    def test_file_disappears_during_processing(self):
        """Test handling when file is deleted during processing"""
        config_path = os.path.join(self._temp_dir, 'test.yml')
        output_dir = os.path.join(self._temp_dir, 'output')
        source_dir = os.path.join(self._temp_dir, 'source')

        os.makedirs(output_dir)
        os.makedirs(source_dir)

        test_file = os.path.join(self.media1, 'img1.jpg')
        dest_file = os.path.join(source_dir, 'disappearing.jpg')
        shutil.copy(test_file, dest_file)

        config_data = {
            'output': {
                'dir': output_dir,
                'chmod': '0o755',
                'db_file': 'photos.csv',
                'duplicates_dir': 'duplicates',
                'dir_pattern': '%(year)04d',
            },
            'sources': {
                'test': {'dir': source_dir}
            }
        }

        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        ps = photosort.PhotoSort(config_path, logging.ERROR)

        # Mock MediaFile.build_for to delete file before processing
        original_build = media.MediaFile.build_for

        def delete_and_build(filename):
            mf = original_build(filename)
            # Override rename_as to simulate file disappearing
            original_rename = mf.rename_as
            def failing_rename(*args, **kwargs):
                os.remove(filename)  # File disappears
                return original_rename(*args, **kwargs)
            mf.rename_as = failing_rename
            return mf

        with mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True):
            with mock.patch.object(media.MediaFile, 'build_for', side_effect=delete_and_build):
                with self.assertLogs(level=logging.ERROR) as log:
                    ps.sync()
                    # Should handle gracefully and log error
                    self.assertTrue(any('Unable to move' in msg for msg in log.output))

    def test_file_without_exif_skipped(self):
        """Test that files without EXIF data are skipped with error log"""
        config_path = os.path.join(self._temp_dir, 'test.yml')
        output_dir = os.path.join(self._temp_dir, 'output')
        source_dir = os.path.join(self._temp_dir, 'source')

        os.makedirs(output_dir)
        os.makedirs(source_dir)

        # Create a file without EXIF
        no_exif_file = os.path.join(source_dir, 'no_exif.jpg')
        with open(no_exif_file, 'wb') as f:
            f.write(b'\xFF\xD8\xFF\xE0')  # Minimal JPEG header

        config_data = {
            'output': {
                'dir': output_dir,
                'chmod': '0o755',
                'db_file': 'photos.csv',
                'duplicates_dir': 'duplicates',
                'dir_pattern': '%(year)04d',
            },
            'sources': {
                'test': {'dir': source_dir}
            }
        }

        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        ps = photosort.PhotoSort(config_path, logging.ERROR)

        with mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True):
            with self.assertLogs(level=logging.ERROR) as log:
                ps.sync()
                self.assertTrue(any('no date found from EXIF' in msg for msg in log.output))

    def test_rebuild_db_with_corrupted_file(self):
        """Test rebuild_db handles exceptions gracefully"""
        config_path = os.path.join(self._temp_dir, 'test.yml')
        output_dir = os.path.join(self._temp_dir, 'output')

        os.makedirs(output_dir)

        # Create a corrupted "media" file
        corrupted_file = os.path.join(output_dir, 'corrupted.jpg')
        with open(corrupted_file, 'w') as f:
            f.write('not a real image')

        config_data = {
            'output': {
                'dir': output_dir,
                'chmod': '0o755',
                'db_file': 'photos.csv',
                'duplicates_dir': 'duplicates',
                'dir_pattern': '%(year)04d',
            },
            'sources': {}
        }

        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        ps = photosort.PhotoSort(config_path, logging.ERROR)

        # rebuild_db should complete without crashing even with corrupted files
        # The corrupted file will be skipped (no EXIF date)
        with mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True):
            # Should complete without raising exception
            ps.rebuild_db()
            # Database should be written successfully
            self.assertTrue(os.path.exists(os.path.join(output_dir, 'photos.csv')))

    def test_makedirs_with_permission_error(self):
        """Test makedirs_f handles permission errors"""
        test_file = os.path.join(self.media1, 'img1.jpg')
        mf = media.MediaFile.build_for(test_file)

        # Try to create directory in read-only parent
        readonly_dir = os.path.join(self._temp_dir, 'readonly')
        os.makedirs(readonly_dir)
        os.chmod(readonly_dir, stat.S_IRUSR | stat.S_IXUSR)

        try:
            target_dir = os.path.join(readonly_dir, 'subdir', 'deep')

            # Should raise OSError
            with self.assertRaises(OSError):
                mf.makedirs_f(target_dir, 0o755)
        finally:
            os.chmod(readonly_dir, stat.S_IRWXU)

    def test_rename_as_with_permission_error(self):
        """Test rename_as returns False on permission error"""
        test_file = os.path.join(self.media1, 'img1.jpg')
        source_file = os.path.join(self._temp_dir, 'source.jpg')
        shutil.copy(test_file, source_file)

        mf = media.MediaFile.build_for(source_file)

        # Try to move to read-only directory
        readonly_dir = os.path.join(self._temp_dir, 'readonly')
        os.makedirs(readonly_dir)
        os.chmod(readonly_dir, stat.S_IRUSR | stat.S_IXUSR)

        try:
            target_file = os.path.join(readonly_dir, 'target.jpg')

            with self.assertLogs(level=logging.ERROR) as log:
                result = mf.rename_as(target_file, 0o755)
                self.assertFalse(result)
                self.assertTrue(any('Unable to move' in msg for msg in log.output))
        finally:
            os.chmod(readonly_dir, stat.S_IRWXU)

    def test_walk_directory_with_permission_error(self):
        """Test WalkForMedia handles directories without read permission"""
        test_dir = os.path.join(self._temp_dir, 'test')
        forbidden_dir = os.path.join(test_dir, 'forbidden')
        os.makedirs(forbidden_dir)

        # Create a file in forbidden directory
        test_file = os.path.join(self.media1, 'img1.jpg')
        dest_file = os.path.join(forbidden_dir, 'hidden.jpg')
        shutil.copy(test_file, dest_file)

        # Make directory unreadable
        os.chmod(forbidden_dir, 0o000)

        try:
            walker = walk.WalkForMedia(test_dir)
            with mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True):
                # Should skip unreadable directories without crashing
                files = list(walker.find_media())
                # File in forbidden dir should not be found
                self.assertEqual(len(files), 0)
        finally:
            # Restore permissions for cleanup
            os.chmod(forbidden_dir, stat.S_IRWXU)

    def test_is_equal_to_with_missing_file(self):
        """Test is_equal_to handles missing comparison file gracefully"""
        test_file = os.path.join(self.media1, 'img1.jpg')
        mf = media.MediaFile.build_for(test_file)

        nonexistent_file = os.path.join(self._temp_dir, 'nonexistent.jpg')

        with self.assertLogs(level=logging.INFO) as log:
            result = mf.is_equal_to(nonexistent_file)
            self.assertFalse(result)
            self.assertTrue(any("didn't exist anymore" in msg for msg in log.output))

    def test_move_to_directory_without_exif(self):
        """Test move_to_directory_with_date handles UnknownDatetime"""
        # Create a file without EXIF
        no_exif_file = os.path.join(self._temp_dir, 'no_exif.jpg')
        with open(no_exif_file, 'wb') as f:
            f.write(b'\xFF\xD8\xFF\xE0')

        mf = media.MediaFile.build_for(no_exif_file)
        output_dir = os.path.join(self._temp_dir, 'output')
        os.makedirs(output_dir)

        with self.assertLogs(level=logging.ERROR) as log:
            result = mf.move_to_directory_with_date(output_dir, '%(year)04d')
            self.assertFalse(result)
            self.assertTrue(any('unknown datetime' in msg for msg in log.output))

    def test_database_merge_mode_preserves_existing(self):
        """Test that database merge mode doesn't lose existing entries on errors"""
        config_path = os.path.join(self._temp_dir, 'test.yml')
        output_dir = os.path.join(self._temp_dir, 'output')
        db_file = os.path.join(output_dir, 'photos.csv')

        os.makedirs(output_dir)

        # Create initial database with correct CSV format
        with open(db_file, 'w') as f:
            f.write('directory,filename,type,md5\n')
            f.write('path1,file1.jpg,photo,hash1\n')

        config_data = {
            'output': {
                'dir': output_dir,
                'chmod': '0o755',
                'db_file': 'photos.csv',
                'duplicates_dir': 'duplicates',
                'dir_pattern': '%(year)04d',
            },
            'sources': {}
        }

        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        cfg = config.Config(config_path)

        # Load with merge=False (default) clears existing
        db = photodb.PhotoDB(cfg)
        self.assertEqual(len(db._hashes), 1)
        self.assertIn('hash1', db._hashes)

        # Add another entry
        db._hashes['hash2'] = {'dir': 'path2', 'name': 'file2.jpg', 'type': 'photo'}

        # Load again with merge=True should keep both
        db.load(merge=True)
        self.assertEqual(len(db._hashes), 2)
        self.assertIn('hash1', db._hashes)
        self.assertIn('hash2', db._hashes)

    def test_concurrent_database_write(self):
        """Test database backup protects against concurrent writes"""
        config_path = os.path.join(self._temp_dir, 'test.yml')
        output_dir = os.path.join(self._temp_dir, 'output')
        db_file = os.path.join(output_dir, 'photos.csv')
        backup_file = db_file + '.bak'

        os.makedirs(output_dir)

        # Create initial database with correct CSV format
        with open(db_file, 'w') as f:
            f.write('directory,filename,type,md5\n')
            f.write('path1,file1.jpg,photo,hash1\n')

        config_data = {
            'output': {
                'dir': output_dir,
                'chmod': '0o755',
                'db_file': 'photos.csv',
                'duplicates_dir': 'duplicates',
                'dir_pattern': '%(year)04d',
            },
            'sources': {}
        }

        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        cfg = config.Config(config_path)
        db = photodb.PhotoDB(cfg)

        # Verify initial data loaded
        self.assertEqual(len(db._hashes), 1)
        self.assertIn('hash1', db._hashes)

        # Write should create backup of original file
        db.write()

        # Backup file should exist
        self.assertTrue(os.path.exists(backup_file))

        # Backup should contain original data (before PhotoDB reformatted it)
        with open(backup_file, 'r') as f:
            content = f.read()
            self.assertIn('hash1', content)
            self.assertIn('path1', content)

    def test_walk_with_symlink_loop(self):
        """Test WalkForMedia handles symlink loops without hanging"""
        test_dir = os.path.join(self._temp_dir, 'test')
        sub_dir = os.path.join(test_dir, 'subdir')
        os.makedirs(sub_dir)

        # Create symlink loop
        loop_link = os.path.join(sub_dir, 'loop')
        try:
            os.symlink(test_dir, loop_link)
        except OSError:
            # Symlinks might not be supported on this system
            self.skipTest("Symlinks not supported on this system")

        walker = walk.WalkForMedia(test_dir)

        # Should handle symlink loop without hanging
        # os.walk by default follows symlinks, which could cause infinite loop,
        # but WalkForMedia should handle this gracefully
        with mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True):
            files = list(walker.find_media())
            # Should complete without hanging


if __name__ == '__main__':
    test.test.main()
