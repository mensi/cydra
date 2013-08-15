# -*- coding: utf-8 -*-
#
# Copyright 2013 Manuel Stocker <mensi@mensi.ch>
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
from __future__ import absolute_import

import socket

from .common import FixtureWithTempPath
from .. import procutils

class FileDatasource(FixtureWithTempPath):
    """Configure Cydra with the file datasource"""

    def setUp(self, configDict):
        super(FileDatasource, self).setUp(configDict)
        configDict.setdefault('components', {}).setdefault('cydra.datasource.file.FileDataSource', {})['base'] = self.path

class MongoDatasource(FixtureWithTempPath):
    """Configure Cydra with the mongoDB datasource and spawn a MongoDB instance"""

    mongo = None

    def setUp(self, configDict):
        super(MongoDatasource, self).setUp(configDict)

        # find a free port for mongo. Might be a bit crude...
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port = None
        for i in range(1025, 65535):
            try:
                s.bind(('localhost', i))
                port = i
                s.close()
                break
            except socket.error:
                continue

        if port is None:
            raise Exception("Unable to find a port for mongoDB")

        self.mongo = procutils.MonitoredDaemon([
                'mongod', '--dbpath', self.path, '--port', str(port),
                # Options for fast startup:
                '--nojournal', '--nohttpinterface', '--noprealloc', '--smallfiles'
        ], wait_for_stdout='waiting for connections on port')
        mongocfg = configDict.setdefault('components', {}).setdefault('cydra.datasource.mongo.MongoDataSource', {})
        mongocfg['host'] = 'localhost'
        mongocfg['port'] = port
        mongocfg['database'] = 'cydratest'

    def tearDown(self):
        self.mongo.process.terminate()
        self.mongo.process.wait()

        super(MongoDatasource, self).tearDown()
