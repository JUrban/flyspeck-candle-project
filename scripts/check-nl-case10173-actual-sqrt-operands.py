#!/usr/bin/env python3
"""Discriminate case-10173 sqrt contracts on the actual Taylor operand.

The literal historical evaluator does not apply sqrt directly to the source
box.  It first constructs a variable Taylor result and applies sqrt to that
result's completed ``value_bound``.  This development-only checker recreates
that operand from the authenticated decimal center/radius data, checks the
source rational sqrt certificate on it, and compares the supplied fixed
second-derivative reciprocal with direct rational outward rounding.

This is an independent data check, not part of Candle's trusted theorem
boundary.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path


FULL_CELLS = 4_173
COORDINATES = 6
DECIMAL_SCALE = 1_000_000_000_000
KERNEL_PREFIX = "CANDLE_NL_NATIVE_HISTORICAL_DIHEDRAL_KERNEL"

EXPECTED_SOURCE_SHA256 = (
    "aaf26e7561345206cbb106a901784a78c95c5819d0f15a19406dca6fa7034f93"
)
EXPECTED_KERNEL_SHA256 = (
    "0750885c2d30cb93dbabf63b0b334ca176f17ed37e1cd6ac3c0a274baeec89a3"
)
EXPECTED_ANALYTIC_SHA256 = (
    "793296918ef37a1ff0eca41decc3bcb6f8138f012c85640dd85133265c376959"
)

Interval = tuple[int, int]
QInterval = tuple[Fraction, Fraction]


def authenticated_lines(path: Path, expected: str, role: str) -> list[str]:
    payload = path.read_bytes()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise ValueError(f"{role} identity drift: {actual}")
    return payload.decode("ascii").splitlines()


def fields_of(line: str, prefix: str, role: str) -> dict[str, str]:
    parts = line.split()
    if not parts or parts[0] != prefix:
        raise ValueError(f"malformed {role} prefix")
    result: dict[str, str] = {}
    for part in parts[1:]:
        if "=" not in part:
            raise ValueError(f"malformed {role} field: {part}")
        key, value = part.split("=", 1)
        if key in result:
            raise ValueError(f"duplicate {role} field: {key}")
        result[key] = value
    return result


def fixed_interval(text: str, context: str) -> Interval:
    fields = text.split(":")
    if len(fields) != 2:
        raise ValueError(f"malformed interval at {context}: {text}")
    lower, upper = map(int, fields)
    if lower > upper:
        raise ValueError(f"reversed interval at {context}: {text}")
    return lower, upper


def fixed_interval_list(text: str, count: int, context: str) -> list[Interval]:
    result = [
        fixed_interval(item, f"{context}[{index}]")
        for index, item in enumerate(text.split(","))
    ]
    if len(result) != count:
        raise ValueError(f"{context} arity drift: {len(result)} != {count}")
    return result


def q_interval(text: str, context: str) -> QInterval:
    fields = text.split(":")
    if len(fields) != 2:
        raise ValueError(f"malformed rational interval at {context}: {text}")
    lower, upper = map(Fraction, fields)
    if lower > upper:
        raise ValueError(f"reversed rational interval at {context}: {text}")
    return lower, upper


def floor_scaled(value: Fraction) -> int:
    return value.numerator * DECIMAL_SCALE // value.denominator


def ceil_scaled(value: Fraction) -> int:
    numerator = value.numerator * DECIMAL_SCALE
    return (numerator + value.denominator - 1) // value.denominator


def direct_sqrt_second_reciprocal(root: QInterval, value: QInterval) -> Interval:
    """Outward fixed interval for 1 / ((2 root) * (2 value))."""
    root_lower, root_upper = root
    value_lower, value_upper = value
    if root_lower <= 0 or value_lower <= 0:
        raise ValueError("nonpositive sqrt second-derivative input")
    return (
        floor_scaled(Fraction(1, 1) / (4 * root_upper * value_upper)),
        ceil_scaled(Fraction(1, 1) / (4 * root_lower * value_lower)),
    )


def positive_fixed_product(left: Interval, right: Interval) -> Interval:
    if left[0] <= 0 or right[0] <= 0:
        raise ValueError("nonpositive fixed product input")
    lower_product = left[0] * right[0]
    upper_product = left[1] * right[1]
    return (
        lower_product // DECIMAL_SCALE,
        (upper_product + DECIMAL_SCALE - 1) // DECIMAL_SCALE,
    )


def positive_fixed_inverse(value: Interval) -> Interval:
    if value[0] <= 0:
        raise ValueError("nonpositive fixed inverse input")
    square_scale = DECIMAL_SCALE * DECIMAL_SCALE
    return (
        square_scale // value[1],
        (square_scale + value[0] - 1) // value[0],
    )


def source_aligned_packet_reciprocal(root: QInterval, box: Interval) -> Interval:
    """Recreate the reciprocal stored by the source-aligned packet generator."""
    fixed_root = (
        floor_scaled(root[0]),
        ceil_scaled(root[1]),
    )
    denominator = positive_fixed_product(
        (2 * box[0], 2 * box[1]),
        (2 * fixed_root[0], 2 * fixed_root[1]),
    )
    return positive_fixed_inverse(denominator)


def sqrt_certificate_holds(value: QInterval, root: QInterval) -> bool:
    value_lower, value_upper = value
    root_lower, root_upper = root
    return (
        0 < root_lower
        and value_lower <= value_upper
        and root_lower <= root_upper
        and root_lower * root_lower <= value_lower
        and value_upper <= root_upper * root_upper
    )


def first_difference(
    current: dict[str, object] | None,
    *,
    cell: int,
    coordinate: int,
    original: QInterval,
    actual: QInterval,
    supplied: Interval,
    expected: Interval,
) -> dict[str, object]:
    if current is not None:
        return current
    return {
        "cell": cell,
        "coordinate": coordinate,
        "original": [str(original[0]), str(original[1])],
        "actual": [str(actual[0]), str(actual[1])],
        "supplied_reciprocal": list(supplied),
        "expected_reciprocal": list(expected),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_jobs", type=Path)
    parser.add_argument("kernel_trace", type=Path)
    parser.add_argument("analytic_certificates", type=Path)
    args = parser.parse_args()

    source_lines = authenticated_lines(
        args.source_jobs, EXPECTED_SOURCE_SHA256, "source jobs"
    )
    kernel_lines = authenticated_lines(
        args.kernel_trace, EXPECTED_KERNEL_SHA256, "kernel trace"
    )
    analytic_lines = authenticated_lines(
        args.analytic_certificates, EXPECTED_ANALYTIC_SHA256, "analytic certificates"
    )
    if len(source_lines) != FULL_CELLS or len(kernel_lines) != FULL_CELLS:
        raise ValueError("full-cell row-count drift")
    if len(analytic_lines) != FULL_CELLS * COORDINATES:
        raise ValueError("analytic row-count drift")

    counts = {
        "cells": FULL_CELLS,
        "coordinates": FULL_CELLS * COORDINATES,
        "actual_operand_differs_from_source_box": 0,
        "actual_operand_sqrt_certificate_passes": 0,
        "source_aligned_packet_reciprocal_matches_original_operand": 0,
        "source_aligned_packet_reciprocal_matches_actual_operand": 0,
        "raw_native_reciprocal_matches_actual_operand": 0,
        "actual_reciprocal_matches_original_reciprocal": 0,
    }
    first_operand_difference: dict[str, object] | None = None
    first_domain_failure: dict[str, object] | None = None
    first_packet_reciprocal_difference: dict[str, object] | None = None
    first_raw_native_reciprocal_difference: dict[str, object] | None = None

    for cell, (source_line, kernel_line) in enumerate(
        zip(source_lines, kernel_lines, strict=True)
    ):
        source_fields = source_line.split("\t")
        if len(source_fields) != 5 or int(source_fields[0]) != cell:
            raise ValueError(f"source row identity/shape drift at {cell}")
        all_box_roots = [
            q_interval(item, f"box root {cell}:{coordinate}")
            for coordinate, item in enumerate(source_fields[1].split(","))
        ]
        box_roots = all_box_roots[:COORDINATES]
        source_lowers = list(map(Fraction, source_fields[3].split(",")))
        source_uppers = list(map(Fraction, source_fields[4].split(",")))
        if not (
            len(all_box_roots) == 7
            and len(box_roots) == len(source_lowers) == len(source_uppers) == COORDINATES
        ):
            raise ValueError(f"source coordinate arity drift at {cell}")

        kernel = fields_of(kernel_line, KERNEL_PREFIX, f"kernel row {cell}")
        center = fixed_interval_list(
            kernel["center_environment"], COORDINATES, f"center {cell}"
        )
        box = fixed_interval_list(
            kernel["box_environment"], COORDINATES, f"box {cell}"
        )

        for coordinate in range(COORDINATES):
            analytic_row = cell * COORDINATES + coordinate
            fields = analytic_lines[analytic_row].split("\t")
            if (
                len(fields) != 15
                or list(map(int, fields[:2])) != [cell, coordinate]
                or fields[2:5] != ["sqrt", "0", "0"]
            ):
                raise ValueError(f"analytic identity/shape drift at row {analytic_row}")
            raw_native_reciprocal = (int(fields[13]), int(fields[14]))

            center_lower, center_upper = center[coordinate]
            box_lower, box_upper = box[coordinate]
            radius = max(center_lower - box_lower, box_upper - center_upper)
            actual_fixed = (center_lower - radius, center_upper + radius)
            actual = (
                Fraction(actual_fixed[0], DECIMAL_SCALE),
                Fraction(actual_fixed[1], DECIMAL_SCALE),
            )
            original = (source_lowers[coordinate], source_uppers[coordinate])
            root = box_roots[coordinate]
            packet_reciprocal = source_aligned_packet_reciprocal(
                root, box[coordinate]
            )

            if actual != original:
                counts["actual_operand_differs_from_source_box"] += 1
                first_operand_difference = first_difference(
                    first_operand_difference,
                    cell=cell,
                    coordinate=coordinate,
                    original=original,
                    actual=actual,
                    supplied=packet_reciprocal,
                    expected=direct_sqrt_second_reciprocal(root, actual),
                )
            if sqrt_certificate_holds(actual, root):
                counts["actual_operand_sqrt_certificate_passes"] += 1
            elif first_domain_failure is None:
                first_domain_failure = {
                    "cell": cell,
                    "coordinate": coordinate,
                    "actual": [str(actual[0]), str(actual[1])],
                    "root": [str(root[0]), str(root[1])],
                }

            original_reciprocal = direct_sqrt_second_reciprocal(root, original)
            actual_reciprocal = direct_sqrt_second_reciprocal(root, actual)
            if packet_reciprocal == original_reciprocal:
                counts[
                    "source_aligned_packet_reciprocal_matches_original_operand"
                ] += 1
            if packet_reciprocal == actual_reciprocal:
                counts[
                    "source_aligned_packet_reciprocal_matches_actual_operand"
                ] += 1
            else:
                first_packet_reciprocal_difference = first_difference(
                    first_packet_reciprocal_difference,
                    cell=cell,
                    coordinate=coordinate,
                    original=original,
                    actual=actual,
                    supplied=packet_reciprocal,
                    expected=actual_reciprocal,
                )
            if raw_native_reciprocal == actual_reciprocal:
                counts["raw_native_reciprocal_matches_actual_operand"] += 1
            else:
                first_raw_native_reciprocal_difference = first_difference(
                    first_raw_native_reciprocal_difference,
                    cell=cell,
                    coordinate=coordinate,
                    original=original,
                    actual=actual,
                    supplied=raw_native_reciprocal,
                    expected=actual_reciprocal,
                )
            if actual_reciprocal == original_reciprocal:
                counts["actual_reciprocal_matches_original_reciprocal"] += 1

    result = {
        "status": "accepted"
        if first_domain_failure is None
        and first_packet_reciprocal_difference is None
        else "rejected",
        "counts": counts,
        "first_operand_difference": first_operand_difference,
        "first_domain_failure": first_domain_failure,
        "first_packet_reciprocal_difference": first_packet_reciprocal_difference,
        "first_raw_native_reciprocal_difference": (
            first_raw_native_reciprocal_difference
        ),
        "note": "development discriminator only; not trusted theorem evidence",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
