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
import os

import tornado.ioloop
import tornado.httpserver
import tornado.netutil
import tornado.web
import tornado.wsgi

import cydra
import cydraplugins.githttp
from cydra.web.wsgihelper import HTTPBasicAuthenticator

from gittornado import RPCHandler, InfoRefsHandler, FileHandler

import logging
logger = logging.getLogger(__name__)

class CydraHelper(object):
    def __init__(self, cyd):
        self.compmgr = self.cydra = cyd
        self.authenticator = HTTPBasicAuthenticator(self.compmgr)

        self.config_dict = {
                            'auth': self.auth,
                            'gitlookup': self.gitlookup,
                            'auth_failed': self.auth_failed
                            }

    def auth(self, request):
        pathlets = request.path.strip('/').split('/')
        if len(pathlets) < 2:
            return False, False

        # get repo
        repository = self.get_repository(request)
        if repository is None:
            return False, False

        # construct fake WSGI environ
        environ = dict([('HTTP_' + key.upper(), val) for key, val in request.headers.items()])
        user = self.authenticator(environ)

        return repository.has_read_access(user), repository.has_write_access(user)

    def auth_failed(self, request):
        msg = 'Authorization needed to access this repository'
        request.write('HTTP/1.1 401 Unauthorized\r\nContent-Type: text/plain\r\nContent-Length: %d\r\nWWW-Authenticate: Basic realm="%s"\r\n\r\n%s' % (
                        len(msg), self.compmgr.config.get('web').get('auth_realm').encode('utf-8'), msg))

    def gitlookup(self, request):
        pathlets = request.path.strip('/').split('/')
        if len(pathlets) < 2:
            return None

        repo = self.get_repository(request)

        if repo is None:
            return None
        else:
            return repo.path

    def get_repository(self, request):
        project = None
        repository = None

        # Project discovery
        pathlets = request.path.strip('/').split('/')
        if len(pathlets) > 0:
            project = pathlets[0]
        else:
            return None

        project = self.cydra.get_project(project)
        if project is None:
            return None

        # Repository discovery
        if len(pathlets) > 1:
            repository = pathlets[1]

            if repository[-4:] != '.git':
                return None

            repository = project.get_repository('git', repository[:-4])
            if repository is None:
                return None
            else:
                return repository
        else:
            return None

class ProxyHelper(object):
    def __init__(self, app, script_name=None, force_https=False):
        self.app = app
        self.script_name = script_name
        self.force_https = force_https

    def __call__(self, environ, start_response):
        if 'HTTP_X_FORWARDED_HOST' in environ:
            environ['HTTP_HOST'] = environ['HTTP_X_FORWARDED_HOST']

            if self.script_name is not None:
                environ['SCRIPT_NAME'] = self.script_name

            if self.force_https:
                environ['wsgi.url_scheme'] = 'https'

        return self.app(environ, start_response)

def run_server():
    import logging
    import logging.handlers
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False)
    parser.add_option('-p', '--proxy', action='store_true', dest='proxy', default=False)
    parser.add_option('-s', '--script-name', action='store', dest='script_name', default=None)
    parser.add_option('-f', '--force-https', action='store_true', dest='force_https', default=False)
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

    port = 8080
    if len(args) > 0:
        port = int(args[0])

    cyd = cydra.Cydra()
    helper = CydraHelper(cyd)
    wsgiapp = cydraplugins.githttp.create_application(cyd=cyd)
    if options.proxy:
        wsgiapp = ProxyHelper(wsgiapp)

        if options.script_name:
            wsgiapp.script_name = options.script_name

        if options.force_https:
            wsgiapp.force_https = True

    fallbackapp = tornado.wsgi.WSGIContainer(wsgiapp)
    app = tornado.web.Application([
                           ('/.*/.*/git-.*', RPCHandler, helper.config_dict),
                           ('/.*/.*/info/refs', InfoRefsHandler, helper.config_dict),
                           ('/.*/.*/HEAD', FileHandler, helper.config_dict),
                           ('/.*/.*/objects/.*', FileHandler, helper.config_dict),
                           ('.*', tornado.web.FallbackHandler, {'fallback': fallbackapp})
                           ])

    sockets = tornado.netutil.bind_sockets(port)

    # daemonize if requested
    if options.daemonize:
        if not options.logfile:
            print "Error: Cannot log to stderr, please specify a log file"
            return

        import daemon, grp, pwd, lockfile

        files = sockets + [handler.stream]

        if options.pidfile:
            pidf = open(options.pidfile, 'w')
            files.append(pidf)

        args = dict(files_preserve=files)

        #if options.pidfile:
        #    args['pidfile'] = PidFile(pidf)

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

    #tornado.process.fork_processes(0)

    import traceback, signal
    def dump_stack(sig, frame):
        logger.debug("Dumping Stack: \n" + ''.join(traceback.format_stack(frame)))
    signal.signal(signal.SIGUSR1, dump_stack)

    server = tornado.httpserver.HTTPServer(app)
    server.add_sockets(sockets)
    tornado.ioloop.IOLoop.instance().start()
