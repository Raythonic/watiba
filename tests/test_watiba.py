import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

from watiba import (
    Watiba,
    WTChainException,
    WTHookException,
    WTOutput,
    WTSpawnException,
    WTWaitException,
)


ROOT = Path(__file__).resolve().parents[1]
COMPILER = ROOT / "watiba" / "watiba-c.py"


class WatibaRuntimeTests(unittest.TestCase):
    def test_bash_captures_output_and_handles_large_streams(self):
        watiba = Watiba()
        output = watiba.bash(
            f"{sys.executable} -c \"import sys; "
            "sys.stdout.write('x' * 200000); sys.stderr.write('problem\\n')\"",
            context=False,
        )
        self.assertEqual(output.exit_code, 0)
        self.assertEqual(len(output.stdout[0]), 200000)
        self.assertEqual(output.stderr, ["problem"])

    def test_cwd_capture_does_not_change_command_output_boundaries(self):
        watiba = Watiba()
        self.assertEqual(watiba.bash("printf no-newline").stdout, ["no-newline"])
        self.assertEqual(watiba.bash("printf '\\n'").stdout, [""])

    def test_directory_context_can_be_kept_or_discarded(self):
        watiba = Watiba()
        original = os.getcwd()
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = watiba.bash(f"cd {temporary_directory}", context=True)
            self.assertEqual(output.cwd, temporary_directory)
            self.assertEqual(os.getcwd(), original)
            self.assertEqual(watiba.bash("pwd").stdout, [temporary_directory])
            discarded = watiba.bash(f"cd {original}", context=False)
            self.assertEqual(discarded.cwd, temporary_directory)
            self.assertEqual(watiba.bash("pwd").stdout, [temporary_directory])

    def test_directory_context_is_independent_between_threads(self):
        watiba = Watiba()
        barrier = threading.Barrier(2)
        results = {}

        def worker(name, directory):
            watiba.bash(f"cd {directory}")
            barrier.wait()
            results[name] = watiba.bash("pwd").stdout[0]

        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            threads = [
                threading.Thread(target=worker, args=("first", first)),
                threading.Thread(target=worker, args=("second", second)),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(results, {"first": first, "second": second})

    def test_spawn_inherits_logical_cwd_without_changing_parent_process(self):
        watiba = Watiba()
        process_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temporary_directory:
            watiba.bash(f"cd {temporary_directory}")
            promise = watiba.spawn("pwd", lambda promise, args: True, {})
            promise.wait({"sleep": .01, "expire": 100})
            self.assertEqual(promise.output.stdout, [temporary_directory])
            self.assertEqual(os.getcwd(), process_cwd)

    def test_spawn_resolves_and_preserves_fractional_wait(self):
        watiba = Watiba()

        def resolver(promise, args):
            self.assertEqual(args, {"answer": 42})
            return True

        promise = watiba.spawn("printf 'ready\\n'", resolver, {"answer": 42})
        promise.join({"sleep": .01, "expire": 100})
        self.assertTrue(promise.resolved())
        self.assertEqual(promise.output.stdout, ["ready"])
        self.assertIsNotNone(promise.end_time)

    def test_spawn_worker_exceptions_are_raised_by_waiters(self):
        watiba = Watiba()

        def resolver(promise, args):
            raise RuntimeError("resolver failed")

        promise = watiba.spawn("true", resolver, {})
        with self.assertRaisesRegex(RuntimeError, "resolver failed"):
            promise.wait({"sleep": .01, "expire": 100})

    def test_non_boolean_resolver_result_fails_instead_of_hanging(self):
        watiba = Watiba()
        promise = watiba.spawn("true", lambda promise, args: None, {})
        with self.assertRaisesRegex(TypeError, "must return True or False"):
            promise.wait({"sleep": .01, "expire": 100})

    def test_child_can_resolve_parent_promise(self):
        watiba = Watiba()

        def parent_resolver(parent, args):
            def child_resolver(child, child_args):
                child.resolve_parent()
                return True

            watiba.spawn("true", child_resolver, {})
            return False

        promise = watiba.spawn("true", parent_resolver, {})
        promise.join({"sleep": .01, "expire": 100})
        self.assertTrue(promise.resolved())
        self.assertEqual(len(promise.children), 1)
        self.assertTrue(promise.children[0].resolved())

    def test_watcher_receives_spawn_arguments(self):
        watiba = Watiba()
        called = threading.Event()
        received = {}

        def watcher(promise, args):
            received.update(args)
            called.set()

        promise = watiba.spawn("sleep .2", lambda promise, args: False, {"job": "demo"})
        promise.watch(watcher, {"sleep": .01, "expire": .03})
        self.assertTrue(called.wait(1))
        self.assertEqual(received, {"job": "demo"})

    def test_pre_and_post_hooks_can_share_a_pattern(self):
        watiba = Watiba()
        calls = []

        def pre_hook(match, args):
            calls.append(("pre", args))
            return True

        def post_hook(match, args):
            calls.append(("post", args))
            return True

        watiba.add_hook(r"echo .*", pre_hook, 1, post=False)
        watiba.add_hook(r"echo .*", post_hook, 2, post=True)
        watiba.bash("echo hooks", context=False)
        self.assertEqual(calls, [("pre", 1), ("post", 2)])

    def test_non_recursive_hook_flag_blocks_same_pattern_reentry(self):
        watiba = Watiba()
        calls = []

        def hook(match, args):
            calls.append(match.string)
            watiba.bash("echo nested", context=False)
            return True

        watiba.add_hook(r"echo .*", hook, {}, recursive=False)
        watiba.bash("echo outer", context=False)
        self.assertEqual(calls, ["echo outer"])

    def test_hook_exception_reports_command_phase_pattern_and_function(self):
        watiba = Watiba()

        def broken_hook(match, args):
            raise ValueError("bad hook")

        watiba.add_hook(r"echo .*", broken_hook, {}, post=True)
        with self.assertRaises(WTHookException) as raised:
            watiba.bash("echo hooks", context=False)
        exception = raised.exception
        self.assertEqual(exception.command, "echo hooks")
        self.assertEqual(exception.phase, "post")
        self.assertEqual(exception.pattern, r"echo .*")
        self.assertIs(exception.function, broken_hook)
        self.assertIsInstance(exception.original_exception, ValueError)
        self.assertIn("bad hook", str(exception))

    def test_false_hook_result_also_reports_hook_context(self):
        watiba = Watiba()

        def failed_hook(match, args):
            return False

        watiba.add_hook(r"echo .*", failed_hook, {}, post=False)
        with self.assertRaises(WTHookException) as raised:
            watiba.bash("echo hooks", context=False)
        self.assertEqual(raised.exception.phase, "pre")
        self.assertEqual(raised.exception.pattern, r"echo .*")
        self.assertIs(raised.exception.function, failed_hook)

    def test_skipping_post_hooks_does_not_reuse_pre_hook_results(self):
        watiba = Watiba()
        calls = []

        def post_hook(match, args):
            calls.append("post")
            return False

        watiba.add_hook(r"echo .*", post_hook, {}, post=True)
        output = watiba.bash("echo hooks", context=False, run_post_hooks=False)
        self.assertEqual(output.stdout, ["hooks"])
        self.assertEqual(calls, [])

    def test_remote_context_is_tracked_per_host_and_applied_remotely(self):
        class FakeRemoteWatiba(Watiba):
            def __init__(self):
                super().__init__()
                self.ssh_commands = []
                self.remote_paths = iter(["/remote/a", "/remote/a", "/remote/b"])

            def bash(self, command, context=True, run_post_hooks=True, run_pre_hooks=True, stdin_text=None):
                self.ssh_commands.append(command)
                marker = re.search(r"(__watiba_cwd_[0-9a-f]+__)", command).group(1)
                output = WTOutput()
                output.stdout = ["\0" + marker + next(self.remote_paths) + "\0"]
                return output

        watiba = FakeRemoteWatiba()
        self.assertEqual(watiba.ssh("cd /remote/a", "host-a").cwd, "/remote/a")
        self.assertEqual(watiba.ssh("pwd", "host-a").cwd, "/remote/a")
        self.assertEqual(watiba.ssh("pwd", "host-b").cwd, "/remote/b")
        self.assertNotIn("cd --", watiba.ssh_commands[0])
        self.assertIn("cd -- /remote/a && pwd", watiba.ssh_commands[1])
        self.assertNotIn("cd -- /remote/a", watiba.ssh_commands[2])

    def test_remote_context_and_pipe_through_a_single_ssh_process(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            fake_bin = temporary_path / "bin"
            fake_bin.mkdir()
            ssh_log = temporary_path / "ssh.log"
            fake_ssh = fake_bin / "ssh"
            fake_ssh.write_text(
                f"#!{sys.executable}\n"
                "import os, subprocess, sys\n"
                "separator = sys.argv.index('--')\n"
                "with open(os.environ['WATIBA_FAKE_SSH_LOG'], 'a') as log:\n"
                "    log.write(sys.argv[separator + 1] + '\\n')\n"
                "result = subprocess.run(sys.argv[separator + 2], shell=True)\n"
                "raise SystemExit(result.returncode)\n"
            )
            fake_ssh.chmod(0o755)
            remote_directory = temporary_path / "remote directory"
            remote_directory.mkdir()
            piped_file = remote_directory / "piped.txt"
            environment = {
                "PATH": f"{fake_bin}:{os.environ['PATH']}",
                "WATIBA_FAKE_SSH_LOG": str(ssh_log),
            }
            with mock.patch.dict(os.environ, environment):
                watiba = Watiba()
                first = watiba.ssh(f"cd {shlex.quote(str(remote_directory))}", "host-a")
                second = watiba.ssh("pwd", "host-a")
                watiba.pipe(["first", "second"], {"host-a": f"cat > {shlex.quote(str(piped_file))}"})

            self.assertEqual(first.cwd, str(remote_directory))
            self.assertEqual(second.stdout, [str(remote_directory)])
            self.assertEqual(piped_file.read_text(), "first\nsecond\n")
            self.assertEqual(ssh_log.read_text().splitlines(), ["host-a", "host-a", "host-a"])

    def test_chain_pipes_only_the_selected_source_host(self):
        class FakeWatiba(Watiba):
            def __init__(self):
                super().__init__()
                self.ssh_calls = []

            def ssh(self, command, host, context=True, port=None, run_post_hooks=True, stdin_text=None):
                self.ssh_calls.append((host, command, stdin_text))
                output = WTOutput()
                output.stdout = [f"first-from-{host}", f"second-from-{host}"]
                return output

        watiba = FakeWatiba()
        watiba.chain(
            "source-command",
            {
                "hosts": ["source-a", "source-b"],
                "stdout": {"source-a": {"target": "consume"}},
            },
        )
        pipe_calls = [call for call in watiba.ssh_calls if call[0] == "target"]
        self.assertEqual(len(pipe_calls), 1)
        self.assertEqual(pipe_calls[0][1], "consume")
        self.assertEqual(pipe_calls[0][2], "first-from-source-a\nsecond-from-source-a\n")

    def test_custom_exceptions_initialize_base_exception_message(self):
        chain_exception = WTChainException("chain failed", "host", "cmd", None)
        spawn_exception = WTSpawnException(None, "spawn failed")
        wait_exception = WTWaitException(None, "wait failed")
        self.assertEqual(str(chain_exception), "chain failed")
        self.assertEqual(str(spawn_exception), "spawn failed")
        self.assertEqual(str(wait_exception), "wait failed")


class WatibaCompilerTests(unittest.TestCase):
    def compile_source(self, source):
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory) / "program.wt"
            source_path.write_text(source)
            result = subprocess.run(
                [sys.executable, str(COMPILER), str(source_path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            compile(result.stdout, str(source_path.with_suffix(".py")), "exec")
            return result.stdout

    def test_compiles_backticks_variables_hosts_and_quotes(self):
        generated = self.compile_source(
            "#!/usr/bin/env python3\n"
            "cmd = 'printf value'\n"
            "host = 'server.example'\n"
            "a = `$cmd`\n"
            "b = -`printf \\\"quoted\\\" and 'single'`\n"
            "c = `hostname`@$host\n"
        )
        self.assertIn("_watiba_.bash(cmd, True)", generated)
        self.assertIn("_watiba_.ssh('hostname', host, True)", generated)

    def test_compiles_nested_spawn_and_hook_blocks(self):
        generated = self.compile_source(
            "def hook(match, args):\n"
            "    return True\n"
            "hook-cmd r\"echo (\\\\S+)\" hook {}\n"
            "root = spawn `echo root` {'level': 1}:\n"
            "    spawn `echo child`:\n"
            "        promise.resolve_parent()\n"
            "        return True\n"
            "    return False\n"
            "root.join()\n"
        )
        self.assertEqual(generated.count("_watiba_.spawn("), 2)
        self.assertIn("recursive=True, post=False", generated)

    def test_generated_spawn_program_runs_end_to_end(self):
        generated = self.compile_source(
            "#!/usr/bin/env python3\n"
            "root = spawn `printf root`:\n"
            "    spawn `printf child`:\n"
            "        promise.resolve_parent()\n"
            "        return True\n"
            "    return False\n"
            "root.join({'sleep': .01, 'expire': 100})\n"
            "print(root.output.stdout[0], root.children[0].output.stdout[0])\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", generated],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "root child")

    def test_shipped_watiba_programs_compile_as_python_312(self):
        for relative_path in ("examples/examples.wt", "tests/integrated_test1.wt"):
            result = subprocess.run(
                [sys.executable, str(COMPILER), str(ROOT / relative_path)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=True,
            )
            compile(result.stdout, relative_path, "exec")


if __name__ == "__main__":
    unittest.main()
