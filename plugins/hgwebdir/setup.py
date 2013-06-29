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

setup(name='CydraHgWebdir',
      install_requires=['Cydra >=0.1', 'mercurial'],
      description='Cydra plugin for hgwebdir',
      keywords='cydra hgwebdir',
      version='0.2.0',
      url='http://www.cydra.org',
      license='GPL',
      author='Manuel Stocker',
      author_email='mensi@vis.ethz.ch',
      long_description="""This plugin integrates hgwebdir with Cydra""",
      namespace_packages=['cydraplugins'],
      packages=['cydraplugins', 'cydraplugins.hgwebdir'],
      package_data={
          #'': ['COPYING', 'README'],
          },
      entry_points={'cydra.plugins': 'cydraplugins.hgwebdir = cydraplugins.hgwebdir',
                    'console_scripts': 'cydra-hgwebdird = cydraplugins.hgwebdir:standalone_serve'})
