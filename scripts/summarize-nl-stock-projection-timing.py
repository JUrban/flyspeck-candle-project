#!/usr/bin/env python3
"""Summarize one controlled stock NL projection timing run."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    nanoseconds: int
    cpu_ticks: int
    marker: str


def parse_receipt(path: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def parse_elapsed(value: str) -> float:
    fields = value.split(":")
    if len(fields) == 2:
        minutes, seconds = fields
        return 60.0 * float(minutes) + float(seconds)
    if len(fields) == 3:
        hours, minutes, seconds = fields
        return 3600.0 * float(hours) + 60.0 * float(minutes) + float(seconds)
    raise ValueError(f"unsupported elapsed time: {value!r}")


def parse_gnu_time(path: pathlib.Path) -> dict[str, float | int]:
    patterns = {
        "user_seconds": r"^\s*User time \(seconds\):\s*(\S+)$",
        "system_seconds": r"^\s*System time \(seconds\):\s*(\S+)$",
        "elapsed_text": (
            r"^\s*Elapsed \(wall clock\) time \(h:mm:ss or m:ss\):\s*(\S+)$"
        ),
        "peak_rss_kib": r"^\s*Maximum resident set size \(kbytes\):\s*(\d+)$",
        "swaps": r"^\s*Swaps:\s*(\d+)$",
        "exit_status": r"^\s*Exit status:\s*(\d+)$",
    }
    found: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        for key, pattern in patterns.items():
            match = re.match(pattern, line)
            if match:
                found[key] = match.group(1)
    missing = sorted(set(patterns) - set(found))
    if missing:
        raise ValueError(f"missing GNU time fields: {missing}")
    user = float(found["user_seconds"])
    system = float(found["system_seconds"])
    return {
        "user_seconds": user,
        "system_seconds": system,
        "cpu_seconds": user + system,
        "wall_seconds": parse_elapsed(found["elapsed_text"]),
        "peak_rss_kib": int(found["peak_rss_kib"]),
        "swaps": int(found["swaps"]),
        "exit_status": int(found["exit_status"]),
    }


def parse_events(path: pathlib.Path) -> list[Event]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "utc_nanoseconds\tprocess_tree_cpu_ticks\tmarker":
        raise ValueError("unexpected phase table header")
    events: list[Event] = []
    for line in lines[1:]:
        timestamp, ticks, marker = line.split("\t", 2)
        events.append(Event(int(timestamp), int(ticks), marker))
    if not events:
        raise ValueError("empty phase table")
    for previous, current in zip(events, events[1:]):
        if current.nanoseconds < previous.nanoseconds:
            raise ValueError("non-monotonic phase timestamp")
        if current.cpu_ticks < previous.cpu_ticks:
            raise ValueError("non-monotonic process-tree CPU ticks")
    return events


def select(events: list[Event], needle: str) -> list[Event]:
    return [event for event in events if needle in event.marker]


def exactly_one(events: list[Event], needle: str) -> Event:
    matches = select(events, needle)
    if len(matches) != 1:
        raise ValueError(f"expected one {needle!r} marker, found {len(matches)}")
    return matches[0]


def phase(start: Event, end: Event, ticks_per_second: int) -> dict[str, float]:
    if end.nanoseconds < start.nanoseconds or end.cpu_ticks < start.cpu_ticks:
        raise ValueError("reversed phase boundary")
    return {
        "cpu_seconds": (end.cpu_ticks - start.cpu_ticks) / ticks_per_second,
        "wall_seconds": (end.nanoseconds - start.nanoseconds) / 1_000_000_000,
    }


def summarize(directory: pathlib.Path) -> dict[str, object]:
    receipt = parse_receipt(directory / "timing.receipt")
    probe_receipt = parse_receipt(directory / "stock" / "input-probe.receipt")
    events = parse_events(directory / "stock.phases.tsv")
    ticks_per_second = int(receipt["clock_ticks_per_second"])

    ack = exactly_one(events, "CANDLE_RESTORE_INPUT_ACK")
    cells_begin = exactly_one(
        events, "CANDLE_NL_STOCK_PROJECTION_CELLS|preparation|begin"
    )
    cells_end = exactly_one(events, "CANDLE_NL_STOCK_PROJECTION_CELLS_OK")
    plan_end = exactly_one(events, "CANDLE_NL_STOCK_PROJECTION_REPAIRED_PLAN_OK")
    complete_begin = exactly_one(
        events, "CANDLE_NL_STOCK_PROJECTION_COMPLETE|complete-check|begin"
    )
    complete_end = exactly_one(
        events, "CANDLE_NL_STOCK_PROJECTION_COMPLETE|complete-check|end"
    )
    root_begin = exactly_one(
        events, "CANDLE_NL_STOCK_PROJECTION_COMPLETE|root-handoff|begin"
    )
    root_end = exactly_one(
        events, "CANDLE_NL_STOCK_PROJECTION_COMPLETE|root-handoff|end"
    )
    reconstruction_begin = exactly_one(
        events, "CANDLE_NL_STOCK_PROJECTION_COMPLETE|reconstruction|begin"
    )
    reconstruction_end = exactly_one(
        events, "CANDLE_NL_STOCK_PROJECTION_COMPLETE|reconstruction|end"
    )
    final = exactly_one(events, "CANDLE_NL_STOCK_PROJECTION_COMPLETE_OK")

    compute_begin = exactly_one(events, "phase=variable-complete-compute-begin")
    compute_end = exactly_one(events, "phase=variable-complete-compute-end")
    validation_begin = exactly_one(
        events, "phase=variable-complete-validation-begin"
    )
    validation_end = exactly_one(events, "phase=variable-complete-validation-end")
    encoding_begin = exactly_one(
        events, "phase=variable-complete-certificate-encoding-begin"
    )
    encoding_end = exactly_one(
        events, "phase=variable-complete-certificate-encoding-end"
    )
    handoff_begins = select(events, "phase=variable-complete-handoff-begin")
    handoff_ends = select(events, "phase=variable-complete-handoff-end")
    if len(handoff_begins) != 2 or len(handoff_ends) != 2:
        raise ValueError("expected two complete-handoff marker pairs")

    ordered = [
        ack,
        cells_begin,
        cells_end,
        plan_end,
        complete_begin,
        encoding_begin,
        encoding_end,
        validation_begin,
        validation_end,
        compute_begin,
        compute_end,
        handoff_begins[0],
        handoff_ends[0],
        complete_end,
        root_begin,
        handoff_begins[1],
        handoff_ends[1],
        root_end,
        reconstruction_begin,
        reconstruction_end,
        final,
    ]
    if ordered != sorted(ordered, key=lambda event: event.nanoseconds):
        raise ValueError("unexpected phase order")

    phases = {
        "post_restore_total": phase(ack, final, ticks_per_second),
        "source_frontend": phase(ack, cells_begin, ticks_per_second),
        "cell_materialization": phase(cells_begin, cells_end, ticks_per_second),
        "repaired_plan_materialization": phase(cells_end, plan_end, ticks_per_second),
        "pre_complete_gap": phase(plan_end, complete_begin, ticks_per_second),
        "complete_check": phase(complete_begin, complete_end, ticks_per_second),
        "certificate_encoding": phase(encoding_begin, encoding_end, ticks_per_second),
        "validation": phase(validation_begin, validation_end, ticks_per_second),
        "kernel_compute": phase(compute_begin, compute_end, ticks_per_second),
        "complete_handoff": phase(
            handoff_begins[0], handoff_ends[0], ticks_per_second
        ),
        "root_handoff": phase(root_begin, root_end, ticks_per_second),
        "root_internal_handoff": phase(
            handoff_begins[1], handoff_ends[1], ticks_per_second
        ),
        "reconstruction": phase(
            reconstruction_begin, reconstruction_end, ticks_per_second
        ),
    }

    gnu_time = parse_gnu_time(directory / "stock.time")
    if gnu_time["exit_status"] != 0 or gnu_time["swaps"] != 0:
        raise ValueError("timed run did not exit cleanly without swaps")
    if receipt.get("theorem_digest") != "ad47952de83b1c56748556d69c4e1cb0":
        raise ValueError("unexpected theorem digest")

    return {
        "status": 0,
        "source_id": receipt["source_id"],
        "parameter_index": int(receipt["parameter_index"]),
        "original_cells": int(receipt["original_cells"]),
        "repaired_cells": int(receipt["repaired_cells"]),
        "token_items": int(receipt["token_items"]),
        "pinned_cpu": int(receipt["pinned_cpu"]),
        "restore_to_ready_seconds": float(probe_receipt["restore_to_repl_ready_seconds"]),
        "gnu_time": gnu_time,
        "phases": phases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=pathlib.Path)
    arguments = parser.parse_args()
    result = summarize(arguments.directory)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
