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
import os, struct, time, shutil, sys
import logging
logger = logging.getLogger('pasaffe')

from pasaffe_lib import Window
from pasaffe.AboutPasaffeDialog import AboutPasaffeDialog
from pasaffe.EditDetailsDialog import EditDetailsDialog
from pasaffe.PasswordEntryDialog import PasswordEntryDialog
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
        self.PasswordEntryDialog = PasswordEntryDialog

        self.needs_saving = False
        self.passfile = None

        self.db_filename = "/tmp/test.psafe3"
        self.password = self.fetch_password()
        if self.password == False:
            sys.exit(1)

        for record in self.passfile.records:
            self.ui.liststore1.append([record[3],record[1]])

        # Select first item by default
        #self.ui.treeview1.set_cursor('0')

        self.display_welcome()

    def fetch_password(self):
        password = False
        password_dialog = self.PasswordEntryDialog()
        while self.passfile == None:
            response = password_dialog.run()
            if response == gtk.RESPONSE_OK:
                password = password_dialog.ui.password_entry.get_text()
                try:
                    self.passfile = PassSafeFile(self.db_filename, password)
                except ValueError:
                    print "we're in the exception, self_passfile = %s" % self.passfile
                    password_dialog.ui.password_error_label.set_property("visible", True)
            else:
                password = False
                break
        password_dialog.destroy()
        return password

    def _display_data(self, entry_uuid):
        for record in self.passfile.records:
            if record[1] == entry_uuid:
                last_updated = time.strftime("%a, %d %b %Y %H:%M:%S",
                                   time.localtime(struct.unpack("<I",
                                       record[12])[0]))
                data_buffer = gtk.TextBuffer()
                data_buffer.set_text('''Title: %s
Notes: %s
Username: %s
Password: %s

Last updated: %s
''' % (record[3], record[5], record[4], record[6], last_updated))
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
        record_dict = { 3 : 'name_entry',
                        4 : 'username_entry',
                        5 : 'notes_entry',
                        6 : 'password_entry' }

        if self.EditDetailsDialog is not None:
            details = self.EditDetailsDialog()

            for record in self.passfile.records:
                if record[1] == entry_uuid:
                    for record_type, widget_name in record_dict.items():
                        details.builder.get_object(widget_name).set_text(record[record_type])
                    break

            response = details.run()
            if response == gtk.RESPONSE_OK:
                data_changed = False
                timestamp = struct.pack("<I", time.time())
                for record_type, widget_name in record_dict.items():
                    new_value = details.builder.get_object(widget_name).get_text()
                    if record[record_type] != new_value:
                        data_changed = True
                        record[record_type] = new_value

                        # Update the name in the tree
                        if record_type == 3:
                            item = self.ui.treeview1.get_model().get_iter_first()
                            while (item != None):
                                if self.ui.liststore1.get_value(item, 1) == entry_uuid:
                                    self.ui.liststore1.set_value(item, 0, new_value)
                                    break
                                else:
                                    item = self.ui.treeview1.get_model().iter_next(item)

                        # Update the password changed date
                        if record_type == 6:
                            record[8] = timestamp

                if data_changed == True:
                    self.needs_saving = True
                    record[12] = timestamp

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
        if self.needs_saving == True:
            # Create backup
            shutil.copyfile(self.db_filename, self.db_filename + ".bak")
            self.passfile.writefile(self.db_filename, self.password)
            self.needs_saving = False

    def on_add_clicked(self, toolbutton):
        uuid = os.urandom(16)
        timestamp = struct.pack("<I", time.time())
        new_entry = {1: uuid, 3: '', 4: '', 5: '', 6: '',
                     7: timestamp, 8: timestamp, 12: timestamp}
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

