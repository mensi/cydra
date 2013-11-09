#!/usr/bin/env python
from setuptools import setup, find_packages

setup(name='CydraActiveDirectory',
      install_requires=['Cydra >=0.3', 'python-ldap'],
      description='Cydra plugin for AD integration',
      keywords='cydra active directory',
      version='0.2',
      url='',
      license='',
      author='Manuel Stocker',
      author_email='mensi@mensi.ch',
      long_description="""Integration of cydra with Active Directory""",
      namespace_packages=['cydraplugins'],
      packages=['cydraplugins', 'cydraplugins.activedirectory'],
      package_data={
          #'': ['COPYING', 'README'],
          },
      entry_points={'cydra.plugins': 'cydraplugins.activedirectory = cydraplugins.activedirectory'})
