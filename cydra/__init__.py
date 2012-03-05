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
__all__ = ['__version__', 'Cydra']

from pkg_resources import DistributionNotFound, get_distribution

try:
    __version__ = get_distribution('Cydra').version
except DistributionNotFound:
    __version__ = '0.1.0'

import logging
logger = logging.getLogger(__name__)

from cydra.component import ComponentManager, Component, ExtensionPoint
from cydra.loader import load_components
from cydra.config import Configuration
from cydra.datasource import IDataSource
from cydra.permission import IPermissionProvider, IUserTranslator, User
from cydra.caching.subject import ISubjectCache

class Cydra(Component, ComponentManager):
    """Main point of integration
    
    """
    datasource = ExtensionPoint(IDataSource)
    permission = ExtensionPoint(IPermissionProvider)
    translator = ExtensionPoint(IUserTranslator)
    subject_cache = ExtensionPoint(ISubjectCache)

    def __init__(self, config=None):
        logging.basicConfig(level=logging.DEBUG)

        ComponentManager.__init__(self)

        load_components(self)

        self.config = Configuration(self)
        self.config.load(config)

        logger.debug("Configuration loaded: %s", repr(self.config._data))

    def get_user(self, userid=None, username=None):
        """Convenience function for user retrieval"""
        if userid == '*':
            return User(self, '*', username='Guest', full_name='Guest')

        if userid is None and username is None:
            raise ValueError("Neither userid nor username given")

        result = None
        failed_caches = []

        # go to caches
        for cache in self.subject_cache:
            if userid is not None:
                result = cache.get_user(userid)
            elif username is not None:
                result = cache.get_user_by_name(username)

            if result is not None:
                break
            else:
                failed_caches.append(cache)

        # not found
        if result is None:
            if userid is not None:
                result = self.translator.userid_to_user(userid)
            elif username is not None:
                result = self.translator.username_to_user(username)

        if result is None:
            return result

        # update caches
        for cache in failed_caches:
            cache.add_users([result])

        return result

    def get_group(self, groupid):
        """Convenience function for group retrieval"""
        if groupid is None:
            raise ValueError("groupid mustn't be None")

        result = None
        failed_caches = []

        # go to caches
        for cache in self.subject_cache:
            result = cache.get_group(groupid)

            if result is not None:
                break
            else:
                failed_caches.append(cache)

        # not found
        if result is None:
            result = self.translator.groupid_to_group(groupid)

        if result is None:
            return result

        # update caches
        for cache in failed_caches:
            cache.add_groups([result])

        return result

    def get_project(self, name):
        return self.datasource.get_project(name)

    def get_projects(self, *args, **kwargs):
        return self.datasource.list_projects(*args, **kwargs)

    def get_project_names(self, *args, **kwargs):
        return self.datasource.get_project_names(*args, **kwargs)

    def get_projects_owned_by(self, *args, **kwargs):
        return self.datasource.get_projects_owned_by(*args, **kwargs)

    def get_projects_where_key_exists(self, *args, **kwargs):
        return self.datasource.get_projects_where_key_exists(*args, **kwargs)

    def get_projects_user_has_permissions_on(self, user):
        """Convenience function to retrieve all projects a user has permissions on"""
        return self.permission.get_projects_user_has_permissions_on(user)

    def get_permissions(self, user, object):
        """Convenience function for global permission enumeration"""
        return self.permission.get_permissions(None, user, object)

    def get_permission(self, user, object, permission):
        """Convenience function for permission retrieval"""
        return self.permission.get_permission(None, user, object, permission)

    def set_permission(self, user, object, permission, value):
        """Convenience function for permission retrieval"""
        return self.permission.set_permission(None, user, object, permission, value)

    def is_component_enabled(self, cls):
        component_name = cls.__module__ + '.' + cls.__name__

        return self.config.is_component_enabled(component_name)
