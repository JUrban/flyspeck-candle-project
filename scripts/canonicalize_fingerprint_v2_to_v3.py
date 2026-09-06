#!/usr/bin/env python3
"""Canonicalize approved structural V2 fingerprint wires to candidate V3.

This module is deliberately a wire transformer, not an authority migration.
Callers must first authenticate the V2 transcript against its existing
approval.  The output may then be used as diagnostic V3 comparison data; it
does not inherit the approval of its input.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable


V2_THEOREM_MARKER = b"CANDLE_FINGERPRINT_V2"
V2_STATE_MARKER = b"CANDLE_STATE_FINGERPRINT_V2"
V3_THEOREM_MARKER = b"CANDLE_FINGERPRINT_V3"
V3_STATE_MARKER = b"CANDLE_STATE_FINGERPRINT_V3"
LOWER_HEX_RE = re.compile(rb"(?:[0-9a-f]{2})*")
DECIMAL_RE = re.compile(rb"(?:0|[1-9][0-9]*)")


class WireError(ValueError):
    """A structural fingerprint wire is malformed or ambiguous."""


@dataclass(frozen=True)
class Node:
    tag: bytes
    fields: tuple[bytes, ...]

    def encode(self) -> bytes:
        return (
            encode_field(self.tag)
            + encode_field(str(len(self.fields)).encode("ascii"))
            + b"".join(encode_field(field) for field in self.fields)
        )


@dataclass(frozen=True)
class TheoremRecord:
    name: bytes
    theorem: bytes
    hypotheses: bytes
    conclusion: bytes
    global_axioms: bytes
    hypothesis_count: int
    global_axiom_count: int


@dataclass(frozen=True)
class StateRecord:
    kernel_state: bytes
    type_constants: bytes
    term_constants: bytes
    definitions: bytes
    global_axioms: bytes
    type_constant_count: int
    term_constant_count: int
    definition_count: int
    global_axiom_count: int


@dataclass(frozen=True)
class Capture:
    theorems: tuple[TheoremRecord, ...]
    state: StateRecord


def encode_field(value: bytes) -> bytes:
    return str(len(value)).encode("ascii") + b":" + value


def encode_node(tag: bytes, fields: Iterable[bytes]) -> bytes:
    return Node(tag, tuple(fields)).encode()


def _read_field(data: bytes, offset: int, label: str) -> tuple[bytes, int]:
    colon = data.find(b":", offset)
    if colon < 0:
        raise WireError(f"missing field delimiter in {label}")
    length_text = data[offset:colon]
    if DECIMAL_RE.fullmatch(length_text) is None:
        raise WireError(f"noncanonical field length in {label}")
    length = int(length_text)
    start = colon + 1
    end = start + length
    if end > len(data):
        raise WireError(f"truncated field in {label}")
    return data[start:end], end


def parse_node(data: bytes, label: str = "node") -> Node:
    tag, offset = _read_field(data, 0, f"{label} tag")
    count_text, offset = _read_field(data, offset, f"{label} field count")
    if DECIMAL_RE.fullmatch(count_text) is None:
        raise WireError(f"noncanonical node field count in {label}")
    fields = []
    for index in range(int(count_text)):
        field, offset = _read_field(data, offset, f"{label} field {index}")
        fields.append(field)
    if offset != len(data):
        raise WireError(f"trailing bytes after {label}")
    return Node(tag, tuple(fields))


def _expect(node: Node, tag: bytes, count: int, label: str) -> None:
    if node.tag != tag or len(node.fields) != count:
        raise WireError(
            f"unexpected {label}: tag={node.tag!r}, fields={len(node.fields)}")


def _list_items(data: bytes, label: str) -> tuple[bytes, ...]:
    node = parse_node(data, label)
    if node.tag != b"list":
        raise WireError(f"{label} is not a list node")
    return node.fields


def _decode_hex(value: bytes, label: str) -> bytes:
    if LOWER_HEX_RE.fullmatch(value) is None:
        raise WireError(f"malformed lowercase hex in {label}")
    return bytes.fromhex(value.decode("ascii"))


def _nonnegative(value: bytes, label: str) -> int:
    if DECIMAL_RE.fullmatch(value) is None:
        raise WireError(f"noncanonical count in {label}")
    return int(value)


def _generated_number(prefix: bytes, value: bytes) -> int | None:
    if not value.startswith(prefix) or len(value) == len(prefix):
        return None
    suffix = value[len(prefix):]
    if not suffix.isdigit():
        return None
    number = int(suffix)
    return number if number > 0 else None


def _generated_ranks(prefix: bytes, values: Iterable[bytes]) -> dict[bytes, int]:
    by_number: dict[int, bytes] = {}
    for value in values:
        number = _generated_number(prefix, value)
        if number is None:
            continue
        previous = by_number.get(number)
        if previous is not None and previous != value:
            raise WireError(
                "ambiguous generated names with equal numeric suffix: "
                f"{previous!r}, {value!r}")
        by_number[number] = value
    return {
        value: rank
        for rank, (_, value) in enumerate(sorted(by_number.items()))
    }


def _canonical_name(value: bytes, prefix: bytes, replacement: bytes,
                    ranks: dict[bytes, int]) -> bytes:
    if _generated_number(prefix, value) is not None:
        try:
            rank = ranks[value]
        except KeyError as error:
            raise WireError(f"generated name missing from rank set: {value!r}") \
                from error
        return replacement + str(rank).encode("ascii")
    suffix = value[len(replacement):] if value.startswith(replacement) else b""
    if suffix and suffix.isdigit():
        raise WireError(f"ordinary name collides with V3 reserved name: {value!r}")
    return value


def _collect_type_names(data: bytes, output: list[bytes], label: str) -> None:
    node = parse_node(data, label)
    if node.tag == b"type-variable":
        _expect(node, b"type-variable", 1, label)
        if _generated_number(b"?", node.fields[0]) is not None:
            output.append(node.fields[0])
        return
    _expect(node, b"type-application", 2, label)
    for index, argument in enumerate(_list_items(node.fields[1], label + " args")):
        _collect_type_names(argument, output, f"{label} argument {index}")


def _transform_type(data: bytes, ranks: dict[bytes, int], label: str) -> bytes:
    node = parse_node(data, label)
    if node.tag == b"type-variable":
        _expect(node, b"type-variable", 1, label)
        name = _canonical_name(
            node.fields[0], b"?", b"?CANDLE_GENERATED_TYPE_", ranks)
        return encode_node(b"type-variable", (name,))
    _expect(node, b"type-application", 2, label)
    arguments = _list_items(node.fields[1], label + " args")
    transformed = [
        _transform_type(argument, ranks, f"{label} argument {index}")
        for index, argument in enumerate(arguments)
    ]
    return encode_node(
        b"type-application",
        (node.fields[0], encode_node(b"list", transformed)),
    )


def _type_ranks(types: Iterable[bytes], label: str) -> dict[bytes, int]:
    names: list[bytes] = []
    for index, data in enumerate(types):
        _collect_type_names(data, names, f"{label} type {index}")
    return _generated_ranks(b"?", names)


def _collect_term_names(data: bytes, type_names: list[bytes],
                        free_names: list[bytes], label: str) -> None:
    node = parse_node(data, label)
    if node.tag == b"free-variable":
        _expect(node, b"free-variable", 2, label)
        if _generated_number(b"_", node.fields[0]) is not None:
            free_names.append(node.fields[0])
        _collect_type_names(node.fields[1], type_names, label + " type")
    elif node.tag == b"bound-variable":
        _expect(node, b"bound-variable", 2, label)
        _nonnegative(node.fields[0], label + " bound index")
        _collect_type_names(node.fields[1], type_names, label + " type")
    elif node.tag == b"constant":
        _expect(node, b"constant", 2, label)
        _collect_type_names(node.fields[1], type_names, label + " type")
    elif node.tag == b"combination":
        _expect(node, b"combination", 2, label)
        _collect_term_names(node.fields[0], type_names, free_names,
                            label + " operator")
        _collect_term_names(node.fields[1], type_names, free_names,
                            label + " operand")
    elif node.tag == b"abstraction":
        _expect(node, b"abstraction", 2, label)
        _collect_type_names(node.fields[0], type_names, label + " binder type")
        _collect_term_names(node.fields[1], type_names, free_names,
                            label + " body")
    else:
        raise WireError(f"unknown term tag in {label}: {node.tag!r}")


def _transform_term(data: bytes, type_ranks: dict[bytes, int],
                    free_ranks: dict[bytes, int],
                    constant_ranks: dict[bytes, int], label: str) -> bytes:
    node = parse_node(data, label)
    if node.tag == b"free-variable":
        _expect(node, b"free-variable", 2, label)
        name = _canonical_name(
            node.fields[0], b"_", b"_CANDLE_GENERATED_VARIABLE_", free_ranks)
        return encode_node(
            b"free-variable",
            (name, _transform_type(node.fields[1], type_ranks, label + " type")),
        )
    if node.tag == b"bound-variable":
        _expect(node, b"bound-variable", 2, label)
        _nonnegative(node.fields[0], label + " bound index")
        return encode_node(
            b"bound-variable",
            (node.fields[0],
             _transform_type(node.fields[1], type_ranks, label + " type")),
        )
    if node.tag == b"constant":
        _expect(node, b"constant", 2, label)
        name = _canonical_name(
            node.fields[0], b"_", b"_CANDLE_GENERATED_CONSTANT_",
            constant_ranks)
        return encode_node(
            b"constant",
            (name, _transform_type(node.fields[1], type_ranks, label + " type")),
        )
    if node.tag == b"combination":
        _expect(node, b"combination", 2, label)
        return encode_node(b"combination", (
            _transform_term(node.fields[0], type_ranks, free_ranks,
                            constant_ranks, label + " operator"),
            _transform_term(node.fields[1], type_ranks, free_ranks,
                            constant_ranks, label + " operand"),
        ))
    if node.tag == b"abstraction":
        _expect(node, b"abstraction", 2, label)
        return encode_node(b"abstraction", (
            _transform_type(node.fields[0], type_ranks, label + " binder type"),
            _transform_term(node.fields[1], type_ranks, free_ranks,
                            constant_ranks, label + " body"),
        ))
    raise WireError(f"unknown term tag in {label}: {node.tag!r}")


def _transform_theorem(data: bytes, constant_ranks: dict[bytes, int],
                       label: str) -> tuple[bytes, bytes, bytes]:
    theorem = parse_node(data, label)
    _expect(theorem, b"theorem", 2, label)
    hypotheses = _list_items(theorem.fields[0], label + " hypotheses")
    conclusion = theorem.fields[1]
    type_names: list[bytes] = []
    free_names: list[bytes] = []
    for index, term in enumerate((*hypotheses, conclusion)):
        _collect_term_names(
            term, type_names, free_names, f"{label} term {index}")
    type_ranks = _generated_ranks(b"?", type_names)
    free_ranks = _generated_ranks(b"_", free_names)
    transformed_hypotheses = sorted(
        _transform_term(term, type_ranks, free_ranks, constant_ranks,
                        f"{label} hypothesis {index}")
        for index, term in enumerate(hypotheses)
    )
    transformed_hypothesis_list = encode_node(
        b"list", transformed_hypotheses)
    transformed_conclusion = _transform_term(
        conclusion, type_ranks, free_ranks, constant_ranks,
        label + " conclusion")
    transformed_theorem = encode_node(
        b"theorem", (transformed_hypothesis_list, transformed_conclusion))
    return (
        transformed_theorem,
        transformed_hypothesis_list,
        transformed_conclusion,
    )


def _generated_constants(term_constants: bytes) -> dict[bytes, int]:
    names = []
    for index, declaration in enumerate(
            _list_items(term_constants, "term constants")):
        node = parse_node(declaration, f"term constant {index}")
        _expect(node, b"term-constant-declaration", 2,
                f"term constant {index}")
        if _generated_number(b"_", node.fields[0]) is not None:
            names.append(node.fields[0])
    return _generated_ranks(b"_", names)


def canonicalize_state(state: StateRecord) -> tuple[StateRecord, dict[bytes, int]]:
    kernel = parse_node(state.kernel_state, "kernel state")
    _expect(kernel, b"kernel-state", 4, "kernel state")
    original_components = (
        state.type_constants, state.term_constants,
        state.definitions, state.global_axioms)
    if kernel.fields != original_components:
        raise WireError("kernel-state fields disagree with component fields")

    type_items = _list_items(state.type_constants, "type constants")
    if len(type_items) != state.type_constant_count:
        raise WireError("type-constant count mismatch")
    for index, declaration in enumerate(type_items):
        _expect(parse_node(declaration, f"type constant {index}"),
                b"type-constant-declaration", 2, f"type constant {index}")
    type_constants = encode_node(b"list", sorted(type_items))

    constant_ranks = _generated_constants(state.term_constants)
    transformed_constants = []
    term_items = _list_items(state.term_constants, "term constants")
    if len(term_items) != state.term_constant_count:
        raise WireError("term-constant count mismatch")
    for index, declaration in enumerate(term_items):
        node = parse_node(declaration, f"term constant {index}")
        _expect(node, b"term-constant-declaration", 2,
                f"term constant {index}")
        ranks = _type_ranks((node.fields[1],), f"term constant {index}")
        transformed_constants.append(encode_node(
            b"term-constant-declaration",
            (_canonical_name(
                node.fields[0], b"_", b"_CANDLE_GENERATED_CONSTANT_",
                constant_ranks),
             _transform_type(node.fields[1], ranks,
                             f"term constant {index} type")),
        ))
    term_constants = encode_node(b"list", sorted(transformed_constants))

    definition_items = _list_items(state.definitions, "definitions")
    if len(definition_items) != state.definition_count:
        raise WireError("definition count mismatch")
    definitions = encode_node(b"list", sorted(
        _transform_theorem(definition, constant_ranks,
                           f"definition {index}")[0]
        for index, definition in enumerate(definition_items)
    ))

    axiom_items = _list_items(state.global_axioms, "global axioms")
    if len(axiom_items) != state.global_axiom_count:
        raise WireError("global-axiom count mismatch")
    global_axioms = encode_node(b"list", sorted(
        _transform_theorem(axiom, constant_ranks, f"axiom {index}")[0]
        for index, axiom in enumerate(axiom_items)
    ))

    kernel_state = encode_node(b"kernel-state", (
        type_constants, term_constants, definitions, global_axioms))
    return StateRecord(
        kernel_state=kernel_state,
        type_constants=type_constants,
        term_constants=term_constants,
        definitions=definitions,
        global_axioms=global_axioms,
        type_constant_count=state.type_constant_count,
        term_constant_count=state.term_constant_count,
        definition_count=state.definition_count,
        global_axiom_count=state.global_axiom_count,
    ), constant_ranks


def validate_capture_structure(capture: Capture) -> None:
    """Validate redundant record structure without changing identifier names."""
    state = capture.state
    kernel = parse_node(state.kernel_state, "kernel state")
    _expect(kernel, b"kernel-state", 4, "kernel state")
    if kernel.fields != (
            state.type_constants, state.term_constants,
            state.definitions, state.global_axioms):
        raise WireError("kernel-state fields disagree with component fields")
    component_counts = (
        (state.type_constants, state.type_constant_count, "type constants"),
        (state.term_constants, state.term_constant_count, "term constants"),
        (state.definitions, state.definition_count, "definitions"),
        (state.global_axioms, state.global_axiom_count, "global axioms"),
    )
    for data, count, label in component_counts:
        if len(_list_items(data, label)) != count:
            raise WireError(f"{label} count mismatch")
    for index, record in enumerate(capture.theorems):
        theorem = parse_node(record.theorem, f"theorem record {index}")
        _expect(theorem, b"theorem", 2, f"theorem record {index}")
        if theorem.fields != (record.hypotheses, record.conclusion):
            raise WireError(
                f"theorem record {index} disagrees with redundant fields")
        if len(_list_items(
                record.hypotheses,
                f"theorem record {index} hypotheses")) != \
                record.hypothesis_count:
            raise WireError(f"theorem record {index} hypothesis count mismatch")
        if (record.global_axioms != state.global_axioms or
                record.global_axiom_count != state.global_axiom_count):
            raise WireError(
                f"theorem record {index} global axioms disagree with state")


def canonicalize_capture(capture: Capture) -> Capture:
    validate_capture_structure(capture)
    state, constant_ranks = canonicalize_state(capture.state)
    theorems = []
    for index, record in enumerate(capture.theorems):
        theorem = parse_node(record.theorem, f"theorem record {index}")
        _expect(theorem, b"theorem", 2, f"theorem record {index}")
        if theorem.fields != (record.hypotheses, record.conclusion):
            raise WireError(
                f"theorem record {index} disagrees with redundant fields")
        if record.global_axioms != capture.state.global_axioms:
            raise WireError(
                f"theorem record {index} global axioms disagree with state")
        if record.global_axiom_count != state.global_axiom_count:
            raise WireError(
                f"theorem record {index} global-axiom count disagrees with state")
        transformed, hypotheses, conclusion = _transform_theorem(
            record.theorem, constant_ranks, f"theorem record {index}")
        if len(_list_items(hypotheses, f"theorem record {index} hypotheses")) != \
                record.hypothesis_count:
            raise WireError(f"theorem record {index} hypothesis count mismatch")
        theorems.append(TheoremRecord(
            name=record.name,
            theorem=transformed,
            hypotheses=hypotheses,
            conclusion=conclusion,
            global_axioms=state.global_axioms,
            hypothesis_count=record.hypothesis_count,
            global_axiom_count=record.global_axiom_count,
        ))
    return Capture(tuple(theorems), state)


def theorem_record_from_fields(fields: list[bytes], label: str) -> TheoremRecord:
    if len(fields) != 8:
        raise WireError(f"{label} has {len(fields)} fields; expected 8")
    return TheoremRecord(
        name=_decode_hex(fields[1], label + " name"),
        theorem=_decode_hex(fields[2], label + " theorem"),
        hypotheses=_decode_hex(fields[3], label + " hypotheses"),
        conclusion=_decode_hex(fields[4], label + " conclusion"),
        global_axioms=_decode_hex(fields[5], label + " global axioms"),
        hypothesis_count=_nonnegative(fields[6], label + " hypothesis count"),
        global_axiom_count=_nonnegative(fields[7], label + " axiom count"),
    )


def state_record_from_fields(fields: list[bytes], label: str) -> StateRecord:
    if len(fields) != 10:
        raise WireError(f"{label} has {len(fields)} fields; expected 10")
    return StateRecord(
        kernel_state=_decode_hex(fields[1], label + " kernel state"),
        type_constants=_decode_hex(fields[2], label + " type constants"),
        term_constants=_decode_hex(fields[3], label + " term constants"),
        definitions=_decode_hex(fields[4], label + " definitions"),
        global_axioms=_decode_hex(fields[5], label + " global axioms"),
        type_constant_count=_nonnegative(fields[6], label + " type count"),
        term_constant_count=_nonnegative(fields[7], label + " constant count"),
        definition_count=_nonnegative(fields[8], label + " definition count"),
        global_axiom_count=_nonnegative(fields[9], label + " axiom count"),
    )


def read_v2_capture(path: Path, expected_names: Iterable[str]) -> Capture:
    expected = [name.encode("ascii") for name in expected_names]
    theorems: list[TheoremRecord] = []
    states: list[StateRecord] = []
    with Path(path).open("rb") as source:
        for number, line in enumerate(source, 1):
            stripped = line.rstrip(b"\r\n")
            if stripped.startswith(V2_THEOREM_MARKER + b"\t"):
                theorems.append(theorem_record_from_fields(
                    stripped.split(b"\t"), f"line {number}"))
            elif stripped.startswith(V2_STATE_MARKER + b"\t"):
                states.append(state_record_from_fields(
                    stripped.split(b"\t"), f"line {number}"))
    observed = [record.name for record in theorems]
    if observed != expected:
        raise WireError(
            f"theorem inventory mismatch: expected={expected!r}, "
            f"observed={observed!r}")
    if len(states) != 1:
        raise WireError(f"expected one state record; observed {len(states)}")
    return Capture(tuple(theorems), states[0])


def theorem_record_line(record: TheoremRecord) -> bytes:
    fields = (
        V3_THEOREM_MARKER,
        record.name.hex().encode("ascii"),
        record.theorem.hex().encode("ascii"),
        record.hypotheses.hex().encode("ascii"),
        record.conclusion.hex().encode("ascii"),
        record.global_axioms.hex().encode("ascii"),
        str(record.hypothesis_count).encode("ascii"),
        str(record.global_axiom_count).encode("ascii"),
    )
    return b"\t".join(fields)


def state_record_line(record: StateRecord) -> bytes:
    fields = (
        V3_STATE_MARKER,
        record.kernel_state.hex().encode("ascii"),
        record.type_constants.hex().encode("ascii"),
        record.term_constants.hex().encode("ascii"),
        record.definitions.hex().encode("ascii"),
        record.global_axioms.hex().encode("ascii"),
        str(record.type_constant_count).encode("ascii"),
        str(record.term_constant_count).encode("ascii"),
        str(record.definition_count).encode("ascii"),
        str(record.global_axiom_count).encode("ascii"),
    )
    return b"\t".join(fields)


def capture_record_lines(capture: Capture) -> tuple[bytes, ...]:
    return tuple(
        [theorem_record_line(record) for record in capture.theorems]
        + [state_record_line(capture.state)])
