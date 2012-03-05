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

# This file also contains code from Werkzeug licensed under the BSD license.
# For more information see http://werkzeug.pocoo.org/ and 
# https://github.com/mitsuhiko/werkzeug/blob/master/werkzeug/contrib/profiler.py

from StringIO import StringIO

try:
    from cProfile import Profile
except ImportError:
    from profile import Profile
from pstats import Stats

import logging
logger = logging.getLogger(__name__)

class DebuggingMiddleware(object):
    def __init__(self, app, debugusers):
        self.app = app
        self.debugusers = debugusers

    def __call__(self, environ, start_response):
        userid = environ.get('REMOTE_USER', None)
        if userid is None:
            author = environ.get('HTTP_AUTHORIZATION', None)
            if author is not None and author.strip().lower()[:5] == 'basic':
                userpw_base64 = author.strip()[5:].strip()
                userid, pw = userpw_base64.decode('base64').split(':', 1)

        if userid not in self.debugusers:
            return self.app(environ, start_response)

        response_body = []
        response = {'status': None, 'headers': None, 'exc_info': None}

        def catching_start_response(status, headers, exc_info=None):
            response['status'] = status
            response['headers'] = headers
            response['exc_info'] = exc_info
            return response_body.append

        def runapp():
            appiter = self.app(environ, catching_start_response)
            response_body.extend(appiter)
            if hasattr(appiter, 'close'):
                appiter.close()

        p = Profile()
        p.runcall(runapp)
        body = ''.join(response_body)

        data = StringIO()
        stats = Stats(p, stream=data)
        stats.sort_stats('cumulative', 'calls')
        stats.print_stats(.1)

        body = body.replace('<div id="cydra_note">', '<div id="profile_button"><button onclick="$(\'#profiledata\').toggle();">Profile</button></div><div id="profiledata" style="position: absolute; display: none; z-index: 1000; top: 25pt; left: 10pt; background-color: white; border: 1px solid black;"><pre>%s</pre></div>' % data.getvalue() + '<div id="cydra_note">')

        response_headers = dict(response['headers'])
        response_headers['Content-Length'] = len(body)
        response_headers = response_headers.items()

        start_response(response['status'], response_headers, response['exc_info'])
        return [body]
