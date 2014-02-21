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


class ISyncParticipant(Interface):
    """Interface for components whishing to participate in project synchronisation"""

    _iface_attribute_proxy = BroadcastAttributeProxy()

    def sync_project(self, project):
        """Sync project

        :param project: Project instance requesting to be synced
        :returns: True on success, False on failure. None is ignored"""


class IProjectObserver(Interface):
    """Interface for various informational events on projects"""

    _iface_attribute_proxy = BroadcastAttributeProxy()

    def pre_delete_project(self, project, archiver):
        """Called prior to project deletion

        3rd party components should delete project-dependent
        resources and deregister links to this project when
        handling this call

        :param project: The project to be deleted
        :param archiver: Archiver instance if archiving is desired
        """
