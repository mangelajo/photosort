# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import logging
import os
from typing import List, Optional

try:
    from ultralytics import YOLO
    import cv2
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False


class YoloNotAvailableError(Exception):
    """Raised when YOLO dependencies are not installed."""
    pass


class YoloTagger:
    """
    Handles YOLO11 object detection and tagging of photos.

    Uses YOLO to detect objects in images and stores detected class names
    (e.g., 'cat', 'dog', 'person') as EXIF keywords. Does NOT store
    bounding box coordinates or object locations.
    """

    def __init__(self, model_path: str = 'yolo11x.pt', confidence: float = 0.25):
        """
        Initialize YOLO tagger.

        Args:
            model_path: Path to YOLO model file (will auto-download if not found)
            confidence: Confidence threshold for detections (0.0-1.0)

        Raises:
            YoloNotAvailableError: If ultralytics/torch not installed
            ValueError: If confidence is not between 0 and 1
        """
        if not YOLO_AVAILABLE:
            raise YoloNotAvailableError(
                "YOLO dependencies not installed. "
                "Install with: pip install photosort[yolo]"
            )

        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {confidence}")

        self.model_path = model_path
        self.confidence = confidence

        # Initialize YOLO model (will auto-download if needed)
        logging.info(f"Loading YOLO model: {model_path}")
        self.model = YOLO(model_path)
        logging.info(f"YOLO model loaded successfully")

    def detect_objects(self, image_path: str) -> List[str]:
        """
        Detect objects in an image and return list of class names.

        Args:
            image_path: Path to image file

        Returns:
            List of detected object class names (e.g., ['cat', 'dog', 'person'])
            Only unique class names, no duplicates, no coordinates.

        Raises:
            FileNotFoundError: If image file doesn't exist
            Exception: If detection fails
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        logging.debug(f"Running YOLO detection on: {image_path}")

        # Run inference
        results = self.model.predict(
            source=image_path,
            conf=self.confidence,
            verbose=False
        )

        # Extract unique class names
        labels = self.get_unique_labels(results)

        logging.debug(f"Detected objects in {image_path}: {labels}")
        return labels

    def get_unique_labels(self, results) -> List[str]:
        """
        Extract unique class names from YOLO results.

        Args:
            results: YOLO prediction results

        Returns:
            Sorted list of unique class names
        """
        if not results or len(results) == 0:
            return []

        # Get the first result (single image)
        result = results[0]

        # Extract class names from boxes
        if result.boxes is None or len(result.boxes) == 0:
            return []

        # Get unique class names
        class_names = set()
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = result.names[class_id]
            class_names.add(class_name)

        return sorted(list(class_names))

    def add_tags_to_photo(self, photo_path: str, tags: List[str]) -> bool:
        """
        Add object detection tags to photo EXIF keywords.

        Merges new tags with existing keywords to avoid overwriting.

        Args:
            photo_path: Path to photo file
            tags: List of tags to add (object class names)

        Returns:
            True if successful, False otherwise

        Note:
            Uses exiftool to write both IPTC:Keywords and XMP:Subject fields
            for maximum compatibility across formats (JPEG, HEIC, etc.).
            Tags are simple class names, no coordinates or locations.
            Existing keywords are preserved and merged with new tags.
        """
        if not tags:
            logging.debug(f"No tags to add for {photo_path}")
            return True

        try:
            # Import exiftool locally to avoid circular dependency
            from . import exif

            # Ensure exiftool is started
            if exif.et is None:
                exif.start()

            # Read existing keywords first to merge (not replace)
            # Try both IPTC:Keywords (for JPEG) and XMP:Subject (for HEIC and others)
            try:
                metadata = exif.et.get_tags(photo_path, ['IPTC:Keywords', 'XMP:Subject'])
                existing_iptc = metadata[0].get('IPTC:Keywords', [])
                existing_xmp = metadata[0].get('XMP:Subject', [])

                # Ensure they're lists
                if isinstance(existing_iptc, str):
                    existing_iptc = [existing_iptc]
                elif not isinstance(existing_iptc, list):
                    existing_iptc = []

                if isinstance(existing_xmp, str):
                    existing_xmp = [existing_xmp]
                elif not isinstance(existing_xmp, list):
                    existing_xmp = []

                # Merge both sources
                existing_keywords = list(set(existing_iptc + existing_xmp))

                logging.debug(f"Existing keywords in {photo_path}: IPTC={existing_iptc}, XMP={existing_xmp}")
            except Exception as read_error:
                logging.debug(f"No existing keywords or read error: {read_error}")
                existing_keywords = []

            # Merge new tags with existing, removing duplicates
            all_tags = list(set(existing_keywords + tags))
            all_tags.sort()  # Keep consistent order

            # Format tags for exiftool - write to both IPTC and XMP for maximum compatibility
            # IPTC:Keywords works for JPEG, XMP:Subject works for HEIC and others
            tag_dict = {
                'IPTC:Keywords': all_tags,
                'XMP:Subject': all_tags
            }

            logging.info(f"Adding tags to {photo_path}: {tags} (total keywords: {all_tags})")
            logging.debug(f"Calling exif.et.set_tags with tags: {tag_dict}")

            try:
                exif.et.set_tags(photo_path, tag_dict)
                logging.debug(f"Successfully set tags for {photo_path}")
            except Exception as set_error:
                logging.error(f"set_tags failed: {set_error}")
                raise

            return True

        except Exception as e:
            logging.error(f"Failed to add tags to {photo_path}: {e}")
            return False

    def visualize_detections(self, image_path: str, show_window: bool = True) -> Optional[any]:
        """
        Visualize YOLO detections with bounding boxes.

        Args:
            image_path: Path to image file
            show_window: If True, display cv2 window (requires display)

        Returns:
            Annotated image as numpy array, or None if failed

        Note:
            This is for interactive visualization only.
            Bounding boxes are NOT stored in EXIF data.
            Window updates automatically without waiting for keypress.
            Press ESC to close the visualization window.
        """
        if not os.path.exists(image_path):
            logging.error(f"Image not found: {image_path}")
            return None

        try:
            # Run inference
            results = self.model.predict(
                source=image_path,
                conf=self.confidence,
                verbose=False
            )

            # Get annotated image
            annotated = results[0].plot()

            if show_window:
                try:
                    # Use a constant window name so the same window is reused
                    window_title = "YOLO Detections"

                    cv2.imshow(window_title, annotated)
                    # Wait 1ms to allow window to update without blocking
                    # User can press any key to pause, or ESC to close window
                    key = cv2.waitKey(1)
                    if key == 27:  # ESC key
                        cv2.destroyAllWindows()
                except Exception as e:
                    logging.warning(f"Could not display window (headless?): {e}")

            return annotated

        except Exception as e:
            logging.error(f"Visualization failed for {image_path}: {e}")
            return None
