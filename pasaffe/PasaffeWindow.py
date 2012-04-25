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

import gettext
t = gettext.translation('pasaffe', fallback=True)
_ = t.ugettext

from gi.repository import GObject, Gio, Gtk, Gdk, Pango, GLib # pylint: disable=E0611
import os, struct, time, sys, webbrowser, re
import logging
logger = logging.getLogger('pasaffe')

from pasaffe_lib import Window
from pasaffe.AboutPasaffeDialog import AboutPasaffeDialog
from pasaffe.EditDetailsDialog import EditDetailsDialog
from pasaffe.PasswordEntryDialog import PasswordEntryDialog
from pasaffe.SaveChangesDialog import SaveChangesDialog
from pasaffe.NewDatabaseDialog import NewDatabaseDialog
from pasaffe.NewPasswordDialog import NewPasswordDialog
from pasaffe.PreferencesPasaffeDialog import PreferencesPasaffeDialog
from pasaffe_lib.readdb import PassSafeFile
from pasaffe_lib.helpers import get_builder

# See pasaffe_lib.Window.py for more details about how this class works
class PasaffeWindow(Window):
    __gtype_name__ = "PasaffeWindow"

    def __new__(cls, database=None):
        """Special static method that's automatically called by Python when 
        constructing a new instance of this class.

        Returns a fully instantiated BasePasaffeWindow object.
        """
        builder = get_builder('PasaffeWindow')
        new_object = builder.get_object("pasaffe_window")
        new_object.finish_initializing(builder, database)
        return new_object


    def finish_initializing(self, builder, database): # pylint: disable=E1002
        """Set up the main window"""
        super(PasaffeWindow, self).finish_initializing(builder)

        self.AboutDialog = AboutPasaffeDialog
        self.EditDetailsDialog = EditDetailsDialog
        self.editdetails_dialog = None
        self.PreferencesDialog = PreferencesPasaffeDialog
        self.PasswordEntryDialog = PasswordEntryDialog
        self.SaveChangesDialog = SaveChangesDialog
        self.NewDatabaseDialog = NewDatabaseDialog
        self.NewPasswordDialog = NewPasswordDialog

        self.connect("delete-event",self.on_delete_event)
        self.ui.textview1.connect("motion-notify-event", self.textview_event_handler)

        self.set_save_status(False)
        self.passfile = None
        self.is_locked = False
        self.idle_id = None
        self.find_results = []
        self.find_results_index = None
        self.find_value = ""

        if database == None:
            self.database = self.settings.get_string('database-path')
        else:
            self.database = database

        self.settings = Gio.Settings("apps.pasaffe")
        self.settings.connect('changed', self.on_preferences_changed)

        # If database doesn't exists, make a new one
        if os.path.exists(self.database):
            success = self.fetch_password()
        else:
            success = self.new_database()

        if success == False:
            self.connect('event-after', Gtk.main_quit)
        else:
            self.set_show_password_status()
            self.display_entries()
            self.display_welcome()

        # Set inactivity timer
        self.set_idle_timeout()

    def on_delete_event(self, widget, event):
        return self.save_warning()

    def save_warning(self):
        if self.get_save_status() == True:
            savechanges_dialog = self.SaveChangesDialog()
            response = savechanges_dialog.run()
            if response == Gtk.ResponseType.OK:
                self.save_db()
            elif response != Gtk.ResponseType.CLOSE:
                savechanges_dialog.destroy()
                return True
        return False

    def fetch_password(self):
        success = True
        password_dialog = self.PasswordEntryDialog()
        while self.passfile == None:
            response = password_dialog.run()
            if response == Gtk.ResponseType.OK:
                password = password_dialog.ui.password_entry.get_text()
                try:
                    self.passfile = PassSafeFile(self.database, password)
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
            if response == Gtk.ResponseType.OK:
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

    def display_entries(self):
        entries = []
        for record in self.passfile.records:
            entries.append([record[3],record[1].encode("hex")])
        self.ui.liststore1.clear()
        for record in sorted(entries, key=lambda entry: entry[0].lower()):
            self.ui.liststore1.append(record)

    def display_data(self, entry_uuid, show_secrets=False):
        for record in self.passfile.records:
            if record[1] == entry_uuid.decode("hex"):
                title = record.get(3)

                url = None
                if record.has_key(13):
                    url = "%s\n\n" % record.get(13)

                contents = ''
                if show_secrets == False and \
                   self.settings.get_boolean('only-passwords-are-secret') == False and \
                   self.settings.get_boolean('visible-secrets') == False:
                    contents += _("Secrets are currently hidden.")
                else:
                    if record.has_key(5):
                            contents += "%s\n\n" % record.get(5)
                    contents += _("Username: %s\n") % record.get(4)
                    if show_secrets == True or self.settings.get_boolean('visible-secrets') == True:
                        contents += _("Password: %s\n\n") % record.get(6)
                    else:
                        contents += _("Password: *****\n\n")
                    if record.has_key(12):
                        last_updated = time.strftime("%a, %d %b %Y %H:%M:%S",
                                       time.localtime(struct.unpack("<I",
                                       record[12])[0]))
                        contents += _("Last updated: %s\n") % last_updated
                    if record.has_key(8):
                        pass_updated = time.strftime("%a, %d %b %Y %H:%M:%S",
                                       time.localtime(struct.unpack("<I",
                                           record[8])[0]))
                        contents += _("Password updated: %s\n") % pass_updated
                self.fill_display(title, url, contents)
                break

    def display_welcome(self):
        self.fill_display(_("Welcome to Pasaffe!"), None,
                          _("Pasaffe is an easy to use\npassword manager for Gnome."))

    def fill_display(self, title, url, contents):
        texttagtable = Gtk.TextTagTable()
        texttag_big = Gtk.TextTag.new("big")
        texttag_big.set_property("weight", Pango.Weight.BOLD)
        texttag_big.set_property("size", 12 * Pango.SCALE)
        texttagtable.add(texttag_big)

        texttag_url = Gtk.TextTag.new("url")
        texttag_url.set_property("foreground", "blue")
        texttag_url.set_property("underline", Pango.Underline.SINGLE)
        texttag_url.connect("event", self.url_event_handler)
        texttagtable.add(texttag_url)

        data_buffer = Gtk.TextBuffer.new(texttagtable)
        data_buffer.insert_with_tags(data_buffer.get_start_iter(), "\n" + title + "\n\n", texttag_big)
        if url != None:
            data_buffer.insert(data_buffer.get_end_iter(), "\n")
            data_buffer.insert_with_tags(data_buffer.get_end_iter(), url, texttag_url)
            data_buffer.insert(data_buffer.get_end_iter(), "\n")
        data_buffer.insert(data_buffer.get_end_iter(), contents)

        self.ui.textview1.set_buffer(data_buffer)

    def url_event_handler(self, tag, widget, event, iter):
        # We also used to check event.button == 1 here, but event.button
        # doesn't seem to get set by PyGObject anymore.
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            self.open_url()
        return False

    def textview_event_handler(self, textview, event):
        x, y = textview.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, int(event.x), int(event.y))
        iter = textview.get_iter_at_location(x, y)
        cursor = Gdk.Cursor.new(Gdk.CursorType.XTERM)
        for tag in iter.get_tags():
            if tag.get_property('name') == 'url':
                cursor = Gdk.Cursor.new(Gdk.CursorType.HAND2)
                break
        textview.get_window(Gtk.TextWindowType.TEXT).set_cursor(cursor)
        return False

    def open_url(self):
        url = None 
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)
            for record in self.passfile.records:
                if record[1] == entry_uuid.decode("hex") and record.has_key(13):
                    url = record[13]
                    break
        if url != None:
            if not url.startswith('http://') and \
               not url.startswith('https://'):
                url = 'http://' + url
        webbrowser.open(url)

    def on_treeview1_cursor_changed(self, treeview):
        self.set_idle_timeout()
        selection = treeview.get_selection()
        if selection is not None:
            treemodel, treeiter = selection.get_selected()
            if treemodel is not None and treeiter is not None:
                entry_uuid = treemodel.get_value(treeiter, 1)
                self.display_data(entry_uuid)
                # Reset the show password button and menu item
                self.ui.display_secrets.set_active(False)
                self.ui.mnu_display_secrets.set_active(False)

    def on_treeview1_button_press_event(self, treeview, event):
        if event.button == 3:
            x = int(event.x)
            y = int(event.y)
            time = event.time
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor(path, col, 0)
                self.ui.menu_popup.popup(None, None, None, None, 3, time)

    def add_entry(self):
        self.disable_idle_timeout()

        # Make sure dialog isn't already open
        if self.editdetails_dialog is not None:
            self.editdetails_dialog.present()
            return

        uuid = os.urandom(16)
        uuid_hex = uuid.encode("hex")
        timestamp = struct.pack("<I", int(time.time()))
        new_entry = {1: uuid, 3: '', 4: '', 5: '', 6: '',
                     7: timestamp, 8: timestamp, 12: timestamp, 13: ''}
        self.passfile.records.append(new_entry)

        response = self.edit_entry(uuid_hex)
        if response != Gtk.ResponseType.OK:
            self.delete_entry(uuid_hex, save=False)
        else:
            self.display_entries()
            item = self.ui.treeview1.get_model().get_iter_first()
            while (item != None):
                if self.ui.liststore1.get_value(item, 1) == uuid_hex:
                    self.ui.treeview1.get_selection().select_iter(item)
                    self.display_data(uuid_hex)
                    path = self.ui.treeview1.get_model().get_path(item)
                    self.ui.treeview1.scroll_to_cell(path)
                    break
                else:
                    item = self.ui.treeview1.get_model().iter_next(item)
            self.set_save_status(True)
            if self.settings.get_boolean('auto-save') == True:
                self.save_db()
        self.set_idle_timeout()
        self.update_find_results(force=True)

    def clone_entry(self, entry_uuid):
        record_list = ( 3, 4, 5, 6, 13 )
        self.disable_idle_timeout()

        # Make sure dialog isn't already open
        if self.editdetails_dialog is not None:
            self.editdetails_dialog.present()
            return

        uuid = os.urandom(16)
        uuid_hex = uuid.encode("hex")
        timestamp = struct.pack("<I", int(time.time()))
        new_entry = {1: uuid, 3: '', 4: '', 5: '', 6: '',
                     7: timestamp, 8: timestamp, 12: timestamp, 13: ''}

        for record in self.passfile.records:
            if record[1] == entry_uuid.decode("hex"):
                for record_type in record_list:
                    if record.has_key(record_type):
                        new_entry[record_type] = record[record_type]
                break

        self.passfile.records.append(new_entry)

        response = self.edit_entry(uuid_hex)
        if response != Gtk.ResponseType.OK:
            self.delete_entry(uuid_hex, save=False)
        else:
            self.display_entries()
            item = self.ui.treeview1.get_model().get_iter_first()
            while (item != None):
                if self.ui.liststore1.get_value(item, 1) == uuid_hex:
                    self.ui.treeview1.get_selection().select_iter(item)
                    self.display_data(uuid_hex)
                    path = self.ui.treeview1.get_model().get_path(item)
                    self.ui.treeview1.scroll_to_cell(path)
                    break
                else:
                    item = self.ui.treeview1.get_model().iter_next(item)
            self.set_save_status(True)
            if self.settings.get_boolean('auto-save') == True:
                self.save_db()
        self.set_idle_timeout()
        self.update_find_results(force=True)

    def remove_entry(self):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)
            entry_name = treemodel.get_value(treeiter, 0)

            information = _('<big><b>Are you sure you wish to remove "%s"?</b></big>\n\n') % entry_name
            information += _('Contents of the entry will be lost.\n')

            info_dialog = Gtk.MessageDialog(parent=self, flags=Gtk.DialogFlags.MODAL, type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO)
            info_dialog.set_markup(information)
            result = info_dialog.run()
            info_dialog.destroy()

            if result == Gtk.ResponseType.YES:
                self.delete_entry(entry_uuid)

    def edit_entry(self, entry_uuid):
        record_dict = { 3 : 'name_entry',
                        4 : 'username_entry',
                        5 : 'notes_buffer',
                        6 : 'password_entry',
                        13: 'url_entry' }

        # Make sure dialog isn't already open
        if self.editdetails_dialog is not None:
            self.editdetails_dialog.present()
            return

        if self.EditDetailsDialog is not None:
            self.disable_idle_timeout()
            self.editdetails_dialog = self.EditDetailsDialog()

            for record in self.passfile.records:
                if record[1] == entry_uuid.decode("hex"):
                    for record_type, widget_name in record_dict.items():
                        if record.has_key(record_type):
                            self.editdetails_dialog.builder.get_object(widget_name).set_text(record[record_type])
                    break

            response = self.editdetails_dialog.run()
            if response == Gtk.ResponseType.OK:
                data_changed = False
                timestamp = struct.pack("<I", int(time.time()))
                for record_type, widget_name in record_dict.items():
                    if record_type == 5:
                        new_value = self.editdetails_dialog.builder.get_object(widget_name).get_text(self.editdetails_dialog.builder.get_object(widget_name).get_start_iter(), self.editdetails_dialog.builder.get_object(widget_name).get_end_iter(), True)
                    else:
                        new_value = self.editdetails_dialog.builder.get_object(widget_name).get_text()

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
                    self.set_save_status(True)
                    record[12] = timestamp
                    if self.settings.get_boolean('auto-save') == True:
                        self.save_db()

            self.editdetails_dialog.destroy()
            self.editdetails_dialog = None

            # Update the right pane only if it's still the one currently selected
            treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
            if treeiter != None and treemodel.get_value(treeiter, 1) == entry_uuid:
                self.display_data(entry_uuid)

            self.set_idle_timeout()
            self.update_find_results(force=True)
            return response

    def delete_entry(self, entry_uuid, save=True):
        self.set_idle_timeout()
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

        if save == True:
            self.set_save_status(True)
            if self.settings.get_boolean('auto-save') == True:
                self.save_db()

        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)
            self.display_data(entry_uuid)
        else:
            self.display_welcome()

        self.update_find_results(force=True)

    def model_get_iter_last(self, model, parent=None):
        """Returns a Gtk.TreeIter to the last row or None if there aren't any rows.
        If parent is None, returns a Gtk.TreeIter to the last root row."""
        n = model.iter_n_children( parent )
        return n and model.iter_nth_child( parent, n - 1 )

    def on_treeview1_row_activated(self, treeview, path, view_column):
        treemodel, treeiter = treeview.get_selection().get_selected()
        entry_uuid = treemodel.get_value(treeiter, 1)
        self.edit_entry(entry_uuid)

    def save_db(self):
        if self.get_save_status() == True:
            self.passfile.writefile(self.database, backup=True)
            self.set_save_status(False)

    def on_save_clicked(self, toolbutton):
        self.set_idle_timeout()
        self.save_db()

    def on_mnu_save_activate(self, menuitem):
        self.set_idle_timeout()
        self.save_db()

    def on_mnu_close_activate(self, menuitem):
        self.disable_idle_timeout()
        if self.settings.get_boolean('auto-save') == True:
            self.save_db()
        if self.save_warning() == False:
            Gtk.main_quit()
        else:
            self.set_idle_timeout()

    def on_mnu_clone_activate(self, menuitem):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)
            self.clone_entry(entry_uuid)

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

    def on_display_secrets_toggled(self, toolbutton):
        is_active = toolbutton.get_active()
        self.display_secrets(is_active)
        self.ui.mnu_display_secrets.set_active(is_active)

    def on_mnu_display_secrets_toggled(self, menuitem):
        is_active = menuitem.get_active()
        self.display_secrets(is_active)
        self.ui.display_secrets.set_active(is_active)

    def display_secrets(self, display=True):
        self.set_idle_timeout()
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)
            self.display_data(entry_uuid, display)

    def copy_selected_entry_item(self, item):
        self.set_idle_timeout()
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)

            for record in self.passfile.records:
                if record[1] == entry_uuid.decode("hex") and record.has_key(item):
                    for atom in [Gdk.SELECTION_CLIPBOARD, Gdk.SELECTION_PRIMARY]:
                        clipboard = Gtk.Clipboard.get(atom)
                        clipboard.set_text(record[item], len(record[item]))
                        clipboard.store()

    def on_mnu_add_activate(self, menuitem):
        self.add_entry()

    def on_mnu_edit1_activate(self, menuitem):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)
            self.edit_entry(entry_uuid)

    def on_mnu_delete_activate(self, menuitem):
        self.remove_entry()

    def on_mnu_lock_activate(self, menuitem):
        self.lock_screen()

    def on_mnu_info_activate(self, menuitem):
        information = _('<big><b>Database Information</b></big>\n\n')
        information += _('Number of entries: %s\n') % len(self.passfile.records)
        information += _('Database version: %s.%s\n') % (self.passfile.header[0][1].encode('hex'),self.passfile.header[0][0].encode('hex'))
        if 7 in self.passfile.header:
            information += _('Last saved by: %s\n') % self.passfile.header[7]
        if 8 in self.passfile.header:
            information += _('Last saved on host: %s\n') % self.passfile.header[8]
        if 4 in self.passfile.header:
            last_saved = time.strftime("%a, %d %b %Y %H:%M:%S",
                                   time.localtime(struct.unpack("<I",
                                   self.passfile.header[4])[0]))
            information += _('Last save date: %s\n') % last_saved
        if 6 in self.passfile.header:
            information += _('Application used: %s\n') % self.passfile.header[6]

        info_dialog = Gtk.MessageDialog(type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK)
        info_dialog.set_markup(information)
        info_dialog.run()
        info_dialog.destroy()

    def on_mnu_open_url_activate(self, menuitem):
        self.open_url()

    def on_mnu_find_toggled(self, menuitem):
        is_active = menuitem.get_active()
        self.show_find(is_active)
        self.ui.toolbar_find.set_active(is_active)

    def on_toolbar_find_toggled(self, toolbutton):
        is_active = toolbutton.get_active()
        self.show_find(is_active)
        self.ui.mnu_find.set_active(is_active)

    def on_find_btn_close_clicked(self, button):
        self.show_find(False)
        self.ui.toolbar_find.set_active(False)
        self.ui.mnu_find.set_active(False)

    def on_find_btn_prev_clicked(self, button):
        self.update_find_results()
        self.goto_next_find_result(backwards=True)

    def on_find_btn_next_clicked(self, button):
        self.update_find_results()
        self.goto_next_find_result()

    def update_find_results(self, force=False):

        if self.ui.find_box.get_property("visible") == False:
            return

        find = self.ui.find_entry.get_text()

        if find == "":
            self.find_results = []
            self.find_results_index = None
            self.find_value = ""
            return

        if find == self.find_value and force == False:
            return

        record_list = ( 3, 5, 13 )
        pat = re.compile(find, re.IGNORECASE)
        results = []

        for record in self.passfile.records:
            found = False
            for record_type in record_list:
                if record.has_key(record_type):
                    if pat.search(record.get(record_type)):
                        found = True
                        break

            if found == True:
                results.append([record[3],record[1].encode("hex")])

        self.find_results = sorted(results, key=lambda results: results[0].lower())
        self.find_results_index = None
        self.find_value = find

    def goto_next_find_result(self, backwards=False):

        if len(self.find_results) == 0:
            return

        if self.find_results_index == None:
            self.find_results_index = 0
        elif backwards == False:
            self.find_results_index += 1
            if self.find_results_index == len(self.find_results):
                self.find_results_index = 0
        else:
            if self.find_results_index == 0:
                self.find_results_index = len(self.find_results) - 1
            else:
                self.find_results_index -= 1

        result = self.find_results[self.find_results_index]
        uuid_hex = result[1]

        item = self.ui.treeview1.get_model().get_iter_first()
        while (item != None):
            if self.ui.liststore1.get_value(item, 1) == uuid_hex:
                self.ui.treeview1.get_selection().select_iter(item)
                self.display_data(uuid_hex)
                path = self.ui.treeview1.get_model().get_path(item)
                self.ui.treeview1.scroll_to_cell(path)
                break
            else:
                item = self.ui.treeview1.get_model().iter_next(item)

    def on_find_entry_activate(self, entry):
        self.update_find_results()
        self.goto_next_find_result()

    def show_find(self, show):

        if self.ui.find_box.get_property("visible") == show:
            return

        if show == True:
            self.ui.find_entry.set_text("")
            self.find_value = ""
            self.ui.find_box.set_property("visible", True)
            self.ui.find_entry.grab_focus()
        else:
            self.ui.find_box.set_property("visible", False)
            self.find_results = []
            self.find_results_index = None

    def on_open_url_clicked(self, toolbutton):
        self.open_url()

    def on_mnu_chg_password_activate(self, menuitem):
        success = False
        newpass_dialog = self.NewPasswordDialog()
        while success == False:
            response = newpass_dialog.run()
            if response == Gtk.ResponseType.OK:
                old_password = newpass_dialog.ui.pass_entry1.get_text()
                passwordA = newpass_dialog.ui.pass_entry2.get_text()
                passwordB = newpass_dialog.ui.pass_entry3.get_text()
                if passwordA != passwordB:
                    newpass_dialog.ui.label3.set_text(_("Passwords don't match! Please try again."))
                    newpass_dialog.ui.label3.set_property("visible", True)
                    newpass_dialog.ui.pass_entry2.grab_focus()
                elif passwordA == '':
                    newpass_dialog.ui.label3.set_text(_("New password cannot be blank! Please try again."))
                    newpass_dialog.ui.label3.set_property("visible", True)
                    newpass_dialog.ui.pass_entry2.grab_focus()
                elif not self.passfile.check_password(old_password):
                    newpass_dialog.ui.label3.set_text(_("Old password is invalid! Please try again."))
                    newpass_dialog.ui.label3.set_property("visible", True)
                    newpass_dialog.ui.pass_entry1.grab_focus()
                else:
                    self.passfile.new_keys(passwordA)
                    self.set_save_status(True)
                    self.save_db()
                    success = True
            else:
                break

        newpass_dialog.destroy()

    def lock_screen(self):
        self.disable_idle_timeout()
        self.is_locked = True
        self.ui.pasaffe_vbox.reparent(self.ui.empty_window)
        self.ui.lock_vbox.reparent(self.ui.pasaffe_window)
        self.set_menu_sensitive(False)
        self.ui.lock_unlock_button.grab_focus()

    def on_lock_unlock_button_clicked(self, button):
        success = False
        password_dialog = self.PasswordEntryDialog()
        password_dialog.set_transient_for(self)
        password_dialog.set_modal(True)
        while success == False:
            response = password_dialog.run()
            if response == Gtk.ResponseType.OK:
                password = password_dialog.ui.password_entry.get_text()
                success = self.passfile.check_password(password)
                if success == False:
                    password_dialog.ui.password_error_label.set_property("visible", True)
                    password_dialog.ui.password_entry.set_text("")
                    password_dialog.ui.password_entry.grab_focus()
            else:
                password_dialog.destroy()
                return
        password_dialog.destroy()
        self.ui.lock_vbox.reparent(self.ui.lock_window)
        self.ui.pasaffe_vbox.reparent(self.ui.pasaffe_window)
        self.set_menu_sensitive(True)
        self.is_locked = False
        self.set_idle_timeout()

    def on_lock_quit_button_clicked(self, button):
        if self.save_warning() == False:
            Gtk.main_quit()
            return

    def set_menu_sensitive(self, status):
        # There's got to be a better way to do this
        self.ui.mnu_lock.set_sensitive(status)
        self.ui.mnu_chg_password.set_sensitive(status)
        self.ui.mnu_add.set_sensitive(status)
        self.ui.mnu_clone.set_sensitive(status)
        self.ui.mnu_delete.set_sensitive(status)
        self.ui.mnu_find.set_sensitive(status)
        self.ui.url_copy.set_sensitive(status)
        self.ui.username_copy.set_sensitive(status)
        self.ui.password_copy.set_sensitive(status)
        self.ui.mnu_preferences.set_sensitive(status)
        self.ui.mnu_open_url.set_sensitive(status)
        self.ui.mnu_info.set_sensitive(status)

        if status == False:
            self.ui.mnu_display_secrets.set_sensitive(False)
        else:
            self.set_show_password_status()

        if status == True and self.needs_saving == True:
            self.ui.mnu_save.set_sensitive(True)
            self.ui.save.set_sensitive(True)
        else:
            self.ui.mnu_save.set_sensitive(False)
            # Work around issue where button is insensitive, but icon is
            # not greyed out
            self.ui.save.set_sensitive(True)
            self.ui.save.set_sensitive(False)

    def on_add_clicked(self, toolbutton):
        self.add_entry()

    def on_edit_clicked(self, toolbutton):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)
            self.edit_entry(entry_uuid)

    def on_remove_clicked(self, toolbutton):
        self.remove_entry()

    def set_idle_timeout(self):
        if self.idle_id != None:
            GObject.source_remove(self.idle_id)
            self.idle_id == None
        if self.settings.get_boolean('lock-on-idle') == True and self.settings.get_int('idle-timeout') != 0:
            idle_time = int(self.settings.get_int('idle-timeout')*1000*60)
            self.idle_id = GObject.timeout_add(idle_time, self.idle_timeout_reached)

    def idle_timeout_reached(self):
        if self.is_locked == False:
            self.lock_screen()
        GObject.source_remove(self.idle_id)
        self.idle_id = None

    def disable_idle_timeout(self):
        if self.idle_id != None:
            GObject.source_remove(self.idle_id)
            self.idle_id == None

    def set_show_password_status(self):
        visible = self.settings.get_boolean('visible-secrets')

        if visible == True:
            self.ui.mnu_display_secrets.set_sensitive(False)
            # Work around issue where button is insensitive, but icon is
            # not greyed out
            self.ui.display_secrets.set_sensitive(True)
            self.ui.display_secrets.set_sensitive(False)
        else:
            self.ui.mnu_display_secrets.set_sensitive(True)
            self.ui.display_secrets.set_sensitive(True)

    def set_save_status(self, needed=False):
        self.needs_saving = needed
        if needed == True:
            self.set_title("*Pasaffe")
            self.ui.save.set_sensitive(True)
            self.ui.mnu_save.set_sensitive(True)
        else:
            self.set_title("Pasaffe")
            self.ui.save.set_sensitive(False)
            self.ui.mnu_save.set_sensitive(False)

    def get_save_status(self):
        return self.needs_saving
