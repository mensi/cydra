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
import traceback
import signal
import grp
import pwd

from twisted.internet import reactor
from twisted.conch.ssh import keys
from twisted.python import log

import cydra
import cydra.project
from cydra.component import ExtensionPoint
from cydra.component import Component, implements
from cydra.datasource import IPubkeyStore
from cydra.web.frontend.hooks import IRepositoryViewerProvider, IProjectFeaturelistItemProvider

from gitserverglue import ssh, http, find_git_viewer

import logging
logger = logging.getLogger(__name__)


class GitServerGlue(Component):
    """Cydra component for integration between GitServerGlue and Cydra"""

    implements(IRepositoryViewerProvider)
    implements(IProjectFeaturelistItemProvider)

    def __init__(self):
        pass

    def get_repository_viewers(self, repository):
        """Add clone URL to the viewers"""
        res = []

        if 'ssh_url_base' not in self.component_config:
            logger.warning("ssh_url_base is not configured!")
        elif repository.type == 'git':
            res.append(('ssh://', self.component_config['ssh_url_base'] + '/git/' + repository.project.name + '/' + repository.name + '.git'))

        if 'http_url_base' not in self.component_config:
            logger.warning("http_url_base is not configured!")
        elif repository.type == 'git':
            res.append(('http://', self.component_config['http_url_base'] + '/' + repository.project.name + '/' + repository.name + '.git'))

        return res

    def get_project_featurelist_items(self, project):
        if project.get_repository_type('git').get_repositories(project):
            if 'http_url_base' not in self.component_config:
                logger.warning("http_url_base is not configured!")
                return ('Git HTTP', [])

            return ('Git HTTP', [{'href': self.component_config['http_url_base'] + '/' + project.name,
                                  'name': 'view'}])


class CydraHelper(object):

    pubkey_store = ExtensionPoint(IPubkeyStore)

    git_binary = 'git'
    git_shell_binary = 'git-shell'

    def __init__(self, cyd):
        self.compmgr = self.cydra = cyd

        repoconfig = cyd.config.get_component_config('cydra.repository.git.GitRepositories', {})
        if 'base' not in repoconfig:
            raise Exception("git base path not configured")
        self.gitbase = repoconfig['base']

        self.config = cyd.config.get_component_config('cydraplugins.gitserverglue.GitServerGlue', {})

    def can_read(self, username, path_info):
        project = path_info.get('cydra_project')
        repo = path_info.get('cydra_repository')

        if username is None:
            user = self.compmgr.get_user(userid='*')
        else:
            user = self.compmgr.get_user(username=username)

        if repo is None and project is not None:
            return project.get_permission(user, '*', 'read')

        if repo is None or user is None:
            return False

        return repo.has_read_access(user)

    def can_write(self, username, path_info):
        repo = path_info.get('cydra_repository')

        if username is None:
            user = self.compmgr.get_user(userid='*')
        else:
            user = self.compmgr.get_user(username=username)

        if repo is None or user is None:
            return False

        return repo.has_write_access(user)

    def check_password(self, username, password):
        user = self.compmgr.get_user(username=username)
        if user is None:
            return False

        return user.check_password(password)

    def check_publickey(self, username, keyblob):
        user = self.compmgr.get_user(username=username)
        if user is None or not user.valid_for_authentication:
            return False

        return self.pubkey_store.user_has_pubkey(user, keyblob)

    def path_lookup(self, url, protocol_hint=None):
        res = {
            'repository_base_fs_path': None,
            'repository_base_url_path': None,
            'repository_fs_path': None
        }

        pathparts = url.lstrip('/').split('/')
        project = None
        reponame = None

        if protocol_hint == 'ssh':
            # /git/project/reponame.git
            if (len(pathparts) < 2 or pathparts[0] != 'git' or
                 not cydra.project.is_valid_project_name(pathparts[1])):
                return
            res['cydra_project'] = project = self.cydra.get_project(pathparts[1])
            res['repository_base_url_path'] = '/git/' + project.name + '/'
            reponame = pathparts[2] if len(pathparts) >= 3 else None

        else:
            # /project/reponame.git resp. /some/prefix/project/reponame.git
            # if gitserverglue is behind a reverse proxy
            prefixparts = []
            if 'http_url_prefix' in self.config:
                prefixparts = self.config['http_url_prefix'].lstrip('/').split('/')

            if len(pathparts) - len(prefixparts) < 1 or not cydra.project.is_valid_project_name(pathparts[len(prefixparts)]):
                return
            res['cydra_project'] = project = self.cydra.get_project(pathparts[len(prefixparts)])

            if project is None:
                return
            res['repository_base_url_path'] = '/' + '/'.join(prefixparts + [project.name]) + '/'

            reponame = pathparts[len(prefixparts) + 1] if len(pathparts) >= len(prefixparts) + 2 else None

        if project is None:
            return

        res['repository_base_fs_path'] = os.path.join(self.gitbase, project.name) + '/'

        if reponame is not None and reponame != '':
            if reponame.endswith('.git'):
                reponame = reponame[:-4]
            res['cydra_repository'] = repo = project.get_repository('git', reponame)
            if repo is None:
                return res

            res['repository_fs_path'] = repo.path
            res['repository_clone_urls'] = {}
            if 'http_url_base' in self.config:
                res['repository_clone_urls']['http'] = self.config['http_url_base'] + '/' + project.name + '/' + repo.name + '.git'

            if 'ssh_url_base' in self.config:
                res['repository_clone_urls']['ssh'] = self.config['ssh_url_base'] + '/git/' + project.name + '/' + repo.name + '.git'

        return res


def run_server():
    import logging.handlers
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False)
    parser.add_option('-i', '--pidfile', action='store', dest='pidfile', default=None)
    parser.add_option('-l', '--logfile', action='store', dest='logfile', default=None)
    parser.add_option('-u', '--user', action='store', dest='user', default=None)
    parser.add_option('-g', '--group', action='store', dest='group', default=None)
    parser.add_option('-s', '--sshport', action='store', type='int', dest='sshport', default=2222)
    parser.add_option('-w', '--httpport', action='store', type='int', dest='httpport', default=8080)
    (options, _) = parser.parse_args()

    if (options.user is None) ^ (options.group is None):
        raise Exception("Both user and group have to be specified")

    # configure logging
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s: <%(name)s@%(filename)s:%(lineno)d> %(message)s')

    if options.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.ERROR

    if options.logfile:
        handler = logging.handlers.TimedRotatingFileHandler(options.logfile, when='midnight', backupCount=7, encoding='utf-8')
    else:
        handler = logging.StreamHandler()

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(loglevel)

    observer = log.PythonLoggingObserver()
    observer.start()

    cyd = cydra.Cydra()
    helper = CydraHelper(cyd)
    config = cyd.config.get_component_config('cydraplugins.gitserverglue.GitServerGlue', {})

    keyfilename = config.get('server_key')
    if keyfilename is None:
        # try to find one anyways
        for location in ['cydra', '/etc/cydra']:
            if os.path.exists(location + '.key') and os.path.exists(location + '.pub'):
                keyfilename = location
                break
    if keyfilename is None:
        raise Exception("Failed to find SSH keypair")

    ssh_factory = ssh.create_factory(
        public_keys={'ssh-rsa': keys.Key.fromFile(keyfilename + '.pub')},
        private_keys={'ssh-rsa': keys.Key.fromFile(keyfilename + '.key')},
        authnz=helper,
        git_configuration=helper
    )

    http_factory = http.create_factory(
        authnz=helper,
        git_configuration=helper,
        git_viewer=find_git_viewer()
    )

    # save pid to file if requested
    if options.pidfile:
        with open(options.pidfile) as pidf:
            pidf.write(str(os.getpid()))

    try:

        def dump_stack(sig, frame):
            logger.debug("Dumping Stack: \n" + ''.join(traceback.format_stack(frame)))
        signal.signal(signal.SIGUSR1, dump_stack)

        reactor.listenTCP(options.sshport, ssh_factory)
        reactor.listenTCP(options.httpport, http_factory)

        # drop privileges if requested
        if os.getuid() == 0 and options.user:
            uid = int(options.user) if options.user.isdigit() else pwd.getpwnam(options.user).pw_uid
            gid = int(options.group) if options.group.isdigit() else grp.getgrnam(options.group).gr_gid

            os.setgroups([])
            os.setgid(gid)
            os.setuid(uid)

        reactor.run()
    except Exception:
        logger.exception("Caught exception during run")
