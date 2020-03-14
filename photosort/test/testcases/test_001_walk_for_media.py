# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import photosort.test as test
from photosort import walk


class TestWalkForMedia(test.TestCase):

    def setUp(self):
        self.media1 = self.get_data_path('media1')

    def test_directory_inspection(self):
        walker = walk.WalkForMedia(self.media1)
        files = [file for root, file in walker.find_media()]
        self.assertIn('img1.jpg', files)

    def test_ignores(self):
        pass


if __name__ == '__main__':
    test.test.main()
