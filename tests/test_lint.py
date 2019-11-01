#!/usr/bin/python3
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

import unittest
import subprocess


class TestPylint(unittest.TestCase):
    def test_project_errors_only(self):
        '''run pylint in error only mode

        your code may well work even with pylint errors
        but have some unusual code'''
        subprocess.call(["pylint", '-E', 'pasaffe'])


if __name__ == '__main__':
    'you will get better results with nosetests'
    unittest.main()
