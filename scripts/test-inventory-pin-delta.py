#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
spec = importlib.util.spec_from_file_location(
    "inventory_pin_delta", SCRIPT_DIR / "compare-compatibility-inventory-pins.py"
)
pin_delta = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pin_delta
assert spec.loader is not None
spec.loader.exec_module(pin_delta)


class InventoryPinDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = pin_delta.build_document(
            PROJECT_ROOT,
            Path("/project/repos"),
            PROJECT_ROOT / "compatibility/generated",
            PROJECT_ROOT / "compatibility/inventory-pin-contract.json",
        )

    def test_checked_in_artifact_is_reproducible(self):
        checked_in = json.loads(
            (PROJECT_ROOT / "compatibility/generated/inventory-pin-delta.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(self.document, checked_in)

    def test_exact_pin_delta(self):
        self.assertEqual(
            self.document["selected_lane"]["flyspeck_commit"],
            "1ce0353008eba83d3c76ae9a25c3c242e4802d53",
        )
        self.assertEqual(
            self.document["comparison_lane"]["flyspeck_commit"],
            "2ea440e9f7c55734d1e47738e44a6129ce0ecf5a",
        )
        self.assertEqual(
            self.document["delta"]["totals"],
            {
                "findings": {"comparison": 6049, "selected": 6074, "selected_minus_comparison": 25},
                "lexical_notes": {"comparison": 1, "selected": 1, "selected_minus_comparison": 0},
                "source_bytes_scanned": {
                    "comparison": 100751549,
                    "selected": 100859921,
                    "selected_minus_comparison": 108372,
                },
                "source_files_scanned": {
                    "comparison": 1347,
                    "selected": 1364,
                    "selected_minus_comparison": 17,
                },
            },
        )

    def test_exact_g3_g4_record_delta(self):
        pointer = self.document["triage"]["pointer"]
        ffi = self.document["triage"]["ffi"]
        self.assertEqual(
            (pointer["stable_records_matched"], pointer["comparison_only_records"], pointer["selected_only_records"]),
            (217, 0, 23),
        )
        self.assertEqual(
            (ffi["stable_records_matched"], ffi["comparison_only_records"], ffi["selected_only_records"]),
            (0, 2, 0),
        )


if __name__ == "__main__":
    unittest.main()
