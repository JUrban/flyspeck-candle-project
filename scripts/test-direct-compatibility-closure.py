#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "direct_compatibility_closure", SCRIPT_DIR / "direct-compatibility-closure.py"
)
closure = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = closure
assert spec.loader is not None
spec.loader.exec_module(closure)


class DirectCompatibilityClosureTests(unittest.TestCase):
    def fixture(self):
        manifest = {
            "source_nodes": {
                "candle:a.ml": {"sha256": "a" * 64},
                "flyspeck:b.hl": {
                    "sha256": "b" * 64,
                    "execution_normalization": {"id": "NORM-1"},
                },
            },
            "build_strata": [{"name": "base"}, {"name": "final"}],
            "source_node_strata": {
                "candle:a.ml": ["base", "final"],
                "flyspeck:b.hl": ["final"],
            },
        }
        findings = [
            {
                "category": "open.declaration", "repository": "candle",
                "source_path": "a.ml", "source_sha256": "a" * 64,
                "finding_id": "CF-" + "1" * 20, "lexeme": "open A",
                "location": {"line": 1, "column": 1, "end_line": 1, "end_column": 7},
            },
            {
                "category": "pointer_equality.infix_use", "repository": "flyspeck",
                "source_path": "b.hl", "source_sha256": "b" * 64,
                "finding_id": "CF-" + "2" * 20, "lexeme": "==",
                "location": {"line": 2, "column": 3, "end_line": 2, "end_column": 5},
            },
            {
                "category": "ffi.custom_call", "repository": "candle",
                "source_path": "outside.ml", "source_sha256": "c" * 64,
                "finding_id": "CF-" + "3" * 20, "lexeme": "customFFI",
                "location": {"line": 3, "column": 1, "end_line": 3, "end_column": 10},
            },
        ]
        manifest_raw = json.dumps(manifest, sort_keys=True).encode()
        findings_raw = b"".join(
            json.dumps(item, sort_keys=True).encode() + b"\n" for item in findings
        )
        return manifest_raw, manifest, findings_raw, findings

    def test_exact_projection_and_explicit_zeroes(self):
        document = closure.project(*self.fixture())
        self.assertEqual(document["selected"]["finding_count"], 2)
        self.assertEqual(document["selected"]["source_files_with_findings"], 2)
        self.assertEqual(document["selected"]["non_dopen_review_occurrences"], 1)
        self.assertEqual(document["selected"]["by_category"]["ffi.custom_call"], 0)
        self.assertEqual(document["selected"]["by_earliest_stratum"], {
            "base": 1, "final": 1,
        })
        self.assertEqual(document["manifest"]["normalization_sources"], [
            "flyspeck:b.hl"
        ])

    def test_stale_selected_source_is_rejected(self):
        manifest_raw, manifest, findings_raw, findings = self.fixture()
        findings[0]["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "stale selected inventory"):
            closure.project(manifest_raw, manifest, findings_raw, findings)


if __name__ == "__main__":
    unittest.main()
