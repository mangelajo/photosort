# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import photosort.test

class TestQAWorks(photosort.test.TestCase):

    def setUp(self):
        self.dummy = None

    def test_assert_true( self ):
        self.assertTrue( True )

    def test_assert_equal( self ):
        self.assertEqual(2, 1+1)


if __name__ == '__main__':
    unittest.main()
   