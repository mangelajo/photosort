# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"


import yaml


class Config:
    def __init__(self, filename='config.yml'):
        with open(filename, 'r') as f_in:
            self._data = yaml.safe_load(f_in)

    def output_dir(self):
        return self._data['output_dir']

    def _relative_or_absolute_to_output(self, filename):
        if filename.startswith('/'):
            return filename
        else:
            return self.output_dir()+"/"+filename

    def log_file(self):
        return self._relative_or_absolute_to_output(self._data['log_file'])

    def db_file(self):
        return self._relative_or_absolute_to_output(self._data['db_file'])

    def duplicates_dir(self):
        return self._relative_or_absolute_to_output(self._data['duplicates_dir'])

    def sources(self):
        return self._data['sources']

    def dir_pattern(self):
        return self._data['dir_pattern']
