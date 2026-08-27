#!/usr/bin/env python3

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
spec = importlib.util.spec_from_file_location("compatibility_triage", SCRIPT_DIR / "triage_compatibility.py")
triage = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = triage
assert spec.loader is not None
spec.loader.exec_module(triage)


class CompatibilityTriageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.findings_raw, cls.findings = triage.load_findings(
            PROJECT_ROOT / "compatibility/generated/inventory-findings.jsonl"
        )
        cls.rules = json.loads(
            (PROJECT_ROOT / "compatibility/pointer-triage-rules.json").read_text(encoding="utf-8")
        )
        cls.ffi_review = json.loads(
            (PROJECT_ROOT / "compatibility/ffi-review.json").read_text(encoding="utf-8")
        )

    def test_review_covers_every_pointer_once(self):
        document = triage.build_pointer_document(self.findings_raw, self.findings, self.rules)
        self.assertEqual(document["counts"]["total"], 240)
        self.assertEqual(document["counts"]["by_s3_dependency_status"], {
            "not_selected_source": 225,
            "required_source": 15,
        })
        self.assertEqual(document["counts"]["by_ledger_disposition"], {
            "excluded_from_pointer_identity_after_name_resolution": 2,
            "excluded_from_selected_s3_route": 225,
            "open_identity_contract": 12,
            "open_immediate_representation_contract": 1,
        })

    def test_overlapping_rule_is_rejected(self):
        rules = copy.deepcopy(self.rules)
        rules["rules"].append(copy.deepcopy(rules["rules"][0]))
        rules["rules"][-1]["id"] = "PTR-DUPLICATE-TEST"
        with self.assertRaisesRegex(ValueError, "expected one review rule"):
            triage.build_pointer_document(self.findings_raw, self.findings, rules)

    def test_selected_source_contains_no_custom_ffi_calls(self):
        document = triage.build_ffi_document(self.findings_raw, self.findings, self.ffi_review)
        self.assertEqual(document["counts"], {
            "by_s3_dependency_status": {},
            "total": 0,
        })
        self.assertEqual(document["records"], [])

    def test_review_for_absent_ffi_is_rejected(self):
        review = copy.deepcopy(self.ffi_review)
        review["calls"].append({"command": "absent"})
        with self.assertRaisesRegex(ValueError, "reviewed FFI commands absent"):
            triage.build_ffi_document(self.findings_raw, self.findings, review)


if __name__ == "__main__":
    unittest.main()
