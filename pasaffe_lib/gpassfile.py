# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2011-2013 Marc Deslauriers <marc.deslauriers@canonical.com>
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

from . import blowfish
import logging
logger = logging.getLogger('pasaffe_lib')


class GPassFile:

    def __init__(self, filename=None, password=None):
        '''Reads a GPass file'''

        self.records = {}
        self.gpass_iv = b"\x05\x17\x01\x7b\x0c\x03\x36\x5e"
        self.decoded_db = None
        self.index = 0
        self.imported_folders = {}
        self.empty_folders = []

        self.cipher = None

        if filename is not None:
            self._readfile(filename, password)

    def _parse_entry(self, entry_id, parent_id, entry_data):
        '''Parse an entry'''

        uuid = os.urandom(16)
        uuid_hex = hexlify(uuid).decode('utf-8')
        timestamp = struct.pack("<I", int(time.time()))
        new_entry = {1: uuid, 3: '', 4: '', 6: '',
                     7: timestamp, 8: timestamp, 12: timestamp}

        # Stick the parent_id in here for now, we'll remove it
        # once we've figured out the folder tree
        new_entry[99] = parent_id

        entry_index = 0

        entry_index, entry_name = self.get_entry_string(entry_data,
                                                        entry_index)
        new_entry[3] = entry_name
        logger.debug("entry_name is %s" % entry_name)

        entry_index, entry_desc = self.get_entry_string(entry_data,
                                                        entry_index)
        if entry_desc != "":
            new_entry[5] = entry_desc
        logger.debug("entry_desc is %s" % entry_desc)

        entry_index, entry_ctime = self.get_entry_int(entry_data,
                                                      entry_index)
        new_entry[7] = entry_ctime
        logger.debug("creation time is %s" % hexlify(entry_ctime))

        entry_index, entry_mtime = self.get_entry_int(entry_data,
                                                      entry_index)

        # Gpass doesn't separately track when password was modified
        new_entry[8] = entry_mtime
        new_entry[12] = entry_mtime
        logger.debug("modification time is %s" %
                     hexlify(entry_mtime))

        entry_index, entry_expflag = self.get_entry_int(entry_data,
                                                        entry_index)
        logger.debug("expiration flag is %s" % hexlify(entry_expflag))

        entry_index, entry_etime = self.get_entry_int(entry_data,
                                                      entry_index)
        if struct.unpack("<I", entry_expflag)[0] != 0:
            new_entry[10] = entry_etime
        logger.debug("expiration time is %s" % hexlify(entry_etime))

        entry_index, entry_username = self.get_entry_string(entry_data,
                                                            entry_index)
        new_entry[4] = entry_username
        logger.debug("username is %s" % entry_username)

        entry_index, entry_pass = self.get_entry_string(entry_data,
                                                        entry_index)
        new_entry[6] = entry_pass
        # logger.debug("password is %s" % entry_pass)

        entry_index, entry_url = self.get_entry_string(entry_data,
                                                       entry_index)
        if entry_url != "":
            new_entry[13] = entry_url
        logger.debug("URL is %s" % entry_url)

        self.records[uuid_hex] = new_entry

    def _parse_folder(self, entry_id, parent_id, entry_data):
        '''Parse a folder'''

        entry_index = 0
        entry_index, entry_name = self.get_entry_string(entry_data,
                                                        entry_index)
        logger.debug("folder_name is %s" % entry_name)

        folder = [entry_name, parent_id]
        self.imported_folders[entry_id] = folder

        # We don't actually do anything with these, but leave them
        # here in case we do parse them at some point
        #
        # entry_index, entry_desc = self.get_entry_string(entry_data,
        #                                                entry_index)
        # logger.debug("entry_desc is %s" % entry_desc)
        #
        # entry_index, entry_ctime = self.get_entry_int(entry_data,
        #                                              entry_index)
        # logger.debug("creation time is %s" % hexlify(entry_ctime))
        #
        # entry_index, entry_mtime = self.get_entry_int(entry_data,
        #                                              entry_index)
        # logger.debug("modification time is %s" %
        #             hexlify(entry_mtime))
        #
        # entry_index, entry_expflag = self.get_entry_int(entry_data,
        #                                                entry_index)
        # logger.debug("expiration flag is %s" % hexlify(entry_expflag))
        #
        # entry_index, entry_etime = self.get_entry_int(entry_data,
        #                                                  entry_index)
        # logger.debug("expiration time is %s" % hexlify(entry_etime))

    def _readfile(self, filename, password):
        '''Parses database file'''
        try:
            dbfile = open(filename, 'rb')
        except Exception:
            raise RuntimeError("Could not open %s. Aborting." % filename)

        dbdata = dbfile.read()

        key = hashlib.sha1(password.encode('utf-8')).digest()
        self.cipher = blowfish.Blowfish(key)
        self.cipher.initCBC(iv=struct.unpack("Q", self.gpass_iv)[0])

        self.decoded_db = self.cipher.decryptCBC(dbdata)
        self.remove_padding()
        self.validate_header()

        self.index = 0

        while self.index < len(self.decoded_db):

            # We just generate a new UUID instead of using the GPass id
            entry_id = self.get_int()
            logger.debug("id is %s" % hexlify(entry_id))

            # We don't handle parents in Pasaffe for now
            parent_id = self.get_int()
            logger.debug("parent_id is %s" % hexlify(parent_id))

            entry_type = self.get_bytes()
            logger.debug("entry_type is %s" % entry_type)

            entry_data = self.get_bytes()

            # We don't handle anything else than standard entries for now
            if entry_type == b"general":
                self._parse_entry(entry_id, parent_id, entry_data)
            elif entry_type == b"folder":
                self._parse_folder(entry_id, parent_id, entry_data)
            else:
                continue

        dbfile.close()

        self._set_folders()
        self._find_empty_folders()

    def _folder_list_to_field(self, folder_list):
        '''Converts a folder list to a folder field'''
        field = ""

        if folder_list is None:
            return field

        for folder in folder_list:
            if field != "":
                field += "."
            field += folder.replace(".", "\\.")
        return field

    def _set_folders(self):
        '''Set an entry's folder from the folder list'''

        for uuid in self.records:
            if self.records[uuid][99] != b'\x00\x00\x00\x00':
                folder_list = self._get_folder_list(self.records[uuid][99])
                self.records[uuid][2] = self._folder_list_to_field(folder_list)

            del self.records[uuid][99]

    def _find_empty_folders(self):
        '''Find empty folders'''

        for folder in self.imported_folders:
            name, parent = self.imported_folders[folder]
            folder_list = [name]
            while(parent != b'\x00\x00\x00\x00'):
                name, parent = self.imported_folders[parent]
                folder_list.insert(0, name)

            self.add_empty_folder(folder_list)

    def add_empty_folder(self, folder):
        '''Adds a folder to the empty folders list'''

        if folder is None or folder == []:
            return

        for part in range(len(folder)):
            field = self._folder_list_to_field(folder[:part + 1])
            logger.debug("searching for %s" % field)
            if field not in self.empty_folders:
                # Make sure it's actually empty
                found = False
                for uuid in list(self.records.keys()):
                    if 2 not in self.records[uuid]:
                        continue
                    if self.records[uuid][2] == field:
                        logger.debug("folder %s isn't empty" % field)
                        found = True
                        break

                if found is False:
                    logger.debug("adding %s" % field)
                    self.empty_folders.append(field)

    def _get_folder_list(self, parent_id):
        '''From a parent id, figure out a folder list'''

        name, parent = self.imported_folders[parent_id]
        folder_list = [name]
        while(parent != b'\x00\x00\x00\x00'):
            name, parent = self.imported_folders[parent]
            folder_list.insert(0, name)

        return folder_list

    def remove_padding(self):
        padding = self.decoded_db[-1]

        for byte in self.decoded_db[-padding:]:
            if byte != padding:
                return

        self.decoded_db = self.decoded_db[:-padding]

    def validate_header(self):
        gpass_magic_prefix = b"GPassFile version 1.1.0"

        logger.debug("decoded_db header is %s" %
                     self.decoded_db[:len(gpass_magic_prefix)])

        # Check magic prefix
        if not self.decoded_db.startswith(gpass_magic_prefix):
            raise RuntimeError("File is not a GPass database,"
                               " or wrong password. Aborting.")

        # Skip header
        self.decoded_db = self.decoded_db[len(gpass_magic_prefix):]

    def get_int(self):
        value = self.decoded_db[self.index:self.index + 4]
        self.index += 4
        return value

    def get_bytes(self):
        length = struct.unpack("<I", self.get_int())[0]
        value = self.decoded_db[self.index:self.index + length]
        self.index += length
        return value

    def get_entry_int(self, entry, entry_index):
        value = 0
        b = 1

        for i in range(6):
            c = entry[entry_index + i]
            if c & 0x80:
                value += b * (c & 0x7f)
                b *= 0x80
            else:
                value += b * c
                return entry_index + i + 1, struct.pack("<I", value)

    def get_entry_string(self, entry, entry_index):
        entry_index, length = self.get_entry_int(entry, entry_index)
        length = struct.unpack("<I", length)[0]
        value = entry[entry_index:entry_index + length]
        entry_index += length
        return entry_index, value.decode('utf-8')
