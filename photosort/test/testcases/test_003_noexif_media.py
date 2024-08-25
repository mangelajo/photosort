# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

from photosort import test
from photosort import media


class TestMovieMedia(test.TestCase):

    def setUp(self):
        super().setUp()
        self.mov1 = self.get_data_path('media2/BigBuckBunny.avi')
        self.movie = media.MediaFile.build_for(self.mov1)

    def test_hash_creation(self):
        expected_hash = "630569ce2efda22d55d271bfe8ec4428"
        self.assertEqual(self.movie.hash(), expected_hash)

        # check for hasher non being re-started
        same_movie = media.MediaFile.build_for(self.mov1)
        self.assertEqual(same_movie.hash(), expected_hash)

    def test_datetime_execption(self):
        with self.assertRaises(media.UnknownDatetime):
            self.movie.datetime()


if __name__ == '__main__':
    test.test.main()
