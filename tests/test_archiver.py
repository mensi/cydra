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
import subprocess
from cydra.test.fixtures import FixtureWithTempPath, FullWithFileDS
from cydra.test import getConfiguredTestCase


class ArchiverFixture(FixtureWithTempPath):
    """Configure archiving"""

    def setUp(self, configDict):
        super(ArchiverFixture, self).setUp(configDict)
        configDict['archive_path'] = self.path


def parameterized(name, fixture):
    class TestArchiver(getConfiguredTestCase(fixture)):
        """Tests for archiver"""

        def test_archive_on_delete(self):
            project = self.cydra.create_project('test', self.cydra.get_user(userid='*'))
            self.assertTrue(project, "Project creation failed")

            # set some arbitrary conf values we can check for
            project.data['test'] = 'test'

            # create repos
            created_repos = []
            for repotype in project.get_repository_types():
                repo = repotype.create_repository(project, "test")
                self.assertTrue(repo, "Unable to create repo of type " + repotype.repository_type)
                created_repos.append(repotype.repository_type)

            project.delete()
            self.assertIsNone(self.cydra.get_project('test'), "Project was NOT deleted properly")

            # verify archive exists
            archive_path = os.path.join(self.cydra.config.get('archive_path'), "test")
            extracted_path = os.path.join(archive_path, "extracted")
            files = os.listdir(archive_path)
            self.assertTrue(len(files) == 1, "Unexpected number of archives")

            os.mkdir(extracted_path)
            ret = subprocess.call(["tar", "-xf", os.path.join(archive_path, files[0]), "-C", extracted_path])

            self.assertTrue(ret == 0, "Extraction failed")
            self.assertTrue(os.path.exists(os.path.join(extracted_path, "project_data")), "Project data not in archive")

    TestArchiver.__name__ = name
    return TestArchiver

TestArchiver_File = parameterized("TestArchiver_File", ArchiverFixture(FullWithFileDS))
