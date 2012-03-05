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

from cydra.component import Interface, Component, implements
from cydra.util import SimpleCache

class ISubjectCache(Interface):
    def get_user(self, userid):
        pass

    def get_user_by_name(self, username):
        pass

    def get_users(self, userids):
        pass

    def add_users(self, users):
        pass

    def get_group(self, groupid):
        pass

    def get_groups(self, groupids):
        pass

    def add_groups(self, groups):
        pass

class MemorySubjectCache(Component):
    """Caches subjects in memory
    """

    implements(ISubjectCache)

    def __init__(self):
        config = self.get_component_config()
        groupttl = config.get('group_ttl', 60 * 60 * 24 * 14)
        groupsize = config.get('group_size', 50)
        userttl = config.get('user_ttl', 5 * 60)
        usersize = config.get('user_size', 500)

        self.groupcache = SimpleCache(lifetime=groupttl, killtime=groupttl, maxsize=groupsize)
        self.usercache = SimpleCache(lifetime=userttl, killtime=userttl, maxsize=usersize)
        self.usernamemap = {}

    def get_user(self, userid):
        return self.usercache.get(userid)

    def get_user_by_name(self, username):
        if username in self.usernamemap:
            return self.get_user(self.usernamemap[username])

    def get_users(self, userids):
        res = {}
        for userid in userids:
            res[userid] = self.get_user(userid)
        return res

    def add_users(self, users):
        for user in users:
            self.usercache.set(user.userid, user)
            self.usernamemap[user.username] = user.userid

    def get_group(self, groupid):
        return self.groupcache.get(groupid)

    def get_groups(self, groupids):
        res = {}
        for groupid in groupids:
            res[groupid] = self.get_group(groupid)
        return res

    def add_groups(self, groups):
        for group in groups:
            self.groupcache.set(group.groupid, group)
