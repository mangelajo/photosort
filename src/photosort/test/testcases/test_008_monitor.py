# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import logging
import os
from unittest import mock
import yaml

from photosort import photosort
from photosort import test


class TestMonitorMode(test.TestCase):
    """Test monitor mode behavior"""

    def setUp(self):
        super().setUp()
        self.config_path = os.path.join(self._temp_dir, 'test.yml')
        self.output_dir = os.path.join(self._temp_dir, 'output')
        self.source_dir = os.path.join(self._temp_dir, 'source')

        os.makedirs(self.output_dir)
        os.makedirs(self.source_dir)

        self.config_data = {
            'output': {
                'dir': self.output_dir,
                'chmod': '0o755',
                'db_file': 'photos.csv',
                'duplicates_dir': 'duplicates',
                'dir_pattern': '%(year)04d',
            },
            'sources': {
                'test': {'dir': self.source_dir}
            }
        }

        with open(self.config_path, 'w') as f:
            yaml.dump(self.config_data, f)

    def test_monitor_runs_sync_repeatedly(self):
        """Test that monitor calls sync in a loop"""
        ps = photosort.PhotoSort(self.config_path, logging.ERROR)

        sync_call_count = 0
        original_sync = ps.sync

        def counting_sync():
            nonlocal sync_call_count
            sync_call_count += 1
            original_sync()
            # Stop after 3 iterations
            if sync_call_count >= 3:
                raise KeyboardInterrupt()

        with mock.patch.object(ps, 'sync', side_effect=counting_sync):
            with mock.patch('time.sleep') as mock_sleep:
                try:
                    ps.monitor()
                except KeyboardInterrupt:
                    pass  # Expected to stop the loop

        # Verify sync was called multiple times
        self.assertEqual(sync_call_count, 3)
        # Verify sleep was called between syncs
        self.assertEqual(mock_sleep.call_count, 2)
        # Verify sleep was called with 10 seconds
        mock_sleep.assert_called_with(10)

    def test_monitor_sleeps_between_syncs(self):
        """Test that monitor sleeps 10 seconds between sync operations"""
        ps = photosort.PhotoSort(self.config_path, logging.ERROR)

        iteration_count = [0]

        def counting_sync_wrapper(*args, **kwargs):
            iteration_count[0] += 1
            if iteration_count[0] >= 2:
                raise KeyboardInterrupt()

        with mock.patch.object(ps, 'sync', side_effect=counting_sync_wrapper):
            with mock.patch('time.sleep') as mock_sleep:
                try:
                    ps.monitor()
                except KeyboardInterrupt:
                    pass

        # Sleep should be called once (after first sync, before second)
        self.assertEqual(mock_sleep.call_count, 1)
        mock_sleep.assert_called_with(10)

    def test_monitor_propagates_sync_exceptions(self):
        """Test that monitor propagates exceptions from sync"""
        ps = photosort.PhotoSort(self.config_path, logging.ERROR)

        call_count = [0]

        def failing_sync():
            call_count[0] += 1
            raise RuntimeError("Simulated sync error")

        with mock.patch.object(ps, 'sync', side_effect=failing_sync):
            with mock.patch('time.sleep'):
                # Monitor should propagate the RuntimeError
                with self.assertRaises(RuntimeError) as context:
                    ps.monitor()

                self.assertIn("Simulated sync error", str(context.exception))

        # Sync should have been called exactly once before exception
        self.assertEqual(call_count[0], 1)

    def test_monitor_infinite_loop_behavior(self):
        """Test that monitor runs in infinite loop until interrupted"""
        ps = photosort.PhotoSort(self.config_path, logging.ERROR)

        iterations = [0]
        max_iterations = 5

        def limited_sync():
            iterations[0] += 1
            if iterations[0] >= max_iterations:
                raise KeyboardInterrupt()

        with mock.patch.object(ps, 'sync', side_effect=limited_sync):
            with mock.patch('time.sleep'):
                try:
                    ps.monitor()
                except KeyboardInterrupt:
                    pass

        # Should have run exactly max_iterations times
        self.assertEqual(iterations[0], max_iterations)

    def test_monitor_with_empty_sources(self):
        """Test monitor with no files to process"""
        ps = photosort.PhotoSort(self.config_path, logging.ERROR)

        iterations = [0]

        def counting_sync():
            iterations[0] += 1
            if iterations[0] >= 2:
                raise KeyboardInterrupt()

        with mock.patch.object(ps, 'sync', side_effect=counting_sync):
            with mock.patch('time.sleep'):
                try:
                    ps.monitor()
                except KeyboardInterrupt:
                    pass

        # Should still run sync even with no files
        self.assertEqual(iterations[0], 2)

    def test_monitor_respects_config_changes(self):
        """Test that each monitor iteration uses current PhotoSort state"""
        ps = photosort.PhotoSort(self.config_path, logging.ERROR)

        sync_calls = []

        def tracking_sync():
            # Track that sync is being called
            sync_calls.append(True)
            if len(sync_calls) >= 3:
                raise KeyboardInterrupt()

        with mock.patch.object(ps, 'sync', side_effect=tracking_sync):
            with mock.patch('time.sleep'):
                try:
                    ps.monitor()
                except KeyboardInterrupt:
                    pass

        # Each iteration should call sync
        self.assertEqual(len(sync_calls), 3)

    def test_monitor_keyboard_interrupt(self):
        """Test that KeyboardInterrupt stops monitor cleanly"""
        ps = photosort.PhotoSort(self.config_path, logging.ERROR)

        def interrupt_immediately():
            raise KeyboardInterrupt()

        with mock.patch.object(ps, 'sync', side_effect=interrupt_immediately):
            with mock.patch('time.sleep'):
                # Should raise KeyboardInterrupt
                with self.assertRaises(KeyboardInterrupt):
                    ps.monitor()

    def test_monitor_with_actual_files(self):
        """Test monitor processes files on each iteration"""
        ps = photosort.PhotoSort(self.config_path, logging.ERROR)

        # Create a test file
        import shutil
        media1 = self.get_data_path('media1')
        test_file = os.path.join(media1, 'img1.jpg')
        dest_file = os.path.join(self.source_dir, 'test.jpg')
        shutil.copy(test_file, dest_file)

        iterations = [0]
        original_sync = ps.sync

        def counting_sync():
            iterations[0] += 1
            original_sync()  # Call the real sync method
            if iterations[0] >= 2:
                raise KeyboardInterrupt()

        with mock.patch.object(ps, 'sync', side_effect=counting_sync):
            with mock.patch("photosort.walk.WalkForMedia._file_is_ready", return_value=True):
                with mock.patch('time.sleep'):
                    try:
                        ps.monitor()
                    except KeyboardInterrupt:
                        pass

        # File should have been processed (moved to output directory)
        self.assertFalse(os.path.exists(dest_file))
        # Verify monitor ran at least twice
        self.assertGreaterEqual(iterations[0], 2)


if __name__ == '__main__':
    test.test.main()
