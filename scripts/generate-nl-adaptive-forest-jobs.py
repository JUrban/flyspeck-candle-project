#!/usr/bin/env python3
"""Reconstruct exact bisection boxes from exported forest roots/topology."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


ZERO_CERTIFICATES = ",".join(["0:0"] * 10)
ARITHMETIC_BASE = 200
SPLIT_PRECISION = 6


@dataclass(frozen=True)
class Node:
    index: int
    component: int
    parent: int
    side: int
    depth: int
    kind: str
    axis: int


def rational_vector(text: str) -> tuple[Fraction, ...]:
    values = tuple(Fraction(item) for item in text.split(","))
    if len(values) != 6:
        raise ValueError("expected a six-coordinate vector")
    return values


def vector_text(values: tuple[Fraction, ...]) -> str:
    return ",".join(str(value) for value in values)


def normalized_base_representation(value: Fraction) -> tuple[int, int]:
    """Return (mantissa, exponent) with value = mantissa * base^exponent.

    Flyspeck's interval endpoints are formal base-200 floats.  Recovering the
    normalized representation lets this development exporter reproduce
    Informal_float.add_float_hi, rather than silently substituting exact
    rational bisection.
    """
    if value < 0:
        raise ValueError("expected a nonnegative magnitude")
    if value == 0:
        return 0, 0
    denominator = value.denominator
    scale = 1
    denominator_exponent = 0
    while scale % denominator:
        scale *= ARITHMETIC_BASE
        denominator_exponent += 1
        if denominator_exponent > 1000:
            raise ValueError("rational is not representable as a base-200 float")
    mantissa = value.numerator * (scale // denominator)
    exponent = -denominator_exponent
    while mantissa % ARITHMETIC_BASE == 0:
        mantissa //= ARITHMETIC_BASE
        exponent += 1
    return mantissa, exponent


def rounded_sum_hi(left: Fraction, right: Fraction) -> Fraction:
    """Reproduce add_float_hi SPLIT_PRECISION for two rational endpoints."""
    value = left + right
    if value == 0:
        return value
    negative = value < 0
    mantissa, exponent = normalized_base_representation(abs(value))
    limit = ARITHMETIC_BASE ** SPLIT_PRECISION
    while mantissa >= limit:
        quotient, remainder = divmod(mantissa, ARITHMETIC_BASE)
        # add_float_hi uses lo_nat for a negative sum and hi_nat otherwise.
        mantissa = quotient if negative or remainder == 0 else quotient + 1
        exponent += 1
    while mantissa and mantissa % ARITHMETIC_BASE == 0:
        mantissa //= ARITHMETIC_BASE
        exponent += 1
    rounded = Fraction(mantissa) * Fraction(ARITHMETIC_BASE) ** exponent
    return -rounded if negative else rounded


def split_center(left: Fraction, right: Fraction) -> Fraction:
    # This is mk_m_center_domain: equal endpoints are preserved verbatim;
    # unequal endpoints use float_inv2 * float_add_hi 6 left right.
    return left if left == right else rounded_sum_hi(left, right) / 2


def read_roots(path: Path) -> dict[int, tuple[tuple[Fraction, ...], tuple[Fraction, ...]]]:
    roots: dict[int, tuple[tuple[Fraction, ...], tuple[Fraction, ...]]] = {}
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        fields = line.split("\t")
        if len(fields) != 3:
            raise ValueError(f"{path}:{line_number}: expected three fields")
        component = int(fields[0])
        lower, upper = rational_vector(fields[1]), rational_vector(fields[2])
        if component in roots or any(left > right for left, right in zip(lower, upper)):
            raise ValueError(f"{path}:{line_number}: invalid root")
        roots[component] = lower, upper
    if not roots:
        raise ValueError("empty root list")
    return roots


def read_topology(path: Path) -> list[Node]:
    nodes: list[Node] = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        fields = line.split("\t")
        if len(fields) != 7:
            raise ValueError(f"{path}:{line_number}: expected seven fields")
        index, component, parent, side, depth, kind, axis = fields
        node = Node(int(index), int(component), int(parent), int(side),
                    int(depth), kind, int(axis))
        if node.index != len(nodes) or node.kind not in {"leaf", "node"}:
            raise ValueError(f"{path}:{line_number}: malformed node")
        nodes.append(node)
    return nodes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", type=Path)
    parser.add_argument("topology", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--leaf-reference", type=Path)
    args = parser.parse_args()

    roots = read_roots(args.roots)
    nodes = read_topology(args.topology)
    boxes: list[tuple[tuple[Fraction, ...], tuple[Fraction, ...]]] = []
    jobs: list[str] = []
    root_components: set[int] = set()
    leaf_jobs: list[str] = []

    for node in nodes:
        if node.parent == -1:
            if node.side != -1 or node.depth != 0 or node.component not in roots:
                raise ValueError(f"malformed root node {node.index}")
            lower, upper = roots[node.component]
            root_components.add(node.component)
        else:
            if not 0 <= node.parent < node.index or node.side not in {0, 1}:
                raise ValueError(f"malformed edge at node {node.index}")
            parent = nodes[node.parent]
            if (parent.kind != "node" or node.component != parent.component or
                    node.depth != parent.depth + 1 or not 1 <= parent.axis <= 6):
                raise ValueError(f"edge identity drift at node {node.index}")
            parent_lower, parent_upper = boxes[node.parent]
            coordinate = parent.axis - 1
            midpoint = split_center(parent_lower[coordinate], parent_upper[coordinate])
            lower_list, upper_list = list(parent_lower), list(parent_upper)
            if node.side == 0:
                upper_list[coordinate] = midpoint
            else:
                lower_list[coordinate] = midpoint
            lower, upper = tuple(lower_list), tuple(upper_list)
        if any(left > right for left, right in zip(lower, upper)):
            raise ValueError(f"empty reconstructed box at node {node.index}")
        boxes.append((lower, upper))
        job = (f"{node.index}\t{ZERO_CERTIFICATES}\t{ZERO_CERTIFICATES}\t"
               f"{vector_text(lower)}\t{vector_text(upper)}")
        jobs.append(job)
        if node.kind == "leaf":
            leaf_jobs.append(job)

    if root_components != set(roots):
        raise ValueError("root/topology component mismatch")

    if args.leaf_reference is not None:
        reference = args.leaf_reference.read_text().splitlines()
        if len(reference) != len(leaf_jobs):
            raise ValueError("leaf reference count mismatch")
        for leaf_index, (actual, expected) in enumerate(zip(leaf_jobs, reference)):
            actual_fields, expected_fields = actual.split("\t"), expected.split("\t")
            if len(expected_fields) != 5 or actual_fields[3:] != expected_fields[3:]:
                raise ValueError(f"leaf reference drift at leaf {leaf_index}")

    args.output.write_text("\n".join(jobs) + "\n")
    print(json.dumps({
        "schema": "candle-nl-adaptive-forest-jobs-v1",
        "status": "DEVELOPMENT_NON_RELEASE",
        "components": len(roots),
        "nodes": len(nodes),
        "leaves": len(leaf_jobs),
        "leaf_reference_checked": args.leaf_reference is not None,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
