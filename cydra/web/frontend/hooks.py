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

from cydra.component import Interface, BroadcastAttributeProxy

class IRepositoryViewerProvider(Interface):

    _iface_attribute_proxy = BroadcastAttributeProxy()

    def get_repository_viewers(self, repository):
        """Provide URLs for repository viewer
        
        :returns: A list of ('name', 'url') tuples or a single one"""
        pass

class IRepositoryActionProvider(Interface):

    _iface_attribute_proxy = BroadcastAttributeProxy()

    def get_repository_actions(self, repository):
        """Provide endpoints for repository actions
        
        The method can either be get or post, depending on if the action
        has side effects.
        
        :returns: A list of ('name', 'endpoint', 'method') tuples or a single one"""
        pass

class IProjectActionProvider(Interface):

    _iface_attribute_proxy = BroadcastAttributeProxy()

    def get_project_actions(self, project):
        """Provide endpoints for project actions
        
        The method can either be get or post, depending on if the action
        has side effects.
        
        :returns: A list of ('name', 'endpoint', 'method') tuples or a single one"""
        pass

class IProjectFeaturelistItemProvider(Interface):

    _iface_attribute_proxy = BroadcastAttributeProxy()

    def get_project_featurelist_items(self, project):
        """Featurelist
        
        :returns: A list of ('name', [actions...]) or a single one. Action is a dict {href: url_or_endpoint, name: name}"""
        pass
