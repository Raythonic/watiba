#!/usr/bin/python3.8
'''
Watiba class wraps the Python subprocess and captures all its outputs in a single object

Author: Ray Walker
Raythonic@gmail.com
'''

from subprocess import Popen, PIPE, STDOUT
import re
import os
import threading
import copy
import inspect
from wtpromise import WTPromise
from wtspawncontroller import WTSpawnController


# The object returned to the caller of _watiba_ for command results
class WTOutput(Exception):
    def __init__(self):
        self.stdout = []
        self.stderr = []
        self.exit_code = 0
        self.cwd = "."


###############################################################################################################
########################################## Watiba #############################################################
###############################################################################################################
# Singleton object with no side effects
# Executes the command an returns a new WTOutput object
class Watiba(Exception):

    def __init__(self):
        self.spawn_ctlr = WTSpawnController()

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

    def spawn(self, command, resolver, spawn_args, parent_locals):
        # Create a new promise object
        l_promise = WTPromise(command)

        # Chain our promise in if we're a child
        if 'promise' in parent_locals \
                and str(type(parent_locals['promise'])).find("WTPromise") >= 0 \
                and hasattr(parent_locals['promise'], "__WTPROMISE_STAMP__") \
                and hasattr(parent_locals['promise'], "resolved") \
                and inspect.ismethod(getattr(parent_locals['promise'], "resolved")):
            # Link this child promise to its parent
            l_promise.relate(parent_locals['promise'])

        def run_command(cmd, resolver_func, resolver_promise, args):

            resolver_promise.thread_id = threading.get_ident()

            # Execute the command in a new thread
            resolver_promise.output = self.bash(cmd)

            # Call the resolver and use its return value for promise resolution
            # The OR is to ensure we don't override a resolved promise from a race condition!
            # once some thread marks it resolved, it's resolved.
            resolver_promise.resolution |= resolver_func(resolver_promise, copy.copy(args))

        try:
            # Create a new thread
            l_promise.thread = threading.Thread(target=run_command, args=(command, resolver, l_promise, spawn_args))

            # Control the threads (the controller starts the thread)
            self.spawn_ctlr.add_promise(l_promise)

        except Exception(BaseException) as ex:
            print("ERROR.  w_async thread execution failed. {}".format(command))

        return l_promise
