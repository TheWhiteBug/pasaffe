#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2013-2024 Marc Deslauriers <marc.deslauriers@canonical.com>
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
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__),
                "..")))

from pasaffe_lib.readdb import PassSafeFile  # noqa: E402


class TestPasaffe058(unittest.TestCase):
    def setUp(self):
        self.passfile = PassSafeFile(
            './tests/databases/pasaffe-058.psafe3', 'pasaffe')

    def test_num_entries(self):
        self.assertEqual(len(self.passfile.records), 3)

    def test_empty_folders(self):

        empty_folders = [['emptygroup1'],
                         ['emptygroup1', 'emptygroup2'],
                         ['emptygroup1', 'emptygroup2', 'emptygroup3'],
                         ['level1group', 'level2group'],
                         ['emptygroup1', 'test'],
                         ['emptygroup1', 'with/slash']]

        empty_fields = ['emptygroup1',
                        'emptygroup1.emptygroup2',
                        'emptygroup1.emptygroup2.emptygroup3',
                        'level1group.level2group',
                        'emptygroup1.test',
                        'emptygroup1.with/slash']

        self.assertEqual(len(self.passfile.empty_folders), len(empty_fields))
        self.assertEqual(self.passfile.get_empty_folders(), empty_folders)
        self.assertEqual(self.passfile.empty_folders, empty_fields)

    def test_get_database_version_string(self):
        self.assertEqual(self.passfile.get_database_version_string(), "03.0b")

    def test_get_database_uuid(self):
        self.assertEqual(self.passfile.header[1],
                         b'\xa6\x95\x8d\xb5\xf6;\x03^\x84.\x84\x9d\xf4F\x8b\xd6')

    def test_get_saved_name(self):
        self.assertEqual(self.passfile.get_saved_name(), "mdeslaur")

    def test_get_saved_host(self):
        self.assertEqual(self.passfile.get_saved_host(), "mdlinux")

    def test_get_saved_application(self):
        self.assertEqual(self.passfile.get_saved_application(), 'Pasaffe v0')

    def test_get_saved_date_string(self):
        self.assertEqual(self.passfile.get_saved_date_string(False),
                         'Sat, 09 Mar 2024 19:52:49')

    def test_entry_1(self):
        uuid = 'bed4430224f472ff6ad4973bed76fcb1'
        self.assertFalse(2 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.get_folder_list(uuid), [])
        self.assertEqual(self.passfile.records[uuid][3], 'topentry1')
        self.assertEqual(self.passfile.records[uuid][4], 'username1')
        self.assertEqual(self.passfile.records[uuid][5], 'This is a note')
        self.assertEqual(self.passfile.records[uuid][6], 'password1')
        self.assertEqual(self.passfile.records[uuid][20], 'test@example.com')
        self.assertEqual(self.passfile.get_creation_time(uuid, False),
                         'Sat, 09 Mar 2024 19:52:49')
        self.assertEqual(self.passfile.records[uuid][13],
                         'http://www.example.com')

    def test_entry_2(self):
        uuid = '51df4cf8a707dc78ec492a757f2ebf7c'
        self.assertEqual(self.passfile.records[uuid][2], 'level1group')
        self.assertEqual(self.passfile.get_folder_list(uuid), ['level1group'])
        self.assertEqual(self.passfile.records[uuid][3], 'level1entry')
        self.assertEqual(self.passfile.records[uuid][4], 'username1')
        self.assertEqual(self.passfile.records[uuid][5], 'This is a note')
        self.assertEqual(self.passfile.records[uuid][6], 'password1')
        self.assertEqual(self.passfile.get_creation_time(uuid, False),
                         'Sat, 09 Mar 2024 19:52:49')

    def test_entry_3(self):
        uuid = 'a737271cba2043009b06cd1434370a7d'
        self.assertEqual(self.passfile.records[uuid][2],
                         'level1group.level2group.level3group')
        self.assertEqual(self.passfile.get_folder_list(uuid),
                         ['level1group', 'level2group', 'level3group'])
        self.assertEqual(self.passfile.records[uuid][3], 'level3entry')
        self.assertEqual(self.passfile.records[uuid][4], 'usernamelevel3')
        self.assertEqual(self.passfile.records[uuid][5], '')
        self.assertEqual(self.passfile.records[uuid][6], 'passwordlevel3')
        self.assertEqual(self.passfile.get_creation_time(uuid, False),
                         'Sat, 09 Mar 2024 19:52:49')


if __name__ == '__main__':
    unittest.main()
