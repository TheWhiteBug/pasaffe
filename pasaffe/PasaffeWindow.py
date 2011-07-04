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

import gettext
from gettext import gettext as _
gettext.textdomain('pasaffe')

import gtk
import logging
logger = logging.getLogger('pasaffe')

from pasaffe_lib import Window
from pasaffe.AboutPasaffeDialog import AboutPasaffeDialog
from pasaffe.EditDetailsDialog import EditDetailsDialog
from pasaffe.PreferencesPasaffeDialog import PreferencesPasaffeDialog
from pasaffe_lib.readdb import PassSafeFile

# See pasaffe_lib.Window.py for more details about how this class works
class PasaffeWindow(Window):
    __gtype_name__ = "PasaffeWindow"

    def finish_initializing(self, builder): # pylint: disable=E1002
        """Set up the main window"""
        super(PasaffeWindow, self).finish_initializing(builder)

        self.AboutDialog = AboutPasaffeDialog
        self.EditDetailsDialog = EditDetailsDialog
        self.PreferencesDialog = PreferencesPasaffeDialog

        self.needs_saving = False

        # Read database
        self.passfile = PassSafeFile("/tmp/test.psafe3", "ubuntu")
        #print self.passfile.records
        for record in self.passfile.records:
            self.ui.liststore1.append([record[3],record[1]])

        # Select first item by default
        #self.ui.treeview1.set_cursor('0')

        data_buffer = gtk.TextBuffer()
        data_buffer.set_text('''Welcome to Pasaffe!

Click an item on the left to see details.
''')
        self.ui.textview1.set_buffer(data_buffer)


    def _display_data(self, entry_uuid):
        for record in self.passfile.records:
            if record[1] == entry_uuid:
                data_buffer = gtk.TextBuffer()
                data_buffer.set_text('''Title: %s
Notes: %s
Username: %s
Password: %s
''' % (record[3], record[5], record[4], record[6]))
                self.ui.textview1.set_buffer(data_buffer)
                break

    def on_treeview1_cursor_changed(self, treeview):
        treemodel, treeiter = treeview.get_selection().get_selected()
        entry_uuid = treemodel.get_value(treeiter, 1)
        self._display_data(entry_uuid)

    def on_treeview1_row_activated(self, treeview, path, view_column):
        treemodel, treeiter = treeview.get_selection().get_selected()
        entry_uuid = treemodel.get_value(treeiter, 1)

        if self.EditDetailsDialog is not None:
            details = self.EditDetailsDialog()

            for record in self.passfile.records:
                if record[1] == entry_uuid:
                    details.ui.name_entry.set_text(record[3])
                    details.ui.notes_entry.set_text(record[5])
                    details.ui.username_entry.set_text(record[4])
                    details.ui.password_entry.set_text(record[6])
                    break

            response = details.run()
            if response == gtk.RESPONSE_OK:
                record[3] = details.ui.name_entry.get_text()
                treemodel.set_value(treeiter, 0, record[3])
                record[5] = details.ui.notes_entry.get_text()
                record[4] = details.ui.username_entry.get_text()
                record[6] = details.ui.password_entry.get_text()
                # FIXME: actually check is anything was modified
                self.needs_saving = True
            details.destroy()

            self._display_data(entry_uuid)

    def on_save_clicked(self, toolbutton):
        print "on_save_clicked called"
        print "needs saving: %s" % self.needs_saving
