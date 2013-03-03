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

import sys
import os.path
import yaml

from cydra.component import Component, implements
from cydra.datasource import IDataSource, IPubkeyStore

from cydra.project import is_valid_project_name, Project

class FileDataSource(Component):
    """Datasource that saves projects into files
    """

    implements(IDataSource)
    
    def __init__(self):
        config = self.get_component_config()

        if 'base' not in config:
            raise InsufficientConfiguration(missing='base', component=self.get_component_name())
        self._base = config['base']
        
    def _get_project_path(self, name):
        return os.path.join(self._base, name + '.yaml')
        
    def get_project(self, projectname):
        # Check name
        if not is_valid_project_name(projectname):
            return None

        path = self._get_project_path(projectname)

        if os.path.exists(path):
            with open(path, 'r') as f:
                return Project(self.compmgr, yaml.safe_load(f))

    def save_project(self, project):
        # Check name
        if not is_valid_project_name(projectname):
            return None
        
        path = self._get_project_path(project.name)
        with open(path, 'w') as f:
                yaml.safe_dump(project.data, f)

    def create_project(self, projectname, owner):
        # Check name
        if not is_valid_project_name(projectname):
            return None

        if self.get_project(projectname) is None:
            path = self._get_project_path(projectname)
            with open(path, 'w') as f:
                yaml.safe_dump({'name': projectname, 'owner': owner.userid}, f)
            return self.get_project(projectname)

    def list_projects(self):
        ret = []
        for filename in os.listdir(self._base):
            if filename.endswith(".yaml"):
                ret.append(self.get_project(filename[:-len(".yaml")]))
        
        return ret

    def get_project_names(self):
        ret = []
        for filename in os.listdir(self._base):
            if filename.endswith(".yaml"):
                ret.append(filename[:-len(".yaml")])
        
        return ret

    def get_projects_owned_by(self, user):
        if user is None:
            return []

        ret = []
        for project in self.list_projects():
            if project.owner == user:
                ret.append(project)

        return ret

    def get_projects_where_key_exists(self, key):
        ret = []
        
        for project in self.list_projects():
            if isinstance(key, list):
                look_in = project.data
                found = True
                for component in key:
                    if component not in look_in:
                        found = False
                        break
                if found:
                    ret.append(project)
            else:
                if str(key) in project.data:
                    ret.append(project)
        
        return ret    
