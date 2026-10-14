#!/usr/bin/env python3
"""Focused tests for the bounded case-10173 registration-ledger generator."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name(
    "generate-nl-case10173-registration-ledger.py"
)
SPEC = importlib.util.spec_from_file_location("case10173_ledger", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RegistrationLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.data = self.root / "data"
        self.output = self.root / "output"
        self.data.mkdir()
        self.original_cell_count = MODULE.CELL_COUNT
        MODULE.CELL_COUNT = 33
        for start, count in ((0, 16), (16, 16), (32, 1)):
            item = MODULE.names(start, count)
            identifier = item["identifier"]
            prefix = f"registered_case10173_historical_chunk_{identifier}"
            (self.data / item["data_file"]).write_text(
                "\n".join(
                    (
                        f'Theory {item["data_theory"]}',
                        f"Definition {prefix}_ceqs_def:",
                        f"Definition {prefix}_cexp_def:",
                        f"Definition {prefix}_result_def:",
                        "(* UTF-8 HOL quotation smoke test: «payload» *)",
                    )
                )
                + "\n",
                encoding="utf-8",
            )

    def tearDown(self) -> None:
        MODULE.CELL_COUNT = self.original_cell_count
        self.temporary.cleanup()

    def test_complete_contiguous_ledger(self) -> None:
        manifest = MODULE.generate(self.data, self.output)
        self.assertEqual(manifest["cell_count"], 33)
        self.assertEqual(manifest["chunk_count"], 3)
        self.assertEqual(manifest["final_chunk_size"], 1)
        self.assertEqual(
            [(chunk["start"], chunk["end"]) for chunk in manifest["chunks"]],
            [(0, 16), (16, 32), (32, 33)],
        )
        self.assertTrue((self.output / "ledger-manifest.json").is_file())
        self.assertEqual(
            len(list(self.output.glob("*EvalScript.sml"))), 3
        )

    def test_missing_chunk_fails_closed(self) -> None:
        (self.data / MODULE.names(16, 16)["data_file"]).unlink()
        with self.assertRaisesRegex(ValueError, "missing exported data theory"):
            MODULE.generate(self.data, self.output)

    def test_identity_drift_fails_closed(self) -> None:
        path = self.data / MODULE.names(0, 16)["data_file"]
        path.write_text("Theory Wrong\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "data theory identity drift"):
            MODULE.generate(self.data, self.output)

    def test_unexpected_chunk_fails_closed(self) -> None:
        unexpected = self.data / MODULE.names(48, 1)["data_file"]
        unexpected.write_text("Theory Unexpected\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "data ledger membership drift"):
            MODULE.generate(self.data, self.output)


if __name__ == "__main__":
    unittest.main()
