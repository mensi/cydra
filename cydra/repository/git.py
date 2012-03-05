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

import os, os.path, stat
import subprocess
import re

import cydra
from cydra.component import Component, implements, ExtensionPoint
from cydra.repository import IRepository, Repository, RepositoryParameter
from cydra.error import CydraError, InsufficientConfiguration, UnknownRepository
from cydra.permission import IPermissionProvider

def is_valid_repository_name(name):
    if re.match('^[a-z][a-z0-9\-_]{0,31}$', name) is None:
        return False
    else:
        return True

param_description = RepositoryParameter(
        keyword='description',
        name='Description',
        description='Description of the repository')

class GitRepositories(Component):
    """Component for git based repositories
    
    Configuration:
    - base: Path to the directory where repositories are stored
    - gitcommand: Path to git command. Defaults to git"""

    implements(IRepository)

    repository_type = 'git'
    repository_type_title = 'Git'

    def __init__(self):
        config = self.get_component_config()

        if 'base' not in config:
            raise InsufficientConfiguration(missing='base', component=self.get_component_name())

        self._base = config['base']
        self.gitcommand = config.get('gitcommand', 'git')

    def get_repositories(self, project):
        """Returns a list of repositories for the project
        
        This list is based on the filesystem"""
        if not os.path.exists(os.path.join(self._base, project.name)):
            return []

        return [GitRepository(self.compmgr, self._base, project, x[:-4]) for x in os.listdir(os.path.join(self._base, project.name)) if x[-4:] == '.git']

    def get_repository(self, project, repository_name):
        """Return a GitRepository instance for a repository"""
        if not self._repo_exists(project, repository_name):
            return
        else:
            return GitRepository(self.compmgr, self._base, project, repository_name)

    def can_create(self, project, user=None):
        """Returns whether the user create a new repository"""
        if user:
            return project.get_permission(user, 'repository.git', 'create')
        else:
            return True

    def create_repository(self, project, repository_name, **params):
        """Create a new git repository
        
        A repository's name can only contain letters, numbers and dashes/underscores."""
        if not is_valid_repository_name(repository_name):
            raise CydraError("Invalid Repository Name", name=repository_name)

        path = os.path.join(self._base, project.name, repository_name + '.git')

        if os.path.exists(path):
            raise CydraError('Path already exists', path=path)

        if not os.path.exists(os.path.join(self._base, project.name)):
            os.mkdir(os.path.join(self._base, project.name))

        git_cmd = subprocess.Popen([self.gitcommand, 'init', '--bare', path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, errors = git_cmd.communicate()

        if git_cmd.returncode != 0:
            if git_cmd.returncode == 127:
                # assume this is command not found
                raise CydraError('Command not found encountered while calling git', stderr=errors)
            else:
                raise CydraError('Error encountered while calling git', stderr=errors, code=git_cmd.returncode)

        # Customize config

        repository = GitRepository(self.compmgr, self._base, project, repository_name)
        repository.set_params(**params)
        repository.sync() # synchronize repository
        return repository

    def get_params(self):
        return [param_description]

    def _repo_exists(self, project, name):
        if not is_valid_repository_name(name):
            raise CydraError("Invalid Repository Name", name=name)

        path = os.path.join(self._base, project.name, name + '.git')

        return os.path.exists(path)

class GitRepository(Repository):

    permission = ExtensionPoint(IPermissionProvider)

    def __init__(self, component_manager, base, project, name):
        """Construct an instance"""
        super(GitRepository, self).__init__(component_manager)

        self.project = project
        self.name = name
        self.base = base
        self.type = 'git'

        self.path = self.path = os.path.abspath(os.path.join(self.base, project.name, name + '.git'))

        # ensure this repository actually exists
        if not os.path.exists(self.path):
            raise UnknownRepository(repository_name=name, project_name=project.name, repository_type='git')

    def get_param(self, param):
        if param == 'description':
            descrfile = os.path.join(self.path, 'description')

            if os.path.exists(descrfile):
                with open(descrfile, 'r') as f:
                    return f.read()

    def set_params(self, **params):
        if 'description' in params:
            descrfile = os.path.join(self.path, 'description')

            with open(descrfile, 'w') as f:
                f.write(params['description'])

    def sync(self):
        """Installs necessary hooks"""
        from jinja2 import Template

        tpl = self.compmgr.config.get_component_config('cydra.repository.git.GitRepositories', {}).get('post_receive_script')
        if tpl:
            with open(tpl, 'r') as f:
                template = Template(f.read())
        else:
            from pkg_resources import resource_string
            template = Template(resource_string('cydra.repository', 'scripts/git_post-receive.sh'))

        hook = template.render(project=self.project, repository=self)
        with open(os.path.join(self.path, 'hooks', 'post-receive'), 'w') as f:
            f.write(hook)
            mode = os.fstat(f.fileno()).st_mode
            mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            os.fchmod(f.fileno(), mode)

        super(GitRepository, self).sync()

    def has_read_access(self, user):
        return self.project.get_permission(user, 'repository.git.' + self.name, 'read')

    def has_write_access(self, user):
        return self.project.get_permission(user, 'repository.git.' + self.name, 'write')

def post_receive_hook():
    """Hook for git"""
    import sys
    import logging
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False)
    (options, args) = parser.parse_args()

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)

    if len(args) != 2:
        print "Usage: %s <projectname> <reponame>" % sys.argv[0]
        sys.exit(2)

    cyd = cydra.Cydra()
    gitconf = cyd.config.get_component_config('cydra.repository.git.GitRepositories', {})
    gitcommand = gitconf.get('gitcommand', 'git')

    project = cyd.get_project(args[0])

    if not project:
        sys.exit("Unknown project")

    repository = project.get_repository('git', args[1])

    if not repository:
        sys.exit("Unknown repository")

    for line in sys.stdin.readlines():
        old, new, ref = line.split()

        args = [new] if old == '0' * 40 else [new, '^' + old]

        commits = subprocess.Popen([gitcommand, '--git-dir', repository.path, 'rev-list'] + args, stdout=subprocess.PIPE).communicate()[0]

        repository.notify_post_commit(commits.splitlines()[::-1])

    sys.exit(0)

