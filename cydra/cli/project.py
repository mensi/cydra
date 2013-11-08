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
import types
from pprint import pprint

from cydra.component import ExtensionPoint
from cydra.cli.common import Command, ICliProjectCommandProvider


class ProjectCommand(Command):
    def __init__(self, cydra_instance):
        super(ProjectCommand, self).__init__(cydra_instance)

        further_commands = ExtensionPoint(ICliProjectCommandProvider,
                    component_manager=self.cydra).get_cli_project_commands()
        commands = []
        for x in further_commands:
            if x is None:
                continue
            commands.extend(x)

        for cmd in commands:
            func = lambda x, y: cmd[1](self.project, y)
            func.__doc__ = cmd[1].__doc__
            func.__name__ = cmd[0]
            setattr(self, cmd[0], types.MethodType(func, self, self.__class__))

    def __call__(self, args):
        if len(args) < 2:
            print("Syntax: project <projectname> <command>")
            return self.help(args[1:])

        self.project = self.cydra.get_project(args[0])
        if self.project is None:
            print("Unknown Project: " + args[0])
            return

        super(ProjectCommand, self).__call__(args[1:])

    def delete(self, args):
        """Deletes a project"""
        self.project.delete()

    def listrepos(self, args):
        """List all repositories in project"""
        repos = []
        for repotype in self.project.repositories:
            repos.extend(repotype.get_repositories(self.project))

        print(', '.join(['%s (%s)' % (r.name, r.type) for r in repos]))

    def sync(self, args):
        """Sync project"""
        if self.project.sync():
            print("Sync successful")
        else:
            print("Sync failed")

    def syncrepos(self, args):
        """Sync all repositories in project"""
        repos = []
        for repotype in self.project.get_repository_types():
            repos.extend(repotype.get_repositories(self.project))

        for repo in repos:
            print("Syncing: %s (%s)" % (repo.name, repo.type))

            repo.sync()

    def createrepo(self, args):
        """Create a new repository

        Syntax: createrepo <type> <name>"""

        if len(args) < 2:
            return self.help(['createrepo'])

        repotype = None
        for rt in self.project.repositories:
            if rt.repository_type == args[0]:
                repotype = rt
                break

        if repotype is None:
            print("Unknown repository type!")
            return

        repotype.create_repository(self.project, args[1])

    def postcommit(self, args):
        """Post commit hook for one or more revisions

        Syntax: postcommit <type> <name> <rev+>"""

        if len(args) < 3:
            return self.help(['postcommit'])

        repository = self.project.get_repository(args[0], args[1])

        if not repository:
            print("Unknown repository")
            return

        repository.notify_post_commit(args[2:])

    def setperm(self, args):
        """Set permission

        Syntax: setperm <userid> <object> <permission> <value>"""
        if len(args) != 4:
            return self.help(['setperm'])

        value = args[3]
        if value.lower() in ['true', 'yes', 'y', '1']:
            value = True
        elif value.lower() in ['false', 'no', 'n', '0']:
            value = False
        elif value.lower() in ['none']:
            value = None
        else:
            print("Unknown value:", value)
            return

        user = self.cydra.get_user(userid=args[0])

        if self.project.set_permission(user, args[1], args[2], value):
            print("Done")
        else:
            print("Failed")

    def setgroupperm(self, args):
        """Set group permission

        Syntax: setgroupperm <groupid> <object> <permission> <value>"""
        if len(args) != 4:
            return self.help(['setgroupperm'])

        value = args[3]
        if value.lower() in ['true', 'yes', 'y', '1']:
            value = True
        elif value.lower() in ['false', 'no', 'n', '0']:
            value = False
        elif value.lower() in ['none', 'unset']:
            value = None
        else:
            print("Unknown value:", value)
            return

        group = self.cydra.get_group(groupid=args[0])

        if self.project.set_group_permission(group, args[1], args[2], value):
            print("Done")
        else:
            print("Failed")

    def setowner(self, args):
        """Set owner of project

        Syntax: setowner <username>"""
        user = self.cydra.get_user(username=args[0])

        assert(user)
        self.project.data['owner'] = user.userid
        self.project.save()

        print(user.full_name, 'is now the new owner of project',
              self.project.name)

    def getperm(self, args):
        """Get permission

        Syntax: getperm <userid> <object> <permission>"""

        if len(args) != 3:
            return self.help(['getperm'])

        print self.project.get_permission(args[0], args[1], args[2])

    def dump(self, args):
        """Dump project data"""
        pprint(self.project.data)
