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

setup(name='CydraGitHTTP',
      install_requires='Cydra >=0.1',
      description='Cydra plugin for git http serving',
      keywords='cydra git http',
      version='0.1',
      url='http://www.cydra.org',
      license='GPL',
      author='Manuel Stocker, D. Dotsenko',
      author_email='mensi@vis.ethz.ch, dotsa@hotmail.com',
      long_description="""This plugin provides methods to serve git repositories over HTTP""",
      namespace_packages=['cydraplugins'],
      packages=['cydraplugins', 'cydraplugins.githttp'],
      package_data={
          #'': ['COPYING', 'README'],
          },
      entry_points={'cydra.plugins': 'githttp = cydraplugins.githttp',
                    'console_scripts': ['cydra-githttpd = cydraplugins.githttp:standalone_serve', 'cydra-gittornado = cydraplugins.githttp.gittornado_integration:run_server']})
