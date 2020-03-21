# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import os.path
import tempfile
import unittest


class TestCase(unittest.TestCase):
    @staticmethod
    def get_data_path(file_path):
        return os.path.join(os.path.dirname(__file__), 'data', file_path)

    def setUp(self):
        _temp_dir = tempfile.TemporaryDirectory(prefix=self.id())
        self._temp_dir = _temp_dir.name
        self.addCleanup(_temp_dir.cleanup)
