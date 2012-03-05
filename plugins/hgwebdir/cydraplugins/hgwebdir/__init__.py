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

import urlparse
import os.path

from mercurial.hgweb.hgwebdir_mod import hgwebdir
from mercurial import ui

import cydra
from cydra.component import Component, implements
from cydra.web.wsgihelper import HTTPBasicAuthenticator
from cydra.web.frontend.hooks import IRepositoryViewerProvider, IProjectFeaturelistItemProvider

import logging
logger = logging.getLogger(__name__)

class HgWebDirIntegration(Component):
    """Cydra component for integration between HgWebDir and Cydra"""

    implements(IRepositoryViewerProvider)
    implements(IProjectFeaturelistItemProvider)

    def __init__(self):
        pass

    def get_repository_viewers(self, repository):
        """Announce hgwebdir as a web viewer"""
        if 'url_base' not in self.component_config:
            logger.warning("url_base is not configured!")
        elif repository.type == 'hg':
            return ('HgWebDir', self.component_config['url_base'] + '/' + repository.project.name + '/' + repository.name)

    def get_project_featurelist_items(self, project):
        if project.get_repository_type('hg').get_repositories(project):
            if 'url_base' not in self.component_config:
                logger.warning("url_base is not configured!")
                return ('HgWebDir', [])

            return ('HgWebDir', [{'href': self.component_config['url_base'] + '/' + project.name,
                                  'name': 'view'}])

class HgWebDir(object):
    """WSGI application"""

    def __init__(self, hgwebdirconfig=None, cyd=None):
        if cyd is None:
            cyd = cydra.Cydra()

        self.cydra = self.compmgr = cyd
        self.authenticator = HTTPBasicAuthenticator(self.compmgr)

        self.config = config = cyd.config.get_component_config('cydra.repository.hg.HgRepositories', {})
        if 'base' not in config:
            raise Exception("hg base path not configured")

        baseui = None

        if hgwebdirconfig is None:
            hgwebdirconfig = {'/': os.path.join(config['base'], '**')}

            baseui = ui.ui()

            # provide sensible defaults
            baseui.setconfig("web", "allow_archive", "gz, zip, bz2") #read access -> downloading archive should be fine
            baseui.setconfig("web", "allow_push", "*") # we are doing access checks, not hg
            baseui.setconfig("web", "push_ssl", "false") # enforcing SSL is left to the user / apache
            baseui.setconfig("web", "encoding", "utf-8")

        self.hgwebdir = hgwebdir(hgwebdirconfig, baseui)

    def __call__(self, environ, start_response):
        """Process hg request
        
        URLs are in the form of /project/repository
        """
        path = environ.get('PATH_INFO', '')
        user = self.authenticator(environ)

        project = None
        repository = None

        try:
            path_components = path.strip('/').split('/')
            project = path_components[0]

            if project == 'static':
                return self.hgwebdir(environ, start_response)

            project = self.cydra.get_project(project)

            if len(path_components) == 1:
                if project.get_permission(user, "repository.hg", "read"):
                    return self.hgwebdir(environ, start_response)
                else:
                    return self.require_authorization(environ, start_response)
            else:
                repository = path_components[1]
                repository = project.get_repository('hg', repository)
        except Exception as e:
            logger.exception("Unknown Repository/Project")
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            return 'Unknown Repository/Project or invalid URL: ' + str(e)

        # auth
        method = environ.get('REQUEST_METHOD', '').upper()

        logger.debug('User %s (%s) is attempting to visit "%s" (%s)', user.full_name, user.userid, environ.get('PATH_INFO'), method)

        if method in ['GET', 'HEAD']:
            # read
            if repository.has_read_access(user):
                return self.hgwebdir(environ, start_response)
            else:
                if not user.is_guest:
                    start_response('401 Unauthorized', [('Content-Type', 'text/plain')]) # mercurial goes into an infinite loop if we are RFC-compliant
                    return 'Authorization needed to access this repository'
                else:
                    return self.require_authorization(environ, start_response)
        else:
            # write
            if repository.has_write_access(user):
                return self.hgwebdir(environ, start_response)
            else:
                if not user.is_guest:
                    start_response('401 Unauthorized', [('Content-Type', 'text/plain')]) # mercurial goes into an infinite loop if we are RFC-compliant
                    return 'Authorization needed to access this repository'
                else:
                    return self.require_authorization(environ, start_response)

    def require_authorization(self, environ, start_response):
        start_response('401 Unauthorized', [('Content-Type', 'text/plain'), ('WWW-Authenticate', 'Basic realm="' + self.compmgr.config.get('web').get('auth_realm').encode('utf-8') + '"')])
        return 'Authorization needed to access this repository'

def standalone_serve():
    """Standalone WSGI Server for debugging purposes"""
    from werkzeug import run_simple
    import sys

    port = 8080
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    app = HgWebDir()

    #from werkzeugprofiler import ProfilerMiddleware
    #app = ProfilerMiddleware(app, stream=open('profile_stats.txt', 'w'), accum_count=100, sort_by=('cumulative', 'calls'), restrictions=(.1,))

    run_simple('0.0.0.0', port, app, use_reloader=True,
            use_debugger=True, #use_evalex=True,
            )
