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


class TestPasswordGorilla15363(unittest.TestCase):
    def setUp(self):
        self.passfile = PassSafeFile(
            './tests/databases/pw-gorilla-15363.psafe3', 'pasaffe')

    def test_num_entries(self):
        self.assertEqual(len(self.passfile.records), 4)

    def test_empty_folders(self):
        # This version of Password Gorilla doesn't save empty folders
        self.assertEqual(len(self.passfile.empty_folders), 0)

    def test_get_database_version_string(self):
        self.assertEqual(self.passfile.get_database_version_string(), "03.00")

    def test_get_database_uuid(self):
        self.assertEqual(self.passfile.header[1],
                         b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
                         '\x00\x00\x00\x00\x00')

    def test_get_saved_name(self):
        self.assertEqual(self.passfile.get_saved_name(), None)

    def test_get_saved_host(self):
        self.assertEqual(self.passfile.get_saved_host(), None)

    def test_get_saved_application(self):
        self.assertEqual(self.passfile.get_saved_application(), None)

    def test_get_saved_date_string(self):
        self.assertEqual(self.passfile.get_saved_date_string(), None)

    def test_entry_1(self):
        uuid = '8642342dfd444e044f50ca8b3b12fd67'
        self.assertEqual(self.passfile.records[uuid][2], 'top\\.withdot')
        self.assertEqual(self.passfile.get_folder_list(uuid), ['top.withdot'])
        self.assertEqual(self.passfile.records[uuid][3], 'insidedot')
        self.assertEqual(self.passfile.records[uuid][4], 'usernamedot')
        self.assertFalse(5 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.records[uuid][6], 'passworddot')
        self.assertEqual(self.passfile.get_password_time(uuid, False),
                         'Thu, 25 Jul 2013 23:58:56')
        self.assertEqual(self.passfile.get_modification_time(uuid, False),
                         'Thu, 25 Jul 2013 23:58:56')

    def test_entry_2(self):
        uuid = '666b02ae0f574d4549f8f57ddae70d77'
        self.assertFalse(2 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.get_folder_list(uuid), None)
        self.assertEqual(self.passfile.records[uuid][3], 'toplevel1')
        self.assertEqual(self.passfile.records[uuid][4], 'usernametop')
        self.assertEqual(self.passfile.records[uuid][5], 'This is a note')
        self.assertEqual(self.passfile.records[uuid][6], 'passwordtop')
        self.assertEqual(self.passfile.get_password_time(uuid, False),
                         'Thu, 25 Jul 2013 23:58:06')
        self.assertEqual(self.passfile.get_modification_time(uuid, False),
                         'Thu, 25 Jul 2013 23:58:06')

    def test_entry_3(self):
        uuid = 'aff6f326353f4be86009bf342e0a0af7'
        self.assertEqual(self.passfile.records[uuid][2],
                         'topgroup1.topgroup2.topgroup3')
        self.assertEqual(self.passfile.get_folder_list(uuid),
                         ['topgroup1', 'topgroup2', 'topgroup3'])
        self.assertEqual(self.passfile.records[uuid][3], 'entrylevel3')
        self.assertEqual(self.passfile.records[uuid][4], 'username3')
        self.assertFalse(5 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.records[uuid][6], 'password3')
        self.assertEqual(self.passfile.get_password_time(uuid, False),
                         'Thu, 25 Jul 2013 00:33:33')
        self.assertEqual(self.passfile.get_modification_time(uuid, False),
                         'Thu, 25 Jul 2013 00:33:33')

    def test_entry_4(self):
        uuid = '66d1cf5e60dc424d6a3b19c89aed2f1e'
        self.assertEqual(self.passfile.records[uuid][2], 'topgroup1')
        self.assertEqual(self.passfile.get_folder_list(uuid), ['topgroup1'])
        self.assertEqual(self.passfile.records[uuid][3], 'entrylevel1')
        self.assertEqual(self.passfile.records[uuid][4], 'username1')
        self.assertEqual(self.passfile.records[uuid][5],
                         'This is a note\nThis is a second line\n'
                         'Unicode: éléphant')
        self.assertEqual(self.passfile.records[uuid][6], 'password1')
        self.assertEqual(self.passfile.get_password_time(uuid, False),
                         'Thu, 25 Jul 2013 00:33:06')
        self.assertEqual(self.passfile.get_modification_time(uuid, False),
                         'Thu, 25 Jul 2013 00:33:06')

if __name__ == '__main__':
    unittest.main()
