#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_script(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


LITERAL = load_script(
    "fast_nl_literal_closure_test",
    "scripts/audit-fast-nl-support-source-closure.py",
)
MODULE = load_script(
    "fast_nl_module_closure_test",
    "scripts/audit-fast-nl-support-module-closure.py",
)


class FastNlSupportClosureTests(unittest.TestCase):
    def test_flyspeck_needs_is_a_literal_loader_edge(self) -> None:
        source = '''
          flyspeck_needs "nonlinear/prep.hl";;
          (* flyspeck_needs "nonlinear/commented.hl";; *)
        '''
        stripped = LITERAL.strip_comments(source)
        self.assertEqual(
            LITERAL.LOAD_RE.findall(stripped), ["nonlinear/prep.hl"]
        )

    def test_indented_module_provider_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = pathlib.Path(directory) / "provider.ml"
            source.write_text(
                " module Functional_equation = struct\nend;;\n",
                encoding="utf-8",
            )
            providers, references, loads, dynamic = MODULE.source_facts(source)
        self.assertEqual(providers, {"Functional_equation"})
        self.assertEqual(references, set())
        self.assertEqual(loads, [])
        self.assertEqual(dynamic, [])

    def test_v664_normalization_is_exact(self) -> None:
        mapping, mismatches = MODULE.parse_normalization()
        canonical = pathlib.Path(
            "/project/flyspeck-candle-runs/"
            "v352-full-boundary-materialization-heap16-dev-005/snapshot/"
            "flyspeck/text_formalization/nonlinear/break_case_exec.hl"
        ).resolve()
        expected = pathlib.Path(
            "/project/worktrees/flyspeck-direct-action296-643bfd12/"
            "text_formalization/nonlinear/break_case_exec.hl"
        ).resolve()
        self.assertEqual(mismatches, [])
        self.assertEqual(mapping[canonical], expected)


if __name__ == "__main__":
    unittest.main()
