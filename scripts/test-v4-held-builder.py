#!/usr/bin/env python3
"""Build and exercise the standalone native V4 held-builder boundary."""

from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
NATIVE = ROOT / "native"


class V4HeldBuilderTests(unittest.TestCase):
    def _compile_and_run(
        self, *, sanitizers: bool
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(
            prefix="candle-v4-held-builder-test-"
        ) as temporary:
            executable = pathlib.Path(temporary) / "test-v4-held-builder"
            flags = ["-std=c11", "-O2", "-Wall", "-Wextra", "-Werror"]
            environment = None
            if sanitizers:
                flags = [
                    "-std=c11", "-O1", "-g", "-Wall", "-Wextra", "-Werror",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                ]
                environment = os.environ.copy()
                environment["ASAN_OPTIONS"] = "detect_leaks=1:halt_on_error=1"
                environment["UBSAN_OPTIONS"] = (
                    "halt_on_error=1:print_stacktrace=1"
                )
            subprocess.run(
                [
                    "cc", *flags, "-I", str(NATIVE),
                    str(NATIVE / "v4_output_root_walk.c"),
                    str(NATIVE / "v4_held_builder.c"),
                    str(NATIVE / "test_v4_held_builder.c"),
                    "-o", str(executable),
                ],
                check=True,
                cwd=ROOT,
            )
            return subprocess.run(
                [str(executable)], cwd=ROOT, capture_output=True, text=True,
                check=False, env=environment,
            )

    def _check(self, result: subprocess.CompletedProcess[str]) -> None:
        if result.returncode == 77:
            self.assertTrue(result.stdout.startswith("SKIP: "), result)
            self.skipTest(result.stdout.strip())
        self.assertEqual(result.returncode, 0, result)
        self.assertEqual(
            result.stdout, "PASS: native V4 held-builder boundary\n"
        )
        self.assertEqual(result.stderr, "")

    def test_real_pidfd_ptrace_gate_and_empty_walk(self) -> None:
        self._check(self._compile_and_run(sanitizers=False))

    def test_real_boundary_under_asan_ubsan(self) -> None:
        self._check(self._compile_and_run(sanitizers=True))

    def test_slice_remains_below_protocol_and_exec(self) -> None:
        source = (NATIVE / "v4_held_builder.c").read_text(encoding="utf-8")
        header = (NATIVE / "v4_held_builder.h").read_text(encoding="utf-8")
        self.assertNotIn("PTRACE_TRACEME", source)
        self.assertNotIn("PTRACE_ATTACH", source)
        self.assertNotIn("fork(", source)
        self.assertNotIn("execve(", source)
        self.assertNotIn("schema", source.lower())
        self.assertIn("PTRACE_SEIZE", source)
        self.assertIn("PTRACE_INTERRUPT", source)
        self.assertIn("PTRACE_EVENT_STOP", source)
        self.assertIn("SYS_clone", source)
        self.assertIn("V4_HB_FIXED_CLONE_FLAGS", source)
        self.assertIn("CLONE_NEWNS", source)
        self.assertIn("CLONE_NEWUSER", source)
        self.assertIn("CLONE_NEWPID", source)
        self.assertIn("CLONE_NEWNET", source)
        self.assertIn("CLONE_NEWIPC", source)
        self.assertNotIn("CLONE_NEWUTS", source)
        self.assertNotIn("CLONE_FILES", source)
        self.assertNotIn("CLONE_FS", source)
        self.assertNotIn("CLONE_VM", source)
        self.assertNotIn("ptrace(PTRACE_SYSCALL", source)
        self.assertNotIn("seccomp", source.lower())
        self.assertIn("getpid(), builder->pid, KCMP_FILE", source)
        self.assertIn("V4_HB_ROOT_STATUS_FLAGS", source)
        self.assertIn("v4_hb_builder_run_bound_root_walks", header)
        self.assertNotIn("v4_hb_builder_run_empty_prewalk", header)
        uid_order = source.index("uid_map_write_order = 1U")
        setgroups_order = source.index("setgroups_deny_write_order = 2U")
        gid_order = source.index("gid_map_write_order = 3U")
        self.assertLess(uid_order, setgroups_order)
        self.assertLess(setgroups_order, gid_order)
        interrupt = source.index("if (ptrace(PTRACE_INTERRUPT")
        event_consumed = source.index(
            "builder->held_stop_consumed = 1", interrupt
        )
        map_capture = source.index(
            "code = v4_hb_configure_child_id_maps", event_consumed
        )
        self.assertLess(interrupt, event_consumed)
        self.assertLess(event_consumed, map_capture)


if __name__ == "__main__":
    unittest.main()
