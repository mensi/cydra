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
import re
import os, os.path
import datetime

from cydra.component import ExtensionPoint, BroadcastAttributeProxy, Interface
from cydra.repository import IRepository
from cydra.datasource import IDataSource
from cydra.permission import IPermissionProvider, IUserTranslator

from cydra.util import NoopArchiver, TarArchiver

import logging
logger = logging.getLogger(__name__)

class ISyncParticipant(Interface):
    """Interface for components whishing to participate in project synchronisation"""

    _iface_attribute_proxy = BroadcastAttributeProxy()

    def sync_project(self, project):
        """Sync project
        
        :param project: Project instance requesting to be synced
        :returns: True on success, False on failure. None is ignored"""

def is_valid_project_name(name):
    # disallow certain words that are frequently used for some magic stuff
    if name in ['static', 'css', 'media']:
        return False

    # only allow alphanumeric names
    if re.match('^[a-z][a-z0-9\-_]{0,31}$', name) is None:
        return False
    else:
        return True

class Project(object):

    #observers = ExtensionPoint(IProjectObserver)
    _repositories = ExtensionPoint(IRepository)
    datasource = ExtensionPoint(IDataSource)
    permission = ExtensionPoint(IPermissionProvider)
    translator = ExtensionPoint(IUserTranslator)
    sync_participants = ExtensionPoint(ISyncParticipant)

    def __init__(self, component_manager, data):
        self.compmgr = component_manager
        self.data = data
        self.delay_save_count = 0
        self.load_time = datetime.datetime.now()

    @property
    def name(self):
        return self.data['name']

    @property
    def owner(self):
        return self.compmgr.get_user(userid=self.data['owner'])

    def get_repository(self, type, name):
        """Convenience function for direct repository lookup"""
        for repotype in self._repositories:
            if repotype.repository_type == type:
                return repotype.get_repository(self, name)

    def get_repository_type(self, repository_type):
        """Convenience function for direct repository type retrieval"""
        for repotype in self._repositories:
            if repotype.repository_type == repository_type:
                return repotype

    def get_repository_types(self):
        return self._repositories

    def get_permissions(self, user, object):
        """Convenience function for permission enumeration"""
        return self.permission.get_permissions(self, user, object)

    def get_permission(self, user, object, permission):
        """Convenience function for permission retrieval"""
        return self.permission.get_permission(self, user, object, permission)

    def set_permission(self, user, object, permission, value):
        """Convenience function for permission retrieval"""
        return self.permission.set_permission(self, user, object, permission, value)

    def get_group_permissions(self, group, object):
        """Convenience function for permission enumeration"""
        return self.permission.get_group_permissions(self, group, object)

    def get_group_permission(self, group, object, permission):
        """Convenience function for permission retrieval"""
        return self.permission.get_group_permission(self, group, object, permission)

    def set_group_permission(self, group, object, permission, value):
        """Convenience function for permission retrieval"""
        return self.permission.set_group_permission(self, group, object, permission, value)

    def sync_repositories(self):
        """Sync all repositories of this project
        
        :returns: False if any of the repositories returned False, True otherwise"""
        # You might wonder why this function exists instead of the repository provider 
        # implementing SyncParticipant. Since the Repository class contains sync, all 
        # repositories provide this function and we can handle all of them here

        repos = []
        for repotype in self.get_repository_types():
            repos.extend(repotype.get_repositories(self))

        res = True

        for repo in repos:
            if repo.sync() == False: # Don't use not here, None should not be considered a failure
                res = False

        return res

    def sync(self):
        """Synchronize the project"""
        return not any([x == False for x in self.sync_participants.sync_project(self)]) # Don't use not here, None should not be considered a failure

    def get_archiver(self, filename):
        """Get an archiver for this project"""
        path = self.compmgr.config.get('archive_path', None)
        if not path:
            return NoopArchiver()

        path = os.path.join(path, self.name)
        if not os.path.exists(path):
            os.mkdir(path)

        path = os.path.join(path, filename + '_' + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.tar')
        return TarArchiver(path)

    def delay_save(self):
        self.delay_save_count += 1

    def undelay_save(self):
        self.delay_save_count -= 1

        if self.delay_save_count == 0:
            self.save()
        elif self.delay_save_count < 0:
            raise Exception("More undelay than delay saves")

    def save(self):
        if self.delay_save_count > 0:
            return

        if datetime.datetime.now() - self.load_time > datetime.timedelta(seconds=5):
            logger.warning("Warning, time elapsed between loading and saving project %s was %s", self.name, str(datetime.datetime.now() - self.load_time))

        self.datasource.save_project(self)

    def __eq__(self, other):
        return self.compmgr == other.compmgr and self.name == other.name

    def __hash__(self):
        return hash((self.compmgr, self.name))
