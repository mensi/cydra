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

__all__ = ['IPubkeyStore', 'IDataSource']

from cydra.component import Interface, FallbackAttributeProxy

class IPubkeyStore(Interface):
    """Interface for places to store/retrieve public keys"""

    _iface_attribute_proxy = FallbackAttributeProxy()

    def get_pubkeys(self, user):
        """Get all pubkeys for user"""
        pass

    def user_has_pubkey(self, user, blob):
        """Does user have a pubkey with blob"""
        pass

    def add_pubkey(self, user, blob, name="unnamed", fingerprint=""):
        """add a new pubkey"""
        pass

    def remove_pubkey(self, user, **kwargs):
        pass

class IDataSource(Interface):
    """Interface for data sources"""

    _iface_single_extension = True

    def get_project(self, projectname):
        """Load a project
        
        :returns: Dict with project data or None"""
        pass

    def save_project(self, project):
        """Save project data
        
        :param project: A Project instance"""
        pass

    def create_project(self, projectname, owner):
        """Create a project
        
        :param projectname: The name of the project
        :param owner: User object of the owner of this project"""
        pass

    def list_projects(self):
        """List all projects"""
        pass

    def get_project_names(self):
        """Get all project names
        
        This is intended to be used when it is not a good idea to retrieve and hold 
        the entire projects in memory"""
        pass

    def get_projects_owned_by(self, user):
        """Get all projects owned by a given user
        
        :param user: The User object for the desired user"""
        pass

    def get_projects_where_key_exists(self, key):
        """Get all projects where a certain key exists in its data
        
        Example to search if a certain UserID is a key in the permissions sub-dict::
        
        get_projects_where_key_exists(['permissions', 'userid'])
        
        :param key: The key to look for. Can be a list to search for a nested key"""
        pass
