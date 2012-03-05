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
import ConfigParser

import cydra
from cydra.component import Component, implements, ExtensionPoint
from cydra.repository import IRepository, RepositoryParameter, Repository
from cydra.error import CydraError, InsufficientConfiguration, UnknownRepository
from cydra.permission import IPermissionProvider

import logging
logger = logging.getLogger(__name__)

param_description = RepositoryParameter(
        keyword='description',
        name='Description',
        description='Description of the repository')

param_contact = RepositoryParameter(
        keyword='contact',
        name='Contact',
        description='Contact for the repository')

def is_valid_repository_name(name):
    if re.match('^[a-z][a-z0-9\-_]{0,31}$', name) is None:
        return False
    else:
        return True

class HgRepositories(Component):

    implements(IRepository)

    repository_type = 'hg'
    repository_type_title = 'Mercurial'

    def __init__(self):
        config = self.get_component_config()

        if 'base' not in config:
            InsufficientConfiguration(missing='base', component=self.get_component_name())

        self._base = config['base']
        self.hgcommand = config.get('hgcommand', 'hg')

    def get_repositories(self, project):
        if not os.path.exists(os.path.join(self._base, project.name)):
            return []

        return [HgRepository(self.compmgr, self._base, project, x) for x in os.listdir(os.path.join(self._base, project.name))]

    def get_repository(self, project, repository_name):
        return HgRepository(self.compmgr, self._base, project, repository_name)

    def can_create(self, project, user=None):
        if user:
            return project.get_permission(user, 'repository.hg', 'create')
        else:
            return True

    def create_repository(self, project, repository_name, **params):
        if not is_valid_repository_name(repository_name):
            raise CydraError("Invalid Repository Name", name=repository_name)

        path = os.path.join(self._base, project.name, repository_name)

        if os.path.exists(path):
            raise CydraError('Path already exists', path=path)

        if not os.path.exists(os.path.join(self._base, project.name)):
            os.mkdir(os.path.join(self._base, project.name))

        hg_cmd = subprocess.Popen([self.hgcommand, 'init', path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, errors = hg_cmd.communicate()

        if hg_cmd.returncode != 0:
            if hg_cmd.returncode == 127:
                # assume this is command not found
                raise CydraError('Command not found encountered while calling hg', stderr=errors)
            else:
                raise CydraError('Error encountered while calling hg', stderr=errors, code=hg_cmd.returncode)

        repository = HgRepository(self.compmgr, self._base, project, repository_name)
        repository.set_params(**params)
        repository.sync() # synchronize repository
        return repository

    def get_params(self):
        return [param_description, param_contact]

class HgRepository(Repository):

    permission = ExtensionPoint(IPermissionProvider)

    def __init__(self, component_manager, base, project, name):
        """Construct an instance"""
        super(HgRepository, self).__init__(component_manager)

        self.project = project
        self.name = name
        self.base = base
        self.type = 'hg'

        self.path = os.path.abspath(os.path.join(self.base, project.name, name))
        self.hgrc_path = os.path.join(self.path, '.hg', 'hgrc')

        # ensure this repository actually exists
        if not os.path.exists(self.path):
            raise UnknownRepository(repository_name=name, project_name=project.name, repository_type='hg')

    def has_read_access(self, user):
        return self.project.get_permission(user, 'repository.hg.' + self.name, 'read')

    def has_write_access(self, user):
        return self.project.get_permission(user, 'repository.hg.' + self.name, 'write')

    def _get_config(self):
        cp = ConfigParser.RawConfigParser()

        if os.path.exists(self.hgrc_path):
            try:
                cp.read(self.hgrc_path)
            except:
                logger.exception("Unable to parse hgrc file %s", self.hgrc_path)
                raise CydraError('Cannot parse existing hgrc file')
        else:
            logger.info("No hgrc file found at %s", self.hgrc_path)

        return cp

    def _set_config(self, config):
        try:
            with open(self.hgrc_path, 'wb') as f:
                config.write(f)
        except Exception:
            logger.exception("Unable to write hgrc file %s", self.hgrc_path)
            raise CydraError('Unable to write hgrc file')

    def get_param(self, param):
        cp = self._get_config()

        if param in ['contact', 'description']:
            if cp.has_option('web', param):
                return cp.get('web', param)

    def set_params(self, **params):
        if not params:
            return

        cp = self._get_config()

        if not cp.has_section('web'):
            cp.add_section('web')

        for param in ['contact', 'description']:
            if param in params:
                if params[param] is None and cp.has_option('web', param):
                    cp.remove_option('web', param)
                elif params[param] is not None:
                    cp.set('web', param, params[param])

        self._set_config(cp)

    def sync(self):
        """Installs necessary hooks"""
        from jinja2 import Template

        tpl = self.compmgr.config.get_component_config('cydra.repository.git.HgRepositories', {}).get('commit_script')
        if tpl:
            with open(tpl, 'r') as f:
                template = Template(f.read())
        else:
            from pkg_resources import resource_string
            template = Template(resource_string('cydra.repository', 'scripts/hg_commit.sh'))

        hook = template.render(project=self.project, repository=self)
        hookpath = os.path.join(self.path, '.hg', 'cydra_commit_hook.sh')
        with open(hookpath, 'w') as f:
            f.write(hook)
            mode = os.fstat(f.fileno()).st_mode
            mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            os.fchmod(f.fileno(), mode)

        # register hook
        cp = self._get_config()
        if not cp.has_section('hooks'):
            cp.add_section('hooks')
        cp.set('hooks', 'commit.cydra', hookpath)
        cp.set('hooks', 'changegroup.cydra', hookpath)
        self._set_config(cp)

        super(HgRepository, self).sync()

def commit_hook():
    """Hook for hg"""
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

    if len(args) != 3:
        print "Usage: %s <projectname> <reponame> <node>" % sys.argv[0]
        sys.exit(2)

    cyd = cydra.Cydra()
    hgconf = cyd.config.get_component_config('cydra.repository.hg.HgRepositories', {})
    hgcommand = hgconf.get('hgcommand', 'hg')

    project = cyd.get_project(args[0])

    if not project:
        sys.exit("Unknown project")

    repository = project.get_repository('hg', args[1])

    if not repository:
        sys.exit("Unknown repository")

    commits = subprocess.Popen([hgcommand, '--repository', repository.path, 'log', '--template', '{node}\\n', '--rev', args[2] + ':tip'], stdout=subprocess.PIPE).communicate()[0]
    repository.notify_post_commit(commits.splitlines())
