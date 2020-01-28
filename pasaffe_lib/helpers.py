# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
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
#

"""Helpers for an Ubuntu application."""
import logging
import os
import subprocess

from . pasaffeconfig import get_data_file
from . pasaffeconfig import get_help_prefix
from . pasaffeconfig import get_help_separator

import gettext
from gettext import gettext as _
gettext.textdomain('pasaffe')


class PathEntry:
    def __init__(self, name, uuid, path):
        self.name = name
        self.uuid = uuid
        self.path = path

    def _mycmp(self, other):

        # First, we sort by path
        result = self._sort_path(self.path, other.path)
        if result != 0:
            return result

        # Then we sort by name
        result = self._sort_name(self.name, other.name)
        return result

    def __lt__(self, other):
        return self._mycmp(other) < 0

    def __gt__(self, other):
        return self._mycmp(other) > 0

    def __eq__(self, other):
        return self._mycmp(other) == 0

    def __le__(self, other):
        return self._mycmp(other) <= 0

    def __ge__(self, other):
        return self._mycmp(other) >= 0

    def __ne__(self, other):
        return self._mycmp(other) != 0

    def _lower(self, name):
        # Doing .lower() is wrong in Python 2 as it doesn't properly
        # handle certain characters in Unicode languages. Unfortunately,
        # I can't think of a better solution right now, and it will work
        # properly once we migrate to Python 3
        if name:
            return name.lower()
        else:
            return ""

    def _sort_name(self, first, second):
        # Perform a case-insensitive sort
        nocase_first = self._lower(first)
        nocase_second = self._lower(second)
        # We assume empty names are folders, so they need to
        # lose to be first in the list
        if nocase_first in (None, "") and nocase_second in (None, ""):
            return 0
        elif nocase_first < nocase_second:
            return -1
        elif nocase_first > nocase_second:
            return 1
        else:
            # If they are the same when they are case-insensitive, we now
            # want to sort in a case-sensitive way
            if first < second:
                return -1
            elif first > second:
                return 1
            else:
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
                # First test in a case insensitive way
                if self._lower(path) < self._lower(second[i]):
                    return -1
                if self._lower(path) > self._lower(second[i]):
                    return 1
                # Now try in a case-sensitive way
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
                # First test in a case insensitive way
                if self._lower(path) > self._lower(first[i]):
                    return -1
                if self._lower(path) < self._lower(first[i]):
                    return 1
                # Now try in a case-sensitive way
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
                # First test in a case insensitive way
                if self._lower(path) < self._lower(second[i]):
                    return -1
                if self._lower(path) > self._lower(second[i]):
                    return 1
                # Now try in a case-sensitive way
                if path < second[i]:
                    return -1
                if path > second[i]:
                    return 1
                i += 1
            return 0

    def __repr__(self):
        return repr((self.name, self.uuid, self.path))


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
    if opts.verbose and opts.verbose > 1:
        lib_logger.setLevel(logging.DEBUG)


def get_help_uri(page=None):
    # help_uri from source tree - default language
    here = os.path.dirname(__file__)
    help_uri = os.path.abspath(os.path.join(here, '..', 'help', 'C'))
    prefix = 'ghelp:'
    separator = '#'

    if not os.path.exists(help_uri):
        # installed so use gnome help tree - user's language
        help_uri = 'pasaffe'
        prefix = get_help_prefix()
        separator = get_help_separator()

    # unspecified page is the index.page
    if page is not None:
        help_uri = '%s%s%s' % (help_uri, separator, page)

    return '%s%s' % (prefix, help_uri)


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

    if folder_list is None:
        return field

    for folder in folder_list:
        if field != "":
            field += "."
        field += folder.replace(".", "\\.")
    return field


def field_to_folder_list(field):
    '''Converts a folder field to a folder list'''

    # We need to split into folders using the "." character, but not
    # if it is escaped with a \
    folders = []

    if field == "":
        return folders

    index = 0
    location = 0
    while index < len(field):
        location = field.find(".", location + 1)

        if location == -1:
            break

        if field[location - 1] == "\\":
            continue

        folders.append(field[index:location].replace("\\", ''))
        index = location + 1

    folders.append(field[index:len(field)].replace('\\', ''))
    return folders


def folder_list_to_path(folders, index=None):
    '''Converts a folder list to a folder path'''
    if len(folders) == 0 or folders is None:
        return "/"

    if index is None:
        index = len(folders)

    folder_path = ""

    for folder in folders[0:index + 1]:
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

        if folder_path[location - 1] == "\\":
            continue

        folders.append(folder_path[index:location].replace("\\", ''))
        index = location + 1

    folders.append(folder_path[index:len(folder_path)].replace('\\', ''))
    return folders


def confirm(prompt=None, resp=False):
    """prompts for yes or no response from the user. Returns True for yes and
    False for no.

    'resp' should be set to the default value assumed by the caller when
    user simply types ENTER.

    >>> confirm(prompt='Create Directory?', resp=True)
    Create Directory? [y]|n:
    True
    >>> confirm(prompt='Create Directory?', resp=False)
    Create Directory? [n]|y:
    False
    >>> confirm(prompt='Create Directory?', resp=False)
    Create Directory? [n]|y: y
    True

    """

    if prompt is None:
        prompt = 'Confirm'

    if resp:
        prompt = '%s [%s]|%s: ' % (prompt, 'y', 'n')
    else:
        prompt = '%s [%s]|%s: ' % (prompt, 'n', 'y')

    while True:
        ans = input(prompt)
        if not ans:
            return resp
        if ans not in ['y', 'Y', 'n', 'N']:
            print('please enter y or n.')
            continue
        if ans == 'y' or ans == 'Y':
            return True
        if ans == 'n' or ans == 'N':
            return False


def get_database_path():
    """Determines standard XDG location for database"""
    if 'XDG_DATA_HOME' in os.environ:
        basedir = os.path.join(os.environ['XDG_DATA_HOME'], 'pasaffe')
    else:
        basedir = os.path.join(os.environ['HOME'], '.local/share/pasaffe')

    if not os.path.exists(basedir):
        os.makedirs(basedir, 0o700)

    return os.path.join(basedir, 'pasaffe.psafe3')


def gen_password(number, size):
    """Generate <number> new passwords, each of size <size>"""
    command = ["apg", "-a", "1", "-n", str(number), "-M", "NCL",
               "-m", str(size),
               "-x", str(size)]
    try:
        passwords = subprocess.check_output(command).splitlines()
    except:  # noqa: E722
        print(_("error running apg"))
        passwords = None
    return passwords
