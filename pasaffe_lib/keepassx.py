# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2011 Francesco Marella <francesco.marella@gmail.com>
# Copyright (C) 2012 Marc Deslauriers <marc.deslauriers@canonical.com>
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
logger = logging.getLogger('pasaffe_lib')


class KeePassX:
    records = []
    skipped = []
    index = 0

    cipher = None

    def __init__(self, filename=None):
        """ Reads a KeePassX/KeePass2 XML file"""

        if filename != None:
            self.readfile(filename)

    def _convert_time(self, timestring, tz):
        """ Converts time format"""
        if timestring:
            if tz:
                value = time.mktime(time.strptime(timestring,"%Y-%m-%dT%H:%M:%SZ"))
            else:
                value = time.mktime(time.strptime(timestring,"%Y-%m-%dT%H:%M:%S"))
        else:
            value = time.time()

        return struct.pack("<I", int(value))

    def readfile(self, filename):
        """ Parses database file"""
        try:
            element = ET.parse(filename)
        except Exception:
            raise RuntimeError("Could not open %s. Aborting." % filename)

        if element.getroot().tag == 'database':
            for groupitem in element.findall('./group'):
                # Don't import the backups
                if groupitem.find('title').text == "Backup":
                    continue

                for pwitem in groupitem.iter('entry'):
                    uuid = os.urandom(16)
                    timestamp = struct.pack("<I", int(time.time()))
                    new_entry = {1: uuid, 3: '', 4: '', 6: '',
                                 7: timestamp, 8: timestamp, 12: timestamp}

                    for x in list(pwitem):
                        if x.tag == 'title':
                            new_entry[3] = (x.text or 'Untitled item').encode("utf-8")
                        elif x.tag == 'username':
                            new_entry[4] = (x.text or '').encode("utf-8")
                        elif x.tag == 'password':
                            new_entry[6] = (x.text or '').encode("utf-8")
                        elif x.tag == 'url':
                            new_entry[13] = (x.text or '').encode("utf-8")
                        elif x.tag == 'creation':
                            new_entry[7] = self._convert_time(x.text, False)
                        elif x.tag == 'lastmod':
                            new_entry[8] = self._convert_time(x.text, False)
                            new_entry[12] = self._convert_time(x.text, False)
                        elif x.tag == 'comment':
                            new_entry[5] = (x.text or '').encode("utf-8")
                            for subelement in list(x):
                                new_entry[5] += "\n" + (subelement.tail or '').encode("utf-8")
                        else:
                            if x.tag not in self.skipped:
                                self.skipped.append(x.tag)

                    self.records.append(new_entry)

        elif element.getroot().tag == 'KeePassFile':
            for groupitem in element.findall('./Root/Group'):
                for pwitem in list(groupitem):
                    uuid = os.urandom(16)
                    timestamp = struct.pack("<I", int(time.time()))
                    new_entry = {1: uuid, 3: '', 4: '', 6: '',
                                 7: timestamp, 8: timestamp, 12: timestamp}

                    if pwitem.tag == 'Entry':
                        for x in list(pwitem):
                            if x.tag == 'Times':
                                for timesitem in list(x):
                                    if timesitem.tag == 'CreationTime':
                                        new_entry[7] = self._convert_time(timesitem.text, True)
                                    elif timesitem.tag == 'LastModificationTime':
                                        new_entry[8] = self._convert_time(timesitem.text, True)
                                        new_entry[12] = self._convert_time(timesitem.text, True)

                            elif x.tag == 'String': 
                                for stritem in list(x):
                                    if stritem.text == 'Title':
                                        new_entry[3] = (x.find('Value').text or 'Untitled item').encode("utf-8")
                                    elif stritem.text == 'UserName':
                                        new_entry[4] = (x.find('Value').text or '').encode("utf-8")
                                    elif stritem.text == 'Password':
                                        new_entry[6] = (x.find('Value').text or '').encode("utf-8")
                                    elif stritem.text == 'URL':
                                        new_entry[13] = (x.find('Value').text or '').encode("utf-8")
                                    elif stritem.text == 'Notes':
                                        new_entry[5] = (x.find('Value').text or '').encode("utf-8")
                                    else:
                                        if stritem.tag == 'Key' and stritem.text not in self.skipped:
                                            self.skipped.append(stritem.text)

                            else:
                                if x.tag not in self.skipped:
                                    self.skipped.append(x.tag)

                        self.records.append(new_entry)

        else:
            raise RuntimeError("Not a valid KeePassX or KeePass2 XML file")

