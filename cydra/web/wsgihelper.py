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
import urllib

import cydra
from cydra.component import ExtensionPoint
from cydra.permission import IUserTranslator, IUserAuthenticator
from cydra.util import SimpleCache

import logging
logger = logging.getLogger(__name__)

def is_urldecode_necessary(useragent):
    """Determine if this user agent needs a manual urldecode of the credentials
    
    Some user agents do not properly urldecode the credentials that have been supplied
    on the URI. git before version 1.7.3.2 is a prominent case."""
    if useragent.startswith('git/'):
        # git got urldecode support in 1.7.3.2 (commit: f39f72d8cf03b61407f64460eba3357ec532280e)
        # the useragent is usually: git/x.x.x.x 
        # but msysgit can do things like git/x.x.x.msysgit.x or x.x.x.x.msysgit.x 
        #
        # this is too simple: gitversion = tuple([int(x) for x in useragent[4:].split('.')])
        gitversion = useragent[4:].split('.') # split
        gitversion = [int(x) if x.isdigit() else 0 for x in gitversion] # make ints, replace text with 0
        if len(gitversion) < 4:
            gitversion.extend(0 for x in range(0, 4 - len(gitversion))) # pad with 0 to get 4 components
        gitversion = tuple(gitversion)

        logger.debug("Detected git version number %r", gitversion)

        if gitversion < (1, 7, 3, 2):
            return True
    return False

class InsufficientPermissions(Exception):
    pass

class AuthenticationMiddleware(object):

    def __init__(self, cyd, next_app):
        """Initialize Middleware
        
        :param cyd: Cydra instance"""
        self.compmgr = cyd
        self.next_app = next_app
        self.authenticator = HTTPBasicAuthenticator(cyd)

    def __call__(self, environ, start_response):
        """WSGI Middleware"""

        user = self.authenticator(environ)

        try:
            return self.next_app(environ, start_response)
        except InsufficientPermissions as e:
            if user.is_guest:
                start_response('401 Unauthorized', [('Content-Type', 'text/plain'), ('WWW-Authenticate', 'Basic realm="' + self.compmgr.config.get('web').get('auth_realm').encode('utf-8') + '"')])
                return "Unauthorized"
            else:
                start_response('403 Forbidden', [('Content-Type', 'text/plain')])
                return "Forbidden"

class HTTPBasicAuthenticator(object):

    translator = ExtensionPoint(IUserTranslator)
    authenticator = ExtensionPoint(IUserAuthenticator)

    def __init__(self, cyd=None):
        if cyd is None:
            cyd = cydra.Cydra()

        self.cydra = self.compmgr = cyd
        self.cache = SimpleCache()

    def __call__(self, environ):
        # default to guest
        environ['cydra_user'] = self.cydra.get_user(userid='*')

        # consult the REMOTE_USER variable. If this is set, apache or some other part
        # already did the authetication. We will trust that judgement
        userid = environ.get('REMOTE_USER', None)
        logger.debug('Remote user: "%s"', str(userid))

        if userid is None:
            # Nothing already set. Perform HTTP auth ourselves
            author = environ.get('HTTP_AUTHORIZATION', None)
            logger.debug("No remote user supplied, trying Authorization header")

            if author is None:
                logger.debug("No Authorization header supplied")
                return self.cydra.get_user(userid='*')

            if author.strip().lower()[:5] != 'basic':
                # atm only basic is supported
                logging.warning("User tried to use a different auth method (not basic): %s")
                return self.cydra.get_user(userid='*')

            userpw_base64 = author.strip()[5:].strip()
            if userpw_base64 in self.cache:
                # login cached as successful, we can now set REMOTE_USER for further use
                user = self.cache.get(userpw_base64)
                logger.debug('Author header found in cache, user: %s (%s)', user.full_name, user.userid)
                environ['REMOTE_USER'] = user.userid
                environ['cydra_user'] = user
                return user

            userid, pw = userpw_base64.decode('base64').split(':', 1)

            # yes, you probably don't want to leak information about a password 
            # such as its length into the log. The length helps to debug issues with extra
            # whitespace though
            logger.debug('Got user "%s" with passwordlen %d. Agent: %s', userid, len(pw), environ.get('HTTP_USER_AGENT', 'None'))

            if is_urldecode_necessary(environ.get('HTTP_USER_AGENT', '')):
                logger.info('Client is broken w.r.t. url encoding: %s', environ.get('HTTP_USER_AGENT', 'None'))
                userid = urllib.unquote(userid)
                pw = urllib.unquote(pw)

            user = self.translator.username_to_user(userid)
            if user is None:
                logger.debug('Lookup for %s failed', userid)
                user = self.cydra.get_user(userid='*')

            logger.debug('User lookup gave %s (%s)', user.full_name, user.userid)

            if user.is_guest:
                logger.info('User %s resolved to guest', userid)
                return user

            elif self.authenticator.user_password(user, pw):
                # login successful, we can now set REMOTE_USER for further use
                environ['REMOTE_USER'] = user.userid
                environ['cydra_user'] = user

                # and cache
                logger.debug('Caching login data for %s (%s)', user.full_name, user.userid)
                self.cache.set(userpw_base64, user)

                return user
            else:
                logger.info('User %s (%s) supplied a wrong password', user.full_name, user.userid)
                return self.cydra.get_user(userid='*')
        else:
            logger.debug("Got REMOTE_USER=%s", userid)

            if userid in self.cache:
                return self.cache.get(userid)
            else:
                user = self.translator.username_to_user(userid)

                if user is None:
                    logger.debug('Lookup for %s failed', userid)
                    user = self.cydra.get_user(userid='*')

                if not user.is_guest:
                    self.cache.set(userid, user)

                return user

class WSGIAuthnzHelper(object):

    translator = ExtensionPoint(IUserTranslator)
    authenticator = ExtensionPoint(IUserAuthenticator)

    def __init__(self, environ_to_perm, cyd=None):
        """Initialize Authnz helper
        
        :param environ_to_perm: Callable that returns the project or project name and the object an environment corresponds to as a tuple(project, object)"""

        if cyd is None:
            cyd = cydra.Cydra()

        self.cydra = self.compmgr = cyd
        self.environ_to_perm = environ_to_perm

    def check_password(self, environ, username, password):
        """Function for WSGIAuthUserScript
        
        Authenticates the user regardless of environment"""
        user = self.translator.username_to_user(username)

        return self.authenticator.user_password(user, password)

    def groups_for_user(self, environ, username):
        """Function for WSGIAuthGroupScript
        
        Returns the permissions a user has on the object corresponding to the environment"""
        user = self.translator.username_to_user(username)

        project, obj = self.environ_to_perm(environ)

        if isinstance(project, basestring):
            project = self.cydra.get_project(project)

            if project is None:
                return []

        return [perm.encode('utf-8') for (perm, value) in project.get_permissions(user, obj).items() if value == True]

def require_authorization(environ, start_response, realm='cydra', msg=''):
    start_response('401 Unauthorized', [('Content-Type', 'text/plain'), ('WWW-Authenticate', 'Basic realm="' + realm + '"')])
    return msg

def move_projectname_into_scriptname(environ, projectname):
    """Moves the project name from PATH_INFO to SCRIPT_NAME
    
    Example:
    
    /some/path/project/repository/more
     SCRIPT   | PATH INFO        
    ->
     SCRIPT           |  PATH INFO"""

    environ['SCRIPT_NAME'] = environ.get('SCRIPT_NAME', '').rstrip('/') + '/' + projectname
    environ['PATH_INFO'] = environ.get('PATH_INFO', '')[len(projectname) + 1:] if environ.get('PATH_INFO', '').startswith('/' + projectname) else environ.get('PATH_INFO', '')
