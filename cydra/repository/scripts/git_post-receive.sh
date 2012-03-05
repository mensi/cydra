#!/bin/bash

exec cydra-git-post-receive {{ project.name }} {{ repository.name }}