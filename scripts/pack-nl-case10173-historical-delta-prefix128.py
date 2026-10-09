#!/usr/bin/env python3
"""Pack a genuine case10173 historical delta transfer gate.

The native output is an untrusted development oracle.  The translated Candle
program recomputes every result with checked bounded-word arithmetic and
rejects any byte, shape, count, overflow, or result mismatch.

The default remains the original prefix-128 fixture.  ``--cells 4173`` packs
the complete authenticated batch from the independently matched full oracle.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
from pathlib import Path
import re
import struct


EXPECTED_JOBS_SHA256 = (
    "c03587283858e7ed3f60ba90909e542a7186707a0f45f702249af57e73920afb"
)
EXPECTED_ORACLE_SHA256 = {
    128: "fda77d3d844e703324585a1c9e1ef86651c343dcab8a31344df303fab29ffc05",
    4173: "888aa093ab67f440f35336a128d52221ef5502db7e5172a2a402951d73ed57c5",
}
MAGIC = b"CNLHDB01"
SCALE = 1 << 40
WORD_LIMIT = 1 << 64
ORACLE_PATTERN = re.compile(
    r"^CANDLE_NL_NATIVE_HISTORICAL_DELTA_BLOCK "
    r"index=([0-9]+) lower=(-?[0-9]+) upper=(-?[0-9]+)$"
)


def authenticated_bytes(path: Path, expected: str, role: str) -> bytes:
    payload = path.read_bytes()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise ValueError(f"{role} identity drift: {actual}")
    return payload


def floor_scaled(value: Fraction) -> int:
    return (value.numerator * SCALE) // value.denominator


def ceil_scaled(value: Fraction) -> int:
    return -((-value.numerator * SCALE) // value.denominator)


def unsigned_word(value: int, context: str) -> int:
    if not 0 <= value < WORD_LIMIT:
        raise ValueError(f"unsigned word range failure at {context}: {value}")
    return value


def signed_endpoint(value: int, context: str) -> bytes:
    magnitude = unsigned_word(abs(value), context)
    return struct.pack("<BQ", int(value < 0), magnitude)


def load_boxes(payload: bytes, cell_count: int) -> list[list[tuple[int, int]]]:
    rows = payload.decode("ascii").splitlines()
    if len(rows) != 4173:
        raise ValueError(f"job count drift: {len(rows)}")
    boxes: list[list[tuple[int, int]]] = []
    for expected_index, row in enumerate(rows[:cell_count]):
        fields = row.split("\t")
        if len(fields) != 5 or int(fields[0]) != expected_index:
            raise ValueError(f"malformed job row {expected_index}")
        lower = [Fraction(value) for value in fields[3].split(",")]
        upper = [Fraction(value) for value in fields[4].split(",")]
        if len(lower) != 6 or len(upper) != 6:
            raise ValueError(f"box arity drift at row {expected_index}")
        box: list[tuple[int, int]] = []
        for coordinate, (lo, hi) in enumerate(zip(lower, upper)):
            scaled_lower = unsigned_word(
                floor_scaled(lo), f"box {expected_index}[{coordinate}] lower"
            )
            scaled_upper = unsigned_word(
                ceil_scaled(hi), f"box {expected_index}[{coordinate}] upper"
            )
            if scaled_lower > scaled_upper:
                raise ValueError(f"reversed box at {expected_index}[{coordinate}]")
            box.append((scaled_lower, scaled_upper))
        boxes.append(box)
    return boxes


def load_oracle(payload: bytes, cell_count: int) -> list[tuple[int, int]]:
    rows = payload.decode("ascii").splitlines()
    if len(rows) != cell_count:
        raise ValueError(f"oracle count drift: {len(rows)}")
    result: list[tuple[int, int]] = []
    for expected_index, row in enumerate(rows):
        match = ORACLE_PATTERN.fullmatch(row)
        if match is None or int(match.group(1)) != expected_index:
            raise ValueError(f"malformed oracle row {expected_index}")
        lower = int(match.group(2))
        upper = int(match.group(3))
        if lower > upper:
            raise ValueError(f"reversed oracle interval at row {expected_index}")
        result.append((lower, upper))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("jobs", type=Path)
    parser.add_argument("oracle", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--cells", type=int, choices=sorted(EXPECTED_ORACLE_SHA256), default=128
    )
    args = parser.parse_args()

    boxes = load_boxes(
        authenticated_bytes(args.jobs, EXPECTED_JOBS_SHA256, "jobs"), args.cells
    )
    oracle = load_oracle(
        authenticated_bytes(
            args.oracle, EXPECTED_ORACLE_SHA256[args.cells], "oracle"
        ),
        args.cells,
    )

    output = bytearray(MAGIC)
    output.extend(struct.pack("<I", args.cells))
    for index, (box, expected) in enumerate(zip(boxes, oracle)):
        for lower, upper in box:
            output.extend(struct.pack("<QQ", lower, upper))
        output.extend(signed_endpoint(expected[0], f"oracle {index} lower"))
        output.extend(signed_endpoint(expected[1], f"oracle {index} upper"))

    expected_size = len(MAGIC) + 4 + args.cells * (6 * 16 + 18)
    if len(output) != expected_size:
        raise AssertionError(f"packed size drift: {len(output)} != {expected_size}")
    args.output.write_bytes(output)
    print(f"cells={args.cells}")
    print(f"bytes={len(output)}")
    print(f"sha256={hashlib.sha256(output).hexdigest()}")


if __name__ == "__main__":
    main()
