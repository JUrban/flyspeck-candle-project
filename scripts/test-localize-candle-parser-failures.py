#!/usr/bin/python3

import importlib.util
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "localize_candle_parser_failures",
    HERE / "localize-candle-parser-failures.py",
)
subject = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = subject
SPEC.loader.exec_module(subject)


class ParserFailureLocalizerTests(unittest.TestCase):
    def test_lexical_events_ignore_nested_comments_strings_and_chars(self) -> None:
        source = (
            b'module X = struct\n'
            b'let a = ";; struct end";;\n'
            b"let c = '`';; (* ;; struct (* end *) *)\n"
            b'begin 1;; 2 end;;\n'
            b'end;;\n'
        )
        events = subject.lexical_events(source)
        semis = [event for event in events if event.kind == "semis"]
        self.assertEqual([event.depth for event in semis], [1, 1, 2, 1, 0])
        self.assertEqual(
            [(event.value, event.depth) for event in events if event.kind == "word"
             and event.value in {"module", "struct", "begin", "end"}],
            [("module", 0), ("struct", 0), ("begin", 1), ("end", 2), ("end", 1)],
        )

    def test_outer_structure_is_split_at_its_item_boundaries(self) -> None:
        source = (
            b"module X = struct\n"
            b"let a = 1;;\n"
            b"module Y = struct let y = 2;; end;;\n"
            b"let b = 3;;\n"
            b"end;;\n"
        )
        chunks = subject.candidate_chunks(source)
        self.assertEqual(len(chunks), 3)
        self.assertIn(b"let a", chunks[0][2])
        self.assertIn(b"module Y", chunks[1][2])
        self.assertIn(b"let b", chunks[2][2])

    def test_signature_before_structure_selects_implementation_body(self) -> None:
        source = (
            b"module X : sig val x : int end = struct\n"
            b"let x = 1;; let y = 2;;\n"
            b"end;;\n"
        )
        chunks = subject.candidate_chunks(source)
        self.assertEqual([chunk[2].strip() for chunk in chunks], [
            b"let x = 1;;", b"let y = 2;;",
        ])

    def test_top_level_source_splits_without_module_wrapper(self) -> None:
        chunks = subject.candidate_chunks(b"type t = A;;\nlet x = 1;;\n")
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0][2].strip(), b"type t = A;;")
        self.assertEqual(chunks[1][2].strip(), b"let x = 1;;")

    def test_ddmin_lines_preserves_interesting_predicate(self) -> None:
        source = b"comment\nkeep failure\nmore\n"
        minimized = subject.ddmin_lines(
            source, lambda candidate: b"failure" in candidate,
        )
        self.assertEqual(minimized, b"keep failure\n")


if __name__ == "__main__":
    unittest.main()
