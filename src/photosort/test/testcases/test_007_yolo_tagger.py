# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import os
import unittest
from unittest import mock

from photosort.test import TestCase

# Try to import YOLO dependencies
try:
    from photosort import yolo_tagger
    YOLO_AVAILABLE = yolo_tagger.YOLO_AVAILABLE
except ImportError:
    YOLO_AVAILABLE = False


@unittest.skipUnless(YOLO_AVAILABLE, "YOLO dependencies not installed")
class TestYoloTaggerInit(TestCase):
    """Test YOLO tagger initialization."""

    def test_model_loading_success(self):
        """Test that YOLO model loads successfully."""
        # Use small model for faster testing
        tagger = yolo_tagger.YoloTagger(model_path='yolo11n.pt', confidence=0.25)
        self.assertIsNotNone(tagger.model)
        self.assertEqual(tagger.confidence, 0.25)
        self.assertEqual(tagger.model_path, 'yolo11n.pt')

    def test_invalid_confidence_low(self):
        """Test that confidence below 0.0 raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            yolo_tagger.YoloTagger(model_path='yolo11n.pt', confidence=-0.1)
        self.assertIn("between 0.0 and 1.0", str(ctx.exception))

    def test_invalid_confidence_high(self):
        """Test that confidence above 1.0 raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            yolo_tagger.YoloTagger(model_path='yolo11n.pt', confidence=1.5)
        self.assertIn("between 0.0 and 1.0", str(ctx.exception))

    def test_confidence_boundaries(self):
        """Test that confidence at boundaries (0.0 and 1.0) works."""
        tagger1 = yolo_tagger.YoloTagger(model_path='yolo11n.pt', confidence=0.0)
        self.assertEqual(tagger1.confidence, 0.0)

        tagger2 = yolo_tagger.YoloTagger(model_path='yolo11n.pt', confidence=1.0)
        self.assertEqual(tagger2.confidence, 1.0)


@unittest.skipUnless(YOLO_AVAILABLE, "YOLO dependencies not installed")
class TestYoloObjectDetection(TestCase):
    """Test YOLO object detection functionality."""

    def setUp(self):
        super().setUp()
        # Initialize tagger once for all tests (faster)
        self.tagger = yolo_tagger.YoloTagger(model_path='yolo11n.pt', confidence=0.25)

    def test_detect_objects_coco_boats(self):
        """Test detection on COCO boats image."""
        image_path = self.get_data_path('coco/boats.jpg')
        labels = self.tagger.detect_objects(image_path)

        # Should detect something in the image
        self.assertIsInstance(labels, list)
        self.assertGreater(len(labels), 0, "Should detect at least one object")
        # All detected items should be strings (class names)
        for label in labels:
            self.assertIsInstance(label, str)

    def test_detect_objects_coco_bus(self):
        """Test detection on COCO bus/street image."""
        image_path = self.get_data_path('coco/bus.jpg')
        labels = self.tagger.detect_objects(image_path)

        # Should detect vehicles and people
        self.assertIsInstance(labels, list)
        self.assertGreater(len(labels), 0)
        detected_set = set(labels)
        # At least one vehicle-related object
        expected = {'bus', 'car', 'truck', 'person'}
        self.assertTrue(len(detected_set & expected) > 0,
                       f"Expected to find at least one of {expected}, got {labels}")

    def test_detect_objects_coco_person(self):
        """Test detection on COCO person image."""
        image_path = self.get_data_path('coco/zidane.jpg')
        labels = self.tagger.detect_objects(image_path)

        # Should detect person
        self.assertIsInstance(labels, list)
        self.assertGreater(len(labels), 0)
        self.assertIn('person', labels)

    def test_detect_objects_returns_class_names_only(self):
        """Test that detection returns only class names, not coordinates."""
        image_path = self.get_data_path('coco/boats.jpg')
        labels = self.tagger.detect_objects(image_path)

        # All items should be strings (class names)
        for label in labels:
            self.assertIsInstance(label, str)
            # Should not contain numbers or special chars indicating coordinates
            self.assertNotIn('[', label)
            self.assertNotIn(']', label)
            self.assertNotIn(',', label)
            # Should be reasonable length for a class name
            self.assertLess(len(label), 50)

    def test_detect_objects_missing_file(self):
        """Test that missing file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            self.tagger.detect_objects('/nonexistent/path/to/image.jpg')

    def test_get_unique_labels_deduplication(self):
        """Test that get_unique_labels removes duplicates and sorts."""
        # Run detection which internally uses get_unique_labels
        image_path = self.get_data_path('coco/boats.jpg')
        labels = self.tagger.detect_objects(image_path)

        # Labels should be unique (no duplicates)
        self.assertEqual(len(labels), len(set(labels)))

        # Labels should be sorted
        self.assertEqual(labels, sorted(labels))

    def test_confidence_threshold_filtering(self):
        """Test that confidence threshold affects number of detections."""
        # Low confidence should detect more objects
        tagger_low = yolo_tagger.YoloTagger(model_path='yolo11n.pt', confidence=0.1)
        image_path = self.get_data_path('coco/boats.jpg')
        labels_low = tagger_low.detect_objects(image_path)

        # High confidence should detect fewer objects
        tagger_high = yolo_tagger.YoloTagger(model_path='yolo11n.pt', confidence=0.9)
        labels_high = tagger_high.detect_objects(image_path)

        # Low confidence should have >= detections than high confidence
        self.assertGreaterEqual(len(labels_low), len(labels_high))


@unittest.skipUnless(YOLO_AVAILABLE, "YOLO dependencies not installed")
class TestYoloTagging(TestCase):
    """Test YOLO EXIF tagging functionality."""

    def setUp(self):
        super().setUp()
        self.tagger = yolo_tagger.YoloTagger(model_path='yolo11n.pt', confidence=0.25)

        # Copy a test image to temp directory for tagging
        import shutil
        self.test_image = os.path.join(self._temp_dir, 'test_image.jpg')
        source_image = self.get_data_path('coco/boats.jpg')
        shutil.copy(source_image, self.test_image)

    def test_add_tags_to_photo_exif_write(self):
        """Test that tags are written to photo EXIF."""
        tags = ['cat', 'dog', 'person']
        result = self.tagger.add_tags_to_photo(self.test_image, tags)
        self.assertTrue(result)

    def test_add_tags_to_photo_verify_readback(self):
        """Test that written tags can be read back from EXIF."""
        from photosort import exif

        tags = ['boat', 'person', 'water']
        result = self.tagger.add_tags_to_photo(self.test_image, tags)
        self.assertTrue(result)

        # Read back the tags
        metadata = exif.et.get_tags(self.test_image, ['IPTC:Keywords'])
        written_tags = metadata[0].get('IPTC:Keywords', [])

        # Ensure written_tags is a list
        if isinstance(written_tags, str):
            written_tags = [written_tags]

        # Check that our tags are present
        for tag in tags:
            self.assertIn(tag, written_tags,
                         f"Tag '{tag}' not found in EXIF. Got: {written_tags}")

    def test_tags_are_label_names_not_coordinates(self):
        """Test that stored tags are simple label names."""
        from photosort import exif

        # Run detection and tag
        labels = self.tagger.detect_objects(self.test_image)
        self.tagger.add_tags_to_photo(self.test_image, labels)

        # Read back tags
        metadata = exif.et.get_tags(self.test_image, ['IPTC:Keywords'])
        written_tags = metadata[0].get('IPTC:Keywords', [])

        if isinstance(written_tags, str):
            written_tags = [written_tags]

        # Verify all tags are simple strings without coordinates
        for tag in written_tags:
            self.assertIsInstance(tag, str)
            # Should not contain coordinate indicators
            self.assertNotIn('[', tag)
            self.assertNotIn(']', tag)
            self.assertNotIn('(', tag)
            self.assertNotIn(')', tag)
            # Should not be JSON
            self.assertNotIn('{', tag)
            self.assertNotIn('}', tag)

    def test_add_tags_empty_list(self):
        """Test that empty tag list returns True without error."""
        result = self.tagger.add_tags_to_photo(self.test_image, [])
        self.assertTrue(result)

    def test_add_tags_merges_with_existing(self):
        """Test that new tags are merged with existing keywords, not replaced."""
        from photosort import exif

        # First, add some initial tags
        initial_tags = ['sunset', 'landscape']
        result1 = self.tagger.add_tags_to_photo(self.test_image, initial_tags)
        self.assertTrue(result1)

        # Verify initial tags were written
        metadata = exif.et.get_tags(self.test_image, ['IPTC:Keywords'])
        keywords = metadata[0].get('IPTC:Keywords', [])
        if isinstance(keywords, str):
            keywords = [keywords]
        self.assertEqual(set(keywords), set(initial_tags))

        # Now add YOLO tags
        yolo_tags = ['boat', 'person']
        result2 = self.tagger.add_tags_to_photo(self.test_image, yolo_tags)
        self.assertTrue(result2)

        # Verify both sets of tags are present (merged, not replaced)
        metadata = exif.et.get_tags(self.test_image, ['IPTC:Keywords'])
        final_keywords = metadata[0].get('IPTC:Keywords', [])
        if isinstance(final_keywords, str):
            final_keywords = [final_keywords]

        expected_tags = set(initial_tags + yolo_tags)
        self.assertEqual(set(final_keywords), expected_tags,
                        f"Expected merged tags {expected_tags}, got {set(final_keywords)}")

        # Check each tag individually
        for tag in initial_tags + yolo_tags:
            self.assertIn(tag, final_keywords,
                         f"Tag '{tag}' should be present after merge")

    def test_add_tags_deduplicates(self):
        """Test that duplicate tags are not added twice."""
        from photosort import exif

        # Add tags with some duplicates
        tags1 = ['cat', 'dog', 'bird']
        self.tagger.add_tags_to_photo(self.test_image, tags1)

        # Add overlapping tags
        tags2 = ['dog', 'bird', 'fish']
        self.tagger.add_tags_to_photo(self.test_image, tags2)

        # Read back and verify no duplicates
        metadata = exif.et.get_tags(self.test_image, ['IPTC:Keywords'])
        keywords = metadata[0].get('IPTC:Keywords', [])
        if isinstance(keywords, str):
            keywords = [keywords]

        # Should have unique tags only
        self.assertEqual(len(keywords), len(set(keywords)),
                        f"Found duplicate tags: {keywords}")

        # Should have all unique tags
        expected = {'cat', 'dog', 'bird', 'fish'}
        self.assertEqual(set(keywords), expected)


@unittest.skipUnless(YOLO_AVAILABLE, "YOLO dependencies not installed")
class TestYoloVisualization(TestCase):
    """Test YOLO visualization functionality."""

    def setUp(self):
        super().setUp()
        self.tagger = yolo_tagger.YoloTagger(model_path='yolo11n.pt', confidence=0.25)

    def test_visualize_detections_creates_annotated_image(self):
        """Test that visualization creates an annotated image."""
        image_path = self.get_data_path('coco/boats.jpg')

        # Mock cv2.imshow to avoid requiring display
        with mock.patch('cv2.imshow'), mock.patch('cv2.waitKey'), mock.patch('cv2.destroyAllWindows'):
            annotated = self.tagger.visualize_detections(image_path, show_window=True)

        # Should return an image
        self.assertIsNotNone(annotated)
        # Should be a numpy array
        import numpy as np
        self.assertIsInstance(annotated, np.ndarray)

    def test_visualize_detections_without_window(self):
        """Test visualization without showing window."""
        image_path = self.get_data_path('coco/boats.jpg')
        annotated = self.tagger.visualize_detections(image_path, show_window=False)

        # Should still return annotated image
        self.assertIsNotNone(annotated)

    def test_visualize_missing_file(self):
        """Test that visualization handles missing file gracefully."""
        result = self.tagger.visualize_detections('/nonexistent/image.jpg', show_window=False)
        self.assertIsNone(result)


@unittest.skipUnless(YOLO_AVAILABLE, "YOLO dependencies not installed")
class TestYoloEndToEndTagging(TestCase):
    """Test end-to-end tagging workflow with actual EXIF verification."""

    def setUp(self):
        super().setUp()
        self.tagger = yolo_tagger.YoloTagger(model_path='yolo11n.pt', confidence=0.25)

        # Initialize exiftool
        from photosort import exif
        if exif.et is None:
            exif.start()

    def test_end_to_end_tagging_boats_jpg(self):
        """Test complete workflow: detect + tag + verify for boats.jpg."""
        import shutil
        from photosort import exif

        # Copy test image to temp directory
        source = self.get_data_path('coco/boats.jpg')
        test_image = os.path.join(self._temp_dir, 'boats.jpg')
        shutil.copy(source, test_image)

        # Detect objects
        labels = self.tagger.detect_objects(test_image)
        self.assertGreater(len(labels), 0, "Should detect at least one object")

        # Tag the photo
        result = self.tagger.add_tags_to_photo(test_image, labels)
        self.assertTrue(result, "Tagging should succeed")

        # Verify tags were actually written to EXIF
        metadata = exif.et.get_tags(test_image, ['IPTC:Keywords'])
        keywords = metadata[0].get('IPTC:Keywords', [])
        if isinstance(keywords, str):
            keywords = [keywords]

        # Should have keywords
        self.assertGreater(len(keywords), 0, "Keywords should be written to EXIF")

        # All detected labels should be in keywords
        for label in labels:
            self.assertIn(label, keywords,
                         f"Detected label '{label}' should be in EXIF keywords")

    def test_end_to_end_tagging_bus_jpg(self):
        """Test complete workflow: detect + tag + verify for bus.jpg."""
        import shutil
        from photosort import exif

        source = self.get_data_path('coco/bus.jpg')
        test_image = os.path.join(self._temp_dir, 'bus.jpg')
        shutil.copy(source, test_image)

        # Detect and tag
        labels = self.tagger.detect_objects(test_image)
        self.assertGreater(len(labels), 0)
        result = self.tagger.add_tags_to_photo(test_image, labels)
        self.assertTrue(result)

        # Verify EXIF
        metadata = exif.et.get_tags(test_image, ['IPTC:Keywords'])
        keywords = metadata[0].get('IPTC:Keywords', [])
        if isinstance(keywords, str):
            keywords = [keywords]

        self.assertGreater(len(keywords), 0)
        for label in labels:
            self.assertIn(label, keywords)

    def test_end_to_end_tagging_zidane_jpg(self):
        """Test complete workflow: detect + tag + verify for zidane.jpg."""
        import shutil
        from photosort import exif

        source = self.get_data_path('coco/zidane.jpg')
        test_image = os.path.join(self._temp_dir, 'zidane.jpg')
        shutil.copy(source, test_image)

        # Detect and tag
        labels = self.tagger.detect_objects(test_image)
        self.assertGreater(len(labels), 0)
        self.assertIn('person', labels, "Should detect person in zidane.jpg")

        result = self.tagger.add_tags_to_photo(test_image, labels)
        self.assertTrue(result)

        # Verify EXIF
        metadata = exif.et.get_tags(test_image, ['IPTC:Keywords'])
        keywords = metadata[0].get('IPTC:Keywords', [])
        if isinstance(keywords, str):
            keywords = [keywords]

        self.assertIn('person', keywords, "EXIF should contain 'person' tag")

    def test_end_to_end_tagging_heic(self):
        """Test complete workflow: detect + tag + verify for HEIC file."""
        import shutil
        from photosort import exif

        source = self.get_data_path('coco/20250926220424_IMG_4861.HEIC')
        if not os.path.exists(source):
            self.skipTest("HEIC test file not available")

        test_image = os.path.join(self._temp_dir, 'test_image.HEIC')
        shutil.copy(source, test_image)

        # Detect objects
        labels = self.tagger.detect_objects(test_image)
        self.assertGreater(len(labels), 0, "Should detect objects in HEIC file")

        # Tag the photo
        result = self.tagger.add_tags_to_photo(test_image, labels)
        self.assertTrue(result, "Tagging HEIC file should succeed")

        # Verify tags were actually written to EXIF
        # HEIC files use XMP:Subject, not IPTC:Keywords
        metadata = exif.et.get_tags(test_image, ['IPTC:Keywords', 'XMP:Subject'])
        iptc_keywords = metadata[0].get('IPTC:Keywords', [])
        xmp_keywords = metadata[0].get('XMP:Subject', [])

        if isinstance(iptc_keywords, str):
            iptc_keywords = [iptc_keywords]
        if isinstance(xmp_keywords, str):
            xmp_keywords = [xmp_keywords]

        # HEIC should have XMP:Subject
        keywords = xmp_keywords if xmp_keywords else iptc_keywords

        # Should have keywords
        self.assertGreater(len(keywords), 0,
                          "Keywords should be written to HEIC EXIF (XMP:Subject)")

        # All detected labels should be in keywords
        for label in labels:
            self.assertIn(label, keywords,
                         f"Detected label '{label}' should be in HEIC EXIF keywords")

        # Verify we can read them back again (double check)
        metadata2 = exif.et.get_tags(test_image, ['IPTC:Keywords', 'XMP:Subject'])
        iptc_keywords2 = metadata2[0].get('IPTC:Keywords', [])
        xmp_keywords2 = metadata2[0].get('XMP:Subject', [])
        if isinstance(iptc_keywords2, str):
            iptc_keywords2 = [iptc_keywords2]
        if isinstance(xmp_keywords2, str):
            xmp_keywords2 = [xmp_keywords2]
        keywords2 = xmp_keywords2 if xmp_keywords2 else iptc_keywords2

        self.assertEqual(set(keywords), set(keywords2),
                        "Keywords should be persistent after writing")

    def test_end_to_end_tagging_is_additive(self):
        """Test that tagging is additive and doesn't replace existing keywords."""
        import shutil
        from photosort import exif

        # Use a JPG file for this test
        source = self.get_data_path('coco/boats.jpg')
        test_image = os.path.join(self._temp_dir, 'test_additive.jpg')
        shutil.copy(source, test_image)

        # First, manually add some existing keywords
        existing_tags = ['vacation', 'summer', 'beach']
        initial_tag_dict = {'IPTC:Keywords': existing_tags}
        exif.et.set_tags(test_image, initial_tag_dict)

        # Verify initial tags were written
        metadata = exif.et.get_tags(test_image, ['IPTC:Keywords', 'XMP:Subject'])
        initial_keywords = metadata[0].get('IPTC:Keywords', [])
        if isinstance(initial_keywords, str):
            initial_keywords = [initial_keywords]
        self.assertEqual(set(initial_keywords), set(existing_tags),
                        "Initial tags should be written")

        # Now run YOLO detection and tagging
        labels = self.tagger.detect_objects(test_image)
        self.assertGreater(len(labels), 0, "Should detect objects")

        result = self.tagger.add_tags_to_photo(test_image, labels)
        self.assertTrue(result, "YOLO tagging should succeed")

        # Verify both original and YOLO tags are present (additive, not replacement)
        metadata = exif.et.get_tags(test_image, ['IPTC:Keywords', 'XMP:Subject'])
        final_iptc = metadata[0].get('IPTC:Keywords', [])
        final_xmp = metadata[0].get('XMP:Subject', [])

        if isinstance(final_iptc, str):
            final_iptc = [final_iptc]
        if isinstance(final_xmp, str):
            final_xmp = [final_xmp]

        # Combine both IPTC and XMP keywords
        final_keywords = set(final_iptc + final_xmp)

        # Verify all original tags are still present
        for tag in existing_tags:
            self.assertIn(tag, final_keywords,
                         f"Original tag '{tag}' should still be present after YOLO tagging")

        # Verify YOLO tags were added
        for label in labels:
            self.assertIn(label, final_keywords,
                         f"YOLO label '{label}' should be added to existing tags")

        # Verify we have more tags now than initially
        self.assertGreaterEqual(len(final_keywords), len(existing_tags) + len(labels),
                               "Should have at least original tags + YOLO tags")

    def test_end_to_end_heic_tagging_is_additive(self):
        """Test that HEIC tagging is also additive."""
        import shutil
        from photosort import exif

        source = self.get_data_path('coco/20250926220424_IMG_4861.HEIC')
        if not os.path.exists(source):
            self.skipTest("HEIC test file not available")

        test_image = os.path.join(self._temp_dir, 'test_additive.HEIC')
        shutil.copy(source, test_image)

        # Add existing XMP tags (HEIC uses XMP:Subject)
        existing_tags = ['portrait', 'outdoor']
        initial_tag_dict = {'XMP:Subject': existing_tags}
        exif.et.set_tags(test_image, initial_tag_dict)

        # Verify initial tags
        metadata = exif.et.get_tags(test_image, ['XMP:Subject'])
        initial_keywords = metadata[0].get('XMP:Subject', [])
        if isinstance(initial_keywords, str):
            initial_keywords = [initial_keywords]
        self.assertEqual(set(initial_keywords), set(existing_tags))

        # Run YOLO tagging
        labels = self.tagger.detect_objects(test_image)
        self.assertGreater(len(labels), 0)

        result = self.tagger.add_tags_to_photo(test_image, labels)
        self.assertTrue(result)

        # Verify additive behavior
        metadata = exif.et.get_tags(test_image, ['IPTC:Keywords', 'XMP:Subject'])
        final_iptc = metadata[0].get('IPTC:Keywords', [])
        final_xmp = metadata[0].get('XMP:Subject', [])

        if isinstance(final_iptc, str):
            final_iptc = [final_iptc]
        if isinstance(final_xmp, str):
            final_xmp = [final_xmp]

        final_keywords = set(final_iptc + final_xmp)

        # Verify original tags preserved
        for tag in existing_tags:
            self.assertIn(tag, final_keywords,
                         f"Original HEIC tag '{tag}' should be preserved")

        # Verify YOLO tags added
        for label in labels:
            self.assertIn(label, final_keywords,
                         f"YOLO label '{label}' should be added to HEIC")


class TestYoloNotAvailable(TestCase):
    """Test behavior when YOLO is not available."""

    @unittest.skipIf(YOLO_AVAILABLE, "YOLO is available, skipping unavailable tests")
    def test_yolo_not_available_error(self):
        """Test that appropriate error is raised when YOLO not available."""
        # This test only runs when YOLO is NOT installed
        with self.assertRaises(NameError):
            # yolo_tagger module should not be importable
            yolo_tagger.YoloTagger()
