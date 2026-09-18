#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


PROGRAM = Path(__file__).with_name("inspect-flyspeck-progress.py")
SPEC = importlib.util.spec_from_file_location("inspect_flyspeck_progress", PROGRAM)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InspectFlyspeckProgressTests(unittest.TestCase):
    def test_good_list_archive_progress(self) -> None:
        result = MODULE.inspect_lines([
            "CANDLE_FLYSPECK_STRATUM_ACTION_OK digest 169 source normalized load",
            "Verifying: |- ALL good_list tame_archive_list",
            "1701 / 19715",
        ])
        self.assertEqual(result["phase"], "good_list_archive")
        self.assertEqual(result["last_committed_action"], 169)
        self.assertEqual(result["archive_completed"], 1701)
        self.assertEqual(result["archive_total"], 19715)

    def test_live_lp_terminal_progress(self) -> None:
        result = MODULE.inspect_lines([
            "Verifying linear programs (it can take more than 15 hours)...",
            "Verifying /inputs/hard_10.dat",
            "(14) 1/1",
            "terminals = 58: 1 2 3 4 5 6",
        ])
        self.assertEqual(result["phase"], "lp_terminal_proof")
        self.assertEqual(result["lp_file"], "hard_10.dat")
        self.assertEqual(result["lp_files_remaining_including_current"], 14)
        self.assertEqual(result["lp_certificate_index"], 1)
        self.assertEqual(result["lp_certificate_total_in_file"], 1)
        self.assertEqual(result["terminal_completed"], 6)
        self.assertEqual(result["terminal_total"], 58)

    def test_later_phase_supersedes_terminal_progress(self) -> None:
        result = MODULE.inspect_lines([
            "terminals = 3: 1 2 3",
            "Linear programs verified",
            "Constructing the final linear programming result...",
            "The final linear programming result is constructed",
        ])
        self.assertEqual(result["phase"], "lp_final_theorem_constructed")
        self.assertEqual(result["terminal_completed"], 3)
        self.assertEqual(result["terminal_total"], 3)

    def test_failure_supersedes_prior_progress(self) -> None:
        result = MODULE.inspect_lines([
            "(15) 1/1",
            "Exception: Failure compatibility defect",
        ])
        self.assertEqual(result["phase"], "failure")
        self.assertEqual(
            result["last_error"], "Exception: Failure compatibility defect"
        )


if __name__ == "__main__":
    unittest.main()
