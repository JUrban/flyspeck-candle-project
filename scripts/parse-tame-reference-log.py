#!/usr/bin/env python3
"""Decode unary Isabelle2014 tame-reference value output into compact JSON."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path


NUMBER_FIELDS = (
    "visited_nodes",
    "final_visits",
    "raw_children",
    "next_tame0_children",
    "retained_children",
    "early_pruned_children",
    "final_pruned_children",
    "maximum_frontier",
)
BOOLEAN_FIELDS = (
    "saw_quadrilateral",
    "saw_exceptional_face",
    "saw_nonzero_excess",
    "saw_multiple_sizes",
)


def read_bytes(path: Path) -> bytes:
    if path.suffix == ".gz":
        with gzip.open(path, "rb") as source:
            return source.read()
    return path.read_bytes()


def field_spans(record: bytes) -> dict[str, bytes]:
    fields = NUMBER_FIELDS + BOOLEAN_FIELDS
    positions = []
    for field in fields:
        match = re.search(rb"\b" + field.encode() + rb"\s*=", record)
        if match is None:
            raise ValueError(f"missing field {field}")
        positions.append((match.start(), match.end(), field))
    positions.sort()
    result = {}
    for index, (_, start, field) in enumerate(positions):
        end = positions[index + 1][0] if index + 1 < len(positions) else len(record)
        result[field] = record[start:end]
    return result


def decode_records(data: bytes) -> list[dict[str, object]]:
    starts = [match.start() for match in re.finditer(rb"\bvisited_nodes\s*=", data)]
    records = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(data)
        spans = field_spans(data[start:end])
        decoded: dict[str, object] = {
            field: spans[field].count(b"Suc") for field in NUMBER_FIELDS
        }
        for field in BOOLEAN_FIELDS:
            match = re.search(rb"\b(True|False)\b", spans[field])
            if match is None:
                raise ValueError(f"bad Boolean field {field}")
            decoded[field] = match.group(1) == b"True"

        # Bounded summaries print a leading frontier length before the record.
        record_open = data.rfind(b"(|", max(0, start - 200000), start)
        quote_open = data.rfind(b'"(', max(0, start - 200000), start)
        if quote_open >= 0 and record_open >= quote_open:
            prefix = data[quote_open:record_open]
            if b"Suc" in prefix:
                decoded["frontier_length"] = prefix.count(b"Suc")
        records.append(decoded)
    return records


def decode_timings(data: bytes) -> dict[str, object]:
    values = []
    command_total = 0.0
    for match in re.finditer(rb"command_timing = \x05\x06:\x06([^\x05]*)", data):
        payload = match.group(1)
        name = re.search(rb"(?:^|\x06)name=([^\x06]+)", payload)
        elapsed = re.search(rb"(?:^|\x06)elapsed=([0-9.]+)", payload)
        offset = re.search(rb"(?:^|\x06)offset=([0-9]+)", payload)
        if elapsed is None:
            continue
        seconds = float(elapsed.group(1))
        command_total += seconds
        if name is not None and name.group(1) == b"value":
            values.append(
                {
                    "offset": int(offset.group(1)) if offset is not None else None,
                    "elapsed_seconds": seconds,
                }
            )
    theory = re.search(
        rb"\fTiming = \x05\x06:\x06([^\x05]*)", data
    )
    theory_timing = None
    if theory is not None:
        theory_timing = {}
        for key in (b"threads", b"elapsed", b"cpu", b"gc", b"factor"):
            value = re.search(rb"(?:^|\x06)" + key + rb"=([0-9.]+)", theory.group(1))
            if value is not None:
                theory_timing[key.decode()] = float(value.group(1))
    return {
        "value_commands": values,
        "all_command_elapsed_seconds": round(command_total, 3),
        "non_value_command_elapsed_seconds": round(
            command_total - sum(item["elapsed_seconds"] for item in values), 3
        ),
        "theory_timing": theory_timing,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("session_log", type=Path)
    args = parser.parse_args()
    raw = args.session_log.read_bytes()
    data = read_bytes(args.session_log)
    result = {
        "session_log": str(args.session_log),
        "session_log_sha256": hashlib.sha256(raw).hexdigest(),
        "decoded_records": decode_records(data),
        "timings": decode_timings(data),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
