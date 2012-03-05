# -*- coding: utf-8 -*-
#
# Copyright 2012 Manuel Stocker <mensi@mensi.ch>
#
# This file is part of Cydra.
#
# Cydra is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Cydra is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Cydra.  If not, see http://www.gnu.org/licenses

import os.path
import json
import codecs

from cydra.component import Component, implements
from cydra.config import IConfigurationProvider

class ConfigurationFile(Component):
    implements(IConfigurationProvider)

    def get_config(self):
        cconfig = self.compmgr.config.get_component_config(self.get_component_name(), {})
        config = {}
        cfiles = []

        if 'file' in cconfig:
            if isinstance(cconfig['file'], list):
                cfiles.extend(cconfig['file'])
            else:
                cfiles.append(cconfig['file'])
        else:
            cfiles.extend(self.find_default_locations())

        for cfile in cfiles:
            self.compmgr.config.merge(config, self.load_file(cfile))

        return config

    def find_default_locations(self):
        locations = ['/etc/cydra.conf',
                     os.path.join(os.path.expanduser('~'), '.cydra'),
                     'cydra.conf']

        locations = [os.path.abspath(location) for location in locations]
        #print "Config locations:", locations
        return [location for location in locations if os.path.exists(location)]

    def load_file(self, filename):
        cfile = open(filename, "r")
        try:
            return json.load(cfile)
        finally:
            cfile.close()
