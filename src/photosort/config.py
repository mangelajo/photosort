# -*- mode: python; coding: utf-8 -*-

__author__ = "Miguel Angel Ajo Pelayo"
__email__ = "miguelangel@ajo.es"
__copyright__ = "Copyright (C) 2013 Miguel Angel Ajo Pelayo"
__license__ = "GPLv3"

import logging
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
        if 'dir_pattern' in self._data['output']:
            return self._data['output']['dir_pattern']
        elif 'pattern' in self._data['output']:
            logging.warning(
                "Config key 'output.pattern' is deprecated, "
                "use 'output.dir_pattern' instead")
            return self._data['output']['pattern']
        else:
            raise KeyError('dir_pattern')

    def file_prefix(self):
        if 'file_prefix' in self._data['output']:
            return self._data['output']['file_prefix']
        else:
            return ""

    def output_chmod(self):
        return int(self._data['output']['chmod'], 8)  # octal conversion

    def output_chmod_dirs(self):
        """
        Returns permissions for directories.
        If chmod_dirs is specified, use that value.
        Otherwise, default to chmod | 0o111 (add execute for user/group/other).
        Directories need execute permission to be traversable.
        """
        if 'chmod_dirs' in self._data['output']:
            return int(self._data['output']['chmod_dirs'], 8)
        else:
            # Default: take file permissions and add execute for all
            return self.output_chmod() | 0o111

    def log_to_stderr(self):
        """
        Returns whether to log to stderr in addition to log file.
        Defaults to True if not specified.
        """
        if 'log_to_stderr' in self._data['output']:
            return bool(self._data['output']['log_to_stderr'])
        else:
            return True  # Default to True for backward compatibility
