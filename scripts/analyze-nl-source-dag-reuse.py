#!/usr/bin/env python3
"""Count exact and coordinate-permutation expression reuse in a Candle cval plan."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import TypeAlias

sys.setrecursionlimit(10000)

Cval: TypeAlias = tuple
Polynomial: TypeAlias = tuple[tuple[tuple[int, ...], int, int], ...]
Expression: TypeAlias = tuple
DIMENSIONS = 6


class ParseError(ValueError):
    pass


@dataclass
class Parser:
    text: str
    position: int = 0

    def skip_space(self) -> None:
        while self.position < len(self.text) and self.text[self.position].isspace():
            self.position += 1

    def parse(self) -> Cval:
        result = self.parse_node()
        self.skip_space()
        if self.position != len(self.text):
            raise ParseError(f"trailing cval data at byte {self.position}")
        return result

    def parse_node(self) -> Cval:
        self.skip_space()
        if self.position >= len(self.text):
            raise ParseError("unexpected end of cval")
        kind = self.text[self.position]
        self.position += 1
        if kind == "n":
            begin = self.position
            while self.position < len(self.text) and self.text[self.position].isdigit():
                self.position += 1
            if begin == self.position:
                raise ParseError(f"empty numeral at byte {begin}")
            return ("n", int(self.text[begin : self.position]))
        if kind == "p":
            self.expect("(")
            left = self.parse_node()
            self.expect(",")
            right = self.parse_node()
            self.expect(")")
            return ("p", left, right)
        raise ParseError(f"expected cval node at byte {self.position - 1}")

    def expect(self, expected: str) -> None:
        self.skip_space()
        if self.position >= len(self.text) or self.text[self.position] != expected:
            raise ParseError(f"expected {expected!r} at byte {self.position}")
        self.position += 1


def numeral(node: Cval, context: str) -> int:
    if node[0] != "n":
        raise ParseError(f"{context}: expected numeral")
    return node[1]


def pair(node: Cval, context: str) -> tuple[Cval, Cval]:
    if node[0] != "p":
        raise ParseError(f"{context}: expected pair")
    return node[1], node[2]


def decode_list(node: Cval, context: str) -> list[Cval]:
    result: list[Cval] = []
    current = node
    while current[0] == "p":
        result.append(current[1])
        current = current[2]
    if numeral(current, context) != 0:
        raise ParseError(f"{context}: nonzero list tail")
    return result


def decode_rational(node: Cval) -> Fraction:
    signed, denominator = pair(node, "rational")
    positive_node, negative_node = pair(signed, "signed rational")
    positive = numeral(positive_node, "positive numerator")
    negative = numeral(negative_node, "negative numerator")
    return Fraction(positive - negative, numeral(denominator, "denominator") + 1)


def poly_add(left: dict[tuple[int, ...], Fraction],
             right: dict[tuple[int, ...], Fraction]) -> dict[tuple[int, ...], Fraction]:
    result = dict(left)
    for monomial, coefficient in right.items():
        result[monomial] = result.get(monomial, Fraction(0)) + coefficient
        if result[monomial] == 0:
            del result[monomial]
    return result


def poly_mul(left: dict[tuple[int, ...], Fraction],
             right: dict[tuple[int, ...], Fraction]) -> dict[tuple[int, ...], Fraction]:
    result: dict[tuple[int, ...], Fraction] = {}
    for left_monomial, left_coefficient in left.items():
        for right_monomial, right_coefficient in right.items():
            monomial = tuple(a + b for a, b in zip(left_monomial, right_monomial))
            result[monomial] = result.get(monomial, Fraction(0)) + (
                left_coefficient * right_coefficient
            )
            if result[monomial] == 0:
                del result[monomial]
    return result


def canonical_polynomial(value: dict[tuple[int, ...], Fraction]) -> Polynomial:
    return tuple(
        (monomial, coefficient.numerator, coefficient.denominator)
        for monomial, coefficient in sorted(value.items())
    )


def decode_polynomial(program: Cval) -> Polynomial:
    stack: list[dict[tuple[int, ...], Fraction]] = []
    zero_monomial = (0,) * DIMENSIONS
    for instruction in decode_list(program, "polynomial program"):
        if instruction[0] == "p":
            tag_node, payload = pair(instruction, "polynomial instruction")
            tag = numeral(tag_node, "polynomial tag")
            if tag == 0:
                constant = decode_rational(payload)
                stack.append({zero_monomial: constant} if constant else {})
            elif tag == 1:
                variable = numeral(payload, "polynomial variable")
                if not 0 <= variable < DIMENSIONS:
                    raise ParseError("polynomial variable out of range")
                monomial = [0] * DIMENSIONS
                monomial[variable] = 1
                stack.append({tuple(monomial): Fraction(1)})
            else:
                raise ParseError(f"unknown polynomial tag {tag}")
            continue
        opcode = numeral(instruction, "polynomial opcode")
        if opcode in (2, 5):
            if not stack:
                raise ParseError("polynomial unary stack underflow")
            value = stack.pop()
            stack.append(
                {key: -coefficient for key, coefficient in value.items()}
                if opcode == 2
                else poly_mul(value, value)
            )
        elif opcode in (3, 4):
            if len(stack) < 2:
                raise ParseError("polynomial binary stack underflow")
            right = stack.pop()
            left = stack.pop()
            stack.append(poly_add(left, right) if opcode == 3 else poly_mul(left, right))
        else:
            raise ParseError(f"unknown polynomial opcode {opcode}")
    if len(stack) != 1:
        raise ParseError("polynomial final stack drift")
    return canonical_polynomial(stack[0])


def expression_digest(expression: Expression) -> str:
    return hashlib.sha256(repr(expression).encode("utf-8")).hexdigest()


def expression_size(expression: Expression, cache: dict[Expression, int]) -> int:
    if expression in cache:
        return cache[expression]
    kind = expression[0]
    if kind in ("poly", "pi_half"):
        result = 1
    elif kind in ("neg", "square", "inverse", "atan", "sqrt"):
        result = 1 + expression_size(expression[1], cache)
    else:
        result = 1 + expression_size(expression[1], cache) + expression_size(expression[2], cache)
    cache[expression] = result
    return result


def permute_polynomial(polynomial: Polynomial, permutation: tuple[int, ...]) -> Polynomial:
    value = []
    for monomial, numerator, denominator in polynomial:
        permuted = tuple(monomial[permutation[index]] for index in range(DIMENSIONS))
        value.append((permuted, numerator, denominator))
    return tuple(sorted(value))


def permute_expression(expression: Expression, permutation: tuple[int, ...],
                       cache: dict[tuple[Expression, tuple[int, ...]], Expression]) -> Expression:
    cache_key = (expression, permutation)
    if cache_key in cache:
        return cache[cache_key]
    kind = expression[0]
    if kind == "poly":
        result = ("poly", permute_polynomial(expression[1], permutation))
    elif kind == "pi_half":
        result = expression
    elif kind in ("neg", "square", "inverse", "atan", "sqrt"):
        result = (kind, permute_expression(expression[1], permutation, cache))
    else:
        result = (
            kind,
            permute_expression(expression[1], permutation, cache),
            permute_expression(expression[2], permutation, cache),
        )
    cache[cache_key] = result
    return result


def permutation_normal_form(expression: Expression,
                            permutations: list[tuple[int, ...]],
                            cache: dict[tuple[Expression, tuple[int, ...]], Expression]) -> Expression:
    return min(permute_expression(expression, permutation, cache) for permutation in permutations)


def build_expressions(instructions: list[Cval]) -> tuple[Expression, list[Expression]]:
    stack: list[Expression] = []
    occurrences: list[Expression] = []
    unary = {2: "neg", 5: "square", 6: "inverse", 7: "atan"}
    binary = {3: "add", 4: "mul"}
    for index, instruction in enumerate(instructions):
        if instruction[0] == "p":
            tag_node, payload = pair(instruction, "analytic instruction")
            tag = numeral(tag_node, "analytic tag")
            if tag == 0:
                expression = ("poly", decode_polynomial(payload))
                stack.append(expression)
            elif tag == 1:
                if not stack:
                    raise ParseError(f"sqrt stack underflow at outer {index}")
                expression = ("sqrt", stack.pop())
                stack.append(expression)
            else:
                raise ParseError(f"unknown analytic tag {tag}")
        else:
            opcode = numeral(instruction, "analytic opcode")
            if opcode == 8:
                expression = ("pi_half",)
                stack.append(expression)
            elif opcode in unary:
                if not stack:
                    raise ParseError(f"unary stack underflow at outer {index}")
                expression = (unary[opcode], stack.pop())
                stack.append(expression)
            elif opcode in binary:
                if len(stack) < 2:
                    raise ParseError(f"binary stack underflow at outer {index}")
                right = stack.pop()
                left = stack.pop()
                expression = (binary[opcode], left, right)
                stack.append(expression)
            else:
                raise ParseError(f"unknown analytic opcode {opcode}")
        occurrences.append(expression)
    if len(stack) != 1:
        raise ParseError(f"analytic final stack depth is {len(stack)}, expected 1")
    return stack[0], occurrences


def repeated_rows(counter: Counter[Expression], indices: dict[Expression, list[int]],
                  size_cache: dict[Expression, int], limit: int) -> list[dict[str, object]]:
    candidates = [expression for expression, count in counter.items() if count > 1]
    candidates.sort(
        key=lambda expression: (
            -(counter[expression] - 1) * expression_size(expression, size_cache),
            -expression_size(expression, size_cache),
            expression_digest(expression),
        )
    )
    return [
        {
            "digest": expression_digest(expression),
            "kind": expression[0],
            "occurrences": counter[expression],
            "source_indices": indices[expression],
            "subtree_nodes": expression_size(expression, size_cache),
            "gross_repeated_subtree_nodes": (
                (counter[expression] - 1) * expression_size(expression, size_cache)
            ),
        }
        for expression in candidates[:limit]
    ]


def main() -> int:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("program", type=Path)
    argument_parser.add_argument("--expected-instructions", type=int)
    argument_parser.add_argument("--top", type=int, default=20)
    args = argument_parser.parse_args()

    source = args.program.read_text(encoding="utf-8")
    root = Parser(source).parse()
    instructions = decode_list(root, "analytic program")
    if args.expected_instructions is not None and len(instructions) != args.expected_instructions:
        raise ParseError(
            f"instruction count {len(instructions)} does not match {args.expected_instructions}"
        )
    final_expression, occurrences = build_expressions(instructions)

    exact_counts = Counter(occurrences)
    exact_indices: dict[Expression, list[int]] = defaultdict(list)
    for index, expression in enumerate(occurrences):
        exact_indices[expression].append(index)
    size_cache: dict[Expression, int] = {}

    permutations = list(itertools.permutations(range(DIMENSIONS)))
    permutation_cache: dict[tuple[Expression, tuple[int, ...]], Expression] = {}
    normal_forms = {
        expression: permutation_normal_form(expression, permutations, permutation_cache)
        for expression in exact_counts
    }
    family_members: dict[Expression, set[Expression]] = defaultdict(set)
    family_occurrences: Counter[Expression] = Counter()
    family_indices: dict[Expression, list[int]] = defaultdict(list)
    for index, expression in enumerate(occurrences):
        normal = normal_forms[expression]
        family_members[normal].add(expression)
        family_occurrences[normal] += 1
        family_indices[normal].append(index)

    permutation_families = []
    for normal, members in family_members.items():
        if len(members) < 2:
            continue
        maximum_size = max(expression_size(member, size_cache) for member in members)
        permutation_families.append(
            {
                "normal_digest": expression_digest(normal),
                "kind": normal[0],
                "occurrences": family_occurrences[normal],
                "exact_variants": len(members),
                "source_indices": family_indices[normal],
                "maximum_subtree_nodes": maximum_size,
            }
        )
    permutation_families.sort(
        key=lambda row: (
            -int(row["maximum_subtree_nodes"]),
            -int(row["exact_variants"]),
            str(row["normal_digest"]),
        )
    )

    polynomial_occurrences = [expression for expression in occurrences if expression[0] == "poly"]
    simple_constants = sum(
        1
        for expression in polynomial_occurrences
        if len(expression[1]) <= 1
        and (not expression[1] or expression[1][0][0] == (0,) * DIMENSIONS)
    )
    simple_variables = sum(
        1
        for expression in polynomial_occurrences
        if len(expression[1]) == 1
        and sum(expression[1][0][0]) == 1
        and expression[1][0][1:] == (1, 1)
    )

    result = {
        "schema": "candle-nl-source-dag-reuse-v1",
        "status": "DEVELOPMENT_NON_RELEASE",
        "program_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "instructions": len(instructions),
        "final_expression_digest": expression_digest(final_expression),
        "exact_expression_nodes": len(occurrences),
        "exact_unique_nodes": len(exact_counts),
        "exact_duplicate_nodes": len(occurrences) - len(exact_counts),
        "polynomial_occurrences": len(polynomial_occurrences),
        "simple_constant_occurrences": simple_constants,
        "simple_variable_occurrences": simple_variables,
        "pi_half_occurrences": sum(1 for expression in occurrences if expression[0] == "pi_half"),
        "exact_repeated_subexpressions": repeated_rows(
            exact_counts, exact_indices, size_cache, args.top
        ),
        "coordinate_permutation_family_count": len(permutation_families),
        "coordinate_permutation_families": permutation_families[: args.top],
    }
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ParseError, ValueError) as error:
        print(f"source DAG reuse analysis failed: {error}", file=sys.stderr)
        raise SystemExit(1)
