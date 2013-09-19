# -*- coding: utf-8 -*-
from __future__ import absolute_import
import subprocess
import threading
import sys
import unittest


class MonitoredDaemon(object):
    name = ""

    stdout = ""
    stderr = ""

    stdout_limit = None
    stderr_limit = None

    stdout_thread = None
    stderr_thread = None

    stdout_encountered = None
    stderr_encountered = None
    read_size = 4096
    process = None

    def __init__(self, args, stdout_limit=None, stderr_limit=None, name=None,
                 wait_for_stdout=None, wait_for_stdout_timeout=10,
                 wait_for_stderr=None, wait_for_stderr_timeout=10):
        """Spawn an monitor a daemon process"""

        self.name = name if name is not None else args[0]
        self.stdout_limit = stdout_limit
        self.stderr_limit = stderr_limit

        self.process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.stdout_encountered = threading.Event()
        self.stderr_encountered = threading.Event()

        self.stdout_thread = threading.Thread(target=self.read_stdout, kwargs={
            'wait_for_stdout': wait_for_stdout
        })
        self.stderr_thread = threading.Thread(target=self.read_stderr, kwargs={
            'wait_for_stderr': wait_for_stderr
        })

        self.stdout_thread.start()
        self.stderr_thread.start()

        if wait_for_stdout is not None:
            self.stdout_encountered.wait(wait_for_stdout_timeout)

        if wait_for_stderr is not None:
            self.stderr_encountered.wait(wait_for_stderr_timeout)

    def read_stdout(self, wait_for_stdout=None):
        for line in iter(self.process.stdout.readline, b''):
            sys.stdout.write("[D: " + self.name + "] " + line)
            self.stdout += line
            if wait_for_stdout is not None and wait_for_stdout in self.stdout:
                self.stdout_encountered.set()

            if self.stdout_limit is not None and len(self.stdout) > self.stdout_limit:
                self.stdout = self.stdout[-self.stdout_limit:]

    def read_stderr(self, wait_for_stderr=None):
        for line in iter(self.process.stderr.readline, b''):
            sys.stderr.write("[D: " + self.name + "] " + line)
            self.stderr += line
            if wait_for_stderr is not None and wait_for_stderr in self.stderr:
                self.stderr_encountered.set()

            if self.stderr_limit is not None and len(self.stderr) > self.stderr_limit:
                self.stderr = self.stderr[-self.stderr_limit:]

class ProcessHelpers(unittest.TestCase):

    def runShellCmd(self, args):
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = proc.communicate(input)
        retcode = proc.returncode
        return retcode, stdout, stderr

    def assertShellCmdReturnCode(self, args, code, msg=None):
        retcode, stdout, stderr = self.runShellCmd(args)

        if retcode != code:
            sys.stdout.write(stdout)
            sys.stderr.write(stderr)

        self.assertEqual(retcode, code, msg)
