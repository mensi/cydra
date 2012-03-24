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
from flask import Blueprint, render_template, abort, redirect, url_for, flash, request, jsonify, current_app
from werkzeug.exceptions import NotFound, BadRequest, Forbidden
from jinja2 import TemplateNotFound
from werkzeug.local import LocalProxy

from cydra.error import CydraError
from cydra.component import ExtensionPoint
from cydra.web.frontend.hooks import *
from cydra.web.wsgihelper import InsufficientPermissions
from cydra.util import get_collator
from cydra.datasource import IPubkeyStore

import logging
logger = logging.getLogger(__name__)

blueprint = Blueprint('frontend', __name__, static_folder='static', template_folder='templates')
cydra_instance = LocalProxy(lambda: current_app.config['cydra'])
cydra_user = LocalProxy(lambda: request.environ['cydra_user'])

@blueprint.route('/')
def index():
    if not cydra_user.is_guest:
        return redirect(url_for('.userhome'))
    return render_template('index.jhtml')

@blueprint.route('/userhome')
def userhome():
    if cydra_user.is_guest:
        raise InsufficientPermissions()

    return render_template('userhome.jhtml',
                           get_global_permission=cydra_instance.get_permission,
                           owned_projects=cydra_instance.get_projects_owned_by(cydra_user),
                           other_projects=cydra_instance.get_projects_user_has_permissions_on(cydra_user))

@blueprint.route('/usersettings')
def usersettings():
    if cydra_user.is_guest:
        raise InsufficientPermissions()

    pubkey_support = True
    pubkeys = []
    try:
        from twisted.conch.ssh import keys
    except:
        pubkey_support = False
    else:
        store = ExtensionPoint(IPubkeyStore, component_manager=cydra_instance)
        pubkeys = store.get_pubkeys(cydra_user)


    return render_template('usersettings.jhtml', pubkey_support=pubkey_support, pubkeys=pubkeys)

@blueprint.route('/usersettings/add_pubkey', methods=['POST'])
def add_pubkey():
    if cydra_user.is_guest:
        raise InsufficientPermissions()

    try:
        from twisted.conch.ssh import keys
        import base64
    except:
        return redirect(url_for('.usersettings'))

    pubkey = request.form.get('key_data', None)
    name = request.form.get('key_name', None)

    if pubkey is None or name is None:
        raise BadRequest('Key or Name missing')

    try:
        pubkey = keys.Key.fromString(pubkey)
    except:
        logger.exception("Unable to parse key")
        flash('Unable to parse key', 'error')
    else:
        store = ExtensionPoint(IPubkeyStore, component_manager=cydra_instance)
        store.add_pubkey(cydra_user, pubkey.blob(), name, pubkey.fingerprint())

    return redirect(url_for('.usersettings'))

@blueprint.route('/usersettings/remove_pubkey', methods=['POST'])
def remove_pubkey():
    if cydra_user.is_guest:
        raise InsufficientPermissions()

    fingerprint = request.form.get('fingerprint', None)
    if fingerprint is None:
        raise BadRequest('Fingerprint missing')

    store = ExtensionPoint(IPubkeyStore, component_manager=cydra_instance)
    store.remove_pubkey(cydra_user, fingerprint=fingerprint)

    return redirect(url_for('.usersettings'))

@blueprint.route('/project/<projectname>/')
def project(projectname):
    project = cydra_instance.get_project(projectname)
    if project is None:
        abort(404)

    if not project.get_permission(cydra_user, '*', 'read'):
        raise InsufficientPermissions()

    repo_viewer_providers = ExtensionPoint(IRepositoryViewerProvider, component_manager=cydra_instance)
    project_action_providers = ExtensionPoint(IProjectActionProvider, component_manager=cydra_instance)
    repository_action_providers = ExtensionPoint(IRepositoryActionProvider, component_manager=cydra_instance)
    featurelist_item_providers = ExtensionPoint(IProjectFeaturelistItemProvider, component_manager=cydra_instance)

    return render_template('project.jhtml',
                           project=project,
                           get_viewers=get_collator(repo_viewer_providers.get_repository_viewers),
                           project_actions=get_collator(project_action_providers.get_project_actions)(project),
                           get_repository_actions=get_collator(repository_action_providers.get_repository_actions),
                           featurelist=get_collator(featurelist_item_providers.get_project_featurelist_items)(project))

@blueprint.route('/project/<projectname>/define_user_project_perms', methods=['POST'])
def define_user_project_perms(projectname):
    project = cydra_instance.get_project(projectname)
    if project is None:
        raise NotFound('Unknown project')

    if not project.get_permission(cydra_user, '*', 'admin'):
        raise InsufficientPermissions()

    username = request.form.get('username', None)
    userid = request.form.get('userid', None)

    if (username is None or username == '') and userid is None:
        raise BadRequest("Either username or userid has to be supplied")

    user = None
    if username is not None and username != '':
        user = cydra_instance.translator.username_to_user(username)
    else:
        user = cydra_instance.translator.userid_to_user(userid)

    if user is None:
        raise BadRequest("Unknown User")

    for perm in ['read', 'write', 'create', 'admin'] if not user.is_guest else ['read']:
        if request.form.get(perm, '') == 'true':
            project.set_permission(user, '*', perm, True)
        else:
            project.set_permission(user, '*', perm, None)

    flash('Permissions successufully set', 'success')
    return redirect(url_for('.project', projectname=projectname))

@blueprint.route('/project/<projectname>/define_group_project_perms', methods=['POST'])
def define_group_project_perms(projectname):
    project = cydra_instance.get_project(projectname)
    if project is None:
        raise NotFound('Unknown project')

    if not project.get_permission(cydra_user, '*', 'admin'):
        raise InsufficientPermissions()

    groupid = request.form.get('groupid', None)

    if groupid is None:
        raise BadRequest("No group supplied")

    group = cydra_instance.translator.groupid_to_group(groupid)

    if group is None:
        raise BadRequest("Unknown Group")

    for perm in ['read', 'write', 'create', 'admin']:
        if request.form.get(perm, '') == 'true':
            project.set_group_permission(group, '*', perm, True)
        else:
            project.set_group_permission(group, '*', perm, None)

    flash('Permissions successufully set', 'success')
    return redirect(url_for('.project', projectname=projectname))

@blueprint.route('/create_project', methods=['POST'])
def create_project():
    if not cydra_instance.get_permission(cydra_user, 'projects', 'create'):
        raise InsufficientPermissions()

    projectname = request.form.get('projectname')

    if not projectname:
        raise BadRequest('Missing project name')

    if cydra_instance.get_project(projectname) is not None:
        flash('There already exists a project with this name', 'error')
        return redirect(url_for('.userhome'))

    project = cydra_instance.datasource.create_project(projectname, cydra_user)
    if project:
        flash('Successfully created new project', 'success')
        return redirect(url_for('.project', projectname=projectname))
    else:
        flash('Project creation failed', 'error')
        return redirect(url_for('.userhome'))

@blueprint.route('/project/<projectname>/create_repository/<repository_type>', methods=['POST'])
def create_repository(projectname, repository_type):
    project = cydra_instance.get_project(projectname)
    if project is None:
        raise NotFound('Unknown Project')

    repository_type = project.get_repository_type(repository_type)
    if repository_type is None:
        raise NotFound('Unknown Repository Type')

    if not repository_type.can_create(project, cydra_user):
        flash('You cannot create a repository of this type', 'error')
        return redirect(url_for('.project', projectname=projectname))

    repository_name = request.form.get('repository_name', None)
    if repository_name is None:
        raise BadRequest('Missing Repository Name')

    params = {}
    for param in repository_type.get_params():
        if param.keyword in request.form:
            value = request.form.get(param.keyword)
            if not param.validate(value):
                raise BadRequest("Invalid value for parameter %s" % param.name)
            params[param.keyword] = value
        else:
            if not param.optional:
                raise BadRequest("Parameter missing: %s" % param.name)

    try:
        repository = repository_type.create_repository(project, repository_name, **params)
    except CydraError as err:
        flash('Repository creation failed: %s' % str(err), 'error')
        return redirect(url_for('.project', projectname=projectname))

    if repository is not None:
        flash('Repository successfully created', 'success')
        return redirect(url_for('.project', projectname=projectname))
    else:
        flash('Repository creation failed', 'error')
        return redirect(url_for('.project', projectname=projectname))

@blueprint.route('/project/<projectname>/delete_repository', methods=['POST'])
def delete_repository(projectname):
    project = cydra_instance.get_project(projectname)
    if project is None:
        raise NotFound('Unknown Project')

    repository_type = project.get_repository_type(request.form.get('repository_type'))
    if repository_type is None:
        raise NotFound('Unknown Repository Type')

    repository = repository_type.get_repository(project, request.form.get('repository_name'))
    if repository is None:
        raise NotFound('Unknown Repository')

    if not repository.can_delete(cydra_user):
        raise InsufficientPermissions()

    repository.delete()
    return redirect(url_for('.project', projectname=projectname))

@blueprint.route('/project/<projectname>/set_repository_param', methods=['POST'])
def set_repository_param(projectname):
    project = cydra_instance.get_project(projectname)
    if project is None:
        raise NotFound('Unknown Project')

    repository_type = project.get_repository_type(request.form.get('repository_type'))
    if repository_type is None:
        raise NotFound('Unknown Repository Type')

    repository = repository_type.get_repository(project, request.form.get('repository_name'))
    if repository is None:
        raise NotFound('Unknown Repository')

    if not repository.can_modify_params(cydra_user):
        raise InsufficientPermissions()

    if 'param' not in request.form or 'value' not in request.form:
        raise BadRequest()

    repository.set_params(**{request.form['param']: request.form['value']})
    return redirect(url_for('.project', projectname=projectname))

@blueprint.route('/is_projectname_available')
def is_projectname_available():
    if not cydra_instance.get_permission(cydra_user, 'projects', 'create'):
        raise InsufficientPermissions()

    projectname = request.args.get('projectname', None)

    if projectname:
        if cydra_instance.get_project(projectname) is None:
            return jsonify(available=True)

    return jsonify(available=False)

@blueprint.route('/project/<projectname>/perms')
def project_perms(projectname):
    project = cydra_instance.get_project(projectname)
    if project is None:
        raise NotFound("Unknown Project")

    if not project.get_permission(cydra_user, '*', 'read'):
        raise InsufficientPermissions()

    username = request.args.get('username', None)
    userid = request.args.get('userid', None)

    if username is None and userid is None:
        raise BadRequest("Either username or userid has to be supplied")

    user = None
    if username is not None and username != '':
        user = cydra_instance.translator.username_to_user(username)
    else:
        user = cydra_instance.translator.userid_to_user(userid)

    if user is None:
        raise BadRequest("Invalid User")

    return jsonify(userid=user.userid, username=user.username, user_full_name=user.full_name, perms=project.get_permissions(user, '*'))

@blueprint.route('/project/<projectname>/group_perms')
def project_group_perms(projectname):
    project = cydra_instance.get_project(projectname)
    if project is None:
        raise NotFound("Unknown Project")

    if not project.get_permission(cydra_user, '*', 'read'):
        raise InsufficientPermissions()

    groupid = request.args.get('groupid', None)

    if groupid is None:
        raise BadRequest("groupid has to be supplied")

    group = cydra_instance.translator.groupid_to_group(groupid)

    if group is None:
        raise BadRequest("Invalid Group")

    return jsonify(groupid=group.groupid, group_name=group.name, perms=project.get_group_permissions(group, '*'))
