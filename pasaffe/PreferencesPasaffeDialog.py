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

from gi.repository import Gio
import logging
from pasaffe_lib.PreferencesDialog import PreferencesDialog

logger = logging.getLogger('pasaffe')


class PreferencesPasaffeDialog(PreferencesDialog):
    __gtype_name__ = "PreferencesPasaffeDialog"

    def finish_initializing(self, builder):
        """Set up the preferences dialog"""
        super(PreferencesPasaffeDialog, self).finish_initializing(builder)

        # Bind each preference widget to gsettings
        settings = Gio.Settings.new("net.launchpad.pasaffe")
        widget = self.builder.get_object('visible-secrets')
        settings.bind("visible-secrets", widget, "active",
                      Gio.SettingsBindFlags.DEFAULT)
        widget = self.builder.get_object('only-passwords-are-secret')
        settings.bind("only-passwords-are-secret", widget, "active",
                      Gio.SettingsBindFlags.DEFAULT)
        widget = self.builder.get_object('lock-on-idle')
        settings.bind("lock-on-idle", widget, "active",
                      Gio.SettingsBindFlags.DEFAULT)
        widget = self.builder.get_object('idle-timeout')
        settings.bind("idle-timeout", widget, "value",
                      Gio.SettingsBindFlags.DEFAULT)
        widget = self.builder.get_object('auto-save')
        settings.bind("auto-save", widget, "active",
                      Gio.SettingsBindFlags.DEFAULT)
        widget = self.builder.get_object('password-length')
        settings.bind("password-length", widget, "value",
                      Gio.SettingsBindFlags.DEFAULT)
        widget = self.builder.get_object('tree-expansion')
        settings.bind("tree-expansion", widget, "active-id",
                      Gio.SettingsBindFlags.DEFAULT)
        widget = self.builder.get_object('double-click')
        settings.bind("double-click", widget, "active-id",
                      Gio.SettingsBindFlags.DEFAULT)
        widget = self.builder.get_object('display-usernames')
        settings.bind("display-usernames", widget, "active",
                      Gio.SettingsBindFlags.DEFAULT)

        # Code for other initialization actions should be added here.
