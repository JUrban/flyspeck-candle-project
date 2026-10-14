#!/usr/bin/env python3
"""Focused tests for the prepared Flyspeck NL coverage summarizer."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).with_name("summarize-nl-prepared-coverage.py")
SPEC = importlib.util.spec_from_file_location("nl_prepared_coverage", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PreparedCoverageTests(unittest.TestCase):
    def write_log(self, text: str) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "runtime.log"
        path.write_text(text, encoding="utf-8")
        return path

    def inventory(self):
        return [
            SimpleNamespace(source_id="a", parameter_count=2),
            SimpleNamespace(source_id="b with spaces", parameter_count=5),
            SimpleNamespace(source_id="c", parameter_count=7),
        ]

    def test_complete_summary_and_weighted_heads(self) -> None:
        log = self.write_log(
            "noise\n"
            "CANDLE_NL_PREPARED_SUPPORT_PROBE DEVELOPMENT_NON_RELEASE "
            "source_id=a dimension=6 disjuncts=1 unsupported= "
            "elapsed_seconds=0\n"
            "CANDLE_NL_PREPARED_SUPPORT_PROBE DEVELOPMENT_NON_RELEASE "
            "source_id=b with spaces dimension=6 disjuncts=2 "
            "unsupported=vol_x,gchi elapsed_seconds=0\n"
            "CANDLE_NL_PREPARED_SUPPORT_PROBE_ERROR DEVELOPMENT_NON_RELEASE "
            "source_id=c message=failed preparation\n"
        )
        result = MODULE.summarize(
            MODULE.read_prepared(log), self.inventory()
        )
        self.assertTrue(result["complete"])
        self.assertEqual(result["normalization"], "strict")
        self.assertEqual(result["supported_source_ids"], 1)
        self.assertEqual(result["supported_parameter_records"], 2)
        self.assertEqual(
            result["supported_sources"],
            [
                {
                    "source_id": "a",
                    "parameter_records": 2,
                    "dimension": 6,
                    "disjuncts": 1,
                }
            ],
        )
        self.assertEqual(result["unsupported_source_ids"], 1)
        self.assertEqual(result["unsupported_parameter_records"], 5)
        self.assertEqual(result["error_source_ids"], 1)
        self.assertEqual(result["error_parameter_records"], 7)
        self.assertEqual(result["dimensions"], {6: 2})
        self.assertEqual(result["disjuncts"], {1: 1, 2: 1})
        self.assertEqual(result["distinct_unsupported_signatures"], 1)
        self.assertEqual(
            result["unsupported_signatures"],
            [
                {
                    "heads": ["gchi", "vol_x"],
                    "source_ids": 1,
                    "parameter_records": 5,
                }
            ],
        )
        self.assertEqual(
            result["unsupported_heads"],
            [
                {"head": "gchi", "source_ids": 1, "parameter_records": 5},
                {"head": "vol_x", "source_ids": 1, "parameter_records": 5},
            ],
        )

    def test_partial_scan_reports_missing_ids(self) -> None:
        log = self.write_log(
            "CANDLE_NL_PREPARED_SUPPORT_PROBE DEVELOPMENT_NON_RELEASE "
            "source_id=a dimension=6 disjuncts=1 unsupported= "
            "elapsed_seconds=0\n"
        )
        result = MODULE.summarize(
            MODULE.read_prepared(log), self.inventory()
        )
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing_source_ids"], ["b with spaces", "c"])

    def test_duplicate_source_fails_closed(self) -> None:
        marker = (
            "CANDLE_NL_PREPARED_SUPPORT_PROBE DEVELOPMENT_NON_RELEASE "
            "source_id=a dimension=6 disjuncts=1 unsupported= "
            "elapsed_seconds=0\n"
        )
        with self.assertRaisesRegex(ValueError, "duplicate prepared"):
            MODULE.read_prepared(self.write_log(marker + marker))

    def test_unexpected_source_fails_closed(self) -> None:
        log = self.write_log(
            "CANDLE_NL_PREPARED_SUPPORT_PROBE DEVELOPMENT_NON_RELEASE "
            "source_id=unexpected dimension=6 disjuncts=1 unsupported= "
            "elapsed_seconds=0\n"
        )
        with self.assertRaisesRegex(ValueError, "unexpected IDs"):
            MODULE.summarize(MODULE.read_prepared(log), self.inventory())

    def test_expanded_mode_is_recorded(self) -> None:
        log = self.write_log(
            "CANDLE_NL_PREPARED_EXPANDED_SUPPORT_PROBE "
            "DEVELOPMENT_NON_RELEASE source_id=a dimension=6 disjuncts=1 "
            "unsupported= elapsed_seconds=0\n"
        )
        records = MODULE.read_prepared(log)
        result = MODULE.summarize(records, self.inventory())
        self.assertEqual(result["normalization"], "expanded")

    def test_mixed_modes_fail_closed(self) -> None:
        log = self.write_log(
            "CANDLE_NL_PREPARED_SUPPORT_PROBE DEVELOPMENT_NON_RELEASE "
            "source_id=a dimension=6 disjuncts=1 unsupported= "
            "elapsed_seconds=0\n"
            "CANDLE_NL_PREPARED_EXPANDED_SUPPORT_PROBE "
            "DEVELOPMENT_NON_RELEASE source_id=b with spaces dimension=6 "
            "disjuncts=1 unsupported= elapsed_seconds=0\n"
        )
        with self.assertRaisesRegex(ValueError, "mixed.*normalization"):
            MODULE.read_prepared(log)

    def test_selected_leaf_weights(self) -> None:
        prepared_log = self.write_log(
            "CANDLE_NL_PREPARED_SUPPORT_PROBE DEVELOPMENT_NON_RELEASE "
            "source_id=a dimension=6 disjuncts=1 unsupported= "
            "elapsed_seconds=0\n"
            "CANDLE_NL_PREPARED_SUPPORT_PROBE DEVELOPMENT_NON_RELEASE "
            "source_id=b with spaces dimension=6 disjuncts=1 "
            "unsupported=vol_x elapsed_seconds=0\n"
            "CANDLE_NL_PREPARED_SUPPORT_PROBE_ERROR DEVELOPMENT_NON_RELEASE "
            "source_id=c message=failed\n"
        )
        selected_log = self.write_log(
            "CANDLE_NL_SELECTED_LEAF_COUNT DEVELOPMENT_NON_RELEASE "
            "source_id=a selected_leaves=11\n"
            "CANDLE_NL_SELECTED_LEAF_COUNT DEVELOPMENT_NON_RELEASE "
            "source_id=b with spaces selected_leaves=13\n"
            "CANDLE_NL_SELECTED_LEAF_COUNT DEVELOPMENT_NON_RELEASE "
            "source_id=c selected_leaves=17\n"
        )
        result = MODULE.summarize(
            MODULE.read_prepared(prepared_log),
            self.inventory(),
            MODULE.read_selected(selected_log),
        )
        self.assertEqual(result["selected_leaves"], 41)
        self.assertEqual(result["missing_selected_leaves"], 0)
        self.assertEqual(result["supported_selected_leaves"], 11)
        self.assertEqual(result["unsupported_selected_leaves"], 13)
        self.assertEqual(result["error_selected_leaves"], 17)

    def test_selected_leaf_identity_mismatch_fails_closed(self) -> None:
        log = self.write_log(
            "CANDLE_NL_SELECTED_LEAF_COUNT DEVELOPMENT_NON_RELEASE "
            "source_id=a selected_leaves=1\n"
        )
        prepared = [
            MODULE.PreparedRecord("strict", "a", 6, 1, (), None)
        ]
        with self.assertRaisesRegex(ValueError, "selected-leaf IDs"):
            MODULE.summarize(
                prepared, self.inventory(), MODULE.read_selected(log)
            )


if __name__ == "__main__":
    unittest.main()
