#!/usr/bin/env python3
"""Pack genuine case16594 boxes and scalar certificates for Candle.

This is untrusted preparation.  The eventual verified parser/checker must
validate the version, exact cell/record counts, tags, option flags, widths,
certificate conditions, source-program identity, and final acceptance.  The
packer pins the DEVELOPMENT fixtures so performance experiments remain
reproducible; its output is never itself proof authority.

Format (little endian):

* 8-byte magic ``CNLCKR01``;
* uint32 cell count and uint32 records per cell;
* for each cell, 30 uint64 words: six Taylor box interval pairs, six center
  interval pairs, then six upward radii.  The Taylor box is reconstructed as
  ``center + [-radius,+radius]``.  This is the (slightly wider) enclosure used
  by the native complete-result path, rather than an independently rounded
  copy of the source endpoints;
* for each of 31 scalar records, one tag byte, one option-flag byte, then ten
  signed endpoints.  A signed endpoint is a sign byte followed by its uint64
  magnitude.  Unused endpoints remain zero and are rejected if they drift.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
from pathlib import Path
import struct


EXPECTED_JOBS_SHA256 = (
    "236c4ffa1773b92c80584defa24beeddfb20b59811bc287a4f4770da87ac8e80"
)
EXPECTED_CERTIFICATES_SHA256 = (
    "a320e38824920816c44ff961c42fb3007369781bc2bc55521f1907aa7dbe1a86"
)
MAGIC = b"CNLCKR01"
CELL_COUNT = 875
RECORDS_PER_CELL = 31
SCALE = 1 << 40
WORD_LIMIT = 1 << 64
TAGS = {"sqrt": 0, "inverse": 1, "atan": 2}


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


def checked_word(value: int, context: str) -> int:
    if not 0 <= value < WORD_LIMIT:
        raise ValueError(f"word width/sign drift at {context}: {value}")
    return value


def pack_jobs(payload: bytes) -> list[bytes]:
    rows = payload.decode("ascii").splitlines()
    if len(rows) != CELL_COUNT:
        raise ValueError(f"job row count drift: {len(rows)}")
    result = []
    for expected_index, row in enumerate(rows):
        fields = row.split("\t")
        if len(fields) != 5 or int(fields[0]) != expected_index:
            raise ValueError(f"malformed job row {expected_index}")
        lower = [Fraction(value) for value in fields[3].split(",")]
        upper = [Fraction(value) for value in fields[4].split(",")]
        if len(lower) != 6 or len(upper) != 6:
            raise ValueError(f"box width drift at row {expected_index}")
        box: list[int] = []
        centers: list[int] = []
        radii: list[int] = []
        for coordinate, (lo, hi) in enumerate(zip(lower, upper)):
            if lo > hi:
                raise ValueError(f"reversed box at {expected_index}[{coordinate}]")
            midpoint = (lo + hi) / 2
            radius = (hi - lo) / 2
            source_lower = checked_word(floor_scaled(lo), "source box lower")
            source_upper = checked_word(ceil_scaled(hi), "source box upper")
            center_lower = checked_word(floor_scaled(midpoint), "center lower")
            center_upper = checked_word(ceil_scaled(midpoint), "center upper")
            radius_upper = checked_word(ceil_scaled(radius), "radius")
            taylor_lower = checked_word(
                center_lower - radius_upper, "Taylor box lower"
            )
            taylor_upper = checked_word(
                center_upper + radius_upper, "Taylor box upper"
            )
            if taylor_lower > source_lower or taylor_upper < source_upper:
                raise AssertionError(
                    f"Taylor box does not enclose source at "
                    f"{expected_index}[{coordinate}]"
                )
            box.extend([taylor_lower, taylor_upper])
            centers.extend([center_lower, center_upper])
            radii.append(radius_upper)
        result.append(struct.pack("<30Q", *(box + centers + radii)))
    return result


def pack_signed(value: int, context: str) -> bytes:
    magnitude = checked_word(abs(value), context)
    return struct.pack("<BQ", int(value < 0), magnitude)


def pack_certificates(payload: bytes) -> list[list[bytes]]:
    rows = payload.decode("ascii").splitlines()
    if len(rows) != CELL_COUNT * RECORDS_PER_CELL:
        raise ValueError(f"certificate row count drift: {len(rows)}")
    cells: list[list[bytes]] = [[] for _ in range(CELL_COUNT)]
    counts = {kind: 0 for kind in TAGS}
    options = [0, 0]
    for row_index, row in enumerate(rows):
        fields = row.split("\t")
        if len(fields) != 15:
            raise ValueError(f"certificate row shape drift: {row_index}")
        cell = int(fields[0])
        ordinal = int(fields[1])
        if cell != row_index // RECORDS_PER_CELL or ordinal != row_index % RECORDS_PER_CELL:
            raise ValueError(f"certificate order drift: {row_index}")
        kind = fields[2]
        if kind not in TAGS or fields[3] not in {"0", "1"} or fields[4] not in {"0", "1"}:
            raise ValueError(f"certificate tag/flag drift: {row_index}")
        lower_option = int(fields[3])
        upper_option = int(fields[4])
        if kind != "atan" and (lower_option or upper_option):
            raise ValueError(f"non-atan option flag: {row_index}")
        values = [int(value) for value in fields[5:]]
        pairs = list(zip(values[0::2], values[1::2]))
        if any(lower > upper for lower, upper in pairs):
            raise ValueError(f"reversed interval: {row_index}")
        if kind == "inverse" and any(value != 0 for value in values[4:]):
            raise ValueError(f"inverse padding drift: {row_index}")
        if kind == "atan" and any(value != 0 for value in values[8:]):
            raise ValueError(f"atan padding drift: {row_index}")
        record = bytearray(struct.pack("<BB", TAGS[kind], lower_option | (upper_option << 1)))
        for endpoint, value in enumerate(values):
            record.extend(pack_signed(value, f"record {row_index} endpoint {endpoint}"))
        if len(record) != 92:
            raise AssertionError("packed record width drift")
        cells[cell].append(bytes(record))
        counts[kind] += 1
        options[0] += lower_option
        options[1] += upper_option
    if counts != {"sqrt": 8750, "inverse": 12250, "atan": 6125}:
        raise ValueError(f"certificate kind-count drift: {counts}")
    if options != [107, 107] or any(len(cell) != RECORDS_PER_CELL for cell in cells):
        raise ValueError(f"certificate option/shape drift: {options}")
    return cells


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("jobs", type=Path)
    parser.add_argument("certificates", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    jobs = pack_jobs(authenticated_bytes(args.jobs, EXPECTED_JOBS_SHA256, "jobs"))
    certificates = pack_certificates(
        authenticated_bytes(
            args.certificates, EXPECTED_CERTIFICATES_SHA256, "certificates"
        )
    )
    output = bytearray(MAGIC)
    output.extend(struct.pack("<II", CELL_COUNT, RECORDS_PER_CELL))
    for job, cell_certificates in zip(jobs, certificates):
        output.extend(job)
        for certificate in cell_certificates:
            output.extend(certificate)
    expected_size = 16 + CELL_COUNT * (30 * 8 + RECORDS_PER_CELL * 92)
    if len(output) != expected_size:
        raise AssertionError(f"packed size drift: {len(output)} != {expected_size}")
    args.output.write_bytes(output)
    print(f"bytes={len(output)}")
    print(f"sha256={hashlib.sha256(output).hexdigest()}")


if __name__ == "__main__":
    main()
