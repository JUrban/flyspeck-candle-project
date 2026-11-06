#!/usr/bin/env python3
"""Focused tests for summarize-nl-stock-projection-inventory.py."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPT = Path(__file__).with_name("summarize-nl-stock-projection-inventory.py")
SPEC = importlib.util.spec_from_file_location("nl_stock_projection_inventory", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class StockProjectionInventoryTest(unittest.TestCase):
    def test_read_and_join(self) -> None:
        text = "\n".join(
            [
                "CANDLE_NL_SELECTED_LEAF_DETAIL|a|0|100|0|0|0",
                "CANDLE_NL_SELECTED_LEAF_DETAIL|b|0|200|2|1|1",
                "CANDLE_NL_SELECTED_LEAF_DETAIL|b|1|300|3|2|1",
                "CANDLE_NL_SELECTED_LEAF_DETAIL_SUMMARY|2|3|7|600|3",
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "detail.log"
            path.write_text(text + "\n", encoding="utf-8")
            leaves, summary = MODULE.read_leaf_details(path)
        sources = [
            SimpleNamespace(source_id="a", constants_serialized="x"),
            SimpleNamespace(source_id="b", constants_serialized="y"),
        ]
        prepared = [
            SimpleNamespace(source_id="a", error=None, unsupported=()),
            SimpleNamespace(source_id="b", error=None, unsupported=("hminus",)),
        ]
        result = MODULE.summarize(leaves, summary, sources, prepared, 20)
        self.assertEqual(result["selected_leaves"], 3)
        self.assertEqual(result["historical_msec"], 600)
        self.assertEqual(result["candidate_sample_group_counts"], {"hminus": 2, "supported": 1})
        self.assertEqual(len(result["top_signature_families"]), 2)

    def test_rejects_depth_mismatch(self) -> None:
        text = "\n".join(
            [
                "CANDLE_NL_SELECTED_LEAF_DETAIL|a|0|100|2|0|1",
                "CANDLE_NL_SELECTED_LEAF_DETAIL_SUMMARY|1|1|1|100|2",
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "detail.log"
            path.write_text(text + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inconsistent path depth"):
                MODULE.read_leaf_details(path)


if __name__ == "__main__":
    unittest.main()
