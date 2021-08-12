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
class Watiba(Exception):

    def __init__(self):
        self.spawn_ctlr = WTSpawnController()
        self.parms = {"ssh-port":22}
        self.hooks = {}
        self.hook_flags = {}
        self.hook_mode = False

    def set_parms(self, args):
        for k,v in args.items():
            self.parms[k] = v

    # Called by spawned thread
    # Dir context is not kept by the spawn expression
    # Returns WTOutput object
    def execute(self, command, host="localhost"):
        context = False
        if host == "localhost":
            return self.bash(command, context)
        else:
            # A simple wrapper for self.bash()
            return self.ssh(command, host)

    # Run command remotely
    # Returns WTOutput object
    def ssh(self, command, host, context=True):
        return self.bash(f'ssh -p {self.parms["ssh-port"]} {host} "{command}"', context)

    # command - command string to execute
    # context = track or not track current dir
    # Returns:
    #   WTOutput object that encapsulates stdout, stderr, exit code, etc.
    def bash(self, command, context=True):

        # In order to be thread-safe in the generated code, ALWAYS create a new output object for each command
        #  This is because in the generated code, the object reference, "_watiba_", is global and needs to be in scope
        #  at all levels.  The compiler cannot be scope sensitive with this reference.  Therefore, it must be
        # singleton with no side effects.
        out = WTOutput()

        # Run any command hooks defined for this command
        results = self.run_hooks(command)

        # Handle any hook failures
        # All hooks are always run, but any one reporting a failure will cause the command to not be run
        if results['success'] != True:
            msg = f"One or more hooks failed. Hooks reporting a problem: {', '.join(results['failed-hooks'])}"
            out.stderr.append(msg)
            raise Exception(msg)

        # Tack on this command to see what the current dir is after the user's command is executed
        ctx = ' && echo "_watiba_cwd_($(pwd))_"' if context else ''
        p = Popen(f"{command}{ctx}",
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

    def spawn(self, command, resolver, spawn_args, parent_locals, host="localhost"):
        # Create a new promise object
        l_promise = WTPromise(command, host) if host else WTPromise(command)

        # Chain our promise in if we're a child
        if 'promise' in parent_locals \
                and str(type(parent_locals['promise'])).find("WTPromise") >= 0 \
                and hasattr(parent_locals['promise'], "__WTPROMISE_STAMP__") \
                and hasattr(parent_locals['promise'], "resolved") \
                and inspect.ismethod(getattr(parent_locals['promise'], "resolved")):
            # Link this child promise to its parent
            l_promise.relate(parent_locals['promise'])
        

        # This is run under the new thread, and under the control of wtspawncontroller.py (i.e. spawn controller calls this function)
        def run_command(promise, thread_args):
            # Get our thread id
            promise.thread_id = threading.get_ident()

            # Execute the command in a new thread (this is synchronously run)
            promise.output = self.execute(thread_args["command"], thread_args["host"])

            # Call promise resolver
            promise.set_resolution(thread_args["resolver"](promise, copy.copy(thread_args["spawn-args"])))


        # Call wtspawncontroller.py to run the command under a new thread
        try:
            thread_args = {"command": command, "resolver": resolver, "spawn-args": spawn_args, "host": host}

            # Control the threads (the controller starts the thread)
            self.spawn_ctlr.start(l_promise, run_command, thread_args)

        except WTSpawnException as ex:
            print(f"ERROR.  w_async thread execution failed. {ex.promise.command}")

        return l_promise
    
    # Run all the command pre-execution hooks
    # If any hooks returns False, meaning it somehow failed (that's determined by the hook)
    # then report so an exception is thrown by the caller
    def run_hooks(self, command):

        # object returned to caller:
        #  "success" - Aggregate True/False of all hooks.  (i.e. any hook that reports False will cause this value to return False)
        #  "failed-hooks" - Array of hook names that reported a False condition
        #       Note: all hooks are called in order even after one reports failure (i.e. reports False)
        return_obj = {"success": True, "failed-hooks": []}

        # Loop through the hooks and run them.  Also track ones that fail (i.e. report a False return code)
        for command_regex, functions in self.hooks.items():

            # Avoid a loop on this command pattern
            if self.hook_flags[command_regex]["recursive"] == False and self.hook_mode == True:
                continue

            # Check if the command passed to us matches the regex expression
            mat = re.match(command_regex, command)

            # Does this command have attached hooks?
            if mat:

                # Yes, command has hooks.  Run them.
                # If the hook fails track it, but keep going with the other hooks
                for func, parms in functions.items():

                    # Indicate we're in a hook
                    self.hook_mode = True

                    # Call the hook.  The hook must return True if succeeded, False if failed
                    rc = func(mat, parms)

                    # Indicate we're no longer in a hook
                    self.hook_mode = False

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
                out = self.ssh(f'echo "{line}" | {command}', pipe_to)
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
                self.pipe(output[host].stdout, pipe_stdout)

            # If we are supposed to pipe the stderr for this host, do it
            if host in pipe_stderr:
                self.pipe(output[host].stderr, pipe_stderr)

        return output


    # Add a new hook.  If command pattern already exists, add the functions to it otherwise create a new pattern level.
    #  Set recursive to True to keep hook from looping because it has a matching command within it
    def add_hook(self, pattern, function, parms, recursive = True):

        defined_pattern = pattern in self.hooks
        defined_function = function in self.hooks[pattern] if defined_pattern else False

        # If the command pattern and hook function are new, then add them
        if defined_pattern and not defined_function:
            self.hooks[pattern].update({function: parms})
            return
        
        # If the command pattern already has this hook function 
        # defined, just update the parms for the hook function
        #  Note: defined_function cannot be True if defined_pattern is false
        if defined_function:
            self.hooks[pattern][function] = parms
            return
        
        # At this point we know the pattern has not been defined yet, so define it
        self.hooks.update({pattern : {function: parms}})
        self.hook_flags[pattern] = {"recursive": recursive}

    
    # Remove a specific hook, keyed by pattern, or all hooks if no pattern is passed
    def remove_hooks(self, pattern = None):
        if not pattern:
            self.hooks = {}
            self.hook_flags = {}
            return

        if pattern in self.hooks:
            del self.hooks[pattern]
            del self.hook_flags[pattern]
            return
        