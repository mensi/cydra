Installation
============

Cydra
--------
python setup.py install

Repositories
------------

SVN
~~~

Prerequisites
^^^^^^^^^^^^^
In order to be able to use SVN repositories, you need to have *subversion* installed. 
Exporting the repository over HTTP requires *dav_svn* and *apache*.

Configuration
^^^^^^^^^^^^^
SVN only requires a path to the directory where SVN repositories will be stored. As 
such, if you are using a configuration file, you would have something like this::

	"components": {
	    "cydra.repository.svn.SVNRepositories": {
    		"base": "/path/to/svn"
		}
	}

Make sure apache can write to this directory. 

HTTP Access
^^^^^^^^^^^
In order to export SVN over HTTP, you need to use Apache with DAV. Permission checks 
can be done with mod_wsgi.

Apache SVN configuration::

	<Location /svn>
	    DAV svn
	    SVNParentPath /path/to/svn
	
	    AuthType                Basic
	    AuthName                "Your Realm"
	    AuthBasicProvider       wsgi
	    WSGIAuthUserScript      /path/to/svn_auth.wsgi
	    WSGIAuthGroupScript     /path/to/svn_auth.wsgi
	    Require                 valid-user
	
	    <Limit GET HEAD OPTIONS CONNECT POST>
	            Require group read
	    </Limit>
	
	    <Limit GET HEAD OPTIONS CONNECT POST PROPFIND PUT DELETE \
	      PROPPATCH MKCOL COPY MOVE LOCK UNLOCK>
	            Require group write
	    </Limit>
	</Location>
	
And the corresponding svn_auth.wsgi::

	# -*- coding: utf-8 -*-
	import logging
	import logging.handlers
	
	# Log to syslog
	handler = logging.handlers.SysLogHandler(address='/dev/log', facility='daemon')
	handler.setFormatter(logging.Formatter('cydra.%(levelname)s: <%(name)s> %(message)s'))
	logging.getLogger().addHandler(handler)
	logging.getLogger().setLevel(logging.ERROR)
	
	def env_mapper(environ):
	    """Returns project, permissionobject for a given URI"""
	    parts = environ.get('REQUEST_URI', '').strip('/').split('/')
	    # REQUEST_URI contains the whole URI, eg. /svn/repos/whatnot. Retrieve the right part 
	    if parts[0] == 'svn':
	        return parts[1], 'repository.svn'
	    else:
	        return parts[0], 'repository.svn'
	
	from cydra.web.wsgihelper import WSGIAuthnzHelper
	helper = WSGIAuthnzHelper(env_mapper)
	
	# Define the functions mod_wsgi is looking for
	check_password = helper.check_password
	groups_for_user = helper.groups_for_user

Git
~~~
Prerequisites
^^^^^^^^^^^^^
In order to be able to use git repositories, you need to have *git* installed.

Configuration
^^^^^^^^^^^^^
Git only requires a path to the directory where git repositories will be stored. As 
such, if you are using a configuration file, you would have something like this::

	"components": {
	    "cydra.repository.svn.GitRepositories": {
    		"base": "/path/to/git"
		}
	}
	
HTTP Access
^^^^^^^^^^^
Codehost contains a plugin *githttp* which provides a WSGI application for read and write access over HTTP. It 
supports both the old HTTP and the newer smart HTTP.

Install the plugin with ``python setup.py install``. If you want to use *mod_wsgi*, here is an example .wsgi file::

	# -*- coding: utf-8 -*-
	import logging
	import logging.handlers
	
	# log to syslog
	handler = logging.handlers.SysLogHandler(address='/dev/log', facility='daemon')
	handler.setFormatter(logging.Formatter('cydra.%(levelname)s: <%(name)s> %(message)s'))
	logging.getLogger().addHandler(handler)
	logging.getLogger().setLevel(logging.DEBUG)
	
	from cydraplugins.githttp import create_application
	
	application = create_application()

Mercurial
~~~~~~~~~
Prerequisites
^^^^^^^^^^^^^
In order to be able to use hg repositories, you need to have *mercurial* installed.

Configuration
^^^^^^^^^^^^^
Hg only requires a path to the directory where hg repositories will be stored. As 
such, if you are using a configuration file, you would have something like this::

	"components": {
	    "cydra.repository.svn.HgRepositories": {
    		"base": "/path/to/hg"
		}
	}
	
HTTP Access
^^^^^^^^^^^
Codehost contains a plugin *hgwebdir* which provides a WSGI application for read and write access over HTTP. It 
is a wrapper for Mercurial's hgwebdir.

Install the plugin with ``python setup.py install``. If you want to use *mod_wsgi*, here is an example .wsgi file::

	# -*- coding: utf-8 -*-
	import logging
	import logging.handlers
	
	# log to syslog
	handler = logging.handlers.SysLogHandler(address='/dev/log', facility='daemon')
	handler.setFormatter(logging.Formatter('cydra.%(levelname)s: <%(name)s> %(message)s'))
	logging.getLogger().addHandler(handler)
	logging.getLogger().setLevel(logging.DEBUG)
	
	from cydraplugins.hgwebdir import HgWebDir
	
	application = HgWebDir()