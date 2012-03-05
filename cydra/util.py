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
import os, os.path

class NoopArchiver(object):
    """Noop archiver"""
    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        pass

    def add_path(self, source, filename=None):
        pass

class TarArchiver(object):
    """Context Manager for archiving files"""

    path = None
    archive_file = None

    def __init__(self, archive_file):
        self.archive_file = archive_file

        if os.path.exists(self.archive_file):
            raise ValueError("File already exists!")

    def __enter__(self):
        self.tar = tarfile.open(self.archive_file, 'w')

    def add_path(self, source, filename=None):
        """Adds a file or directory to the archive"""
        if not filename:
            os.path.join(prefix, os.path.basename(source.rstrip('/')))
        self.tar.add(source, filename)

    def __exit__(self, type, value, traceback):
        self.tar.close()


def get_collator(callable):
    """Calls the callable and iterates through the result.
    
    Every item is either a list or a scalar or None. This 
    returns a function that merges all items into one list, ignoring the Nones
    
    Example:
    Callable returns [1,[3,4],None]. Result will be [1,3,4]"""
    def func(*args, **kwargs):
        result = []
        for x in callable(*args, **kwargs):
            if isinstance(x, list):
                result.extend(x)
            elif x:
                result.append(x)
        return result

    return func

def archive_data(data_path, archive_name):
    """Interfaces with tar to archive
    
    :param data_path: Path to data to archive. Can be a file or directory
    :param archive_name: Path to archive file. Do not add a file extension since it will be different depending on method 
    :returns: True on success, False on failure"""
    import subprocess
    import os.path

    target_path = archive_name + '.tar.gz'
    if not os.path.exists(os.path.dirname(target_path)):
        logger.error('Archive target directory does not exist: %s', target_path)
        return False

    if os.path.exists(target_path):
        logger.error('Archive target file already exists: %s', target_path)
        return False

    if not os.path.exists(data_path):
        logger.error('Data path does not exist: %s', data_path)
        return False

    tarproc = subprocess.Popen(['tar', 'czf', target_path, data_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = tarproc.communicate()

    if tarproc.returncode != 0:
        logger.error('Tar failed with returncode %d: %s', tarproc.returncode, output[1])
        return False
    else:
        return True


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
        min = time.time()
        minkey = None

        for key, item in self.data.items():
            if item.last_access < min:
                min = item.last_access
                minkey = key

        if minkey is not None:
            del(self.data[minkey])
