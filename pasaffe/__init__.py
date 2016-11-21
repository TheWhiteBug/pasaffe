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

import optparse
import os

import gettext
t = gettext.translation('pasaffe', fallback=True)
_ = t.gettext

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, Gtk

from pasaffe import PasaffeWindow

from pasaffe_lib import set_up_logging, get_version
from pasaffe_lib.helpers import get_database_path


def parse_options():
    """Support for command line options"""
    parser = optparse.OptionParser(usage="Usage: %prog [filename] [options]",
        version="%%prog %s" % get_version())
    parser.add_option(
        "-v", "--verbose", action="count", dest="verbose",
        help=_("Show debug messages (-vv debugs pasaffe_lib also)"))
    parser.add_option(
        "-f", "--file", dest="filename",
        help=_("use database FILE"), metavar="FILE")
    parser.add_option(
        "-s", "--set-default", dest="set_default",
        help=_("set database as default"), action='store_true')
    (options, args) = parser.parse_args()
    if len(args) > 0 and options.filename is None:
        options.filename = args[0]
    set_up_logging(options)
    return options


def main():
    'constructor for your class instances'
    options = parse_options()

    filename = get_database_path()

    settings = Gio.Settings.new("net.launchpad.pasaffe")

    # On first launch, set the standard location
    if settings.get_string('database-path') == "":
        settings.set_string('database-path', filename)

    # Override path that was saved with path from command line
    if options.set_default and options.filename is not None:
        settings.set_string('database-path', options.filename)

    # Run the application.
    window = PasaffeWindow.PasaffeWindow(database=options.filename)
    window.show()  # pylint: disable=E1101
    Gtk.main()
