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

import sys, struct, hashlib, operator, hmac, random, os
import pytwofish

class PassSafeFile:

    keys = {}
    header = {}
    records = []
    cipher = None
    cipher_cbc = ''
    cipher_block_size = 0
    hmac = None

    def __init__(self, filename=None, password=None, cipher='Twofish'):
        '''Reads a Password Safe v3 file'''

        if cipher == 'Twofish':
            self.cipher = pytwofish.Twofish()
            self.cipher_block_size = self.cipher.get_block_size()
        else:
            raise ValueError("Sorry, we don't support %s yet." % cipher)

        if filename != None:
            self.readfile(filename, password)

    def readfile(self, filename, password):
        '''Parses database file'''
        try:
            dbfile = open(filename, 'r')
        except Exception:
            raise RuntimeError("Could not open %s. Aborting." % filename)

        tag = dbfile.read(4)
        if tag != "PWS3":
            raise RuntimeError("File %s is not a password safe database. Aborting." % filename)

        self._readkeys(dbfile, password)
        # Don't need the password anymore, clear it out
        password = ''
        self._readheader(dbfile)
        self._readrecords(dbfile)
        self._validatehmac(dbfile)
        dbfile.close()

    def new_db(self, password):
        '''Creates a new database in memory'''
        self.keys['SALT'] = os.urandom(32)
        self.keys['ITER'] = 2048

        stretched_key = self._keystretch(password, self.keys['SALT'], self.keys['ITER'])
        self.keys['HP'] = hashlib.sha256(stretched_key).digest()

        b1_rand = os.urandom(16)
        b2_rand = os.urandom(16)
        b3_rand = os.urandom(16)
        b4_rand = os.urandom(16)
        self.keys['K'] = b1_rand + b2_rand
        self.keys['L'] = b3_rand + b4_rand
        self.cipher.set_key(stretched_key)
        self.keys['B1'] = self.cipher.encrypt(b1_rand)
        self.keys['B2'] = self.cipher.encrypt(b2_rand)
        self.keys['B3'] = self.cipher.encrypt(b3_rand)
        self.keys['B4'] = self.cipher.encrypt(b4_rand)

        self.keys['IV'] = os.urandom(16)

        self.header[0] = '\x00\x03' # database version
        self.header[1] = os.urandom(16) # uuid

    def writefile(self, filename, password):
        '''Writes database file'''
        try:
            dbfile = open(filename, 'wb')
        except Exception:
            raise RuntimeError("Could not create %s. Aborting." % filename)

        dbfile.write("PWS3")
        self._writekeys(dbfile, password)
        # Don't need the password anymore, clear it out
        password = ''
        self._writeheader(dbfile)
        self._writerecords(dbfile)
        self._writeeofblock(dbfile)
        self._writehmac(dbfile)
        dbfile.close()

    def _keystretch(self, password, salt, iters):
        '''Takes a password, and stretches it using iters iterations'''
        password = hashlib.sha256(password + salt).digest()
        for i in range(iters):
            password = hashlib.sha256(password).digest()
        return password

    def _xor(self, string, pw):
        result = ''
        for k in xrange(len(string)):
            result += chr(operator.xor(ord(string[k]), ord(pw[k])))
        return result

    def _readkeys(self, dbfile, password):
        self.keys['SALT'] = dbfile.read(32)
        self.keys['ITER'] = struct.unpack("<i", dbfile.read(4))[0]
        # Sanity check so we don't gobble up massive amounts of ram
        if self.keys['ITER'] > 50000:
            raise RuntimeError("Too many iterations: %s. Aborting." % self.keys['ITER'])
        #print "Number of iters is %d" % self.keys['ITER']
        self.keys['HP'] = dbfile.read(32)
        #print "hp is %s" % self.keys['HP']
        self.keys['B1'] = dbfile.read(16)
        self.keys['B2'] = dbfile.read(16)
        self.keys['B3'] = dbfile.read(16)
        self.keys['B4'] = dbfile.read(16)
        self.keys['IV'] = dbfile.read(16)
        self.cipher_cbc = self.keys['IV']
        stretched_key = self._keystretch(password, self.keys['SALT'], self.keys['ITER'])
        #print "stretched pass is %s" % stretched_key.encode("hex")
        if hashlib.sha256(stretched_key).digest() != self.keys['HP']:
            raise ValueError("Password supplied doesn't match database. Aborting.")

        self.cipher.set_key(stretched_key)
        self.keys['K'] = self.cipher.decrypt(self.keys['B1']) + self.cipher.decrypt(self.keys['B2'])
        self.keys['L'] = self.cipher.decrypt(self.keys['B3']) + self.cipher.decrypt(self.keys['B4'])
        self.hmac = hmac.new(self.keys['L'], digestmod=hashlib.sha256)
        #print "K is %s and L is %s" % (self.keys['K'].encode("hex"), self.keys['L'].encode("hex"))

    def _writekeys(self, dbfile, password):
        dbfile.write(self.keys['SALT'])
        dbfile.write(struct.pack("i", self.keys['ITER']))
        stretched_key = self._keystretch(password, self.keys['SALT'], self.keys['ITER'])
        # write HP
        dbfile.write(hashlib.sha256(stretched_key).digest())
        dbfile.write(self.keys['B1'])
        dbfile.write(self.keys['B2'])
        dbfile.write(self.keys['B3'])
        dbfile.write(self.keys['B4'])
        dbfile.write(self.keys['IV'])
        self.cipher_cbc = self.keys['IV']
        self.cipher.set_key(stretched_key)
        self.hmac = hmac.new(self.keys['L'], digestmod=hashlib.sha256)

    def _readheader(self, dbfile):
        self.cipher.set_key(self.keys['K'])

        while(1):
            status, field_type, field_data = self._readfield(dbfile)
            if status == False:
                raise RuntimeError("Malformed file, was expecting more data in header")
            if field_type == 0xff:
                #print "_readheader: Found end field"
                break
            else:
                self.header[field_type] = field_data
                #print "_readheader: Found field 0x%.2x with data: %s" % (field_type, field_data)

    def _writeheader(self, dbfile):
        self.cipher.set_key(self.keys['K'])

        for entry in self.header.keys():
            #print "_writeheader: Writing %.2x - %s" % (entry, self.header[entry])
            self._writefield(dbfile, entry, self.header[entry])

        self._writefieldend(dbfile)

    def _readrecords(self, dbfile):
        self.cipher.set_key(self.keys['K'])

        record = {}

        while(1):
            status, field_type, field_data = self._readfield(dbfile)
            if status == False:
                break
            if field_type == 0xff:
                #print "_readrecords: Found end field"
                self.records.append(record)
                record = {}
            else:
                record[field_type] = field_data
                #print "_readrecords: Found field 0x%.2x with data: %s" % (field_type, field_data)

    def _writerecords(self, dbfile):
        self.cipher.set_key(self.keys['K'])

        record = {}

        for record in self.records:
            for field in record.keys():
                self._writefield(dbfile, field, record[field])
            self._writefieldend(dbfile)

    def _readfield(self, dbfile):
        field_data = ''
        status, first_block = self._readblock(dbfile)
        if status == False:
            return False, 0xFF, ''
        field_length = struct.unpack("<I", first_block[0:4])[0]
        field_type = struct.unpack("B", first_block[4])[0]

        #print "_readfield: field length is %d" % field_length
        #print "_readfield: field_type is 0x%.2x" % field_type

        # Do we need multiple blocks?
        if field_length <= self.cipher_block_size - 5:
            #print "_readfield: single block"
            field_data = first_block[5:5 + field_length]
        else:
            field_data = first_block[5:self.cipher_block_size]
            field_length -= self.cipher_block_size - 5
            while field_length > 0:
                #print "_readfield: extra block"
                status, data = self._readblock(dbfile)
                if status == False:
                    raise RuntimeError("Malformed file, was expecting more data")
                field_data += data[0:field_length]
                field_length -= self.cipher_block_size

        #print "_readfield: actual data length is %d" % len(field_data)

        self.hmac.update(field_data)

        return True, field_type, field_data

    def _writefield(self, dbfile, field_type, field_data):
        self.hmac.update(field_data)
        field_length = len(field_data)
        field_free_space = self.cipher_block_size - 5
        index = 0
        block = ''
        block += struct.pack("I", field_length)
        block += struct.pack("B", field_type)

        #print "_writefield: Writing field type %.2x, data %s, length %d" % (field_type, field_data, field_length)

        while field_length >= 0:
            if field_length < field_free_space:
                #print "_writefield: smaller than block"
                block += field_data[index:index+field_length]
                for x in range(field_free_space - field_length):
                    block += struct.pack("B", random.randint(0, 254))
                self._writeblock(dbfile, block)
                field_length = -1
                block = ''
            else:
                #print "_writefield: bigger than block"
                block += field_data[index:field_free_space]
                self._writeblock(dbfile, block)
                field_length -= field_free_space
                if field_length == 0:
                    field_length = -1
                index += field_free_space
                field_free_space = self.cipher_block_size
                block = ''

    def _writefieldend(self, dbfile):
        block = struct.pack("I", 0)
        block += struct.pack("B", 0xff)

        #print "_writefieldend: Writing field end"

        for x in range(self.cipher_block_size - 5):
            block += struct.pack("B", random.randint(0, 254))
        self._writeblock(dbfile, block)

    def _readblock(self, dbfile):
        block = dbfile.read(self.cipher_block_size)
        if block == 'PWS3-EOFPWS3-EOF':
            return False, block
        decrypted_block = self._xor(self.cipher.decrypt(block), self.cipher_cbc)
        self.cipher_cbc = block
        return True, decrypted_block

    def _writeblock(self, dbfile, block):
        #print "_writeblock: writing %s, length is %d" % (block, len(block))
        self.cipher_cbc = self.cipher.encrypt(self._xor(block, self.cipher_cbc))
        dbfile.write(self.cipher_cbc)

    def _writeeofblock(self, dbfile):
        dbfile.write('PWS3-EOFPWS3-EOF')

    def _validatehmac(self, dbfile):
        hmac = dbfile.read(32)
        if hmac != self.hmac.digest():
            raise RuntimeError("Malformed file, HMAC didn't match!")
        else:
            #print "_validatehmac: HMAC Matched!"
            self.hmac = None

    def _writehmac(self, dbfile):
        dbfile.write(self.hmac.digest())
        self.hmac = None
