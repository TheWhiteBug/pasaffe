#!/usr/bin/python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2013 Marc Deslauriers <marc.deslauriers@canonical.com>
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

from autopilot.testcase import AutopilotTestCase
from os.path import abspath, dirname, join
from testtools.matchers import Equals

class MainWindowTitleTests(AutopilotTestCase):

    def launch_application(self):
        """Work out the full path to the application and launch it.

        This is necessary since our test application will not be in $PATH.

        :returns: The application proxy object.

        """
        full_path = abspath(join(dirname(__file__), '..', '..', '..', '..', 'bin', 'pasaffe'))
        test_database = abspath(join(dirname(__file__), '..', '..', '..', 'databases', 'pasaffe-025.psafe3'))

        return self.launch_test_application(full_path, '-f', test_database, app_type='gtk')

    def test_main_window_title_string(self):
        """The main window title must be 'Hello World'."""
        app_root = self.launch_application()
        main_window = app_root.select_single('PasaffeWindow')
        self.assertThat(main_window.title, Equals("Pasaffe"))

