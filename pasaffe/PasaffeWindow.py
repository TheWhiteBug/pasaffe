# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
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
### END LICENSE

import gettext
from gettext import gettext as _
gettext.textdomain('pasaffe')

from gi.repository import Gio, Gtk  # pylint: disable=E0611
from gi.repository import Gdk, Pango, GLib  # pylint: disable=E0611
import logging
import os
import re
import struct
import sys
import time
import webbrowser

logger = logging.getLogger('pasaffe')

from pasaffe_lib.Window import Window
from pasaffe.AboutPasaffeDialog import AboutPasaffeDialog
from pasaffe.EditDetailsDialog import EditDetailsDialog
from pasaffe.PasswordEntryDialog import PasswordEntryDialog
from pasaffe.SaveChangesDialog import SaveChangesDialog
from pasaffe.NewDatabaseDialog import NewDatabaseDialog
from pasaffe.NewPasswordDialog import NewPasswordDialog
from pasaffe.PreferencesPasaffeDialog import PreferencesPasaffeDialog
from pasaffe_lib.readdb import PassSafeFile
from pasaffe_lib.helpersgui import get_builder

# pylint: disable=E1101

class PathEntry:
    def __init__(self, name, uuid, path):
        self.name = name
        self.uuid = uuid
        self.path = path

    def __cmp__(self, other):
        if self.path == None and other.path == None:
            return 0
        elif self.path == None:
            return -1
        elif other.path == None:
            return 1
        elif not len(self.path) or len(self.path) < len(other.path):
            i = 0
            for path in self.path:
                if not len(path):
                    return 1
                if not len(other.path[i]):
                    return -1
                if path < other.path[i]:
                    return -1
                if path > other.path[i]:
                    return 1
                i += 1
            return 1
        elif not len(other.path) or len(self.path) > len(other.path):
            i = 0
            for path in other.path:
                if not len(path):
                    return -1
                if not len(self.path[i]):
                    return 1
                if path > self.path[i]:
                    return -1
                if path < self.path[i]:
                    return 1
                i += 1
            return -1
        else:
            i = 0
            for path in self.path:
                if not len(path):
                    return 1
                if not len(other.path[i]):
                    return -1
                if path < other.path[i]:
                    return -1
                if path > other.path[i]:
                    return 1
                i += 1
            return 0


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

    def finish_initializing(self, builder, database):  # pylint: disable=E1002
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

        self.connect("delete-event", self.on_delete_event)
        self.ui.textview1.connect("motion-notify-event",
                                  self.textview_event_handler)

        self.set_save_status(False)
        self.passfile = None
        self.is_locked = False
        self.idle_id = None
        self.clipboard_id = None
        self.find_results = []
        self.find_results_index = None
        self.find_value = ""

        if database == None:
            self.database = self.settings.get_string('database-path')
        else:
            self.database = database

        self.settings = Gio.Settings("net.launchpad.pasaffe")
        self.settings.connect('changed', self.on_preferences_changed)

        self.state = Gio.Settings("net.launchpad.pasaffe.state")

        # If database doesn't exists, make a new one
        if os.path.exists(self.database):
            success = self.fetch_password()
        else:
            success = self.new_database()

        if success == False:
            self.connect('event-after', Gtk.main_quit)
        else:
            self.set_window_size()
            self.set_show_password_status()
            self.display_entries()
            self.display_welcome()

        # Set inactivity timer
        self.set_idle_timeout()

    def on_delete_event(self, _widget, _event):
        self.save_window_size()
        return self.save_warning()

    def set_window_size(self):
        width = self.state.get_int('main-size-width')
        height = self.state.get_int('main-size-height')
        split = self.state.get_int('main-split')
        self.ui.pasaffe_window.resize(width, height)
        self.ui.hpaned1.set_position(split)

    def save_window_size(self):
        (width, height) = self.ui.pasaffe_window.get_size()
        split = self.ui.hpaned1.get_position()
        self.state.set_int('main-size-width', width)
        self.state.set_int('main-size-height', height)
        self.state.set_int('main-split', split)

    def set_entry_window_size(self):
        width = self.state.get_int('entry-size-width')
        height = self.state.get_int('entry-size-height')
        self.editdetails_dialog.ui.edit_details_dialog.resize(width, height)

    def save_entry_window_size(self):
        (width, height) = self.editdetails_dialog.ui.edit_details_dialog.get_size()
        self.state.set_int('entry-size-width', width)
        self.state.set_int('entry-size-height', height)

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
                password_a = newdb_dialog.ui.entry1.get_text()
                password_b = newdb_dialog.ui.entry2.get_text()
                if password_a != password_b:
                    newdb_dialog.ui.error_label.set_property("visible", True)
                    newdb_dialog.ui.entry1.grab_focus()
                else:
                    self.passfile = PassSafeFile()
                    self.passfile.new_db(password_a)
                    success = True
            else:
                break

        newdb_dialog.destroy()
        return success

    def find_path(self, paths):
        parent = None

        if paths == None or len(paths) == 0:
            return None

        node = self.ui.liststore1.get_iter_first()

        for path in paths:
            if len(path) == 0:
                return parent
            found = False
            while node != None and not found:
                if self.ui.liststore1.get_value(node, 0) == path:
                    if self.ui.liststore1.iter_has_child(node):
                        parent = node
                        node = self.ui.liststore1.iter_children(node)
                        found = True
                    else:
                        break
                if not found:
                    node = self.ui.liststore1.iter_next(node)
            if not found:
                parent = self.ui.liststore1.append(parent, [path, "pasaffe_treenode."+path])
                node = self.ui.liststore1.iter_children(parent)
        return parent

    def display_entries(self):
        entries = []
        for uuid in self.passfile.records:
            entry = PathEntry(self.passfile.records[uuid][3], uuid, self.passfile.get_folder_list(uuid))
            entries.append(entry)

        self.ui.liststore1.clear()

        # Sort the records alphabetically first
        entries = sorted(entries, key=lambda x:x.name.lower())

        # Then sort on path
        for record in sorted(entries):
            parent = self.find_path(record.path)
            self.ui.liststore1.append(parent, [record.name, record.uuid])
        self.ui.treeview1.expand_all()

    def display_data(self, entry_uuid, show_secrets=False):
        title = self.passfile.records[entry_uuid].get(3)

        url = None
        if 13 in self.passfile.records[entry_uuid]:
            url = "%s\n\n" % self.passfile.records[entry_uuid].get(13)

        contents = ''
        if show_secrets == False and \
           self.settings.get_boolean('only-passwords-are-secret') == False and \
           self.settings.get_boolean('visible-secrets') == False:
            contents += _("Secrets are currently hidden.")
        else:
            if 5 in self.passfile.records[entry_uuid]:
                contents += "%s\n\n" % self.passfile.records[entry_uuid].get(5)
            contents += _("Username: %s\n") % self.passfile.records[entry_uuid].get(4)
            if show_secrets == True or self.settings.get_boolean('visible-secrets') == True:
                contents += _("Password: %s\n\n") % self.passfile.records[entry_uuid].get(6)
            else:
                contents += _("Password: *****\n\n")
            if 12 in self.passfile.records[entry_uuid]:
                last_updated = time.strftime("%a, %d %b %Y %H:%M:%S",
                               time.localtime(struct.unpack("<I",
                               self.passfile.records[entry_uuid][12])[0]))
                contents += _("Last updated: %s\n") % last_updated
            if 8 in self.passfile.records[entry_uuid]:
                pass_updated = time.strftime("%a, %d %b %Y %H:%M:%S",
                               time.localtime(struct.unpack("<I",
                                   self.passfile.records[entry_uuid][8])[0]))
                contents += _("Password updated: %s\n") % pass_updated
        self.fill_display(title, url, contents)

    def display_welcome(self):
        self.fill_display(_("Welcome to Pasaffe!"), None,
                          _("Pasaffe is an easy to use\npassword manager for Gnome."))

    def display_folder(self, folder_name):
        self.fill_display(folder_name, None,
                          _("This is a folder."))

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

    def url_event_handler(self, _tag, _widget, event, _iter):
        # We also used to check event.button == 1 here, but event.button
        # doesn't seem to get set by PyGObject anymore.
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            self.open_url()
        return False

    def textview_event_handler(self, textview, event):
        loc_x, loc_y = textview.window_to_buffer_coords(Gtk.TextWindowType.WIDGET, int(event.x), int(event.y))
        itera = textview.get_iter_at_location(loc_x, loc_y)
        cursor = Gdk.Cursor.new(Gdk.CursorType.XTERM)
        for tag in itera.get_tags():
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
            url = self.passfile.records[entry_uuid].get(13)
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
                if "pasaffe_treenode." in entry_uuid:
                    self.display_folder(treemodel.get_value(treeiter, 0))
                    return
                self.display_data(entry_uuid)
                # Reset the show password button and menu item
                self.ui.display_secrets.set_active(False)
                self.ui.mnu_display_secrets.set_active(False)

    def on_treeview1_button_press_event(self, treeview, event):
        if event.button == 3:
            loc_x = int(event.x)
            loc_y = int(event.y)
            event_time = event.time
            pthinfo = treeview.get_path_at_pos(loc_x, loc_y)
            if pthinfo is not None:
                path, col, _cellx, _celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor(path, col, 0)
                self.ui.menu_popup.popup(None, None, None, None, 3, event_time)

    def add_entry(self):
        self.disable_idle_timeout()

        # Make sure dialog isn't already open
        if self.editdetails_dialog is not None:
            self.editdetails_dialog.present()
            return

        uuid_hex = self.passfile.new_entry()

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
        record_list = (2, 3, 4, 5, 6, 13)
        self.disable_idle_timeout()

        # Make sure dialog isn't already open
        if self.editdetails_dialog is not None:
            self.editdetails_dialog.present()
            return

        uuid_hex = self.passfile.new_entry()

        for record_type in record_list:
            if record_type in self.passfile.records[entry_uuid]:
                self.passfile.records[uuid_hex][record_type] = self.passfile.records[entry_uuid][record_type]

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
        if "pasaffe_treenode." in entry_uuid:
            return None
        record_dict = {2: 'folder_entry',
                       3: 'name_entry',
                       4: 'username_entry',
                       5: 'notes_buffer',
                       6: 'password_entry',
                       13: 'url_entry'}

        # Make sure dialog isn't already open
        if self.editdetails_dialog is not None:
            self.editdetails_dialog.present()
            return

        if self.EditDetailsDialog is not None:
            self.disable_idle_timeout()
            self.editdetails_dialog = self.EditDetailsDialog()

            for record_type, widget_name in record_dict.items():
                if record_type in self.passfile.records[entry_uuid]:
                    self.editdetails_dialog.builder.get_object(widget_name).set_text(self.passfile.records[entry_uuid][record_type])

            self.set_entry_window_size()
            response = self.editdetails_dialog.run()
            if response == Gtk.ResponseType.OK:
                data_changed = False
                for record_type, widget_name in record_dict.items():
                    if record_type == 5:
                        new_value = self.editdetails_dialog.builder.get_object(widget_name).get_text(self.editdetails_dialog.builder.get_object(widget_name).get_start_iter(), self.editdetails_dialog.builder.get_object(widget_name).get_end_iter(), True)
                    else:
                        new_value = self.editdetails_dialog.builder.get_object(widget_name).get_text()

                    if (record_type == 5 or record_type == 13) and new_value == "" and record_type in self.passfile.records[entry_uuid]:
                        del self.passfile.records[entry_uuid][record_type]
                    elif self.passfile.records[entry_uuid].get(record_type, "") != new_value:
                        data_changed = True
                        self.passfile.records[entry_uuid][record_type] = new_value
                        # Reset the entire tree on name and path changes
                        if record_type in [2, 3]:
                            self.display_entries()

                        # Update the password changed date
                        if record_type == 6:
                            self.passfile.update_password_time(entry_uuid)

                if data_changed == True:
                    self.set_save_status(True)
                    self.passfile.update_modification_time(entry_uuid)
                    if self.settings.get_boolean('auto-save') == True:
                        self.save_db()

            self.save_entry_window_size()
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

        del self.passfile.records[entry_uuid]

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
        nchild = model.iter_n_children(parent)
        return nchild and model.iter_nth_child(parent, nchild - 1)

    def on_treeview1_row_activated(self, treeview, _path, _view_column):
        treemodel, treeiter = treeview.get_selection().get_selected()
        entry_uuid = treemodel.get_value(treeiter, 1)
        self.edit_entry(entry_uuid)

    def save_db(self):
        if self.get_save_status() == True:
            self.passfile.writefile(self.database, backup=True)
            self.set_save_status(False)

    def on_save_clicked(self, _toolbutton):
        self.set_idle_timeout()
        self.save_db()

    def on_mnu_save_activate(self, _menuitem):
        self.set_idle_timeout()
        self.save_db()

    def on_mnu_close_activate(self, _menuitem):
        self.disable_idle_timeout()
        if self.settings.get_boolean('auto-save') == True:
            self.save_db()
        if self.save_warning() == False:
            Gtk.main_quit()
        else:
            self.set_idle_timeout()

    def on_mnu_clone_activate(self, _menuitem):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)
            self.clone_entry(entry_uuid)

    def on_username_copy_activate(self, _menuitem):
        self.copy_selected_entry_item(4)

    def on_password_copy_activate(self, _menuitem):
        self.copy_selected_entry_item(6)

    def on_url_copy_activate(self, _menuitem):
        self.copy_selected_entry_item(13)

    def on_copy_username_clicked(self, _toolbutton):
        self.copy_selected_entry_item(4)

    def on_copy_password_clicked(self, _toolbutton):
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

            if item in self.passfile.records[entry_uuid]:
                for atom in [Gdk.SELECTION_CLIPBOARD, Gdk.SELECTION_PRIMARY]:
                    clipboard = Gtk.Clipboard.get(atom)
                    clipboard.set_text(self.passfile.records[entry_uuid][item],
                                       len(self.passfile.records[entry_uuid][item]))
                    clipboard.store()
                self.set_clipboard_timeout()

    def on_mnu_add_activate(self, _menuitem):
        self.add_entry()

    def on_mnu_edit1_activate(self, _menuitem):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)
            self.edit_entry(entry_uuid)

    def on_mnu_delete_activate(self, _menuitem):
        self.remove_entry()

    def on_mnu_lock_activate(self, _menuitem):
        self.lock_screen()

    def on_mnu_info_activate(self, _menuitem):
        information = _('<big><b>Database Information</b></big>\n\n')
        information += _('Number of entries: %s\n') % len(self.passfile.records)
        information += _('Database version: %s\n') % self.passfile.get_database_version_string()
        if self.passfile.get_saved_name():
            information += _('Last saved by: %s\n') % self.passfile.get_saved_name()
        if self.passfile.get_saved_host():
            information += _('Last saved on host: %s\n') % self.passfile.get_saved_host()
            information += _('Last save date: %s\n') % self.passfile.get_saved_date_string()
        if self.passfile.get_saved_application():
            information += _('Application used: %s\n') % self.passfile.get_saved_application()

        info_dialog = Gtk.MessageDialog(type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK)
        info_dialog.set_markup(information)
        info_dialog.run()
        info_dialog.destroy()

    def on_mnu_open_url_activate(self, _menuitem):
        self.open_url()

    def on_mnu_find_toggled(self, menuitem):
        is_active = menuitem.get_active()
        self.show_find(is_active)
        self.ui.toolbar_find.set_active(is_active)

    def on_toolbar_find_toggled(self, toolbutton):
        is_active = toolbutton.get_active()
        self.show_find(is_active)
        self.ui.mnu_find.set_active(is_active)

    def on_find_btn_close_clicked(self, _button):
        self.show_find(False)
        self.ui.toolbar_find.set_active(False)
        self.ui.mnu_find.set_active(False)

    def on_find_btn_prev_clicked(self, _button):
        self.update_find_results()
        self.goto_next_find_result(backwards=True)

    def on_find_btn_next_clicked(self, _button):
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

        record_list = (3, 5, 13)
        pat = re.compile(find, re.IGNORECASE)
        results = []

        for uuid in self.passfile.records:
            found = False
            for record_type in record_list:
                if record_type in self.passfile.records[uuid]:
                    if pat.search(self.passfile.records[uuid].get(record_type)):
                        found = True
                        break

            if found == True:
                results.append([self.passfile.records[uuid][3], uuid])

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

    def on_find_entry_activate(self, _entry):
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

    def on_open_url_clicked(self, _toolbutton):
        self.open_url()

    def on_mnu_chg_password_activate(self, _menuitem):
        success = False
        newpass_dialog = self.NewPasswordDialog()
        while success == False:
            response = newpass_dialog.run()
            if response == Gtk.ResponseType.OK:
                old_password = newpass_dialog.ui.pass_entry1.get_text()
                password_a = newpass_dialog.ui.pass_entry2.get_text()
                password_b = newpass_dialog.ui.pass_entry3.get_text()
                if password_a != password_b:
                    newpass_dialog.ui.label3.set_text(_("Passwords don't match! Please try again."))
                    newpass_dialog.ui.label3.set_property("visible", True)
                    newpass_dialog.ui.pass_entry2.grab_focus()
                elif password_a == '':
                    newpass_dialog.ui.label3.set_text(_("New password cannot be blank! Please try again."))
                    newpass_dialog.ui.label3.set_property("visible", True)
                    newpass_dialog.ui.pass_entry2.grab_focus()
                elif not self.passfile.check_password(old_password):
                    newpass_dialog.ui.label3.set_text(_("Old password is invalid! Please try again."))
                    newpass_dialog.ui.label3.set_property("visible", True)
                    newpass_dialog.ui.pass_entry1.grab_focus()
                else:
                    self.passfile.new_keys(password_a)
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

    def on_lock_unlock_button_clicked(self, _button):
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

    def on_add_clicked(self, _toolbutton):
        self.add_entry()

    def on_edit_clicked(self, _toolbutton):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter != None:
            entry_uuid = treemodel.get_value(treeiter, 1)
            self.edit_entry(entry_uuid)

    def on_remove_clicked(self, _toolbutton):
        self.remove_entry()

    def set_idle_timeout(self):
        if self.idle_id != None:
            GLib.source_remove(self.idle_id)
            self.idle_id = None
        if self.settings.get_boolean('lock-on-idle') == True and self.settings.get_int('idle-timeout') != 0:
            idle_time = int(self.settings.get_int('idle-timeout') * 1000 * 60)
            self.idle_id = GLib.timeout_add(idle_time, self.idle_timeout_reached)

    def idle_timeout_reached(self):
        if self.is_locked == False:
            self.lock_screen()
        if self.idle_id != None:
            GLib.source_remove(self.idle_id)
            self.idle_id = None

    def disable_idle_timeout(self):
        if self.idle_id != None:
            GLib.source_remove(self.idle_id)
            self.idle_id = None

    def set_clipboard_timeout(self):
        if self.clipboard_id != None:
            GLib.source_remove(self.clipboard_id)
            self.clipboard_id = None
        if self.settings.get_int('clipboard-timeout') != 0:
            clipboard_time = int(self.settings.get_int('clipboard-timeout') * 1000)
            self.clipboard_id = GLib.timeout_add(clipboard_time,
                                                    self.clipboard_timeout_reached)

    def clipboard_timeout_reached(self):
        if self.clipboard_id != None:
            GLib.source_remove(self.clipboard_id)
            self.clipboard_id = None
        for atom in [Gdk.SELECTION_CLIPBOARD, Gdk.SELECTION_PRIMARY]:
            clipboard = Gtk.Clipboard.get(atom)
            clipboard.set_text("", 0)
            clipboard.store()

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
