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

from gi.repository import Gio, Gtk # pylint: disable=E0611

from pasaffe_lib.helpers import get_builder

import gettext
from gettext import gettext as _
gettext.textdomain('pasaffe')

import subprocess

class EditDetailsDialog(Gtk.Dialog):
    __gtype_name__ = "EditDetailsDialog"

    def __new__(cls):
        """Special static method that's automatically called by Python when 
        constructing a new instance of this class.
        
        Returns a fully instantiated EditDetailsDialog object.
        """
        builder = get_builder('EditDetailsDialog')
        new_object = builder.get_object('edit_details_dialog')
        new_object.finish_initializing(builder)
        return new_object

    def finish_initializing(self, builder):
        """Called when we're finished initializing.

        finish_initalizing should be called after parsing the ui definition
        and creating a EditDetailsDialog object with it in order to
        finish initializing the start of the new EditDetailsDialog
        instance.
        """
        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.ui = builder.get_ui(self)

        settings = Gio.Settings("apps.pasaffe")
        self.password_length = settings.get_int("password-length")

    def on_btn_ok_clicked(self, widget, data=None):
        """The user has elected to save the changes.

        Called before the dialog returns Gtk.RESONSE_OK from run().
        """
        pass

    def on_btn_cancel_clicked(self, widget, data=None):
        """The user has elected cancel changes.

        Called before the dialog returns Gtk.ResponseType.CANCEL for run()
        """
        pass

    def on_password_button_clicked(self, widget):
        """The user has clicked the password button"""
        self.show_passwords_menu()

    def on_menuitem_activate(self, widget):
        """The user has clicked on a menu item"""
        label = widget.get_label()
        self.ui.password_entry.set_text(label)

    def show_passwords_menu(self):
        """Generate some new passwords"""
        command = ["apg", "-n", "6", "-M", "sNC",
                   "-m", str(self.password_length),
                   "-x", str(self.password_length)]
        try:
            passwords = subprocess.check_output(command).splitlines()
            self.ui.password1.set_label(passwords[0])
            self.ui.password2.set_label(passwords[1])
            self.ui.password3.set_label(passwords[2])
            self.ui.password4.set_label(passwords[3])
            self.ui.password5.set_label(passwords[4])
            self.ui.password6.set_label(passwords[5])
            self.ui.password_menu.popup(None, None, None, None,
                                        0, Gtk.get_current_event_time())
        except:
            pass

if __name__ == "__main__":
    dialog = EditDetailsDialog()
    dialog.show()
    Gtk.main()
