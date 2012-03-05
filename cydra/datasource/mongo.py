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

from pymongo import Connection, ASCENDING, binary

from cydra.component import Component, implements
from cydra.datasource import IDataSource, IPubkeyStore

from cydra.project import is_valid_project_name, Project

class MongoDataSource(Component):
    """Datasource that saves projects into a MongoDB database
    
    This datasource encodes keys to allow for '.' in key names.
    """

    implements(IDataSource)
    implements(IPubkeyStore)

    def __init__(self):
        config = self.get_component_config()

        if 'host' not in config:
            raise Exception('Host not configured')

        if 'database' not in config:
            raise Exception('Database not configured')

        self.connection = Connection(config['host'])
        self.database = self.connection[config['database']]

        if 'user' in config and 'password' in config:
            self.database.authenticate(config['user'], config['password'])

    @staticmethod
    def _encode_key(val, magic='%'):
        """Helper function to encode . in keys as mongoDB does not allow them"""
        ret = val

        ret = ret.replace(magic, magic + '1')
        ret = ret.replace('.', magic + '2')

        return ret

    @staticmethod
    def _decode_key(val, magic='%'):
        """Helper function to decode . in keys as mongoDB does not allow them"""
        ret = val

        ret = ret.replace(magic + '2', '.')
        ret = ret.replace(magic + '1', magic)

        return ret

    @staticmethod
    def _process_dict_keys(data, f):
        if type(data) not in [list, set, dict]:
            return data

        ret = type(data)()
        if isinstance(data, dict):
            for key, val in data.items():
                ret[f(key)] = MongoDataSource._process_dict_keys(val, f)

        elif isinstance(data, list):
            for val in data:
                ret.append(MongoDataSource._process_dict_keys(val, f))

        elif isinstance(data, set):
            for val in data:
                ret.add(MongoDataSource._process_dict_keys(val, f))

        else:
            raise Exception("The universe exploded")

        return ret

    @staticmethod
    def _encode_dict_keys(data):
        return MongoDataSource._process_dict_keys(data, MongoDataSource._encode_key)

    @staticmethod
    def _decode_dict_keys(data):
        return MongoDataSource._process_dict_keys(data, MongoDataSource._decode_key)

    def get_project(self, projectname):
        # Check name
        if not is_valid_project_name(projectname):
            return None

        project = self.database.projects.find_one({'name': projectname})
        if project is not None:
            return Project(self.compmgr, self._decode_dict_keys(project))

    def save_project(self, project):
        self.database.projects.save(self._encode_dict_keys(project.data))

    def create_project(self, projectname, owner):
        # Check name
        if not is_valid_project_name(projectname):
            return None

        if self.get_project(projectname) is None:
            self.database.projects.insert({'name': projectname, 'owner': owner.userid})
            return self.get_project(projectname)

    def list_projects(self):
        ret = []
        for p in self.database.projects.find(sort=[('name', ASCENDING)]):
            ret.append(Project(self.compmgr, self._decode_dict_keys(p)))

        return ret

    def get_project_names(self):
        ret = []
        for p in self.database.projects.find(fields=['name'], sort=[('name', ASCENDING)]):
            ret.append(self._decode_dict_keys(p)['name'])

        return ret

    def get_projects_owned_by(self, user):
        if user is None:
            return []

        ret = []
        for p in self.database.projects.find({'owner': user.userid}, sort=[('name', ASCENDING)]):
            ret.append(Project(self.compmgr, self._decode_dict_keys(p)))

        return ret

    def get_projects_where_key_exists(self, key):
        search = {self._encode_key(str(key)): {'$exists': True}}

        if isinstance(key, list):
            search = {'.'.join(map(self._encode_key, key)): {'$exists': True}}

        ret = []
        for p in self.database.projects.find(search, sort=[('name', ASCENDING)]):
            ret.append(Project(self.compmgr, self._decode_dict_keys(p)))

        return ret

    def get_pubkeys(self, user):
        """Does user have a pubkey with blob"""
        return self.database.pubkeys.find({'userid': user.userid}, sort=[('name', ASCENDING)])

    def user_has_pubkey(self, user, blob):
        return bool(self.database.pubkeys.find_one({'blob': binary.Binary(blob), 'userid': user.userid}))

    def add_pubkey(self, user, blob, name="unnamed", fingerprint=""):
        """Add a new public key for a user"""
        if self.user_has_pubkey(user, blob):
            return False

        self.database.pubkeys.insert({'userid': user.userid, 'blob': binary.Binary(blob), 'name': name, 'fingerprint': fingerprint})
        return True

    def remove_pubkey(self, user, **kwargs):
        spec = {'userid': user.userid}
        for k, v in kwargs.items():
            if k in ['name', 'blob', 'fingerprint']:
                spec[k] = v

        if len(spec) > 1:
            self.database.pubkeys.remove(spec)
        return True
