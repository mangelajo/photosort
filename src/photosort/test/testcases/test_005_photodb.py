# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import csv
import logging
import mock
import os
import tempfile
import unittest

from photosort import config
from photosort import photodb
from photosort import test


class TestPhotoDB(test.TestCase):

    def _create_config(self, output_dir, db_file='photosort.db'):
        """Helper to create a mock config object"""
        cfg = mock.Mock()
        cfg.db_file.return_value = os.path.join(output_dir, db_file)
        cfg.output_dir.return_value = output_dir
        cfg.output_chmod.return_value = 0o644
        return cfg

    def _create_mock_media_file(self, hash_value, file_type='photo',
                                  path='/test/path/file.jpg'):
        """Helper to create a mock MediaFile"""
        media_file = mock.Mock()
        media_file.hash.return_value = hash_value
        media_file.type.return_value = file_type
        media_file.get_path.return_value = path
        media_file.is_equal_to.return_value = True
        return media_file

    def test_create_empty_database(self):
        """Test creating a new database with no existing file"""
        cfg = self._create_config(self._temp_dir)
        db = photodb.PhotoDB(cfg)

        # Should create empty hashes dict
        self.assertEqual(len(db._hashes), 0)

    def test_add_entry_to_database(self):
        """Test adding a single entry to the database"""
        cfg = self._create_config(self._temp_dir)
        db = photodb.PhotoDB(cfg)

        media_file = self._create_mock_media_file('abc123hash')
        result = db.add_to_db(self._temp_dir + '/2024/01', 'photo.jpg', media_file)

        self.assertTrue(result)
        self.assertEqual(len(db._hashes), 1)
        self.assertIn('abc123hash', db._hashes)
        self.assertEqual(db._hashes['abc123hash']['dir'], '2024/01')
        self.assertEqual(db._hashes['abc123hash']['name'], 'photo.jpg')
        self.assertEqual(db._hashes['abc123hash']['type'], 'photo')

    def test_add_multiple_entries(self):
        """Test adding multiple entries to the database"""
        cfg = self._create_config(self._temp_dir)
        db = photodb.PhotoDB(cfg)

        media1 = self._create_mock_media_file('hash1')
        media2 = self._create_mock_media_file('hash2', file_type='movie')
        media3 = self._create_mock_media_file('hash3')

        db.add_to_db(self._temp_dir + '/2024/01', 'photo1.jpg', media1)
        db.add_to_db(self._temp_dir + '/2024/02', 'video1.mp4', media2)
        db.add_to_db(self._temp_dir + '/2024/03', 'photo2.jpg', media3)

        self.assertEqual(len(db._hashes), 3)
        self.assertIn('hash1', db._hashes)
        self.assertIn('hash2', db._hashes)
        self.assertIn('hash3', db._hashes)

    def test_path_prefix_stripping(self):
        """Test that output_dir is stripped from file paths"""
        output_dir = '/base/output'
        cfg = self._create_config(output_dir)
        db = photodb.PhotoDB(cfg)

        media_file = self._create_mock_media_file('hash1')
        db.add_to_db('/base/output/2024/01', 'photo.jpg', media_file)

        # Path should be stored without the output_dir prefix
        self.assertEqual(db._hashes['hash1']['dir'], '2024/01')

    def test_write_and_load_database(self):
        """Test writing database to CSV and loading it back"""
        cfg = self._create_config(self._temp_dir)
        db = photodb.PhotoDB(cfg)

        # Add some entries
        media1 = self._create_mock_media_file('hash1')
        media2 = self._create_mock_media_file('hash2', file_type='movie')

        db.add_to_db(self._temp_dir + '/2024/01', 'photo.jpg', media1)
        db.add_to_db(self._temp_dir + '/2024/02', 'video.mp4', media2)

        # Write to file
        db.write()

        # Verify file exists
        db_file = cfg.db_file()
        self.assertTrue(os.path.exists(db_file))

        # Load into a new database instance
        db2 = photodb.PhotoDB(cfg)

        # Verify loaded data matches
        self.assertEqual(len(db2._hashes), 2)
        self.assertIn('hash1', db2._hashes)
        self.assertIn('hash2', db2._hashes)
        self.assertEqual(db2._hashes['hash1']['name'], 'photo.jpg')
        self.assertEqual(db2._hashes['hash2']['name'], 'video.mp4')

    def test_csv_format(self):
        """Test that CSV is written with correct format"""
        cfg = self._create_config(self._temp_dir)
        db = photodb.PhotoDB(cfg)

        media_file = self._create_mock_media_file('testhash123')
        db.add_to_db(self._temp_dir + '/2024/01', 'test.jpg', media_file)
        db.write()

        # Read CSV directly and verify format
        db_file = cfg.db_file()
        with open(db_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            self.assertEqual(header, ['directory', 'filename', 'type', 'md5'])

            row = next(reader)
            self.assertEqual(row[0], '2024/01')  # directory
            self.assertEqual(row[1], 'test.jpg')  # filename
            self.assertEqual(row[2], 'photo')     # type
            self.assertEqual(row[3], 'testhash123')  # hash

    def test_backup_file_creation(self):
        """Test that backup file is created when writing"""
        cfg = self._create_config(self._temp_dir)
        db = photodb.PhotoDB(cfg)

        media1 = self._create_mock_media_file('hash1')
        db.add_to_db(self._temp_dir + '/2024', 'photo1.jpg', media1)
        db.write()

        # Add another entry and write again
        media2 = self._create_mock_media_file('hash2')
        db.add_to_db(self._temp_dir + '/2024', 'photo2.jpg', media2)
        db.write()

        # Backup file should exist
        db_file = cfg.db_file()
        backup_file = db_file + '.bak'
        self.assertTrue(os.path.exists(backup_file))

        # Backup should contain only the first entry
        with open(backup_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            rows = list(reader)
            self.assertEqual(len(rows), 1)

    def test_duplicate_detection_found(self):
        """Test duplicate detection when hash exists"""
        cfg = self._create_config(self._temp_dir)
        db = photodb.PhotoDB(cfg)

        # Add an entry
        media1 = self._create_mock_media_file('duplicatehash')
        db.add_to_db(self._temp_dir + '/2024', 'original.jpg', media1)

        # Create a file to match the duplicate check
        os.makedirs(os.path.join(self._temp_dir, '2024'), exist_ok=True)
        test_file = os.path.join(self._temp_dir, '2024', 'original.jpg')
        with open(test_file, 'w') as f:
            f.write('test content')

        # Check for duplicate with same hash
        media2 = self._create_mock_media_file('duplicatehash',
                                               path='/new/path/copy.jpg')

        is_dupe = db.is_duplicate(media2)
        self.assertTrue(is_dupe)

    def test_duplicate_detection_not_found(self):
        """Test duplicate detection when hash doesn't exist"""
        cfg = self._create_config(self._temp_dir)
        db = photodb.PhotoDB(cfg)

        # Add an entry
        media1 = self._create_mock_media_file('hash1')
        db.add_to_db(self._temp_dir + '/2024', 'photo1.jpg', media1)

        # Check for different hash
        media2 = self._create_mock_media_file('hash2')
        is_dupe = db.is_duplicate(media2)

        self.assertFalse(is_dupe)

    def test_hash_collision_detection(self):
        """Test hash collision detection (same hash, different files)"""
        cfg = self._create_config(self._temp_dir)
        db = photodb.PhotoDB(cfg)

        # Add an entry
        media1 = self._create_mock_media_file('samehash')
        db.add_to_db(self._temp_dir + '/2024', 'file1.jpg', media1)

        # Create a file for the first entry
        os.makedirs(os.path.join(self._temp_dir, '2024'), exist_ok=True)
        test_file = os.path.join(self._temp_dir, '2024', 'file1.jpg')
        with open(test_file, 'w') as f:
            f.write('original content')

        # Check with same hash but different content
        media2 = self._create_mock_media_file('samehash',
                                               path='/new/file2.jpg')
        media2.is_equal_to.return_value = False  # Files are different

        # Should log CRITICAL for collision but still return True
        with self.assertLogs(level=logging.CRITICAL) as log:
            is_dupe = db.is_duplicate(media2)
            self.assertTrue(is_dupe)
            self.assertTrue(any('collision' in msg.lower() for msg in log.output))

    def test_load_missing_database(self):
        """Test loading when database file doesn't exist"""
        cfg = self._create_config(self._temp_dir, 'nonexistent.db')

        # Should not raise an error, just create empty database
        db = photodb.PhotoDB(cfg)
        self.assertEqual(len(db._hashes), 0)

    def test_load_empty_database_file(self):
        """Test loading an empty CSV file"""
        cfg = self._create_config(self._temp_dir)
        db_file = cfg.db_file()

        # Create empty file
        with open(db_file, 'w') as f:
            pass

        # Should handle empty file gracefully
        db = photodb.PhotoDB(cfg)
        self.assertEqual(len(db._hashes), 0)

    def test_load_merge_mode_false(self):
        """Test that merge=False clears existing data"""
        cfg = self._create_config(self._temp_dir)
        db = photodb.PhotoDB(cfg)

        # Add initial data
        media1 = self._create_mock_media_file('hash1')
        db.add_to_db(self._temp_dir + '/2024', 'photo1.jpg', media1)
        db.write()

        # Add more data in memory
        media2 = self._create_mock_media_file('hash2')
        db.add_to_db(self._temp_dir + '/2024', 'photo2.jpg', media2)

        # Load without merge (should clear hash2)
        db.load(merge=False)

        self.assertEqual(len(db._hashes), 1)
        self.assertIn('hash1', db._hashes)
        self.assertNotIn('hash2', db._hashes)

    def test_load_merge_mode_true(self):
        """Test that merge=True keeps existing data"""
        cfg = self._create_config(self._temp_dir)
        db = photodb.PhotoDB(cfg)

        # Add initial data
        media1 = self._create_mock_media_file('hash1')
        db.add_to_db(self._temp_dir + '/2024', 'photo1.jpg', media1)
        db.write()

        # Add more data in memory
        media2 = self._create_mock_media_file('hash2')
        db.add_to_db(self._temp_dir + '/2024', 'photo2.jpg', media2)

        # Load with merge (should keep both)
        db.load(merge=True)

        self.assertEqual(len(db._hashes), 2)
        self.assertIn('hash1', db._hashes)
        self.assertIn('hash2', db._hashes)

    def test_load_from_alternate_file(self):
        """Test loading from a different file"""
        cfg = self._create_config(self._temp_dir)
        db = photodb.PhotoDB(cfg)

        # Create an alternate database file
        alt_db_file = os.path.join(self._temp_dir, 'alternate.db')
        with open(alt_db_file, 'w', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['directory', 'filename', 'type', 'md5'])
            writer.writerow(['2024/alt', 'alternate.jpg', 'photo', 'althash'])

        # Load from alternate file
        db.load(filename=alt_db_file)

        self.assertEqual(len(db._hashes), 1)
        self.assertIn('althash', db._hashes)
        self.assertEqual(db._hashes['althash']['name'], 'alternate.jpg')

    def test_add_with_ioerror(self):
        """Test that IOError during hashing is handled"""
        cfg = self._create_config(self._temp_dir)
        db = photodb.PhotoDB(cfg)

        # Create media file that raises IOError on hash()
        media_file = mock.Mock()
        media_file.hash.side_effect = IOError("Unable to read file")
        media_file.get_path.return_value = '/test/bad/file.jpg'

        # Should return False and log error
        with self.assertLogs(level=logging.ERROR) as log:
            result = db.add_to_db(self._temp_dir + '/2024', 'bad.jpg', media_file)
            self.assertFalse(result)
            self.assertTrue(any('IOError' in msg for msg in log.output))

    def test_write_multiple_times(self):
        """Test writing database multiple times updates correctly"""
        cfg = self._create_config(self._temp_dir)
        db = photodb.PhotoDB(cfg)

        # Write first batch
        media1 = self._create_mock_media_file('hash1')
        db.add_to_db(self._temp_dir + '/2024', 'photo1.jpg', media1)
        db.write()

        # Write second batch
        media2 = self._create_mock_media_file('hash2')
        db.add_to_db(self._temp_dir + '/2024', 'photo2.jpg', media2)
        db.write()

        # Load and verify both entries present
        db2 = photodb.PhotoDB(cfg)
        self.assertEqual(len(db2._hashes), 2)

    def test_different_file_types(self):
        """Test database handles different media types"""
        cfg = self._create_config(self._temp_dir)
        db = photodb.PhotoDB(cfg)

        media_photo = self._create_mock_media_file('hash1', file_type='photo')
        media_movie = self._create_mock_media_file('hash2', file_type='movie')
        media_unknown = self._create_mock_media_file('hash3', file_type='unknown')

        db.add_to_db(self._temp_dir + '/2024', 'photo.jpg', media_photo)
        db.add_to_db(self._temp_dir + '/2024', 'video.mp4', media_movie)
        db.add_to_db(self._temp_dir + '/2024', 'file.dat', media_unknown)

        self.assertEqual(db._hashes['hash1']['type'], 'photo')
        self.assertEqual(db._hashes['hash2']['type'], 'movie')
        self.assertEqual(db._hashes['hash3']['type'], 'unknown')

    def test_unicode_filenames(self):
        """Test database handles unicode characters in filenames"""
        cfg = self._create_config(self._temp_dir)
        db = photodb.PhotoDB(cfg)

        media_file = self._create_mock_media_file('unicodehash')
        db.add_to_db(self._temp_dir + '/2024', 'фото_日本_🎉.jpg', media_file)
        db.write()

        # Load and verify unicode preserved
        db2 = photodb.PhotoDB(cfg)
        self.assertEqual(db2._hashes['unicodehash']['name'], 'фото_日本_🎉.jpg')

    def test_special_characters_in_paths(self):
        """Test database handles special characters in directory paths"""
        cfg = self._create_config(self._temp_dir)
        db = photodb.PhotoDB(cfg)

        media_file = self._create_mock_media_file('hash1')
        db.add_to_db(self._temp_dir + '/2024/my photos (old)', 'test.jpg', media_file)

        self.assertEqual(db._hashes['hash1']['dir'], '2024/my photos (old)')


if __name__ == '__main__':
    test.test.main()
