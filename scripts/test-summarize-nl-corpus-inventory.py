#!/usr/bin/env python3
"""Focused tests for summarize-nl-corpus-inventory.py."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("summarize-nl-corpus-inventory.py")
SPEC = importlib.util.spec_from_file_location("nl_inventory", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InventorySummaryTests(unittest.TestCase):
    def write(self, text: str) -> Path:
        temporary = tempfile.NamedTemporaryFile("w", delete=False)
        self.addCleanup(Path(temporary.name).unlink)
        temporary.write(text)
        temporary.close()
        return Path(temporary.name)

    def test_family_counts_and_selection(self) -> None:
        path = self.write(
            "noise\n"
            "CANDLE_NL_CORPUS_SOURCE|a|2|digest-a|x,y\n"
            "# CANDLE_NL_CORPUS_SOURCE|b|3|digest-b|x,y\n"
            "CANDLE_NL_CORPUS_SOURCE|c|7|digest-c|z\n"
        )
        result = MODULE.summarize(MODULE.read_sources(path), "a")
        self.assertEqual(result["source_ids"], 3)
        self.assertEqual(result["parameter_count"], 12)
        self.assertEqual(result["serialized_signature_families"], 2)
        self.assertEqual(result["selected_family"]["source_ids"], 2)
        self.assertEqual(result["selected_family"]["parameter_count"], 5)
        self.assertEqual(result["families"][0]["constants_serialized"], "z")

    def test_comma_named_constant_stays_opaque(self) -> None:
        path = self.write(
            "CANDLE_NL_CORPUS_SOURCE|a|1|d1|!,,,BIT0\n"
            "CANDLE_NL_CORPUS_SOURCE|b|1|d2|!,,,BIT0\n"
        )
        result = MODULE.summarize(MODULE.read_sources(path), "a")
        self.assertEqual(result["serialized_signature_families"], 1)
        self.assertEqual(
            result["selected_family"]["constants_serialized"], "!,,,BIT0"
        )

    def test_duplicate_source_fails_closed(self) -> None:
        path = self.write(
            "CANDLE_NL_CORPUS_SOURCE|a|1|d1|x\n"
            "CANDLE_NL_CORPUS_SOURCE|a|1|d2|y\n"
        )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            MODULE.read_sources(path)

    def test_empty_log_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "no nonlinear"):
            MODULE.read_sources(self.write("noise\n"))


if __name__ == "__main__":
    unittest.main()
