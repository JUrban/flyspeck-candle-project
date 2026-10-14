#!/usr/bin/env python3
"""Summarize the direct Flyspeck nonlinear source inventory.

The action-296 capture writes one pipe-delimited marker per source ID.  This
tool keeps family selection reproducible: it validates unique source IDs and
reports both exact serialized constant-signature families and the family
containing a requested source.  The capture used comma-separated constant
names even though `,` is itself a HOL constant.  The raw field therefore
remains the family identity; a narrowly checked decoder recovers the one
literal comma used by this capture for the usage inventory.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple


MARKER = "CANDLE_NL_CORPUS_SOURCE|"


class Source(NamedTuple):
    source_id: str
    parameter_count: int
    formula_digest: str
    constants_serialized: str


def read_sources(path: Path) -> list[Source]:
    sources: list[Source] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
    ):
        if MARKER not in line:
            continue
        record = line[line.index(MARKER) :]
        fields = record.split("|", 4)
        if len(fields) != 5:
            raise ValueError(f"malformed inventory marker at line {line_number}")
        _, source_id, parameter_count, formula_digest, constants = fields
        if not source_id or not formula_digest:
            raise ValueError(f"empty inventory identity at line {line_number}")
        try:
            count = int(parameter_count)
        except ValueError as error:
            raise ValueError(
                f"invalid parameter count at line {line_number}"
            ) from error
        if count < 0:
            raise ValueError(f"negative parameter count at line {line_number}")
        if not constants:
            raise ValueError(f"empty constant signature at line {line_number}")
        sources.append(Source(source_id, count, formula_digest, constants))
    if not sources:
        raise ValueError("no nonlinear corpus inventory markers found")
    identities = [source.source_id for source in sources]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate nonlinear source ID")
    return sources


def decode_constants(serialized: str) -> tuple[str, ...]:
    """Decode the canonical capture's sole delimiter-shaped constant.

    Every empty split field must occur as one adjacent pair, produced by the
    literal constant name `,`.  Anything else is schema drift and fails
    closed.  The exact raw string, not this decoded view, remains the family
    key.
    """
    parts = serialized.split(",")
    decoded: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part:
            decoded.append(part)
            index += 1
        elif index + 1 < len(parts) and not parts[index + 1]:
            decoded.append(",")
            index += 2
        else:
            raise ValueError("ambiguous comma-separated constant signature")
    if ",".join(decoded) != serialized:
        raise ValueError("constant signature does not round-trip")
    return tuple(decoded)


def summarize(sources: list[Source], signature_of: str | None) -> dict:
    families: dict[str, list[Source]] = defaultdict(list)
    for source in sources:
        families[source.constants_serialized].append(source)

    ordered = sorted(
        families.items(),
        key=lambda item: (
            -sum(source.parameter_count for source in item[1]),
            -len(item[1]),
            item[0],
        ),
    )
    family_rows = [
        {
            "source_ids": len(members),
            "parameter_count": sum(
                source.parameter_count for source in members
            ),
            "formula_digests": len(
                {source.formula_digest for source in members}
            ),
            "constants_serialized": constants,
            "examples": [source.source_id for source in members[:3]],
        }
        for constants, members in ordered
    ]
    constant_members: dict[str, list[Source]] = defaultdict(list)
    for source in sources:
        for constant in decode_constants(source.constants_serialized):
            constant_members[constant].append(source)
    constant_usage = [
        {
            "constant": constant,
            "source_ids": len(members),
            "parameter_count": sum(
                source.parameter_count for source in members
            ),
        }
        for constant, members in sorted(
            constant_members.items(),
            key=lambda item: (
                -sum(source.parameter_count for source in item[1]),
                -len(item[1]),
                item[0],
            ),
        )
    ]
    result = {
        "source_ids": len(sources),
        "parameter_count": sum(source.parameter_count for source in sources),
        "formula_digests": len({source.formula_digest for source in sources}),
        "serialized_signature_families": len(families),
        "families": family_rows,
        "constant_usage": constant_usage,
    }
    if signature_of is not None:
        matches = [source for source in sources if source.source_id == signature_of]
        if len(matches) != 1:
            raise ValueError(f"unknown nonlinear source ID: {signature_of}")
        members = families[matches[0].constants_serialized]
        result["selected_family"] = {
            "source_id": signature_of,
            "source_ids": len(members),
            "parameter_count": sum(
                source.parameter_count for source in members
            ),
            "formula_digests": len(
                {source.formula_digest for source in members}
            ),
            "constants_serialized": matches[0].constants_serialized,
            "members": [source.source_id for source in members],
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory_log", type=Path)
    parser.add_argument("--signature-of")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--constant-top", type=int, default=0)
    args = parser.parse_args()
    if args.top < 0:
        parser.error("--top must be nonnegative")
    if args.constant_top < 0:
        parser.error("--constant-top must be nonnegative")
    result = summarize(read_sources(args.inventory_log), args.signature_of)
    result["families"] = result["families"][: args.top]
    result["constant_usage"] = result["constant_usage"][: args.constant_top]
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
