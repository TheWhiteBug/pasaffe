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
import struct
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__),
                                                 "..")))

from pasaffe_lib.keepassx import KeePassX


class TestKeePass2224(unittest.TestCase):
    def setUp(self):
        self.passfile = KeePassX('./tests/databases/keepass2-224.xml')

    def _find_uuid(self, name):
        for uuid in self.passfile.records:
            if self.passfile.records[uuid][3] == name:
                return uuid
        return None

    def _get_time(self, uuid, entry):
        '''Returns a string of time'''
        if entry in self.passfile.records[uuid]:
            unpacked_time = struct.unpack(
                "<I", self.passfile.records[uuid][entry])[0]
            converted_time = time.gmtime(unpacked_time)
            return time.strftime("%a, %d %b %Y %H:%M:%S", converted_time)
        else:
            return None

    def test_num_entries(self):
        self.assertEqual(len(self.passfile.records), 3)

    def test_entry_1(self):

        entry_name = "Sample Entry"
        uuid = self._find_uuid(entry_name)

        self.assertFalse(2 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.records[uuid][3], entry_name)
        self.assertEqual(self.passfile.records[uuid][4], 'User Name')
        self.assertEqual(self.passfile.records[uuid][5], 'Notes')
        self.assertEqual(self.passfile.records[uuid][6], 'Password')
        self.assertEqual(self._get_time(uuid, 7), 'Sat, 15 Feb 2014 18:56:55')
        self.assertEqual(self._get_time(uuid, 8), 'Sat, 15 Feb 2014 18:56:55')
        self.assertEqual(self._get_time(uuid, 12), 'Sat, 15 Feb 2014 18:56:55')
        self.assertEqual(self.passfile.records[uuid][13],
                         'http://keepass.info/')

    def test_entry_2(self):

        entry_name = "Sample Entry #2"
        uuid = self._find_uuid(entry_name)

        self.assertFalse(2 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.records[uuid][3], entry_name)
        self.assertEqual(self.passfile.records[uuid][4], 'Michael321')
        self.assertFalse(5 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.records[uuid][6], '12345')
        self.assertEqual(self._get_time(uuid, 7), 'Sat, 15 Feb 2014 18:56:55')
        self.assertEqual(self._get_time(uuid, 8), 'Sat, 15 Feb 2014 18:56:55')
        self.assertEqual(self._get_time(uuid, 12), 'Sat, 15 Feb 2014 18:56:55')
        self.assertEqual(self.passfile.records[uuid][13],
                         'http://keepass.info/help/kb/testform.html')

    def test_entry_3(self):

        entry_name = "innetwork1"
        uuid = self._find_uuid(entry_name)

        self.assertEqual(self.passfile.records[uuid][2], 'Network')
        self.assertEqual(self.passfile.records[uuid][3], entry_name)
        self.assertEqual(self.passfile.records[uuid][4], 'username1')
        self.assertEqual(self.passfile.records[uuid][5],
                         'This is a note\nThis is line two\n' +
                         'This is unicode: ééé\nThis is line four')
        self.assertEqual(self.passfile.records[uuid][6], 'password1')
        self.assertEqual(self._get_time(uuid, 7), 'Sat, 15 Feb 2014 18:57:52')
        self.assertEqual(self._get_time(uuid, 8), 'Sat, 15 Feb 2014 18:58:30')
        self.assertEqual(self._get_time(uuid, 12), 'Sat, 15 Feb 2014 18:58:30')
        self.assertEqual(self.passfile.records[uuid][13], 'hostname1')


if __name__ == '__main__':
    unittest.main()
