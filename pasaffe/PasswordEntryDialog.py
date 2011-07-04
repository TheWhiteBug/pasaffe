# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This file is in the public domain
### END LICENSE

import gtk

from pasaffe_lib.helpers import get_builder

import gettext
from gettext import gettext as _
gettext.textdomain('pasaffe')

class PasswordEntryDialog(gtk.Dialog):
    __gtype_name__ = "PasswordEntryDialog"

    def __new__(cls):
        """Special static method that's automatically called by Python when 
        constructing a new instance of this class.
        
        Returns a fully instantiated PasswordEntryDialog object.
        """
        builder = get_builder('PasswordEntryDialog')
        new_object = builder.get_object('password_entry_dialog')
        new_object.finish_initializing(builder)
        return new_object

    def finish_initializing(self, builder):
        """Called when we're finished initializing.

        finish_initalizing should be called after parsing the ui definition
        and creating a PasswordEntryDialog object with it in order to
        finish initializing the start of the new PasswordEntryDialog
        instance.
        """
        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.ui = builder.get_ui(self)

    def on_btn_ok_clicked(self, widget, data=None):
        """The user has elected to save the changes.

        Called before the dialog returns gtk.RESONSE_OK from run().
        """
        pass

    def on_btn_cancel_clicked(self, widget, data=None):
        """The user has elected cancel changes.

        Called before the dialog returns gtk.RESPONSE_CANCEL for run()
        """
        pass


if __name__ == "__main__":
    dialog = PasswordEntryDialog()
    dialog.show()
    gtk.main()
