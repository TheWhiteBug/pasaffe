#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2014 Marc Deslauriers <marc.deslauriers@canonical.com>
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


class TestPasswdSafeAndroid510(unittest.TestCase):
    def setUp(self):
        self.passfile = PassSafeFile(
            './tests/databases/passwdsafe-510.psafe3', 'pasaffe')

    def test_num_entries(self):
        self.assertEqual(len(self.passfile.records), 4)

    def test_empty_folders(self):
        self.assertEqual(len(self.passfile.empty_folders), 0)

    def test_get_database_version_string(self):
        self.assertEqual(self.passfile.get_database_version_string(), "03.0d")

    def test_get_database_uuid(self):
        self.assertEqual(self.passfile.header[1],
                         b'b\xfb\x00\x00\x9al2\x13\x05\xb8\xccnh\x81L\xb5')

    def test_get_saved_name(self):
        self.assertEqual(self.passfile.get_saved_name(),
                         'User')

    def test_get_saved_host(self):
        self.assertEqual(self.passfile.get_saved_host(),
                         'Galaxy Nexus')

    def test_get_saved_application(self):
        self.assertEqual(self.passfile.get_saved_application(),
                         'PasswdSafe 5.1.0')

    def test_get_saved_date_string(self):
        self.assertEqual(self.passfile.get_saved_date_string(),
                         'Sat, 25 Oct 2014 12:05:42')

    def test_entry_1(self):
        uuid = 'af5304edb06c32131d502487eeb21009'
        self.assertEqual(self.passfile.records[uuid][2], 'Toplevel2')
        self.assertEqual(self.passfile.get_folder_list(uuid), ['Toplevel2'])
        self.assertEqual(self.passfile.records[uuid][3], 'Intoplevel2')
        self.assertEqual(self.passfile.records[uuid][4], 'username')
        self.assertFalse(5 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.records[uuid][6], 'password')
        self.assertFalse(8 in self.passfile.records[uuid])
        self.assertFalse(12 in self.passfile.records[uuid])

    def test_entry_2(self):
        uuid = '7f1f06b3a36c3213061dc476b88f83fd'
        self.assertFalse(2 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.get_folder_list(uuid), [])
        self.assertEqual(self.passfile.records[uuid][3], 'Toplevel')
        self.assertEqual(self.passfile.records[uuid][4], 'topuser')
        self.assertEqual(self.passfile.records[uuid][5], 'This is a note\n' +
                                                         'This is line 2\n' +
                                                         'Unicode: éléphant')
        self.assertEqual(self.passfile.records[uuid][6], 'toppass')
        self.assertFalse(8 in self.passfile.records[uuid])
        self.assertFalse(12 in self.passfile.records[uuid])

    def test_entry_3(self):
        uuid = '82bd036bb86c32130facf0a8e3e3809b'
        self.assertEqual(self.passfile.records[uuid][2], 'Top.withdot')
        self.assertEqual(self.passfile.get_folder_list(uuid),
                         ['Top', 'withdot'])
        self.assertEqual(self.passfile.records[uuid][3], 'Indot')
        self.assertEqual(self.passfile.records[uuid][4], '')
        self.assertFalse(5 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.records[uuid][6], 'password')
        self.assertFalse(8 in self.passfile.records[uuid])
        self.assertFalse(12 in self.passfile.records[uuid])

    def test_entry_4(self):
        uuid = '116301c0aa6c321334769a2131e417c5'
        self.assertEqual(self.passfile.records[uuid][2], 'Toplevel1')
        self.assertEqual(self.passfile.get_folder_list(uuid), ['Toplevel1'])
        self.assertEqual(self.passfile.records[uuid][3], 'Intoplevel1')
        self.assertEqual(self.passfile.records[uuid][4], 'username')
        self.assertEqual(self.passfile.records[uuid][6], 'password')
        self.assertEqual(self.passfile.records[uuid][13],
                         'http://www.example.com')
        self.assertFalse(8 in self.passfile.records[uuid])
        self.assertFalse(12 in self.passfile.records[uuid])


if __name__ == '__main__':
    unittest.main()
