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
import copy

# The object returned to the caller of _watiba_ for command results
class WTOutput(Exception):
    def __init__(self):
        self.stdout = []
        self.stderr = []
        self.exit_code = 0
        self.cwd = "."

# The object returned for Watbia thread spawns
class WTPromise(Exception):
    def __init__(self):
        self.output = WTOutput()
        self.resolution = False
        self.id = time.time()
        self.children = []
        self.parent = None

    def resolved(self):
        return self.resolution

    def set_resolved(self):
        self.resolution = True

    def resolve_parent(self):
        if self.parent:
            self.parent.set_resolved()

    # Check any child promises
    def tree_resolved(self, p=None):
        p = self if not p else p
        r = p.resolved()
        for c in p.children:
            r &= self.tree_resolved(c)
        return r

    # Wait until this promise and all its children down the tree are ALL resolved
    def join(self, args={}):
        self.wait(args, self.tree_resolved)

    # Wait on just this promise
    def wait(self, args = {}, promise_function = None):
        sleep_time = int(args["sleep"]) if "sleep" in args else .5
        expiration = int(args["expire"]) * sleep_time if "expire" in args else -1
        exception_msg = args["exception_msg"] if "exception_msg" in args else "wait expired"
        func = promise_function if promise_function else self.resolved
        while not func():
            time.sleep(sleep_time)
            if expiration != -1:
                expiration -= 1
                if expiration == 0:
                    raise Exception(exception_msg)

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

    def spawn(self, command, resolver, spawn_args, parent_locals):
        # Create a new promise object
        l_promise = WTPromise()

        # Chain our promise in if we're a child
        if 'promise' in parent_locals and str(type(parent_locals['promise'])).find("WTPromise") >= 0:
            parent_locals['promise'].children.append(l_promise)
            l_promise.parent = parent_locals['promise']

        def run_command(cmd, resolver_func, resolver_promise, args):

            # Execute the command in a new thread
            resolver_promise.output = self.bash(cmd)

            # Call the resolver and use its return value for promise resolution
            # The OR is to ensure we don't override a resolved promise from a race condition!
            # once some thread marks it resolved, it's resolved.
            resolver_promise.resolution |= resolver_func(resolver_promise, copy.copy(args))
        try:
            # Create a new thread
            t = threading.Thread(target=run_command, args=(command, resolver, l_promise, spawn_args))

            # Run the command and call the resolver
            t.start()
        except:
            print("ERROR.  w_async thread execution failed. {}".format(command))

        return l_promise