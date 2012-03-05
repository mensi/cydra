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

class CydraError(Exception):
    """Base exception for all errors"""

    def __init__(self, msg="Error", **kwargs):
        self._args = kwargs
        self.msg = msg

        self.__dict__.update(kwargs)

    def __str__(self):
        return self.msg + " (" + ', '.join([x[0] + '=' + str(x[1]) for x in self._args.items()]) + ")"

    def __repr__(self):
        return self.__class__.__name__ + '(' + repr(self.msg) + ', ' + ', '.join([x[0] + '=' + repr(x[1]) for x in self._args.items()]) + ')'

def create_error(name, msg):
    """Helper function to define new errors
    
    use like this: TestError = create_error("TestError", "Test Message") in modules"""

    def new_init(self, **kwargs):
        CydraError.__init__(self, msg, **kwargs)

    return type(name, (CydraError,), {'__init__': new_init})

class InsufficientConfiguration(CydraError):
    """Configuration values missing but needed
    
    Params:
    missing: name of the value
    component: name of component"""

    def __str__(self):
        return "Configuration is not sufficient for component %s. No value for %s" % (self.component, self.missing)

class UnknownRepository(CydraError):
    """Repository that was asked for is unknown
    
    Params:
    repository_name: name of the repository
    repository_type: type of the repository
    project_name: name of project the repository is in"""

    def __str__(self):
        return "The Project %s does not contain a repository named %s of type %s" % (self.project_name, self.repository_name, self.repository_type)
