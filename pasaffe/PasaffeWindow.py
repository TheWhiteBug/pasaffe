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

import gettext
from gettext import gettext as _
gettext.textdomain('pasaffe')

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, Gtk  # pylint: disable=E0611
from gi.repository import Gdk, Pango, GLib  # pylint: disable=E0611
import logging
import os
import webbrowser

logger = logging.getLogger('pasaffe')

from pasaffe_lib.Window import Window
from pasaffe.AboutPasaffeDialog import AboutPasaffeDialog
from pasaffe.EditDetailsDialog import EditDetailsDialog
from pasaffe.EditFolderDialog import EditFolderDialog
from pasaffe.PasswordEntryDialog import PasswordEntryDialog
from pasaffe.SaveChangesDialog import SaveChangesDialog
from pasaffe.NewDatabaseDialog import NewDatabaseDialog
from pasaffe.NewPasswordDialog import NewPasswordDialog
from pasaffe.PreferencesPasaffeDialog import PreferencesPasaffeDialog
from pasaffe_lib.readdb import PassSafeFile
from pasaffe_lib.helpersgui import get_builder
from pasaffe_lib.helpers import folder_list_to_field
from pasaffe_lib.helpers import field_to_folder_list
from pasaffe_lib.helpers import folder_list_to_path
from pasaffe_lib.helpers import folder_path_to_list
from pasaffe_lib.helpers import PathEntry


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
        self.EditFolderDialog = EditFolderDialog
        self.editfolder_dialog = None
        self.PreferencesDialog = PreferencesPasaffeDialog
        self.PasswordEntryDialog = PasswordEntryDialog
        self.SaveChangesDialog = SaveChangesDialog
        self.NewDatabaseDialog = NewDatabaseDialog
        self.NewPasswordDialog = NewPasswordDialog

        self.connect("delete-event", self.on_delete_event)
        self.ui.textview1.connect("motion-notify-event",
                                  self.textview_event_handler)

        self.passfile = None
        self.is_locked = False
        self.idle_id = None
        self.clipboard_id = None
        self.folder_state = {}

        if database is None:
            self.database = self.settings.get_string('database-path')
        else:
            self.database = database
        self.default_database = database is None

        self.set_save_status(False)

        self.settings = Gio.Settings.new("net.launchpad.pasaffe")
        self.settings.connect('changed', self.on_preferences_changed)

        self.state = Gio.Settings.new("net.launchpad.pasaffe.state")

        # If database doesn't exists, make a new one
        if os.path.exists(self.database):
            success = self.fetch_password()
        else:
            success = self.new_database()

        if success is False:
            self.connect('event-after', Gtk.main_quit)
        else:
            self.set_window_size()
            self.set_show_password_status()
            self.display_entries()
            self.set_initial_tree_expansion()
            self.display_welcome()
            self.ui.treeview1.grab_focus()

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
        (width, height) = \
            self.editdetails_dialog.ui.edit_details_dialog.get_size()
        self.state.set_int('entry-size-width', width)
        self.state.set_int('entry-size-height', height)

    def set_folder_window_size(self):
        width = self.state.get_int('folder-size-width')
        height = self.state.get_int('folder-size-height')
        self.editfolder_dialog.ui.edit_folder_dialog.resize(width, height)

    def save_folder_window_size(self):
        (width, height) = \
            self.editfolder_dialog.ui.edit_folder_dialog.get_size()
        self.state.set_int('folder-size-width', width)
        self.state.set_int('folder-size-height', height)

    def save_warning(self):
        if self.get_save_status() is True:
            savechanges_dialog = self.SaveChangesDialog()
            savechanges_dialog.set_transient_for(self)
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
        password_dialog.set_transient_for(self)
        while self.passfile is None:
            response = password_dialog.run()
            if response == Gtk.ResponseType.OK:
                password = password_dialog.ui.password_entry.get_text()
                try:
                    self.passfile = PassSafeFile(self.database, password)
                except ValueError:
                    password_dialog.ui.password_error_label.set_property(
                        "visible", True)
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
        newdb_dialog.set_transient_for(self)
        while success is False:
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

    def create_folders(self, folders):
        parent = None

        if not folders:
            return None

        node = self.ui.liststore1.get_iter_first()

        for folder in folders:
            if not folder:
                return parent
            found = False
            while node is not None and not found:
                if (self.ui.liststore1.get_value(node, 1) == folder) and \
                   ("pasaffe_treenode." in self.ui.liststore1.get_value(
                           node, 2)):
                    found = True
                    parent = node
                    if self.ui.liststore1.iter_has_child(node):
                        node = self.ui.liststore1.iter_children(node)
                    else:
                        break
                if not found:
                    node = self.ui.liststore1.iter_next(node)
            if not found:
                parent = self.ui.liststore1.append(parent,
                                                   ["inode-directory-symbolic",
                                                    folder,
                                                    "pasaffe_treenode." +
                                                    folder])
                node = self.ui.liststore1.iter_children(parent)
        return parent

    def _fixup_folders(self, folder_list):
        if folder_list:
            return [_("[Untitled]") if x == "" else x for x in folder_list]

        return None

    def display_entries(self):
        entries = []

        # Add empty folders first
        for folder in self.passfile.get_empty_folders():
            folder = self._fixup_folders(folder)
            entry = PathEntry("", "", folder)
            entries.append(entry)

        # Then add records
        for uuid in self.passfile.records:
            title = self.passfile.get_title(uuid)
            username = self.passfile.get_username(uuid)
            folder = self._fixup_folders(self.passfile.get_folder_list(uuid))
            # Empty names don't display properly in tree
            if title in [None, ""]:
                title = _("[Untitled]")
            elif username not in [None, ""]:
                title = title + " [" + username + "]"
            entry = PathEntry(title,
                              uuid,
                              folder)
            entries.append(entry)

        self.ui.liststore1.clear()

        # Then sort and add
        for record in sorted(entries):
            parent = self.create_folders(record.path)
            if record.name != "":
                self.ui.liststore1.append(parent,
                                          ["text-x-generic-symbolic",
                                           record.name,
                                           record.uuid])
        self.set_tree_expansion()
        self.set_menu_for_entry(False)

        # enable drag and drop
        dnd_targets = [('MY_TREE_MODEL_ROW',
                        Gtk.TargetFlags.SAME_WIDGET, 0)]

        self.ui.treeview1.enable_model_drag_source(
            Gdk.ModifierType.BUTTON1_MASK,
            dnd_targets,
            Gdk.DragAction.DEFAULT |
            Gdk.DragAction.MOVE)
        self.ui.treeview1.enable_model_drag_dest(dnd_targets,
                                                 Gdk.DragAction.DEFAULT)
        self.ui.treeview1.connect("drag_data_received",
                                  self.drag_data_received_data)

    def set_tree_expansion(self):
        folders = list(self.folder_state.copy().keys())
        folders.sort()
        for folder in folders:
            folder_iter = self.search_folder(field_to_folder_list(folder))
            if folder_iter is not None:
                path = self.ui.treeview1.get_model().get_path(folder_iter)
                if self.folder_state[folder] is True:
                    self.ui.treeview1.expand_row(path, False)
                else:
                    self.ui.treeview1.collapse_row(path)

    def set_folder_state(self, folder, state):
        folder_field = folder_list_to_field(folder)
        self.folder_state[folder_field] = state

    def set_initial_tree_expansion(self):
        entries = []

        expansion_status = self.passfile.get_tree_status()

        config = self.settings.get_string('tree-expansion')
        if config == "collapsed":
            self.ui.treeview1.collapse_all()
            return
        elif config == "expanded" or expansion_status is None:
            self.ui.treeview1.expand_all()
            return

        for folder in self.passfile.get_all_folders():
            entry = PathEntry("", "", folder)
            entries.append(entry)

        index = 0
        for record in sorted(entries):
            if index + 1 > len(expansion_status):
                return
            folder_iter = self.search_folder(record.path)
            if folder_iter is not None:
                path = self.ui.treeview1.get_model().get_path(folder_iter)
                if expansion_status[index] == "1":
                    # FIXME: For some reason, GtkTreeView will not expand
                    # a folder inside a folder that is collapsed. Need to
                    # find a workaround.
                    self.ui.treeview1.expand_row(path, False)
            index += 1

    def save_tree_expansion(self):
        entries = []
        expansion_status = ""

        for folder in self.passfile.get_all_folders():
            entry = PathEntry("", "", folder)
            entries.append(entry)

        for record in sorted(entries):
            if self.folder_state.get(folder_list_to_field(record.path),
                                     False) is True:
                expansion_status += "1"
            else:
                expansion_status += "0"

        if expansion_status == "":
            expansion_status = None

        self.passfile.set_tree_status(expansion_status)

    def drag_data_received_data(self, treeview, _context, x, y, _selection,
                                _info, _etime):
        sourcemodel, sourceiter = treeview.get_selection().get_selected()
        source_uuid = sourcemodel.get_value(sourceiter, 2)

        destmodel = treeview.get_model()
        drop_info = treeview.get_dest_row_at_pos(x, y)
        if drop_info:
            path, position = drop_info
            destiter = destmodel.get_iter(path)
            dest_uuid = destmodel.get_value(destiter, 2)

            # Ignore entries as drop destinations
            if "pasaffe_treenode." not in dest_uuid:
                return

            if ((position == Gtk.TreeViewDropPosition.INTO_OR_BEFORE) or
                    (position == Gtk.TreeViewDropPosition.INTO_OR_AFTER)):

                new_parents = self.get_folders_from_iter(destmodel, destiter)

                if "pasaffe_treenode." in source_uuid:
                    current_folders = self.get_folders_from_iter(sourcemodel,
                                                                 sourceiter)
                    parent_folders = current_folders[:-1]

                    # Bail out if the folder is dragged onto itself
                    if current_folders == new_parents:
                        return

                    # Bail out if we're trying to drag a folder into a
                    # subdirectory of itself
                    if current_folders == new_parents[:len(current_folders)]:
                        return

                    if new_parents != parent_folders:
                        new_folders = new_parents[:]
                        new_folders.append(current_folders[-1:][0])
                        old_folders = current_folders[:]

                        self.passfile.rename_folder_list(old_folders,
                                                         new_folders)

                        self.display_entries()
                        self.goto_folder(new_folders)

                        self.set_save_status(True)
                        if self.settings.get_boolean('auto-save') is True:
                            self.save_db()
                else:
                    parent_folders = self.passfile.get_folder_list(source_uuid)
                    if new_parents != parent_folders:
                        self.passfile.remove_empty_folder(new_parents)
                        self.passfile.add_empty_folder(parent_folders)
                        self.passfile.update_folder_list(source_uuid,
                                                         new_parents)

                        self.passfile.update_modification_time(source_uuid)

                        self.display_entries()
                        self.goto_uuid(source_uuid)

                        self.set_save_status(True)
                        if self.settings.get_boolean('auto-save') is True:
                            self.save_db()

                self.set_idle_timeout()
                self.update_find_results(force=True)

    def goto_uuid(self, uuid):
        item = self.search_uuid(uuid)

        if item is not None:
            treemodel = self.ui.treeview1.get_model()

            # See if we need to expand some folders
            parent = treemodel.iter_parent(item)
            while parent is not None:
                path = treemodel.get_path(parent)
                self.ui.treeview1.expand_row(path, False)
                parent = treemodel.iter_parent(parent)

            if "pasaffe_treenode." in uuid:
                self.display_folder(treemodel.get_value(item, 1))
            else:
                self.display_data(uuid)
            path = treemodel.get_path(item)
            self.ui.treeview1.scroll_to_cell(path)
            self.ui.treeview1.set_cursor(path)

    def goto_folder(self, folders):
        item = self.search_folder(folders)
        if item is not None:
            self.display_folder(self.ui.liststore1.get_value(item, 1))
            path = self.ui.treeview1.get_model().get_path(item)
            self.ui.treeview1.scroll_to_cell(path)
            self.ui.treeview1.set_cursor(path)

    def search_uuid(self, uuid, item=None, toplevel=True):
        if toplevel is True:
            item = self.ui.treeview1.get_model().get_iter_first()
        while item:
            if self.ui.liststore1.get_value(item, 2) == uuid:
                return item
            result = self.search_uuid(
                uuid, self.ui.treeview1.get_model().iter_children(item), False)
            if result:
                return result
            item = self.ui.treeview1.get_model().iter_next(item)
        return None

    def search_folder(self, folders):
        parent = None

        if not folders:
            return None

        node = self.ui.liststore1.get_iter_first()

        for folder in folders:
            if not folder:
                return parent
            found = False
            while node is not None and not found:
                if (self.ui.liststore1.get_value(node, 1) == folder) and \
                   ("pasaffe_treenode." in self.ui.liststore1.get_value(
                           node, 2)):
                    found = True
                    parent = node
                    if self.ui.liststore1.iter_has_child(node):
                        node = self.ui.liststore1.iter_children(node)
                    else:
                        break
                if not found:
                    node = self.ui.liststore1.iter_next(node)
            if not found:
                return None
        return parent

    def find_prev_iter(self, uuid, item=None, toplevel=True, prev_item=None):
        if toplevel is True:
            item = self.ui.treeview1.get_model().get_iter_first()
        if item is None:
            return prev_item, None
        while item:
            if self.ui.liststore1.get_value(item, 2) == uuid:
                return prev_item, item
            prev_item, result = self.find_prev_iter(
                uuid, self.ui.treeview1.get_model().iter_children(item),
                False, item)
            if result:
                return prev_item, result
            prev_item = item
            item = self.ui.treeview1.get_model().iter_next(item)
        return item, None

    def display_data(self, entry_uuid, show_secrets=False):
        ttt = self.get_texttagtable()
        data_buffer = Gtk.TextBuffer.new(ttt)

        # title
        data_buffer.insert(data_buffer.get_start_iter(), "\n")
        title = self.passfile.get_title(entry_uuid)
        # Fixup Empty names
        if title in [None, ""]:
            title = _("[Untitled]")

        data_buffer.insert_with_tags(data_buffer.get_end_iter(),
                                     title,
                                     ttt.lookup('title'))
        data_buffer.insert(data_buffer.get_end_iter(), "\n\n")

        # url
        if self.passfile.get_url(entry_uuid):
            data_buffer.insert_with_tags(data_buffer.get_end_iter(),
                                         _("URL:") + "\n",
                                         ttt.lookup('section'))
            data_buffer.insert_with_tags(
                data_buffer.get_end_iter(),
                self.passfile.get_url(entry_uuid),
                ttt.lookup('url'))
            data_buffer.insert(data_buffer.get_end_iter(), "\n\n")

        if show_secrets is False and \
           self.settings.get_boolean('only-passwords-are-secret') is False \
           and self.settings.get_boolean('visible-secrets') is False:
            data_buffer.insert(data_buffer.get_end_iter(),
                               _("Secrets are currently hidden."))
        else:
            # username
            data_buffer.insert_with_tags(data_buffer.get_end_iter(),
                                         _("Username:") + "\n",
                                         ttt.lookup('section'))
            data_buffer.insert(data_buffer.get_end_iter(),
                               self.passfile.get_username(entry_uuid))
            data_buffer.insert(data_buffer.get_end_iter(), "\n\n")

            # password
            data_buffer.insert_with_tags(data_buffer.get_end_iter(),
                                         _("Password:") + "\n",
                                         ttt.lookup('section'))

            if show_secrets is True or \
                    self.settings.get_boolean('visible-secrets') is True:
                data_buffer.insert(data_buffer.get_end_iter(),
                                   self.passfile.get_password(entry_uuid))
            else:
                data_buffer.insert(data_buffer.get_end_iter(), '*****')
            data_buffer.insert(data_buffer.get_end_iter(), "\n\n")

            # notes
            if self.passfile.get_notes(entry_uuid):
                data_buffer.insert_with_tags(data_buffer.get_end_iter(),
                                             _("Notes:") + "\n",
                                             ttt.lookup('section'))
                data_buffer.insert(data_buffer.get_end_iter(),
                                   self.passfile.get_notes(entry_uuid))
                data_buffer.insert(data_buffer.get_end_iter(), "\n\n")

            # modification time
            last_updated = self.passfile.get_modification_time(entry_uuid)
            if last_updated is not None:
                data_buffer.insert_with_tags(data_buffer.get_end_iter(),
                                             _("Last updated:") + "\n",
                                             ttt.lookup('section'))
                data_buffer.insert(data_buffer.get_end_iter(),
                                   last_updated)
                data_buffer.insert(data_buffer.get_end_iter(), "\n")

            # password updated time
            pass_updated = self.passfile.get_password_time(entry_uuid)
            if pass_updated is not None:
                data_buffer.insert_with_tags(data_buffer.get_end_iter(),
                                             _("Password updated:") + "\n",
                                             ttt.lookup('section'))
                data_buffer.insert(data_buffer.get_end_iter(),
                                   pass_updated)
                data_buffer.insert(data_buffer.get_end_iter(), "\n\n")

        self.ui.textview1.set_buffer(data_buffer)

        self.set_menu_for_entry(True)

        # Now disable menus for blank entries
        if self.passfile.get_url(entry_uuid) in [None, ""]:
            self.ui.url_copy.set_sensitive(False)
            self.ui.mnu_open_url.set_sensitive(False)
            self.ui.url_copy1.set_sensitive(False)
            self.ui.open_url.set_sensitive(False)

        if self.passfile.get_username(entry_uuid) in [None, ""]:
            self.ui.username_copy.set_sensitive(False)
            self.ui.username_copy1.set_sensitive(False)
            self.ui.copy_username.set_sensitive(False)

        if self.passfile.get_password(entry_uuid) in [None, ""]:
            self.ui.password_copy.set_sensitive(False)
            self.ui.password_copy1.set_sensitive(False)
            self.ui.copy_password.set_sensitive(False)

    def display_welcome(self):
        ttt = self.get_texttagtable()
        data_buffer = Gtk.TextBuffer.new(ttt)

        data_buffer.insert(data_buffer.get_start_iter(), "\n")
        data_buffer.insert_with_tags(data_buffer.get_end_iter(),
                                     _("Welcome to Pasaffe!"),
                                     ttt.lookup('title'))
        data_buffer.insert(data_buffer.get_end_iter(), "\n\n")

        data_buffer.insert(data_buffer.get_end_iter(),
                           _("Pasaffe is an easy to use\npassword manager."))

        self.ui.textview1.set_buffer(data_buffer)

    def display_folder(self, folder_name):
        ttt = self.get_texttagtable()
        data_buffer = Gtk.TextBuffer.new(ttt)

        data_buffer.insert(data_buffer.get_start_iter(), "\n")
        data_buffer.insert_with_tags(data_buffer.get_end_iter(),
                                     folder_name,
                                     ttt.lookup('title'))
        data_buffer.insert(data_buffer.get_end_iter(), "\n\n")

        data_buffer.insert(data_buffer.get_end_iter(),
                           _("This is a folder."))

        self.ui.textview1.set_buffer(data_buffer)
        self.set_menu_for_entry(False)

    def get_texttagtable(self):
        texttagtable = Gtk.TextTagTable()
        texttag_big = Gtk.TextTag.new("title")
        texttag_big.set_property("weight", Pango.Weight.BOLD)
        texttag_big.set_property("size", 14 * Pango.SCALE)
        texttagtable.add(texttag_big)

        texttag_section = Gtk.TextTag.new("section")
        texttag_section.set_property("weight", Pango.Weight.BOLD)
        texttagtable.add(texttag_section)

        texttag_url = Gtk.TextTag.new("url")
        texttag_url.set_property("foreground", "blue")
        texttag_url.set_property("underline", Pango.Underline.SINGLE)
        texttag_url.connect("event", self.url_event_handler)
        texttagtable.add(texttag_url)

        return texttagtable

    def url_event_handler(self, _tag, _widget, event, _iter):
        # We also used to check event.button == 1 here, but event.button
        # doesn't seem to get set by PyGObject anymore.
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            self.open_url()
        return False

    def textview_event_handler(self, textview, event):
        loc_x, loc_y = textview.window_to_buffer_coords(
            Gtk.TextWindowType.WIDGET, int(event.x), int(event.y))

        # Fix dumb Gtk 3.20 API change
        try:
            itera = textview.get_iter_at_location(loc_x, loc_y)
            tags = itera.get_tags()
        except AttributeError:
            (_over, itera) = textview.get_iter_at_location(loc_x, loc_y)
            tags = itera.get_tags()

        cursor = Gdk.Cursor.new(Gdk.CursorType.XTERM)
        for tag in tags:
            if tag.get_property('name') == 'url':
                cursor = Gdk.Cursor.new(Gdk.CursorType.HAND2)
                break
        textview.get_window(Gtk.TextWindowType.TEXT).set_cursor(cursor)
        return False

    def open_url(self):
        url = None
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter is not None:
            entry_uuid = treemodel.get_value(treeiter, 2)

            # Bail out of we're a folder
            if "pasaffe_treenode." in entry_uuid:
                return

            url = self.passfile.get_url(entry_uuid)
        if url is not None:
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
                entry_uuid = treemodel.get_value(treeiter, 2)
                if "pasaffe_treenode." in entry_uuid:
                    self.display_folder(treemodel.get_value(treeiter, 1))
                else:
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

                if not Gtk.check_version(3, 22, 0):
                    self.ui.menu_popup.popup_at_pointer(event)
                else:
                    self.ui.menu_popup.popup(None, None, None, None, 3, event_time)

    def add_entry(self):
        self.disable_idle_timeout()

        # Make sure dialog isn't already open
        if self.editdetails_dialog is not None:
            self.editdetails_dialog.present()
            return

        uuid_hex = self.passfile.new_entry()

        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()

        folder = None
        if treeiter is not None:
            folder = self.get_folders_from_iter(treemodel, treeiter)

        if folder is not None:
            # expand folder
            path = self.ui.treeview1.get_model().get_path(treeiter)
            self.ui.treeview1.expand_row(path, False)

            self.passfile.update_folder_list(uuid_hex, folder)

        response = self.edit_entry(uuid_hex, True)
        if response != Gtk.ResponseType.OK:
            self.delete_entry(uuid_hex, save=False)
        else:
            self.display_entries()
            self.goto_uuid(uuid_hex)
            self.set_save_status(True)
            if self.settings.get_boolean('auto-save') is True:
                self.save_db()
        self.set_idle_timeout()
        self.update_find_results(force=True)

    def add_folder(self):
        self.disable_idle_timeout()

        # Make sure dialog isn't already open
        if self.editfolder_dialog is not None:
            self.editfolder_dialog.present()
            return

        # Get currently selected folder
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter is not None:
            entry_uuid = treemodel.get_value(treeiter, 2)
            if "pasaffe_treenode." not in entry_uuid:
                treeiter = None

        # TODO: make sure folder name is unique in same level

        new_iter = self.ui.liststore1.append(treeiter,
                                             ['inode-directory-symbolic',
                                              _('New Folder'),
                                              "pasaffe_treenode.New Folder"])
        if treeiter is not None:
            path = self.ui.treeview1.get_model().get_path(treeiter)
            self.ui.treeview1.expand_row(path, False)

        self.ui.treeview1.get_selection().select_iter(new_iter)
        self.display_folder(self.ui.liststore1.get_value(new_iter, 1))

        new_folder = self.get_folders_from_iter(treemodel, new_iter)
        response = self.edit_folder(self.ui.liststore1, new_iter, True)

        if response != Gtk.ResponseType.OK:
            self.delete_folder(new_folder, save=False)

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
                self.passfile.records[uuid_hex][record_type] = \
                    self.passfile.records[entry_uuid][record_type]

        response = self.edit_entry(uuid_hex)
        if response != Gtk.ResponseType.OK:
            self.delete_entry(uuid_hex, save=False)
        else:
            self.display_entries()
            self.goto_uuid(uuid_hex)
            self.set_save_status(True)
            if self.settings.get_boolean('auto-save') is True:
                self.save_db()
        self.set_idle_timeout()
        self.update_find_results(force=True)

    def remove_entry(self):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter is not None:
            entry_uuid = treemodel.get_value(treeiter, 2)
            entry_name = treemodel.get_value(treeiter, 1)

            information = \
                _('<big><b>Are you sure you wish to'
                  ' remove "%s"?</b></big>\n\n') % \
                    GLib.markup_escape_text(entry_name)
            information += _('Contents of the entry will be lost.\n')

            info_dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO)
            info_dialog.set_markup(information)
            result = info_dialog.run()
            info_dialog.destroy()

            if result == Gtk.ResponseType.YES:
                self.delete_entry(entry_uuid)

    def remove_folder(self):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter is not None:
            folder_name = treemodel.get_value(treeiter, 1)

            information = \
                _('<big><b>Are you sure you wish'
                  ' to remove folder "%s"?</b></big>\n\n') % \
                    GLib.markup_escape_text(folder_name)
            information += _('All entries in this folder will be lost.\n')

            info_dialog = Gtk.MessageDialog(
                transient_for=self,
                modal=True,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO)
            info_dialog.set_markup(information)
            result = info_dialog.run()
            info_dialog.destroy()

            if result == Gtk.ResponseType.YES:
                folder = self.get_folders_from_iter(treemodel, treeiter)
                self.delete_folder(folder)

    def populate_folders(self, liststore, combobox, default=None):

        folders = [["/"]]
        for folder in self.passfile.get_all_folders():
            for index in range(len(folder)):
                folder_path = [folder_list_to_path(folder, index)]
                if folder_path not in folders:
                    folders.append(folder_path)

        folders.sort()

        for folder in folders:
            liststore.append(folder)

        if default is not None:
            item = self.search_folder_ui(liststore,
                                         folder_list_to_path(default))
            if item is not None:
                combobox.set_active_iter(item)

    def search_folder_ui(self, liststore, folder):
        item = liststore.get_iter_first()
        while item:
            if liststore.get_value(item, 0) == folder:
                return item
            item = liststore.iter_next(item)
        return None

    def edit_entry(self, entry_uuid, new_entry=False):
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
            if new_entry is True:
                title = self.editdetails_dialog.builder.get_object('title')
                title.set_markup(_("<big><b>New entry</b></big>"))

            for record_type, widget_name in list(record_dict.items()):
                # Handle folders separately
                if record_type == 2:
                    liststore = \
                        self.editdetails_dialog.builder.get_object(
                            'liststore1')
                    combobox = \
                        self.editdetails_dialog.builder.get_object(
                            'folder_combo')
                    if self.passfile.get_folder_list(entry_uuid):
                        self.populate_folders(
                            liststore,
                            combobox,
                            self.passfile.get_folder_list(entry_uuid))
                    else:
                        self.populate_folders(liststore, combobox, [])
                elif record_type == 3:
                    self.editdetails_dialog.builder.get_object(
                        widget_name).set_text(
                            self.passfile.get_title(entry_uuid))
                elif record_type in self.passfile.records[entry_uuid]:
                    self.editdetails_dialog.builder.get_object(
                        widget_name).set_text(
                            self.passfile.records[entry_uuid][record_type])

            self.set_entry_window_size()
            self.editdetails_dialog.set_transient_for(self)
            response = self.editdetails_dialog.run()

            data_changed = False
            tree_changed = False

            if response == Gtk.ResponseType.OK:
                for record_type, widget_name in list(record_dict.items()):
                    # Get the new value
                    if record_type == 2:
                        combo = self.editdetails_dialog.builder.get_object(
                            'folder_combo')
                        combo_iter = combo.get_active_iter()
                        if combo_iter is not None:
                            new_value = folder_path_to_list(
                                combo.get_model()[combo_iter][0])
                        else:
                            new_value = folder_path_to_list(
                                combo.get_child().get_text())
                    elif record_type == 5:
                        new_value = self.editdetails_dialog.builder.get_object(
                            widget_name).get_text(
                                self.editdetails_dialog.builder.get_object(
                                    widget_name).get_start_iter(),
                                self.editdetails_dialog.builder.get_object(
                                    widget_name).get_end_iter(), True)
                    else:
                        new_value = self.editdetails_dialog.builder.get_object(
                            widget_name).get_text()

                    # Now do something with it
                    if record_type == 2:
                        old_folder = self.passfile.get_folder_list(entry_uuid)
                        self.passfile.remove_empty_folder(new_value)
                        if old_folder != new_value:
                            self.passfile.add_empty_folder(old_folder)
                            self.passfile.update_folder_list(
                                entry_uuid, new_value)
                            data_changed = True
                            tree_changed = True
                    elif ((record_type in [5, 13]) and
                          new_value == "" and
                          record_type in self.passfile.records[entry_uuid]):
                        del self.passfile.records[entry_uuid][record_type]
                        data_changed = True
                    elif self.passfile.records[entry_uuid].get(
                            record_type, "") != new_value:
                        data_changed = True
                        self.passfile.records[entry_uuid][record_type] = \
                            new_value
                        # Reset the entire tree on name and path changes
                        if record_type in [2, 3, 4]:
                            tree_changed = True

                        # Update the password changed date
                        if record_type == 6:
                            self.passfile.update_password_time(entry_uuid)

                if data_changed is True:
                    self.set_save_status(True)
                    self.passfile.update_modification_time(entry_uuid)
                    if self.settings.get_boolean('auto-save') is True:
                        self.save_db()

            self.save_entry_window_size()
            self.editdetails_dialog.destroy()
            self.editdetails_dialog = None

            if tree_changed is True:
                self.display_entries()
                self.goto_uuid(entry_uuid)
            else:
                # Update the right pane only if it's still the one
                # currently selected
                treemodel, treeiter = \
                    self.ui.treeview1.get_selection().get_selected()
                if treeiter is not None and treemodel.get_value(
                        treeiter, 2) == entry_uuid:
                    self.display_data(entry_uuid)

            self.set_idle_timeout()
            self.update_find_results(force=True)
            return response

    def edit_folder(self, treemodel, treeiter, new_folder=False):

        # Make sure dialog isn't already open
        if self.editfolder_dialog is not None:
            self.editfolder_dialog.present()
            return

        if self.EditFolderDialog is not None:
            self.disable_idle_timeout()
            self.editfolder_dialog = self.EditFolderDialog()

            if new_folder is True:
                title = self.editfolder_dialog.builder.get_object('title')
                title.set_markup(_("<big><b>New folder</b></big>"))

            folder_name = treemodel.get_value(treeiter, 1)
            if folder_name == _("[Untitled]"):
                folder_name = ""
            self.editfolder_dialog.ui.folder_name_entry.set_text(folder_name)
            self.editfolder_dialog.ui.folder_name_entry.select_region(0, -1)

            liststore = self.editfolder_dialog.builder.get_object('liststore1')
            combobox = self.editfolder_dialog.builder.get_object(
                'folder_combo')
            parent_folder = self.get_folders_from_iter(
                treemodel, treeiter)[:-1]
            self.populate_folders(liststore, combobox, parent_folder)

            self.set_folder_window_size()
            self.editfolder_dialog.set_transient_for(self)
            response = self.editfolder_dialog.run()
            if response == Gtk.ResponseType.OK:
                new_name = \
                    self.editfolder_dialog.ui.folder_name_entry.get_text()

                combo_iter = combobox.get_active_iter()
                if combo_iter is not None:
                    new_parent = folder_path_to_list(
                        combobox.get_model()[combo_iter][0])
                else:
                    new_parent = []

                if new_name != folder_name or new_parent != parent_folder:

                    # TODO: make sure new_name is unique in the same level
                    new_folders = new_parent[:]
                    new_folders.append(new_name)

                    old_folders = parent_folder[:]
                    old_folders.append(folder_name)

                    if new_folder is False:
                        self.passfile.rename_folder_list(
                            old_folders, new_folders)
                    else:
                        self.passfile.add_empty_folder(new_folders)

                    self.display_entries()
                    self.goto_folder(new_folders)

                    self.set_save_status(True)
                    if self.settings.get_boolean('auto-save') is True:
                        self.save_db()

            self.save_folder_window_size()
            self.editfolder_dialog.destroy()
            self.editfolder_dialog = None

            self.set_idle_timeout()
            self.update_find_results(force=True)
            return response

    def get_folders_from_iter(self, treemodel, treeiter):
        folders = []

        if treemodel is None or treeiter is None:
            return folders

        uuid = treemodel.get_value(treeiter, 2)
        if "pasaffe_treenode." in uuid:
            folders.append(treemodel.get_value(treeiter, 1))

        parent = treemodel.iter_parent(treeiter)
        while parent is not None:
            folders.insert(0, treemodel.get_value(parent, 1))
            parent = treemodel.iter_parent(parent)

        return folders

    def delete_entry(self, entry_uuid, save=True):
        self.set_idle_timeout()

        item = self.search_uuid(entry_uuid)
        if item:
            new_item = self.ui.treeview1.get_model().iter_next(item)

            if new_item is None:
                # No more items in the current level, try and get the parent
                new_item, _item = self.find_prev_iter(entry_uuid)

            self.ui.liststore1.remove(item)

        # Delete the entry, and add the folder to the empty list
        folder = self.passfile.get_folder_list(entry_uuid)
        self.passfile.delete_entry(entry_uuid)
        self.passfile.add_empty_folder(folder)

        if item:
            if new_item is None:
                new_item = self.ui.treeview1.get_model().get_iter_first()

            if new_item != 0 and new_item is not None:
                self.ui.treeview1.get_selection().select_iter(new_item)

        if save is True:
            self.set_save_status(True)
            if self.settings.get_boolean('auto-save') is True:
                self.save_db()

        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter is not None:
            entry_uuid = treemodel.get_value(treeiter, 2)
            if "pasaffe_treenode." in entry_uuid:
                self.display_folder(treemodel.get_value(treeiter, 1))
            else:
                self.display_data(entry_uuid)
        else:
            self.display_welcome()

        self.update_find_results(force=True)

    def delete_folder(self, folders, save=True):
        self.set_idle_timeout()

        item = self.search_folder(folders)
        if item:
            self.passfile.delete_folder(folders)

            self.display_entries()
            parent_folder = folders[:-1]
            # TODO: if top level, switch to next iter
            if parent_folder != []:
                self.goto_folder(parent_folder)

        if save is True:
            self.set_save_status(True)
            if self.settings.get_boolean('auto-save') is True:
                self.save_db()

        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter is not None:
            entry_uuid = treemodel.get_value(treeiter, 2)
            if "pasaffe_treenode." in entry_uuid:
                self.display_folder(treemodel.get_value(treeiter, 1))
            else:
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
        entry_uuid = treemodel.get_value(treeiter, 2)
        if "pasaffe_treenode." in entry_uuid:
            # Toggle expanded state of folder
            folder = self.get_folders_from_iter(treemodel, treeiter)
            folder_field = folder_list_to_field(folder)
            if folder_field in self.folder_state and self.folder_state[folder_field] is True:
                self.collapse_folder(folder)
            else:
                self.expand_folder(folder)
        else:
            # Copy password
            self.copy_selected_entry_item(6)

    def collapse_folder(self, folder):
        self.set_folder_state(folder, False)
        self.set_tree_expansion()

    def expand_folder(self, folder):
        self.set_folder_state(folder, True)
        self.set_tree_expansion()

    def on_treeview1_row_expanded(self, treeview, treeiter, _path):
        treemodel = treeview.get_model()
        folder = self.get_folders_from_iter(treemodel, treeiter)
        self.set_folder_state(folder, True)

    def on_treeview1_row_collapsed(self, treeview, treeiter, _path):
        treemodel = treeview.get_model()
        folder = self.get_folders_from_iter(treemodel, treeiter)
        self.set_folder_state(folder, False)

    def on_treeview1_key_pressed(self, treeview, event):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter is None:
            return
        entry_uuid = treemodel.get_value(treeiter, 2)
        if event.keyval in [Gdk.KEY_Return, Gdk.KEY_KP_Enter]:
            if "pasaffe_treenode." in entry_uuid:
                return
            else:
                self.edit_entry(entry_uuid)
                return True
        if event.keyval == Gdk.KEY_Left:
            if "pasaffe_treenode." in entry_uuid:
                folder = self.get_folders_from_iter(treemodel, treeiter)
                folder_field = folder_list_to_field(folder)
                if folder_field in self.folder_state and self.folder_state[folder_field] is True:
                    self.collapse_folder(folder)
                    return True
                folders = self.get_folders_from_iter(treemodel, treeiter)[:-1]
            else:
                folders = self.get_folders_from_iter(treemodel, treeiter)
            if folders:
                # Select parent folder
                self.goto_folder(folders)
            return True
        if event.keyval == Gdk.KEY_Right:
            if "pasaffe_treenode." in entry_uuid:
                folder = self.get_folders_from_iter(treemodel, treeiter)
                folder_field = folder_list_to_field(folder)
                if folder_field not in self.folder_state or self.folder_state[folder_field] is False:
                    self.expand_folder(folder)
                    return True
                # Select first child item
                iterchild = self.ui.treeview1.get_model().iter_children(treeiter)
                if iterchild:
                    uuid = treemodel.get_value(iterchild, 2)
                    self.goto_uuid(uuid)
                return True

    def save_db(self):
        if self.get_save_status() is True:
            self.save_tree_expansion()
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
        if self.settings.get_boolean('auto-save') is True:
            self.save_db()
        if self.save_warning() is False:
            Gtk.main_quit()
        else:
            self.set_idle_timeout()

    def on_mnu_clone_activate(self, _menuitem):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter is not None:
            entry_uuid = treemodel.get_value(treeiter, 2)
            # TODO: what happens when we clone a folder?
            if "pasaffe_treenode." in entry_uuid:
                return
            else:
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
        if treeiter is not None:
            entry_uuid = treemodel.get_value(treeiter, 2)

            # Bail out of we're a folder
            if "pasaffe_treenode." in entry_uuid:
                return

            self.display_data(entry_uuid, display)

    def copy_selected_entry_item(self, item):
        self.set_idle_timeout()
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter is not None:
            entry_uuid = treemodel.get_value(treeiter, 2)

            # Bail out of we're a folder
            if "pasaffe_treenode." in entry_uuid:
                return

            if item in self.passfile.records[entry_uuid]:
                for atom in [Gdk.SELECTION_CLIPBOARD, Gdk.SELECTION_PRIMARY]:
                    clipboard = Gtk.Clipboard.get(atom)
                    value = self.passfile.records[entry_uuid][item]
                    length = len(value.encode('utf-8'))
                    clipboard.set_text(value, length)
                    clipboard.store()
                self.set_clipboard_timeout()

    def on_mnu_add_entry_activate(self, _menuitem):
        self.add_entry()

    def on_mnu_add_folder_activate(self, _menuitem):
        self.add_folder()

    def on_mnu_edit1_activate(self, _menuitem):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter is not None:
            entry_uuid = treemodel.get_value(treeiter, 2)
            if "pasaffe_treenode." in entry_uuid:
                self.edit_folder(treemodel, treeiter)
            else:
                self.edit_entry(entry_uuid)

    def on_mnu_delete_activate(self, _menuitem):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter is not None:
            entry_uuid = treemodel.get_value(treeiter, 2)
            if "pasaffe_treenode." in entry_uuid:
                self.remove_folder()
            else:
                self.remove_entry()

    def on_mnu_lock_activate(self, _menuitem):
        self.lock_screen()

    def on_mnu_info_activate(self, _menuitem):
        header = _('<big><b>Database Information</b></big>\n\n')
        information = _('Number of entries: %s\n') % \
            len(self.passfile.records)
        information += '\n'
        if self.passfile.get_saved_name():
            information += _('Last saved by: %s\n') % \
                self.passfile.get_saved_name()
        if self.passfile.get_saved_host():
            information += _('Last saved on host: %s\n') % \
                self.passfile.get_saved_host()
            information += _('Last save date: %s\n') % \
                self.passfile.get_saved_date_string()
        information += '\n'
        information += _('Database version: %s\n') % \
            self.passfile.get_database_version_string()
        if self.passfile.get_saved_application():
            information += _('Application used: %s\n') % \
                self.passfile.get_saved_application()
        information += '\n'
        information += _('Database location:\n%s\n') % self.database
        information = header + GLib.markup_escape_text(information)

        info_dialog = Gtk.MessageDialog(transient_for=self,
                                        modal=True,
                                        message_type=Gtk.MessageType.INFO,
                                        buttons=Gtk.ButtonsType.OK)
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

        if self.ui.find_box.get_property("visible") is False:
            return

        find = self.ui.find_entry.get_text()

        # Don't crash with stupid "bogus escape (end of line)" error
        while find[-1:] == '\\':
            find = find[:-1]

        self.passfile.update_find_results(find, force)

    def goto_next_find_result(self, backwards=False):

        uuid_hex = self.passfile.get_next_find_result(backwards)

        if uuid_hex is not None:
            self.goto_uuid(uuid_hex)

    def on_find_entry_activate(self, _entry):
        self.update_find_results()
        self.goto_next_find_result()

    def show_find(self, show):

        if self.ui.find_box.get_property("visible") == show:
            return

        if show is True:
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
        newpass_dialog.set_transient_for(self)

        while success is False:
            response = newpass_dialog.run()
            if response == Gtk.ResponseType.OK:
                old_password = newpass_dialog.ui.pass_entry1.get_text()
                password_a = newpass_dialog.ui.pass_entry2.get_text()
                password_b = newpass_dialog.ui.pass_entry3.get_text()
                if password_a != password_b:
                    newpass_dialog.ui.label3.set_text(
                        _("Passwords don't match! Please try again."))
                    newpass_dialog.ui.label3.set_property("visible", True)
                    newpass_dialog.ui.pass_entry2.grab_focus()
                elif password_a == '':
                    newpass_dialog.ui.label3.set_text(
                        _("New password cannot be blank! Please try again."))
                    newpass_dialog.ui.label3.set_property("visible", True)
                    newpass_dialog.ui.pass_entry2.grab_focus()
                elif not self.passfile.check_password(old_password):
                    newpass_dialog.ui.label3.set_text(
                        _("Old password is invalid! Please try again."))
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
        while success is False:
            response = password_dialog.run()
            if response == Gtk.ResponseType.OK:
                password = password_dialog.ui.password_entry.get_text()
                success = self.passfile.check_password(password)
                if success is False:
                    password_dialog.ui.password_error_label.set_property(
                        "visible", True)
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

    def on_lock_quit_button_clicked(self, _button):
        if self.save_warning() is False:
            Gtk.main_quit()
            return

    def set_menu_sensitive(self, status):
        # There's got to be a better way to do this
        self.ui.mnu_lock.set_sensitive(status)
        self.ui.mnu_chg_password.set_sensitive(status)
        self.ui.mnu_add_entry.set_sensitive(status)
        self.ui.mnu_add_folder.set_sensitive(status)
        self.ui.mnu_clone.set_sensitive(status)
        self.ui.mnu_delete.set_sensitive(status)
        self.ui.mnu_find.set_sensitive(status)
        self.ui.url_copy.set_sensitive(status)
        self.ui.username_copy.set_sensitive(status)
        self.ui.password_copy.set_sensitive(status)
        self.ui.mnu_preferences.set_sensitive(status)
        self.ui.mnu_open_url.set_sensitive(status)
        self.ui.mnu_info.set_sensitive(status)

        if status is False:
            self.ui.mnu_display_secrets.set_sensitive(False)
        else:
            self.set_show_password_status()

        if status is True and self.needs_saving is True:
            self.ui.mnu_save.set_sensitive(True)
            self.ui.save.set_sensitive(True)
        else:
            self.ui.mnu_save.set_sensitive(False)
            # Work around issue where button is insensitive, but icon is
            # not greyed out
            self.ui.save.set_sensitive(True)
            self.ui.save.set_sensitive(False)

    def set_menu_for_entry(self, status):
        # main menu
        self.ui.mnu_clone.set_sensitive(status)
        self.ui.url_copy.set_sensitive(status)
        self.ui.username_copy.set_sensitive(status)
        self.ui.password_copy.set_sensitive(status)
        self.ui.mnu_open_url.set_sensitive(status)

        # context menu
        self.ui.mnu_clone1.set_sensitive(status)
        self.ui.url_copy1.set_sensitive(status)
        self.ui.username_copy1.set_sensitive(status)
        self.ui.password_copy1.set_sensitive(status)

        # Toolbar
        self.ui.open_url.set_sensitive(status)
        self.ui.copy_username.set_sensitive(status)
        self.ui.copy_password.set_sensitive(status)

        if status is False:
            self.ui.mnu_display_secrets.set_sensitive(False)
            self.ui.display_secrets.set_sensitive(False)
        else:
            self.set_show_password_status()

    def on_add_clicked(self, _toolbutton):
        self.add_entry()

    def on_add_folder_clicked(self, _toolbutton):
        self.add_folder()

    def on_edit_clicked(self, _toolbutton):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter is not None:
            entry_uuid = treemodel.get_value(treeiter, 2)
            if "pasaffe_treenode." in entry_uuid:
                self.edit_folder(treemodel, treeiter)
            else:
                self.edit_entry(entry_uuid)

    def on_remove_clicked(self, _toolbutton):
        treemodel, treeiter = self.ui.treeview1.get_selection().get_selected()
        if treeiter is not None:
            entry_uuid = treemodel.get_value(treeiter, 2)
            if "pasaffe_treenode." in entry_uuid:
                self.remove_folder()
            else:
                self.remove_entry()

    def set_idle_timeout(self):
        if self.idle_id is not None:
            GLib.source_remove(self.idle_id)
            self.idle_id = None
        if (self.settings.get_boolean('lock-on-idle') is True and
                self.settings.get_int('idle-timeout') != 0):
            idle_time = int(self.settings.get_int('idle-timeout') * 1000 * 60)
            self.idle_id = GLib.timeout_add(
                idle_time, self.idle_timeout_reached)

    def idle_timeout_reached(self):
        if self.is_locked is False:
            self.lock_screen()
        if self.idle_id is not None:
            GLib.source_remove(self.idle_id)
            self.idle_id = None

    def disable_idle_timeout(self):
        if self.idle_id is not None:
            GLib.source_remove(self.idle_id)
            self.idle_id = None

    def set_clipboard_timeout(self):
        if self.clipboard_id is not None:
            GLib.source_remove(self.clipboard_id)
            self.clipboard_id = None
        if self.settings.get_int('clipboard-timeout') != 0:
            clipboard_time = int(
                self.settings.get_int('clipboard-timeout') * 1000)
            self.clipboard_id = GLib.timeout_add(
                clipboard_time, self.clipboard_timeout_reached)

    def clipboard_timeout_reached(self):
        if self.clipboard_id is not None:
            GLib.source_remove(self.clipboard_id)
            self.clipboard_id = None
        for atom in [Gdk.SELECTION_CLIPBOARD, Gdk.SELECTION_PRIMARY]:
            clipboard = Gtk.Clipboard.get(atom)
            clipboard.set_text("", 0)
            clipboard.store()

    def set_show_password_status(self):
        visible = self.settings.get_boolean('visible-secrets')

        if visible is True:
            self.ui.mnu_display_secrets.set_sensitive(False)
            # Work around issue where button is insensitive, but icon is
            # not greyed out
            self.ui.display_secrets.set_sensitive(True)
            self.ui.display_secrets.set_sensitive(False)
        else:
            self.ui.mnu_display_secrets.set_sensitive(True)
            self.ui.display_secrets.set_sensitive(True)

    def _set_title(self):
        prefix = ""
        if not self.default_database:
            prefix = "%s - " % os.path.basename(self.database)
        self.set_title("%s%sPasaffe" % (
            prefix,
            "*" if self.needs_saving else ""))

    def set_save_status(self, needed):
        self.needs_saving = needed
        self.ui.save.set_sensitive(needed)
        self.ui.mnu_save.set_sensitive(needed)
        self._set_title()

    def get_save_status(self):
        return self.needs_saving
