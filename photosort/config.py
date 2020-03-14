# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import yaml


class Config:
    """
    YAML configuration reading class
    """

    def __init__(self, filename='/etc/photosort.yml'):
        with open(filename, 'r') as f_in:
            self._data = yaml.safe_load(f_in)

    def output_dir(self):
        return self._data['output']['dir']

    def _relative_or_absolute_to_output(self, filename):
        """
            If filename starts with a slash it does return
            the filename, otherwise it will add the output dir
            in front
        """
        if filename.startswith('/'):
            return filename
        else:
            return self.output_dir() + "/" + filename

    def sources(self):
        return self._data['sources']

    def log_file(self):
        if 'log_file' in self._data['output']:
            return self._relative_or_absolute_to_output(
                self._data['output']['log_file'])
        else:
            return None

    def db_file(self):
        return self._relative_or_absolute_to_output(
            self._data['output']['db_file'])

    def duplicates_dir(self):
        return self._relative_or_absolute_to_output(
            self._data['output']['duplicates_dir'])

    def dir_pattern(self):
        try:
            return self._data['output']['dir_pattern']
        except KeyError as exc:
            if str(exc) == "'dir_pattern'":
                return self._data['output']['pattern']
            else:
                raise

    def file_prefix(self):
        try:
            return self._data['output']['file_prefix']
        except KeyError as exc:
            if str(exc) == "'file_prefix'":
                return ""
            else:
                raise

    def output_chmod(self):
        return int(self._data['output']['chmod'], 8)  # octal conversion
