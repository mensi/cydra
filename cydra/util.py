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
import time
import tarfile
import os.path


class NoopArchiver(object):
    """Noop archiver"""
    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        pass

    def add_path(self, source, filename=None):
        pass

    def dump_as_file(self, data, filename):
        pass


class TarArchiver(object):
    """Context Manager for archiving files"""

    path = None
    archive_file = None
    tar = None
    entries = 0

    def __init__(self, archive_file):
        self.archive_file = archive_file

        if os.path.exists(self.archive_file):
            raise ValueError("File already exists!")

    def __enter__(self):
        if self.entries == 0:
            self.tar = tarfile.open(self.archive_file, 'w')
        self.entries += 1

    def add_path(self, source, filename=None):
        """Adds a file or directory to the archive"""
        if not filename:
            os.path.basename(source.rstrip('/'))
        self.tar.add(source, filename)

    def dump_as_file(self, data, filename):
        import yaml
        from tempfile import mkdtemp

        tempdir = mkdtemp()
        tmpfile = os.path.join(tempdir, os.path.basename(filename))
        with open(tmpfile, "w") as f:
            yaml.safe_dump(data, f)

        self.add_path(tmpfile, filename)
        os.remove(tmpfile)
        os.rmdir(tempdir)

    def __exit__(self, type, value, traceback):
        self.entries -= 1
        if self.entries == 0:
            self.tar.close()


def get_collator(target_callable):
    """Calls the callable and iterates through the result.

    Every item is either a list or a scalar or None. This
    returns a function that merges all items into one list, ignoring the Nones

    Example:
    Callable returns [1,[3,4],None]. Result will be [1,3,4]"""
    def func(*args, **kwargs):
        result = []
        for x in target_callable(*args, **kwargs):
            if isinstance(x, list):
                result.extend(x)
            elif x:
                result.append(x)
        return result

    return func


class SimpleCacheItem(object):
    """Represents an item in the SimpleCache"""
    def __init__(self, value):
        self._value = value

        self.creation = time.time()
        self.last_access = time.time()

    @property
    def value(self):
        self.last_access = time.time()
        return self._value


class SimpleCache(object):
    """A simple in-memory cache

    This class does not do any locking. This means that keys should map to
    relatively stable, immutable values"""
    def __init__(self, lifetime=30, killtime=None, maxsize=100):
        self.data = {}
        self.lifetime = lifetime
        self.maxsize = maxsize

        if killtime is None:
            self.killtime = lifetime * 10
        else:
            self.killtime = killtime

    def set(self, key, value):
        self.data[key] = SimpleCacheItem(value)

        if len(self.data) > self.maxsize:
            self._remove_oldest()

    def cached(self, key, func):
        self._remove_old()
        if key in self.data:
            return self.data[key].value
        else:
            res = func()
            self.set(key, res)
            return res

    def get(self, key, default=None):
        self._remove_old()
        item = self.data.get(key)
        if item is not None:
            return item.value
        else:
            return default

    def __contains__(self, key):
        self._remove_old()
        return key in self.data

    def _remove_old(self):
        t = time.time()

        for key, item in self.data.items():
            if t - item.creation > self.killtime or t - item.last_access > self.lifetime:
                del(self.data[key])

    def _remove_oldest(self):
        mintime = time.time()
        minkey = None

        for key, item in self.data.items():
            if item.last_access < mintime:
                mintime = item.last_access
                minkey = key

        if minkey is not None:
            del(self.data[minkey])
