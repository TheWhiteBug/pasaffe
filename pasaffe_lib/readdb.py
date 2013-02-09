# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
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
### END LICENSE

import sys
import struct
import hashlib
import hmac
import random
import os
import time
import tempfile
import shutil
import pwd

import pytwofishcbc
import logging
logger = logging.getLogger('pasaffe_lib')
from . pasaffeconfig import get_version


class PassSafeFile:

    def __init__(self, filename=None, password=None, req_cipher='Twofish'):
        '''Reads a Password Safe v3 file'''

        self.keys = {}
        self.header = {}
        self.records = {}
        self.cipher = None
        self.cipher_block_size = 0
        self.hmac = None
        self.dbfile = None

        if req_cipher == 'Twofish':
            self.cipher = pytwofishcbc.TwofishCBC()
            self.cipher_block_size = self.cipher.get_block_size()
        else:
            raise ValueError("Sorry, we don't support %s yet." % cipher)

        if filename != None:
            self.readfile(filename, password)

    def readfile(self, filename, password):
        '''Parses database file'''
        logger.debug('Opening database: %s' % filename)
        try:
            self.dbfile = open(filename, 'r')
        except Exception:
            raise RuntimeError("Could not open %s. Aborting." % filename)

        tag = self.dbfile.read(4)
        if tag != "PWS3":
            raise RuntimeError("File %s is not a password safe database."
                               " Aborting." % filename)

        self._readkeys(password)
        self._readheader()
        self._readrecords()
        self._validatehmac()
        self.dbfile.close()
        self.dbfile = None

        # Now that we've read the file, but before we get rid of the
        # password, generate new keys for our next save
        self.new_keys(password)

        # Don't need the password anymore, clear it out
        password = ''

    def new_db(self, password):
        '''Creates a new database in memory'''
        self.keys['ITER'] = 2048

        self.new_keys(password)

        self.header[0] = '\x02\x03'  # database version
        self.header[1] = os.urandom(16)  # uuid

    def check_password(self, password):
        '''Checks if password is valid'''
        stretched_key = self._keystretch(password,
                                         self.keys['SALT'],
                                         self.keys['ITER'])
        # Don't need the password anymore, clear it out
        password = ''
        if hashlib.sha256(stretched_key).digest() != self.keys['HP']:
            return False
        else:
            return True

    def new_keys(self, password):
        '''Generates new keys'''
        self.keys['SALT'] = os.urandom(32)

        stretched_key = self._keystretch(password, self.keys['SALT'],
                                                   self.keys['ITER'])
        # Don't need the password anymore, clear it out
        password = ''
        self.keys['HP'] = hashlib.sha256(stretched_key).digest()
        self.cipher.set_key(stretched_key)
        # Don't need the stretched key anymore, clear it out
        stretched_key = ''

        b1_rand = os.urandom(16)
        b2_rand = os.urandom(16)
        b3_rand = os.urandom(16)
        b4_rand = os.urandom(16)
        self.keys['K'] = b1_rand + b2_rand
        self.keys['L'] = b3_rand + b4_rand
        self.keys['B1'] = self.cipher.encrypt(b1_rand)
        self.keys['B2'] = self.cipher.encrypt(b2_rand)
        self.keys['B3'] = self.cipher.encrypt(b3_rand)
        self.keys['B4'] = self.cipher.encrypt(b4_rand)
        self.keys['IV'] = os.urandom(16)

    def writefile(self, filename, backup=False):
        '''Writes database file'''

        # Set username
        self.header[7] = pwd.getpwuid(os.getuid())[0]
        # Remove the old deprecated username field if it exists
        if 5 in self.header:
            del self.header[5]
        # Set hostname
        self.header[8] = os.uname()[1]
        # Set timestamp
        self.header[4] = struct.pack("<I", int(time.time()))
        self.header[6] = "Pasaffe v%s" % get_version()
        # TODO: we should probably update the database version
        # string here to at least what we use in new_db()

        # Create backup if requested
        if backup == True and os.path.exists(filename):
            shutil.copy(filename, filename + ".bak")

        basedir = os.path.dirname(filename)

        try:
            self.dbfile = tempfile.NamedTemporaryFile(dir=basedir,
                                                      delete=False)
        except Exception:
            raise RuntimeError("Could not create %s. Aborting." % filename)

        tempname = self.dbfile.name

        self.dbfile.write("PWS3")
        self._writekeys()
        self._writeheader()
        self._writerecords()
        self._writeeofblock()
        self._writehmac()
        self.dbfile.close()
        self.dbfile = None

        # TODO: add sanity check
        # At this point, intention was to reopen the temp file and see
        # if we can parse it before copying it over as a sanity check,
        # but we don't have the password anymore

        # Copy it over the real database
        shutil.copy(tempname, filename)
        os.unlink(tempname)

    def get_database_version_string(self):
        '''Returns a string of the current database version'''
        return '%s.%s' % (self.header[0][1].encode('hex'),
                          self.header[0][0].encode('hex'))

    def get_saved_name(self):
        '''Returns the username of the last save'''
        return self.header.get(7)

    def get_saved_host(self):
        '''Returns the hostname of the last save'''
        return self.header.get(8)

    def get_saved_application(self):
        '''Returns the application of the last save'''
        return self.header.get(6)

    def get_saved_date_string(self):
        '''Returns a string of the date of the last save'''
        if 4 in self.header:
            return time.strftime("%a, %d %b %Y %H:%M:%S",
                                 time.localtime(struct.unpack("<I",
                                 self.header[4])[0]))
        else:
            return None

    def get_folder_list(self, uuid):
        '''Returns a list of folders an entry belongs to'''
        if uuid not in self.records:
            return None

        if 2 not in self.records[uuid]:
            return None

        # We need to split into folders using the "." character, but not
        # if it is escaped with a \
        folders = []
        index = 0
        while index < len(self.records[uuid][2]):
            print "index = %s" % index
            location = self.records[uuid][2].find(".", index)
            print "location is %s" % location

            if self.records[uuid][2][location-1] == "\\":
                break
            if location == -1:
                break
            folders.append(self.records[uuid][2][index:location].replace("\\",''))
            index = location + 1

        folders.append(self.records[uuid][2][index:len(self.records[uuid][2])].replace('\\',''))
        return folders

    def update_folder_list(self, old_list, new_list):
        '''Updates a folder name in all entries'''
        old_field = self._folder_list_to_field(old_list)
        new_field = self._folder_list_to_field(new_list)

        for uuid in self.records:
            if 2 not in self.records[uuid]:
                continue

            if self.records[uuid][2] == old_field:
                self.records[uuid][2] = new_field
            elif self.records[uuid][2].startswith(old_field + '.'):
                updated_field = self.records[uuid][2].replace(old_field, new_field, 1)
                self.records[uuid][2] = updated_field
            else:
                continue

            self.update_modification_time(uuid)

    def update_modification_time(self, uuid):
        '''Updates the modification time of an entry'''
        timestamp = struct.pack("<I", int(time.time()))
        self.records[uuid][12] = timestamp

    def update_password_time(self, uuid):
        '''Updates the password time of an entry'''
        timestamp = struct.pack("<I", int(time.time()))
        self.records[uuid][8] = timestamp

    def _folder_list_to_field(self, folder_list):
        '''Converts a folder list to a folder field'''
        field = ""
        for folder in folder_list:
            if field != "":
                field += "."
            field += folder.replace(".", "\\.")
        return field

    def new_entry(self):
        '''Creates a new entry'''
        uuid = os.urandom(16)
        uuid_hex = uuid.encode("hex")
        timestamp = struct.pack("<I", int(time.time()))
        new_entry = {1: uuid, 3: '', 4: '', 5: '', 6: '',
                     7: timestamp, 8: timestamp, 12: timestamp, 13: ''}
        self.records[uuid_hex] = new_entry

        return uuid_hex

    def _keystretch(self, password, salt, iters):
        '''Takes a password, and stretches it using iters iterations'''
        password = hashlib.sha256(password + salt).digest()
        for i in range(iters):
            password = hashlib.sha256(password).digest()
        return password

    def _readkeys(self, password):
        self.keys['SALT'] = self.dbfile.read(32)
        self.keys['ITER'] = struct.unpack("<i", self.dbfile.read(4))[0]
        # Sanity check so we don't gobble up massive amounts of ram
        if self.keys['ITER'] > 50000:
            raise RuntimeError("Too many iterations: %s. Aborting." %
                               self.keys['ITER'])
        logger.debug("Number of iters is %d" % self.keys['ITER'])
        self.keys['HP'] = self.dbfile.read(32)
        #logger.debug("hp is %s" % self.keys['HP'])
        self.keys['B1'] = self.dbfile.read(16)
        self.keys['B2'] = self.dbfile.read(16)
        self.keys['B3'] = self.dbfile.read(16)
        self.keys['B4'] = self.dbfile.read(16)
        self.keys['IV'] = self.dbfile.read(16)
        self.cipher.initCBC(self.keys['IV'])
        stretched_key = self._keystretch(password, self.keys['SALT'],
                                                   self.keys['ITER'])
        # Don't need the password anymore, clear it out
        password = ''
        #logger.debug("stretched pass is %s" % stretched_key.encode("hex"))
        if hashlib.sha256(stretched_key).digest() != self.keys['HP']:
            raise ValueError("Password supplied doesn't match database."
                             " Aborting.")

        self.cipher.set_key(stretched_key)
        # Don't need the stretched key anymore, clear it out
        stretched_key = ''
        self.keys['K'] = self.cipher.decrypt(self.keys['B1']) + \
                         self.cipher.decrypt(self.keys['B2'])
        self.keys['L'] = self.cipher.decrypt(self.keys['B3']) + \
                         self.cipher.decrypt(self.keys['B4'])
        self.hmac = hmac.new(self.keys['L'], digestmod=hashlib.sha256)
        #logger.debug("K is %s and L is %s" % (self.keys['K'].encode("hex"),
        #                                      self.keys['L'].encode("hex")))

    def _writekeys(self):
        self.dbfile.write(self.keys['SALT'])
        self.dbfile.write(struct.pack("i", self.keys['ITER']))
        self.dbfile.write(self.keys['HP'])
        self.dbfile.write(self.keys['B1'])
        self.dbfile.write(self.keys['B2'])
        self.dbfile.write(self.keys['B3'])
        self.dbfile.write(self.keys['B4'])
        self.dbfile.write(self.keys['IV'])
        self.cipher.initCBC(self.keys['IV'])
        self.hmac = hmac.new(self.keys['L'], digestmod=hashlib.sha256)

    def _readheader(self):
        self.cipher.set_key(self.keys['K'])

        while(1):
            status, field_type, field_data = self._readfield()
            if status == False:
                raise RuntimeError("Malformed file, "
                                   "was expecting more data in header")
            if field_type == 0xff:
                logger.debug("Found end field")
                break
            else:
                self.header[field_type] = field_data
                logger.debug("Found field 0x%.2x" % field_type)

    def _writeheader(self):
        self.cipher.set_key(self.keys['K'])

        for entry in self.header.keys():
            logger.debug("Writing %.2x" % entry)
            self._writefield(entry, self.header[entry])

        self._writefieldend()

    def _readrecords(self):
        self.cipher.set_key(self.keys['K'])

        record = {}

        while(1):
            status, field_type, field_data = self._readfield()
            if status == False:
                break
            if field_type == 0xff:
                logger.debug("Found end field")
                uuid = record[1].encode('hex')
                self.records[uuid] = record
                record = {}
            else:
                record[field_type] = field_data
                logger.debug("Found field 0x%.2x" % field_type)

    def _writerecords(self):
        self.cipher.set_key(self.keys['K'])

        record = {}

        for uuid in self.records:
            for field in self.records[uuid].keys():
                self._writefield(field, self.records[uuid][field])
            self._writefieldend()

    def _readfield(self):
        field_data = ''
        status, first_block = self._readblock()
        if status == False:
            return False, 0xFF, ''
        field_length = struct.unpack("<I", first_block[0:4])[0]
        field_type = struct.unpack("B", first_block[4])[0]

        logger.debug("field length is %d" % field_length)
        logger.debug("field_type is 0x%.2x" % field_type)

        # Do we need multiple blocks?
        if field_length <= self.cipher_block_size - 5:
            logger.debug("single block")
            field_data = first_block[5:5 + field_length]
        else:
            field_data = first_block[5:self.cipher_block_size]
            field_length -= self.cipher_block_size - 5
            while field_length > 0:
                logger.debug("extra block")
                status, data = self._readblock()
                if status == False:
                    raise RuntimeError("Malformed file, "
                                       "was expecting more data")
                field_data += data[0:field_length]
                field_length -= self.cipher_block_size

        logger.debug("actual data length is %d" % len(field_data))

        self.hmac.update(field_data)

        return True, field_type, field_data

    def _writefield(self, field_type, field_data):
        self.hmac.update(field_data)
        field_length = len(field_data)
        field_free_space = self.cipher_block_size - 5
        index = 0
        block = ''
        block += struct.pack("I", field_length)
        block += struct.pack("B", field_type)

        logger.debug("Writing field type %.2x, length %d" %
                     (field_type, field_length))

        while field_length >= 0:
            if field_length < field_free_space:
                logger.debug("smaller than block")
                block += field_data[index:index + field_length]
                for x in range(field_free_space - field_length):
                    block += struct.pack("B", random.randint(0, 254))
                self._writeblock(block)
                field_length = -1
                block = ''
            else:
                logger.debug("bigger than block")
                block += field_data[index:index + field_free_space]
                self._writeblock(block)
                field_length -= field_free_space
                if field_length == 0:
                    field_length = -1
                index += field_free_space
                field_free_space = self.cipher_block_size
                block = ''

    def _writefieldend(self):
        block = struct.pack("I", 0)
        block += struct.pack("B", 0xff)

        logger.debug("Writing field end")

        for x in range(self.cipher_block_size - 5):
            block += struct.pack("B", random.randint(0, 254))
        self._writeblock(block)

    def _readblock(self):
        block = self.dbfile.read(self.cipher_block_size)
        if block == 'PWS3-EOFPWS3-EOF':
            return False, block
        return True, self.cipher.decryptCBC(block)

    def _writeblock(self, block):
        logger.debug("writing block, length is %d" % len(block))
        self.dbfile.write(self.cipher.encryptCBC(block))

    def _writeeofblock(self):
        self.dbfile.write('PWS3-EOFPWS3-EOF')

    def _validatehmac(self):
        hmac = self.dbfile.read(32)
        if hmac != self.hmac.digest():
            raise RuntimeError("Malformed file, HMAC didn't match!")
        else:
            logger.debug("HMAC Matched")
            self.hmac = None

    def _writehmac(self):
        self.dbfile.write(self.hmac.digest())
        self.hmac = None
