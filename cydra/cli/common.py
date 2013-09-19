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
from itertools import chain
from cydra.component import Interface, BroadcastAttributeProxy


class ICliProjectCommandProvider(Interface):

    _iface_attribute_proxy = BroadcastAttributeProxy()

    def get_cli_project_commands(self):
        """Provide further commands for the CLI

        :returns: A list of ('command', function) tuples"""
        pass


class Command(object):
    def __init__(self, cydra_instance):
        self.cydra = cydra_instance

    def __call__(self, args):
        """By default, dispatch commands to methods by name"""
        if len(args) < 1:
            return self.help(args)

        if hasattr(self, args[0]):
            return getattr(self, args[0])(args[1:])
        else:
            return self.help(args)

    def help(self, args):
        if len(args) == 1:
            if hasattr(self, args[0]):
                print(getattr(self, args[0]).__doc__)
                return
            else:
                print("Unknown command: " + args[0])

        cmds = [x for x in chain(self.__class__.__dict__, self.__dict__)
                if callable(getattr(self, x)) and x[0] != '_']
        maxlen = max(len(x) for x in cmds)
        print("Available commands:")
        for cmd in cmds:
            doc = getattr(self, cmd).__doc__
            doc = doc if doc is not None else ""
            print('\t' + cmd + ': ' + ' ' * (maxlen - len(cmd)) +
                  doc.split('\n')[0])
