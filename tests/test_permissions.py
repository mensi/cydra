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


def parameterizedGeneric(name, fixture):
    class TestGenericPermissions(getConfiguredTestCase(fixture,
            create_users=[{'username': 'owner', 'full_name': 'Test Owner'},
                          {'username': 'test', 'full_name': 'Tester Testesterus'}],
            create_projects={'test': 'owner'})):
        """Generic tests for permissions, require user store"""

        def test_project_set_get_permission(self):
            self.project_test.set_permission(self.user_test, 'some_object', 'read', True)
            self.assertTrue(self.project_test.get_permission(self.user_test, 'some_object', 'read'))
            self.assertEqual(self.project_test.get_permissions(self.user_test, None), {'some_object': {'read': True}})
            self.assertEqual(self.project_test.get_permissions(self.user_test, 'some_object'), {'read': True})

        def test_project_owner_has_admin(self):
            self.assertIn('admin', self.project_test.get_permissions(self.user_owner, '*'))
            self.assertTrue(self.project_test.get_permissions(self.user_owner, '*')['admin'])
            self.assertTrue(self.project_test.get_permission(self.user_owner, '*', 'admin'))

        def test_project_owner_admin_permission_cannot_be_overwritten(self):
            self.project_test.set_permission(self.user_owner, '*', 'admin', None)
            self.assertTrue(self.project_test.get_permission(self.user_owner, '*', 'admin'))
            self.project_test.set_permission(self.user_owner, '*', 'admin', False)
            self.assertTrue(self.project_test.get_permission(self.user_owner, '*', 'admin'))

    TestGenericPermissions.__name__ = name
    return TestGenericPermissions


def parameterizedInternalProviderOwner(name, fixture):
    class TestInternalProviderOwnerPermissions(getConfiguredTestCase(fixture,
            config={
                'components': {
                    'cydra.permission.InternalPermissionProvider': {
                        'project_owner_permissions':
                            {'admin': True, 'manuallyconfigured': True}
                    }
                }
            },
            create_users=[{'username': 'owner', 'full_name': 'Test Owner'},
                          {'username': 'test', 'full_name': 'Tester Testesterus'}],
            create_projects={'test': 'owner'})):
        """Test that the internal permission provider properly takes owner permissions from config"""

        def test_project_owner_permissions(self):
            self.assertEqual(self.project_test.get_permissions(self.user_owner, None), {'*': {'admin': True, 'manuallyconfigured': True}})
            self.assertEqual(self.project_test.get_permissions(self.user_owner, '*'), {'admin': True, 'manuallyconfigured': True})
            self.assertEqual(self.project_test.get_permissions(self.user_owner, 'some_object'), {'admin': True, 'manuallyconfigured': True})

        def test_project_owner_permissions_cannot_be_overwritten(self):
            self.project_test.set_permission(self.user_owner, '*', 'admin', None)
            self.assertEqual(self.project_test.get_permissions(self.user_owner, None), {'*': {'admin': True, 'manuallyconfigured': True}})
            self.project_test.set_permission(self.user_owner, '*', 'admin', False)
            self.assertEqual(self.project_test.get_permissions(self.user_owner, None), {'*': {'admin': True, 'manuallyconfigured': True}})

        def test_project_owner_permissions_get_properly_merged(self):
            self.project_test.set_permission(self.user_owner, '*', 'foo', True)
            self.assertEqual(self.project_test.get_permissions(self.user_owner, None), {'*': {'admin': True, 'manuallyconfigured': True, 'foo': True}})
            self.assertEqual(self.project_test.get_permissions(self.user_owner, '*'), {'admin': True, 'manuallyconfigured': True, 'foo': True})

    TestInternalProviderOwnerPermissions.__name__ = name
    return TestInternalProviderOwnerPermissions



TestPermissionsGeneric_File = parameterizedGeneric("TestPermissionsGeneric_File", FullWithFileDS)
TestPermissionsInternalProvider_File = parameterizedInternalProviderOwner("TestPermissionsInternalProvider_File", FullWithFileDS)
