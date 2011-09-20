# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2011 Francesco Marella <francesco.marella@gmail.com>
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
import struct
import hashlib
import os
import time
from xml.etree import cElementTree as ET
import logging
logger = logging.getLogger('pasaffe')


class FigaroXML:
    records = []
    index = 0

    cipher = None

    def __init__(self, filename=None, password=None):
        """ Reads a FPM2 file"""

        if filename != None:
            self.readfile(filename, password)

    def readfile(self, filename, password):
        """ Parses database file"""
        try:
            element = ET.parse(filename)
        except Exception:
            raise RuntimeError("Could not open %s. Aborting." % filename)

        if element.getroot().tag != 'FPM':
            raise RuntimeError("Not a valid FPM2 XML file")

        for pwitem in element.findall('./PasswordList/PasswordItem'):
            uuid = os.urandom(16)
            timestamp = struct.pack("<I", int(time.time()))
            new_entry = {1: uuid, 3: '', 4: '', 6: '',
                         7: timestamp, 8: timestamp, 12: timestamp}

            for x in list(pwitem):
                if x.tag == 'title':
                    new_entry[3] = x.text or 'Untitled item'
                elif x.tag == 'user':
                    new_entry[4] = x.text or ''
                elif x.tag == 'password':
                    new_entry[6] = x.text or ''
                elif x.tag == 'url':
                    new_entry[13] = x.text or ''
                elif x.tag == 'notes':
                    new_entry[5] = x.text or ''

            self.records.append(new_entry)