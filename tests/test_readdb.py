#!/usr/bin/python
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

class TestReadDB(unittest.TestCase):
    def setUp(self):
        self.passfile = PassSafeFile()

    def test_folder_list_to_field(self):

        folder_list = [ [ [ ], "" ],
                        [ [ "foldera" ], "foldera" ],
                        [ [ "folder.a" ], "folder\.a" ],
                        [ [ "foldera." ], "foldera\." ],
                        [ [ ".foldera" ], "\.foldera" ],
                        [ [ "foldera.", "folderb." ], "foldera\..folderb\." ],
                        [ [ "foldera", "folderb" ], "foldera.folderb" ],
                        [ [ "folder.a", "folderb" ], "folder\.a.folderb" ],
                        [ [ "foldera", "folder.b" ], "foldera.folder\.b" ],
                        [ [ "folder.a", "folder.b" ], "folder\.a.folder\.b" ],
                        [ [ "folder.a", "folder.b", "folder.c" ], "folder\.a.folder\.b.folder\.c" ],
                      ]

        for (folder, field) in folder_list:
            self.assertEqual(self.passfile._folder_list_to_field(folder), field)

    def test_field_to_folder_list(self):

        folder_list = [ [ "", [ ] ],
                        [ "foldera", [ "foldera" ] ],
                        [ "folder\.a", [ "folder.a" ] ],
                        [ "foldera\.", [ "foldera." ] ],
                        [ "\.foldera", [ ".foldera" ] ],
                        [ "foldera\..folderb\.", [ "foldera.", "folderb." ] ],
                        [ "foldera.folderb", [ "foldera", "folderb" ] ],
                        [ "folder\.a.folderb", [ "folder.a", "folderb" ] ],
                        [ "foldera.folder\.b", [ "foldera", "folder.b" ] ],
                        [ "folder\.a.folder\.b", [ "folder.a", "folder.b" ] ],
                        [ "folder\.a.folder\.b.folder\.c", [ "folder.a", "folder.b", "folder.c" ] ],
                      ]

        for (field, folder) in folder_list:
            self.assertEqual(self.passfile._field_to_folder_list(field), folder)

    def test_get_database_version_string(self):

        self.passfile.new_db("test")

        expected = '%s.%s' % (self.passfile.db_version[1].encode('hex'),
                              self.passfile.db_version[0].encode('hex'))

        self.assertEqual(self.passfile.get_database_version_string(), expected)

        self.passfile.header[0] = '\x0B\x03'

        self.assertEqual(self.passfile.get_database_version_string(), "03.0b")

    def test_new_entry(self):

        self.passfile.new_db("test")
        uuid_hex = self.passfile.new_entry()

        self.assertEqual(len(uuid_hex), 32)
        self.assertTrue(uuid_hex in self.passfile.records)

        for field in [ 1, 3, 4, 5, 6, 7, 8, 12, 13 ]:
            self.assertTrue(field in self.passfile.records[uuid_hex])

    def test_delete_entry(self):

        self.passfile.new_db("test")
        uuid_hex = self.passfile.new_entry()

        self.assertTrue(uuid_hex in self.passfile.records)

        self.passfile.delete_entry(uuid_hex)

        self.assertTrue(uuid_hex not in self.passfile.records)

    def test_update_modification_time(self):

        self.passfile.new_db("test")
        uuid_hex = self.passfile.new_entry()

        old_time = self.passfile.records[uuid_hex][12]
        time.sleep(1.1)
        self.passfile.update_modification_time(uuid_hex)
        new_time = self.passfile.records[uuid_hex][12]

        self.assertTrue(old_time != new_time)

    def test_update_password_time(self):

        self.passfile.new_db("test")
        uuid_hex = self.passfile.new_entry()

        old_time = self.passfile.records[uuid_hex][8]
        time.sleep(1.1)
        self.passfile.update_password_time(uuid_hex)
        new_time = self.passfile.records[uuid_hex][8]

        self.assertTrue(old_time != new_time)

    def test_update_folder_list(self):

        self.passfile.new_db("test")
        uuid_hex = self.passfile.new_entry()

        self.assertTrue(2 not in self.passfile.records[uuid_hex])

        folder = [ 'folderA', 'folderB', 'folderC' ]
        folder_field = 'folderA.folderB.folderC'

        self.passfile.update_folder_list(uuid_hex, folder)

        self.assertTrue(2 in self.passfile.records[uuid_hex])
        self.assertTrue(self.passfile.records[uuid_hex][2] == folder_field)

        self.passfile.update_folder_list(uuid_hex, [])
        self.assertTrue(2 not in self.passfile.records[uuid_hex])

    def test_get_folder_list(self):

        self.passfile.new_db("test")
        uuid_hex = self.passfile.new_entry()

        self.assertTrue(2 not in self.passfile.records[uuid_hex])
        self.assertTrue(self.passfile.get_folder_list(uuid_hex) == None)

        folder = [ 'folderA', 'folderB', 'folderC' ]
        folder_field = 'folderA.folderB.folderC'

        self.passfile.update_folder_list(uuid_hex, folder)

        self.assertTrue(2 in self.passfile.records[uuid_hex])
        self.assertTrue(self.passfile.records[uuid_hex][2] == folder_field)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex) == folder)

        self.assertTrue(self.passfile.get_folder_list('nonexistent') == None)

    def test_get_empty_folders(self):

        folder_fields = [ 'folderA',
                          'folderA.folderB',
                          'folderA.folderB.folderC' ]

        folder_list = [ [ 'folderA' ],
                        [ 'folderA', 'folderB' ],
                        [ 'folderA', 'folderB', 'folderC' ] ]

        self.assertTrue(self.passfile.get_empty_folders() == [])
        self.passfile.empty_folders = folder_fields

        self.assertTrue(self.passfile.get_empty_folders() == folder_list)





if __name__ == '__main__':    
    unittest.main()
