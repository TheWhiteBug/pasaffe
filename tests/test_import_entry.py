#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2013-2024 Marc Deslauriers <marc.deslauriers@canonical.com>
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
import tempfile
import shutil
import subprocess
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__),
                                                 "..")))

from pasaffe_lib.readdb import PassSafeFile  # noqa: E402


class TestImportEntry(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.tempdir, 'test.psafe3')
        shutil.copy('./tests/databases/pasaffe-058.psafe3', self.test_db)

    def tearDown(self):
        if os.path.exists(self.tempdir):
            shutil.rmtree(self.tempdir)

    def test_orig_db(self):
        passfile = PassSafeFile(self.test_db, 'pasaffe')
        self.assertEqual(len(passfile.records), 3)

    def test_import_entry(self):

        name = 'testimport1'
        url = 'http://www.launchpad.net/pasaffe'
        user = 'testuser'
        password = 'testpass'
        note = "This is a note"
        email = "test2@example.com"

        rc = subprocess.call(['bin/pasaffe-import-entry', '-q',
                              '-f', self.test_db,
                              '-m', 'pasaffe',
                              '-e', name,
                              '-l', url,
                              '-i', email,
                              '-u', user,
                              '-p', password,
                              '-n', note])

        self.assertEqual(rc, 0)

        passfile = PassSafeFile(self.test_db, 'pasaffe')
        self.assertEqual(len(passfile.records), 4)

        # Locate the new entry
        for uuid in passfile.records:
            if passfile.records[uuid][3] == name:
                break

        self.assertEqual(passfile.records[uuid][3], name)
        self.assertEqual(passfile.records[uuid][4], user)
        self.assertEqual(passfile.records[uuid][5], note)
        self.assertEqual(passfile.records[uuid][6], password)
        self.assertEqual(passfile.records[uuid][13], url)
        self.assertEqual(passfile.records[uuid][20], email)


if __name__ == '__main__':
    unittest.main()
