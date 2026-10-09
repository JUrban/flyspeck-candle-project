#!/usr/bin/env python3
"""Pack the checked historical-dihedral center-jet transfer gate.

The two text inputs are authenticated development oracles.  The resulting
payload contains only scale-2^40 intervals: six center coordinates, two
square-root certificates, five reciprocal certificates, and the expected
value plus six gradient entries.  The CakeML checker recomputes the complete
center jet and checks every supplied numerical certificate before comparing
the result.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct


EXPECTED_KERNEL_SHA256 = (
    "a4591c1d5e93fc9fa3cfae61585d42b32f181afb69955d7dc85cebac45d55d3a"
)
EXPECTED_RECIPROCAL_SHA256 = (
    "8983a97132fc395213c6bd0ff1eb24bbe7390480ddd04a3500ce6791cd095b92"
)
KERNEL_PREFIX = "CANDLE_NL_NATIVE_HISTORICAL_DIHEDRAL_KERNEL"
RECIPROCAL_PREFIX = "CANDLE_NL_NATIVE_HISTORICAL_RECIPROCAL"
MAGIC = b"CNLHDF01"
FULL_CELLS = 4173
RECIPROCALS_PER_CELL = 14
FIRST_RECIPROCALS = 5
WORD_LIMIT = 1 << 64


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


def interval(text: str, context: str) -> tuple[int, int]:
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError(f"malformed interval at {context}: {text}")
    lower, upper = map(int, parts)
    if lower > upper:
        raise ValueError(f"reversed interval at {context}: {text}")
    if abs(lower) >= WORD_LIMIT or abs(upper) >= WORD_LIMIT:
        raise ValueError(f"word64 overflow at {context}: {text}")
    return lower, upper


def interval_list(text: str, count: int, context: str) -> list[tuple[int, int]]:
    values = [interval(item, f"{context}[{index}]")
              for index, item in enumerate(text.split(","))]
    if len(values) != count:
        raise ValueError(f"{context} arity drift: {len(values)} != {count}")
    return values


def encode_endpoint(value: int) -> bytes:
    return struct.pack("<BQ", int(value < 0), abs(value))


def encode_interval(value: tuple[int, int]) -> bytes:
    return encode_endpoint(value[0]) + encode_endpoint(value[1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("kernel_trace", type=Path)
    parser.add_argument("reciprocal_trace", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cells", type=int, default=FULL_CELLS)
    args = parser.parse_args()
    if not 1 <= args.cells <= FULL_CELLS:
        raise ValueError(f"cell count out of range: {args.cells}")

    kernel_lines = authenticated_lines(
        args.kernel_trace, EXPECTED_KERNEL_SHA256, "kernel trace")
    reciprocal_lines = authenticated_lines(
        args.reciprocal_trace, EXPECTED_RECIPROCAL_SHA256,
        "reciprocal trace")
    if len(kernel_lines) != FULL_CELLS:
        raise ValueError(f"kernel trace count drift: {len(kernel_lines)}")
    if len(reciprocal_lines) != FULL_CELLS * RECIPROCALS_PER_CELL:
        raise ValueError(
            f"reciprocal trace count drift: {len(reciprocal_lines)}")

    payload = bytearray(MAGIC)
    payload.extend(struct.pack("<I", args.cells))
    for index in range(args.cells):
        kernel = fields_of(
            kernel_lines[index], KERNEL_PREFIX, f"kernel row {index}")
        if int(kernel.get("index", "-1")) != index:
            raise ValueError(f"kernel index drift at row {index}")
        values = interval_list(
            kernel["center_environment"], 6,
            f"kernel {index} center environment")
        values.extend([
            interval(kernel["center_root_delta"],
                     f"kernel {index} root delta"),
            interval(kernel["center_root_four_x0"],
                     f"kernel {index} root four-x0"),
        ])
        reciprocal_base = index * RECIPROCALS_PER_CELL
        for ordinal in range(FIRST_RECIPROCALS):
            record = fields_of(
                reciprocal_lines[reciprocal_base + ordinal],
                RECIPROCAL_PREFIX,
                f"reciprocal row {reciprocal_base + ordinal}")
            if (int(record.get("index", "-1")) != index or
                    int(record.get("ordinal", "-1")) != ordinal):
                raise ValueError(
                    f"reciprocal identity drift at {index}:{ordinal}")
            values.append(interval(
                record["output"], f"reciprocal {index}:{ordinal} output"))
        values.append(interval(
            kernel["center_value"], f"kernel {index} center value"))
        values.extend(interval_list(
            kernel["center_gradient"], 6,
            f"kernel {index} center gradient"))
        if len(values) != 20:
            raise AssertionError(f"cell shape drift at {index}: {len(values)}")
        for value in values:
            payload.extend(encode_interval(value))

    expected_size = len(MAGIC) + 4 + args.cells * 20 * 18
    if len(payload) != expected_size:
        raise AssertionError(f"payload size drift: {len(payload)} != {expected_size}")
    args.output.write_bytes(payload)
    print(f"cells={args.cells}")
    print(f"bytes={len(payload)}")
    print(f"sha256={hashlib.sha256(payload).hexdigest()}")


if __name__ == "__main__":
    main()
