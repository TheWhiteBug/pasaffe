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

from pasaffe_lib.gpassfile import GPassFile


class TestGPass50(unittest.TestCase):
    def setUp(self):
        self.passfile = GPassFile('./tests/databases/gpass-050.gps', 'pasaffe')

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

        entry_name = "entry2"
        uuid = self._find_uuid(entry_name)

        self.assertEqual(self.passfile.records[uuid][2], 'folder2')
        self.assertEqual(self.passfile.records[uuid][3], entry_name)
        self.assertEqual(self.passfile.records[uuid][4], 'username2')
        self.assertEqual(self.passfile.records[uuid][5],
                         'This is a description\nline 2\nline 3\n')
        self.assertEqual(self.passfile.records[uuid][6], 'password2')
        self.assertEqual(self._get_time(uuid, 7), 'Mon, 27 Jan 2014 01:16:44')
        self.assertEqual(self._get_time(uuid, 8), 'Mon, 27 Jan 2014 01:16:44')
        self.assertEqual(self._get_time(uuid, 12), 'Mon, 27 Jan 2014 01:16:44')
        self.assertEqual(self.passfile.records[uuid][13], 'hostname2')
        self.assertFalse(99 in self.passfile.records[uuid])

    def test_entry_2(self):

        entry_name = "topentry1"
        uuid = self._find_uuid(entry_name)

        self.assertFalse(2 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.records[uuid][3], entry_name)
        self.assertEqual(self.passfile.records[uuid][4], 'username1')
        self.assertEqual(self.passfile.records[uuid][5],
                         'This is a description\nSecond line\nUnicode: ééé')
        self.assertEqual(self.passfile.records[uuid][6], 'password1')
        self.assertEqual(self._get_time(uuid, 7), 'Mon, 27 Jan 2014 01:15:54')
        self.assertEqual(self._get_time(uuid, 8), 'Mon, 27 Jan 2014 01:15:54')
        self.assertEqual(self._get_time(uuid, 12), 'Mon, 27 Jan 2014 01:15:54')
        self.assertEqual(self.passfile.records[uuid][13], 'hostname1')
        self.assertFalse(99 in self.passfile.records[uuid])

    def test_entry_3(self):

        entry_name = "infolder4"
        uuid = self._find_uuid(entry_name)

        self.assertEqual(self.passfile.records[uuid][2], 'folder3.folder4')
        self.assertEqual(self.passfile.records[uuid][3], entry_name)
        self.assertEqual(self.passfile.records[uuid][4], 'username4')
        self.assertFalse(5 in self.passfile.records[uuid])
        self.assertEqual(self.passfile.records[uuid][6], 'password4')
        self.assertEqual(self._get_time(uuid, 7), 'Fri, 14 Feb 2014 03:53:29')
        self.assertEqual(self._get_time(uuid, 8), 'Fri, 14 Feb 2014 03:53:58')
        self.assertEqual(self._get_time(uuid, 12), 'Fri, 14 Feb 2014 03:53:58')
        self.assertFalse(13 in self.passfile.records[uuid])
        self.assertFalse(99 in self.passfile.records[uuid])

    def test_empty_folders(self):

        empty_fields = ['folder3',
                        'folder3.folder5',
                        'emptyfolder1',
                        'emptyfolder1.emptyfolder2']

        self.assertEqual(len(self.passfile.empty_folders), len(empty_fields))
        self.assertEqual(self.passfile.empty_folders.sort(),
                         empty_fields.sort())


if __name__ == '__main__':
    unittest.main()
