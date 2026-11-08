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
