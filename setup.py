#!/usr/bin/env python
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

###################### DO NOT TOUCH THIS (HEAD TO THE SECOND PART) ######################

import os
import sys
from glob import glob

try:
    import DistUtilsExtra.auto
except ImportError:
    print >> sys.stderr, 'To build pasaffe you need https://launchpad.net/python-distutils-extra'
    sys.exit(1)
assert DistUtilsExtra.auto.__version__ >= '2.18', 'needs DistUtilsExtra.auto >= 2.18'

def update_config(values = {}):

    oldvalues = {}
    try:
        fin = file('pasaffe_lib/pasaffeconfig.py', 'r')
        fout = file(fin.name + '.new', 'w')

        for line in fin:
            fields = line.split(' = ') # Separate variable from value
            if fields[0] in values:
                oldvalues[fields[0]] = fields[1].strip()
                line = "%s = %s\n" % (fields[0], values[fields[0]])
            fout.write(line)

        fout.flush()
        fout.close()
        fin.close()
        os.rename(fout.name, fin.name)
    except (OSError, IOError), e:
        print ("ERROR: Can't find pasaffe_lib/pasaffeconfig.py")
        sys.exit(1)
    return oldvalues


def update_desktop_file(datadir):

    try:
        fin = file('pasaffe.desktop.in', 'r')
        fout = file(fin.name + '.new', 'w')

        for line in fin:            
            if 'Icon=' in line:
                line = "Icon=%s\n" % (datadir + 'media/pasaffe.svg')
            fout.write(line)
        fout.flush()
        fout.close()
        fin.close()
        os.rename(fout.name, fin.name)
    except (OSError, IOError), e:
        print ("ERROR: Can't find pasaffe.desktop.in")
        sys.exit(1)


class InstallAndUpdateDataDirectory(DistUtilsExtra.auto.install_auto):
    def run(self):
        values = {'__pasaffe_data_directory__': "'%s'" % (self.prefix + '/share/pasaffe/'),
                  '__version__': "'%s'" % self.distribution.get_version()}
        previous_values = update_config(values)
        update_desktop_file(self.prefix + '/share/pasaffe/')
        DistUtilsExtra.auto.install_auto.run(self)
        update_config(previous_values)

# python-distutils-extra in Lucid and Maverick doesn't support Mallard
# help files, so work around it
class BuildHelp(DistUtilsExtra.auto.build_help_auto):
    def get_data_files(self):
        data_files = []
        name = self.distribution.metadata.name
        omf_pattern = os.path.join(self.help_dir, '*', '*.omf')

        for path in glob(os.path.join(self.help_dir, '*')):
            lang = os.path.basename(path)
            path_xml = os.path.join('share/gnome/help', name, lang)
            path_figures = os.path.join('share/gnome/help', name, lang, 'figures')
            
            docbook_files = glob('%s/*.xml' % path)
            mallard_files = glob('%s/*.page' % path)
            data_files.append((path_xml, docbook_files + mallard_files))
            data_files.append((path_figures, glob('%s/figures/*.png' % path)))
        
        omf_files = glob(omf_pattern)
        if omf_files:
            data_files.append((os.path.join('share', 'omf', name), omf_files))
        
        return data_files


##################################################################################
###################### YOU SHOULD MODIFY ONLY WHAT IS BELOW ######################
##################################################################################

DistUtilsExtra.auto.setup(
    name='pasaffe',
    version='0.16',
    license='GPL-3',
    author='Marc Deslauriers',
    author_email='marc.deslauriers@canonical.com',
    description='Password manager for GNOME',
    long_description='Pasaffe is an easy to use password manager for GNOME.',
    url='https://launchpad.net/pasaffe',
    data_files=[("share/GConf/gsettings", ("data/pasaffe.convert",))],
    cmdclass={'install': InstallAndUpdateDataDirectory,
              'build_help' : BuildHelp}
    )

