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
import tempfile
import shutil

class Fixture(object):
    inner = None

    def __init__(self, inner=None):
        self.inner = inner

    def setUp(self, configDict):
        if self.inner is not None:
            self.inner.setUp(configDict)

    def tearDown(self):
        if self.inner is not None:
            self.inner.tearDown()

    def checkHealth(self):
        if self.inner is not None:
            self.inner.checkHealth()

def chain_fixtures(*args):
    def instantiator(inner=None):
        for fixture in args:
            inner = fixture(inner)
        return inner
    return instantiator

class FixtureWithTempPath(Fixture):
    """A fixture that creates a temporary directory"""
    path = None

    def setUp(self, configDict):
        super(FixtureWithTempPath, self).setUp(configDict)
        self.path = tempfile.mkdtemp(prefix="cydratests_")

    def tearDown(self):
        shutil.rmtree(self.path)
        super(FixtureWithTempPath, self).tearDown()

