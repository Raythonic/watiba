#!/usr/bin/python3.8
'''
Watiba class wraps the Python subprocess and captures all its outputs in a single object

Author: Ray Walker
ipyRaythonic@gmail.com
'''


from subprocess import Popen, PIPE, STDOUT
import re
import os
import threading
import time


# The object returned to the caller of _watiba_ for command results
class WTOutput(Exception):
    def __init__(self):
        self.stdout = []
        self.stderr = []
        self.exit_code = 0
        self.cwd = "."

# The object returned for Watbia thread spawns
class WTPromise(Exception):
    def __init__(self, args):
        self.output = WTOutput()
        self.args = args
        self.resolution = False

    def resolved(self):
        return self.resolution

    def set_resolved(self):
        self.resolution = True

    def join(self):
        while not self.resolution:
            time.sleep(1)

# Singleton object with no side effects
# Executes the command an returns a new WTOutput object
class Watiba(Exception):

    # cmd - command string to execute
    # context = track or not track current dir
    # Returns:
    #   WTOutput object that encapsulates stdout, stderr, exit code, etc.
    def bash(self, cmd, context=True):

        # In order to be thread-safe in the generated code, ALWAYS create a new output object for each command
        #  This is because in the generated code, the object reference, "_watiba_", is global and needs to be in scope
        #  at all levels.  The compiler cannot be scope sensitive with this reference.  Therefore, it must be
        # singleton with no side effects.
        out = WTOutput()

        # Tack on this command to see what the current dir is after the user's command is executed
        ctx = ' && echo "_watiba_cwd_($(pwd))_"' if context else ''
        p = Popen("{}{}".format(cmd, ctx),
                  shell=True,
                  stdout=PIPE,
                  stderr=PIPE,
                  close_fds=True)
        out.exit_code = p.wait()
        out.stdout = p.stdout.read().decode('utf-8').split('\n')
        out.stderr = p.stderr.read().decode('utf-8').split('\n')

        # Are we supposed to track context?  Yes, then set Python's CWD to where the command took us
        if context:
            # if asked to keep CWD context, find our echo string and remove so the
            # user doesn't see it
            for n, o in enumerate(out.stdout):
                m = re.match(r'^_watiba_cwd_\((\S.*)\)_$', o)
                if m:
                    os.chdir(m.group(1))
                    del out.stdout[n]
        out.cwd = os.getcwd()
        return out

    def spawn(self, command, resolver, spawn_args):
        def run_command(cmd, resolver):
            # Execute the command in a new thread
            self.promise.output = self.bash(cmd)

            # Call the resolver and use its return value for promise resolution
            self.promise.resolution = resolver(self.promise)
        try:
            # Create a new promise object
            self.promise = WTPromise(spawn_args)

            # Create a new thread
            t = threading.Thread(target=run_command, args=(command, resolver, ))

            # Run the command and call the resolver
            t.start()
        except:
            print("ERROR.  w_async thread execution failed. {}".format(command))

        return self.promise