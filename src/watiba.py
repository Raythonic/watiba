#!/usr/bin/python3.8
from subprocess import Popen, PIPE, STDOUT
import re
import os


class WTOutput(Exception):
    def __init__(self):
        self.stdout = []
        self.stderr = []
        self.exit_code = 0
        self.cwd = "."

    def set_stdout(self, stdout):
        self.stdout = stdout

    def set_stderr(self, stderr):
        self.stderr = stderr

    def set_exit_code(self, exit_code):
        self.exit_code = exit_code

class Watiba(Exception):
    def __init__(self):
        self.out = WTOutput()

    def set_context(self):
        for n, o in enumerate(self.out.stdout):
            m = re.match(r'^_watiba_\((\S.*)\)$', o)
            if m:
                os.chdir(m.group(1))
                self.out.cwd = os.getcwd()
                del self.out.stdout[n]

    # cmd - command string to execute
    # context = track or not track current dir
    # Returns:
    #   string array of command result
    def bash(self, cmd, context=True):
        # Tack on this command to see what the current dir is after the user's command is executed
        ctx = ' && echo "_watiba_($(pwd))"' if context else ''
        p = Popen("{}{}".format(cmd, ctx),
                  shell=True,
                  stdout=PIPE,
                  stderr=PIPE,
                  close_fds=True)
        self.out.set_exit_code(p.wait())
        self.out.set_stdout(p.stdout.read().decode('utf-8').split('\n'))
        self.out.set_stderr(p.stderr.read().decode('utf-8').split('\n'))

        # Are we supposed to track context?  Yes, then set Python's CWD to where the command took us
        if context:
            self.set_context()
        return self.out
