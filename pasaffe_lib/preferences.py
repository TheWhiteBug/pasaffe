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

"""Provides a shared preferences dictionary"""

import gtk
import gobject
import gconf
import logging
logger = logging.getLogger('pasaffe')

ROOT_DIR = '/apps/pasaffe'

class User_dict(dict):
    ''' a dictionary with extra methods:

    persistence: load, save
    gobject signals: connect and emit.

    Don't use this directly. Please use the preferences instance.'''

    def __init__(self, *args, **kwds):
        dict.__init__(self, *args, **kwds)

        # Set up gconf
        self.gconf_client = gconf.client_get_default()

        class Publisher(gtk.Invisible): # pylint: disable=R0904
            '''set up signals in a separate class

            gtk.Invisible has 230 public methods'''
            __gsignals__ = {'changed' : (gobject.SIGNAL_RUN_LAST,
                 gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
                 'loaded' : (gobject.SIGNAL_RUN_LAST,
                 gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,))}

        publisher = Publisher()
        self.emit  = publisher.emit
        self.connect  = publisher.connect

    def save(self):
        'save to gconf'
        for (key, value) in dict.items(self):
            logger.debug("saving preference: %s" % key)
            if type(value) == bool:
                self.gconf_client.set_bool(ROOT_DIR + "/" + key, value)
            elif type(value) == str:
                self.gconf_client.set_string(ROOT_DIR + "/" + key, value)
            elif type(value) == int:
                self.gconf_client.set_int(ROOT_DIR + "/" + key, value)
 
    def load(self):
        'load from gconf'
        self.gconf_client.add_dir(ROOT_DIR, gconf.CLIENT_PRELOAD_NONE)
        self.gconf_client.notify_add(ROOT_DIR, self.prefs_changed_callback)

        for key in dict.keys(self):
            logger.debug("loading preference: %s" % key)
            value = self.gconf_client.get(ROOT_DIR + "/" + key)

            if value != None:
                if type(dict.get(self, key)) == bool:
                    data = value.get_bool()
                elif type(dict.get(self, key)) == str:
                    data = value.get_string()
                elif type(dict.get(self, key)) == int:
                    data = value.get_int()
                self[key] = data
                logger.debug("preference '%s' loaded value '%s'" % (key, data))

        self.emit('loaded', None)

    def update(self, *args, **kwds):
        ''' interface for dictionary

        send changed signal when appropriate '''

        # parse args
        new_data = {}
        new_data.update(*args, **kwds)

        changed_keys = []
        for key in new_data.keys():
            if new_data.get(key) != dict.get(self, key):
                changed_keys.append(key)
        dict.update(self, new_data)
        if changed_keys:
            self.emit('changed', tuple(changed_keys))

    def prefs_changed_callback(self, client, timestamp, entry, *extra):
        """
        This is the callback function that is called when the keys in our
        namespace change (such as editing them with gconf-editor).
        """
        key = entry.get_key()[entry.get_key().rfind('/')+1:]
        if (entry.get_value().type == gconf.VALUE_BOOL):
            value = entry.get_value().get_bool()
        if (entry.get_value().type == gconf.VALUE_INT):
            value = entry.get_value().get_int()
        if (entry.get_value().type == gconf.VALUE_STRING):
            value = entry.get_value().get_string()
        logger.debug("key '%s' got changed to '%s'" % (key, value))
        self[key] = value

    def __setitem__(self, key, value):
        ''' interface for dictionary

        send changed signal when appropriate '''
        if value != dict.get(self, key):
            dict.__setitem__(self, key, value)
            self.emit('changed', (key,))

preferences = User_dict()

