#!/usr/bin/env python
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
from setuptools import setup, find_packages

setup(name='CydraGitServerGlue',
      install_requires=['Cydra >=0.1', 'GitServerGlue>=0.3'],
      description='Cydra plugin for ssh-based repository serving',
      keywords='cydra ssh',
      version='0.3.1',
      url='http://www.cydra.org',
      license='GPL',
      author='Manuel Stocker',
      author_email='mensi@vis.ethz.ch',
      long_description="""Integrates GitServerGlue with Cydra""",
      namespace_packages=['cydraplugins'],
      packages=['cydraplugins', 'cydraplugins.gitserverglue'],
      package_data={
          # '': ['COPYING', 'README'],
          },
      entry_points={'cydra.plugins': 'cydraplugins.gitserverglue = cydraplugins.gitserverglue',
                    'console_scripts': ['cydra-gitserverglue = cydraplugins.gitserverglue:run_server']})
