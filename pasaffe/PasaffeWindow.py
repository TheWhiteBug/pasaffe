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

import gtk, pango
import os, struct, time, shutil, sys
import logging
logger = logging.getLogger('pasaffe')

from pasaffe_lib import Window
from pasaffe.AboutPasaffeDialog import AboutPasaffeDialog
from pasaffe.EditDetailsDialog import EditDetailsDialog
from pasaffe.PasswordEntryDialog import PasswordEntryDialog
from pasaffe.SaveChangesDialog import SaveChangesDialog
from pasaffe.NewDatabaseDialog import NewDatabaseDialog
from pasaffe.PreferencesPasaffeDialog import PreferencesPasaffeDialog
from pasaffe_lib.readdb import PassSafeFile
from pasaffe_lib import preferences

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
        self.SaveChangesDialog = SaveChangesDialog
        self.NewDatabaseDialog = NewDatabaseDialog

        self.connect("delete-event",self.on_delete_event)

        self.needs_saving = False
        self.passfile = None

        self.set_database()

        # If database doesn't exists, make a new one
        if os.path.exists(self.db_filename):
            success = self.fetch_password()
        else:
            success = self.new_database()

        if success == False:
            self.connect('event-after', gtk.main_quit)
        else:
            self.display_entries()
            self.display_welcome()

    def on_delete_event(self, widget, event):
        if self.needs_saving == True:
            savechanges_dialog = self.SaveChangesDialog()
            response = savechanges_dialog.run()
            if response == gtk.RESPONSE_OK:
                self.save_db()
            elif response == gtk.RESPONSE_CLOSE:
                return False
            else:
                savechanges_dialog.destroy()
                return True

    def fetch_password(self):
        success = True
        password_dialog = self.PasswordEntryDialog()
        while self.passfile == None:
            response = password_dialog.run()
            if response == gtk.RESPONSE_OK:
                password = password_dialog.ui.password_entry.get_text()
                try:
                    self.passfile = PassSafeFile(self.db_filename, password)
                except ValueError:
                    password_dialog.ui.password_error_label.set_property("visible", True)
                    password_dialog.ui.password_entry.set_text("")
                    password_dialog.ui.password_entry.grab_focus()
            else:
                success = False
                break
        password_dialog.destroy()
        return success

    def new_database(self):
        success = False
        newdb_dialog = self.NewDatabaseDialog()
        while success == False:
            response = newdb_dialog.run()
            if response == gtk.RESPONSE_OK:
                passwordA = newdb_dialog.ui.entry1.get_text()
                passwordB = newdb_dialog.ui.entry2.get_text()
                if passwordA != passwordB:
                    newdb_dialog.ui.error_label.set_property("visible", True)
                    newdb_dialog.ui.entry1.grab_focus()
                else:
                    self.passfile = PassSafeFile()
                    self.passfile.new_db(passwordA)
                    success = True
            else:
                break

        newdb_dialog.destroy()
        return success

    def set_database(self):
        if os.environ.has_key('XDG_DATA_HOME'):
            basedir = os.path.join(os.environ['XDG_DATA_HOME'], 'pasaffe')
        else:
            basedir = os.path.join(os.environ['HOME'], '.local/share/pasaffe')

        if not os.path.exists(basedir):
            os.mkdir(basedir, 0700)
        self.db_filename = os.path.join(basedir, 'pasaffe.psafe3')

    def display_entries(self):
        entries = []
        for record in self.passfile.records:
            entries.append([record[3],record[1].encode("hex")])
        self.ui.liststore1.clear()
        for record in sorted(entries, key=lambda entry: entry[0]):
            self.ui.liststore1.append(record)

    def display_data(self, entry_uuid, show_password=False):
        for record in self.passfile.records:
            if record[1] == entry_uuid.decode("hex"):
                last_updated = time.strftime("%a, %d %b %Y %H:%M:%S",
                                   time.localtime(struct.unpack("<I",
                                       record[12])[0]))
                pass_updated = time.strftime("%a, %d %b %Y %H:%M:%S",
                                   time.localtime(struct.unpack("<I",
                                       record[8])[0]))
                title = record.get(3)
                contents = ''
                if record.has_key(5):
                    contents += "%s\n\n" % record.get(5)
                contents += "Username: %s\n" % record.get(4)
                if show_password == True or preferences['visible-passwords'] == True:
                    contents += "Password: %s\n\n" % record.get(6)
                else:
                    contents += "Password: *****\n\n"
                if record.has_key(13):
                    contents += "URL: %s\n\n" % record.get(13)
                contents += "Last updated: %s\nPassword updated: %s\n" % (last_updated, pass_updated)
                self.fill_display(title, contents)
                break

    def display_welcome(self):
        self.fill_display("Welcome to Pasaffe!",
                          "Pasaffe is an easy to use\npassword manager for Gnome.")

    def fill_display(self, title, contents):
        texttagtable = gtk.TextTagTable()
        texttag_big = gtk.TextTag("big")
        texttag_big.set_property("weight", pango.WEIGHT_BOLD)
        texttag_big.set_property("scale", pango.SCALE_LARGE)
        texttagtable.add(texttag_big)
        data_buffer = gtk.TextBuffer(texttagtable)
        data_buffer.insert_with_tags(data_buffer.get_start_iter(), "\n" + title + "\n\n", texttag_big)
        data_buffer.insert(data_buffer.get_end_iter(), contents)

        self.ui.textview1.set_buffer(data_buffer)

    def on_treeview1_cursor_changed(self, treeview):
        treemodel, treeiter = treeview.get_selection().get_selected()
        entry_uuid = treemodel.get_value(treeiter, 1)
        self.display_data(entry_uuid)

    def add_entry(self):
        uuid = os.urandom(16)
        uuid_hex = uuid.encode("hex")
        timestamp = struct.pack("<I", time.time())
        new_entry = {1: uuid, 3: '', 4: '', 5: '', 6: '',
                     7: timestamp, 8: timestamp, 12: timestamp, 13: ''}
        self.passfile.records.append(new_entry)

        response = self.edit_entry(uuid_hex)
        if response != gtk.RESPONSE_OK:
            self.delete_entry(uuid_hex)
        else:
            self.display_entries()
            item = self.ui.treeview1.get_model().get_iter_first()
            while (item != None):
                if self.ui.liststore1.get_value(item, 1) == uuid_hex:
                    self.ui.treeview1.get_selection().select_iter(item)
                    self.display_data(uuid_hex)
                    break
                else:
                    item = self.ui.treeview1.get_model().iter_next(item)

    def edit_entry(self, entry_uuid):
        record_dict = { 3 : 'name_entry',
                        4 : 'username_entry',
                        5 : 'notes_buffer',
                        6 : 'password_entry',
                        13: 'url_entry' }

        if self.EditDetailsDialog is not None:
            details = self.EditDetailsDialog()

            for record in self.passfile.records:
                if record[1] == entry_uuid.decode("hex"):
                    for record_type, widget_name in record_dict.items():
                        if record.has_key(record_type):
                            details.builder.get_object(widget_name).set_text(record[record_type])
                    break

            response = details.run()
            if response == gtk.RESPONSE_OK:
                data_changed = False
                timestamp = struct.pack("<I", time.time())
                for record_type, widget_name in record_dict.items():
                    if record_type == 5:
                        new_value = details.builder.get_object(widget_name).get_text(*details.builder.get_object(widget_name).get_bounds())
                    else:
                        new_value = details.builder.get_object(widget_name).get_text()

                    if (record_type == 5 or record_type == 13) and new_value == "" and record.has_key(record_type):
                            del record[record_type]
                    elif record.get(record_type, "") != new_value:
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
            self.display_data(entry_uuid)
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
            if record[1].encode("hex") == entry_uuid:
                self.passfile.records.remove(record)

        self.needs_saving = True

        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)
            self.display_data(entry_uuid)
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

    def save_db(self):
        if self.needs_saving == True:
            # Create backup if exists
            if os.path.exists(self.db_filename):
                shutil.copy(self.db_filename, self.db_filename + ".bak")
            self.passfile.writefile(self.db_filename)
            self.needs_saving = False

    def on_save_clicked(self, toolbutton):
        self.save_db()

    def on_mnu_save_activate(self, menuitem):
        self.save_db()

    def on_mnu_close_activate(self, menuitem):
        gtk.main_quit()

    def on_mnu_cut_activate(self, menuitem):
        print "TODO: implement on_mnu_cut_activate()"

    def on_mnu_copy_activate(self, menuitem):
        clipboard = gtk.clipboard_get()
        self.ui.textview1.get_buffer().copy_clipboard(clipboard)
        clipboard.store()

    def on_mnu_paste_activate(self, menuitem):
        print "TODO: implement on_mnu_paste_activate()"

    def on_username_copy_activate(self, menuitem):
        self.copy_selected_entry_item(4)

    def on_password_copy_activate(self, menuitem):
        self.copy_selected_entry_item(6)

    def on_url_copy_activate(self, menuitem):
        self.copy_selected_entry_item(13)

    def on_copy_username_clicked(self, toolbutton):
        self.copy_selected_entry_item(4)

    def on_copy_password_clicked(self, toolbutton):
        self.copy_selected_entry_item(6)

    def on_display_password_clicked(self, toolbutton):
        self.display_password()

    def on_mnu_display_password_activate(self, menuitem):
        self.display_password()

    def display_password(self):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)
            self.display_data(entry_uuid, show_password=True)

    def copy_selected_entry_item(self, item):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)

            for record in self.passfile.records:
                if record[1] == entry_uuid.decode("hex") and record.has_key(item):
                    clipboard = gtk.clipboard_get()
                    clipboard.set_text(record[item])
                    clipboard.store()

    def on_mnu_add_activate(self, menuitem):
        self.add_entry()

    def on_mnu_delete_activate(self, menuitem):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)
            self.delete_entry(entry_uuid)

    def on_add_clicked(self, toolbutton):
        self.add_entry()

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

