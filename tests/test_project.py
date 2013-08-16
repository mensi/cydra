# -*- coding: utf-8 -*-
#
# Copyright 2013 Manuel Stocker <mensi@mensi.ch>
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
import os.path
from cydra.test.fixtures import *
from cydra.test import getConfiguredTestCase

def parameterized(name, fixture):
    class TestProjectOps(getConfiguredTestCase(fixture)):
        """Tests for basic project functionality"""

        def test_create(self):
            user = self.cydra.get_user(userid='*')
            proj1 = self.cydra.datasource.create_project('project1', user)
            self.assertTrue(proj1, "Project creation failed")

            proj2 = self.cydra.get_project('project1')
            self.assertTrue(proj2, "Unable to get created project")
            self.assertEqual(proj1, proj2, "Project retrieved is not the same as the created project")
            self.assertEqual(proj2.owner, user, "User of created project is not correct")

            self.assertIsNone(self.cydra.datasource.create_project('project1', user), "Duplicate project creation possible")

        def test_delete(self):
            project1 = self.cydra.datasource.create_project('project1', self.cydra.get_user(userid='*'))
            project2 = self.cydra.datasource.create_project('project2', self.cydra.get_user(userid='*'))
            self.assertTrue(project1, "Project creation failed")

            project1_2nd = self.cydra.get_project('project1')
            self.assertTrue(project1_2nd, "Unable to get created project")
            self.assertEqual(project1, project1_2nd, "Project retrieved is not the same as the created project")
            self.assertIsNotNone(self.cydra.get_project('project2'), "Project2 not found")

            project1.delete()
            self.assertIsNone(self.cydra.get_project('project1'), "Project was NOT deleted properly")
            self.assertIsNotNone(self.cydra.get_project('project2'), "Project2 was errornously deleted")

        def test_delete_with_repos(self):
            project = self.cydra.datasource.create_project('project', self.cydra.get_user(userid='*'))
            repopaths = []

            for repotype in project.get_repository_types():
                repo = repotype.create_repository(project, "project")
                self.assertTrue(repo, "Unable to create repo of type " + repotype.repository_type)
                repopaths.append(repo.path)

            self.assertGreater(len(repopaths), 0, "No repositories created")
            for path in repopaths:
                self.assertTrue(os.path.exists(path), "Repository path does not exist")
            project.delete()

            for path in repopaths:
                self.assertFalse(os.path.exists(path), "Repository path was not removed")


    TestProjectOps.__name__ = name
    return TestProjectOps

TestProjectOps_File = parameterized("TestProjectOps_File", FullWithFileDS)
TestProjectOps_Mongo = parameterized("TestProjectOps_Mongo", FullWithMongoDS)

