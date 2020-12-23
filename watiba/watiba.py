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
from watiba.wtspawncontroller import WTSpawnController, WTSpawnException
from watiba.wtpromise import WTPromise
from watiba.wtoutput import WTOutput


###############################################################################################################
########################################## Watiba #############################################################
###############################################################################################################
# Singleton object with no side effects
# Executes the command an returns a new WTOutput object
class Watiba(Exception):

    def __init__(self):
        self.spawn_ctlr = WTSpawnController()

    # Called by spawned thread
    # Dir context is not kept by the spawn expression
    # Returns WTOutput object
    def execute(self, cmd, host):
        context = False
        if host == "localhost":
            return self.bash(cmd, context)
        else:
            return self.ssh(cmd, host)

    # Run command remotely
    # Returns WTOutput object
    def ssh(self, cmd, host, context=True):
        return self.bash(f'ssh {host} "{cmd}"', context)

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
        p = Popen(f"{cmd}{ctx}",
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

        def run_command(promise, temp_id, thread_args):
            # Since we cannot know our thread id until running in the thread, this pattern was adopted
            #  Replace our temporary location in the thread dictionary with the one we want: by thread id
            promise.reattach(temp_id, threading.get_ident())

            # Execute the command in a new thread
            promise.output[thread_args["host"]] = self.execute(thread_args["command"], thread_args["host"])

            # This thread complete.  Detach it from the promise
            promise.detach(threading.get_ident())

            # Are we the last thread to finish for this promise?  Yes-call resolver
            if len(promise.threads) < 1:
                # Call the resolver and use its return value for promise resolution
                promise.set_resolution(thread_args["resolver"](thread_args["promise"], copy.copy(thread_args["spawn-args"])))

        try:
            args = {"command":command, "resolver":resolver, "spawn-args": spawn_args}

            # Control the threads (the controller starts the thread)
            self.spawn_ctlr.start(l_promise, run_command, args)

        except WTSpawnException as ex:
            print(f"ERROR.  w_async thread execution failed. {ex.promise.command}")

        return l_promise
