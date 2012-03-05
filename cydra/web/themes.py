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
import os.path
import types
import flask
from flask.globals import _request_ctx_stack
from flask.helpers import send_from_directory
from jinja2 import BaseLoader, TemplateNotFound, FileSystemLoader
from werkzeug.exceptions import NotFound

from cydra.component import Interface, BroadcastAttributeProxy

import logging
logger = logging.getLogger(__name__)

class IThemeProvider(Interface):
    """Components providing themes for the website"""

    _iface_attribute_proxy = BroadcastAttributeProxy(merge_lists=True)

    def get_themes(self):
        """Return an iterable with Theme instances"""
        pass

class Theme(object):
    def __init__(self, path, name=None):
        if name is None:
            name = os.path.basename(path)
        self.name = name
        self.template_path = os.path.join(path, 'templates')
        self.static_path = os.path.join(path, 'static')

    def get_blueprint_loader(self, blueprint_name):
        return FileSystemLoader(os.path.join(self.template_path, blueprint_name))

    def get_loader(self):
        return FileSystemLoader(self.template_path)

def patch_static(obj, blueprint_name=''):
    def themed_send_static_file(self, filename):
        # do we have an active theme?
        theme = None
        if hasattr(flask.g, 'theme'):
            theme = flask.g.theme
        if theme is not None:
            try:
                return send_from_directory(os.path.join(theme.static_path, blueprint_name), filename)
            except NotFound:
                pass

        if not self.has_static_folder:
            raise RuntimeError('No static folder for this object')
        return send_from_directory(self.static_folder, filename)

    obj.send_static_file = types.MethodType(themed_send_static_file, obj)

class ThemedTemplateLoader(BaseLoader):
    def __init__(self, app):
        self.app = app
        self.app_loader = app.jinja_loader

    def get_source(self, environment, template):
        for loader in self._iter_loaders():
            try:
                return loader.get_source(environment, template)
            except TemplateNotFound:
                pass
        raise TemplateNotFound(template)

    def _iter_loaders(self):
        # do we have an active theme?
        theme = None
        if hasattr(flask.g, 'theme'):
            theme = flask.g.theme
        if theme is None:
            logger.debug("No Theme found")

        # is there an active blueprint?
        bp = _request_ctx_stack.top.request.blueprint
        if bp is not None and bp in self.app.blueprints:
            bp = self.app.blueprints[bp]
            logger.debug("Request in BP: %s", bp.name)
            if theme is not None:
                yield theme.get_blueprint_loader(bp.name)
            yield bp.jinja_loader

        if theme is not None:
            yield theme.get_loader()

        yield self.app_loader
