# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2011-2012 Marc Deslauriers <marc.deslauriers@canonical.com>
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

from gi.repository import Gio # pylint: disable=E0611

import gettext
from gettext import gettext as _
gettext.textdomain('pasaffe')

import logging
logger = logging.getLogger('pasaffe')

from pasaffe_lib.PreferencesDialog import PreferencesDialog

class PreferencesPasaffeDialog(PreferencesDialog):
    __gtype_name__ = "PreferencesPasaffeDialog"

    def finish_initializing(self, builder): # pylint: disable=E1002
        """Set up the preferences dialog"""
        super(PreferencesPasaffeDialog, self).finish_initializing(builder)

        # Bind each preference widget to gsettings
        settings = Gio.Settings("apps.pasaffe")
        widget = self.builder.get_object('visible-secrets')
        settings.bind("visible-secrets", widget, "active", Gio.SettingsBindFlags.DEFAULT)
        widget = self.builder.get_object('only-passwords-are-secret')
        settings.bind("only-passwords-are-secret", widget, "active", Gio.SettingsBindFlags.DEFAULT)
        widget = self.builder.get_object('lock-on-idle')
        settings.bind("lock-on-idle", widget, "active", Gio.SettingsBindFlags.DEFAULT)
        widget = self.builder.get_object('idle-timeout')
        settings.bind("idle-timeout", widget, "value", Gio.SettingsBindFlags.DEFAULT)
        widget = self.builder.get_object('auto-save')
        settings.bind("auto-save", widget, "active", Gio.SettingsBindFlags.DEFAULT)
        widget = self.builder.get_object('password-length')
        settings.bind("password-length", widget, "value", Gio.SettingsBindFlags.DEFAULT)

        # Code for other initialization actions should be added here.
