# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2011-2013 Marc Deslauriers <marc.deslauriers@canonical.com>
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

"""Helpers for an Ubuntu application."""
import logging
import os

from . pasaffeconfig import get_data_file

import gettext
from gettext import gettext as _
gettext.textdomain('pasaffe')


class PathEntry:
    def __init__(self, name, uuid, path):
        self.name = name
        self.uuid = uuid
        self.path = path

    def __cmp__(self, other):

        # First, we sort by path
        result = self._sort_path(self.path, other.path)
        if result != 0:
            return result

        # Then we sort by name
        result = self._sort_name(self.name, other.name)
        return result

    def _sort_name(self, first, second):
        # We assume empty names are folders, so they need to
        # lose to be first in the list
        if first in (None, "") and second in (None, ""):
            return 0
        elif first < second:
            return -1
        elif first > second:
            return 1
        else:
            # Gah, fail.
            return 0

    def _sort_path(self, first, second):

        # Folders should be displayed first, so they should lose to
        # entries that don't have folders
        if first in (None, []) and second in (None, []):
            return 0
        elif first in (None, []):
            return 1
        elif second in (None, []):
            return -1
        elif len(first) < len(second):
            i = 0
            for path in first:
                if not len(path):
                    return 1
                if not len(second[i]):
                    return -1
                if path < second[i]:
                    return -1
                if path > second[i]:
                    return 1
                i += 1
            return 1
        elif len(first) > len(second):
            i = 0
            for path in second:
                if not len(path):
                    return -1
                if not len(first[i]):
                    return 1
                if path > first[i]:
                    return -1
                if path < first[i]:
                    return 1
                i += 1
            return -1
        else:
            i = 0
            for path in first:
                if not len(path):
                    return 1
                if not len(second[i]):
                    return -1
                if path < second[i]:
                    return -1
                if path > second[i]:
                    return 1
                i += 1
            return 0

# Owais Lone : To get quick access to icons and stuff.
def get_media_file(media_file_name):
    media_filename = get_data_file('media', '%s' % (media_file_name,))
    if not os.path.exists(media_filename):
        media_filename = None

    return "file:///" + media_filename


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


def set_up_logging(opts):
    # add a handler to prevent basicConfig
    root = logging.getLogger()
    null_handler = NullHandler()
    root.addHandler(null_handler)

    formatter = logging.Formatter("%(levelname)s:%(name)s: %(funcName)s()"
                                  " '%(message)s'")

    logger = logging.getLogger('pasaffe')
    logger_sh = logging.StreamHandler()
    logger_sh.setFormatter(formatter)
    logger.addHandler(logger_sh)

    lib_logger = logging.getLogger('pasaffe_lib')
    lib_logger_sh = logging.StreamHandler()
    lib_logger_sh.setFormatter(formatter)
    lib_logger.addHandler(lib_logger_sh)

    # Set the logging level to show debug messages.
    if opts.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug('logging enabled')
    if opts.verbose > 1:
        lib_logger.setLevel(logging.DEBUG)


def get_help_uri(page=None):
    # help_uri from source tree - default language
    here = os.path.dirname(__file__)
    help_uri = os.path.abspath(os.path.join(here, '..', 'help', 'C'))

    if not os.path.exists(help_uri):
        # installed so use gnome help tree - user's language
        help_uri = 'pasaffe'

    # unspecified page is the index.page
    if page is not None:
        help_uri = '%s#%s' % (help_uri, page)

    return help_uri


def alias(alternative_function_name):
    '''see http://www.drdobbs.com/web-development/184406073#l9'''
    def decorator(function):
        '''attach alternative_function_name(s) to function'''
        if not hasattr(function, 'aliases'):
            function.aliases = []
        function.aliases.append(alternative_function_name)
        return function
    return decorator

def folder_list_to_field(folder_list):
    '''Converts a folder list to a folder field'''
    field = ""

    if folder_list == None:
        return field

    for folder in folder_list:
        if field != "":
            field += "."
        field += folder.replace(".", "\\.")
    return field

def folder_list_to_path(folders, index=None):
    '''Converts a folder list to a folder path'''
    if len(folders) == 0 or folders == None:
        return "/"

    if index == None:
        index = len(folders)

    folder_path = ""

    for folder in folders[0:index+1]:
        folder_path += "/"
        folder_path += folder.replace("/", "\\/")

    folder_path += "/"

    return folder_path

def folder_path_to_list(folder_path):
    '''Converts a folder path to a folder list'''
    folders = []

    if folder_path.endswith("/"):
        folder_path = folder_path[:-1]
    if folder_path.startswith("/"):
        folder_path = folder_path[1:]

    if folder_path == '':
        return folders

    # We need to split into folders using the "/" character, but not
    # if it is escaped with a \
    index = 0
    location = 0
    while index < len(folder_path):
        location = folder_path.find("/", location + 1)

        if location == -1:
            break

        if folder_path[location-1] == "\\":
            continue

        folders.append(folder_path[index:location].replace("\\",''))
        index = location + 1

    folders.append(folder_path[index:len(folder_path)].replace('\\',''))
    return folders


