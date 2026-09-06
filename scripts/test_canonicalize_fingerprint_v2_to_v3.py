#!/usr/bin/env python3
"""Focused tests for the diagnostic structural V2-to-V3 transformer."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parent))
import canonicalize_fingerprint_v2_to_v3 as canonical


def node(tag: str, *fields: bytes) -> bytes:
    return canonical.encode_node(tag.encode("ascii"), fields)


def list_node(*items: bytes) -> bytes:
    return node("list", *items)


def type_variable(name: str) -> bytes:
    return node("type-variable", name.encode("ascii"))


def type_application(name: str, *arguments: bytes) -> bytes:
    return node("type-application", name.encode("ascii"), list_node(*arguments))


def free_variable(name: str, ty: bytes) -> bytes:
    return node("free-variable", name.encode("ascii"), ty)


def bound_variable(index: int, ty: bytes) -> bytes:
    return node("bound-variable", str(index).encode("ascii"), ty)


def constant(name: str, ty: bytes) -> bytes:
    return node("constant", name.encode("ascii"), ty)


def combination(operator: bytes, operand: bytes) -> bytes:
    return node("combination", operator, operand)


def abstraction(ty: bytes, body: bytes) -> bytes:
    return node("abstraction", ty, body)


def theorem(hypotheses: list[bytes], conclusion: bytes) -> bytes:
    return node("theorem", list_node(*sorted(hypotheses)), conclusion)


def make_capture(offset: int, ordinary_name: str = "ordinary") -> canonical.Capture:
    generated_type = type_variable(f"?{offset + 1}")
    second_type = type_variable(f"?{offset + 4}")
    function_type = type_application("fun", generated_type, second_type)
    anonymous_constant_name = f"_{offset + 9}"
    term_constants = list_node(
        node("term-constant-declaration", b"T", function_type),
        node("term-constant-declaration",
             anonymous_constant_name.encode("ascii"), generated_type),
    )
    generated_free = free_variable(f"_{offset + 20}", generated_type)
    named_free = free_variable(ordinary_name, second_type)
    conclusion = combination(
        constant(anonymous_constant_name, function_type),
        abstraction(second_type, bound_variable(0, second_type)),
    )
    definition = theorem([generated_free], conclusion)
    axiom = theorem([], named_free)
    type_constants = list_node(
        node("type-constant-declaration", b"bool", b"0"))
    definitions = list_node(definition)
    global_axioms = list_node(axiom)
    kernel_state = node(
        "kernel-state", type_constants, term_constants,
        definitions, global_axioms)
    state = canonical.StateRecord(
        kernel_state=kernel_state,
        type_constants=type_constants,
        term_constants=term_constants,
        definitions=definitions,
        global_axioms=global_axioms,
        type_constant_count=1,
        term_constant_count=2,
        definition_count=1,
        global_axiom_count=1,
    )
    target = theorem([generated_free], conclusion)
    return canonical.Capture((canonical.TheoremRecord(
        name=b"TARGET",
        theorem=target,
        hypotheses=canonical.parse_node(target).fields[0],
        conclusion=canonical.parse_node(target).fields[1],
        global_axioms=global_axioms,
        hypothesis_count=1,
        global_axiom_count=1,
    ),), state)


class CanonicalWireTest(unittest.TestCase):
    def test_node_round_trip(self):
        wire = node("sample", b"", b"abc", node("child", b"value"))
        self.assertEqual(canonical.parse_node(wire).encode(), wire)

    def test_rejects_noncanonical_or_truncated_fields(self):
        for wire in (b"01:x1:0", b"1:x1:1", b"1:x1:q"):
            with self.subTest(wire=wire):
                with self.assertRaises(canonical.WireError):
                    canonical.parse_node(wire)

    def test_generated_offsets_canonicalize_identically(self):
        left = canonical.canonicalize_capture(make_capture(10))
        right = canonical.canonicalize_capture(make_capture(900))
        self.assertEqual(
            canonical.capture_record_lines(left),
            canonical.capture_record_lines(right),
        )

    def test_ordinary_free_name_remains_significant(self):
        left = canonical.canonicalize_capture(make_capture(10, "left"))
        right = canonical.canonicalize_capture(make_capture(10, "right"))
        self.assertNotEqual(
            canonical.capture_record_lines(left),
            canonical.capture_record_lines(right),
        )

    def test_reserved_name_collision_is_rejected(self):
        with self.assertRaises(canonical.WireError):
            canonical.canonicalize_capture(
                make_capture(10, "_CANDLE_GENERATED_VARIABLE_0"))

    def test_kernel_component_disagreement_is_rejected(self):
        capture = make_capture(10)
        state = capture.state
        bad_state = canonical.StateRecord(
            **{**state.__dict__, "definitions": list_node()})
        with self.assertRaises(canonical.WireError):
            canonical.canonicalize_state(bad_state)

    def test_redundant_theorem_field_disagreement_is_rejected(self):
        capture = make_capture(10)
        record = capture.theorems[0]
        bad = canonical.TheoremRecord(
            **{**record.__dict__, "conclusion": free_variable(
                "different", type_application("bool"))})
        with self.assertRaises(canonical.WireError):
            canonical.canonicalize_capture(
                canonical.Capture((bad,), capture.state))


if __name__ == "__main__":
    unittest.main()
