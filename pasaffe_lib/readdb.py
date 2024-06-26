# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2011-2024 Marc Deslauriers <marc.deslauriers@canonical.com>
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
import hashlib
import hmac
import random
import re
import os
import time
import tempfile
import shutil
if os.name == "posix":
    import pwd
elif os.name == "nt":
    import getpass
# import pwd
from binascii import hexlify  # noqa: E402
from unidecode import unidecode  # noqa: E402
from pasaffe_lib.helpers import PathEntry  # noqa: E402

from . import pytwofishcbc  # noqa: E402
import logging  # noqa: E402
logger = logging.getLogger('pasaffe_lib')
from . pasaffeconfig import get_version  # noqa: E402


class PassSafeFile:

    def __init__(self, filename=None, password=None, req_cipher='Twofish',
                 fixup=True):
        '''Reads a Password Safe v3 file'''

        self.keys = {}
        self.header = {}
        self.records = {}
        self.cipher = None
        self.cipher_block_size = 0
        self.hmac = None
        self.dbfile = None
        self.empty_folders = []

        self.find_results = []
        self.find_results_index = None
        self.find_value = ""

        # These fields need converting between strings and bytes
        self.header_text = [0x03, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0a, 0x11]
        self.record_text = [0x02, 0x03, 0x04, 0x05, 0x06, 0x0d, 0x14]

        # Use version 0x030B, since we support saving empty folders
        self.db_version = b'\x0B\x03'

        if req_cipher == 'Twofish':
            self.cipher = pytwofishcbc.TwofishCBC()
            self.cipher_block_size = self.cipher.get_block_size()
        else:
            raise ValueError("Sorry, we don't support %s yet." % req_cipher)

        if filename is not None:
            self.readfile(filename, password, fixup=fixup)

    def readfile(self, filename, password, fixup=True):
        '''Parses database file'''
        logger.debug('Opening database: %s' % filename)
        try:
            self.dbfile = open(filename, 'rb')
        except Exception:
            raise RuntimeError("Could not open %s. Aborting." % filename)

        tag = self.dbfile.read(4)
        if tag != b"PWS3":
            raise RuntimeError("File %s is not a password safe database."
                               " Aborting." % filename)

        self._readkeys(password)
        self._readheader()
        self._readrecords()
        self._validatehmac()
        self.dbfile.close()
        self.dbfile = None

        if fixup:
            self._postread_fixup()

        # Now that we've read the file, but before we get rid of the
        # password, generate new keys for our next save
        self.new_keys(password)

        # Don't need the password anymore, clear it out
        password = ''

    def new_db(self, password):
        '''Creates a new database in memory'''
        self.keys['ITER'] = 2048

        self.new_keys(password)

        self.header[0] = self.db_version
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
        if os.name == "posix":
            self.header[7] = pwd.getpwuid(os.getuid())[0]
        elif os.name == "nt":
            self.header[7] = getpass.getuser()
        # Remove the old deprecated username field if it exists
        if 5 in self.header:
            del self.header[5]
        # Set hostname
        self.header[8] = os.uname()[1]
        # Set timestamp
        self.header[4] = struct.pack("<I", int(time.time()))
        self.header[6] = "Pasaffe v%s" % get_version()

        # Update the database version if it's older than what we support.
        # Do major version first
        if self.header[0][1] < self.db_version[1]:
            self.header[0] = self.db_version
        # Now check minor version if major version is same
        elif self.header[0][1] == self.db_version[1]:
            if self.header[0][0] < self.db_version[0]:
                self.header[0] = self.db_version

        # Create backup if requested
        if backup is True and os.path.exists(filename):
            shutil.copy(filename, filename + ".bak")

        basedir = os.path.dirname(filename)

        try:
            self.dbfile = tempfile.NamedTemporaryFile(dir=basedir,
                                                      delete=False)
        except Exception:
            raise RuntimeError("Could not create %s. Aborting." % filename)

        tempname = self.dbfile.name

        self.dbfile.write(b"PWS3")
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
        return '%s.%s' % (hexlify(self.header[0][1:2]).decode('utf-8'),
                          hexlify(self.header[0][0:1]).decode('utf-8'))

    def get_saved_name(self):
        '''Returns the username of the last save'''
        return self.header.get(7)

    def get_saved_host(self):
        '''Returns the hostname of the last save'''
        return self.header.get(8)

    def get_saved_application(self):
        '''Returns the application of the last save'''
        return self.header.get(6)

    def get_saved_date_string(self, localtime=True):
        '''Returns a string of the date of the last save'''
        if 4 in self.header:
            unpacked_time = struct.unpack("<I", self.header[4])[0]
            if localtime:
                converted_time = time.localtime(unpacked_time)
            else:
                converted_time = time.gmtime(unpacked_time)
            return time.strftime("%a, %d %b %Y %H:%M:%S", converted_time)
        else:
            return None

    def get_tree_status(self):
        '''Returns the tree display status'''
        # Tree display status is implementation specific
        if self.header.get(6, "").startswith("Pasaffe") and 3 in self.header:
            return self.header.get(3)
        else:
            return None

    def set_tree_status(self, status):
        '''Sets the tree display status'''
        if status is None:
            if 3 in self.header:
                del self.header[3]
        else:
            self.header[3] = status

    def get_folder_list(self, uuid):
        '''Returns a list of folders an entry belongs to'''
        if uuid not in self.records:
            return []

        if 2 not in self.records[uuid]:
            return []

        return (self._field_to_folder_list(self.records[uuid][2]))

    def update_folder_list(self, uuid, folder):
        '''Updates an entry folder list'''
        if uuid not in self.records:
            return

        self.records[uuid][2] = self._folder_list_to_field(folder)

        # If the record is empty, just delete it
        if self.records[uuid][2] == "":
            del self.records[uuid][2]

    def get_empty_folders(self):
        '''Returns the empty folders list'''
        folders = []

        for folder in self.empty_folders:
            folders.append(self._field_to_folder_list(folder))

        logger.debug("returning %s" % folders)
        return folders

    def get_all_folders(self):
        '''Returns a list of all the folders'''

        # First, get the empty folders
        folders = self.get_empty_folders()

        # Now, do the records
        for uuid in self.records:
            if 2 not in self.records[uuid]:
                continue

            folder = self._field_to_folder_list(self.records[uuid][2])
            if folder not in folders:
                folders.append(folder)

        return folders

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

    def remove_empty_folder(self, folder):
        '''Removes a folder from the empty folders list'''
        field = self._folder_list_to_field(folder)
        if field in self.empty_folders:
            logger.debug("removing %s" % field)
            self.empty_folders.remove(field)

    def rename_folder_list(self, old_list, new_list):
        '''Renamed a folder name in all entries'''
        old_field = self._folder_list_to_field(old_list)
        new_field = self._folder_list_to_field(new_list)

        # Do the records first
        for uuid in self.records:
            if 2 not in self.records[uuid]:
                continue

            if self.records[uuid][2] == old_field:
                self.records[uuid][2] = new_field
            elif self.records[uuid][2].startswith(old_field + '.'):
                updated_field = self.records[uuid][2].replace(
                    old_field, new_field, 1)
                self.records[uuid][2] = updated_field
            else:
                continue

            self.update_modification_time(uuid)

        # Now do the empty folders
        for empty_folder in self.empty_folders[:]:
            if empty_folder == old_field:
                logger.debug("renaming %s to %s" % (empty_folder, new_field))
                self.empty_folders.remove(empty_folder)
                self.empty_folders.append(new_field)
            elif empty_folder.startswith(old_field + '.'):
                updated_field = empty_folder.replace(old_field, new_field, 1)
                logger.debug("renaming %s to %s" % (empty_folder,
                                                    updated_field))
                self.empty_folders.remove(empty_folder)
                self.empty_folders.append(updated_field)

    def delete_entry(self, uuid):
        '''Deletes an entry'''
        del self.records[uuid]

    def delete_folder(self, folder):
        '''Deletes a folder and all contents'''

        if folder is None or folder == []:
            return

        field = self._folder_list_to_field(folder)

        # Do the records first
        for uuid in list(self.records.keys()):
            if 2 not in self.records[uuid]:
                continue
            if self.records[uuid][2] == field:
                self.delete_entry(uuid)
            elif self.records[uuid][2].startswith(field + '.'):
                self.delete_entry(uuid)

        # Now do the empty folders
        for empty_folder in self.empty_folders[:]:
            if empty_folder == field:
                logger.debug("removing folder '%s'" % empty_folder)
                self.empty_folders.remove(empty_folder)
            elif empty_folder.startswith(field + '.'):
                logger.debug("removing folder '%s'" % empty_folder)
                self.empty_folders.remove(empty_folder)

        # If the parent folder has no contents,
        # add it to empty folders list
        parent = folder[:-1]
        if parent == []:
            return
        parent_field = self._folder_list_to_field(parent)

        for uuid in self.records:
            if 2 not in self.records[uuid]:
                continue
            if self.records[uuid][2] == parent_field:
                return

        self.add_empty_folder(parent)

    def update_modification_time(self, uuid):
        '''Updates the modification time of an entry'''
        timestamp = struct.pack("<I", int(time.time()))
        self.records[uuid][12] = timestamp

    def get_title(self, uuid):
        '''Returns the entry title'''
        return self.records[uuid].get(3)

    def get_username(self, uuid):
        '''Returns the entry username'''
        return self.records[uuid].get(4)

    def get_notes(self, uuid):
        '''Returns the entry notes'''
        return self.records[uuid].get(5)

    def get_password(self, uuid):
        '''Returns the entry password'''
        return self.records[uuid].get(6)

    def get_url(self, uuid):
        '''Returns the entry URL'''
        return self.records[uuid].get(13)

    def get_email(self, uuid):
        '''Returns the entry email'''
        return self.records[uuid].get(20)

    def get_modification_time(self, uuid, localtime=True):
        '''Returns a string of the entry modification time'''
        return self.get_time(uuid, 12, localtime)

    def update_password_time(self, uuid):
        '''Updates the password time of an entry'''
        timestamp = struct.pack("<I", int(time.time()))
        self.records[uuid][8] = timestamp

    def get_password_time(self, uuid, localtime=True):
        '''Returns a string of the password modification time'''
        return self.get_time(uuid, 8, localtime)

    def get_creation_time(self, uuid, localtime=True):
        '''Returns a string of the creation time'''
        return self.get_time(uuid, 7, localtime)

    def get_time(self, uuid, entry, localtime=True):
        '''Returns a string of time'''
        if entry in self.records[uuid]:
            unpacked_time = struct.unpack("<I", self.records[uuid][entry])[0]
            if localtime:
                converted_time = time.localtime(unpacked_time)
            else:
                converted_time = time.gmtime(unpacked_time)
            return time.strftime("%a, %d %b %Y %H:%M:%S", converted_time)
        else:
            return None

    def _folder_list_to_field(self, folder_list):
        '''Converts a folder list to a folder field'''
        field = ""

        if folder_list is None:
            return field

        have_folders = False
        for folder in folder_list:
            if have_folders is True:
                field += "."
            field += folder.replace(".", "\\.")
            have_folders = True
        return field

    def _field_to_folder_list(self, field):
        '''Converts a folder field to a folder list'''

        # We need to split into folders using the "." character, but not
        # if it is escaped with a \
        folders = []

        if field == "":
            return folders

        index = 0
        location = 0

        while index < len(field):

            if field[index] == ".":
                folders.append("")
                location += 1
                index += 1
                continue

            location = field.find(".", location + 1)

            if location == -1:
                break

            if field[location - 1] == "\\":
                continue

            folders.append(field[index:location].replace("\\", ''))
            index = location + 1

        folders.append(field[index:len(field)].replace('\\', ''))
        return folders

    def new_entry(self):
        '''Creates a new entry'''
        uuid = os.urandom(16)
        uuid_hex = hexlify(uuid).decode('utf-8')
        timestamp = struct.pack("<I", int(time.time()))
        new_entry = {1: uuid, 3: '', 4: '', 5: '', 6: '',
                     7: timestamp, 8: timestamp, 12: timestamp, 13: '',
                     20: ''}
        self.records[uuid_hex] = new_entry

        return uuid_hex

    def _keystretch(self, password, salt, iters):
        '''Takes a password, and stretches it using iters iterations'''
        password = hashlib.sha256(password.encode('utf-8') + salt).digest()
        for i in range(iters):
            password = hashlib.sha256(password).digest()
        return password

    def _readkeys(self, password):
        self.keys['SALT'] = self.dbfile.read(32)
        self.keys['ITER'] = struct.unpack("<i", self.dbfile.read(4))[0]
        # Sanity check so we don't gobble up massive amounts of ram
        if self.keys['ITER'] > 100000:
            raise RuntimeError("Too many iterations: %s. Aborting." %
                               self.keys['ITER'])
        logger.debug("Number of iters is %d" % self.keys['ITER'])
        self.keys['HP'] = self.dbfile.read(32)
        # logger.debug("hp is %s" % self.keys['HP'])
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
        # logger.debug("stretched pass is %s" % hexlify(stretched_key))
        if hashlib.sha256(stretched_key).digest() != self.keys['HP']:
            raise ValueError("Password supplied doesn't match database."
                             " Aborting.")

        self.cipher.set_key(stretched_key)
        # Don't need the stretched key anymore, clear it out
        stretched_key = b''
        self.keys['K'] = self.cipher.decrypt(self.keys['B1']) + \
            self.cipher.decrypt(self.keys['B2'])
        self.keys['L'] = self.cipher.decrypt(self.keys['B3']) + \
            self.cipher.decrypt(self.keys['B4'])
        self.hmac = hmac.new(self.keys['L'], digestmod=hashlib.sha256)
        # logger.debug("K is %s and L is %s" % (hexlify(self.keys['K']),
        #                                       hexlify(self.keys['L']))

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
            if status is False:
                raise RuntimeError("Malformed file, "
                                   "was expecting more data in header")

            # Convert from bytes to strings
            if field_type in self.header_text:
                field_data = field_data.decode('utf-8')

            if field_type == 0xff:
                logger.debug("Found end field")
                break
            elif field_type == 0x11:
                # Empty group fields can appear more than once
                # Store them in their own variable
                self.empty_folders.append(field_data)
                logger.debug("found empty folder: %s" % field_data)
            else:
                self.header[field_type] = field_data
                logger.debug("Found field 0x%.2x" % field_type)

    def _writeheader(self):
        self.cipher.set_key(self.keys['K'])

        # v3.30 of the spec says the version type needs to be the
        # first field in the header. Handle it first.
        logger.debug("Writing Version Type field")
        self._writefield(0x00, self.header[0x00])

        for entry in list(self.header.keys()):
            # Skip Version Type, we've already handled it
            if entry == 0x00:
                continue

            # Convert from strings to bytes
            if entry in self.header_text:
                value = self.header[entry].encode('utf-8')
            else:
                value = self.header[entry]

            logger.debug("Writing %.2x" % entry)
            self._writefield(entry, value)

        # Now handle empty folders
        logger.debug("Writing empty folders")
        for folder in self.empty_folders:
            logger.debug("writing empty folder: %s" % folder)
            self._writefield(0x11, folder.encode('utf-8'))

        self._writefieldend()

    def _readrecords(self):
        self.cipher.set_key(self.keys['K'])

        record = {}

        while(1):
            status, field_type, field_data = self._readfield()
            if status is False:
                break
            if field_type == 0xff:
                logger.debug("Found end field")
                uuid = hexlify(record[1]).decode('utf-8')
                self.records[uuid] = record
                record = {}
            else:

                # Convert from bytes to strings
                if field_type in self.record_text:
                    field_data = field_data.decode('utf-8')

                record[field_type] = field_data
                logger.debug("Found field 0x%.2x" % field_type)

    def _writerecords(self):
        self.cipher.set_key(self.keys['K'])

        for uuid in self.records:
            for field in list(self.records[uuid].keys()):

                # Fix up some of the fields
                fixed_value = self._presave_fixup(uuid, field)

                # Convert from strings to bytes
                if field in self.record_text:
                    value = fixed_value.encode('utf-8')
                else:
                    value = fixed_value

                self._writefield(field, value)
            self._writefieldend()

    def _readfield(self):
        field_data = b''
        status, first_block = self._readblock()
        if status is False:
            return False, 0xFF, b''
        field_length = struct.unpack("<I", first_block[0:4])[0]
        field_type = struct.unpack("B", first_block[4:5])[0]

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
                if status is False:
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
        block = b''
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
                block = b''
            else:
                logger.debug("bigger than block")
                block += field_data[index:index + field_free_space]
                self._writeblock(block)
                field_length -= field_free_space
                if field_length == 0:
                    field_length = -1
                index += field_free_space
                field_free_space = self.cipher_block_size
                block = b''

    def _writefieldend(self):
        block = struct.pack("I", 0)
        block += struct.pack("B", 0xff)

        logger.debug("Writing field end")

        for x in range(self.cipher_block_size - 5):
            block += struct.pack("B", random.randint(0, 254))
        self._writeblock(block)

    def _readblock(self):
        block = self.dbfile.read(self.cipher_block_size)
        if block == b'PWS3-EOFPWS3-EOF':
            return False, block
        return True, self.cipher.decryptCBC(block)

    def _writeblock(self, block):
        logger.debug("writing block, length is %d" % len(block))
        self.dbfile.write(self.cipher.encryptCBC(block))

    def _writeeofblock(self):
        self.dbfile.write(b'PWS3-EOFPWS3-EOF')

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

    def _postread_fixup(self):
        '''Performs some cleanup after reading certain databases'''

        for uuid in self.records:
            # Some apps don't create username fields, so let's default
            # to what the real Password Safe does and fix it up to be a
            # field with an empty string
            if 4 not in self.records[uuid]:
                self.records[uuid][4] = ''

            # Do basically the same with password fields
            if 6 not in self.records[uuid]:
                self.records[uuid][6] = ''

            # And the same with title fields
            if 3 not in self.records[uuid]:
                self.records[uuid][3] = ''

            # Most apps use CRLF line terminators. Convert them to LF
            # when opening in Pasaffe, we'll convert them back to CRLF
            # before saving
            if 5 in self.records[uuid]:
                self.records[uuid][5] = self.records[uuid][5].replace(
                    "\r\n", "\n")

    def _presave_fixup(self, uuid, field):
        '''Performs some cleanup before saving certain databases'''

        if field == 5:
            # Most apps use CRLF line terminators. Convert LF to CRLF
            # before saving
            return self.records[uuid][5].replace("\n", "\r\n")
        else:
            return self.records[uuid][field]

    def update_find_results(self, find, force=False):

        if find == "":
            self.find_results = []
            self.find_results_index = None
            self.find_value = ""
            return

        if find == self.find_value and force is False:
            return

        find_ascii = unidecode(find)
        if find_ascii != find:
            pat = re.compile(find + "|" + find_ascii, re.IGNORECASE)
        else:
            pat = re.compile(find, re.IGNORECASE)

        record_list = (2, 3, 4, 5, 6, 13, 20, 22)
        results = []

        for uuid in self.records:
            found = False
            for record_type in record_list:
                if record_type in self.records[uuid]:
                    try:
                        if pat.search(
                                self.records[uuid].get(record_type)):
                            found = True
                            break
                        if pat.search(unidecode(
                                self.records[uuid].get(record_type))):
                            found = True
                            break
                    except:
                        pass

            if found is True:
                entry = PathEntry(
                    self.records[uuid][3],
                    uuid,
                    self.get_folder_list(uuid))
                results.append(entry)

        self.find_results = sorted(results)
        self.find_results_index = None
        self.find_value = find

    def get_next_find_result(self, backwards=False):

        if len(self.find_results) == 0:
            return None

        if self.find_results_index is None:
            self.find_results_index = 0
        elif backwards is False:
            self.find_results_index += 1
            if self.find_results_index == len(self.find_results):
                self.find_results_index = 0
        else:
            if self.find_results_index == 0:
                self.find_results_index = len(self.find_results) - 1
            else:
                self.find_results_index -= 1

        return self.find_results[self.find_results_index].uuid
