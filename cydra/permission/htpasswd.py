# -*- coding: utf-8 -*-
import os.path
from passlib.apache import HtpasswdFile

from cydra.component import Component, implements
from cydra.permission import IUserTranslator, IUserAuthenticator, User, Group
from cydra.error import CydraError, InsufficientConfiguration

import logging
logger = logging.getLogger(__name__)

import warnings

class HtpasswdUsers(Component):

    implements(IUserAuthenticator)
    implements(IUserTranslator)

    def __init__(self):
        config = self.get_component_config()

        if 'file' not in config:
            raise InsufficientConfiguration(missing='file', component=self.get_component_name())

        self.htpasswd = HtpasswdFile(config['file'])

    def username_to_user(self, username):
        self.htpasswd.load_if_changed()
        if username in self.htpasswd.users():
            return User(self.compmgr, username, username=username, full_name=username)


    def userid_to_user(self, userid):
        if userid is None or userid == '*':
            warnings.warn("You should not call this directly. Use cydra.get_user()", DeprecationWarning, stacklevel=2)
            return User(self.compmgr, '*', username='Guest', full_name='Guest')

        self.htpasswd.load_if_changed()
        if userid in self.htpasswd.users():
            return User(self.compmgr, userid, username=userid, full_name=userid)
        else:
            # since the client was looking for a specific ID,
            # we return a dummy user object with empty data
            return User(self.compmgr, userid, full_name='N/A')

    def groupid_to_group(self, groupid):
        pass

    def user_password(self, user, password):
        self.htpasswd.load_if_changed()
        return self.htpasswd.check_password(user.userid, password)
