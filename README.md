Cydra
=====

Cydra is a platform for project hosting written in Python. It has an 
extensible architecture to facilitate integration of 3rd party software 
such as version control systems and project management tools.

Cydra is ideal for organizations wishing to provide code hosting facilities 
for their users. Projects and repositories can be created via the built-in 
web interface.

Features
========

Cydra provides the glue code to integrate authentication/authorization with 
version control systems and 3rd party tools. Builtin or plugin support exists for:

 *  **Project meta-data storage**: mongoDB, yaml files
 *  **Version Control**: git, svn, hg
 *  **Project Management**: trac
 *  **Authorization**: internal, permission can be set via web interface
 *  **Authentication**: htpasswd, ldap/AD
 *  **VCS Viewers**: hgwebdir, apache-dav-svn
 *  **VCS Access**: gitserverglue (ssh/http/git protocols)
 
Stability/Roadmap
=================

Right now, Cydra is being used in two productional deployments, one of which 
hosts ~2500 projects. Still, at least some refactoring will have to be done 
on the way to a 1.0 release and inputs/ideas/code contributions are welcome.

License
=======

The code is licensed under GPLv3. If this should be a problem for your use-case 
or preventing you from contributing code, feel to open an issue with your license 
concerns. Since the code is currently written by a single author, relicensing
is not an issue should there be valid concerns.
