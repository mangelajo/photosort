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
            return self.output_dir()+"/"+filename

    def sources(self):
        return self._data['sources']

    def log_file(self):
        return self._relative_or_absolute_to_output(self._data['output']['log_file'])

    def db_file(self):
        return self._relative_or_absolute_to_output(self._data['output']['db_file'])

    def duplicates_dir(self):
        return self._relative_or_absolute_to_output(
            self._data['output']['duplicates_dir'])

    def sources(self):
        return self._data['sources']

    def dir_pattern(self):
        return self._data['output']['pattern']

    def output_chmod(self):
        return self._data['output']['chmod']

