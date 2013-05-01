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
#
# This file also contains code from trac, see trac/core.py

__all__ = ['Component', 'implements', 'Interface', 'ExtensionPoint',
           'FallbackAttributeProxy', 'BroadcastAttributeProxy']

import warnings
import logging
logger = logging.getLogger(__name__)

class Interface(object):
    """Marker base class for extension point interfaces.
    
    Behavior of the ExtensionPoints for an interface can be customized with 
    _iface_XY class attributes. These behaviors are specified in the interface 
    in order to establish common ground rules in accessing the components for 
    an interface."""

    _iface_single_extension = False
    """Only allow one active component for this interface"""

    _iface_attribute_proxy = None
    """Callable to use for attribute access
    
    The callable will receive the paramenters interface, components and name (in this order)"""

    _iface_disable_extension_cache = False
    """Disable the cache for the active extensions"""

class ExtensionPoint(object):
    """Extension point for an interface
    
    You can use an extension point in a class definition::
    
        class Foo(Component):
            bars = ExtensionPoint(IBar)
            
            def __init__(self):
                print(list(self.bars))
    
    Or standalone::
    
        def foo():
            c = Cydra()
            bars = ExtensionPoint(IBar, component_manager=cydra)
            print(list(bars))
            
    In both cases, the extension point has to be bound to a component manager
    before usage. When used in a class definition, the class has to have a
    compmgr attribute at runtime; children of Component that are loaded via
    the component machinery will already satisfy this condition. Standalone
    extension point instances have to be supplied with a component manager
    explicitly.
    
    Iterating an extension point will yield the enabled components implementing
    the given interface. Further behaviour depends on the interface itself. Usually
    you will be able to call the interfaces functions. Depending on the attribute
    proxy specified in the interface, function calls will be performed on all
    components or in another way. See :class:`Interface`,
    :class:`BroadcastAttributeProxy` and :class:`BroadcastAttributeProxy` for
    further details"""

    _caching = True
    """Is caching enabled for this ExtensionPoint?"""

    _cache = None
    """The cache of components are relevant to this ExtensionPoint"""

    _ep_cache = None
    """The cache of ComponentManager to ExtensionPoint mapping"""

    def __init__(self, interface, name=None, component_manager=None, caching=True):
        self._interface = interface
        self._ep_cache = {}

        if caching == False or interface._iface_disable_extension_cache == False:
            self._caching = False

        if name is None:
            name = interface.__name__

        self._name = name
        self._component_manager = component_manager

        # hackedy hack docstring for sphinx
        self.__doc__ = ':class:`cydra.component.ExtensionPoint` for :class:`%s`' % (
            interface.__module__ + '.' + interface.__name__,)

    def _get_extensions(self):
        if self._component_manager is None:
            raise ValueError("Component manager not set")

        if self._cache is not None:
            return self._cache

        classes = ComponentMeta._registry.get(self._interface, ())
        components = [self._component_manager[cls] for cls in classes if self._component_manager[cls]]

        order = self._component_manager.config.get('extensionpointorder', {}).get(self._name, [])
        if order:
            def sort_key(component):
                if component.get_component_name() in order:
                    return order.index(component.get_component_name())
                elif component.get_component_shortname() in order:
                    return order.index(component.get_component_shortname())
                else:
                    return len(order) + 1

            components.sort(key=sort_key)

        if self._interface._iface_single_extension and len(components) != 1:
            raise Exception("Interface " + self._name + " has " + str(len(components)) + " components activated but only allows 1")

        if self._caching:
            self._cache = components

        return components

    # Descriptor protocol for property-like usage
    def __get__(self, obj, typ=None):
        if obj is None:
            return self

        if self._component_manager is not None:
            logger.warn("__get__ on ExtensionPoint that has already been bound to a compmgr")

        if obj.compmgr not in self._ep_cache:
            self._ep_cache[obj.compmgr] = self.__class__(
                self._interface,
                name=self._name,
                component_manager=obj.compmgr,
                caching=self._caching
            )

        return self._ep_cache[obj.compmgr]

    # Iterator protocol for iteration over extensions
    def __iter__(self):
        return iter(self._get_extensions())

    # Attribute access
    def __getattr__(self, name):
        if self._interface._iface_single_extension:
            return getattr(self._get_extensions()[0], name)

        if self._interface._iface_attribute_proxy is None:
            raise Exception("Interface " + self._name + " does not specify an attribute proxy")

        return self._interface._iface_attribute_proxy(self._interface, self._get_extensions(), name)

    # Repr and stuff
    def __repr__(self):
        return '<ExtensionPoint for Interface %s>' % (self._name,)


class FallbackAttributeProxy(object):
    """Proxy for use in interfaces
    
    Tries one extension after the other until something not None is returned"""

    def __init__(self):
        pass

    def __call__(self, interface, components, name):
        def call_all_components(*args, **kwargs):
            for o in components:
                ret = getattr(o, name)(*args, **kwargs)
                if ret is not None:
                    return ret

        if callable(getattr(interface, name)):
            return call_all_components
        else:
            for o in components:
                ret = getattr(o, name)
                if ret is not None:
                    return ret
            return None

class BroadcastAttributeProxy(object):
    """Proxy for use in interfaces
    
    Calls all extensions and returns a list with the results"""

    def __init__(self, merge_lists=False):
        """Init BroadcastAttributeProxy
        
        :param merge_lists: Consider return values to be lists and merge them into a single list"""
        self.merge_lists = merge_lists

    def __call__(self, interface, components, name):
        def call_all_components(*args, **kwargs):
            return self.post_process([getattr(o, name)(*args, **kwargs) for o in components if hasattr(o, name)])

        if callable(getattr(interface, name)):
            return call_all_components
        else:
            return self.post_process([getattr(o, name) for o in components if hasattr(o, name)])

    def post_process(self, result):
        if self.merge_lists:
            res = []
            for l in result:
                if l is None:
                    continue
                if isinstance(l, list):
                    res.extend(l)
                else:
                    res.append(l)
            result = res
        return result

class ComponentMeta(type):
    """Meta class for components.
    
    Takes care of component and extension point registration.
    """
    _components = []
    _registry = {}

    def __new__(mcs, name, bases, d):
        """Create the component class."""

        new_class = type.__new__(mcs, name, bases, d)
        if name == 'Component':
            # Don't put the Component base class in the registry
            return new_class

        if d.get('abstract'):
            # Don't put abstract component classes in the registry
            return new_class

        ComponentMeta._components.append(new_class)
        registry = ComponentMeta._registry
        for cls in new_class.__mro__:
            for interface in cls.__dict__.get('_implements', ()):
                classes = registry.setdefault(interface, [])
                if new_class not in classes:
                    classes.append(new_class)

        return new_class

    def __call__(cls, *args, **kwargs):
        """Return an existing instance of the component if it has
        already been activated, otherwise create a new instance.
        """
        # If this component is also the component manager, just invoke that
        if issubclass(cls, ComponentManager):
            self = cls.__new__(cls)
            self.compmgr = self
            self.__init__(*args, **kwargs)
            return self

        # The normal case where the component is not also the component manager
        compmgr = args[0]
        self = compmgr.components.get(cls)
        # Note that this check is racy, we intentionally don't use a
        # lock in order to keep things simple and avoid the risk of
        # deadlocks, as the impact of having temporarily two (or more)
        # instances for a given `cls` is negligible.
        if self is None:
            self = cls.__new__(cls)
            self.compmgr = compmgr
            compmgr.component_activated(self)
            self.__init__()
            # Only register the instance once it is fully initialized (#9418)
            compmgr.components[cls] = self
        return self


class Component(object):
    """Base class for components.

    Every component can declare what extension points it provides, as
    well as what extension points of other components it extends.
    """
    __metaclass__ = ComponentMeta
    __config = None

    @staticmethod
    def implements(*interfaces):
        """Can be used in the class definition of `Component`
        subclasses to declare the extension points that are extended.
        """
        import sys

        frame = sys._getframe(1)
        locals_ = frame.f_locals

        # Some sanity checks
        assert locals_ is not frame.f_globals and '__module__' in locals_, \
               'implements() can only be used in a class definition'

        locals_.setdefault('_implements', []).extend(interfaces)

    def get_component_name(self):
        return self.__class__.__module__ + '.' + self.__class__.__name__

    def get_component_shortname(self):
        return self.__class__.__name__

    def get_component_config(self, default={}):
        return self.compmgr.config.get_component_config(self.get_component_name(), default)

    @property
    def component_config(self):
        if self.__config is None:
            self.__config = self.get_component_config()

        return self.__config


implements = Component.implements


class ComponentManager(object):
    """The component manager keeps a pool of active components."""

    def __init__(self):
        """Initialize the component manager."""
        self.components = {}
        self.enabled = {}
        if isinstance(self, Component):
            self.components[self.__class__] = self

    def __contains__(self, cls):
        """Return wether the given class is in the list of active
        components."""
        return cls in self.components

    def __getitem__(self, cls):
        """Activate the component instance for the given class, or
        return the existing instance if the component has already been
        activated.
        """
        component = self.components.get(cls)
        if component is not None:
            return component  # if there already is an instance, just return it

        if not self.is_enabled(cls):
            # logger.debug("Component %s is not enabled" % cls.__name__)
            return None

        if cls not in ComponentMeta._components:
            raise Exception('Component "%s" not registered' % cls.__name__)
        try:
            component = cls(self)
        except TypeError, e:
            raise Exception('Unable to instantiate component %r (%s)' %
                            (cls, e))
        return component

    def is_enabled(self, cls):
        """Return whether the given component class is enabled."""
        # if cls not in self.enabled:
        #    self.enabled[cls] = self.is_component_enabled(cls)
        # return self.enabled[cls]
        return self.is_component_enabled(cls)

    def disable_component(self, component):
        """Force a component to be disabled.
        
        :param component: can be a class or an instance.
        """
        if not isinstance(component, type):
            component = component.__class__
        self.enabled[component] = False
        self.components[component] = None

    def component_activated(self, component):
        """Can be overridden by sub-classes so that special
        initialization for components can be provided.
        """

    def is_component_enabled(self, cls):
        """Can be overridden by sub-classes to veto the activation of
        a component.

        If this method returns `False`, the component was disabled
        explicitly.  If it returns `None`, the component was neither
        enabled nor disabled explicitly. In both cases, the component
        with the given class will not be available.
        """
        return True
