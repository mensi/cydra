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


def parameterizedStaticDefaultConfigurator(name, fixture):
    class TestStaticDefaultConfigurator(getConfiguredTestCase(fixture,
            config={
                'components': {
                    'cydra.project.configurators.StaticDefaultConfigurator': {
                        'config': {
                            'owner': 'test',
                            'permissions': {
                                'test': {
                                    '*': {'read': True}
                                }
                            }
                        }
                    },
                    'cydra.permission.InternalPermissionProvider': True
                }
            },
            create_users=[{'username': 'owner', 'full_name': 'Test Owner'},
                          {'username': 'test', 'full_name': 'Tester Testesterus'}],
            create_projects={'test': 'owner'})):
        """Test that the internal permission provider properly takes owner permissions from config"""

        def test_owner_overridable(self):
            self.assertEqual(self.project_test.owner, self.user_test)
            self.assertNotEqual(self.project_test.owner, self.user_owner)

        def test_internal_permissions_overridable(self):
            self.assertTrue(self.project_test.get_permission(self.user_test, 'some_object', 'read'))

    TestStaticDefaultConfigurator.__name__ = name
    return TestStaticDefaultConfigurator


TestStaticDefaultConfigurator_File = parameterizedStaticDefaultConfigurator("TestStaticDefaultConfigurator_File", FullWithFileDS)
