# -*- coding: utf-8 -*-
from __future__ import absolute_import
import unittest

from .procutils import ProcessHelpers

from cydra import Cydra
from cydra.permission import User

def getConfiguredTestCase(fixture):
    class ConfiguredTestCase(ProcessHelpers, unittest.TestCase):
        def setUp(self):
            config = {}
            fixture.setUp(config)
            self.cydra = Cydra(config)

        def tearDown(self):
            fixture.tearDown()

    return ConfiguredTestCase
