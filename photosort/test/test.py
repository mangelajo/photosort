# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import unittest
import platform
import os.path

if platform.python_version() < '2.7':
    unittest = __import__('unittest2')
else:
    import unittest


def main():
    tests_dir = os.path.join(os.path.dirname(__file__),'testcases')
    testsuite = unittest.TestLoader().discover(tests_dir,pattern="*.py")
    unittest.TextTestRunner(verbosity=100).run(testsuite)

if __name__ == '__main__':
    main()

