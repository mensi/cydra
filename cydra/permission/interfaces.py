# -*- coding: utf-8 -*-
#
# Copyright 2013 Manuel Stocker <mensi@mensi.ch>
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
from functools import partial
from cydra.component import Interface, FallbackAttributeProxy


class PermissionProviderAttributeProxy(object):
    """Attribute Proxy object for permission providers"""

    def __init__(self):
        pass

    def __call__(self, interface, components, name):
        return partial(getattr(self, name), components)

    def get_permissions(self, components, project, user, obj):
        perms = {}

        for provider in components:
            if hasattr(provider, 'get_permissions'):
                perms.update(provider.get_permissions(project, user, obj))

        return perms

    def get_group_permissions(self, components, project, group, obj):
        perms = {}

        for provider in components:
            if hasattr(provider, 'get_group_permissions'):
                perms.update(provider.get_group_permissions(project, group, obj))

        return perms

    def get_permission(self, components, project, user, obj, permission):
        value = None

        for provider in components:
            if hasattr(provider, 'get_permission'):
                value = provider.get_permission(project, user, obj, permission)

            if value is not None:
                return value

    def get_group_permission(self, components, project, group, obj, permission):
        value = None

        for provider in components:
            if hasattr(provider, 'get_group_permission'):
                value = provider.get_group_permission(project, group, obj, permission)

            if value is not None:
                return value

    def set_permission(self, components, project, user, obj, permission, value=None):
        for provider in components:
            if hasattr(provider, 'set_permission') and provider.set_permission(project, user, obj, permission, value):
                return True

    def set_group_permission(self, components, project, group, obj, permission, value=None):
        for provider in components:
            if hasattr(provider, 'set_group_permission') and provider.set_group_permission(project, group, obj, permission, value):
                return True

    def get_projects_user_has_permissions_on(self, components, user):
        projects = set()

        for provider in components:
            if hasattr(provider, 'get_projects_user_has_permissions_on'):
                projects.update(provider.get_projects_user_has_permissions_on(user))

        return projects


class IPermissionProvider(Interface):
    """Used to lookup permissions for a user

    Permissions are given for a userid,object tuple. A permission provider
    can either return True (user has the specified permission on the specified object),
    False (user does not have the permission) or None (provider has no authority)
    """

    _iface_attribute_proxy = PermissionProviderAttributeProxy()

    def get_permissions(self, project, user, obj):
        """Retrieve all permissions a user has on a certain object

        :param project: project instance. If None is supplied, global permissions are checked
        :param user: User object. user of '*' means any user/guest access. None will enumerate all users
        :param obj: object (dotted, hierarchical string) or None to enumerate all objects

        :return: dict of permission: value entries or a dict of object: {permission: value} entries if object is None"""
        pass

    def get_group_permissions(self, project, group, obj):
        """Retrieve all permissions a group has on a certain object

        :param project: project instance. If None is supplied, global permissions are checked
        :param group: Group object
        :param obj: object (dotted, hierarchical string) or None to enumerate all objects

        :return: dict of permission: value entries or a dict of object: {permission: value} entries if object is None"""
        pass

    def get_permission(self, project, user, obj, permission):
        """Test if the user has this permission

        :param project: project instance. If None is supplied, global permissions are checked
        :param user: userid. user of '*' means any user/guest access
        :param obj: object (dotted, hierarchical string)
        :param permission: permission (eg: read, write, view, edit, ...)

        :return: True if the user has this permission, False if not and None if undefined in this provider"""
        pass

    def get_group_permission(self, project, group, obj, permission):
        """Test if the group has this permission

        :param project: project instance. If None is supplied, global permissions are checked
        :param group: Group object
        :param obj: object (dotted, hierarchical string)
        :param permission: permission (eg: read, write, view, edit, ...)

        :return: True if the user has this permission, False if not and None if undefined in this provider"""
        pass

    def set_permission(self, project, user, obj, permission, value=None):
        """Set or unset the permission

        :param project: project instance. If None is supplied, global permissions are set
        :param user: userid. user of '*' means any user/guest access
        :param obj: object (dotted, hierarchical string)
        :param permission: permission (eg: read, write, view, edit, ...)

        :return: True if successfully set, None if this provider is not authoritative for this tuple"""
        pass

    def set_group_permission(self, project, group, obj, permission, value=None):
        """Set or unset the permission

        :param project: project instance. If None is supplied, global permissions are set
        :param group: Group object
        :param obj: object (dotted, hierarchical string)
        :param permission: permission (eg: read, write, view, edit, ...)

        :return: True if successfully set, None if this provider is not authoritative for this tuple"""
        pass

    def get_projects_user_has_permissions_on(self, userid):
        """Get all projects a user has permissions on

        :param userid: User to test for

        :return: List of projects
        """
        pass


class IUserTranslator(Interface):
    """Translates IDs and Names to Users resp. their Groups

    A user translator is used to get from an identifying ID or username
    to a User instance. Since you might want to integrate user/group
    backends that do not support write access, this is distinct to
    IUserStore. An example for this would by a read-only LDAP backend.
    """

    _iface_attribute_proxy = FallbackAttributeProxy()

    def username_to_user(self, username):
        """Given a username (what a user can use to log in) find the user

        :returns: a User object on success, None on failure"""
        pass

    def userid_to_user(self, userid):
        """Given a userid find the user

        A translator should construct a guest user if the userid is '*'."""
        pass

    def groupid_to_group(self, userid):
        """Given a groupid find the group

        :returns: a Group object on success, None on failure"""
        pass


class IUserStore(Interface):
    """Used to create/modify users"""

    _iface_single_extension = True

    def create_user(self, **kwargs):
        """Create a user with the given attributes

        If no id was given and the store supports automatic generation
        (or in case the store *requires* automatic generation) the store
        should generate an id.

        If arguments have been given that cannot be fulfilled, eg:
          * illegal characters in username
          * no support for passwords but a password was given
          * userid given but ids are assigned by the backend

        A ValueError should be raised

        :param username: Desired username
        :param password: Desired password
        :returns: UserID if user generation was successful
        """
        pass


class IUserAuthenticator(Interface):
    """Authenticate users"""

    _iface_attribute_proxy = FallbackAttributeProxy()

    def user_password(self, user, password):
        """Authenticate users by user and password"""
        pass
