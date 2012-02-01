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

import optparse
import os

import gettext
from gettext import gettext as _
gettext.textdomain('pasaffe')

from gi.repository import Gtk # pylint: disable=E0611

from pasaffe import PasaffeWindow

from pasaffe_lib import set_up_logging, preferences, get_version

def parse_options():
    """Support for command line options"""
    parser = optparse.OptionParser(version="%%prog %s" % get_version())
    parser.add_option(
        "-v", "--verbose", action="count", dest="verbose",
        help=_("Show debug messages (-vv debugs pasaffe_lib also)"))
    parser.add_option(
        "-f", "--file", dest="filename",
        help=_("set database to FILE"), metavar="FILE")
    (options, args) = parser.parse_args()

    set_up_logging(options)
    return options

def get_database_path():
    """Determines standard XDG location for database"""
    if os.environ.has_key('XDG_DATA_HOME'):
        basedir = os.path.join(os.environ['XDG_DATA_HOME'], 'pasaffe')
    else:
        basedir = os.path.join(os.environ['HOME'], '.local/share/pasaffe')

    if not os.path.exists(basedir):
        os.mkdir(basedir, 0700)

    return os.path.join(basedir, 'pasaffe.psafe3')

def main():
    'constructor for your class instances'
    options = parse_options()

    filename = get_database_path()

    # preferences
    # set some values for our first session
    default_preferences = {
    'visible-secrets': False,
    'only-passwords-are-secret': True,
    'database-path': filename,
    'lock-on-idle': True,
    'idle-timeout': 5,
    'auto-save': False
    }

    preferences.update(default_preferences)
    preferences.load()

    if preferences['database-path'] == "":
        preferences['database-path'] = filename

    # Override path that was saved with path from command line
    if options.filename != None:
        preferences['database-path'] = options.filename

    # Run the application.
    window = PasaffeWindow.PasaffeWindow()
    window.show()
    Gtk.main()

    preferences.save()
