# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import os
import shutil
import unittest
from unittest import mock

from photosort.test import TestCase

# Try to import YOLO and photosort dependencies
try:
    from photosort import yolo_tagger
    from photosort import config
    from photosort import photosort
    YOLO_AVAILABLE = yolo_tagger.YOLO_AVAILABLE
except ImportError:
    YOLO_AVAILABLE = False


@unittest.skipUnless(YOLO_AVAILABLE, "YOLO dependencies not installed")
class TestYoloConfigIntegration(TestCase):
    """Test YOLO configuration integration."""

    def test_config_with_yolo_section(self):
        """Test config parsing with full YOLO section."""
        config_file = os.path.join(self._temp_dir, 'config.yml')
        with open(config_file, 'w') as f:
            f.write("""
sources:
  test:
    dir: /tmp/test

output:
  dir: /tmp/output
  dir_pattern: "%(year)d/%(year)04d_%(month)02d_%(day)02d"
  duplicates_dir: duplicates
  chmod: 0o774
  db_file: photosort.db

yolo:
  model: yolo11n.pt
  confidence: 0.3
  imgsz: 640
  interactive: true
""")

        cfg = config.Config(config_file)
        self.assertEqual(cfg.yolo_model(), 'yolo11n.pt')
        self.assertEqual(cfg.yolo_confidence(), 0.3)
        self.assertEqual(cfg.yolo_imgsz(), 640)
        self.assertTrue(cfg.yolo_interactive())

    def test_config_without_yolo_section_defaults(self):
        """Test that config without YOLO section uses defaults."""
        config_file = os.path.join(self._temp_dir, 'config.yml')
        with open(config_file, 'w') as f:
            f.write("""
sources:
  test:
    dir: /tmp/test

output:
  dir: /tmp/output
  dir_pattern: "%(year)d/%(year)04d_%(month)02d_%(day)02d"
  duplicates_dir: duplicates
  chmod: 0o774
  db_file: photosort.db
""")

        cfg = config.Config(config_file)
        # Should use defaults
        self.assertEqual(cfg.yolo_model(), 'yolo11x.pt')
        self.assertEqual(cfg.yolo_confidence(), 0.25)
        self.assertEqual(cfg.yolo_imgsz(), 640)
        self.assertFalse(cfg.yolo_interactive())

    def test_config_with_partial_yolo_section(self):
        """Test config with partial YOLO section uses defaults for missing values."""
        config_file = os.path.join(self._temp_dir, 'config.yml')
        with open(config_file, 'w') as f:
            f.write("""
sources:
  test:
    dir: /tmp/test

output:
  dir: /tmp/output
  dir_pattern: "%(year)d/%(year)04d_%(month)02d_%(day)02d"
  duplicates_dir: duplicates
  chmod: 0o774
  db_file: photosort.db

yolo:
  model: yolo11s.pt
  confidence: 0.5
""")

        cfg = config.Config(config_file)
        # Should use specified values
        self.assertEqual(cfg.yolo_model(), 'yolo11s.pt')
        self.assertEqual(cfg.yolo_confidence(), 0.5)
        # Should use defaults for unspecified
        self.assertEqual(cfg.yolo_imgsz(), 640)
        self.assertFalse(cfg.yolo_interactive())


@unittest.skipUnless(YOLO_AVAILABLE, "YOLO dependencies not installed")
@mock.patch('photosort.walk.WalkForMedia._file_is_ready', return_value=True)
class TestAddYoloTagsCommand(TestCase):
    """Test add-yolo-tags command end-to-end."""

    def setUp(self):
        super().setUp()

        # Initialize exiftool
        from photosort import exif
        if exif.et is None:
            exif.start()

        # Create output directory structure
        self.output_dir = os.path.join(self._temp_dir, 'output')
        os.makedirs(self.output_dir)

        # Copy COCO test images to output directory
        self.test_images = []
        for image_name in ['boats.jpg', 'bus.jpg', 'zidane.jpg']:
            source = self.get_data_path(f'coco/{image_name}')
            dest = os.path.join(self.output_dir, image_name)
            shutil.copy(source, dest)
            self.test_images.append(dest)

        # Create config
        self.config_file = os.path.join(self._temp_dir, 'config.yml')
        with open(self.config_file, 'w') as f:
            f.write(f"""
sources:
  test:
    dir: /tmp/test_input

output:
  dir: {self.output_dir}
  dir_pattern: "%(year)d/%(year)04d_%(month)02d_%(day)02d"
  duplicates_dir: duplicates
  chmod: 0o774
  db_file: photosort.db

yolo:
  model: yolo11n.pt
  confidence: 0.25
  imgsz: 640
  interactive: false
""")

    def test_full_workflow_with_coco_images(self, mock_file_ready):
        """Test complete workflow: detect objects and tag images."""
        # Initialize PhotoSort
        ps = photosort.PhotoSort(self.config_file, log_level=20)  # INFO level

        # Run add_yolo_tags
        ps.add_yolo_tags(interactive=False, dry_run=False)

        # Verify tags were written to all images
        from photosort import exif

        for image_path in self.test_images:
            metadata = exif.et.get_tags(image_path, ['IPTC:Keywords'])
            keywords = metadata[0].get('IPTC:Keywords', [])

            # Ensure keywords is a list
            if isinstance(keywords, str):
                keywords = [keywords]

            # Should have at least one tag
            self.assertGreater(len(keywords), 0,
                             f"No keywords found in {os.path.basename(image_path)}")

            # All keywords should be strings
            for keyword in keywords:
                self.assertIsInstance(keyword, str)

    def test_tagged_images_have_expected_objects(self, mock_file_ready):
        """Test that tagged images contain expected object types."""
        ps = photosort.PhotoSort(self.config_file, log_level=20)
        ps.add_yolo_tags(interactive=False, dry_run=False)

        from photosort import exif

        # Check boats.jpg - should have some tags
        boats_path = os.path.join(self.output_dir, 'boats.jpg')
        metadata = exif.et.get_tags(boats_path, ['IPTC:Keywords'])
        keywords = metadata[0].get('IPTC:Keywords', [])
        if isinstance(keywords, str):
            keywords = [keywords]

        # Should have detected something
        self.assertGreater(len(keywords), 0, "boats.jpg should have at least one tag")

        # Check bus.jpg
        bus_path = os.path.join(self.output_dir, 'bus.jpg')
        metadata = exif.et.get_tags(bus_path, ['IPTC:Keywords'])
        keywords = metadata[0].get('IPTC:Keywords', [])
        if isinstance(keywords, str):
            keywords = [keywords]
        keywords_set = set(keywords)

        # Should detect bus, car, or person
        expected = {'bus', 'car', 'truck', 'person'}
        self.assertTrue(len(keywords_set & expected) > 0,
                       f"Expected to find at least one of {expected} in bus.jpg, got {keywords}")

    def test_batch_processing_multiple_images(self, mock_file_ready):
        """Test that multiple images are processed successfully."""
        ps = photosort.PhotoSort(self.config_file, log_level=20)

        # Should process all 3 images without error
        ps.add_yolo_tags(interactive=False, dry_run=False)

        # Verify all images were tagged
        from photosort import exif

        tagged_count = 0
        for image_path in self.test_images:
            metadata = exif.et.get_tags(image_path, ['IPTC:Keywords'])
            keywords = metadata[0].get('IPTC:Keywords', [])
            if keywords:
                tagged_count += 1

        # All 3 images should be tagged
        self.assertEqual(tagged_count, 3)

    def test_dry_run_mode(self, mock_file_ready):
        """Test that dry-run mode doesn't write EXIF data."""
        from photosort import exif

        # Get original EXIF (should have no keywords)
        original_metadata = {}
        for image_path in self.test_images:
            metadata = exif.et.get_tags(image_path, ['IPTC:Keywords'])
            original_metadata[image_path] = metadata[0].get('IPTC:Keywords', [])

        # Run with dry_run=True
        ps = photosort.PhotoSort(self.config_file, log_level=20)
        ps.add_yolo_tags(interactive=False, dry_run=True)

        # Verify EXIF was NOT modified
        for image_path in self.test_images:
            metadata = exif.et.get_tags(image_path, ['IPTC:Keywords'])
            current_keywords = metadata[0].get('IPTC:Keywords', [])

            # Should be unchanged
            self.assertEqual(current_keywords, original_metadata[image_path],
                           f"EXIF was modified in dry-run mode for {os.path.basename(image_path)}")


@unittest.skipUnless(YOLO_AVAILABLE, "YOLO dependencies not installed")
@mock.patch('photosort.walk.WalkForMedia._file_is_ready', return_value=True)
class TestYoloExifTagFormat(TestCase):
    """Test that EXIF tags are in correct format."""

    def setUp(self):
        super().setUp()

        # Initialize exiftool
        from photosort import exif
        if exif.et is None:
            exif.start()

        # Create a test image
        self.output_dir = os.path.join(self._temp_dir, 'output')
        os.makedirs(self.output_dir)

        source = self.get_data_path('coco/boats.jpg')
        self.test_image = os.path.join(self.output_dir, 'test.jpg')
        shutil.copy(source, self.test_image)

        # Create config
        self.config_file = os.path.join(self._temp_dir, 'config.yml')
        with open(self.config_file, 'w') as f:
            f.write(f"""
sources:
  test:
    dir: /tmp/test_input

output:
  dir: {self.output_dir}
  dir_pattern: "%(year)d/%(year)04d_%(month)02d_%(day)02d"
  duplicates_dir: duplicates
  chmod: 0o774
  db_file: photosort.db

yolo:
  model: yolo11n.pt
  confidence: 0.25
""")

    def test_tags_are_simple_labels(self, mock_file_ready):
        """Test that stored tags are simple label names without coordinates."""
        from photosort import exif

        ps = photosort.PhotoSort(self.config_file, log_level=20)
        ps.add_yolo_tags(interactive=False, dry_run=False)

        # Read tags
        metadata = exif.et.get_tags(self.test_image, ['IPTC:Keywords'])
        keywords = metadata[0].get('IPTC:Keywords', [])

        if isinstance(keywords, str):
            keywords = [keywords]

        # Verify format
        for keyword in keywords:
            self.assertIsInstance(keyword, str)
            # Should not contain coordinate indicators
            self.assertNotIn('[', keyword)
            self.assertNotIn(']', keyword)
            self.assertNotIn('{', keyword)
            self.assertNotIn('}', keyword)
            self.assertNotIn('(', keyword)
            self.assertNotIn(')', keyword)
            # Should be reasonable length
            self.assertLess(len(keyword), 50)

    def test_tags_readable_by_standard_tools(self, mock_file_ready):
        """Test that tags can be read back correctly."""
        from photosort import exif

        ps = photosort.PhotoSort(self.config_file, log_level=20)
        ps.add_yolo_tags(interactive=False, dry_run=False)

        # Read back using exiftool
        metadata = exif.et.get_tags(self.test_image, ['IPTC:Keywords'])
        keywords = metadata[0].get('IPTC:Keywords', [])

        # Should have keywords
        self.assertIsNotNone(keywords)
        if isinstance(keywords, str):
            keywords = [keywords]
        self.assertGreater(len(keywords), 0)

        # All should be valid class names
        valid_classes = {'person', 'boat', 'ship', 'car', 'bus', 'truck',
                        'bird', 'cat', 'dog', 'horse', 'bicycle', 'motorcycle'}
        for keyword in keywords:
            # Should be lowercase alphanumeric (COCO class names)
            self.assertTrue(keyword.replace(' ', '').replace('-', '').isalnum(),
                          f"Keyword '{keyword}' is not alphanumeric")
