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

from cydra.component import Interface, BroadcastAttributeProxy

class IRepositoryProvider(Interface):

    _iface_attribute_proxy = BroadcastAttributeProxy()

    repository_type = ''
    repository_type_title = ''

    def get_repositories(self, project):
        """Get a list of repository objects for this project"""
        pass

    def get_repository(self, project, repository_name):
        """Get a repository object"""
        pass

    def can_create(self, project, user=None):
        """Can the given user create repositories"""
        pass

    def create_repository(self, project, repository_name):
        """Create repository"""
        pass

    def get_params(self):
        """Return the list of parameters for this repository type
        
        :return: list of RepositoryParameter instances  
        """
        pass

class ISyncParticipant(Interface):
    """Interface for components wishing to perform actions upon synchronisation"""

    _iface_attribute_proxy = BroadcastAttributeProxy()

    def sync_repository(self, repository):
        """Synchronise repository"""
        pass

class IRepositoryObserver(Interface):
    """Events on repository modifications"""

    _iface_attribute_proxy = BroadcastAttributeProxy()

    def repository_post_commit(self, repository, revisions):
        """One or more commits have occured
        
        :param repository: The repository object
        :param revisions: A list of revision strings"""
        pass

    def pre_delete_repository(self, repository, project_deletion):
        """Gets called before a repository is deleted
        
        :param repository: The repository that will be deleted
        :param project_deletion: True if the project is being deleted
        """
        pass

    def post_delete_repository(self, repository):
        """Gets called after a repository has been deleted"""
        pass
