# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2011-2012 Francesco Marella <fra.marella@gmx.com>
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

import struct
import os
import time
from binascii import hexlify
from xml.etree import cElementTree as ET
import logging
logger = logging.getLogger('pasaffe_lib')


class FigaroXML:
    def __init__(self, filename=None):
        """ Reads a FPM2 file"""

        self.records = {}
        self.skipped = []
        self.index = 0
        self.cipher = None

        if filename is not None:
            self.readfile(filename)

    def readfile(self, filename):
        """ Parses database file"""
        try:
            element = ET.parse(filename)
        except Exception:
            raise RuntimeError("Could not open %s. Aborting." % filename)

        if element.getroot().tag != 'FPM':
            raise RuntimeError("Not a valid FPM2 XML file")

        for pwitem in element.findall('./PasswordList/PasswordItem'):
            uuid = os.urandom(16)
            uuid_hex = hexlify(uuid).decode('utf-8')
            timestamp = struct.pack("<I", int(time.time()))
            new_entry = {1: uuid, 3: '', 4: '', 6: '',
                         7: timestamp, 8: timestamp, 12: timestamp}

            for x in list(pwitem):
                if x.tag == 'title':
                    new_entry[3] = (x.text or 'Untitled item')
                elif x.tag == 'user':
                    new_entry[4] = (x.text or '')
                elif x.tag == 'password':
                    new_entry[6] = (x.text or '')
                elif x.tag == 'url':
                    new_entry[13] = (x.text or '')
                elif x.tag == 'notes':
                    new_entry[5] = (x.text or '')
                elif x.tag == 'category':
                    category = x.text
                    if category is not None:
                        new_entry[2] = category.replace(".", "\\.")
                else:
                    if x.tag not in self.skipped:
                        self.skipped.append(x.tag)

            self.records[uuid_hex] = new_entry
