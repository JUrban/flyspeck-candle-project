#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest


SCRIPT = pathlib.Path(__file__).with_name(
    "summarize-nl-stock-projection-timing.py"
)
SPEC = importlib.util.spec_from_file_location("timing_summary", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class TimingSummaryTest(unittest.TestCase):
    def test_complete_phase_summary(self) -> None:
        markers = [
            "CANDLE_RESTORE_INPUT_ACK nonce=test",
            "CANDLE_NL_STOCK_PROJECTION_CELLS|preparation|begin",
            "CANDLE_NL_STOCK_PROJECTION_CELLS_OK",
            "CANDLE_NL_STOCK_PROJECTION_REPAIRED_PLAN_OK",
            "CANDLE_NL_STOCK_PROJECTION_COMPLETE|complete-check|begin",
            "CANDLE_CERT_PROFILE phase=variable-complete-certificate-encoding-begin",
            "CANDLE_CERT_PROFILE phase=variable-complete-certificate-encoding-end",
            "CANDLE_CERT_PROFILE phase=variable-complete-validation-begin",
            "CANDLE_CERT_PROFILE phase=variable-complete-validation-end",
            "CANDLE_CERT_PROFILE phase=variable-complete-compute-begin",
            "CANDLE_CERT_PROFILE phase=variable-complete-compute-end",
            "CANDLE_CERT_PROFILE phase=variable-complete-handoff-begin",
            "CANDLE_CERT_PROFILE phase=variable-complete-handoff-end",
            "CANDLE_NL_STOCK_PROJECTION_COMPLETE|complete-check|end",
            "CANDLE_NL_STOCK_PROJECTION_COMPLETE|root-handoff|begin",
            "CANDLE_CERT_PROFILE phase=variable-complete-validation-begin",
            "CANDLE_CERT_PROFILE phase=variable-complete-validation-end",
            "CANDLE_CERT_PROFILE phase=variable-complete-handoff-begin",
            "CANDLE_CERT_PROFILE phase=variable-complete-handoff-end",
            "CANDLE_NL_STOCK_PROJECTION_COMPLETE|root-handoff|end",
            "CANDLE_NL_STOCK_PROJECTION_COMPLETE|reconstruction|begin",
            "CANDLE_NL_STOCK_PROJECTION_COMPLETE|reconstruction|end",
            "CANDLE_NL_STOCK_PROJECTION_COMPLETE_OK",
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root / "stock").mkdir()
            (root / "timing.receipt").write_text(
                "\n".join(
                    [
                        "clock_ticks_per_second=100",
                        "source_id=prep-1395142356",
                        "parameter_index=3",
                        "original_cells=521",
                        "repaired_cells=534",
                        "token_items=1067",
                        "pinned_cpu=110",
                        "theorem_digest=ad47952de83b1c56748556d69c4e1cb0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (root / "stock" / "input-probe.receipt").write_text(
                "restore_to_repl_ready_seconds=109.5\n", encoding="utf-8"
            )
            (root / "stock.time").write_text(
                """\
\tUser time (seconds): 20.00
\tSystem time (seconds): 2.00
\tElapsed (wall clock) time (h:mm:ss or m:ss): 0:24.00
\tMaximum resident set size (kbytes): 18000000
\tSwaps: 0
\tExit status: 0
""",
                encoding="utf-8",
            )
            rows = ["utc_nanoseconds\tprocess_tree_cpu_ticks\tmarker"]
            rows.extend(
                f"{index * 1_000_000_000}\t{index * 100}\t{marker}"
                for index, marker in enumerate(markers)
            )
            (root / "stock.phases.tsv").write_text(
                "\n".join(rows) + "\n", encoding="utf-8"
            )

            result = MODULE.summarize(root)
            self.assertEqual(result["status"], 0)
            self.assertEqual(result["repaired_cells"], 534)
            self.assertEqual(result["gnu_time"]["cpu_seconds"], 22.0)
            self.assertEqual(result["phases"]["post_restore_total"]["cpu_seconds"], 22.0)
            self.assertEqual(result["phases"]["kernel_compute"]["wall_seconds"], 1.0)
            self.assertEqual(result["phases"]["root_validation"]["cpu_seconds"], 1.0)
            self.assertEqual(result["restore_to_ready_seconds"], 109.5)

    def test_elapsed_formats(self) -> None:
        self.assertEqual(MODULE.parse_elapsed("10:25.57"), 625.57)
        self.assertEqual(MODULE.parse_elapsed("1:02:03"), 3723.0)


if __name__ == "__main__":
    unittest.main()
