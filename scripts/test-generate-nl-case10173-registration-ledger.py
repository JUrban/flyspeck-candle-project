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
                        f"  {prefix}_ceqs =",
                        "    [(«shared»,([],Num 1))]",
                        "End",
                        f"Definition {prefix}_cexp_def:",
                        f"  {prefix}_cexp : compute_exp =",
                        f"    Num {start}",
                        "End",
                        f"Definition {prefix}_result_def:",
                        f"  {prefix}_result : cv =",
                        "    Num 1",
                        "End",
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
        self.assertEqual(manifest["aggregate"]["group_count"], 1)
        self.assertEqual(
            manifest["aggregate"]["authority"], "exact_registered_ledger"
        )
        self.assertFalse(
            manifest["aggregate"]["reusable_packed_object_refinement"]
        )
        self.assertEqual(manifest["aggregate"]["groups"][0]["chunk_count"], 3)
        self.assertRegex(manifest["shared_ceqs_body_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            [(chunk["start"], chunk["end"]) for chunk in manifest["chunks"]],
            [(0, 16), (16, 32), (32, 33)],
        )
        self.assertTrue((self.output / "ledger-manifest.json").is_file())
        self.assertEqual(
            len(list(self.output.glob("*EvalScript.sml"))), 5
        )
        first_eval = (
            self.output / MODULE.names(0, 16)["eval_file"]
        ).read_text(encoding="ascii")
        self.assertIn(
            f'Theory {MODULE.names(0, 16)["eval_theory"]}[no_sig_docs]',
            first_eval,
        )
        group = MODULE.group_names(0)
        group_eval = (self.output / group["eval_file"]).read_text(
            encoding="ascii"
        )
        self.assertIn(f'Theory {group["eval_theory"]}[no_sig_docs]', group_eval)
        self.assertIn(
            "registered_case10173_historical_chunk_at32_count1_pure_eval",
            group_eval,
        )
        ledger_eval = (
            self.output / f"{MODULE.LEDGER_EVAL_THEORY}Script.sml"
        ).read_text(encoding="ascii")
        ledger_fast = (
            self.output / f"{MODULE.LEDGER_FAST_THEORY}Script.sml"
        ).read_text(encoding="ascii")
        ledger_packed_fast = (
            self.output / f"{MODULE.LEDGER_PACKED_FAST_THEORY}Script.sml"
        ).read_text(encoding="ascii")
        self.assertIn(
            "compute_eval_pure ("
            + MODULE.suc_fuel(
                MODULE.suc_fuel("100000", MODULE.GROUP_DEPTH),
                MODULE.LEDGER_DEPTH,
            )
            + ")",
            ledger_eval,
        )
        self.assertIn("PURE_REWRITE_TAC", group_eval)
        self.assertIn("_pair_SOME", group_eval)
        self.assertIn("_shared_value", group_eval)
        self.assertIn("compute_fast_eval_ok", ledger_fast)
        self.assertIn(
            "qexists_tac `"
            + MODULE.suc_fuel(
                MODULE.suc_fuel("100000", MODULE.GROUP_DEPTH),
                MODULE.LEDGER_DEPTH,
            )
            + "`",
            ledger_fast,
        )
        self.assertIn(
            "bounded_packed_chars_case10173_full_check",
            ledger_packed_fast,
        )
        self.assertRegex(
            manifest["aggregate"]["fast_sha256"], r"^[0-9a-f]{64}$"
        )
        self.assertRegex(
            manifest["aggregate"]["packed_fast_sha256"],
            r"^[0-9a-f]{64}$",
        )

    def test_suc_fuel_preserves_structural_depth(self) -> None:
        self.assertEqual(
            MODULE.suc_fuel("100000", 3),
            "SUC (SUC (SUC (100000)))",
        )

    def test_balanced_pair_has_uniform_depth_and_fails_on_overflow(self) -> None:
        rendered = MODULE.balanced_pair(["A", "B", "C"], 2, "P")
        self.assertEqual(rendered, "Pair (Pair (A) (B)) (Pair (C) (P))")
        with self.assertRaisesRegex(ValueError, "too many balanced-tree leaves"):
            MODULE.balanced_pair(["A", "B", "C"], 1, "P")

    def test_missing_chunk_fails_closed(self) -> None:
        (self.data / MODULE.names(16, 16)["data_file"]).unlink()
        with self.assertRaisesRegex(ValueError, "missing exported data theory"):
            MODULE.generate(self.data, self.output)

    def test_normalized_shared_equations_are_emitted_once(self) -> None:
        manifest = MODULE.generate(
            self.data, self.output, normalize_shared_ceqs=True
        )
        self.assertTrue(manifest["normalized_shared_ceqs"])
        self.assertIsNotNone(manifest["shared_files"])
        self.assertTrue(
            (self.output / f"{MODULE.SHARED_DATA_THEORY}Script.sml").is_file()
        )
        normalized_data = (
            self.output / MODULE.names(16, 16)["data_file"]
        ).read_text(encoding="utf-8")
        self.assertIn(
            f"    {MODULE.SHARED_CEQS}\nEnd", normalized_data
        )
        self.assertNotIn("«shared»", normalized_data)
        normalized_eval = (
            self.output / MODULE.names(16, 16)["eval_file"]
        ).read_text(encoding="ascii")
        self.assertIn(MODULE.SHARED_EVAL_THEORY, normalized_eval)
        self.assertNotIn(
            f"cv_trans registered_case10173_historical_chunk_at16_count16_ceqs_def",
            normalized_eval,
        )

    def test_normalization_rejects_in_place_output(self) -> None:
        with self.assertRaisesRegex(ValueError, "must differ"):
            MODULE.generate(
                self.data, self.data, normalize_shared_ceqs=True
            )

    def test_identity_drift_fails_closed(self) -> None:
        path = self.data / MODULE.names(0, 16)["data_file"]
        path.write_text("Theory Wrong\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "data theory identity drift"):
            MODULE.generate(self.data, self.output)

    def test_equation_environment_drift_fails_closed(self) -> None:
        item = MODULE.names(16, 16)
        path = self.data / item["data_file"]
        source = path.read_text(encoding="utf-8")
        path.write_text(
            source.replace("[(«shared»,([],Num 1))]", "[(«changed»,([],Num 1))]"),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "equation environment drift"):
            MODULE.generate(self.data, self.output)

    def test_unexpected_chunk_fails_closed(self) -> None:
        unexpected = self.data / MODULE.names(48, 1)["data_file"]
        unexpected.write_text("Theory Unexpected\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "data ledger membership drift"):
            MODULE.generate(self.data, self.output)


if __name__ == "__main__":
    unittest.main()
