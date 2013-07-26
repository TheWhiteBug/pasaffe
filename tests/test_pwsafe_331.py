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

class TestPasswordSafe331(unittest.TestCase):
    def setUp(self):
        self.passfile = PassSafeFile('./tests/databases/pwsafe-331.psafe3', 'pasaffe')

    def test_num_entries(self):
        self.assertEqual(len(self.passfile.records), 3)

    def test_empty_folders(self):
        self.assertEqual(len(self.passfile.empty_folders), 6)

    def test_get_database_version_string(self):
        self.assertEqual(self.passfile.get_database_version_string(), "03.0b")

    def test_get_saved_name(self):
        self.assertEqual(self.passfile.get_saved_name(), "mdeslaur")

    def test_get_saved_host(self):
        self.assertEqual(self.passfile.get_saved_host(), "mdlinux")

    def test_get_saved_application(self):
        self.assertEqual(self.passfile.get_saved_application(), 'Password Safe V3.31')

    def test_get_saved_date_string(self):
        self.assertEqual(self.passfile.get_saved_date_string(), 'Thu, 25 Jul 2013 19:57:08')


if __name__ == '__main__':
    unittest.main()
