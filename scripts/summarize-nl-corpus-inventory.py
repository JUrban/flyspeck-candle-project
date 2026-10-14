#!/usr/bin/env python3
"""Summarize the direct Flyspeck nonlinear source inventory.

The action-296 capture writes one pipe-delimited marker per source ID.  This
tool keeps family selection reproducible: it validates unique source IDs and
reports both exact serialized constant-signature families and the family
containing a requested source.  The capture used comma-separated constant
names even though `,` is itself a HOL constant, so the serialized field is
kept opaque rather than being split into a misleading list.
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
    result = {
        "source_ids": len(sources),
        "parameter_count": sum(source.parameter_count for source in sources),
        "formula_digests": len({source.formula_digest for source in sources}),
        "serialized_signature_families": len(families),
        "families": family_rows,
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
    args = parser.parse_args()
    if args.top < 0:
        parser.error("--top must be nonnegative")
    result = summarize(read_sources(args.inventory_log), args.signature_of)
    result["families"] = result["families"][: args.top]
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
