#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2013 Marc Deslauriers <marc.deslauriers@canonical.com>
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

import sys
import os.path
import unittest
import time
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__),
                                                 "..")))

from pasaffe_lib.readdb import PassSafeFile


def get_test_data():
    empty_folders = [['emptygroup1'],
                     ['emptygroup1', 'emptygroup2'],
                     ['emptygroup1', 'emptygroup2', 'emptygroup3'],
                     ['level1group', 'level2group'],
                     ['emptygroup1', 'test'],
                     ['emptygroup1', 'with/slash']]

    entries = [{3:  "topentry1",
                4:  "username1",
                5:  "This is a note",
                6:  "password1",
                13: "http://www.example.com"},
               {2:  "level1group",
                3:  "level1entry",
                4:  "username1",
                5:  "This is a note",
                6:  "password1"},
               {2:  "level1group.level2group.level3group",
                3:  "level3entry",
                4:  "usernamelevel3",
                6:  "passwordlevel3"}]

    return entries, empty_folders


def create_test_db():
    passfile = PassSafeFile()
    passfile.new_db('pasaffe')

    entries, empty_folders = get_test_data()

    for entry in entries:
        uuid = passfile.new_entry()
        for key in entry.keys():
            passfile.records[uuid][key] = entry[key]

    for folder in empty_folders:
        passfile.add_empty_folder(folder)

    return passfile

if __name__ == '__main__':
    # This script can be used to create a test database
    # Simply run it with a filename, and a database will be created

    if len(sys.argv) < 2:
        print("Missing database output filename. Aborting.",
              file=sys.stderr)
        sys.exit(1)

    filename = sys.argv[1]
    if os.path.exists(filename):
        print("Output file '%s' already exists. Aborting." % filename,
              file=sys.stderr)
        sys.exit(1)

    passfile = create_test_db()
    passfile.writefile(filename)
