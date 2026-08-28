#!/usr/bin/env python3

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("compatibility_ledger_validator", SCRIPT_DIR / "validate_compatibility_ledger.py")
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
assert spec.loader is not None
spec.loader.exec_module(validator)


class LedgerLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads((SCRIPT_DIR.parent / "compatibility/ledger.json").read_text(encoding="utf-8"))

    def test_seed_entries_are_valid_review_candidates(self):
        for entry in self.ledger["entries"]:
            validator.validate_local_entry(entry)

    def test_confirmed_divergence_requires_observations(self):
        entry = copy.deepcopy(self.ledger["entries"][0])
        entry["entry_kind"] = "confirmed_divergence"
        entry["divergence_state"] = "confirmed_divergence"
        with self.assertRaisesRegex(validator.ValidationError, "needs reproducer"):
            validator.validate_local_entry(entry)

    def test_dopen_review_fails_closed_before_compiled_provenance(self):
        entry = next(
            item for item in self.ledger["entries"]
            if item["id"] == "PROJECT-OPEN-DECLARATION-REVIEW-001"
        )
        self.assertEqual(entry["status"], "regression_pending")
        self.assertEqual(entry["chosen_remedy"]["status"], "chosen")
        self.assertEqual(entry["proof_obligation"]["status"], "open")
        self.assertIn(
            "PROJECT-DOPEN-ARTIFACT-PROVENANCE-GATE",
            entry["regression_ids"],
        )
        self.assertIn(
            "A synthetic Dopen smoke alone is insufficient",
            entry["proof_obligation"]["description"],
        )
        self.assertIn(
            "4e312c0f7e18b9c5789c8ac4e0af257bff895cf5",
            entry["notes"],
        )

    def test_lp_normalizations_remain_pending_until_compiled_closure(self):
        immediate = next(
            item for item in self.ledger["entries"]
            if item["id"] == "PROJECT-POINTER-S3-IMMEDIATE-001"
        )
        shell = next(
            item for item in self.ledger["entries"]
            if item["id"] == "PROJECT-FFI-SYSTEM-001"
        )
        for entry in (immediate, shell):
            self.assertEqual(entry["status"], "regression_pending")
            self.assertEqual(entry["chosen_remedy"]["status"], "implemented")
            self.assertEqual(entry["proof_obligation"]["status"], "open")
            self.assertIn(
                "PROJECT-LP-CERTIFICATE-CLOSURE-GATE",
                entry["regression_ids"],
            )
        self.assertIn("no longer invokes", shell["notes"])
        self.assertIn("legacy compiler", immediate["notes"])

    def test_resolved_requires_regression_and_proof_evidence(self):
        entry = copy.deepcopy(self.ledger["entries"][0])
        entry.update({
            "entry_kind": "confirmed_divergence",
            "divergence_state": "confirmed_divergence",
            "status": "resolved",
            "affected_files_status": "enumerated",
            "affected_corpus_files": [{"repository": "candle", "path": "x.ml"}],
            "minimal_reproducer": {"status": "ready", "path": "tests/x.ml"},
            "ocaml_reference": {"status": "observed", "outcome": "accepted", "evidence": ["ocaml.log"]},
            "candle_outcome": {"status": "observed", "outcome": "accepted", "evidence": ["candle.log"]},
            "chosen_remedy": {"status": "implemented", "kind": "language_fix", "description": "implemented"},
            "proof_obligation": {"status": "discharged", "description": "proved", "evidence": ["theory.log"]},
            "regression_ids": [],
        })
        with self.assertRaisesRegex(validator.ValidationError, "stable regression IDs"):
            validator.validate_local_entry(entry)
        entry["regression_ids"] = ["REG-001"]
        validator.validate_local_entry(entry)


if __name__ == "__main__":
    unittest.main()
