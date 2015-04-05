# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2011 Francesco Marella <fra.marella@gmx.com>
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
#

import sys
import struct
import hashlib
import os
import time
from binascii import hexlify, unhexlify
from xml.etree import cElementTree as ET
import logging
logger = logging.getLogger('pasaffe_lib')


class KeePassX:
    def __init__(self, filename=None):
        """ Reads a KeePassX/KeePass2 XML file"""

        self.records = {}
        self.skipped = []
        self.index = 0
        self.cipher = None
        self.parent_map = None

        if filename is not None:
            self.readfile(filename)

    def _convert_time(self, timestring, tz):
        """ Converts time format"""
        if timestring:
            if tz:
                value = time.mktime(time.strptime(
                                    timestring, "%Y-%m-%dT%H:%M:%SZ"))
            else:
                value = time.mktime(time.strptime(
                                    timestring, "%Y-%m-%dT%H:%M:%S"))
        else:
            value = time.time()

        return struct.pack("<I", int(value))

    def _folder_list_to_field(self, folder_list):
        '''Converts a folder list to a folder field'''
        field = ""

        if folder_list is None:
            return field

        if folder_list == []:
            return field

        for folder in folder_list:
            if field != "":
                field += "."
            field += folder.replace(".", "\\.")
        return field

    def _get_folders(self, entry):
        '''Searches parent map to locate folders for KeePassX'''
        folder_list = []
        if entry not in self.parent_map:
            return folder_list

        parent = self.parent_map[entry]
        while True:
            if parent.tag == 'group':
                for x in list(parent):
                    if x.tag == 'title':
                        folder_list.insert(0, x.text)
                        break
            if parent not in self.parent_map:
                break
            else:
                parent = self.parent_map[parent]

        return folder_list

    def _get_folders_v2(self, entry):
        '''Searches parent map to locate folders for KeePass2'''
        folder_list = []
        if entry not in self.parent_map:
            return folder_list

        parent = self.parent_map[entry]
        while True:
            if parent.tag == 'Group':
                for x in list(parent):
                    if x.tag == 'Name':
                        folder_list.insert(0, x.text)
                        break
            if parent not in self.parent_map:
                break
            else:
                parent = self.parent_map[parent]

        # Remove the top-level 'NewDatabase' folder
        folder_list.pop(0)

        return folder_list

    def readfile(self, filename):
        """ Parses database file"""
        try:
            element = ET.parse(filename)
        except Exception:
            raise RuntimeError("Could not open %s. Aborting." % filename)

        self.parent_map = {c: p for p in element.iter() for c in p}

        if element.getroot().tag == 'database':
            for groupitem in element.findall('./group'):
                # Don't import the backups
                if groupitem.find('title').text == "Backup":
                    continue

                for pwitem in groupitem.iter('entry'):
                    uuid = os.urandom(16)
                    uuid_hex = hexlify(uuid).decode('utf-8')
                    timestamp = struct.pack("<I", int(time.time()))
                    new_entry = {1: uuid, 3: '', 4: '', 6: '',
                                 7: timestamp, 8: timestamp, 12: timestamp}

                    for x in list(pwitem):
                        if x.tag == 'title':
                            new_entry[3] = (x.text or 'Untitled item')
                        elif x.tag == 'username':
                            new_entry[4] = (x.text or '')
                        elif x.tag == 'password':
                            new_entry[6] = (x.text or '')
                        elif x.tag == 'url':
                            new_entry[13] = (x.text or '')
                        elif x.tag == 'creation':
                            new_entry[7] = self._convert_time(x.text, False)
                        elif x.tag == 'lastmod':
                            new_entry[8] = self._convert_time(x.text, False)
                            new_entry[12] = self._convert_time(x.text, False)
                        elif x.tag == 'comment':
                            new_entry[5] = (x.text or '')
                            for subelement in list(x):
                                new_entry[5] += "\n" + (subelement.tail or '')
                        else:
                            if x.tag not in self.skipped:
                                self.skipped.append(x.tag)

                    folders = self._get_folders(pwitem)
                    if folders != []:
                        new_entry[2] = self._folder_list_to_field(folders)

                    self.records[uuid_hex] = new_entry

        elif element.getroot().tag == 'KeePassFile':
            for groupitem in element.findall('./Root/Group'):
                for pwitem in groupitem.iter('Entry'):
                    uuid = os.urandom(16)
                    uuid_hex = hexlify(uuid).decode('utf-8')
                    timestamp = struct.pack("<I", int(time.time()))
                    new_entry = {1: uuid, 3: '', 4: '', 6: '',
                                 7: timestamp, 8: timestamp, 12: timestamp}

                    for x in list(pwitem):
                        if x.tag == 'Times':
                            for timesitem in list(x):
                                if timesitem.tag == 'CreationTime':
                                    new_entry[7] = self._convert_time(
                                        timesitem.text, True)
                                elif timesitem.tag == 'LastModificationTime':
                                    new_entry[8] = self._convert_time(
                                        timesitem.text, True)
                                    new_entry[12] = self._convert_time(
                                        timesitem.text, True)

                        elif x.tag == 'String':
                            for stritem in list(x):
                                if stritem.text == 'Title':
                                    new_entry[3] = (x.find('Value').text or
                                                    'Untitled item')
                                elif stritem.text == 'UserName':
                                    new_entry[4] = (x.find('Value').text or
                                                    '')
                                elif stritem.text == 'Password':
                                    new_entry[6] = (x.find('Value').text or
                                                    '')
                                elif stritem.text == 'URL':
                                    new_entry[13] = (x.find('Value').text or
                                                     '')
                                elif stritem.text == 'Notes':
                                    new_entry[5] = (x.find('Value').text or
                                                    '')
                                else:
                                    if (stritem.tag == 'Key' and
                                            stritem.text not in self.skipped):
                                        self.skipped.append(stritem.text)

                        else:
                            if x.tag not in self.skipped:
                                self.skipped.append(x.tag)

                    folders = self._get_folders_v2(pwitem)
                    if folders != []:
                        new_entry[2] = self._folder_list_to_field(folders)

                    self.records[uuid_hex] = new_entry

        else:
            raise RuntimeError("Not a valid KeePassX or KeePass2 XML file")
