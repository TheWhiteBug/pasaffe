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
from binascii import hexlify, unhexlify

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__),
                                    "..")))

from pasaffe_lib.readdb import PassSafeFile


class TestReadDB(unittest.TestCase):
    def setUp(self):
        self.passfile = PassSafeFile()

    def test_folder_list_to_field(self):

        folder_list = [[[], ""],
                       [["foldera"], "foldera"],
                       [["folder.a"], "folder\.a"],
                       [["foldera."], "foldera\."],
                       [[".foldera"], "\.foldera"],
                       [["foldera.", "folderb."], "foldera\..folderb\."],
                       [["foldera", "folderb"], "foldera.folderb"],
                       [["folder.a", "folderb"], "folder\.a.folderb"],
                       [["foldera", "folder.b"], "foldera.folder\.b"],
                       [["folder.a", "folder.b"], "folder\.a.folder\.b"],
                       [["folder.a", "folder.b", "folder.c"],
                        "folder\.a.folder\.b.folder\.c"],
                       ]

        for (folder, field) in folder_list:
            self.assertEqual(self.passfile._folder_list_to_field(folder),
                             field)

    def test_field_to_folder_list(self):

        folder_list = [["", []],
                       ["foldera", ["foldera"]],
                       ["folder\.a", ["folder.a"]],
                       ["foldera\.", ["foldera."]],
                       ["\.foldera", [".foldera"]],
                       ["foldera\..folderb\.", ["foldera.", "folderb."]],
                       ["foldera.folderb", ["foldera", "folderb"]],
                       ["folder\.a.folderb", ["folder.a", "folderb"]],
                       ["foldera.folder\.b", ["foldera", "folder.b"]],
                       ["folder\.a.folder\.b", ["folder.a", "folder.b"]],
                       ["folder\.a.folder\.b.folder\.c",
                       ["folder.a", "folder.b", "folder.c"]],
                       ]

        for (field, folder) in folder_list:
            self.assertEqual(self.passfile._field_to_folder_list(field),
                             folder)

    def test_get_database_version_string(self):

        self.passfile.new_db("test")

        expected = '%s.%s' % (
            hexlify(self.passfile.db_version[1:2]).decode('utf-8'),
            hexlify(self.passfile.db_version[0:1]).decode('utf-8'))

        self.assertEqual(self.passfile.get_database_version_string(), expected)

        self.passfile.header[0] = b'\x0B\x03'

        self.assertEqual(self.passfile.get_database_version_string(), "03.0b")

    def test_new_entry(self):

        self.passfile.new_db("test")
        uuid_hex = self.passfile.new_entry()

        self.assertEqual(len(uuid_hex), 32)
        self.assertTrue(uuid_hex in self.passfile.records)

        for field in [1, 3, 4, 5, 6, 7, 8, 12, 13]:
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

        folder = ['folderA', 'folderB', 'folderC']
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
        self.assertTrue(self.passfile.get_folder_list(uuid_hex) is None)

        folder = ['folderA', 'folderB', 'folderC']
        folder_field = 'folderA.folderB.folderC'

        self.passfile.update_folder_list(uuid_hex, folder)

        self.assertTrue(2 in self.passfile.records[uuid_hex])
        self.assertTrue(self.passfile.records[uuid_hex][2] == folder_field)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex) == folder)

        self.assertTrue(self.passfile.get_folder_list('nonexistent') is None)

    def test_get_empty_folders(self):

        folder_fields = ['folderA',
                         'folderA.folderB',
                         'folderA.folderB.folderC']

        folder_list = [['folderA'],
                       ['folderA', 'folderB'],
                       ['folderA', 'folderB', 'folderC']]

        self.assertTrue(self.passfile.get_empty_folders() == [])
        self.passfile.empty_folders = folder_fields

        self.assertTrue(self.passfile.get_empty_folders() == folder_list)

    def test_add_empty_folder(self):

        folder_fields = ['folderA',
                         'folderA.folderB',
                         'folderA.folderB.folderC']

        folder = ['folderA', 'folderB', 'folderC']

        # Make sure it's empty
        self.assertTrue(self.passfile.empty_folders == [])

        # Add a folder, and make sure it created the children
        self.passfile.add_empty_folder(folder)
        self.assertTrue(self.passfile.empty_folders == folder_fields)

        # Make sure empty parameters work
        self.passfile.add_empty_folder(None)
        self.assertTrue(self.passfile.empty_folders == folder_fields)
        self.passfile.add_empty_folder([])
        self.assertTrue(self.passfile.empty_folders == folder_fields)

        # Try adding it again, to make sure we don't have duplicates
        self.passfile.add_empty_folder(folder)
        self.assertTrue(self.passfile.empty_folders == folder_fields)

        # Make sure adding an empty folder that isn't actually empty
        # works
        uuid_hex = self.passfile.new_entry()
        entry_folder = ['otherA']
        self.passfile.update_folder_list(uuid_hex, entry_folder)
        self.passfile.add_empty_folder(entry_folder)
        self.assertTrue(self.passfile.empty_folders == folder_fields)

        # Adding an empty folder that only has an empty subfolder should
        # only add the subfolder
        uuid_hex = self.passfile.new_entry()
        entry_folder = ['thirdA', 'thirdB']
        self.passfile.update_folder_list(uuid_hex, entry_folder)
        self.passfile.add_empty_folder(entry_folder)

        folder_fields.append('thirdA')
        self.assertTrue(self.passfile.empty_folders == folder_fields)

        # Do the same, but for 3 levels
        uuid_hex = self.passfile.new_entry()
        entry_folder = ['fourthA', 'fourthB', 'fourthC']
        self.passfile.update_folder_list(uuid_hex, entry_folder)
        self.passfile.add_empty_folder(entry_folder)

        folder_fields.append('fourthA')
        folder_fields.append('fourthA.fourthB')
        self.assertTrue(self.passfile.empty_folders == folder_fields)

    def test_remove_empty_folder(self):

        folder_fields = ['folderA',
                         'folderA.folderB',
                         'folderA.folderB.folderC']

        folder = ['folderA', 'folderB', 'folderC']

        # pass by value
        self.passfile.empty_folders = folder_fields[:]

        # Try and remove a bogus folder
        self.passfile.remove_empty_folder(['bogus'])
        self.assertTrue(self.passfile.empty_folders == folder_fields)

        # Make sure empty parameters work
        self.passfile.remove_empty_folder(None)
        self.assertTrue(self.passfile.empty_folders == folder_fields)
        self.passfile.remove_empty_folder([])
        self.assertTrue(self.passfile.empty_folders == folder_fields)

        # Now, remove an empty folder
        self.passfile.remove_empty_folder(['folderA', 'folderB'])
        folder_fields.remove('folderA.folderB')
        self.assertTrue(self.passfile.empty_folders == folder_fields)

    def test_get_all_folders(self):
        self.passfile.new_db("test")
        uuid_hex = self.passfile.new_entry()

        # First make sure there's no folders at all
        self.assertTrue(self.passfile.get_all_folders() == [])

        # Now handle an entry, but no empty folders
        folder = ['folderA', 'folderB']
        self.passfile.update_folder_list(uuid_hex, folder)
        self.assertTrue(self.passfile.get_all_folders() == [folder])

        # Now handle empty folders, but no entry
        self.passfile.update_folder_list(uuid_hex, [])
        self.assertTrue(self.passfile.get_all_folders() == [])

        folder_fields = ['folderA',
                         'folderA.folderB',
                         'folderA.folderB.folderC']
        self.passfile.empty_folders = folder_fields

        folder_list = [['folderA'],
                       ['folderA', 'folderB'],
                       ['folderA', 'folderB', 'folderC']]

        self.assertTrue(self.passfile.get_all_folders() == folder_list)

        # Now handle multiple entries, and empty folders
        self.passfile.update_folder_list(uuid_hex, folder)

        folderB = ['OtherFolderA', 'OtherFolderB']

        uuid_hex_B = self.passfile.new_entry()
        uuid_hex_C = self.passfile.new_entry()
        self.passfile.update_folder_list(uuid_hex_B, folderB)

        all_folders = folder_list + [folderB]
        self.assertTrue(self.passfile.get_all_folders() == all_folders)

    def test_rename_folder_list(self):

        self.passfile.new_db("test")

        # Create a few entries
        folderA = ['firstA', 'firstB']
        folderB = ['firstA', 'firstB', 'firstC']
        folderC = ['secondA', 'secondB']

        uuid_hex_A = self.passfile.new_entry()
        uuid_hex_B = self.passfile.new_entry()
        uuid_hex_C = self.passfile.new_entry()
        uuid_hex_D = self.passfile.new_entry()

        self.passfile.update_folder_list(uuid_hex_A, folderA)
        self.passfile.update_folder_list(uuid_hex_B, folderB)
        self.passfile.update_folder_list(uuid_hex_C, folderC)

        self.assertTrue(self.passfile.get_folder_list(uuid_hex_A) == folderA)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex_B) == folderB)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex_C) == folderC)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex_D) is None)

        # Ok, let's rename one
        new_folderA = ['firstA', 'renamedB']
        new_folderB = ['firstA', 'renamedB', 'firstC']
        self.passfile.rename_folder_list(folderA, new_folderA)

        self.assertTrue(
            self.passfile.get_folder_list(uuid_hex_A) == new_folderA)
        self.assertTrue(
            self.passfile.get_folder_list(uuid_hex_B) == new_folderB)
        self.assertTrue(
            self.passfile.get_folder_list(uuid_hex_C) == folderC)
        self.assertTrue(
            self.passfile.get_folder_list(uuid_hex_D) is None)

        # Now add some empty_folders
        folder_fields = ['firstA',
                         'secondA',
                         'thirdA',
                         'thirdA.thirdB']

        # pass by value
        self.passfile.empty_folders = folder_fields[:]

        # OK, rename entries and empty_folders
        another_new_folderA = ['renamedA', 'renamedB']
        another_new_folderB = ['renamedA', 'renamedB', 'firstC']
        new_empty_folders = [['secondA'],
                             ['thirdA'],
                             ['thirdA', 'thirdB'],
                             ['renamedA']]

        self.passfile.rename_folder_list(['firstA'], ['renamedA'])

        self.assertTrue(
            self.passfile.get_folder_list(uuid_hex_A) == another_new_folderA)
        self.assertTrue(
            self.passfile.get_folder_list(uuid_hex_B) == another_new_folderB)
        self.assertTrue(
            self.passfile.get_folder_list(uuid_hex_C) == folderC)
        self.assertTrue(
            self.passfile.get_folder_list(uuid_hex_D) is None)

        self.assertTrue(
            self.passfile.get_empty_folders() == new_empty_folders)

    def test_delete_folder(self):

        self.passfile.new_db("test")

        # Create a few entries
        folderA = ['firstA', 'firstB']
        folderB = ['firstA', 'firstB', 'firstC']
        folderC = ['secondA', 'secondB']

        uuid_hex_A = self.passfile.new_entry()
        uuid_hex_B = self.passfile.new_entry()
        uuid_hex_C = self.passfile.new_entry()
        uuid_hex_D = self.passfile.new_entry()

        self.passfile.update_folder_list(uuid_hex_A, folderA)
        self.passfile.update_folder_list(uuid_hex_B, folderB)
        self.passfile.update_folder_list(uuid_hex_C, folderC)

        self.assertTrue(self.passfile.get_folder_list(uuid_hex_A) == folderA)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex_B) == folderB)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex_C) == folderC)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex_D) is None)

        self.assertTrue(self.passfile.get_empty_folders() == [])

        # Try and delete some invalid things
        self.passfile.delete_folder(None)
        self.passfile.delete_folder([])
        self.passfile.delete_folder(['banana'])

        self.assertTrue(self.passfile.get_folder_list(uuid_hex_A) == folderA)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex_B) == folderB)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex_C) == folderC)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex_D) is None)

        self.assertTrue(self.passfile.get_empty_folders() == [])

        # Now, delete a third level.
        self.passfile.delete_folder(folderB)

        self.assertTrue(self.passfile.get_folder_list(uuid_hex_A) == folderA)
        self.assertTrue(uuid_hex_B not in self.passfile.records)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex_C) == folderC)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex_D) is None)
        self.assertTrue(uuid_hex_D in self.passfile.records)
        self.assertTrue(self.passfile.get_empty_folders() == [])

        # Add some empty_folders and delete a toplevel
        emptyA = [['firstA'],
                  ['firstA', 'firstB', 'emptyC']]
        emptyB = emptyA + [['some'],
                           ['some', 'random']]
        for folder in emptyB:
            self.passfile.add_empty_folder(folder)

        self.assertTrue(self.passfile.get_empty_folders() == emptyB)
        self.passfile.delete_folder(['some'])
        self.assertTrue(self.passfile.get_empty_folders() == emptyA)

        self.assertTrue(self.passfile.get_folder_list(uuid_hex_A) == folderA)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex_C) == folderC)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex_D) is None)
        self.assertTrue(uuid_hex_D in self.passfile.records)

        # Now delete a top level
        self.passfile.delete_folder(['firstA'])
        self.assertTrue(self.passfile.get_empty_folders() == [])
        self.assertTrue(uuid_hex_A not in self.passfile.records)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex_C) == folderC)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex_D) is None)
        self.assertTrue(uuid_hex_D in self.passfile.records)

        # Delete the remaining second level. We should gain an empty folder.
        self.passfile.delete_folder(['secondA', 'secondB'])
        self.assertTrue(uuid_hex_C not in self.passfile.records)
        self.assertTrue(self.passfile.get_folder_list(uuid_hex_D) is None)
        self.assertTrue(uuid_hex_D in self.passfile.records)
        self.assertTrue(self.passfile.get_empty_folders() == [['secondA']])

    def test_get_tree_status(self):

        self.passfile.new_db("test")
        self.assertEqual(self.passfile.get_tree_status(), None)

        self.passfile.header[6] = "Pasaffe test"
        self.assertEqual(self.passfile.get_tree_status(), None)

        self.passfile.header[3] = "101010"
        self.assertEqual(self.passfile.get_tree_status(), "101010")

        self.passfile.header[6] = "AnotherApp v1"
        self.assertEqual(self.passfile.get_tree_status(), None)

    def test_set_tree_status(self):

        self.passfile.new_db("test")
        self.passfile.header[6] = "Pasaffe test"
        self.assertEqual(self.passfile.get_tree_status(), None)

        self.passfile.set_tree_status("101010")
        self.assertEqual(self.passfile.get_tree_status(), "101010")
        self.assertTrue(3 in self.passfile.header)

        self.passfile.set_tree_status(None)
        self.assertEqual(self.passfile.get_tree_status(), None)
        self.assertFalse(3 in self.passfile.header)

    def test_fixups(self):

        self.passfile.new_db("test")
        uuid_hex = self.passfile.new_entry()

        # New entry should have empty strings
        self.assertEqual(self.passfile.records[uuid_hex][4], '')
        self.assertEqual(self.passfile.records[uuid_hex][5], '')
        self.assertEqual(self.passfile.records[uuid_hex][6], '')

        # Delete username and password
        del self.passfile.records[uuid_hex][4]
        del self.passfile.records[uuid_hex][6]

        # add a comment with CRLF terminators
        crlf = ("First line\r\n" +
                "Second line\r\n" +
                "Third line")

        lf = ("First line\n" +
              "Second line\n" +
              "Third line")

        self.passfile.records[uuid_hex][5] = crlf

        self.assertTrue(4 not in self.passfile.records[uuid_hex])
        self.assertTrue(6 not in self.passfile.records[uuid_hex])
        self.assertEqual(self.passfile.records[uuid_hex][5], crlf)

        # Now do the postread fixup
        self.passfile._postread_fixup()

        self.assertEqual(self.passfile.records[uuid_hex][4], '')
        self.assertEqual(self.passfile.records[uuid_hex][5], lf)
        self.assertEqual(self.passfile.records[uuid_hex][6], '')

        # OK, do the presave fixup
        self.assertEqual(self.passfile._presave_fixup(uuid_hex, 5), crlf)

    def _create_find_db(self):

        entries = [{3: "carte de crédit",
                    4: "username1",
                    5: "This is a note",
                    6: "password1",
                    13: "http://www.example.com"},
                   {2: "folder1",
                    3: "carte de credit",
                    4: "username1",
                    5: "anothernote",
                    6: "password1"},
                   {2: "level1group.level2group.level3group",
                    3: "level3entry",
                    4: "usernamelevel3",
                    6: "passwordlevel3",
                    13: "http://note.com"}]

        self.passfile.new_db('pasaffe')

        for entry in entries:
            uuid = self.passfile.new_entry()
            for key in entry.keys():
                self.passfile.records[uuid][key] = entry[key]

    def test_update_find_results(self):

        self._create_find_db()

        self.passfile.update_find_results("")
        self.assertEqual(self.passfile.find_results, [])
        self.assertEqual(self.passfile.find_results_index, None)
        self.assertEqual(self.passfile.find_value, "")

        # Test field 3
        self.passfile.update_find_results("level3entry")
        self.assertEqual(len(self.passfile.find_results), 1)
        self.assertEqual(self.passfile.find_results_index, None)
        self.assertEqual(self.passfile.find_value, "level3entry")

        # Test field 5
        self.passfile.update_find_results("another")
        self.assertEqual(len(self.passfile.find_results), 1)
        self.assertEqual(self.passfile.find_results_index, None)
        self.assertEqual(self.passfile.find_value, "another")

        # Test field 13
        self.passfile.update_find_results("example.com")
        self.assertEqual(len(self.passfile.find_results), 1)
        self.assertEqual(self.passfile.find_results_index, None)
        self.assertEqual(self.passfile.find_value, "example.com")

        # Test matching entries with accents
        self.passfile.update_find_results("credit")
        self.assertEqual(len(self.passfile.find_results), 2)
        self.assertEqual(self.passfile.find_results_index, None)
        self.assertEqual(self.passfile.find_value, "credit")

        # Test specifying search term with accent
        self.passfile.update_find_results("crédit")
        self.assertEqual(len(self.passfile.find_results), 2)
        self.assertEqual(self.passfile.find_results_index, None)
        self.assertEqual(self.passfile.find_value, "crédit")

        # Test force option
        self.passfile.find_results = []
        self.passfile.update_find_results("crédit")
        self.assertEqual(len(self.passfile.find_results), 0)
        self.passfile.update_find_results("crédit", True)
        self.assertEqual(len(self.passfile.find_results), 2)

        # Test clearing out values
        self.passfile.update_find_results("")
        self.assertEqual(self.passfile.find_results, [])
        self.assertEqual(self.passfile.find_results_index, None)
        self.assertEqual(self.passfile.find_value, "")

    def test_get_next_find_result(self):

        self._create_find_db()

        self.assertEqual(self.passfile.get_next_find_result(), None)
        self.assertEqual(self.passfile.get_next_find_result(True), None)

        self.passfile.update_find_results("note")
        self.assertEqual(len(self.passfile.find_results), 3)
        self.assertEqual(self.passfile.find_results_index, None)
        self.assertEqual(self.passfile.find_value, "note")

        self.assertEqual(self.passfile.find_results_index, None)

        uuid1 = self.passfile.get_next_find_result()
        self.assertEqual(self.passfile.find_results_index, 0)
        self.assertNotEqual(uuid1, None)

        uuid2 = self.passfile.get_next_find_result()
        self.assertEqual(self.passfile.find_results_index, 1)
        self.assertNotEqual(uuid2, None)
        self.assertNotEqual(uuid1, uuid2)

        uuid3 = self.passfile.get_next_find_result()
        self.assertEqual(self.passfile.find_results_index, 2)
        self.assertNotEqual(uuid3, None)
        self.assertNotEqual(uuid1, uuid3)
        self.assertNotEqual(uuid2, uuid3)

        # This should wrap around
        uuid4 = self.passfile.get_next_find_result()
        self.assertEqual(self.passfile.find_results_index, 0)
        self.assertNotEqual(uuid4, None)
        self.assertEqual(uuid1, uuid4)

        # And now try backwards
        uuid5 = self.passfile.get_next_find_result(True)
        self.assertEqual(self.passfile.find_results_index, 2)
        self.assertNotEqual(uuid5, None)
        self.assertEqual(uuid3, uuid5)

if __name__ == '__main__':
    unittest.main()
