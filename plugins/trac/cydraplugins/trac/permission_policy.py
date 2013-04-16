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

from trac.core import Component, implements
from trac.perm import IPermissionPolicy

import cydra

# Trac permissions usually are in the form of
# SUBSYSTEM_PERMISSION, so map the permission part to
# cydra permissions and use the subsystem as part of the object
# See http://trac.edgewall.org/wiki/TracPermissions
tracpermsuffix_to_generic = {
    'VIEW': 'read',
    'SQL_VIEW': 'read',

    'CREATE': 'write',
    'MODIFY': 'write',
    'DELETE': 'write',

    'APPEND': 'write',
    'RENAME': 'write',
    'CHGPROP': 'write',
    'EDIT_CC': 'write',
    'EDIT_DESCRIPTION': 'write',
    'EDIT_COMMENT': 'write',
    'BATCH_MODIFY': 'write',

    'ADMIN': 'admin'
}

# Permissions that should never be granted
blocked_permissions = [
    'VERSIONCONTROL_ADMIN',  # Would allow to just add foreign repositories by guessing the local path
    'TRAC_ADMIN',  # Can do anything

    'PERMISSION_GRANT',  # Could lead to confusion if further permissions are defined after cydra auth
    'PERMISSION_REVOKE',
    'PERMISSION_ADD',
    'PERMISSION_REMOVE'
]

class CydraPermissionPolicy(Component):
    """Trac permission policy that uses Cydra for authorization"""

    implements(IPermissionPolicy)

    def __init__(self):
        self.log.debug('CydraPolicy initializing')

        # We should reuse the last instance since the auth wrapper
        # will already have created one.
        #
        # DO NOT use compmgr as the variable name here, since
        # Trac will use it for its (incompatible) component manager
        # and this is a trac component
        self.cydra = cydra.Cydra.reuse_last_instance()

    def check_permission(self, action, username, resource, perm):
        self.log.debug('Checking %s on %s', action, resource)

        # map trac's anonymous to cydra's '*'
        if username == 'anonymous':
            username = '*'

        # Refuse to give blocked permissions right away
        if action in blocked_permissions:
            return False

        project_name = self.env.path[self.env.path.rfind("/") + 1:]
        project = self.cydra.get_project(project_name)
        if project is None:
            self.log.error('Unable to find project %r', project_name)
            return False

        user = self.cydra.get_user(userid=username)
        if user is None:
            self.log.error('Unknown user %r', username)
            return False

        # extract subsystem and perm (SUBSYSTEM_PERMISSION_BLA)
        subsystem = subsysperm = None
        try:
            subsystem, subsysperm = action.split('_', 1)
        except ValueError:
            self.log.warning('Trac action does not match SUBSYSTEM_PERMISSION pattern: %s', action)

        # if we have a subsystem + perm, try with the suffix mappings
        if subsystem is not None and subsysperm is not None:
            if subsysperm not in tracpermsuffix_to_generic:
                self.log.warning('Unable to map trac permission to cydra: %s', action)
            else:
                if project.get_permission(user,
                                          'plugins.trac.' + subsystem.lower(),
                                          tracpermsuffix_to_generic[subsysperm]):
                    return True

        # fallback: try the explicit permission, eg. plugins.trac:WIKI_ADMIN
        if project.get_permission(user, 'plugins.trac', action):
            return True

        # default to False since we are overriding everything.
        # in the future, we might want to return None instead, to
        # allow other permission policies to make a decision
        return False
