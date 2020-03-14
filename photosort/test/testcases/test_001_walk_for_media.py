# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import mock
import photosort.test as test
from photosort import walk


class TestWalkForMedia(test.TestCase):

    def setUp(self):
        self.media1 = self.get_data_path('media1')

    def test_directory_inspection(self):

        # We need to patch the timecheck (not modified in last 30 seconds)
        # in CI (recent checkout)
        with mock.patch("photosort.walk.WalkForMedia._file_is_ready") as m:
            instance = m.return_value
            instance.method.return_value = True
            walker = walk.WalkForMedia(self.media1)
            files = [file for root, file in walker.find_media()]
            self.assertIn('img1.jpg', files)

    def test_directory_inspection_file_not_ready(self):

        with mock.patch("photosort.walk.WalkForMedia._file_is_ready") as m:
            instance = m.return_value
            instance.method.return_value = False
            walker = walk.WalkForMedia(self.media1)
            files = [file for root, file in walker.find_media()]
            self.assertNotIn('img1', files)

    def test_ignores(self):
        pass


if __name__ == '__main__':
    test.test.main()
