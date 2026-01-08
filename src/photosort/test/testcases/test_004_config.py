# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import os
import tempfile
import unittest
import yaml

from photosort import config
from photosort import test


class TestConfig(test.TestCase):

    def _create_config_file(self, config_data):
        """Helper to create a temporary YAML config file"""
        fd, path = tempfile.mkstemp(suffix='.yml', dir=self._temp_dir)
        with os.fdopen(fd, 'w') as f:
            yaml.dump(config_data, f)
        return path

    def test_basic_config_parsing(self):
        """Test basic YAML configuration parsing"""
        config_data = {
            'sources': {
                'source1': {'dir': '/path/to/source1'},
                'source2': {'dir': '/path/to/source2'}
            },
            'output': {
                'dir': '/output/path',
                'dir_pattern': '%(year)d/%(month)02d',
                'file_prefix': '%(year)d_',
                'duplicates_dir': 'duplicates',
                'chmod': '0o755',
                'log_file': 'photosort.log',
                'db_file': 'photosort.db'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        self.assertEqual(cfg.output_dir(), '/output/path')
        self.assertEqual(cfg.dir_pattern(), '%(year)d/%(month)02d')
        self.assertEqual(cfg.file_prefix(), '%(year)d_')
        self.assertEqual(cfg.output_chmod(), 0o755)

    def test_sources_parsing(self):
        """Test sources dictionary parsing"""
        config_data = {
            'sources': {
                'dropbox': {'dir': '/Users/test/Dropbox'},
                'nas': {'dir': '/mnt/nas/inbox'}
            },
            'output': {
                'dir': '/output',
                'duplicates_dir': 'dupes',
                'chmod': '0o644',
                'db_file': 'db.csv'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        sources = cfg.sources()
        self.assertEqual(len(sources), 2)
        self.assertIn('dropbox', sources)
        self.assertIn('nas', sources)
        self.assertEqual(sources['dropbox']['dir'], '/Users/test/Dropbox')
        self.assertEqual(sources['nas']['dir'], '/mnt/nas/inbox')

    def test_relative_path_conversion(self):
        """Test that relative paths are converted to absolute using output_dir"""
        config_data = {
            'sources': {'src': {'dir': '/source'}},
            'output': {
                'dir': '/base/output',
                'duplicates_dir': 'duplicates',
                'log_file': 'logs/photosort.log',
                'db_file': 'data/photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        # Relative paths should be prefixed with output_dir
        self.assertEqual(cfg.duplicates_dir(), '/base/output/duplicates')
        self.assertEqual(cfg.log_file(), '/base/output/logs/photosort.log')
        self.assertEqual(cfg.db_file(), '/base/output/data/photosort.db')

    def test_absolute_path_preservation(self):
        """Test that absolute paths are preserved as-is"""
        config_data = {
            'sources': {'src': {'dir': '/source'}},
            'output': {
                'dir': '/base/output',
                'duplicates_dir': '/var/photosort/duplicates',
                'log_file': '/var/log/photosort.log',
                'db_file': '/var/db/photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        # Absolute paths should be returned as-is
        self.assertEqual(cfg.duplicates_dir(), '/var/photosort/duplicates')
        self.assertEqual(cfg.log_file(), '/var/log/photosort.log')
        self.assertEqual(cfg.db_file(), '/var/db/photosort.db')

    def test_optional_log_file_missing(self):
        """Test that log_file returns None when not specified"""
        config_data = {
            'sources': {'src': {'dir': '/source'}},
            'output': {
                'dir': '/output',
                'duplicates_dir': 'duplicates',
                'db_file': 'photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        self.assertIsNone(cfg.log_file())

    def test_optional_file_prefix_missing(self):
        """Test that file_prefix returns empty string when not specified"""
        config_data = {
            'sources': {'src': {'dir': '/source'}},
            'output': {
                'dir': '/output',
                'dir_pattern': '%(year)d',
                'duplicates_dir': 'duplicates',
                'db_file': 'photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        self.assertEqual(cfg.file_prefix(), '')

    def test_backward_compatibility_pattern_vs_dir_pattern(self):
        """Test backward compatibility: 'pattern' should work as 'dir_pattern'"""
        config_data = {
            'sources': {'src': {'dir': '/source'}},
            'output': {
                'dir': '/output',
                'pattern': '%(year)d/%(month)02d',  # Old field name
                'duplicates_dir': 'duplicates',
                'db_file': 'photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        # Should fall back to 'pattern' when 'dir_pattern' is missing
        self.assertEqual(cfg.dir_pattern(), '%(year)d/%(month)02d')

    def test_dir_pattern_takes_precedence(self):
        """Test that dir_pattern takes precedence over pattern"""
        config_data = {
            'sources': {'src': {'dir': '/source'}},
            'output': {
                'dir': '/output',
                'dir_pattern': '%(year)d/new_pattern',
                'pattern': '%(year)d/old_pattern',
                'duplicates_dir': 'duplicates',
                'db_file': 'photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        # dir_pattern should take precedence
        self.assertEqual(cfg.dir_pattern(), '%(year)d/new_pattern')

    def test_chmod_octal_parsing(self):
        """Test various octal chmod formats are parsed correctly"""
        test_cases = [
            ('0o755', 0o755),
            ('0o644', 0o644),
            ('0o777', 0o777),
            ('0o700', 0o700),
            ('0o774', 0o774)
        ]

        for chmod_str, expected_value in test_cases:
            config_data = {
                'sources': {'src': {'dir': '/source'}},
                'output': {
                    'dir': '/output',
                    'duplicates_dir': 'duplicates',
                    'db_file': 'photosort.db',
                    'chmod': chmod_str
                }
            }
            config_path = self._create_config_file(config_data)
            cfg = config.Config(config_path)

            self.assertEqual(cfg.output_chmod(), expected_value,
                           f"Failed for chmod: {chmod_str}")

    def test_invalid_yaml_file_not_found(self):
        """Test that FileNotFoundError is raised for missing config file"""
        with self.assertRaises(FileNotFoundError):
            config.Config('/nonexistent/config.yml')

    def test_invalid_yaml_malformed(self):
        """Test that invalid YAML raises an exception"""
        fd, path = tempfile.mkstemp(suffix='.yml', dir=self._temp_dir)
        with os.fdopen(fd, 'w') as f:
            f.write("sources:\n  - invalid:\n    - badly: nested\n  }")

        with self.assertRaises(yaml.YAMLError):
            config.Config(path)

    def test_missing_required_output_dir(self):
        """Test that missing required 'output.dir' raises KeyError"""
        config_data = {
            'sources': {'src': {'dir': '/source'}},
            'output': {
                'duplicates_dir': 'duplicates',
                'db_file': 'photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        with self.assertRaises(KeyError):
            cfg.output_dir()

    def test_missing_required_sources(self):
        """Test that missing 'sources' raises KeyError"""
        config_data = {
            'output': {
                'dir': '/output',
                'duplicates_dir': 'duplicates',
                'db_file': 'photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        with self.assertRaises(KeyError):
            cfg.sources()

    def test_missing_required_db_file(self):
        """Test that missing 'db_file' raises KeyError"""
        config_data = {
            'sources': {'src': {'dir': '/source'}},
            'output': {
                'dir': '/output',
                'duplicates_dir': 'duplicates',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        with self.assertRaises(KeyError):
            cfg.db_file()

    def test_missing_required_duplicates_dir(self):
        """Test that missing 'duplicates_dir' raises KeyError"""
        config_data = {
            'sources': {'src': {'dir': '/source'}},
            'output': {
                'dir': '/output',
                'db_file': 'photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        with self.assertRaises(KeyError):
            cfg.duplicates_dir()

    def test_missing_required_chmod(self):
        """Test that missing 'chmod' raises KeyError"""
        config_data = {
            'sources': {'src': {'dir': '/source'}},
            'output': {
                'dir': '/output',
                'duplicates_dir': 'duplicates',
                'db_file': 'photosort.db'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        with self.assertRaises(KeyError):
            cfg.output_chmod()

    def test_complex_dir_pattern(self):
        """Test complex directory patterns with multiple variables"""
        config_data = {
            'sources': {'src': {'dir': '/source'}},
            'output': {
                'dir': '/output',
                'dir_pattern': '%(year)d/%(year)04d_%(month)02d_%(day)02d',
                'duplicates_dir': 'duplicates',
                'db_file': 'photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        self.assertEqual(cfg.dir_pattern(),
                        '%(year)d/%(year)04d_%(month)02d_%(day)02d')

    def test_complex_file_prefix(self):
        """Test complex file prefix patterns"""
        config_data = {
            'sources': {'src': {'dir': '/source'}},
            'output': {
                'dir': '/output',
                'dir_pattern': '%(year)d',
                'file_prefix': '%(year)d%(month)02d%(day)02d%(hour)02d%(minute)02d%(second)02d_',
                'duplicates_dir': 'duplicates',
                'db_file': 'photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        self.assertEqual(cfg.file_prefix(),
                        '%(year)d%(month)02d%(day)02d%(hour)02d%(minute)02d%(second)02d_')

    def test_multiple_sources(self):
        """Test configuration with multiple source directories"""
        config_data = {
            'sources': {
                'dropbox': {'dir': '/Users/test/Dropbox/Camera Uploads'},
                'nasinbox': {'dir': '/mnt/nas/Pictures/inbox'},
                'phone': {'dir': '/media/phone/DCIM'},
                'camera': {'dir': '/media/camera/SD_CARD'}
            },
            'output': {
                'dir': '/output',
                'duplicates_dir': 'duplicates',
                'db_file': 'photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        sources = cfg.sources()
        self.assertEqual(len(sources), 4)
        self.assertIn('dropbox', sources)
        self.assertIn('nasinbox', sources)
        self.assertIn('phone', sources)
        self.assertIn('camera', sources)

    def test_empty_file_prefix(self):
        """Test explicitly empty file_prefix"""
        config_data = {
            'sources': {'src': {'dir': '/source'}},
            'output': {
                'dir': '/output',
                'dir_pattern': '%(year)d',
                'file_prefix': '',
                'duplicates_dir': 'duplicates',
                'db_file': 'photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        self.assertEqual(cfg.file_prefix(), '')

    def test_fallback_to_file_date_default_false(self):
        """Test that fallback_to_file_date defaults to False when not specified"""
        config_data = {
            'sources': {
                'source1': {'dir': '/path/to/source1'}
            },
            'output': {
                'dir': '/output',
                'dir_pattern': '%(year)d',
                'duplicates_dir': 'duplicates',
                'db_file': 'photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        self.assertFalse(cfg.source_fallback_to_file_date('source1'))

    def test_fallback_to_file_date_explicit_true(self):
        """Test that fallback_to_file_date can be explicitly set to True"""
        config_data = {
            'sources': {
                'source1': {'dir': '/path/to/source1', 'fallback_to_file_date': True}
            },
            'output': {
                'dir': '/output',
                'dir_pattern': '%(year)d',
                'duplicates_dir': 'duplicates',
                'db_file': 'photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        self.assertTrue(cfg.source_fallback_to_file_date('source1'))

    def test_fallback_to_file_date_explicit_false(self):
        """Test that fallback_to_file_date can be explicitly set to False"""
        config_data = {
            'sources': {
                'source1': {'dir': '/path/to/source1', 'fallback_to_file_date': False}
            },
            'output': {
                'dir': '/output',
                'dir_pattern': '%(year)d',
                'duplicates_dir': 'duplicates',
                'db_file': 'photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        self.assertFalse(cfg.source_fallback_to_file_date('source1'))

    def test_fallback_to_file_date_multiple_sources(self):
        """Test that different sources can have different fallback settings"""
        config_data = {
            'sources': {
                'source1': {'dir': '/path/to/source1', 'fallback_to_file_date': True},
                'source2': {'dir': '/path/to/source2', 'fallback_to_file_date': False},
                'source3': {'dir': '/path/to/source3'}  # Default: False
            },
            'output': {
                'dir': '/output',
                'dir_pattern': '%(year)d',
                'duplicates_dir': 'duplicates',
                'db_file': 'photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        self.assertTrue(cfg.source_fallback_to_file_date('source1'))
        self.assertFalse(cfg.source_fallback_to_file_date('source2'))
        self.assertFalse(cfg.source_fallback_to_file_date('source3'))

    def test_fallback_to_file_date_nonexistent_source(self):
        """Test that querying a nonexistent source returns False"""
        config_data = {
            'sources': {
                'source1': {'dir': '/path/to/source1'}
            },
            'output': {
                'dir': '/output',
                'dir_pattern': '%(year)d',
                'duplicates_dir': 'duplicates',
                'db_file': 'photosort.db',
                'chmod': '0o644'
            }
        }
        config_path = self._create_config_file(config_data)
        cfg = config.Config(config_path)

        self.assertFalse(cfg.source_fallback_to_file_date('nonexistent'))


if __name__ == '__main__':
    test.test.main()
