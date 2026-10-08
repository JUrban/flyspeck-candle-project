#!/usr/bin/env python3
"""Hash native nonlinear Taylor stack traces like Candle's discriminator.

The native trace stores the stack from bottom to top and serializes every
Taylor value as a domain bit followed by 35 signed fixed-scale intervals.
Candle's development discriminator hashes that same logical stream with a
64-bit FNV-1a-style multiplier.  This tool validates the trace shape and
prints one post-instruction stack hash per row.
"""

from __future__ import annotations

import argparse
from pathlib import Path


MASK64 = (1 << 64) - 1
OFFSET_BASIS = 1469598103934665603
FNV_PRIME = 1099511628211
DIMENSIONS = 6
INTERVALS_PER_TAYLOR = (
    1 + DIMENSIONS + 1 + DIMENSIONS + DIMENSIONS * (DIMENSIONS + 1) // 2
)
FIELDS_PER_TAYLOR = 1 + 2 * INTERVALS_PER_TAYLOR


def hash_word(current: int, value: int) -> int:
    return (current * FNV_PRIME + value) & MASK64


def hash_signed(current: int, value: int) -> int:
    current = hash_word(current, int(value < 0))
    return hash_word(current, abs(value))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    parser.add_argument(
        "--hol-list",
        action="store_true",
        help="print a HOL word64 list instead of a two-column table",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with args.trace.open(encoding="ascii", newline="") as stream:
        header = stream.readline().rstrip("\n").split("\t")
        if len(header) != 3 or header[0] != "CANDLE_NL_NATIVE_STATE_TRACE_V1":
            raise SystemExit("invalid native state-trace header")
        instruction_count = int(header[1])
        scale = int(header[2])
        if instruction_count <= 0 or scale <= 0:
            raise SystemExit("invalid instruction count or scale")

        rows: list[tuple[int, int]] = []
        for expected_index, raw_line in enumerate(stream):
            fields = raw_line.rstrip("\n").split("\t")
            if len(fields) < 4:
                raise SystemExit(f"truncated trace row {expected_index}")
            index = int(fields[0])
            if index != expected_index:
                raise SystemExit(
                    f"trace index drift: expected {expected_index}, got {index}"
                )
            int(fields[2])  # sqrt slot; validated as an integer but not hashed.
            stack_size = int(fields[3])
            expected_fields = 4 + stack_size * FIELDS_PER_TAYLOR
            if len(fields) != expected_fields:
                raise SystemExit(
                    f"trace row {index}: expected {expected_fields} fields, "
                    f"got {len(fields)}"
                )

            current = hash_word(OFFSET_BASIS, stack_size)
            cursor = 4
            for _ in range(stack_size):
                domain = int(fields[cursor])
                cursor += 1
                if domain not in (0, 1):
                    raise SystemExit(f"trace row {index}: invalid domain bit")
                current = hash_word(current, domain)
                for _ in range(INTERVALS_PER_TAYLOR):
                    lower = int(fields[cursor])
                    upper = int(fields[cursor + 1])
                    cursor += 2
                    current = hash_signed(current, lower)
                    current = hash_signed(current, upper)
            rows.append((index, current))

        if len(rows) != instruction_count:
            raise SystemExit(
                f"expected {instruction_count} trace rows, got {len(rows)}"
            )

    if args.hol_list:
        print("[")
        for offset in range(0, len(rows), 4):
            chunk = "; ".join(f"{value}w" for _, value in rows[offset : offset + 4])
            suffix = ";" if offset + 4 < len(rows) else ""
            print(f"  {chunk}{suffix}")
        print("]")
    else:
        print("index\thash")
        for index, value in rows:
            print(f"{index}\t{value}")


if __name__ == "__main__":
    main()
