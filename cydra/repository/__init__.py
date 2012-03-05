# -*- coding: utf-8 -*-
import os, os.path, shutil
import uuid
from cydra.component import Interface, ExtensionPoint, BroadcastAttributeProxy

import logging
logger = logging.getLogger(__name__)

class IRepository(Interface):

    _iface_attribute_proxy = BroadcastAttributeProxy()

    repository_type = ''
    repository_type_title = ''

    def get_repositories(self, project):
        """Get a list of repository objects for this project"""
        pass

    def get_repository(self, project, repository_name):
        """Get a repository object"""
        pass

    def can_create(self, project, user=None):
        """Can the given user create repositories"""
        pass

    def create_repository(self, project, repository_name):
        """Create repository"""
        pass

    def get_params(self):
        """Return the list of parameters for this repository type
        
        :return: list of RepositoryParameter instances  
        """
        pass

class ISyncParticipant(Interface):
    """Interface for components wishing to perform actions upon synchronisation"""

    _iface_attribute_proxy = BroadcastAttributeProxy()

    def sync_repository(self, repository):
        """Synchronise repository"""
        pass

class IRepositoryObserver(Interface):
    """Events on repository modifications"""

    _iface_attribute_proxy = BroadcastAttributeProxy()

    def repository_post_commit(self, repository, revisions):
        """One or more commits have occured
        
        :param repository: The repository object
        :param revisions: A list of revision strings"""
        pass

    def pre_delete_repository(self, repository):
        """Gets called before a repository is deleted"""
        pass

    def post_delete_repository(self, repository):
        """Gets called after a repository has been deleted"""
        pass

class RepositoryParameter(object):
    def __init__(self, keyword, name, optional=True, description=""):
        self.keyword = keyword
        self.name = name
        self.optional = optional
        self.description = description

    def validate(self, value):
        return True

class Repository(object):
    """Repository base"""

    path = None
    """Absolute path of the repository"""

    type = None
    """Type of the repository (string)"""

    project = None
    """Project this repository belongs to"""

    sync_participants = ExtensionPoint(ISyncParticipant)
    repository_observers = ExtensionPoint(IRepositoryObserver)

    def __init__(self, compmgr):
        """Construct a repository instance
        
        :param compmgr: Component manager (i.e. cydra instance)"""
        self.compmgr = compmgr

    def sync(self):
        """Synchronize repository with data stored in project and do maintenance work
        
        A repository should make sure post-commit hooks are registered and may collect statistics"""

        self.sync_participants.sync_repository(self)

    def delete(self, archiver=None):
        """Delete the repository"""
        if not archiver:
            archiver = self.project.get_archiver('repository_' + self.type + '_' + self.name)

        self.repository_observers.pre_delete_repository(self)

        tmppath = os.path.join(os.path.dirname(self.path), uuid.uuid1().hex)
        os.rename(self.path, tmppath) # POSIX guarantees this to be atomic.

        with archiver:
            archiver.add_path(tmppath, os.path.join('repository', self.type, os.path.basename(self.path.rstrip('/'))))

        logger.info("Deleted repository %s of type %s: %s", self.name, self.type, tmppath)

        shutil.rmtree(tmppath)

        self.repository_observers.post_delete_repository(self)

    def notify_post_commit(self, revisions):
        """A commit has occured. Notify observers"""
        self.repository_observers.repository_post_commit(self, revisions)

    #
    # Permission checks
    # Also provide sensible defaults
    #
    def can_delete(self, user):
        return self.project.get_permission(user, 'repository.' + self.type + '.' + self.name, 'admin')

    def can_modify_params(self, user):
        return self.project.get_permission(user, 'repository.' + self.type + '.' + self.name, 'admin')

    def can_read(self, user):
        return self.project.get_permission(user, 'repository.' + self.type + '.' + self.name, 'read')

    def can_write(self, user):
        return self.project.get_permission(user, 'repository.' + self.type + '.' + self.name, 'write')
