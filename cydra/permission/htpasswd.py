# -*- coding: utf-8 -*-
import os
import hashlib
from passlib.apache import HtpasswdFile

from cydra.component import Component, implements
from cydra.permission import User
from cydra.permission.interfaces import IUserTranslator, IUserAuthenticator, IUserStore
from cydra.error import InsufficientConfiguration

import logging
logger = logging.getLogger(__name__)

import warnings


class HtpasswdUser(User):

    supports_check_password = True
    supports_set_password = True
    valid_for_authentication = True

    def __init__(self, htpasswdusers, userid, **kwargs):
        super(HtpasswdUser, self).__init__(htpasswdusers.compmgr, userid, **kwargs)
        self.htpasswd = htpasswdusers.htpasswd

    def check_password(self, password):
        self.htpasswd.load_if_changed()
        return self.htpasswd.check_password(self.userid, password)

    def set_password(self, password):
        self.htpasswd.load_if_changed()
        self.htpasswd.set_password(self.id, password)
        self.htpasswd.save()


class HtpasswdUsers(Component):

    implements(IUserAuthenticator)
    implements(IUserTranslator)
    implements(IUserStore)

    def __init__(self):
        config = self.get_component_config()

        if 'file' not in config:
            raise InsufficientConfiguration(missing='file', component=self.get_component_name())

        self.htpasswd = HtpasswdFile(config['file'])

    def username_to_user(self, username):
        self.htpasswd.load_if_changed()
        if username in self.htpasswd.users():
            return HtpasswdUser(self, username, username=username, full_name=username)

    def userid_to_user(self, userid):
        if userid is None or userid == '*':
            warnings.warn("You should not call this directly. Use cydra.get_user()", DeprecationWarning, stacklevel=2)
            return self.compmgr.get_user(userid='*')

        self.htpasswd.load_if_changed()
        if userid in self.htpasswd.users():
            return HtpasswdUser(self, userid, username=userid, full_name=userid)
        else:
            # since the client was looking for a specific ID,
            # we return a dummy user object with empty data
            return User(self, userid, full_name='N/A')

    def groupid_to_group(self, groupid):
        pass

    def user_password(self, user, password):
        self.htpasswd.load_if_changed()
        return self.htpasswd.check_password(user.userid, password)

    def create_user(self, **kwargs):
        self.htpasswd.load_if_changed()

        userid = None
        if 'id' in kwargs:
            userid = kwargs['id']
        elif 'username' in kwargs:
            userid = kwargs['username']
        else:
            raise ValueError("No username/id specified")

        if userid in self.htpasswd.users():
            raise ValueError("User with this id already exists")
        else:
            self.htpasswd.set_password(userid, hashlib.sha1(os.urandom(8)).hexdigest())
            self.htpasswd.save()
            return userid
