#!/bin/sh
python3 setup.py sdist upload --sign
python3 setup.py bdist_egg upload --sign

