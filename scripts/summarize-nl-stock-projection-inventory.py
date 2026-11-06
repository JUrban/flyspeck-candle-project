#!/usr/bin/env python3
"""Join the sealed Flyspeck NL inventories for stock-route projection.

The detailed selected-leaf capture provides production `iargs` path shape and
historical C++ time estimates.  It deliberately does not provide numerical
certificate cell counts or internal certificate topology.  This script keeps
those fields visibly missing while selecting a deterministic, stratified seed
sample for the stock-route benchmark.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import NamedTuple


LEAF_MARKER = "CANDLE_NL_SELECTED_LEAF_DETAIL|"
SUMMARY_MARKER = "CANDLE_NL_SELECTED_LEAF_DETAIL_SUMMARY|"


class Leaf(NamedTuple):
    source_id: str
    leaf_index: int
    historical_msec: int
    depth: int
    bisects: int
    facets: int


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load inventory parser: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_leaf_details(path: Path) -> tuple[list[Leaf], dict[str, int]]:
    leaves: list[Leaf] = []
    summary: dict[str, int] | None = None
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
    ):
        if line.startswith(LEAF_MARKER):
            fields = line.split("|")
            if len(fields) != 7:
                raise ValueError(f"malformed leaf detail at line {line_number}")
            _, source_id, leaf_index, historical_msec, depth, bisects, facets = (
                fields
            )
            if not source_id:
                raise ValueError(f"empty source ID at line {line_number}")
            try:
                values = tuple(
                    int(value)
                    for value in (
                        leaf_index,
                        historical_msec,
                        depth,
                        bisects,
                        facets,
                    )
                )
            except ValueError as error:
                raise ValueError(
                    f"non-integer leaf detail at line {line_number}"
                ) from error
            if any(value < 0 for value in values):
                raise ValueError(f"negative leaf detail at line {line_number}")
            if values[2] != values[3] + values[4]:
                raise ValueError(f"inconsistent path depth at line {line_number}")
            leaves.append(Leaf(source_id, *values))
        elif line.startswith(SUMMARY_MARKER):
            fields = line.split("|")
            if len(fields) != 6:
                raise ValueError(f"malformed detail summary at line {line_number}")
            if summary is not None:
                raise ValueError("duplicate detail summary")
            try:
                summary = dict(
                    zip(
                        (
                            "source_ids",
                            "selected_leaves",
                            "production_iarg_nodes",
                            "historical_msec",
                            "max_depth",
                        ),
                        (int(value) for value in fields[1:]),
                        strict=True,
                    )
                )
            except ValueError as error:
                raise ValueError(
                    f"non-integer detail summary at line {line_number}"
                ) from error
    if not leaves:
        raise ValueError("no selected-leaf detail markers found")
    if summary is None:
        raise ValueError("selected-leaf detail summary missing")

    keys = [(leaf.source_id, leaf.leaf_index) for leaf in leaves]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate selected-leaf identity")
    by_source: dict[str, list[int]] = defaultdict(list)
    for leaf in leaves:
        by_source[leaf.source_id].append(leaf.leaf_index)
    for source_id, indices in by_source.items():
        if sorted(indices) != list(range(len(indices))):
            raise ValueError(f"non-contiguous leaf indices for {source_id}")

    measured = {
        "source_ids": len(by_source),
        "selected_leaves": len(leaves),
        "historical_msec": sum(leaf.historical_msec for leaf in leaves),
        "max_depth": max(leaf.depth for leaf in leaves),
    }
    for key, value in measured.items():
        if summary[key] != value:
            raise ValueError(f"detail summary mismatch for {key}")
    return leaves, summary


def quantiles(values: list[int]) -> dict[str, int]:
    if not values:
        return {}
    ordered = sorted(values)
    result = {}
    for name, numerator in (
        ("min", 0),
        ("p10", 10),
        ("p25", 25),
        ("p50", 50),
        ("p75", 75),
        ("p90", 90),
        ("p95", 95),
        ("p99", 99),
        ("max", 100),
    ):
        index = ((len(ordered) - 1) * numerator) // 100
        result[name] = ordered[index]
    return result


def group_of(record) -> str:
    if record.error is not None:
        return "preparation_error"
    if not record.unsupported:
        return "supported"
    return "+".join(sorted(record.unsupported))


def evenly_spaced(records: list[Leaf], count: int) -> list[Leaf]:
    if count <= 0 or not records:
        return []
    ordered = sorted(
        records,
        key=lambda leaf: (
            leaf.historical_msec,
            leaf.depth,
            leaf.source_id,
            leaf.leaf_index,
        ),
    )
    count = min(count, len(ordered))
    if count == 1:
        return [ordered[len(ordered) // 2]]
    indices = [round(index * (len(ordered) - 1) / (count - 1)) for index in range(count)]
    return [ordered[index] for index in indices]


def sample_allocations(groups: dict[str, list[Leaf]], target: int) -> dict[str, int]:
    if target <= 0:
        return {group: 0 for group in groups}
    allocations = {group: 0 for group in groups}
    preferred = {
        "supported": 12,
        "hminus": 4,
        "matan": 4,
        "acs+arc_hhn": 1,
        "asn": 1,
        "acs": 1,
    }
    for group, count in preferred.items():
        if group in groups:
            allocations[group] = min(count, len(groups[group]))
    while sum(allocations.values()) > target:
        group = max(allocations, key=lambda key: (allocations[key], key))
        allocations[group] -= 1
    while sum(allocations.values()) < target:
        eligible = [
            group
            for group in groups
            if allocations[group] < len(groups[group])
        ]
        if not eligible:
            break
        group = max(
            eligible,
            key=lambda key: (
                len(groups[key]) / (allocations[key] + 1),
                key == "supported",
                key,
            ),
        )
        allocations[group] += 1
    return allocations


def summarize(
    leaves: list[Leaf],
    detail_summary: dict[str, int],
    sources: list,
    prepared: list,
    target_sample: int,
) -> dict:
    source_by_id = {source.source_id: source for source in sources}
    prepared_by_id = {record.source_id: record for record in prepared}
    leaf_source_ids = {leaf.source_id for leaf in leaves}
    if leaf_source_ids != set(source_by_id):
        raise ValueError("leaf details do not match source inventory")
    if leaf_source_ids != set(prepared_by_id):
        raise ValueError("leaf details do not match prepared coverage")

    groups: dict[str, list[Leaf]] = defaultdict(list)
    families: dict[str, list[Leaf]] = defaultdict(list)
    for leaf in leaves:
        groups[group_of(prepared_by_id[leaf.source_id])].append(leaf)
        families[source_by_id[leaf.source_id].constants_serialized].append(leaf)

    group_rows = []
    for group, members in sorted(
        groups.items(), key=lambda item: (-len(item[1]), item[0])
    ):
        group_rows.append(
            {
                "group": group,
                "selected_leaves": len(members),
                "source_ids": len({leaf.source_id for leaf in members}),
                "historical_msec": sum(leaf.historical_msec for leaf in members),
                "historical_msec_quantiles": quantiles(
                    [leaf.historical_msec for leaf in members]
                ),
                "production_depth_quantiles": quantiles(
                    [leaf.depth for leaf in members]
                ),
            }
        )

    family_rows = []
    for signature, members in sorted(
        families.items(),
        key=lambda item: (
            -sum(leaf.historical_msec for leaf in item[1]),
            -len(item[1]),
            item[0],
        ),
    ):
        family_rows.append(
            {
                "signature_sha256_16": hashlib.sha256(
                    signature.encode("utf-8")
                ).hexdigest()[:16],
                "source_ids": len({leaf.source_id for leaf in members}),
                "selected_leaves": len(members),
                "historical_msec": sum(leaf.historical_msec for leaf in members),
                "examples": sorted({leaf.source_id for leaf in members})[:3],
            }
        )

    allocations = sample_allocations(groups, target_sample)
    selected: list[tuple[str, Leaf]] = []
    for group, count in sorted(allocations.items()):
        selected.extend((group, leaf) for leaf in evenly_spaced(groups[group], count))
    selected.sort(
        key=lambda item: (
            item[0],
            item[1].historical_msec,
            item[1].source_id,
            item[1].leaf_index,
        )
    )

    return {
        **detail_summary,
        "historical_cpp_hours": detail_summary["historical_msec"] / 3_600_000,
        "historical_msec_quantiles": quantiles(
            [leaf.historical_msec for leaf in leaves]
        ),
        "production_depth_quantiles": quantiles([leaf.depth for leaf in leaves]),
        "groups": group_rows,
        "top_signature_families": family_rows[:20],
        "candidate_sample": [
            {
                "group": group,
                "source_id": leaf.source_id,
                "leaf_index": leaf.leaf_index,
                "historical_msec": leaf.historical_msec,
                "production_depth": leaf.depth,
                "production_bisects": leaf.bisects,
                "production_facets": leaf.facets,
                "signature_sha256_16": hashlib.sha256(
                    source_by_id[leaf.source_id].constants_serialized.encode("utf-8")
                ).hexdigest()[:16],
            }
            for group, leaf in selected
        ],
        "candidate_sample_group_counts": dict(
            sorted(Counter(group for group, _ in selected).items())
        ),
        "missing_before_final_sample": [
            "numerical certificate cell count per selected leaf",
            "internal certificate topology token count/depth per selected leaf",
            "stock-checker operation coverage after prepared normalization",
        ],
        "scope_note": (
            "Historical C++ milliseconds and production iargs depth are sampling "
            "coordinates, not Candle runtime or numerical-certificate size."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("detail_log", type=Path)
    parser.add_argument("corpus_log", type=Path)
    parser.add_argument("prepared_log", type=Path)
    parser.add_argument("--sample-size", type=int, default=24)
    args = parser.parse_args()
    if not 20 <= args.sample_size <= 30:
        parser.error("--sample-size must be between 20 and 30")
    script_dir = Path(__file__).resolve().parent
    corpus_module = load_module(
        script_dir / "summarize-nl-corpus-inventory.py", "nl_corpus_inventory"
    )
    prepared_module = load_module(
        script_dir / "summarize-nl-prepared-coverage.py", "nl_prepared_coverage"
    )
    leaves, detail_summary = read_leaf_details(args.detail_log)
    result = summarize(
        leaves,
        detail_summary,
        corpus_module.read_sources(args.corpus_log),
        prepared_module.read_prepared(args.prepared_log),
        args.sample_size,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
