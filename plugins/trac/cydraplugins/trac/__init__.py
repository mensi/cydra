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
import pkg_resources

import logging
logger = logging.getLogger(__name__)

import cydra
from cydra.web.wsgihelper import HTTPBasicAuthenticator, move_projectname_into_scriptname
from cydra.web import IBlueprintProvider
from cydra.web.frontend.hooks import IRepositoryActionProvider, IProjectActionProvider, IProjectFeaturelistItemProvider
from cydra.component import Component, implements
from cydra.cli import ICliProjectCommandProvider
from cydra.repository import IRepositoryObserver
from cydra.project import ISyncParticipant as IProjectSyncParticipant

from trac.core import Component as TracComponent, implements as trac_implements
from trac.env import Environment
from trac.config import Configuration
from trac.wiki.admin import WikiAdmin
from trac.perm import IPermissionPolicy
from trac.versioncontrol.api import DbRepositoryProvider, RepositoryManager

# monkey patch trac to prevent it from setting up logging
# we do this ourselves and don't want trac to mess it up
import trac.log
def _patched_logger_handler_factory(*args, **kwargs):
    import logging.handlers
    traclogger = logging.getLogger('trac')
    hdlr = logging.handlers.BufferingHandler(0)
    hdlr.setFormatter(logging.Formatter())
    traclogger.addHandler(hdlr)

    return traclogger, hdlr
trac.log.logger_handler_factory = _patched_logger_handler_factory

class TracEnvironments(Component):
    """Cydra component for trac support"""

    implements(ICliProjectCommandProvider)
    implements(IRepositoryObserver)
    implements(IBlueprintProvider)
    implements(IProjectActionProvider)
    implements(IRepositoryActionProvider)
    implements(IProjectFeaturelistItemProvider)
    implements(IProjectSyncParticipant)

    # this map might look silly right now, but it is not guaranteed that cydra and trac name
    # repository types the same
    typemap = {
               'svn': 'svn',
               'hg': 'hg',
               'git': 'git'
    }

    def __init__(self):
        """Initialize Trac component
        
        This will raise an exception if the base path for the environments 
        has not been configured"""

        if 'base' not in self.component_config:
            raise Exception("trac environments base path not configured")

    def get_env_path(self, project):
        return os.path.join(self.component_config['base'], project.name)

    def get_default_options(self, project):
        """Get the default set of options Cydra enforces
        
        These options override everything"""
        return [
            ('project', 'name', project.name),
            ('trac', 'database', 'sqlite:db/trac.db'), #TODO: implement the possibility to override this
            ('trac', 'repository_sync_per_request', ''), # We use hooks, don't sync per request
            ('trac', 'permission_policies', 'CydraPermissionPolicy'),
            ('components', 'tracext.hg.*', 'enabled'),
            ('components', 'tracext.git.*', 'enabled'),
            ('components', 'cydraplugins.*', 'enabled'),
            ('git', 'cached_repository', 'true'),
            ('header_logo', 'src', 'common/trac_banner.png'), # Perhaps let user set a custom one
        ]

    def has_env(self, project):
        """Does the project contain a Trac environment"""
        return os.path.exists(self.get_env_path(project))

    def create(self, project):
        """Create a Trac environment for the project
        
        This will NOT call trac-admin but interfaces with Trac's API 
        directly. It performs the same steps as trac-admin"""

        if self.has_env(project):
            return True

        # When creating environments, you can supply a list
        # of (section, option, value) tuples to trac which serve as a default
        options = self.get_default_options(project)

        # If an (inherit, file, xy) option is present, trac will omit the default values
        if 'inherit_config' in self.component_config:
            options.append(('inherit', 'file', self.component_config['inherit_config']))

        try:
            # create environment
            env = Environment(self.get_env_path(project), create=True, options=options)

            # preload wiki pages
            wiki_pages = None
            if 'preload_wiki' in self.component_config:
                wiki_pages = self.component_config['preload_wiki']
            else:
                try:
                    wiki_pages = pkg_resources.resource_filename('trac.wiki', 'default-pages')
                except Exception as e:
                    logger.exception("Exception while trying to find wiki pages")
                    wiki_pages = None

            if wiki_pages:
                try:
                    WikiAdmin(env).load_pages(wiki_pages)
                except Exception as e:
                    logger.exception("Unable to load wiki pages from %s", wiki_pages)
            else:
                logger.warning("Not wiki pages found for preloading")

            # all done
            return True
        except Exception as e:
            logger.exception("Caught exception while creating Trac environment in " + self.get_env_path(project))

        return False

    def sync_project(self, project):
        """For project.ISyncParticipant"""
        self.sync(project)

    def sync(self, project):
        """Sync the trac environment with cydra
        
        This sets the options returned by ``get_default_options`` and adds Trac's own defaults if necessary"""
        if not self.has_env(project):
            logger.warning('Project %s has no Trac Environment to sync', project.name)
            return

        tracini = os.path.join(self.get_env_path(project), 'conf', 'trac.ini')
        options = self.get_default_options(project)

        # if inherit is enabled, the default values are supposed to be in
        # the inherited file. Thus, we can truncate the config file to get a bare minimum
        if 'inherit_config' in self.component_config:
            options.append(('inherit', 'file', self.component_config['inherit_config']))
            with open(tracini, 'w') as f:
                f.truncate()

        # re-create the configuration file
        config = Configuration(tracini)
        for section, name, value in options:
            config.set(section, name, value)
        config.save()

        # load defaults
        if not any((section, option) == ('inherit', 'file') for section, option, value in options):
            config.set_defaults()
            config.save()

        # check if repositories in cydra match repositories in trac
        env = Environment(self.get_env_path(project))
        rm = RepositoryManager(env)
        trac_repos = rm.get_real_repositories()
        trac_repo_names = [r.reponame for r in trac_repos]

        for repotype, repos in project.data.get('plugins', {}).get('trac', {}).items():
            for repo, tracname in (repos or {}).items():
                if tracname not in trac_repo_names:
                    logger.warning("Removing trac mapping from cydra for %s repo %s", repo, tracname)
                    del repos[repo]
                    if not repos:
                        del project.data.get('plugins', {}).get('trac', {})[repotype]

        # Now do the reverse
        revmap = dict([(y, x) for (x, y) in self.typemap.items()])

        for repo in trac_repos:
            logger.debug('Looking at trac repo %s', repo.reponame)

            try:
                baseparts = repo.get_base().split(':') # This is extremely naiive and possibly breaks some time
                repotype, path = baseparts[0], baseparts[-1]
            except:
                logger.error("Unable to parse: " + repo.get_base())

            reponame = os.path.basename(path)
            if repotype == 'git':
                reponame = reponame[:-4]

            try:
                repository = project.get_repository(revmap[repotype], reponame)
            except:
                logger.error("Unable to locate %s %s (%s)", repotype, reponame, path)
                repository = None

            logger.debug('Cydra repo %r', repository)

            if repository:
                # set this mapping if not there already
                project.data.setdefault('plugins', {}).setdefault('trac', {}).setdefault(repository.type, {})[repository.name] = repo.reponame
                logger.info('Setting trac mapping for %s %s -> %s', repository.type, repository.name, repo.reponame)
            else:
                logger.error("Unable to load %s %s (%s)", revmap[repotype], reponame, path)

        project.save()

    def register_repository(self, repository, name=None):
        """Register a repository with trac"""

        project = repository.project
        tracname = name if name is not None else repository.name

        if repository.name in project.data.get('plugins', {}).get('trac', {}).get(repository.type, {}):
            logger.error("Repository %s:%s is already registered in project %s",
                        repository.type, repository.name, project.name)
            return False

        if repository.type not in self.typemap:
            logger.error("Repository type %s is not supported in Trac", repository.type)
            return False

        if not self.has_env(project):
            logger.warning("Tried to add repository %s:%s to Trac of project %s, but there is no environment",
                        repository.type, repository.name, project.name)
            return False

        try:
            env = Environment(self.get_env_path(project))

            DbRepositoryProvider(env).add_repository(tracname, repository.path, self.typemap[repository.type])

            # save mapping in project
            project.data.setdefault('plugins', {}).setdefault('trac', {}).setdefault(repository.type, {})[repository.name] = tracname
            project.save()

            # Synchronise repository
            rm = RepositoryManager(env)
            repos = rm.get_repository(tracname)
            repos.sync(lambda rev: logger.debug("Synced revision: %s", rev), clean=True)

            return True
        except Exception as e:
            logger.exception("Exception occured while addingrepository %s:%s to Trac of project %s",
                        repository.type, repository.name, project.name)
            return False

    def get_cli_project_commands(self):
        return [('trac', self.cli_command)]

    def cli_command(self, project, args):
        """Manipulate the trac environment for a project
        
        Supported arguments:
        - create: creates an environment
        - sync: Synchronizes the configuration with Cydra's requirements
        - addrepo <type> <name> [tracname]: adds the repository to trac, identified by tracname
        - updatedefaults <file>: Adds trac's default options to config"""

        if len(args) < 1 or args[0] not in ['create', 'addrepo', 'sync', 'updatedefaults']:
            print self.cli_command.__doc__
            return

        if args[0] == 'create':
            if self.has_env(project):
                print "Project already has a Trac environment!"
                return

            if self.create(project):
                print "Environment created"
            else:
                print "Creation failed!"

        elif args[0] == 'sync':
            self.sync(project)

            print project.name, "synced"

        elif args[0] == 'addrepo':
            if len(args) < 3:
                print self.cli_command.__doc__
                return

            repository = project.get_repository(args[1], args[2])

            if not repository:
                print "Unknown repository"
                return

            ret = False
            if len(args) == 4:
                ret = self.register_repository(repository, args[3])
            else:
                ret = self.register_repository(repository)

            if ret:
                print "Successfully added repository"
            else:
                print "Adding repository failed!"

        elif args[0] == 'updatedefaults':
            if len(args) < 2:
                print self.cli_command.__doc__
                return

            config = Configuration(args[1])
            # load defaults
            config.set_defaults()
            config.save()


    def get_blueprint(self):
        """Get the blueprint for trac actions in the web interface"""
        from flask import Blueprint, render_template, abort, redirect, url_for, flash, request, jsonify, current_app
        from cydra.web.wsgihelper import InsufficientPermissions
        from werkzeug.exceptions import NotFound
        from werkzeug.local import LocalProxy

        blueprint = Blueprint('trac', __name__, static_folder='static', template_folder='templates')
        cydra_instance = LocalProxy(lambda: current_app.config['cydra'])
        cydra_user = LocalProxy(lambda: request.environ['cydra_user'])

        @blueprint.route('/project/<projectname>/trac/create', methods=['POST'])
        def create(projectname):
            project = cydra_instance.get_project(projectname)
            if project is None:
                raise NotFound('Unknown project')

            if not project.get_permission(cydra_user, '*', 'admin'):
                raise InsufficientPermissions()

            self.create(project)
            return redirect(url_for('frontend.project', projectname=projectname))

        @blueprint.route('/project/<projectname>/trac/register_repository/<repositorytype>/<repositoryname>', methods=['POST'])
        def register_repository(projectname, repositorytype, repositoryname):
            project = cydra_instance.get_project(projectname)
            if project is None:
                raise NotFound('Unknown project')

            if not project.get_permission(cydra_user, '*', 'admin'):
                raise InsufficientPermissions()

            repository = project.get_repository(repositorytype, repositoryname)
            if repository is None:
                raise NotFound('Unknown repository')

            self.register_repository(repository)
            return redirect(url_for('frontend.project', projectname=projectname))

        return blueprint

    def get_project_featurelist_items(self, project):
        if not self.has_env(project):
            return

        if 'url_base' not in self.component_config:
            logger.warning("url_base is not configured!")
            return ('Trac', [])
        else:
            return ('Trac', [{'href': self.component_config['url_base'] + '/' + project.name,
                             'name': 'view'}])

    def get_project_actions(self, project):
        if not self.has_env(project):
            return ('Create Trac', 'trac.create', 'post')

    def get_repository_actions(self, repository):
        if self.has_env(repository.project):
            if repository.name not in repository.project.data.get('plugins', {}).get('trac', {}).get(repository.type, {}):
                return ('Register in Trac', 'trac.register_repository', 'post')
            else:
                pass # TODO: deregister

    def repository_change_commit(self, repository, revisions):
        self._changeset_event(repository, 'changeset_added', revisions)

    # IRepositoryObserver
    def repository_post_commit(self, repository, revisions):
        self._changeset_event(repository, 'changeset_modified', revisions)

    # IRepositoryObserver
    def pre_delete_repository(self, repository):
        tracrepo = repository.project.data.get('plugins', {}).get('trac', {}).get(repository.type, {}).get(repository.name)
        if tracrepo and self.has_env(repository.project):
            # remove it
            logger.info("Removing repository %s from Trac environment %s", tracrepo, repository.project.name)
            env = Environment(self.get_env_path(repository.project))
            DbRepositoryProvider(env).remove_repository(tracrepo)

            # clean up
            del repository.project.data['plugins']['trac'][repository.type][repository.name]
            if not repository.project.data['plugins']['trac'][repository.type]:
                del repository.project.data['plugins']['trac'][repository.type]

    def _changeset_event(self, repository, event, revisions):
        project = repository.project

        if not self.has_env(project):
            return

        tracrepos = project.data.get('plugins', {}).get('trac', {}).get(repository.type, {}).get(repository.name)

        if tracrepos:
            try:
                env = Environment(self.get_env_path(project))

                RepositoryManager(env).notify(event, tracrepos, revisions)
            except Exception as e:
                logger.exception("Exception occured while calling post-commit hook for revs %s on repository %s (%s) in project %s",
                                 revisions, repository.name, repository.type, project.name)

class TracWrapper(object):
    """WSGI wrapper for trac"""

    def __init__(self, cyd=None):
        if cyd is None:
            cyd = cydra.Cydra()

        self.cydra = self.compmgr = cyd
        self.authenticator = HTTPBasicAuthenticator(self.compmgr)

        self.config = config = cyd.config.get_component_config('cydraplugins.trac.TracEnvironments', {})
        if 'base' not in config:
            raise Exception("trac environments base path not configured")

        os.environ['TRAC_ENV_PARENT_DIR'] = config['base']
        import trac.web.main
        self.trac = trac.web.main.dispatch_request

    def __call__(self, environ, start_response):
        """Process trac request
        
        URLs are in the form of /project
        """

        path = environ.get('PATH_INFO', '')
        user = self.authenticator(environ)

        project = None

        try:
            pathparts = path.strip('/').split('/')
            project = pathparts[0]
            project = self.cydra.get_project(project)

            if project is None:
                logger.debug("Unknown project: %s", path)
                start_response('404 Not Found', [('Content-Type', 'text/plain')])
                return 'Unknown Project'

            if not os.path.exists(os.path.join(self.config['base'], project.name)):
                logger.debug("No trac found for: %s", project.name)
                start_response('404 Not Found', [('Content-Type', 'text/plain')])
                return 'No trac environment found'

            if (len(pathparts) == 2 and pathparts[1] == 'login') and user.is_guest:
                return self.require_authorization(environ, start_response)

            return self.trac(environ, start_response)

        except Exception as e:
            logger.exception("Exception during Trac dispatch")
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            return 'Unknown Trac/Project or invalid URL'

    def require_authorization(self, environ, start_response):
        start_response('401 Unauthorized', [('Content-Type', 'text/plain'), ('WWW-Authenticate', 'Basic realm="' + self.compmgr.config.get('web').get('auth_realm').encode('utf-8') + '"')])
        return 'Authorization needed to access this Trac environment'

def standalone_serve():
    """Standalone WSGI Server for debugging purposes"""
    from werkzeug import run_simple
    import sys

    port = 8080
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    app = TracWrapper()

    #from werkzeugprofiler import ProfilerMiddleware
    #app = ProfilerMiddleware(app, stream=open('profile_stats.txt', 'w'), accum_count=100, sort_by=('cumulative', 'calls'), restrictions=(.1,))

    run_simple('0.0.0.0', port, app, use_reloader=True,
            use_debugger=False, #use_evalex=True,
            )
