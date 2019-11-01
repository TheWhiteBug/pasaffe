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
import subprocess
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__),
                                                 "..")))


class TestDumpDB(unittest.TestCase):
    def setUp(self):
        pass

    def test_dump_db(self):
        out = subprocess.check_output(['bin/pasaffe-dump-db', '-q', '-f',
                                       './tests/databases/pasaffe-025.psafe3',
                                       '-m', 'pasaffe'])

        expected_out = b'''Entry: level1entry
Username: username1
Password: password1
Notes: This is a note

Entry: level3entry
Username: usernamelevel3
Password: passwordlevel3

Entry: topentry1
Username: username1
Password: password1
URL: http://www.example.com
Notes: This is a note

'''
        self.assertEqual(out, expected_out)

    def test_dump_db_verbose(self):
        out = subprocess.check_output(['bin/pasaffe-dump-db', '-f',
                                       './tests/databases/pasaffe-025.psafe3',
                                       '-m', 'pasaffe'])

        self.assertTrue(b'WARNING: this will display all password entries.'
                        in out)


if __name__ == '__main__':
    unittest.main()
