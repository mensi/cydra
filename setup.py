#!/usr/bin/env python
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
from setuptools import setup, find_packages

setup(
    name='Cydra',
    version='0.1.2',
    description='Code hosting platform',
    long_description="Cydra provides a platform to build code hosting services similar to systems like sourceforge or google code",
    author='Manuel Stocker',
    author_email='mensi@mensi.ch',
    license='GPL',
    url='http://www.cydra.org',
#    download_url='http://www.cydra.org/download/cydra-0.1.0.tar.gz',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],

    setup_requires=[],
    install_requires=[
        'setuptools>=0.6b1',
        'Flask',
        'flask-csrf',
        'Werkzeug'
    ],
    extras_require={},

    entry_points="""
        [console_scripts]
        cydra-admin = cydra.cli:main
        cydra-httpd = cydra.web:standalone_serve
        cydra-git-post-receive = cydra.repository.git:post_receive_hook
        cydra-hg-commit = cydra.repository.hg:commit_hook
        cydra-svn-commit = cydra.repository.svn:commit_hook

        [cydra.plugins]
        cydra.config.file = cydra.config.file
        cydra.datasource.mongo = cydra.datasource.mongo
        cydra.repository.git = cydra.repository.git
        cydra.repository.hg = cydra.repository.hg
        cydra.repository.svn = cydra.repository.svn
        cydra.caching.subject = cydra.caching.subject
        cydra.permission.htpasswd = cydra.permission.htpasswd
    """,

    packages=find_packages(),
    package_data={
        'cydra': ['repository/scripts/*.sh',
                  'web/templates/*.jhtml',
                  'web/static/*.js',
                  'web/static/*.css',
                  'web/static/jquery-ui-smoothness/*.css',
                  'web/static/jquery-ui-smoothness/images/*.png',
                  'web/frontend/templates/*.jhtml'],
    },
    zip_safe=False,
)
