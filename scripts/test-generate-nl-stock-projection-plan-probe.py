#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


SCRIPT = pathlib.Path(__file__).with_name(
    "generate-nl-stock-projection-plan-probe.py"
)
SPEC = importlib.util.spec_from_file_location("projection_generator", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ProjectionGeneratorTest(unittest.TestCase):
    def test_certificate_subclass_counts_are_not_double_counted(self) -> None:
        canonical = MODULE.CANONICAL.read_text(encoding="utf-8")
        self.assertIn(
            "string_of_int (stats.pass + stats.pass_mono)", canonical
        )
        self.assertIn(
            "!precision_leaves <> stats.pass + stats.pass_mono", canonical
        )
        self.assertIn(
            "!precision_glues <> stats.glue", canonical
        )
        self.assertNotIn("stats.pass + stats.pass_raw", canonical)
        self.assertNotIn("stats.glue + stats.glue_convex", canonical)

    def test_opaque_domain_endpoints_fail_before_float_conversion(self) -> None:
        canonical = MODULE.CANONICAL.read_text(encoding="utf-8")
        preflight = canonical.index("ensure_evaluable_endpoint")
        conversion = canonical.index("M_verifier_main.mk_float_domain")
        self.assertLess(preflight, conversion)
        self.assertIn("opaque \" ^ side ^", canonical)
        self.assertIn("Eval_interval.eval_interval_fun", canonical)

    def test_proved_hminus_interval_is_registered(self) -> None:
        canonical = MODULE.CANONICAL.read_text(encoding="utf-8")
        self.assertIn(
            "Candle_nl_stock_projection_hminus_setup.hminus_interval", canonical
        )

    def test_plan_uses_the_structural_scanner_definition_prefix(self) -> None:
        canonical = MODULE.CANONICAL.read_text(encoding="utf-8")
        self.assertIn(
            "let projection_expanded_defs =\n"
            "  candle_direct_flyspeck_defs @\n"
            "  Break_case_exec.nonlin_rewrites @",
            canonical,
        )

    def test_exact_two_field_instantiation(self) -> None:
        canonical = (
            "module Test = struct\n"
            'let source_id = "prep-1395142356";;\n'
            "let parameter_index = 3;;\n"
            "let retained = 7;;\n"
            "end;;\n"
        )
        generated = MODULE.instantiate(
            canonical, 'prep-example "quoted" \\ path', 23
        )
        self.assertIn(
            'let source_id = "prep-example \\"quoted\\" \\\\ path";;',
            generated,
        )
        self.assertIn("let parameter_index = 23;;", generated)
        self.assertIn("let retained = 7;;", generated)
        self.assertNotIn('let source_id = "prep-1395142356";;', generated)

    def test_rejects_placeholder_drift(self) -> None:
        with self.assertRaisesRegex(ValueError, "placeholder drift"):
            MODULE.instantiate("let parameter_index = 3;;\n", "prep-x", 0)

    def test_rejects_invalid_identity_or_index(self) -> None:
        canonical = (
            'let source_id = "prep-1395142356";;\n'
            "let parameter_index = 3;;\n"
        )
        with self.assertRaisesRegex(ValueError, "one non-NUL line"):
            MODULE.instantiate(canonical, "prep-x\ny", 0)
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            MODULE.instantiate(canonical, "prep-x", -1)


if __name__ == "__main__":
    unittest.main()
