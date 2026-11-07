#!/usr/bin/env python3
"""Focused tests for summarize-nl-urban-certificate-inventory.py."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name(
    "summarize-nl-urban-certificate-inventory.py"
)
SPEC = importlib.util.spec_from_file_location(
    "nl_urban_certificate_inventory", SCRIPT
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def record_text(source_id: str = "prep-a", leaf_index: int = 2) -> str:
    return "\n".join(
        [
            "pass = 1 (pass_raw = 1)",
            "mono = 0",
            "glue = 0 (glue_convex = 0)",
            "pass_mono = 0",
            f"Verifying: 7:  7,({source_id},{leaf_index})",
            "pass = 3 (pass_raw = 1)",
            "mono = 2",
            "glue = 2 (glue_convex = 1)",
            "pass_mono = 1",
            f"Time  7,({source_id},{leaf_index}): 12.5",
        ]
    )


class UrbanCertificateInventoryTest(unittest.TestCase):
    def test_parses_record_and_ignores_startup_stats(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "out" / "stdout"
            path.parent.mkdir()
            path.write_text(record_text() + "\n", encoding="utf-8")
            records = MODULE.read_records(Path(directory))
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual((record.source_id, record.leaf_index), ("prep-a", 2))
        self.assertEqual(record.numerical_terminals, 4)
        self.assertEqual(record.topology_constructors, 8)
        self.assertEqual(record.historical_total_seconds, 12.5)

    def test_rejects_identity_drift(self) -> None:
        text = record_text().replace("Time  7,(prep-a,2)", "Time  7,(prep-b,2)")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stdout"
            path.write_text(text + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "identity drift"):
                MODULE.read_records(Path(directory))

    def test_rejects_incomplete_record(self) -> None:
        text = record_text().replace("mono = 2\n", "")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stdout"
            path.write_text(text + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "incomplete verifier record"):
                MODULE.read_records(Path(directory))

    def test_closed_constant_has_zero_certificate_counts(self) -> None:
        text = "\n".join(
            [
                "Verifying: 9:  9,(prep-constant,0)",
                "Time  9,(prep-constant,0): 0.125",
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stdout"
            path.write_text(text + "\n", encoding="utf-8")
            records = MODULE.read_records(Path(directory))
        self.assertEqual(records[0].numerical_terminals, 0)
        self.assertEqual(records[0].topology_constructors, 0)


if __name__ == "__main__":
    unittest.main()
