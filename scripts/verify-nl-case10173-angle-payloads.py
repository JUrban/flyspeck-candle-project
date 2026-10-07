#!/usr/bin/env python3
"""Verify the two pinned case-10173 dihedral polynomial payloads exactly."""

from __future__ import annotations

import hashlib
import sys
from fractions import Fraction
from pathlib import Path


Monomial = tuple[int, int, int, int, int, int]
Polynomial = dict[Monomial, Fraction]
ZERO_MONOMIAL: Monomial = (0, 0, 0, 0, 0, 0)


def fail(message: str) -> None:
    raise RuntimeError(message)


def normalize(polynomial: Polynomial) -> Polynomial:
    return {term: coefficient for term, coefficient in polynomial.items()
            if coefficient != 0}


def constant(value: Fraction | int) -> Polynomial:
    coefficient = Fraction(value)
    return {} if coefficient == 0 else {ZERO_MONOMIAL: coefficient}


def variable(index: int) -> Polynomial:
    if index < 0 or index >= 6:
        fail(f"variable index outside six-dimensional source language: {index}")
    exponents = [0] * 6
    exponents[index] = 1
    return {tuple(exponents): Fraction(1)}  # type: ignore[arg-type]


def negate(value: Polynomial) -> Polynomial:
    return {term: -coefficient for term, coefficient in value.items()}


def add(left: Polynomial, right: Polynomial) -> Polynomial:
    result = dict(left)
    for term, coefficient in right.items():
        result[term] = result.get(term, Fraction(0)) + coefficient
    return normalize(result)


def multiply(left: Polynomial, right: Polynomial) -> Polynomial:
    result: Polynomial = {}
    for left_term, left_coefficient in left.items():
        for right_term, right_coefficient in right.items():
            term = tuple(left_term[index] + right_term[index]
                         for index in range(6))
            result[term] = result.get(term, Fraction(0)) + (
                left_coefficient * right_coefficient)
    return normalize(result)


def scale(coefficient: int, value: Polynomial) -> Polynomial:
    return multiply(constant(coefficient), value)


class CvalParser:
    def __init__(self, source: str) -> None:
        self.source = source
        self.position = 0
        self.nodes: list[tuple[str, int] | tuple[str, int, int]] = []

    def parse(self) -> int:
        root = self.parse_node()
        if self.position != len(self.source):
            fail(f"trailing cval source at byte {self.position}")
        return root

    def parse_node(self) -> int:
        if self.position >= len(self.source):
            fail("unexpected end of cval source")
        if self.source[self.position] == "n":
            self.position += 1
            begin = self.position
            while (self.position < len(self.source) and
                   self.source[self.position].isdigit()):
                self.position += 1
            if begin == self.position:
                fail(f"empty numeral at byte {begin}")
            self.nodes.append(("n", int(self.source[begin:self.position])))
            return len(self.nodes) - 1
        if self.source.startswith("p(", self.position):
            self.position += 2
            left = self.parse_node()
            self.expect(",")
            right = self.parse_node()
            self.expect(")")
            self.nodes.append(("p", left, right))
            return len(self.nodes) - 1
        fail(f"unexpected cval token at byte {self.position}")

    def expect(self, token: str) -> None:
        if not self.source.startswith(token, self.position):
            fail(f"expected {token!r} at byte {self.position}")
        self.position += len(token)

    def numeral(self, index: int) -> int:
        node = self.nodes[index]
        if node[0] != "n":
            fail("expected cval numeral")
        return node[1]

    def pair(self, index: int) -> tuple[int, int]:
        node = self.nodes[index]
        if node[0] != "p":
            fail("expected cval pair")
        return node[1], node[2]

    def list_items(self, index: int) -> list[int]:
        result: list[int] = []
        while self.nodes[index][0] == "p":
            item, index = self.pair(index)
            result.append(item)
        if self.numeral(index) != 0:
            fail("nonzero cval list tail")
        return result

    def rational(self, index: int) -> Fraction:
        signed, denominator_predecessor = self.pair(index)
        positive, negative = self.pair(signed)
        return Fraction(
            self.numeral(positive) - self.numeral(negative),
            self.numeral(denominator_predecessor) + 1,
        )

    def polynomial(self, payload: int) -> tuple[Polynomial, int]:
        instructions = self.list_items(payload)
        stack: list[Polynomial] = []
        for instruction in instructions:
            node = self.nodes[instruction]
            if node[0] == "p":
                tag, argument = self.pair(instruction)
                decoded_tag = self.numeral(tag)
                if decoded_tag == 0:
                    stack.append(constant(self.rational(argument)))
                elif decoded_tag == 1:
                    stack.append(variable(self.numeral(argument)))
                else:
                    fail(f"unknown polynomial pair tag: {decoded_tag}")
                continue
            opcode = self.numeral(instruction)
            if opcode in (2, 5):
                if not stack:
                    fail("unary polynomial stack underflow")
                stack[-1] = (negate(stack[-1]) if opcode == 2
                             else multiply(stack[-1], stack[-1]))
            elif opcode in (3, 4):
                if len(stack) < 2:
                    fail("binary polynomial stack underflow")
                right = stack.pop()
                left = stack.pop()
                stack.append(add(left, right) if opcode == 3
                             else multiply(left, right))
            else:
                fail(f"unknown polynomial opcode: {opcode}")
        if len(stack) != 1:
            fail(f"polynomial stack drift: {len(stack)} results")
        return stack[0], len(instructions)


def expected_payloads() -> tuple[Polynomial, Polynomial]:
    x0, x1, x2, x3, x4, x5 = [variable(index) for index in range(6)]

    delta_x4 = add(
        add(
            add(negate(multiply(x1, x2)), negate(multiply(x0, x3))),
            add(multiply(x1, x4), multiply(x2, x5)),
        ),
        add(
            negate(multiply(x4, x5)),
            multiply(x0, add(
                add(add(negate(x0), x1), add(x2, negate(x3))),
                add(x4, x5),
            )),
        ),
    )

    delta = add(
        add(
            multiply(multiply(x0, x3), add(
                add(add(negate(x0), x1), add(x2, negate(x3))),
                add(x4, x5),
            )),
            multiply(multiply(x1, x4), add(
                add(add(x0, negate(x1)), add(x2, x3)),
                add(negate(x4), x5),
            )),
        ),
        add(
            multiply(multiply(x2, x5), add(
                add(add(x0, x1), add(negate(x2), x3)),
                add(x4, negate(x5)),
            )),
            negate(add(
                add(multiply(multiply(x1, x2), x3),
                    multiply(multiply(x0, x2), x4)),
                add(add(multiply(multiply(x0, x1), x5),
                        multiply(multiply(x3, x4), x5)),
                    constant(0)),
            )),
        ),
    )
    return negate(delta_x4), scale(4, multiply(x0, delta))


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} CASE10173-PROGRAM.cval", file=sys.stderr)
        return 2
    source_path = Path(sys.argv[1])
    source_bytes = source_path.read_bytes()
    source = source_bytes.decode("utf-8").strip()
    parser = CvalParser(source)
    outer = parser.list_items(parser.parse())
    if len(outer) != 54:
        fail(f"outer instruction count drift: {len(outer)}")

    expected_neg_delta_x4, expected_four_x0_delta = expected_payloads()
    observations = [
        (32, 39, expected_neg_delta_x4, "neg_delta_x4"),
        (33, 85, expected_four_x0_delta, "four_x0_delta"),
    ]
    for outer_index, expected_steps, expected, label in observations:
        tag, payload = parser.pair(outer[outer_index])
        if parser.numeral(tag) != 0:
            fail(f"outer instruction {outer_index} is not a polynomial")
        actual, steps = parser.polynomial(payload)
        if steps != expected_steps:
            fail(f"{label} step count drift: {steps} != {expected_steps}")
        if actual != expected:
            fail(f"{label} semantic polynomial identity mismatch")

    digest = hashlib.sha256(source_bytes).hexdigest()
    print(
        "CANDLE_NL_CASE10173_ANGLE_PAYLOAD_IDENTITIES_OK"
        f" outer_instructions=54 neg_delta_x4_steps=39"
        f" four_x0_delta_steps=85 source_sha256={digest}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, ZeroDivisionError) as error:
        print(f"case10173 payload verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
