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

import pytwofish
import operator


class TwofishCBC(pytwofish.Twofish):

    cbc_iv = "\0" * 16

    def _xor(self, string, pw):
        result = ''
        for k in xrange(len(string)):
            result += chr(operator.xor(ord(string[k]), ord(pw[k])))
        return result

    def initCBC(self, iv="\0" * 16):
        """Sets the CBC mode initialization vector."""
        self.cbc_iv = iv

    def encryptCBC(self, block):
        """Encrypts using CBC mode"""
        self.cbc_iv = self.encrypt(self._xor(block, self.cbc_iv))
        return self.cbc_iv

    def decryptCBC(self, block):
        decrypted_block = self._xor(self.decrypt(block), self.cbc_iv)
        self.cbc_iv = block
        return decrypted_block
