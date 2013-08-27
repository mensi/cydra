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
import sys
from cydra import Cydra
from cydra.cli.common import Command, ICliProjectCommandProvider
from cydra.cli.project import ProjectCommand

class RootCommand(Command):
    def project(self, args):
        """Commands on projects"""
        return ProjectCommand(self.cydra)(args)

    def sync(self, args):
        """Sync all projects"""
        projects = self.cydra.get_project_names()

        for projectname in projects:
            project = self.cydra.get_project(projectname)

            if not project:
                print "Unknown Project:", projectname
            else:
                if project.sync():
                    print "Synced Project:", projectname
                else:
                    print "Synced FAILED:", projectname


def main():
    import logging
    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False)
    (options, args) = parser.parse_args()

    if options.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)

    cydra_instance = Cydra()

    RootCommand(cydra_instance)(args)
