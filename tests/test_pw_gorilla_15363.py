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

class TestPasswordGorilla15363(unittest.TestCase):
    def setUp(self):
        self.passfile = PassSafeFile('./tests/databases/pw-gorilla-15363.psafe3', 'pasaffe')

    def test_num_entries(self):
        self.assertEqual(len(self.passfile.records), 4)

    def test_empty_folders(self):
        # This version of Password Gorilla doesn't save empty folders
        self.assertEqual(len(self.passfile.empty_folders), 0)

    def test_get_database_version_string(self):
        self.assertEqual(self.passfile.get_database_version_string(), "03.00")

    def test_get_saved_name(self):
        self.assertEqual(self.passfile.get_saved_name(), None)

    def test_get_saved_host(self):
        self.assertEqual(self.passfile.get_saved_host(), None)

    def test_get_saved_application(self):
        self.assertEqual(self.passfile.get_saved_application(), None)

    def test_get_saved_date_string(self):
        self.assertEqual(self.passfile.get_saved_date_string(), None)


if __name__ == '__main__':
    unittest.main()
