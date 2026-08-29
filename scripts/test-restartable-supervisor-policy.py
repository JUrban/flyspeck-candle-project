#!/usr/bin/env python3
"""Structural regressions for the restartable PFT generation watchdog."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR = ROOT / "scripts/run-restartable-flyspeck-export.sh"
RUNBOOK = ROOT / "docs/full-l2-runbook.md"


class RestartableSupervisorPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.supervisor = SUPERVISOR.read_text(encoding="utf-8")
        cls.runbook = RUNBOOK.read_text(encoding="utf-8")

    def test_generation_timeout_is_finite_configurable_and_long_enough(self) -> None:
        self.assertIn(
            "generation_timeout_seconds="
            "${CANDLE_PFT_GENERATION_TIMEOUT_SECONDS:-259200}",
            self.supervisor,
        )
        self.assertIn(
            '[[ "$generation_timeout_seconds" =~ ^[1-9][0-9]*$ ]]',
            self.supervisor,
        )
        self.assertEqual(
            self.supervisor.count('timeout "$generation_timeout_seconds"'),
            2,
        )

    def test_no_dmtcp_generation_retains_the_old_one_day_limit(self) -> None:
        self.assertIsNone(
            re.search(r"timeout\s+86400\s+dmtcp_(?:launch|restart)", self.supervisor)
        )
        self.assertIn("72-hour operational timeout", self.runbook)
        self.assertIn("CANDLE_PFT_GENERATION_TIMEOUT_SECONDS", self.runbook)


if __name__ == "__main__":
    unittest.main()
