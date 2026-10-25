#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check-long-run-hazards.py"
SPEC = importlib.util.spec_from_file_location("long_run_gate", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class LongRunHazardGateTests(unittest.TestCase):
    def test_ledger_has_only_registered_checks(self) -> None:
        ledger = json.loads(
            (ROOT / "docs/long-run-hazard-ledger.json").read_text(encoding="utf-8")
        )
        hazards = ledger["hazards"]
        self.assertEqual(len({item["id"] for item in hazards}), len(hazards))
        self.assertGreaterEqual(len(hazards), 15)
        for item in hazards:
            self.assertIn(item["check_id"], GATE.CHECKS)

    def test_parse_receipt_splits_only_first_equals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "receipt"
            path.write_text("status=0\nmarker=a=b\n", encoding="utf-8")
            self.assertEqual(GATE.parse_receipt(path), {"status": "0", "marker": "a=b"})

    def test_controller_target_must_be_literal_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            good = root / "good.sh"
            bad = root / "bad.sh"
            good.write_text("run=/project/example-run\n", encoding="utf-8")
            bad.write_text("run=$base/example-run\n", encoding="utf-8")
            self.assertEqual(
                GATE.controller_run_target(good), pathlib.Path("/project/example-run")
            )
            self.assertIsNone(GATE.controller_run_target(bad))

    def test_existing_controller_retains_exact_theorem_contract(self) -> None:
        controller = ROOT / "scripts/run-fast-nl-v664-first-theorem-controller.sh"
        result = GATE.check_theorem_controller_contract({}, controller)
        self.assertTrue(result.ok, result.detail)


if __name__ == "__main__":
    unittest.main()
