'''
Watiba class wraps the Python subprocess and captures all its outputs in a single object

Author: Ray Walker
Raythonic@gmail.com
'''

from subprocess import Popen, PIPE
from contextvars import ContextVar
from dataclasses import dataclass, field
import re
import os
import threading
import copy
import shlex
import uuid
from typing import Any, Callable, Dict, Iterable, List, Match, Optional
from watiba.wtspawncontroller import WTSpawnController, WTSpawnException
from watiba.wtpromise import WTPromise
from watiba.wtoutput import WTOutput


HookCallable = Callable[[Match[str], Any], bool]


@dataclass(frozen=True)
class HookKey:
    pattern: str
    recursive: bool
    post: bool


@dataclass
class HookFailure:
    pattern: str
    function: HookCallable

    @property
    def function_name(self) -> str:
        return getattr(self.function, "__name__", repr(self.function))


@dataclass
class HookResult:
    failures: List[HookFailure] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return not self.failures


class WTChainException(Exception):
    def __init__(
        self, message: str, host: str, command: str, output: Optional[WTOutput]
    ) -> None:
        super().__init__(message)
        self.host = host
        self.message = message
        self.command = command
        self.output = output


class WTHookException(Exception):
    def __init__(
        self,
        message: str,
        command: str,
        phase: str,
        pattern: Optional[str] = None,
        function: Optional[Callable[..., Any]] = None,
        original_exception: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.command = command
        self.phase = phase
        self.pattern = pattern
        self.function = function
        self.original_exception = original_exception


###############################################################################################################
########################################## Watiba #############################################################
###############################################################################################################
# Singleton object with no side effects
# Executes the command and returns a new WTOutput object
class Watiba:

    def __init__(self) -> None:
        self.spawn_ctlr = WTSpawnController()
        self.parms: Dict[str, Any] = {"ssh-port": 22}
        self.hooks: Dict[HookKey, Dict[HookCallable, Any]] = {}
        self._hook_state = threading.local()
        self._spawn_state = threading.local()
        self._local_cwd: ContextVar[str] = ContextVar(
            f"watiba_local_cwd_{id(self)}", default=os.getcwd()
        )
        self._remote_cwds: ContextVar[Optional[Dict[str, str]]] = ContextVar(
            f"watiba_remote_cwds_{id(self)}", default=None
        )

    # Merge in Watiba parameter changes
    def set_parms(self, args: Dict[str, Any]) -> None:
        self.parms = {**self.parms, **args}

    # Called by spawned thread
    # Dir context is not kept by the spawn expression
    # Returns WTOutput object
    def execute(self, command: str, host: str = "localhost") -> WTOutput:
        context = False
        if host == "localhost":
            return self.bash(command, context, run_post_hooks=False)
        else:
            # A simple wrapper for self.bash()
            return self.ssh(command, host, context=False, run_post_hooks=False)

    # Run command remotely
    # Returns WTOutput object
    def ssh(
        self,
        command: str,
        host: str,
        context: bool = True,
        port: Optional[int] = None,
        run_post_hooks: bool = True,
        stdin_text: Optional[str] = None,
    ) -> WTOutput:
        out = WTOutput()
        pre_hook_results = self.run_hooks(command, post_hook=False)
        self._raise_hook_failures(command, "pre", pre_hook_results, out)

        ssh_port = port if port is not None else self.parms["ssh-port"]
        remote_cwds = self._remote_cwds.get() or {}
        known_remote_cwd = remote_cwds.get(host)
        cwd_prefix = f"cd -- {shlex.quote(known_remote_cwd)} && " if known_remote_cwd else ""
        marker = self._cwd_marker()
        remote_command = self._command_with_cwd_capture(f"{cwd_prefix}{command}", marker)
        ssh_command = (
            f"ssh -p {shlex.quote(str(ssh_port))} -- "
            f"{shlex.quote(str(host))} {shlex.quote(remote_command)}"
        )
        out = self.bash(
            ssh_command,
            context=False,
            run_pre_hooks=False,
            run_post_hooks=False,
            stdin_text=stdin_text,
        )
        remote_cwd = self._extract_cwd(out, marker, known_remote_cwd or ".")
        out.cwd = remote_cwd
        if context:
            updated_remote_cwds = dict(remote_cwds)
            updated_remote_cwds[host] = remote_cwd
            self._remote_cwds.set(updated_remote_cwds)

        if run_post_hooks:
            post_hook_results = self.run_hooks(command, post_hook=True)
            self._raise_hook_failures(command, "post", post_hook_results, out)
        return out

    # command - command string to execute
    # context - track or not track current dir
    # run_post_hooks - allows spawned threads to avoid running post-hooks
    # Returns:
    #   WTOutput object that encapsulates stdout, stderr, exit code, etc.
    def bash(
        self,
        command: str,
        context: bool = True,
        run_post_hooks: bool = True,
        run_pre_hooks: bool = True,
        stdin_text: Optional[str] = None,
    ) -> WTOutput:

        # In order to be thread-safe in the generated code, ALWAYS create a new output object for each command
        #  This is because in the generated code, the object reference, "_watiba_", is global and needs to be in scope
        #  at all levels.  The compiler cannot be scope sensitive with this reference.  Therefore, it must be
        # singleton with no side effects.
        out = WTOutput()


        ##############################################################################################################
        #                                           PRE-HOOKS
        ##############################################################################################################
        if run_pre_hooks:
            pre_hook_results = self.run_hooks(command, post_hook=False)
            self._raise_hook_failures(command, "pre", pre_hook_results, out)

        ##############################################################################################################
        #                                           COMMAND
        ##############################################################################################################
        logical_cwd = self._local_cwd.get()
        marker = self._cwd_marker() if context else None
        shell_command = self._command_with_cwd_capture(command, marker) if marker else command
        p = Popen(shell_command,
                  shell=True,
                  cwd=logical_cwd,
                  stdin=PIPE if stdin_text is not None else None,
                  stdout=PIPE,
                  stderr=PIPE,
                  executable="/bin/bash",
                  close_fds=True)
        stdin_bytes = stdin_text.encode("utf-8") if stdin_text is not None else None
        stdout, stderr = p.communicate(input=stdin_bytes)
        out.exit_code = p.returncode
        out.stdout = stdout.decode("utf-8", errors="replace").splitlines()
        out.stderr = stderr.decode("utf-8", errors="replace").splitlines()

        out.cwd = self._extract_cwd(out, marker, logical_cwd) if marker else logical_cwd
        if context:
            self._local_cwd.set(out.cwd)


        ##############################################################################################################
        #                                           POST-HOOKS
        ##############################################################################################################
        # Run any command post-hooks defined for this command
        if run_post_hooks:
            post_hook_results = self.run_hooks(command, post_hook=True)
            self._raise_hook_failures(command, "post", post_hook_results, out)

        return out

    @staticmethod
    def _cwd_marker() -> str:
        return f"__watiba_cwd_{uuid.uuid4().hex}__"

    @staticmethod
    def _command_with_cwd_capture(command: str, marker: str) -> str:
        return (
            f"{command}; __watiba_rc=$?; "
            f"printf '\\0{marker}%s\\0' \"$PWD\"; exit $__watiba_rc"
        )

    @staticmethod
    def _extract_cwd(out: WTOutput, marker: Optional[str], fallback: str) -> str:
        if marker:
            for index in range(len(out.stdout) - 1, -1, -1):
                line = out.stdout[index]
                marker_start = line.find(f"\0{marker}")
                if marker_start >= 0:
                    cwd_start = marker_start + len(marker) + 1
                    cwd_end = line.find("\0", cwd_start)
                    cwd_end = len(line) if cwd_end < 0 else cwd_end
                    cwd = line[cwd_start:cwd_end] or fallback
                    remaining = line[:marker_start] + line[cwd_end + 1:]
                    if remaining:
                        out.stdout[index] = remaining
                    else:
                        del out.stdout[index]
                    return cwd
        return fallback

    @staticmethod
    def _raise_hook_failures(command: str, phase: str, hook_results: HookResult, out: WTOutput) -> None:
        if hook_results.success:
            return
        failed_hooks = ", ".join(failure.function_name for failure in hook_results.failures)
        message = f"One or more {phase}-hooks failed for `{command}`: {failed_hooks}"
        out.stderr.append(message)
        first_failure = hook_results.failures[0]
        raise WTHookException(
            message,
            command,
            phase,
            pattern=first_failure.pattern,
            function=first_failure.function,
        )

    def spawn(
        self,
        command: str,
        resolver: Callable[[WTPromise, Any], bool],
        spawn_args: Any,
        host: str = "localhost",
    ) -> WTPromise:
        # Create a new promise object
        l_promise = WTPromise(command, host or "localhost", copy.copy(spawn_args))

        # A spawn issued by a resolver is a child of that resolver's promise.
        parent_promise = getattr(self._spawn_state, "current_promise", None)
        if isinstance(parent_promise, WTPromise):
            l_promise.relate(parent_promise)
        

        execution_cwd = self._local_cwd.get()
        remote_cwds = dict(self._remote_cwds.get() or {})

        # This is run under the new thread, and under the control of wtspawncontroller.py (i.e. spawn controller calls this function)
        def run_command(promise: WTPromise, thread_args: Dict[str, Any]) -> None:
            cwd_token = self._local_cwd.set(thread_args["cwd"])
            remote_cwds_token = self._remote_cwds.set(dict(thread_args["remote-cwds"]))
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
            finally:
                self._remote_cwds.reset(remote_cwds_token)
                self._local_cwd.reset(cwd_token)


        # Call wtspawncontroller.py to run the command under a new thread
        try:
            thread_args = {
                "command": command,
                "resolver": resolver,
                "spawn-args": spawn_args,
                "host": host,
                "cwd": execution_cwd,
                "remote-cwds": remote_cwds,
            }

            # Control the threads (the controller starts the thread)
            self.spawn_ctlr.start(l_promise, run_command, thread_args)

        except WTSpawnException:
            raise

        return l_promise
    

    # Determine if the command pattern can be run at this time
    # Return the condition of the regex match() function
    def is_hook_runnable(
        self, hook_key: HookKey, command: str, post_hook: bool
    ) -> Optional[Match[str]]:
        command_regex = hook_key.pattern

        # Avoid a loop on this command pattern
        # Note: Doesn't matter if the command matches the pattern or not.
        active_patterns = getattr(self._hook_state, "active_patterns", set())
        if not hook_key.recursive and command_regex in active_patterns:
            return None
        
        # See if we're to run this hook before or after the command
        # Note: Doesn't matter if the command matches the pattern or not.
        if hook_key.post != post_hook:
            return None

        # Tell the caller if the command passed to us matches the regex expression
        return re.match(command_regex, command)


    # Run all the command hooks
    # If any hook returns False, meaning it somehow failed (that's determined by the hook)
    # then report it so an exception is thrown by the caller
    #
    # post_hook - False if this is called before the command, True if after
    def run_hooks(self, command: str, post_hook: bool = False) -> HookResult:

        # Every matching hook is called even after another hook returns False.
        result = HookResult()

        # Loop through the hooks and run them.  Also track ones that fail (i.e. report a False return code)
        for hook_key, functions in list(self.hooks.items()):
            command_regex = hook_key.pattern

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
                    except Exception as ex:
                        phase = "post" if post_hook else "pre"
                        function_name = getattr(func, "__name__", repr(func))
                        message = (
                            f"{phase}-hook `{function_name}` raised while processing "
                            f"`{command}` for pattern `{command_regex}`: {ex}"
                        )
                        raise WTHookException(
                            message,
                            command,
                            phase,
                            pattern=command_regex,
                            function=func,
                            original_exception=ex,
                        ) from ex
                    finally:
                        active_patterns.discard(command_regex)

                    # If caller's hook didn't return a bool value, then it is marked as failed
                    rc = False if type(rc) != bool else rc

                    # Track failed hooks
                    if rc == False:
                        result.failures.append(HookFailure(command_regex, func))
        
        return result

    # Pipe either stdout or stderr to some target host with some target command
    def pipe(self, pipe_source: Iterable[str], pipe_target: Dict[str, str]) -> None:
        # Send the complete source stream through one remote process per target.
        source_lines = list(pipe_source)
        stdin_text = "\n".join(source_lines)
        if source_lines:
            stdin_text += "\n"
        for pipe_to, command in pipe_target.items():
            out = self.ssh(command, pipe_to, context=False, stdin_text=stdin_text)
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
    def chain(self, command: str, parms: Dict[str, Any]) -> Dict[str, WTOutput]:
        output: Dict[str, WTOutput] = {}
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


    # Add a hook for a command pattern and phase.
    # recursive=False prevents the same pattern from being re-entered by commands issued inside its hook.
    def add_hook(
        self,
        pattern: str,
        function: HookCallable,
        parms: Any,
        recursive: bool = True,
        post: bool = False,
    ) -> None:
        hook_key = HookKey(pattern, bool(recursive), bool(post))
        self.hooks.setdefault(hook_key, {})[function] = parms

    
    # Remove a specific hook, keyed by pattern, or all hooks if no pattern is passed
    def remove_hooks(self, pattern: Optional[str] = None) -> None:

        # No pattern passed, so nuke it all!
        if not pattern:
            self.hooks = {}
            return

        # Remove the hook for only the pattern passed
        for hook_key in [key for key in self.hooks if key.pattern == pattern]:
            del self.hooks[hook_key]
