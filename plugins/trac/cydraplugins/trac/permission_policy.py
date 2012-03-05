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

from trac.core import *
from trac.perm import PermissionSystem, IPermissionPolicy

import cydra

write_permissions = ['MILESTONE_CREATE', 'MILESTONE_MODIFY', 'MILESTONE_DELETE', 'REPORT_CREATE', 'REPORT_DELETE', 'REPORT_MODIFY', 'WIKI_CREATE', 'WIKI_DELETE', 'WIKI_MODIFY', 'TICKET_CREATE']
admin_permissions = ['TICKET_ADMIN', 'MILESTONE_ADMIN', 'ROADMAP_ADMIN', 'WIKI_ADMIN']
blocked_permissions = ['VERSIONCONTROL_ADMIN', 'TRAC_ADMIN', 'PERMISSION_GRANT', 'PERMISSION_REVOKE']

class CydraPermissionPolicy(Component):
    implements(IPermissionPolicy)

    def __init__(self):
        self.log.debug('CydraPolicy initializing')

        self.cydra = cydra.Cydra() # DO NOT set compmgr to cydra as this is a Trac component!

    def check_permission(self, action, username, resource, perm):
        self.log.debug('Checking %s on %s', action, resource)

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

        # first, try the explicit permission
        if project.get_permission(user, 'plugins.trac', action):
            return True

        # if that didn't work, generalize them
        simple_perm = 'read'
        if action in admin_permissions:
            simple_perm = 'admin'
        if action in write_permissions:
            simple_perm = 'write'

        return bool(project.get_permission(user, 'plugins.trac', simple_perm))
