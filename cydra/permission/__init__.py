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
from cydra.permission.interfaces import IPermissionProvider
from cydra.component import Component, implements, ExtensionPoint

import logging
logger = logging.getLogger(__name__)

virtual_owner_permissions = {'admin': True, 'owner': True}


class Subject(object):
    id = None

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.id)

    def __unicode__(self):
        return u'<%s: %s>' % (self.__class__.__name__, self.id)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

    def __ne__(self, other):
        return self.id != other.id

    def __cmp__(self, other):
        return cmp(self.id, other.id)


class Group(Subject):
    """Represents a group"""

    groupid = None
    name = None

    def __init__(self, component_manager, groupid, **kwargs):
        self.compmgr = component_manager
        self.groupid = groupid

        for key, value in kwargs.items():
            if not hasattr(self, key) or getattr(self, key) is None:  # do not overwrite internals
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

    supports_check_password = False
    supports_set_password = False
    valid_for_authentication = False

    def __init__(self, component_manager, userid, **kwargs):
        self.compmgr = component_manager
        self.userid = userid

        for key, value in kwargs.items():
            if not hasattr(self, key) or getattr(self, key) is None or getattr(self, key) == []:  # do not overwrite internals
                setattr(self, key, value)

    @property
    def is_guest(self):
        return self.userid == '*'

    @property
    def id(self):
        return self.userid

    def check_password(self, password):
        if not self.is_guest:
            logger.warn('Trying to check password on %s that does not support password checking %r (%r)', self.__class__, self.full_name, self.userid)
        return False

    def set_password(self, password):
        logger.warn('Trying to set password on %s that does not support password setting %r (%r)', self.__class__, self.full_name, self.userid)
        return False


def object_walker(obj):
    parts = obj.split('.')
    numparts = len(parts)
    for i, _ in enumerate(parts):
        yield '.'.join(parts[0:numparts - i])

    if obj != '*':
        yield '*'


class StaticGlobalPermissionProvider(Component):
    """Global permissions defined in config"""

    implements(IPermissionProvider)

    def get_configured_user_perms(self, user):
        """Get the applicable part of the config depending on the user"""
        if user.is_guest:
            return self.component_config.get("guest_permissions", {})
        else:
            section = self.component_config.get("user_permissions", {})
            if user.id in section:
                return section[user.id]
            elif user.username in section:
                return section[user.username]
            else:
                return section.get('*', {})

    def get_permissions(self, project, user, obj):
        if project is not None or user is None:
            return {}

        return self.get_configured_user_perms(user).get(obj, {})

    def get_group_permissions(self, project, group, obj):
        return {}

    def get_permission(self, project, user, obj, permission):
        if project is not None or user is None:
            return None

        return self.get_configured_user_perms(user).get(obj, {}).get(permission)

    def get_group_permission(self, project, group, obj, permission):
        return None

    def set_permission(self, project, user, obj, permission, value=None):
        return None

    def set_group_permission(self, project, group, obj, permission, value=None):
        return None

    def get_projects_user_has_permissions_on(self, userid):
        return []


class InternalPermissionProvider(Component):
    """Stores permissions in the project's dict

    Example::

    'permissions': {
        '*': {'repository.svn': {'read': True}},
        'user1': {'*': {'admin': True}}
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
            return {}  # no project, no permissions

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
            for group in [x for x in subject.groups if x is not None]:  # safeguard against failing translators
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
        elif mode == self.MODE_USER and '*' in perms:  # if we are in user mode, fall back to guest
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

