#!/usr/bin/python3
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
import struct
import tempfile
import shutil
import subprocess
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from pasaffe_lib.keepassx import KeePassX
from pasaffe_lib.readdb import PassSafeFile
from test_figaro_079 import TestFigaroXML079

class TestFigaroXMLImport(TestFigaroXML079):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.imported_db = os.path.join(self.tempdir, 'imported.psafe3')
        rc = subprocess.call(['bin/pasaffe-import-figaroxml', '-q',
                              '-f', './tests/databases/figaro-079.xml',
                              '-d', self.imported_db,
                              '-y', '-m', 'pasaffe'])
        self.passfile = PassSafeFile(self.imported_db, 'pasaffe')

    def tearDown(self):
        if os.path.exists(self.tempdir):
            shutil.rmtree(self.tempdir)

if __name__ == '__main__':
    unittest.main()
