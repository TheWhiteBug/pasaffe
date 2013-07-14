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


if __name__ == '__main__':    
    unittest.main()
