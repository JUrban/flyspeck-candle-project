#!/usr/bin/env python3
"""Build and exercise the standalone native V4 output-root walk primitive."""

from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
NATIVE = ROOT / "native"


class V4OutputRootWalkTests(unittest.TestCase):
    def test_native_private_tmpfs_and_attacks(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="candle-v4-output-root-walk-test-"
        ) as temporary:
            executable = pathlib.Path(temporary) / "test-v4-output-root-walk"
            subprocess.run(
                [
                    "cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                    "-I", str(NATIVE),
                    str(NATIVE / "v4_output_root_walk.c"),
                    str(NATIVE / "test_v4_output_root_walk.c"),
                    "-o", str(executable),
                ],
                check=True,
                cwd=ROOT,
            )
            result = subprocess.run(
                [str(executable)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 77:
                self.assertTrue(result.stdout.startswith("SKIP: "), result)
                self.skipTest(result.stdout.strip())
            self.assertEqual(result.returncode, 0, result)
            self.assertEqual(
                result.stdout,
                "PASS: native V4 output-root anchor/walk\n",
            )
            self.assertEqual(result.stderr, "")

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
