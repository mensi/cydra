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
import os
from functools import wraps

import cydra
from cydra.component import ExtensionPoint, Interface
from cydra.permission import IUserTranslator, IUserAuthenticator

__all__ = ['IBlueprintProvider', 'create_app', 'standalone_serve']

import logging
logger = logging.getLogger(__name__)

class IBlueprintProvider(Interface):
    """Components providing blueprints for the website"""

    def get_blueprint(self):
        pass

def create_app(cyd=None):
    """Create the web interface WSGI application"""

    if cyd is None:
        cyd = cydra.Cydra()

    from flask import Flask
    from flaskext.csrf import csrf
    from cydra.web.themes import IThemeProvider, ThemedTemplateLoader, patch_static

    app = Flask(__name__)

    # register themes
    theme_providers = ExtensionPoint(IThemeProvider, component_manager=cyd)
    app.config['cydra_themes'] = dict([(theme.name, theme) for theme in theme_providers.get_themes()])

    default_theme = cyd.config.get('web').get('default_theme')
    if default_theme is not None and default_theme in app.config['cydra_themes']:
        default_theme = app.config['cydra_themes'][default_theme]
        logger.debug("Default theme: %s", default_theme.name)
    else:
        default_theme = None
    theme_detector = ThemeDetector(default_theme)
    app.before_request(theme_detector)

    # replace default loader
    app.jinja_options = Flask.jinja_options.copy()
    app.jinja_options['loader'] = ThemedTemplateLoader(app)

    # patch static file resolver
    patch_static(app)

    # secret key for cookies
    app.secret_key = os.urandom(24)

    # consider the cydra instance to be a form of configuration
    # and therefore store it in the config dict.
    app.config['cydra'] = cyd

    # common views
    app.add_url_rule('/login', 'login', login)

    # Add shorthands to context
    app.context_processor(add_shorthands_to_context)

    # load frontend and backend
    from cydra.web.frontend import blueprint as frontend_blueprint
    patch_static(frontend_blueprint, 'frontend')
    #from cydra.web.admin import blueprint as admin_blueprint
    #patch_static(admin_blueprint, 'admin')

    app.register_blueprint(frontend_blueprint)
    #app.register_blueprint(admin_blueprint)

    # load additional blueprints
    pages = ExtensionPoint(IBlueprintProvider, component_manager=cyd)
    for bpprovider in pages:
        bp = bpprovider.get_blueprint()
        patch_static(bp, bp.name)
        app.register_blueprint(bp)

    # some utility template filters
    from cydra.web.filters import filters
    map(app.template_filter(), filters)

    # prevent flask from handling exceptions
    app.debug = True

    # add CSRF protection
    csrf(app)

    # wrap in authentication middleware
    from cydra.web.wsgihelper import AuthenticationMiddleware
    app = AuthenticationMiddleware(cyd, app)

    # enable debugging for certain users
    debugusers = cyd.config.get('web').get('debug_users', [])
    if debugusers:
        from cydra.web.debugging import DebuggingMiddleware
        app = DebuggingMiddleware(app, debugusers)

    return app

def add_shorthands_to_context():
    from flask import request

    return dict(cydra_user=request.environ['cydra_user'])

class ThemeDetector(object):
    def __init__(self, default_theme=None):
        self.default_theme = default_theme

    def __call__(self):
        from flask import request, g

        if self.default_theme is not None:
            g.theme = self.default_theme


def login():
    from flask import request, redirect, url_for
    from cydra.web.wsgihelper import InsufficientPermissions

    if request.environ['cydra_user'].is_guest:
        raise InsufficientPermissions()

    return redirect(url_for('frontend.userhome'))

def standalone_serve():
    """Standalone WSGI Server for debugging purposes"""
    from werkzeug import run_simple
    import sys

    port = 8080
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    app = create_app()

    #from werkzeugprofiler import ProfilerMiddleware
    #app = ProfilerMiddleware(app, stream=open('profile_stats.txt', 'w'), accum_count=100, sort_by=('cumulative', 'calls'), restrictions=(.1,))

    run_simple('0.0.0.0', port, app, use_reloader=True,
            use_debugger=True, #use_evalex=True,
            )

