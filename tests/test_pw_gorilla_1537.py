#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
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
### END LICENSE

import sys
import os.path
import unittest
import time
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from pasaffe_lib.readdb import PassSafeFile

class TestPasswordGorilla1537(unittest.TestCase):
    def setUp(self):
        self.passfile = PassSafeFile('./tests/databases/pw-gorilla-1537.psafe3', 'pasaffe')

    def test_num_entries(self):
        self.assertEqual(len(self.passfile.records), 6)

    def test_empty_folders(self):
        # This version of Password Gorilla doesn't save empty folders
        self.assertEqual(len(self.passfile.empty_folders), 0)

    def test_get_database_version_string(self):
        self.assertEqual(self.passfile.get_database_version_string(), "03.00")

    def test_get_database_uuid(self):
        self.assertEqual(self.passfile.header[1],
                         b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

    def test_get_saved_name(self):
        self.assertEqual(self.passfile.get_saved_name(), None)

    def test_get_saved_host(self):
        self.assertEqual(self.passfile.get_saved_host(), None)

    def test_get_saved_application(self):
        self.assertEqual(self.passfile.get_saved_application(), None)

    def test_get_saved_date_string(self):
        self.assertEqual(self.passfile.get_saved_date_string(), None)

    def test_entry_1(self):
        uuid = '009eeceaad754732634e37d2f70b0985'
        self.assertEqual(self.passfile.records[uuid][2], 'top\\.withdot')
        self.assertEqual(self.passfile.get_folder_list(uuid), ['top.withdot'])
        self.assertEqual(self.passfile.records[uuid][3], 'insidedot')
        self.assertEqual(self.passfile.records[uuid][4], 'usernamedot')
        self.assertFalse(5 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.records[uuid][6], 'passworddot')
        self.assertEqual(self.passfile.get_password_time(uuid, False),
                         'Sat, 25 Oct 2014 15:05:30')
        self.assertEqual(self.passfile.get_modification_time(uuid, False),
                         'Sat, 25 Oct 2014 15:05:30')

    def test_entry_2(self):
        uuid = 'd68cee64c2794300561837e248abddd1'
        self.assertFalse(2 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.get_folder_list(uuid), None)
        self.assertEqual(self.passfile.records[uuid][3], 'toplevel1')
        self.assertEqual(self.passfile.records[uuid][4], 'usernametop')
        self.assertEqual(self.passfile.records[uuid][5], 'This is a note')
        self.assertEqual(self.passfile.records[uuid][6], 'passwordtop')
        self.assertEqual(self.passfile.get_password_time(uuid, False),
                         'Sat, 25 Oct 2014 15:04:48')
        self.assertEqual(self.passfile.get_modification_time(uuid, False),
                         'Sat, 25 Oct 2014 15:04:48')

    def test_entry_3(self):
        uuid = '8e869cc656a942fd7beecf36605140d8'
        self.assertEqual(self.passfile.records[uuid][2], 'topgroup1.topgroup2.topgroup3')
        self.assertEqual(self.passfile.get_folder_list(uuid), ['topgroup1', 'topgroup2', 'topgroup3'])
        self.assertEqual(self.passfile.records[uuid][3], 'entrylevel3')
        self.assertEqual(self.passfile.records[uuid][4], 'username3')
        self.assertFalse(5 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.records[uuid][6], 'password3')
        self.assertEqual(self.passfile.get_password_time(uuid, False),
                         'Sat, 25 Oct 2014 15:06:51')
        self.assertEqual(self.passfile.get_modification_time(uuid, False),
                         'Sat, 25 Oct 2014 15:06:51')

    def test_entry_4(self):
        uuid = '3e317b83f4d645056abc5526f9c1f7e6'
        self.assertEqual(self.passfile.records[uuid][2], 'topgroup1')
        self.assertEqual(self.passfile.get_folder_list(uuid), ['topgroup1'])
        self.assertEqual(self.passfile.records[uuid][3], 'entrylevel1')
        self.assertEqual(self.passfile.records[uuid][4], 'username1')
        self.assertEqual(self.passfile.records[uuid][5],
                         'This is a note\r\nThis is a second line\r\nUnicode: éléphant')
        self.assertEqual(self.passfile.records[uuid][6], 'password1')
        self.assertEqual(self.passfile.get_password_time(uuid, False),
                         'Sat, 25 Oct 2014 15:07:24')
        self.assertEqual(self.passfile.get_modification_time(uuid, False),
                         'Sat, 25 Oct 2014 15:07:24')

    def test_entry_5(self):
        uuid = '11fbf64e83e240a25e8bb657cea6edcd'
        self.assertFalse(2 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.get_folder_list(uuid), None)
        self.assertEqual(self.passfile.records[uuid][3], 'topnopass')
        self.assertEqual(self.passfile.records[uuid][4], 'topusername')
        self.assertFalse(5 in self.passfile.records[uuid])
        self.assertFalse(6 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.get_password_time(uuid, False),
                         None)
        self.assertEqual(self.passfile.get_modification_time(uuid, False),
                         'Sat, 25 Oct 2014 15:07:52')

    def test_entry_6(self):
        uuid = 'd0b7295a7fc447fa4d8c1aa701ba8c30'
        self.assertFalse(2 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.get_folder_list(uuid), None)
        self.assertEqual(self.passfile.records[uuid][3], 'topnouser')
        self.assertFalse(4 in self.passfile.records[uuid])
        self.assertFalse(5 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.records[uuid][6], 'toppassword')
        self.assertEqual(self.passfile.get_password_time(uuid, False),
                         'Sat, 25 Oct 2014 15:07:40')
        self.assertEqual(self.passfile.get_modification_time(uuid, False),
                         'Sat, 25 Oct 2014 15:07:40')

if __name__ == '__main__':
    unittest.main()
