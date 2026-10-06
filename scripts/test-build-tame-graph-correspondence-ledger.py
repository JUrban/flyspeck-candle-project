#!/usr/bin/env python3
"""Focused integration checks for the tame-graph correspondence ledger."""

from __future__ import annotations

import importlib.util
import json
import os
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "build-tame-graph-correspondence-ledger.py"
INVENTORY = (
    PROJECT_ROOT
    / "third_party"
    / "afp-flyspeck-tame-2014-08-28"
    / "inventory.json"
)
FLYSPECK_ROOT = Path(
    os.environ.get(
        "CANDLE_TAME_FLYSPECK_ROOT",
        str(PROJECT_ROOT.parent / "repos" / "flyspeck"),
    )
)
SPEC = importlib.util.spec_from_file_location("build_tame_graph_ledger", SCRIPT)
assert SPEC and SPEC.loader
LEDGER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LEDGER)


class TameGraphCorrespondenceLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not FLYSPECK_ROOT.is_dir():
            raise unittest.SkipTest(f"missing direct Flyspeck worktree: {FLYSPECK_ROOT}")
        cls.ledger = LEDGER.build_ledger(INVENTORY, FLYSPECK_ROOT)

    def test_closures_and_anchors(self) -> None:
        closures = self.ledger["theory_closures"]
        self.assertIn("ArchComp", closures["parameter0_computation"]["theories"])
        self.assertIn("ArchCompProps", closures["parameter0_computation"]["theories"])
        self.assertNotIn("ArchStat", closures["full_completeness"]["theories"])
        self.assertEqual(closures["excluded_historical_theories"], ["ArchStat"])
        anchors = {(item["theory"], item["name"]) for item in self.ledger["anchors"]}
        self.assertEqual(anchors, {(theory, name) for theory, name, _ in LEDGER.ANCHORS})

    def test_known_existing_and_missing_boundaries(self) -> None:
        entries = {
            (item["theory"], item["name"]): item
            for item in self.ledger["declarations"]
        }
        for key in (
            ("Plane1", "PlaneGraphs"),
            ("Tame", "tame"),
            ("ArchCompAux", "fgraph"),
            ("Completeness", "Archive"),
        ):
            self.assertEqual(
                entries[key]["status"], "existing_translation_entry_unvalidated", key
            )
        for key in (
            ("ArchCompAux", "pre_iso_test"),
            ("ArchCompAux", "samet"),
            ("ArchCompProps", "tameEnumFilter"),
        ):
            self.assertEqual(entries[key]["status"], "missing_definition_correspondence", key)

    def test_serialization_is_stable(self) -> None:
        first = LEDGER.canonical_bytes(self.ledger)
        second = LEDGER.canonical_bytes(LEDGER.build_ledger(INVENTORY, FLYSPECK_ROOT))
        self.assertEqual(first, second)
        parsed = json.loads(first)
        self.assertEqual(parsed["artifact_kind"], "tame_graph_isabelle_hol_correspondence_ledger")


if __name__ == "__main__":
    unittest.main()
