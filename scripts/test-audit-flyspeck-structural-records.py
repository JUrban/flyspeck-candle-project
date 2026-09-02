#!/usr/bin/python3

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit-flyspeck-structural-records.py")
SPEC = importlib.util.spec_from_file_location("record_audit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class StructuralRecordAuditTests(unittest.TestCase):
    def test_records_mutability_and_uses(self) -> None:
        source = br'''
          (* type fake = { ignored : int } *)
          module M = struct
            type t = { a : int; mutable b : string }
            let x = { a = 1; b = "x.y <- fake" }
            let y = { x with a = 2 }
            let z = x.a
            let _ = x.b <- "q"
            type u = C of { q : int }
            let c = C { q = 1 }
            let d = Other.value
          end
        '''
        record = AUDIT.audit_source(source, 7, "fixture:m")
        self.assertEqual(len(record["structural_types"]), 1)
        structural = record["structural_types"][0]
        self.assertEqual(structural["type_name"], "t")
        self.assertEqual(structural["module_path"], ["M"])
        self.assertEqual(
            structural["fields"],
            [{"name": "a", "mutable": False}, {"name": "b", "mutable": True}],
        )
        self.assertEqual(
            [(use["kind"], use.get("field"), use.get("fields")) for use in record["uses"]],
            [
                ("construction", None, ["a", "b"]),
                ("update", None, ["a"]),
                ("projection", "a", None),
                ("assignment", "b", None),
            ],
        )

    def test_mutually_recursive_types_and_duplicate_labels(self) -> None:
        first = AUDIT.audit_source(
            b"type t = { a : int } and u = { a : string; c : bool };;",
            0, "fixture:first",
        )
        second = AUDIT.audit_source(
            b"module N = struct type v = { a : int } end;;",
            1, "fixture:second",
        )
        totals = AUDIT.aggregate([first, second])
        self.assertEqual(totals["structural_type_count"], 3)
        self.assertEqual(totals["field_declaration_count"], 4)
        self.assertEqual(totals["duplicate_field_label_count"], 1)
        duplicate = totals["duplicate_field_labels"][0]
        self.assertEqual(duplicate["module_path"], [])
        self.assertEqual(duplicate["field"], "a")
        self.assertEqual(len(duplicate["owners"]), 2)

    def test_strings_comments_and_constructor_records_are_excluded(self) -> None:
        source = br'''
          let s = "{ fake = x }.bad"
          (* nested (* { fake : int } *) comment *)
          type t = C of { q : int }
          let x = C { q = 1 }
          let y = Module.value
        '''
        record = AUDIT.audit_source(source, 0, "fixture:excluded")
        self.assertEqual(record["structural_types"], [])
        self.assertEqual(record["uses"], [])


if __name__ == "__main__":
    unittest.main()
