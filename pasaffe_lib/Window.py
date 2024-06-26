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

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, Gtk  # noqa: E402
import logging  # noqa: E402
logger = logging.getLogger('pasaffe_lib')

from . helpers import get_help_uri  # noqa: E402
from . helpersgui import get_builder, show_uri  # noqa: E402


# This class is meant to be subclassed by PasaffeWindow.  It provides
# common functions and some boilerplate.
class Window(Gtk.Window):
    __gtype_name__ = "Window"

    # To construct a new instance of this method, the following notable
    # methods are called in this order:
    # __new__(cls)
    # __init__(self)
    # finish_initializing(self, builder)
    # __init__(self)
    #
    # For this reason, it's recommended you leave __init__ empty and put
    # your initialization code in finish_initializing

    def __new__(cls):
        """Special static method that's automatically called by Python when
        constructing a new instance of this class.

        Returns a fully instantiated BasePasaffeWindow object.
        """
        builder = get_builder('PasaffeWindow')
        new_object = builder.get_object("pasaffe_window")
        new_object.finish_initializing(builder)
        return new_object

    def finish_initializing(self, builder):
        """Called while initializing this instance in __new__

        finish_initializing should be called after parsing the UI definition
        and creating a PasaffeWindow object with it in order to finish
        initializing the start of the new PasaffeWindow instance.
        """
        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.ui = builder.get_ui(self, True)
        self.PreferencesDialog = None  # class
        self.preferences_dialog = None  # instance
        self.AboutDialog = None  # class

        self.settings = Gio.Settings.new("net.launchpad.pasaffe")
        self.settings.connect('changed', self.on_preferences_changed)

    def on_mnu_contents_activate(self, widget, data=None):
        show_uri(self, get_help_uri())

    def on_mnu_about_activate(self, widget, data=None):
        """Display the about box for pasaffe."""
        if self.AboutDialog is not None:
            about = self.AboutDialog()  # pylint: disable=E1102
            about.set_transient_for(self)
            about.run()
            about.destroy()

    def on_mnu_preferences_activate(self, widget, data=None):
        """Display the preferences window for pasaffe."""

        """ From the PyGTK Reference manual
           Say for example the preferences dialog is currently open,
           and the user chooses Preferences from the menu a second time;
           use the present() method to move the already-open dialog
           where the user can see it."""
        if self.preferences_dialog is not None:
            logger.debug('show existing preferences_dialog')
            self.preferences_dialog.present()
        elif self.PreferencesDialog is not None:
            logger.debug('create new preferences_dialog')
            # pylint: disable=E1102
            self.preferences_dialog = \
                self.PreferencesDialog()
            self.preferences_dialog.set_transient_for(self)
            self.preferences_dialog.connect(
                'destroy', self.on_preferences_dialog_destroyed)
            self.preferences_dialog.show()
        # destroy command moved into dialog to allow for a help button

    def on_mnu_close_activate(self, widget, data=None):
        """Signal handler for closing the PasaffeWindow."""
        self.destroy()

    def on_destroy(self, widget, data=None):
        """Called when the PasaffeWindow is closed."""
        # Clean up code for saving application state should be added here.
        Gtk.main_quit()

    def on_preferences_changed(self, settings, key, data=None):
        logger.debug('preference changed: %s = %s' %
                     (key, str(settings.get_value(key))))
        if key == 'visible-secrets':
            self.set_show_password_status()  # pylint: disable=E1101
            treemodel, treeiter = \
                self.ui.treeview1.get_selection().get_selected()
            if treeiter is not None:
                entry_uuid = treemodel.get_value(treeiter, 2)
                if "pasaffe_treenode." not in entry_uuid:
                    self.display_data(entry_uuid,  # pylint: disable=E1101
                                      show_secrets=settings.get_boolean(key))

    def on_preferences_dialog_destroyed(self, widget, data=None):
        '''only affects gui

        logically there is no difference between the user closing,
        minimising or ignoring the preferences dialog'''
        logger.debug('on_preferences_dialog_destroyed')
        # to determine whether to create or present preferences_dialog
        self.preferences_dialog = None
