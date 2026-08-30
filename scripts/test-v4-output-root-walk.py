#!/usr/bin/env python3
"""Build and exercise the standalone native V4 output-root walk primitive."""

from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
NATIVE = ROOT / "native"


class V4OutputRootWalkTests(unittest.TestCase):
    def _compile_and_run(
        self, *, sanitizers: bool
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(
            prefix="candle-v4-output-root-walk-test-"
        ) as temporary:
            executable = pathlib.Path(temporary) / "test-v4-output-root-walk"
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
                    "cc", *flags,
                    "-I", str(NATIVE),
                    str(NATIVE / "v4_output_root_walk.c"),
                    str(NATIVE / "test_v4_output_root_walk.c"),
                    "-o", str(executable),
                ],
                check=True,
                cwd=ROOT,
            )
            return subprocess.run(
                [str(executable)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                env=environment,
            )

    def _check_native_result(
        self, result: subprocess.CompletedProcess[str]
    ) -> None:
        if result.returncode == 77:
            self.assertTrue(result.stdout.startswith("SKIP: "), result)
            self.skipTest(result.stdout.strip())
        self.assertEqual(result.returncode, 0, result)
        self.assertEqual(
            result.stdout,
            "PASS: native V4 output-root anchor/walk\n",
        )
        self.assertEqual(result.stderr, "")

    def test_native_private_tmpfs_and_attacks(self) -> None:
        self._check_native_result(self._compile_and_run(sanitizers=False))

    def test_native_private_tmpfs_and_attacks_under_sanitizers(self) -> None:
        self._check_native_result(self._compile_and_run(sanitizers=True))

    def test_primitive_has_no_pathname_walk_fallback(self) -> None:
        source = (NATIVE / "v4_output_root_walk.c").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("openat(", source)
        self.assertNotIn("opendir(", source)
        self.assertNotIn("readdir(", source)
        self.assertNotIn("nftw(", source)
        self.assertIn("SYS_openat2", source)
        self.assertIn("SYS_getdents64", source)
        self.assertIn("RESOLVE_NO_XDEV", source)


if __name__ == "__main__":
    unittest.main()
