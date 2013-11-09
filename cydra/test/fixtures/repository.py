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
from cydra.test.fixtures.common import FixtureWithTempPath, chain_fixtures


class GitRepositories(FixtureWithTempPath):
    """Configure Cydra for local git repositories"""

    def setUp(self, configDict):
        super(GitRepositories, self).setUp(configDict)
        configDict.setdefault('components', {}).setdefault('cydra.repository.git.GitRepositories', {})['base'] = self.path


class MercurialRepositories(FixtureWithTempPath):
    """Configure Cydra for local mercurial repositories"""

    def setUp(self, configDict):
        super(MercurialRepositories, self).setUp(configDict)
        configDict.setdefault('components', {}).setdefault('cydra.repository.hg.HgRepositories', {})['base'] = self.path


class SubversionRepositories(FixtureWithTempPath):
    """Configure Cydra for local subversion repositories"""

    def setUp(self, configDict):
        super(SubversionRepositories, self).setUp(configDict)
        configDict.setdefault('components', {}).setdefault('cydra.repository.svn.SVNRepositories', {})['base'] = self.path

AllRepositories = chain_fixtures(
    GitRepositories,
    MercurialRepositories,
    SubversionRepositories
)
