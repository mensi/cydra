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

from git_http_backend import GitHTTPBackendInfoRefs, GitHTTPBackendSmartHTTP, StaticWSGIServer

import cydra
from cydra.component import Component, implements
from cydra.web.wsgihelper import HTTPBasicAuthenticator, move_projectname_into_scriptname
from cydra.web.frontend.hooks import IRepositoryViewerProvider, IProjectFeaturelistItemProvider

import logging
logger = logging.getLogger(__name__)

class GitIntegration(Component):
    """Cydra component for integration between Git and Cydra"""

    implements(IRepositoryViewerProvider)
    implements(IProjectFeaturelistItemProvider)

    def __init__(self):
        pass

    def get_repository_viewers(self, repository):
        """Announce git as a web viewer"""
        if 'url_base' not in self.component_config:
            logger.warning("url_base is not configured!")
        elif repository.type == 'git':
            return ('Git HTTP', self.component_config['url_base'] + '/' + repository.project.name + '/' + repository.name + '.git')

    def get_project_featurelist_items(self, project):
        if project.get_repository_type('git').get_repositories(project):
            if 'url_base' not in self.component_config:
                logger.warning("url_base is not configured!")
                return ('Git HTTP', [])

            return ('Git HTTP', [{'href': self.component_config['url_base'] + '/' + project.name,
                                  'name': 'view'}])

class GitHTTP(object):
    """WSGI application"""

    def __init__(self, cyd=None, gitviewer=None):
        if cyd is None:
            cyd = cydra.Cydra()

        self.cydra = self.compmgr = cyd
        self.authenticator = HTTPBasicAuthenticator(self.compmgr)
        self.gitviewer = gitviewer

        self.config = config = cyd.config.get_component_config('cydra.repository.git.GitRepositories', {})
        if 'base' not in config:
            raise Exception("git base path not configured")

        self.git_inforefs_handler = GitHTTPBackendInfoRefs(content_path=config['base'], uri_marker='')
        self.git_rpc_handler = GitHTTPBackendSmartHTTP(content_path=config['base'], uri_marker='')
        self.static_handler = StaticWSGIServer(content_path=config['base'], uri_marker='')

        self.git_inforefs_handler.repo_auto_create = False
        self.git_rpc_handler.repo_auto_create = False
        self.static_handler.repo_auto_create = False

    def __call__(self, environ, start_response):
        """Process git request
        
        URLs are in the form of /project/repo.git
        """

        url = path = environ.get('PATH_INFO', '')
        query_string = environ.get('QUERY_STRING', '')
        if query_string:
            url += '?' + query_string

        project = None
        repository = None

        # Project discovery
        pathlets = path.strip('/').split('/')
        if len(pathlets) > 0:
            project = pathlets[0]
        else:
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            return 'No project specified'

        project = self.cydra.get_project(project)
        if project is None:
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            return 'Unknown Project'

        # add repo base for project to routing args
        environ.setdefault('wsgiorg.routing_args', ([], {}))[1]['repository_base'] = os.path.join(self.config['base'], project.name)
        # add site_name to routing args
        environ.setdefault('wsgiorg.routing_args', ([], {}))[1]['site_name'] = project.name

        # Authentication
        user = self.authenticator(environ)
        logger.debug('User "%s" is attempting to access project "%s"', str(user), project.name)

        # Repository discovery
        if len(pathlets) > 1:
            repository = pathlets[1]

            if repository[-4:] != '.git':
                # assume its for static media of the viewer
                if self.gitviewer is not None:
                    move_projectname_into_scriptname(environ, project.name)
                    return self.gitviewer(environ, start_response)
                else:
                    start_response('404 Not Found', [('Content-Type', 'text/plain')])
                    return 'No gitviewer configured'

            repository = project.get_repository('git', repository[:-4])
            if repository is None:
                start_response('404 Not Found', [('Content-Type', 'text/plain')])
                return 'Unknown repository'
        else:
            if self.gitviewer is not None:
                if project.get_permission(user, 'repository.git', 'read'):
                    move_projectname_into_scriptname(environ, project.name)
                    return self.gitviewer(environ, start_response)
                else:
                    return self.require_authorization(environ, start_response)
            else:
                start_response('404 Not Found', [('Content-Type', 'text/plain')])
                return 'No repository specified and no gitviewer configured'

        #
        # We are in a repository now. Either it is a command for the 
        # old or smart HTTP backends, otherwise forward to gitviewer
        #
        git_command = None
        working_path = project.name + '/' + repository.name + '.git' if repository else project.name  # this is a URL. Dont use os.path.join
        handler = None

        # add working path to routing args
        environ.setdefault('wsgiorg.routing_args', ([], {}))[1]['working_path'] = working_path

        if pathlets[2:4] == ['info', 'refs']:
            # old style http. /project/repo/info/refs?service=git-command
            git_command = urlparse.parse_qs(query_string).get('service', [''])[0]
            if not git_command:
                git_command = "DUMMY-static-read"
                working_path = path
                handler = self.static_handler
            else:
                logger.debug("repo path = %s" % working_path)
                handler = self.git_inforefs_handler

        elif len(pathlets) > 2 and pathlets[2] == 'refs':
            # old style http /project/repo/refs/*
            git_command = "DUMMY-static-read"
            working_path = path
            handler = self.static_handler

        elif len(pathlets) > 2 and pathlets[2][:4] == 'git-':
            # smart HTTP. /project/repo/git-command
            git_command = pathlets[2]
            handler = self.git_rpc_handler

        # add git command to routing args
        environ.setdefault('wsgiorg.routing_args', ([], {}))[1]['git_command'] = git_command

        # authorization
        logger.debug('User "%s" is attempting to execute git command "%s"', str(user), str(git_command))

        if git_command in ['git-upload-pack', 'DUMMY-static-read']:
            # read
            if repository.has_read_access(user):
                return handler(environ, start_response)
            else:
                return self.require_authorization(environ, start_response)
        elif git_command in ['git-receive-pack']:
            # write
            if repository.has_write_access(user):
                return handler(environ, start_response)
            else:
                return self.require_authorization(environ, start_response)
        else:
            if self.gitviewer is not None:
                if repository and repository.has_read_access(user):
                    # For the viewer, we transform the URL a bit. 
                    # /some/path/project/repository/more
                    #  SCRIPT   | PATH INFO        
                    # ->
                    # SCRIPT            |  PATH INFO
                    # The physical repository base directory is provided in wsgiorg.routing_args
                    move_projectname_into_scriptname(environ, project.name)

                    logger.debug("Passing off request to git viewer app with SCRIPT_NAME: %s and PATH_INFO: %s", environ['SCRIPT_NAME'], environ['PATH_INFO'])
                    return self.gitviewer(environ, start_response)
                elif project.get_permission(user, "*", "read"):
                    move_projectname_into_scriptname(environ, project.name)
                    logger.debug("Passing off request to git viewer app with SCRIPT_NAME: %s and PATH_INFO: %s", environ['SCRIPT_NAME'], environ['PATH_INFO'])
                    return self.gitviewer(environ, start_response)
                else:
                    return self.require_authorization(environ, start_response)
            else:
                start_response('400 Bad Request', [('Content-Type', 'text/plain')])
                return 'Unknown git command: ' + str(git_command)

    def require_authorization(self, environ, start_response):
        start_response('401 Unauthorized', [('Content-Type', 'text/plain'), ('WWW-Authenticate', 'Basic realm="' + self.compmgr.config.get('web').get('auth_realm').encode('utf-8') + '"')])
        return 'Authorization needed to access this repository'

def create_application(cyd=None, viewer=None):
    if viewer is None:
        # try to automatically detect pyggi and use it as viewer
        try:
            import pyggi.lib.config
            pyggi.lib.config.config.read(['/etc/pyggi.conf'])

            from pyggi import create_app
            viewer = create_app()
        except Exception as e:
            logging.info("Pyggi not found", exc_info=True)

    if viewer is None:
        logging.warn("No viewer for git found!")

    return GitHTTP(cyd=cyd, gitviewer=viewer)

def standalone_serve():
    """Standalone WSGI Server for debugging purposes"""
    from werkzeug import run_simple
    import logging
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False)
    (options, args) = parser.parse_args()

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)

    port = 8080
    if len(args) > 0:
        port = int(args[0])

    app = create_application()

    #from werkzeugprofiler import ProfilerMiddleware
    #app = ProfilerMiddleware(app, stream=open('profile_stats.txt', 'w'), accum_count=100, sort_by=('cumulative', 'calls'), restrictions=(.1,))

    run_simple('0.0.0.0', port, app, use_reloader=True,
            use_debugger=True, #use_evalex=True,
            )
