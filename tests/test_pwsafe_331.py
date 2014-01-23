#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
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
### END LICENSE

import sys
import os.path
import unittest
import time
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from pasaffe_lib.readdb import PassSafeFile

class TestPasswordSafe331(unittest.TestCase):
    def setUp(self):
        self.passfile = PassSafeFile('./tests/databases/pwsafe-331.psafe3', 'pasaffe')

    def test_num_entries(self):
        self.assertEqual(len(self.passfile.records), 3)

    def test_empty_folders(self):

        empty_folders =  [ ['emptygroup1'],
                           ['emptygroup1', 'emptygroup2'],
                           ['emptygroup1', 'emptygroup2', 'emptygroup3'],
                           ['level1group', 'level2group'],
                           ['emptygroup1', 'test'],
                           ['emptygroup1', 'with/slash'] ]

        empty_fields = [ 'emptygroup1',
                         'emptygroup1.emptygroup2',
                         'emptygroup1.emptygroup2.emptygroup3',
                         'level1group.level2group',
                         'emptygroup1.test',
                         'emptygroup1.with/slash' ]

        self.assertEqual(len(self.passfile.empty_folders), len(empty_fields))
        self.assertEqual(self.passfile.get_empty_folders(), empty_folders)
        self.assertEqual(self.passfile.empty_folders, empty_fields)

    def test_get_database_version_string(self):
        self.assertEqual(self.passfile.get_database_version_string(), "03.0b")

    def test_get_database_uuid(self):
        self.assertEqual(self.passfile.header[1],
                         b'cf\xfe\xea\x00wBU\xa2TM\xc3k\x0f>\x0f')

    def test_get_saved_name(self):
        self.assertEqual(self.passfile.get_saved_name(), "mdeslaur")

    def test_get_saved_host(self):
        self.assertEqual(self.passfile.get_saved_host(), "mdlinux")

    def test_get_saved_application(self):
        self.assertEqual(self.passfile.get_saved_application(), 'Password Safe V3.31')

    def test_get_saved_date_string(self):
        self.assertEqual(self.passfile.get_saved_date_string(False),
                         'Thu, 25 Jul 2013 23:57:08')

    def test_entry_1(self):
        uuid = b'4a32a8ad616343b692e85c721bfce0e2'
        self.assertFalse(2 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.get_folder_list(uuid), None)
        self.assertEqual(self.passfile.records[uuid][3], 'topentry1')
        self.assertEqual(self.passfile.records[uuid][4], 'username1')
        self.assertEqual(self.passfile.records[uuid][5],
                         'This is a note\r\nThis is a second line\r\nUnicode: éléphant')
        self.assertEqual(self.passfile.records[uuid][6], 'password1')
        self.assertEqual(self.passfile.get_creation_time(uuid, False),
                         'Thu, 25 Jul 2013 00:21:00')
        self.assertEqual(self.passfile.records[uuid][13], 'http://www.example.com')

    def test_entry_2(self):
        uuid = b'722328d418584201803a119fa517b799'
        self.assertEqual(self.passfile.records[uuid][2], 'level1group')
        self.assertEqual(self.passfile.get_folder_list(uuid), ['level1group'])
        self.assertEqual(self.passfile.records[uuid][3], 'level1entry')
        self.assertEqual(self.passfile.records[uuid][4], 'username1')
        self.assertEqual(self.passfile.records[uuid][5], 'This is a note\r\n')
        self.assertEqual(self.passfile.records[uuid][6], 'password1')
        self.assertEqual(self.passfile.get_creation_time(uuid, False),
                         'Thu, 25 Jul 2013 00:25:42')

    def test_entry_3(self):
        uuid = b'cb16d230853247ad8cb12ef6ea615cb4'
        self.assertEqual(self.passfile.records[uuid][2], 'level1group.level2group.level3group')
        self.assertEqual(self.passfile.get_folder_list(uuid),
                         ['level1group', 'level2group', 'level3group'])
        self.assertEqual(self.passfile.records[uuid][3], 'level3entry')
        self.assertEqual(self.passfile.records[uuid][4], 'usernamelevel3')
        self.assertFalse(5 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.records[uuid][6], 'passwordlevel3')
        self.assertEqual(self.passfile.get_creation_time(uuid, False),
                         'Thu, 25 Jul 2013 00:26:36')

if __name__ == '__main__':
    unittest.main()
