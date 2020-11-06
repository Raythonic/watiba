#!/usr/bin/python3.8
import subprocess
import re
import os


class Watiba(Exception):
    def __init__(self):
        self.out = []

    def set_context(self):
        for n,o in enumerate(self.out):
            m = re.match(r'^_watiba_\((\S.*)\)$', o)
            if m:
                os.chdir(m.group(1))
                del self.out[n]


    def getcwd(self):
        return os.getcwd()

    # cmd - command string to execute
    # context = track or not track current dir
    # Returns:
    #   string array of command result
    def bash(self, cmd, context=True):
        # Tack on this command to see what the current dir is after the user's command is executed
        ctx = ' && echo "_watiba_($(pwd))"' if context else ''
        self.out = subprocess.check_output("{}{}".format(cmd, ctx), shell=True).decode('utf-8').split('\n')

        # Are we supposed to track context?  Yes, then set Python's CWD to where the command took us
        if context:
            self.set_context()
        return self.out