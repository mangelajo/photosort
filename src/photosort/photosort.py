# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import argparse
from importlib.metadata import version
import logging
import os
import sys
import time
import traceback


from . import config
from . import exif
from . import media
from . import photodb
from . import walk

# Monitor mode sleep interval in seconds between sync operations
MONITOR_INTERVAL_SECONDS = 10


class PhotoSort:

    def __init__(self, config_filename, log_level):

        self._config = config.Config(config_filename)
        self._setup_logging(log_level)
        self._photodb = photodb.PhotoDB(self._config)
        self._duplicates_dir = self._config.duplicates_dir()
        self._dir_pattern = self._config.dir_pattern()
        self._file_prefix = self._config.file_prefix()
        self._inputs = (self._config.sources()[source]['dir']
                        for source in self._config.sources().keys())
        self._file_mode = self._config.output_chmod()
        self._dir_mode = self._config.output_chmod_dirs()

    def _setup_logging(self, log_level):
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Add console handler based on config or debug mode
        # Console logging is enabled when:
        # 1. In debug mode, OR
        # 2. No log file is specified, OR
        # 3. log_to_stderr is explicitly enabled in config (defaults to True)
        should_log_to_stderr = (
            log_level == logging.DEBUG or
            not self._config.log_file() or
            self._config.log_to_stderr()
        )

        if should_log_to_stderr:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        # Add file handler if log file is specified
        if self._config.log_file():
            file_handler = logging.FileHandler(self._config.log_file())
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

    def _sync_source(self, src_dir, source_name):
        try:
            walker = walk.WalkForMedia(src_dir)
        except IOError:
            logging.error("Unable to walk dir %s", src_dir)
            return

        fallback_to_file_date = self._config.source_fallback_to_file_date(source_name)

        for file_dir, file_name in walker.find_media():
            file_path = os.path.join(file_dir, file_name)
            media_file = media.MediaFile.build_for(file_path)

            try:
                media_file.datetime(fallback_to_file_date=fallback_to_file_date)
            except media.UnknownDatetime:
                logging.error("skipping %s, no date found from EXIF",
                              file_path)
                continue

            if self._photodb.is_duplicate(media_file):
                file = media_file.get_filename()
                duplicates_path = os.path.join(self._duplicates_dir, file)

                logging.info("moving to duplicates: %s", duplicates_path)

                media_file.rename_as(duplicates_path, self._file_mode, self._dir_mode)
            else:
                if media_file.move_to_directory_with_date(
                        self._config.output_dir(),
                        self._dir_pattern,
                        self._file_prefix,
                        self._file_mode,
                        self._dir_mode):
                    self._photodb.add_to_db(
                        media_file.get_directory(), media_file.get_filename(),
                        media_file)
        self._photodb.write()

    def rebuild_db(self):
        """
        registers in the DB the media files already existing in the
        target directory to be able to detect duplicates and avoid
        overwritting
        """
        walker = walk.WalkForMedia(
            self._config.output_dir(), ignores=self._inputs)
        for file_dir, file_name in walker.find_media():
            try:
                file_path = os.path.join(file_dir, file_name)
                media_file = media.MediaFile.build_for(file_path)
                self._photodb.add_to_db(file_dir, file_name, media_file)
            except Exception:
                logging.critical("Unexpected error: %s", sys.exc_info()[0])
        self._photodb.write()

    def sync(self):
        """
        ensures that the media files of the input directories are sorted
        """
        for source, value in self._config.sources().items():
            self._sync_source(value['dir'], source)

    def monitor(self):
        """
        Continuously monitors and syncs media files from input directories.
        Runs sync operation every MONITOR_INTERVAL_SECONDS (default: 10s).
        """
        while True:
            self.sync()
            time.sleep(MONITOR_INTERVAL_SECONDS)

    def add_yolo_tags(self, interactive=False, dry_run=False):
        """
        Add YOLO object detection tags to photos in output directory.

        Args:
            interactive: Show cv2 visualization window for each image
            dry_run: Preview tags without writing to EXIF
        """
        try:
            from . import yolo_tagger
        except ImportError:
            logging.error("YOLO dependencies not installed.")
            print("ERROR: YOLO dependencies not installed.")
            print("")
            print("Install with: pip install photosort[yolo]")
            print("Or: pip install ultralytics torch opencv-python")
            sys.exit(1)

        # Check if YOLO is available
        if not yolo_tagger.YOLO_AVAILABLE:
            logging.error("YOLO dependencies not installed.")
            print("ERROR: YOLO dependencies not installed.")
            print("")
            print("Install with: pip install photosort[yolo]")
            sys.exit(1)

        # Initialize YOLO tagger
        try:
            tagger = yolo_tagger.YoloTagger(
                model_path=self._config.yolo_model(),
                confidence=self._config.yolo_confidence()
            )
        except yolo_tagger.YoloNotAvailableError as e:
            logging.error(f"YOLO initialization failed: {e}")
            print(f"ERROR: {e}")
            sys.exit(1)

        # Walk output directory to find photos
        walker = walk.WalkForMedia(
            self._config.output_dir(),
            ignores=self._inputs
        )

        processed = 0
        tagged = 0
        errors = 0

        logging.info("Starting YOLO tagging of photos in output directory")

        for file_dir, file_name in walker.find_media():
            file_path = os.path.join(file_dir, file_name)

            # Only process photos, skip movies for now
            media_file = media.MediaFile.build_for(file_path)
            if media_file.type() != 'photo':
                logging.debug(f"Skipping non-photo: {file_path}")
                continue

            try:
                # Detect objects
                labels = tagger.detect_objects(file_path)

                if labels:
                    if dry_run:
                        logging.info(f"[DRY RUN] Would tag {file_path} with: {labels}")
                        print(f"[DRY RUN] {file_name}: {', '.join(labels)}")
                    else:
                        # Add tags to EXIF
                        success = tagger.add_tags_to_photo(file_path, labels)
                        if success:
                            logging.info(f"Tagged {file_path}: {labels}")
                            print(f"Tagged {file_name}: {', '.join(labels)}")
                            tagged += 1
                        else:
                            logging.error(f"Failed to tag {file_path}")
                            errors += 1

                    # Show visualization if interactive
                    if interactive:
                        tagger.visualize_detections(file_path, show_window=True)
                else:
                    logging.debug(f"No objects detected in {file_path}")

                processed += 1

            except KeyboardInterrupt:
                logging.info("Interrupted by user")
                print("\nInterrupted by user")
                break
            except Exception as e:
                logging.error(f"Error processing {file_path}: {e}")
                errors += 1

        # Print summary
        print(f"\nSummary:")
        print(f"  Processed: {processed}")
        if not dry_run:
            print(f"  Tagged: {tagged}")
        print(f"  Errors: {errors}")

        logging.info(f"YOLO tagging complete: {processed} processed, {tagged} tagged, {errors} errors")

    @staticmethod
    def version():
        print("photosort version %s" % version('photosort'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('op', action="store",
                        choices=['sync', 'rebuilddb', 'monitor', 'add-yolo-tags', "version"],
                        help="Operation")

    group = parser.add_argument_group('Common parameters')
    group.add_argument('--config', action="store",
                       help="Customized configuration file",
                       default='/etc/photosort.yml')
    group.add_argument('--debug',
                       action="store_true",
                       help="Enable debugging")

    yolo_group = parser.add_argument_group('YOLO tagging parameters')
    yolo_group.add_argument('--interactive',
                           action="store_true",
                           help="Show visualization window for each detection (requires display)")
    yolo_group.add_argument('--dry-run',
                           action="store_true",
                           help="Preview tags without writing to EXIF")

    ns = parser.parse_args()

    try:
        exif.start()
    except FileNotFoundError:
        print("ERROR: exiftool is not installed. PhotoSort requires exiftool to read EXIF metadata.")
        print("")
        print("Installation instructions:")
        print("  Ubuntu/Debian: sudo apt-get install exiftool")
        print("  macOS:         brew install exiftool")
        print("  Other:         https://exiftool.org/install.html")
        sys.exit(1)

    log_level = logging.INFO
    if ns.debug:
        print("Debug log level")
        log_level = logging.DEBUG
    photo_sort = PhotoSort(ns.config, log_level)

    try:
        if ns.op == "sync":
            photo_sort.sync()

        elif ns.op == "rebuilddb":
            photo_sort.rebuild_db()

        elif ns.op == "monitor":
            photo_sort.monitor()

        elif ns.op == "add-yolo-tags":
            photo_sort.add_yolo_tags(
                interactive=ns.interactive,
                dry_run=ns.dry_run
            )

        elif ns.op == "version":
            photo_sort.version()
        else:
            print("Unknown operation: %s" % ns.op)
    except Exception:
        logging.critical("Unexpected error: %s", sys.exc_info()[0])
        logging.critical(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
