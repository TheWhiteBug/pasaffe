#!/usr/bin/env python3
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

###################### DO NOT TOUCH THIS (HEAD TO THE SECOND PART) ######################

import os
import sys
from glob import glob

try:
    import DistUtilsExtra.auto
except ImportError:
    print('To build pasaffe you need https://launchpad.net/python-distutils-extra', file=sys.stderr)
    sys.exit(1)
assert DistUtilsExtra.auto.__version__ >= '2.18', 'needs DistUtilsExtra.auto >= 2.18'

def update_config(values = {}):

    oldvalues = {}
    try:
        fin = open('pasaffe_lib/pasaffeconfig.py', 'r')
        fout = open(fin.name + '.new', 'w')

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
    except (OSError, IOError) as e:
        print ("ERROR: Can't find pasaffe_lib/pasaffeconfig.py")
        sys.exit(1)
    return oldvalues


class InstallAndUpdateDataDirectory(DistUtilsExtra.auto.install_auto):
    def run(self):
        values = {'__pasaffe_data_directory__': "'%s'" % (self.prefix + '/share/pasaffe/'),
                  '__version__': "'%s'" % self.distribution.get_version()}

        # Older DistUtilsExtra put help files in /usr/share/gnome/help and
        # needed a ghelp: URL
        if DistUtilsExtra.auto.__version__ < '2.38':
            values['__help_prefix__'] = "'ghelp:'"
            values['__help_separator__'] = "'#'"

        previous_values = update_config(values)
        DistUtilsExtra.auto.install_auto.run(self)
        update_config(previous_values)


##################################################################################
###################### YOU SHOULD MODIFY ONLY WHAT IS BELOW ######################
##################################################################################

DistUtilsExtra.auto.setup(
    name='pasaffe',
    version='0.54',
    license='GPL-3',
    author='Marc Deslauriers',
    author_email='marc.deslauriers@canonical.com',
    description='Password manager for GNOME',
    long_description='Pasaffe is an easy to use password manager for GNOME.',
    url='https://launchpad.net/pasaffe',
    data_files=[('share/mime/packages', glob('mime/*'))],
    cmdclass={'install': InstallAndUpdateDataDirectory}
    )

