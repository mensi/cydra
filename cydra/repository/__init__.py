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

import os
import os.path
import shutil
import uuid
from cydra.component import Component, ExtensionPoint, implements
from cydra.repository.interfaces import ISyncParticipant, IRepositoryObserver, IRepositoryProvider
from cydra.project.interfaces import IProjectObserver

import logging
logger = logging.getLogger(__name__)


class RepositoryParameter(object):
    def __init__(self, keyword, name, optional=True, description=""):
        self.keyword = keyword
        self.name = name
        self.optional = optional
        self.description = description

    def validate(self, value):
        return True


class RepositoryProviderComponent(Component):
    """Base class for components providing repositories"""

    implements(IProjectObserver)
    implements(IRepositoryProvider)

    abstract = True

    def pre_delete_project(self, project, archiver=None):
        """Handle project delete by deleting all repositories"""
        for repo in self.get_repositories(project):
            repo.delete(archiver, project_deletion=True)


class Repository(object):
    """Repository base"""

    #: Absolute path of the repository
    path = None

    #: Type of the repository (string)
    type = None

    #: Name of the repository
    name = None

    @property
    def repository_provider(self):
        """Get the repository provider of this repository"""
        return self.project.get_repository_type(self.type)

    #: Project this repository belongs to
    project = None

    sync_participants = ExtensionPoint(ISyncParticipant)
    repository_observers = ExtensionPoint(IRepositoryObserver)

    def __init__(self, compmgr):
        """Construct a repository instance

        :param compmgr: Component manager (i.e. cydra instance)"""
        self.compmgr = compmgr

    def sync(self):
        """Synchronize repository with data stored in project and do maintenance work

        A repository should make sure post-commit hooks are registered and may collect statistics"""

        self.sync_participants.sync_repository(self)

    def delete(self, archiver=None, project_deletion=False):
        """Delete the repository"""
        if not archiver:
            archiver = self.project.get_archiver('repository_' + self.type + '_' + self.name)

        self.repository_observers.pre_delete_repository(self, project_deletion=project_deletion)

        tmppath = os.path.join(os.path.dirname(self.path), uuid.uuid1().hex)
        os.rename(self.path, tmppath)  # POSIX guarantees this to be atomic.

        with archiver:
            archiver.add_path(tmppath, os.path.join('repository', self.type, os.path.basename(self.path.rstrip('/'))))

        logger.info("Deleted repository %s of type %s: %s", self.name, self.type, tmppath)

        shutil.rmtree(tmppath)

        self.repository_observers.post_delete_repository(self)

    def notify_post_commit(self, revisions):
        """A commit has occured. Notify observers"""
        self.repository_observers.repository_post_commit(self, revisions)

    #
    # Permission checks
    # Also provide sensible defaults
    #
    def can_delete(self, user):
        return self.project.get_permission(user, 'repository.' + self.type + '.' + self.name, 'admin')

    def can_modify_params(self, user):
        return self.project.get_permission(user, 'repository.' + self.type + '.' + self.name, 'admin')

    def can_read(self, user):
        return self.project.get_permission(user, 'repository.' + self.type + '.' + self.name, 'read')

    def can_write(self, user):
        return self.project.get_permission(user, 'repository.' + self.type + '.' + self.name, 'write')
