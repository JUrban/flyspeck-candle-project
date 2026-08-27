#!/usr/bin/env python3
"""Regression tests for the narrow post-DMTCP truncate helper."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


HELPER = Path(__file__).resolve().parent / "bin" / "truncate"


class ResumeTruncateTests(unittest.TestCase):
    def run_helper(self, *arguments):
        environment = os.environ.copy()
        environment["CANDLE_PFT_TRUNCATE_SETTLE_SECONDS"] = "0"
        return subprocess.run(
            [str(HELPER), *arguments],
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_exact_supported_form_truncates(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "trace.bin"
            target.write_bytes(b"abcdefgh")
            result = self.run_helper("-s", "3", "--", str(target))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(target.read_bytes(), b"abc")

    def test_other_forms_are_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "trace.bin"
            target.write_bytes(b"abcdefgh")
            result = self.run_helper("-s", "3", str(target))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(target.read_bytes(), b"abcdefgh")

    def test_negative_sizes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "trace.bin"
            target.write_bytes(b"abcdefgh")
            result = self.run_helper("-s", "-1", "--", str(target))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(target.read_bytes(), b"abcdefgh")


if __name__ == "__main__":
    unittest.main()
