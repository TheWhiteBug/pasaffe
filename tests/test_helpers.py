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

if __name__ == '__main__':
    unittest.main()
