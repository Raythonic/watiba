'''
Watiba class wraps the Python subprocess and captures all its outputs in a single object

Author: Ray Walker
Raythonic@gmail.com
'''

from subprocess import Popen, PIPE
import re
import os
import threading
import copy
import shlex
from watiba.wtspawncontroller import WTSpawnController, WTSpawnException
from watiba.wtpromise import WTPromise
from watiba.wtoutput import WTOutput


class WTChainException(Exception):
    def __init__(self, message, host, command, output):
        self.host = host
        self.message = message
        self.command = command
        self.output = output


###############################################################################################################
########################################## Watiba #############################################################
###############################################################################################################
# Singleton object with no side effects
# Executes the command and returns a new WTOutput object
class Watiba:

    def __init__(self):
        self.spawn_ctlr = WTSpawnController()
        self.parms = {"ssh-port":22}
        self.hooks = {}
        self.hook_flags = {}
        self._hook_state = threading.local()
        self._spawn_state = threading.local()

    # Merge in Watiba parameter changes
    def set_parms(self, args):
        self.parms = {**self.parms, **args}

    # Called by spawned thread
    # Dir context is not kept by the spawn expression
    # Returns WTOutput object
    def execute(self, command, host="localhost"):
        context = False
        if host == "localhost":
            return self.bash(command, context, run_post_hooks=False)
        else:
            # A simple wrapper for self.bash()
            return self.ssh(command, host, context=False, run_post_hooks=False)

    # Run command remotely
    # Returns WTOutput object
    def ssh(self, command, host, context=True, port=None, run_post_hooks=True):
        ssh_port = port if port is not None else self.parms["ssh-port"]
        ssh_command = f"ssh -p {shlex.quote(str(ssh_port))} -- {shlex.quote(str(host))} {shlex.quote(command)}"
        return self.bash(ssh_command, context, run_post_hooks=run_post_hooks)

    # command - command string to execute
    # context - track or not track current dir
    # run_post_hooks - allows spawned threads to avoid running post-hooks
    # Returns:
    #   WTOutput object that encapsulates stdout, stderr, exit code, etc.
    def bash(self, command, context=True, run_post_hooks=True):

        # In order to be thread-safe in the generated code, ALWAYS create a new output object for each command
        #  This is because in the generated code, the object reference, "_watiba_", is global and needs to be in scope
        #  at all levels.  The compiler cannot be scope sensitive with this reference.  Therefore, it must be
        # singleton with no side effects.
        out = WTOutput()


        ##############################################################################################################
        #                                           PRE-HOOKS
        ##############################################################################################################
        # Run any command hooks defined for this command
        results = self.run_hooks(command, post_hook=False)

        # Handle any hook failures
        # All hooks are always run, but any one reporting a failure will cause the command to not be run
        if results['success'] != True:
            msg = f"One or more hooks failed. Hooks reporting a problem: {', '.join(results['failed-hooks'])}"
            out.stderr.append(msg)
            raise Exception(msg)

        ##############################################################################################################
        #                                           COMMAND
        ##############################################################################################################
        # Tack on this command to see what the current dir is after the user's command is executed
        ctx = ' && echo "__watiba_cwd__($(pwd))_"' if context else ''
        p = Popen(f"{command}{ctx}",
                  shell=True,
                  stdout=PIPE,
                  stderr=PIPE,
                  executable="/bin/bash",
                  close_fds=True)
        stdout, stderr = p.communicate()
        out.exit_code = p.returncode
        out.stdout = stdout.decode("utf-8", errors="replace").splitlines()
        out.stderr = stderr.decode("utf-8", errors="replace").splitlines()

        # Are we supposed to track context?  Yes, then set Python's CWD to where the command took us
        if context:
            # if asked to keep CWD context, find our echo string and remove so the
            # user doesn't see it
            for n, o in enumerate(out.stdout):
                m = re.match(r'^__watiba_cwd__\((\S.*)\)_$', o)
                if m:
                    os.chdir(m.group(1))
                    del out.stdout[n]
        out.cwd = os.getcwd()


        ##############################################################################################################
        #                                           POST-HOOKS
        ##############################################################################################################
        # Run any command post-hooks defined for this command
        if run_post_hooks:
            results = self.run_hooks(command, post_hook=True)

        # Handle any post-hook failures
        # All hooks are always run, but any one reporting a failure will cause the command to not be run
        if results['success'] != True:
            msg = f"One or more post-hooks failed. Hooks reporting a problem: {', '.join(results['failed-hooks'])}"
            out.stderr.append(msg)
            raise Exception(msg)

        return out

    def spawn(self, command, resolver, spawn_args, host="localhost"):
        # Create a new promise object
        l_promise = WTPromise(command, host or "localhost", copy.copy(spawn_args))

        # A spawn issued by a resolver is a child of that resolver's promise.
        parent_promise = getattr(self._spawn_state, "current_promise", None)
        if isinstance(parent_promise, WTPromise):
            l_promise.relate(parent_promise)
        

        # This is run under the new thread, and under the control of wtspawncontroller.py (i.e. spawn controller calls this function)
        def run_command(promise, thread_args):
            try:
                # Get our thread id
                promise.thread_id = threading.get_ident()

                # Execute the command in a new thread (this is synchronously run)
                promise.output = self.execute(thread_args["command"], thread_args["host"])

                # Call promise resolver
                self._spawn_state.current_promise = promise
                try:
                    resolution = thread_args["resolver"](promise, copy.copy(thread_args["spawn-args"]))
                    promise.set_resolution(resolution)
                finally:
                    self._spawn_state.current_promise = None
            except BaseException as ex:
                promise.set_exception(ex)


        # Call wtspawncontroller.py to run the command under a new thread
        try:
            thread_args = {"command": command, "resolver": resolver, "spawn-args": spawn_args, "host": host}

            # Control the threads (the controller starts the thread)
            self.spawn_ctlr.start(l_promise, run_command, thread_args)

        except WTSpawnException:
            raise

        return l_promise
    

    # Determine if the command pattern can be run at this time
    # Return the condition of the regex match() function
    def is_hook_runnable(self, hook_key, command, post_hook):
        command_regex, recursive, configured_post = hook_key

        # Avoid a loop on this command pattern
        # Note: Doesn't matter if the command matches the pattern or not.
        active_patterns = getattr(self._hook_state, "active_patterns", set())
        if not recursive and command_regex in active_patterns:
            return None
        
        # See if we're to run this hook before or after the command
        # Note: Doesn't matter if the command matches the pattern or not.
        if configured_post != post_hook:
            return None

        # Tell the caller if the command passed to us matches the regex expression
        return re.match(command_regex, command)


    # Run all the command hooks
    # If any hook returns False, meaning it somehow failed (that's determined by the hook)
    # then report it so an exception is thrown by the caller
    #
    # post_hook - False if this is called before the command, True if after
    def run_hooks(self, command, post_hook=False):

        # return_obj - object returned to caller:
        #  "success" - Aggregate True/False of all hooks.  (i.e. any hook that reports False will cause this value to return False)
        #  "failed-hooks" - Array of hook names that reported a False condition
        #       Note: all hooks are called in order even after one reports failure (i.e. reports False)
        return_obj = {"success": True, "failed-hooks": []}

        # Loop through the hooks and run them.  Also track ones that fail (i.e. report a False return code)
        for hook_key, functions in list(self.hooks.items()):
            command_regex = hook_key[0]

            # Are we allowed to run this hook for this command?
            mat = self.is_hook_runnable(hook_key, command, post_hook)

            # Does this command have attached hooks?
            if mat:
                # Yes, command has hooks.  Run them.
                # If the hook fails track it, but keep going with the other hooks
                for func, parms in functions.items():

                    # Track this pattern as an active hook
                    active_patterns = getattr(self._hook_state, "active_patterns", set())
                    self._hook_state.active_patterns = active_patterns
                    active_patterns.add(command_regex)

                    # Call the hook.  The hook must return True if succeeded, False if failed
                    try:
                        rc = func(mat, parms)
                    finally:
                        active_patterns.discard(command_regex)

                    # If caller's hook didn't return a bool value, then it is marked as failed
                    rc = False if type(rc) != bool else rc

                    # Track failed hooks
                    if rc == False:
                        return_obj["failed-hooks"].append(func.__name__)
                
                    return_obj["success"] &= rc
        
        return return_obj

    # Pipe either stdout or stderr to some target host with some target command
    def pipe(self, pipe_source, pipe_target):
        # Pipe output to target host command
        for pipe_to, command in pipe_target.items():
            for line in pipe_source:
                # The output for piped command is not kept, but is checked for the exit code
                out = self.ssh(f"printf '%s\\n' {shlex.quote(line)} | {command}", pipe_to)
                if out.exit_code != 0:
                    raise WTChainException(f'Piped command failed on {pipe_to}.  Error code: {out.exit_code}', pipe_to,
                                           command, out)

    # chain commands across various servers.  (Run sequentially and with regard to exit code.  A bad exit code causes
    # an exception to be thrown.
    #  A dictionary structure must be passed by the user's program as follows:
    #       {"hosts": ["host1", "host2", ...],  # These are the hosts to run the command on and is required
    #        "stdout": {"source-host": {"target-host1":command, "target-host2":command, ...}}, # Pipe stdout from source to target(s) (optional)
    #        "stderr": {"source-host": {"target-host1":command, "target-host2":command, ...}}   # Pipe stderr from source to target(s) (optional)
    #       }
    # Returns dictionary of WTOutput objects by host name: {host:WTOutput, ...}
    def chain(self, command, parms):
        output = {}
        if "hosts" not in parms:
            raise WTChainException("No hosts in argument dict", "none", command, None)

        pipe_stdout = parms["stdout"] if "stdout" in parms else {}
        pipe_stderr = parms["stderr"] if "stderr" in parms else {}

        # Loop through each host and run the command on it
        for host in parms["hosts"]:
            # Run command remotely through SSH
            output[host] = self.ssh(command, host)

            # If the command fails, bomb the whole execution
            if output[host].exit_code != 0:
                raise WTChainException(f'Command failed on {host}. Error code: {output[host].exit_code}', host, command,
                                       output[host])

            # If we are supposed to pipe the stdout for this host, do it
            if host in pipe_stdout:
                self.pipe(output[host].stdout, pipe_stdout[host])

            # If we are supposed to pipe the stderr for this host, do it
            if host in pipe_stderr:
                self.pipe(output[host].stderr, pipe_stderr[host])

        return output


    # Add a new hook.  If command pattern already exists, add the functions to it otherwise create a new pattern level.
    #  Set recursive to True to keep hook from looping because it has a matching command within it
    def add_hook(self, pattern, function, parms, recursive=True, post=False):
        hook_key = (pattern, bool(recursive), bool(post))
        self.hooks.setdefault(hook_key, {})[function] = parms
        self.hook_flags[hook_key] = {"recursive": bool(recursive), "post": bool(post)}

    
    # Remove a specific hook, keyed by pattern, or all hooks if no pattern is passed
    def remove_hooks(self, pattern = None):

        # No pattern passed, so nuke it all!
        if not pattern:
            self.hooks = {}
            self.hook_flags = {}
            return

        # Remove the hook for only the pattern passed
        for hook_key in [key for key in self.hooks if key[0] == pattern]:
            del self.hooks[hook_key]
            self.hook_flags.pop(hook_key, None)
