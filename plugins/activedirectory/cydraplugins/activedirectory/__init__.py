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
import os.path
import re

import ldap
from ldap.ldapobject import ReconnectLDAPObject

from cydra.component import Component, implements
from cydra.permission import IUserTranslator, IUserAuthenticator, User, Group

import logging
logger = logging.getLogger(__name__)

LDAP_ESCAPES = {
    '*':  '\\2A',
    '(':  '\\28',
    ')':  '\\29',
    '\\': '\\5C',
    '\0': '\\00',
}
_ldap_escape_pat = re.compile('|'.join(re.escape(k) for k in LDAP_ESCAPES.keys()))

def ldap_escape(s):
    return _ldap_escape_pat.sub(lambda x: LDAP_ESCAPES[x.group()], s)

def force_unicode(txt):
    try:
        return unicode(txt)
    except UnicodeDecodeError:
        pass
    
    orig = txt
    if type(txt) != str:
        txt = str(txt)
        
    for args in [('utf-8',), ('latin1',), ('ascii', 'replace')]:
        try:
            return txt.decode(*args)
        except UnicodeDecodeError:
            pass
    raise ValueError("Unable to force %s object %r to unicode" % (type(orig).__name__, orig))

class LdapLookup(object):

    connection = None
    uri = None
    user = None
    password = None

    user_searchbase = ''
    group_searchbase = ''

    user_searchfilter = {'objectClass': 'user'}
    group_searchfilter = {'objectClass': 'group'}

    def __init__(self, **kw):
        for key, item in kw.items():
            if hasattr(self, key) and not key.startswith('_'):
                setattr(self, key, item)

    def connect(self):
        try:
            self.connection = ReconnectLDAPObject(self.uri)
            if self.user is not None:
                self.connection.simple_bind_s(self.user, self.password)
        except:
            logger.exception("LDAP connection failed")
            return False
        return True

    def get_safe(self, basedn, **kw):
        return self.get(basedn, **dict([(ldap_escape(k), ldap_escape(v)) for k, v in kw.iteritems()]))

    def get(self, basedn, **kw):
        search = '(&%s)' %  ''.join(['(%s=%s)' % item for item in kw.iteritems()])
        result = self.connection.search_s(basedn, ldap.SCOPE_SUBTREE, search)
        return result

    def get_dn(self, dn):
        res = self.connection.search_s(dn, ldap.SCOPE_BASE, '(objectClass=*)')
        if len(res) == 0:
            return None
        else:
            return res[0]

    def get_users(self):
        return self.get(self.user_searchbase, **self.user_searchfilter)

    def get_user(self, username):
        search = self.user_searchfilter.copy()
        if '@' in username:
            search['userPrincipalName'] = username
        else:
            search['sAMAccountName'] = username

        res = self.get_safe(self.user_searchbase, **search)
        if len(res) == 0:
            return None
        else:
            return res[0]

    def get_groups(self):
        return self.get(self.group_searchbase, **self.group_searchfilter)

    def get_group(self, groupname):
        search = self.group_searchfilter.copy()
        search['name'] = groupname
        res = self.get_safe(self.group_searchbase, **search)

        if len(res) == 0:
            return None
        else:
            return res[0]


class ADUsers(Component):

    implements(IUserAuthenticator)
    implements(IUserTranslator)

    def __init__(self):
        config = self.get_component_config()

        self.ldap = LdapLookup(**config)
        if not self.ldap.connect():
            raise Exception('Connection failed')

    def username_to_user(self, username):
        user = self._ldap_to_user(self.ldap.get_user(username))
        if user is None:
            logger.error("Translation failed for: %s" % username)
        return user

    def userid_to_user(self, userid):
        if userid is None or userid == '*':
            return User(self.compmgr, '*', username='Guest', full_name='Guest')

        user = self._ldap_to_user(self.ldap.get_user(userid))
        if user is None:
            logger.error("Translation failed for: %s" % userid)

            # since the client was looking for a specific ID,
            # we return a dummy user object with empty data
            return User(self.compmgr, userid, full_name='N/A')
        else:
            return user

    def _ldap_to_user(self, data):
        if data is None:
            return None

        dn, userobj = data

        if 'memberOf' in userobj:
            groups = [self._ldap_to_group(self.ldap.get_dn(x)) for x in userobj['memberOf']]
        else:
            groups = []

        return User(self.compmgr, 
                userobj['userPrincipalName'][0], 
                username=userobj['sAMAccountName'][0], 
                full_name=force_unicode(userobj['displayName'][0]), groups=groups)

    def groupid_to_group(self, groupid):
        group = self._ldap_to_group(self.ldap.get_group(groupid))
        if group is None:
            logger.error("Group lookup error for %s", groupid)
        return group

    def _ldap_to_group(self, data):
        if data is None:
            return None
        dn, groupobj = data
        return Group(self.compmgr,
                groupobj['name'][0],
                name=groupobj['name'][0])

    def user_password(self, user, password):
        if not user or not password:
            return False

        try:
            conn = ldap.initialize(self.get_component_config()['uri'])
            conn.simple_bind_s(user.userid, password)
        except ldap.INVALID_CREDENTIALS:
            logger.exception("Authentication failed")
            return False

        return True
