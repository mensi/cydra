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

from functools import partial

from cydra.component import Interface, Component, implements, ExtensionPoint, FallbackAttributeProxy

import logging
logger = logging.getLogger(__name__)

virtual_owner_permissions = {'admin': True, 'owner': True}

class PermissionProviderAttributeProxy(object):
    """Attribute Proxy object for permission providers"""

    def __init__(self):
        pass

    def __call__(self, interface, components, name):
        return partial(getattr(self, name), components)

    def get_permissions(self, components, project, user, object):
        perms = {}

        for provider in components:
            if hasattr(provider, 'get_permissions'):
                perms.update(provider.get_permissions(project, user, object))

        return perms

    def get_group_permissions(self, components, project, group, object):
        perms = {}

        for provider in components:
            if hasattr(provider, 'get_group_permissions'):
                perms.update(provider.get_group_permissions(project, group, object))

        return perms

    def get_permission(self, components, project, user, object, permission):
        value = None

        for provider in components:
            if hasattr(provider, 'get_permission'):
                value = provider.get_permission(project, user, object, permission)

            if value is not None:
                return value

    def get_group_permission(self, components, project, group, object, permission):
        value = None

        for provider in components:
            if hasattr(provider, 'get_group_permission'):
                value = provider.get_group_permission(project, group, object, permission)

            if value is not None:
                return value

    def set_permission(self, components, project, user, object, permission, value=None):
        for provider in components:
            if hasattr(provider, 'set_permission') and provider.set_permission(project, user, object, permission, value):
                return True

    def set_group_permission(self, components, project, group, object, permission, value=None):
        for provider in components:
            if hasattr(provider, 'set_group_permission') and provider.set_group_permission(project, group, object, permission, value):
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

    def get_permissions(self, project, user, object):
        """Retrieve all permissions a user has on a certain object
        
        :param project: project instance. If None is supplied, global permissions are checked
        :param user: User object. user of '*' means any user/guest access. None will enumerate all users
        :param object: object (dotted, hierarchical string) or None to enumerate all objects
            
        :return: dict of permission: value entries or a dict of object: {permission: value} entries if object is None"""
        pass

    def get_group_permissions(self, project, group, object):
        """Retrieve all permissions a group has on a certain object
        
        :param project: project instance. If None is supplied, global permissions are checked
        :param group: Group object
        :param object: object (dotted, hierarchical string) or None to enumerate all objects
            
        :return: dict of permission: value entries or a dict of object: {permission: value} entries if object is None"""
        pass

    def get_permission(self, project, user, object, permission):
        """Test if the user has this permission
        
        :param project: project instance. If None is supplied, global permissions are checked
        :param user: userid. user of '*' means any user/guest access
        :param object: object (dotted, hierarchical string)
        :param permission: permission (eg: read, write, view, edit, ...)
        
        :return: True if the user has this permission, False if not and None if undefined in this provider"""
        pass

    def get_group_permission(self, project, group, object, permission):
        """Test if the group has this permission
        
        :param project: project instance. If None is supplied, global permissions are checked
        :param group: Group object
        :param object: object (dotted, hierarchical string)
        :param permission: permission (eg: read, write, view, edit, ...)
        
        :return: True if the user has this permission, False if not and None if undefined in this provider"""
        pass

    def set_permission(self, project, user, object, permission, value=None):
        """Set or unset the permission
        
        :param project: project instance. If None is supplied, global permissions are set
        :param user: userid. user of '*' means any user/guest access
        :param object: object (dotted, hierarchical string)
        :param permission: permission (eg: read, write, view, edit, ...)
        
        :return: True if successfully set, None if this provider is not authoritative for this tuple"""
        pass

    def set_group_permission(self, project, group, object, permission, value=None):
        """Set or unset the permission
        
        :param project: project instance. If None is supplied, global permissions are set
        :param group: Group object
        :param object: object (dotted, hierarchical string)
        :param permission: permission (eg: read, write, view, edit, ...)
        
        :return: True if successfully set, None if this provider is not authoritative for this tuple"""
        pass

    def get_projects_user_has_permissions_on(self, userid):
        """Get all projects a user has permissions on
        
        :param userid: User to test for
        
        :return: List of projects
        """
        pass

class Subject(object):
    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.id)

    def __unicode__(self):
        return u'<%s: %s>' % (self.__class__.__name__, self.id)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

class Group(Subject):
    """Represents a group"""

    groupid = None
    name = None

    def __init__(self, component_manager, groupid, **kwargs):
        self.compmgr = component_manager
        self.groupid = groupid

        for key, value in kwargs.items():
            if not hasattr(self, key) or getattr(self, key) is None: #do not overwrite internals
                setattr(self, key, value)

    @property
    def id(self):
        return self.groupid

class User(Subject):
    """Represents a user
    
    Note that a user with userid '*' is considered an anonymous, unauthenticatable 
    guest user. The username and full_name should be set to 'Guest' in this case."""

    userid = None
    username = None
    full_name = None
    groups = []

    def __init__(self, component_manager, userid, **kwargs):
        self.compmgr = component_manager
        self.userid = userid

        for key, value in kwargs.items():
            if not hasattr(self, key) or getattr(self, key) is None or getattr(self, key) == []: #do not overwrite internals
                setattr(self, key, value)

    @property
    def is_guest(self):
        return self.userid == '*'

    @property
    def id(self):
        return self.userid

class IUserTranslator(Interface):
    """Translates various aspects of users"""

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

class IUserAuthenticator(Interface):
    """Authenticate users"""

    _iface_attribute_proxy = FallbackAttributeProxy()

    def user_password(self, user, password):
        """Authenticate users by user and password"""
        pass

def object_walker(obj):
    parts = obj.split('.')
    numparts = len(parts)
    for i, part in enumerate(parts):
        yield '.'.join(parts[0:numparts - i])

    if obj != '*':
        yield '*'

class StaticGlobalPermissionProvider(Component):
    """Global permissions defined in config"""

    implements(IPermissionProvider)

    def get_permissions(self, project, user, object):
        if project is not None:
            return {}

        if user is not None and not user.is_guest and object == 'projects':
            return {'create': True}

    def get_group_permissions(self, project, group, object):
        return {}

    def get_permission(self, project, user, object, permission):
        if project is not None:
            return None

        if user is not None and not user.is_guest and object == 'projects' and permission == 'create':
            return True

    def get_group_permission(self, project, group, object, permission):
        return None

    def set_permission(self, project, user, object, permission, value=None):
        return None

    def set_group_permission(self, project, group, object, permission, value=None):
        return None

    def get_projects_user_has_permissions_on(self, userid):
        return []

class InternalPermissionProvider(Component):
    """Stores permissions in the project's dict
    
    Example::
    
    'permissions': {
        '*': {'object': ['read']},
        'user': {'*': ['admin']}
    }
    """

    implements(IPermissionProvider)

    MODE_GROUP, MODE_USER = range(2)
    PERMISSION_ROOT = {MODE_GROUP: 'group_permissions', MODE_USER: 'permissions'}

    def get_permissions(self, project, user, obj):
        return self._get_permissions(self.MODE_USER, project, user, obj)

    def get_group_permissions(self, project, group, obj):
        return self._get_permissions(self.MODE_GROUP, project, group, obj)

    def _get_permissions(self, mode, project, subject, obj):
        if project is None:
            return {} # no project, no permissions

        # Resolve root of permissions and translator
        # depending on what we try to find
        permroot = self.PERMISSION_ROOT[mode]
        if mode == self.MODE_USER:
            translator = self.compmgr.get_user
        elif mode == self.MODE_GROUP:
            translator = self.compmgr.get_group
        else:
            raise ValueError('Unknown mode')

        res = {}
        perms = project.data.get(permroot, {})

        # if both subject and obj are None, return all (subject, obj, perm)
        # copy whole structure to prevent side effects 
        if subject is None and obj is None:
            for s, objs in perms.items():
                s = translator(s)
                res[s] = {}
                for o, perm in objs:
                    res[s][o] = perm.copy()

            # Inject global owner permissions if necessary
            if mode == self.MODE_USER:
                res.setdefault(project.owner, {}).setdefault('*', {}).update(virtual_owner_permissions)

            return res

        # construct a list of objects in the hierarchy
        if obj is not None:
            objparts = list(object_walker(obj))
            objparts.reverse()

        # if subject is none, find all subjects and return all (subject, perm)
        # we know here that obj is not none as we handled subject none and obj none
        # case above
        if subject is None:
            for s, p in perms.items():
                s = translator(s)

                res[s] = {}
                for o in objparts:
                    if o in p:
                        res[s].update(p[o].copy())

                # delete empty entries
                if res[s] == {}:
                    del res[s]

            # Inject global owner permissions if necessary
            if mode == self.MODE_USER:
                res.setdefault(project.owner, {}).update(virtual_owner_permissions)

            return res

        # subject is given.
        # in case of user mode, we also check the guest account
        subjects = [subject.id]
        if mode == self.MODE_USER:
            subjects.append('*')

        for p in [perms[x] for x in subjects if x in perms]:
            if obj is not None:
                for o in objparts:
                    if o in p:
                        res.update(p[o].copy())
            else:
                for o in p:
                    res[o] = p[o].copy()

        # this is the owner, Inject global owner perms
        if mode == self.MODE_USER and project.owner == subject:
            if obj is None:
                res.setdefault('*', {}).update(virtual_owner_permissions)
            else:
                res.update(virtual_owner_permissions)

        # also inject all group permissions
        if mode == self.MODE_USER:
            for group in [x for x in subject.groups if x is not None]: # safeguard against failing translators
                res.update(self.get_group_permissions(project, group, obj))

        return res

    def get_permission(self, project, user, obj, permission):
        return self._get_permission(self.MODE_USER, project, user, obj, permission)

    def get_group_permission(self, project, group, obj, permission):
        return self._get_permission(self.MODE_GROUP, project, group, obj, permission)

    def _get_permission(self, mode, project, subject, obj, permission):
        if project is None:
            return None
        if subject is None:
            return None
        if obj is None:
            return None

        # Resolve root of permissions and translator
        # depending on what we try to find
        permroot = self.PERMISSION_ROOT[mode]
        if mode == self.MODE_USER:
            translator = self.compmgr.get_user
        elif mode == self.MODE_GROUP:
            translator = self.compmgr.get_group
        else:
            raise ValueError('Unknown mode')

        # the owner can do everything
        if mode == self.MODE_USER and project.owner == subject:
            return True

        perms = project.data.get(permroot, {})

        # What we want to find here is a specific permission on a specific
        # object. First get the most precise. If we have a conflict, return the most positive one
        ret = None

        # If we are in user mode, check groups first
        if mode == self.MODE_USER:
            for group in subject.groups:
                ret = self._merge_perm_values(ret, self.get_group_permission(project, group, obj, permission))

        # root level -> find subject in perms
        if subject.id in perms:
            perms = perms[subject.id]
        elif mode == self.MODE_USER and '*' in perms: # if we are in user mode, fall back to guest
            perms = perms['*']
        else:
            return ret

        # subject level. Now walk the tree. deeper value overwrites lower
        subjret = None
        for o in object_walker(obj):
            if o in perms:
                # object level
                perm = perms[o].get(permission, None)
                if perm is None:
                    perm = perms[o].get('admin', None)
                if perm is not None:
                    subjret = perm

        # now merge subjret with the previous value
        return self._merge_perm_values(ret, subjret)

    def _merge_perm_values(self, a, b):
        if a == False or b == False:
            return False
        elif a == True or b == True:
            return True
        else:
            return None

    def set_permission(self, project, user, obj, permission, value=None):
        return self._set_permission(self.MODE_USER, project, user, obj, permission, value)

    def set_group_permission(self, project, group, obj, permission, value=None):
        return self._set_permission(self.MODE_GROUP, project, group, obj, permission, value)

    def _set_permission(self, mode, project, subject, obj, permission, value=None):
        if project is None:
            return None
        if subject is None:
            return None
        if obj is None:
            return None

        # Resolve root of permissions depending on what we try to find
        permroot = self.PERMISSION_ROOT[mode]

        if value is None:
            # check if the permission is set, otherwise do nothing
            if permission in project.data.get(permroot, {}).get(subject.id, {}).get(obj, {}):
                # remove permission
                del project.data[permroot][subject.id][obj][permission]

                if project.data[permroot][subject.id][obj] == {}:
                    del project.data[permroot][subject.id][obj]
                if project.data[permroot][subject.id] == {}:
                    del project.data[permroot][subject.id]
        else:
            project.data.setdefault(permroot, {}).setdefault(subject.id, {}).setdefault(obj, {})[permission] = value

        project.save()
        return True

    def get_projects_user_has_permissions_on(self, user):
        res = set([project for project in self.compmgr.get_projects_where_key_exists(['permissions', user.userid]) if any(project.data.get('permissions', {}).get(user.userid, {}).values())])
        for group in user.groups:
            res.update(set([project for project in self.compmgr.get_projects_where_key_exists(['group_permissions', group.id]) if any(project.data.get('group_permissions', {}).get(group.id, {}).values())]))
        res.update(self.compmgr.get_projects_owned_by(user))
        return res

class NopTranslator(Component):
    """Dummy user translator"""

    def username_to_user(self, username):
        return User(self.compmgr, username)

    def userid_to_user(self, userid):
        return User(self.compmgr, userid)
