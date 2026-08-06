import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

from watiba import Watiba, WTOutput, WTWaitException


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

    def test_directory_context_can_be_kept_or_discarded(self):
        watiba = Watiba()
        original = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as temporary_directory:
                output = watiba.bash(f"cd {temporary_directory}", context=True)
                self.assertEqual(output.cwd, temporary_directory)
                watiba.bash(f"cd {original}", context=False)
                self.assertEqual(os.getcwd(), temporary_directory)
        finally:
            os.chdir(original)

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

    def test_chain_pipes_only_the_selected_source_host(self):
        class FakeWatiba(Watiba):
            def __init__(self):
                super().__init__()
                self.ssh_calls = []

            def ssh(self, command, host, context=True, port=None, run_post_hooks=True):
                self.ssh_calls.append((host, command))
                output = WTOutput()
                output.stdout = [f"from-{host}"]
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
        self.assertIn("from-source-a", pipe_calls[0][1])


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
