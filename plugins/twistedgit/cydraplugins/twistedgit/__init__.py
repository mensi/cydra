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

from twisted.internet import reactor
from twisted.conch.ssh import keys
from twisted.python import log

import cydra
from cydra.component import ExtensionPoint
from cydra.permission import IUserTranslator, IUserAuthenticator
from cydra.component import Component, implements
from cydra.datasource import IPubkeyStore
from cydra.web.frontend.hooks import IRepositoryViewerProvider, IProjectFeaturelistItemProvider

from twistedgit import ssh

import logging
logger = logging.getLogger(__name__)


import logging
logger = logging.getLogger(__name__)

class TwistedGit(Component):
    """Cydra component for integration between TwistedGit and Cydra"""

    implements(IRepositoryViewerProvider)

    def __init__(self):
        pass

    def get_repository_viewers(self, repository):
        """Add clone URL to the viewers"""
        if 'url_base' not in self.component_config:
            logger.warning("url_base is not configured!")
        elif repository.type == 'git':
            return ('Git over ssh', self.component_config['url_base'] + '/' + repository.project.name + '/' + repository.name + '.git')

class CydraHelper(object):

    authenticator = ExtensionPoint(IUserAuthenticator)
    pubkey_store = ExtensionPoint(IPubkeyStore)

    git_binary = 'git'
    git_shell_binary = 'git-shell'

    path_matcher = re.compile('^/git/(?P<project>[a-z][a-z0-9\-_]{0,31})/(?P<repository>[a-z][a-z0-9\-_]{0,31})\.git$')

    def __init__(self, cyd):
        self.compmgr = self.cydra = cyd

    def can_read(self, username, virtual_path):
        repo = self.get_repository(virtual_path)
        user = self.compmgr.get_user(username=username)

        if repo is None or user is None:
            return False

        return repo.has_read_access(user)

    def can_write(self, username, virtual_path):
        repo = self.get_repository(virtual_path)
        user = self.compmgr.get_user(username=username)

        if repo is None or user is None:
            return False

        return repo.has_write_access(user)

    def check_password(self, username, password):
        user = self.compmgr.get_user(username=username)
        if user is None:
            return False

        return self.authenticator.user_password(user, password)

    def check_publickey(self, username, keyblob):
        user = self.compmgr.get_user(username=username)
        if user is None:
            return False

        return self.pubkey_store.user_has_pubkey(user, keyblob)

    def translate_path(self, virtual_path):
        repo = self.get_repository(virtual_path)
        if repo is not None:
            return repo.path

    def get_repository(self, path):
        m = self.path_matcher.match(path)
        if not m:
            return None

        project = m.group('project')
        repository = m.group('repository')

        project = self.cydra.get_project(project)
        if project is None:
            return None

        # Repository discovery
        repository = project.get_repository('git', repository)
        return repository

def run_server():
    import logging
    import logging.handlers
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False)
    parser.add_option('-d', '--daemonize', action='store_true', dest='daemonize', default=False)
    parser.add_option('-i', '--pidfile', action='store', dest='pidfile', default=None)
    parser.add_option('-l', '--logfile', action='store', dest='logfile', default=None)
    parser.add_option('-u', '--user', action='store', dest='user', default=None)
    parser.add_option('-g', '--group', action='store', dest='group', default=None)
    (options, args) = parser.parse_args()

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
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(loglevel)

    observer = log.PythonLoggingObserver()
    observer.start()

    port = 2222
    if len(args) > 0:
        port = int(args[0])

    cyd = cydra.Cydra()
    helper = CydraHelper(cyd)
    config = cyd.config.get_component_config('cydraplugins.twistedgit.TwistedGit', {})

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

    # daemonize if requested
    if options.daemonize:
        if not options.logfile:
            print "Error: Cannot log to stderr, please specify a log file"
            return

        import daemon, grp, pwd

        files = [handler.stream]

        if options.pidfile:
            pidf = open(options.pidfile, 'w')
            files.append(pidf)

        args = dict(files_preserve=files)

        if options.group:
            if options.group.isdigit():
                args['gid'] = int(options.group)
            else:
                args['gid'] = grp.getgrnam(options.group).gr_gid
        elif os.getgid() == 0:
            args['gid'] = grp.getgrnam('www-data').gr_gid


        if options.user:
            if options.user.isdigit():
                args['uid'] = int(options.user)
            else:
                args['uid'] = pwd.getpwnam(options.user).pw_uid
        elif os.getuid() == 0:
            args['uid'] = pwd.getpwnam('www-data').pw_uid

        context = daemon.DaemonContext(**args)
        context.open()

        # save pid to file
        if options.pidfile:
            pidf.write(str(os.getpid()))
            pidf.close()

    import traceback, signal
    def dump_stack(sig, frame):
        logger.debug("Dumping Stack: \n" + ''.join(traceback.format_stack(frame)))
    signal.signal(signal.SIGUSR1, dump_stack)

    reactor.listenTCP(port, ssh_factory())
    reactor.run()
