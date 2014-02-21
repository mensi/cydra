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
from cydra.project.interfaces import IProjectObserver
from cydra.component import Component, implements
from cydra.config import merge

import logging
logger = logging.getLogger(__name__)


class StaticDefaultConfigurator(Component):
    """Applies a static default configuration to every created project"""
    implements(IProjectObserver)

    def post_create_project(self, project):
        config = self.component_config.get("config", {})
        logger.debug("Extending project %s with config %r", project.name, config)
        merge(project.data, config)
        project.save()
