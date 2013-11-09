# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest

from .procutils import ProcessHelpers

from cydra import Cydra
from cydra.permission import User


def getConfiguredTestCase(fixture, create_users=None, create_projects=None):
    class ConfiguredTestCase(ProcessHelpers, unittest.TestCase):
        def setUp(self):
            config = {}
            fixture.setUp(config)
            self.cydra = Cydra(config)

            if create_users is not None:
                for user in create_users:
                    setattr(self, "user_" + user['username'], self.cydra.create_user(**user))

            if create_projects is not None:
                for projectname, owner in create_projects.items():
                    if not hasattr(owner, 'id'):
                        owner = self.cydra.get_user(userid=owner)
                    setattr(self, "project_" + projectname, self.cydra.create_project(projectname, owner))

        def tearDown(self):
            fixture.tearDown()

    return ConfiguredTestCase
