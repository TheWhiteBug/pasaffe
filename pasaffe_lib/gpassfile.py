# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2011 Marc Deslauriers <marc.deslauriers@canonical.com>
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

import sys, struct, hashlib, os, time
import blowfish
import logging
logger = logging.getLogger('pasaffe_lib')

class GPassFile:

    records = []
    gpass_iv = "\x05\x17\x01\x7b\x0c\x03\x36\x5e"
    decoded_db = None
    index = 0

    cipher = None

    def __init__(self, filename=None, password=None):
        '''Reads a GPass file'''

        if filename != None:
            self.readfile(filename, password)

    def readfile(self, filename, password):
        '''Parses database file'''
        try:
            dbfile = open(filename, 'r').read()
        except Exception:
            raise RuntimeError("Could not open %s. Aborting." % filename)

        key = hashlib.sha1(password).digest()
        self.cipher = blowfish.Blowfish(key)
        self.cipher.initCBC(iv=struct.unpack("Q", self.gpass_iv)[0])

        self.decoded_db = self.cipher.decryptCBC(dbfile)
        self.remove_padding()
        self.validate_header()

        self.index = 0

        while self.index < len(self.decoded_db):
            uuid = os.urandom(16)
            timestamp = struct.pack("<I", int(time.time()))
            new_entry = {1: uuid, 3: '', 4: '', 6: '',
                         7: timestamp, 8: timestamp, 12: timestamp}

            # We just generate a new UUID instead of using the GPass id
            entry_id = self.get_int()
            logger.debug("id is %s" % entry_id.encode("hex"))

            # We don't handle parents in Pasaffe for now
            parent_id = self.get_int()
            logger.debug("parent_id is %s" % parent_id.encode("hex"))

            entry_type = self.get_string()
            logger.debug("entry_type is %s" % entry_type)

            entry_data = self.get_string()
            #logger.debug("entry_data is %s" % entry_data)

            # We don't handle anything else than standard entries for now
            if entry_type != "general":
                continue

            # OK, now parse entry data
            entry_index = 0

            entry_index, entry_name = self.get_entry_string(entry_data, entry_index)
            new_entry[3] = entry_name
            logger.debug("entry_name is %s" % entry_name)

            entry_index, entry_desc = self.get_entry_string(entry_data, entry_index)
            if entry_desc != "":
                new_entry[5] = entry_desc
            logger.debug("entry_desc is %s" % entry_desc)

            entry_index, entry_ctime = self.get_entry_int(entry_data, entry_index)
            new_entry[7] = entry_ctime
            logger.debug("creation time is %s" % entry_ctime.encode("hex"))

            entry_index, entry_mtime = self.get_entry_int(entry_data, entry_index)
            # Gpass doesn't separately track when password was modified
            new_entry[8] = entry_mtime
            new_entry[12] = entry_mtime
            logger.debug("modification time is %s" % entry_mtime.encode("hex"))

            entry_index, entry_expflag = self.get_entry_int(entry_data, entry_index)
            logger.debug("expiration flag is %s" % entry_expflag.encode("hex"))

            entry_index, entry_etime = self.get_entry_int(entry_data, entry_index)
            if struct.unpack("<I", entry_expflag)[0] != 0:
                new_entry[10] = entry_etime
            logger.debug("expiration time is %s" % entry_etime.encode("hex"))

            entry_index, entry_username = self.get_entry_string(entry_data, entry_index)
            new_entry[4] = entry_username
            logger.debug("username is %s" % entry_username)

            entry_index, entry_pass = self.get_entry_string(entry_data, entry_index)
            new_entry[6] = entry_pass
            #logger.debug("password is %s" % entry_pass)

            entry_index, entry_url = self.get_entry_string(entry_data, entry_index)
            if entry_url != "":
                new_entry[13] = entry_url
            logger.debug("URL is %s" % entry_url)

            self.records.append(new_entry)

    def remove_padding(self):
        padding = self.decoded_db[-1]

        for byte in self.decoded_db[:-ord(padding)]:
            if byte != padding:
                return

        self.decoded_db = self.decoded_db[:-ord(padding)]

    def validate_header(self):
        gpass_magic_prefix = "GPassFile version 1.1.0"

        logger.debug("decoded_db header is %s" % self.decoded_db[:len(gpass_magic_prefix)])

        # Check magic prefix
		if not self.decoded_db.startswith(gpass_magic_prefix):
            raise RuntimeError("File is not a GPass database, or wrong password. Aborting.")

        # Skip header
        self.decoded_db = self.decoded_db[len(gpass_magic_prefix):]

    def get_int(self):
        value = self.decoded_db[self.index:self.index+4]
        self.index += 4
        return value

    def get_string(self):
        length = struct.unpack("<I", self.get_int())[0]
        value = self.decoded_db[self.index:self.index+length]
        self.index += length
        return value

    def get_entry_int(self, entry, entry_index):
        value = 0
        b = 1

        for i in range(6):
            c = ord(entry[entry_index+i])
            if c & 0x80:
                value += b * (c & 0x7f)
                b *= 0x80;
            else:
                value += b * c
				return entry_index + i + 1, struct.pack("<I", value)

    def get_entry_string(self, entry, entry_index):
        entry_index, length = self.get_entry_int(entry, entry_index)
        length = struct.unpack("<I", length)[0]
        value = entry[entry_index:entry_index+length]
        entry_index += length
        return entry_index, value
