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

from pasaffe_lib.helpers import folder_list_to_field
from pasaffe_lib.helpers import folder_list_to_path
from pasaffe_lib.helpers import folder_path_to_list
from pasaffe_lib.helpers import PathEntry

class TestHelpers(unittest.TestCase):
    def test_folder_list_to_field(self):

        folder_list = [ [ [ ], "" ],
                        [ [ "foldera" ],  "foldera" ],
                        [ [ "folder.a" ], "folder\.a" ],
                        [ [ "foldera." ], "foldera\." ],
                        [ [ ".foldera" ], "\.foldera" ],
                        [ [ "foldera.", "folderb." ], "foldera\..folderb\." ],
                        [ [ "foldera",  "folderb" ],  "foldera.folderb" ],
                        [ [ "folder.a", "folderb" ],  "folder\.a.folderb" ],
                        [ [ "foldera",  "folder.b" ], "foldera.folder\.b" ],
                        [ [ "folder.a", "folder.b" ], "folder\.a.folder\.b" ],
                        [ [ "folder.a", "folder.b", "folder.c" ],
                          "folder\.a.folder\.b.folder\.c" ],
                      ]

        for (folder, field) in folder_list:
            self.assertEqual(folder_list_to_field(folder), field)

    def test_folder_list_to_path(self):

        folder_list = [ [ [ ], "/" ],
                        [ [ "foldera" ],  "/foldera/" ],
                        [ [ "folder.a" ], "/folder.a/" ],
                        [ [ "folder/a" ], "/folder\/a/" ],
                        [ [ "foldera." ], "/foldera./" ],
                        [ [ "foldera/" ], "/foldera\//" ],
                        [ [ ".foldera" ], "/.foldera/" ],
                        [ [ "/foldera" ], "/\/foldera/" ],
                        [ [ "foldera.", "folderb." ], "/foldera./folderb./" ],
                        [ [ "foldera/", "folderb/" ], "/foldera\//folderb\//" ],
                        [ [ "foldera",  "folderb" ],  "/foldera/folderb/" ],
                        [ [ "folder.a", "folderb" ],  "/folder.a/folderb/" ],
                        [ [ "folder/a", "folderb" ],  "/folder\/a/folderb/" ],
                        [ [ "foldera",  "folder.b" ], "/foldera/folder.b/" ],
                        [ [ "foldera",  "folder/b" ], "/foldera/folder\/b/" ],
                        [ [ "folder.a", "folder.b" ], "/folder.a/folder.b/" ],
                        [ [ "folder/a", "folder/b" ], "/folder\/a/folder\/b/" ],
                        [ [ "folder.a", "folder.b", "folder.c" ],
                          "/folder.a/folder.b/folder.c/" ],
                        [ [ "folder/a", "folder/b", "folder/c" ],
                          "/folder\/a/folder\/b/folder\/c/" ],
                      ]

        for (folder, path) in folder_list:
            self.assertEqual(folder_list_to_path(folder), path)

    def test_folder_path_to_list(self):

        folder_list = [ [ "/", [ ] ],
                        [ "/foldera/",   [ "foldera" ]  ],
                        [ "/folder.a/",  [ "folder.a" ] ],
                        [ "/folder\/a/", [ "folder/a" ] ],
                        [ "/foldera./",  [ "foldera." ] ],
                        [ "/foldera\//", [ "foldera/" ] ],
                        [ "/.foldera/",  [ ".foldera" ] ],
                        [ "/\/foldera/", [ "/foldera" ] ],
                        [ "/foldera./folderb./",   [ "foldera.", "folderb." ] ],
                        [ "/foldera\//folderb\//", [ "foldera/", "folderb/" ] ],
                        [ "/foldera/folderb/",     [ "foldera",  "folderb" ]  ],
                        [ "/folder.a/folderb/",    [ "folder.a", "folderb" ]  ],
                        [ "/folder\/a/folderb/",   [ "folder/a", "folderb" ]  ],
                        [ "/foldera/folder.b/",    [ "foldera",  "folder.b" ] ],
                        [ "/foldera/folder\/b/",   [ "foldera",  "folder/b" ] ],
                        [ "/folder.a/folder.b/",   [ "folder.a", "folder.b" ] ],
                        [ "/folder\/a/folder\/b/", [ "folder/a", "folder/b" ] ],
                        [ "/folder.a/folder.b/folder.c/",
                          [ "folder.a", "folder.b", "folder.c" ] ],
                        [ "/folder\/a/folder\/b/folder\/c/",
                          [ "folder/a", "folder/b", "folder/c" ] ],
                      ]

        for (path, folder) in folder_list:
            self.assertEqual(folder_path_to_list(path), folder)

    def test_sort_name(self):
        pathentry = PathEntry(None, None, None)

        names = [ [ "",    "zzz", -1 ],
                  [ None,  "zzz", -1 ],
                  [ "a",   "zzz", -1 ],
                  [ "aaa", "z",   -1 ],
                  [ "aaa", "zzz", -1 ],
                  [ "z",   "zzz", -1 ],
                  [ "aaa", "aaa",  0 ],
                  [ "zzz", "zzz",  0 ],
                  [ None,  None,   0 ],
                  [ None,  "",     0 ],
                  [ "",    None,   0 ],
                  [ "zzz", "z",    1 ],
                  [ "zzz",  "",    1 ],
                  [ "zzz",  None,  1 ]
                ]

        for (first, second, result) in names:
            self.assertEqual(pathentry._sort_name(first, second), result)

    def test_sort_path(self):
        pathentry = PathEntry(None, None, None)

        paths = [
                  [ ["zzz"],          [],             -1 ],
                  [ ["zzz"],          None,           -1 ],
                  [ ["a"],            ["zzz"],        -1 ],
                  [ ["aaa"],          ["z"],          -1 ],
                  [ ["aaa"],          ["zzz"],        -1 ],
                  [ ["z"],            ["zzz"],        -1 ],
                  [ ["a", "a"],       ["a"],          -1 ],
                  [ ["a", "a", "a"],  ["a"],          -1 ],
                  [ ["aaa"],          ["aaa"],         0 ],
                  [ ["zzz"],          ["zzz"],         0 ],
                  [ None,             None,            0 ],
                  [ None,             [],              0 ],
                  [ [],               None,            0 ],
                  [ ["a"],            ["a", "a"],      1 ],
                  [ ["a", "a"],       ["a", "a", "a"], 1 ],
                  [ ["zzz"],          ["z"],           1 ],
                  [ [],               ["zzz"],         1 ],
                  [ None,             ["zzz"],         1 ],
                ]

        for (first, second, result) in paths:
            self.assertEqual(pathentry._sort_path(first, second), result)

    def test_sort_entries(self):
        test_entries = [
                         [ "z",  None ],
                         [ "a",  None ],
                         [ "aa", None ],
                         [ "a",  ["a"] ],
                         [ "a",  ["b"] ],
                         [ "z",  ["a", "b"] ],
                         [ "a",  ["a", "b"] ],
                         [ None, ["a", "b", "c"] ],
                         [ "c",  ["a", "b"] ],
                       ]

        test_results = [
                         [ None, ["a", "b", "c"] ],
                         [ "a",  ["a", "b"] ],
                         [ "c",  ["a", "b"] ],
                         [ "z",  ["a", "b"] ],
                         [ "a",  ["a"] ],
                         [ "a",  ["b"] ],
                         [ "a",  None ],
                         [ "aa", None ],
                         [ "z",  None ],
                       ]

        entries = []
        results = []

        for (name, path) in test_entries:
            new_entry = PathEntry(name, None, path)
            entries.append(new_entry)

        for (name, path) in test_results:
            new_result = PathEntry(name, None, path)
            results.append(new_result)

        # Now, sort them and check
        sorted_entries = sorted(entries)
        self.assertEqual(len(test_entries), len(results))
        self.assertEqual(len(test_entries), len(entries))
        self.assertEqual(len(test_entries), len(sorted_entries))

        for i in range(len(test_entries)):
            self.assertEqual(sorted_entries[i], results[i])

if __name__ == '__main__':
    unittest.main()
