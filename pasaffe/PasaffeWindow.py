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
import os, struct, time
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
        print self.passfile.records
        for record in self.passfile.records:
            self.ui.liststore1.append([record[3],record[1]])

        # Select first item by default
        #self.ui.treeview1.set_cursor('0')

        self.display_welcome()

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

    def display_welcome(self):
        data_buffer = gtk.TextBuffer()
        data_buffer.set_text('''Welcome to Pasaffe!

Click an item on the left to see details.
''')
        self.ui.textview1.set_buffer(data_buffer)

    def on_treeview1_cursor_changed(self, treeview):
        treemodel, treeiter = treeview.get_selection().get_selected()
        entry_uuid = treemodel.get_value(treeiter, 1)
        self._display_data(entry_uuid)

    def edit_entry(self, entry_uuid):
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
                record[5] = details.ui.notes_entry.get_text()
                record[4] = details.ui.username_entry.get_text()
                record[6] = details.ui.password_entry.get_text()

                # Update the name in the tree
                item = self.ui.treeview1.get_model().get_iter_first()
                while (item != None):
                    if self.ui.liststore1.get_value(item, 1) == entry_uuid:
                        self.ui.liststore1.set_value(item, 0, record[3])
                        break
                    else:
                        item = self.ui.treeview1.get_model().iter_next(item)

                # FIXME: actually check is anything was modified
                self.needs_saving = True

            details.destroy()
            self._display_data(entry_uuid)
            return response

    def delete_entry(self, entry_uuid):
        item = self.ui.treeview1.get_model().get_iter_first()

        while (item != None):
            if self.ui.liststore1.get_value(item, 1) == entry_uuid:
                next_item = self.ui.treeview1.get_model().iter_next(item)
                self.ui.liststore1.remove(item)
                if next_item == None:
                    next_item = self.model_get_iter_last(self.ui.treeview1.get_model())
                if next_item != 0:
                    self.ui.treeview1.get_selection().select_iter(next_item)
                break
            else:
                item = self.ui.treeview1.get_model().iter_next(item)

        for record in self.passfile.records:
            if record[1] == entry_uuid:
                self.passfile.records.remove(record)

        self.needs_saving = True

        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)
            self._display_data(entry_uuid)
        else:
            self.display_welcome()

    def model_get_iter_last(self, model, parent=None):
        """Returns a gtk.TreeIter to the last row or None if there aren't any rows.
        If parent is None, returns a gtk.TreeIter to the last root row."""
        n = model.iter_n_children( parent )
        return n and model.iter_nth_child( parent, n - 1 )

    def on_treeview1_row_activated(self, treeview, path, view_column):
        treemodel, treeiter = treeview.get_selection().get_selected()
        entry_uuid = treemodel.get_value(treeiter, 1)
        self.edit_entry(entry_uuid)

    def on_save_clicked(self, toolbutton):
        print "on_save_clicked called"
        print "needs saving: %s" % self.needs_saving

    def on_add_clicked(self, toolbutton):
        uuid = os.urandom(16)
        timestamp = struct.pack("<I", time.time())
        new_entry = {1: uuid, 3: '', 4: '', 5: '', 6: '',
                     7: timestamp, 8: timestamp, 13: timestamp}
        self.passfile.records.append(new_entry)

        new_iter=self.ui.liststore1.append(['',uuid])
        self.ui.treeview1.get_selection().select_iter(new_iter)
        self._display_data(uuid)
        response = self.edit_entry(uuid)
        if response != gtk.RESPONSE_OK:
            self.delete_entry(uuid)

    def on_edit_clicked(self, toolbutton):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)
            self.edit_entry(entry_uuid)

    def on_remove_clicked(self, toolbutton):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)
            self.delete_entry(entry_uuid)

