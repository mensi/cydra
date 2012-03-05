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
from cydra.repository import IRepository, Repository
from cydra.error import CydraError, InsufficientConfiguration, UnknownRepository
from cydra.permission import IPermissionProvider
from cydra.web.frontend.hooks import IRepositoryViewerProvider, IProjectFeaturelistItemProvider

import logging
logger = logging.getLogger(__name__)

class SVNExternalViewer(Component):

    implements(IRepositoryViewerProvider)
    implements(IProjectFeaturelistItemProvider)

    def __init__(self):
        self.title = 'SVN'

        if 'title' in self.component_config:
            self.title = self.component_config['title']

    def get_repository_viewers(self, repository):
        """Announce announce an external viewer"""
        if 'url_base' not in self.component_config:
            logger.warning("url_base is not configured!")
        elif repository.type == 'svn':
            return (self.title, self.component_config['url_base'] + '/' + repository.name)

    def get_project_featurelist_items(self, project):
        if project.get_repository_type('svn').get_repositories(project):
            if 'url_base' not in self.component_config:
                logger.warning("url_base is not configured!")
                return (self.title, [])

            return (self.title, [{'href': self.component_config['url_base'] + '/' + project.name,
                                  'name': 'view'}])

class SVNRepositories(Component):

    implements(IRepository)

    repository_type = 'svn'
    repository_type_title = 'SVN'

    def __init__(self):
        config = self.get_component_config()

        if 'base' not in config:
            InsufficientConfiguration(missing='base', component=self.get_component_name())

        self._base = config['base']
        self.svncommand = config.get('svncommand', 'svnadmin')

    def get_repositories(self, project):
        if not os.path.exists(os.path.join(self._base, project.name)):
            return []
        else:
            return [SVNRepository(self.compmgr, self._base, project)]

    def get_repository(self, project, repository_name):
        return SVNRepository(self.compmgr, self._base, project)

    def can_create(self, project, user=None):
        if user:
            return len(self.get_repositories(project)) == 0 and project.get_permission(user, 'repository.svn', 'create')
        else:
            return len(self.get_repositories(project)) == 0

    def create_repository(self, project, repository_name):
        if repository_name != project.name:
            raise CydraError("SVN Repository name has to be the same as the project's name")

        path = os.path.join(self._base, project.name)

        if os.path.exists(path):
            raise CydraError('Path already exists', path=path)

        svn_cmd = subprocess.Popen([self.svncommand, 'create', path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, errors = svn_cmd.communicate()

        if svn_cmd.returncode != 0:
            if svn_cmd.returncode == 127:
                # assume this is command not found
                raise CydraError('Command not found encountered while calling svn', stderr=errors)
            else:
                raise CydraError('Error encountered while calling svn', stderr=errors, code=hg_cmd.returncode)

        # Customize config

        repository = SVNRepository(self.compmgr, self._base, project)
        repository.sync()
        return repository

    def get_params(self):
        return []

class SVNRepository(Repository):

    permission = ExtensionPoint(IPermissionProvider)

    def __init__(self, component_manager, base, project):
        """Construct repository instance"""
        super(SVNRepository, self).__init__(component_manager)

        self.project = project
        self.name = project.name
        self.base = base
        self.type = 'svn'

        self.path = self.path = os.path.abspath(os.path.join(self.base, self.name))

        # ensure this repository actually exists
        if not os.path.exists(self.path):
            raise UnknownRepository(repository_name=self.name, project_name=project.name, repository_type='svn')

    def has_read_access(self, user):
        return self.project.get_permission(user, 'repository.svn.' + self.name, 'read')

    def has_write_access(self, user):
        return self.project.get_permission(user, 'repository.svn.' + self.name, 'write')

    def sync(self):
        """Installs necessary hooks"""
        from jinja2 import Template

        tpl = self.compmgr.config.get_component_config('cydra.repository.svn.SVNRepositories', {}).get('commit_script')
        if tpl:
            with open(tpl, 'r') as f:
                template = Template(f.read())
        else:
            from pkg_resources import resource_string
            template = Template(resource_string('cydra.repository', 'scripts/svn_commit.sh'))

        hook = template.render(project=self.project, repository=self)
        with open(os.path.join(self.path, 'hooks', 'post-commit'), 'w') as f:
            f.write(hook)
            mode = os.fstat(f.fileno()).st_mode
            mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            os.fchmod(f.fileno(), mode)

        super(SVNRepository, self).sync()

def commit_hook():
    """Hook for svn"""
    import sys

    if len(sys.argv) != 4:
        print "Usage: %s <projectname> <reponame> <revision>" % sys.argv[0]
        sys.exit(2)

    cyd = cydra.Cydra()

    project = cyd.get_project(sys.argv[1])

    if not project:
        sys.exit("Unknown project")

    repository = project.get_repository('svn', sys.argv[2])

    if not repository:
        sys.exit("Unknown repository")

    repository.notify_post_commit(sys.argv[3])
