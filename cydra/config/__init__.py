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

__all__ = ['Configuration', 'MergeException', 'IConfigurationProvider']

from cydra.component import ExtensionPoint, Interface, Component
from cydra.loader import load_components

default_configuration = {
    'components': {
        'cydra.config.file.ConfigurationFile': True
    },
    'web': {
        'auth_realm': 'Cydra'
    }
}

class IConfigurationProvider(Interface):
    """Interface for Components providing configuration"""

    def get_config(self):
        """Returns a dict with configuration data"""
        pass

class MergeException(Exception):
    pass

class Configuration(Component):
    """Encapsulates the configuration
    
    Configuration is held as a dict
    
    Example::
    
        {
            'plugin_paths': ['/some/path'],
            'components':
            {
                'component_a': True,
                'component_b': {'someoption': 42}
            },
            'extension_points':
            {
                'ep_a': {'someoption': 42}
            }
        }
    """

    configuration_providers = ExtensionPoint(IConfigurationProvider)

    def __init__(self):
        """Initialize Configuration"""
        self.cydra = self.compmgr
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def get_component_config(self, component, default=None):
        """Find configuration node for a component
        
        """
        ret = self._data.setdefault('components', {}).get(component, default)

        # since setting a component to True or False is a short-hand to enable/disable
        # the component, also return the default in this case
        if isinstance(ret, bool):
            return default
        else:
            return ret

    def is_component_enabled(self, component):
        return bool(self._data.setdefault('components', {}).get(component, False))

    def load(self, config=None):
        """Load configuration data into the config tree
        
        If config is None, the default configuration will be loaded
        """
        providers = set(self.configuration_providers) # copy the providers for later reference

        if config is not None:
            self._load(config)
        elif self._data == {} or self._data == {'components':{}}: #only load default config if config is empty
            self._load(default_configuration)

        # if new configuration providers have been enabled, query them
        for provider in self.configuration_providers:
            if provider not in providers:
                self.load(provider.get_config())

    def _load(self, config):

        root = self._data
        plugin_paths_dirty = False

        for k, v in config.iteritems():
            if k == 'plugin_paths':
                self._data.setdefault('plugin_paths', set()).update(config['plugin_paths'])
                plugin_paths_dirty = True
            else:
                if isinstance(v, dict):
                    self.merge(self._data.setdefault(k, dict()), v)
                elif isinstance(v, list):
                    self._data.setdefault(k, list()).extend(v)
                elif isinstance(v, set):
                    self._data.setdefault(k, set()).update(v)
                else:
                    self._data[k] = v

        if plugin_paths_dirty :
            load_components(self.cydra, self._data.get('plugin_paths', set())) # new plugin paths, load from those

    def merge(self, dest, source):
        """Merges a subtree into a subtree of the config
        
        Recurses into dicts
        
        :param dest: Object to merge into. This should be a node of the config tree
        :param source: Source for merge.
        """
        if type(dest) != type(source):
            raise MergeException("Types do not match: %s, %s" % (type(dest).__name__, type(source).__name__))

        if isinstance(dest, dict):
            for k, v in source.iteritems():
                if isinstance(v, dict):
                    self.merge(dest.setdefault(k, dict()), v)
                elif isinstance(v, list):
                    dest.setdefault(k, list()).extend(v)
                elif isinstance(v, set):
                    dest.setdefault(k, set()).update(v)
                else:
                    dest[k] = v
        else:
            raise MergeException("Unhandled type: " + type(dest).__name__)
