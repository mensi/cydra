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
from cydra.test.fixtures import FullWithFileDS
from cydra.test import getConfiguredTestCase


def parameterized(name, fixture):
    class TestPermissions(getConfiguredTestCase(fixture,
            create_users=[{'username': 'owner', 'full_name': 'Test Owner'},
                          {'username': 'test', 'full_name': 'Tester Testesterus'}],
            create_projects={'test': 'owner'})):
        """Tests for permissions"""

        def test_project_set_get_permission(self):
            self.project_test.set_permission(self.user_test, 'some_object', 'read', True)
            self.assertTrue(self.project_test.get_permission(self.user_test, 'some_object', 'read'))
            self.assertEqual(self.project_test.get_permissions(self.user_test, None), {'some_object': {'read': True}})
            self.assertEqual(self.project_test.get_permissions(self.user_test, 'some_object'), {'read': True})

    TestPermissions.__name__ = name
    return TestPermissions

TestPermissions_File = parameterized("TestPermissions_File", FullWithFileDS)
