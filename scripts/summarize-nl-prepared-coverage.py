#!/usr/bin/env python3
"""Summarize proved-preparation coverage of the Flyspeck NL source corpus."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path
from typing import NamedTuple


PREPARED_RE = re.compile(
    r"^CANDLE_NL_PREPARED(_EXPANDED)?_SUPPORT_PROBE "
    r"DEVELOPMENT_NON_RELEASE "
    r"source_id=(.*?) dimension=([0-9]+) disjuncts=([0-9]+) "
    r"unsupported=(.*?) elapsed_seconds=(.*)$"
)
ERROR_RE = re.compile(
    r"^CANDLE_NL_PREPARED(_EXPANDED)?_SUPPORT_PROBE_ERROR "
    r"DEVELOPMENT_NON_RELEASE "
    r"source_id=(.*?) message=(.*)$"
)
SELECTED_RE = re.compile(
    r"^CANDLE_NL_SELECTED_LEAF_COUNT DEVELOPMENT_NON_RELEASE "
    r"source_id=(.*?) selected_leaves=([0-9]+)$"
)


class PreparedRecord(NamedTuple):
    normalization: str
    source_id: str
    dimension: int
    disjuncts: int
    unsupported: tuple[str, ...]
    error: str | None


def load_inventory_module(project_root: Path):
    source = project_root / "scripts" / "summarize-nl-corpus-inventory.py"
    spec = importlib.util.spec_from_file_location("nl_corpus_inventory", source)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load nonlinear corpus inventory parser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_prepared(path: Path) -> list[PreparedRecord]:
    records: list[PreparedRecord] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
    ):
        match = PREPARED_RE.match(line)
        if match is not None:
            expanded, source_id, dimension, disjuncts, unsupported, _elapsed = (
                match.groups()
            )
            heads = tuple(value for value in unsupported.split(",") if value)
            if len(set(heads)) != len(heads):
                raise ValueError(
                    f"duplicate unsupported head at line {line_number}"
                )
            records.append(
                PreparedRecord(
                    "expanded" if expanded else "strict",
                    source_id,
                    int(dimension),
                    int(disjuncts),
                    heads,
                    None,
                )
            )
            continue
        match = ERROR_RE.match(line)
        if match is not None:
            expanded, source_id, message = match.groups()
            records.append(
                PreparedRecord(
                    "expanded" if expanded else "strict",
                    source_id,
                    0,
                    0,
                    (),
                    message,
                )
            )
    if not records:
        raise ValueError("no prepared-coverage markers found")
    identities = [record.source_id for record in records]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate prepared-coverage source ID")
    if len({record.normalization for record in records}) != 1:
        raise ValueError("mixed prepared-coverage normalization modes")
    return records


def read_selected(path: Path) -> dict[str, int]:
    selected: dict[str, int] = {}
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
    ):
        match = SELECTED_RE.match(line)
        if match is None:
            continue
        source_id, count = match.groups()
        if source_id in selected:
            raise ValueError(
                f"duplicate selected-leaf source ID at line {line_number}"
            )
        selected[source_id] = int(count)
    if not selected:
        raise ValueError("no selected-leaf markers found")
    return selected


def summarize(
    prepared: list[PreparedRecord],
    inventory: list,
    selected: dict[str, int] | None = None,
) -> dict:
    inventory_by_id = {source.source_id: source for source in inventory}
    prepared_ids = {record.source_id for record in prepared}
    inventory_ids = set(inventory_by_id)
    unexpected = sorted(prepared_ids - inventory_ids)
    missing = sorted(inventory_ids - prepared_ids)
    if unexpected:
        raise ValueError(f"prepared coverage has unexpected IDs: {unexpected}")
    if selected is not None and set(selected) != inventory_ids:
        raise ValueError("selected-leaf IDs do not match the source inventory")

    supported = [
        record
        for record in prepared
        if record.error is None and not record.unsupported
    ]
    unsupported = [record for record in prepared if record.unsupported]
    errors = [record for record in prepared if record.error is not None]
    source_counts: Counter[str] = Counter()
    parameter_counts: Counter[str] = Counter()
    selected_counts: Counter[str] = Counter()
    signature_sources: Counter[tuple[str, ...]] = Counter()
    signature_parameters: Counter[tuple[str, ...]] = Counter()
    signature_selected: Counter[tuple[str, ...]] = Counter()
    for record in unsupported:
        signature = tuple(sorted(record.unsupported))
        signature_sources[signature] += 1
        signature_parameters[signature] += inventory_by_id[
            record.source_id
        ].parameter_count
        if selected is not None:
            signature_selected[signature] += selected[record.source_id]
        for head in record.unsupported:
            source_counts[head] += 1
            parameter_counts[head] += inventory_by_id[
                record.source_id
            ].parameter_count
            if selected is not None:
                selected_counts[head] += selected[record.source_id]

    ordered_heads = sorted(
        source_counts,
        key=lambda head: (
            -parameter_counts[head],
            -source_counts[head],
            head,
        ),
    )
    ordered_signatures = sorted(
        signature_sources,
        key=lambda signature: (
            -signature_parameters[signature],
            -signature_sources[signature],
            signature,
        ),
    )
    ordered_supported = sorted(
        supported,
        key=lambda record: (
            -inventory_by_id[record.source_id].parameter_count,
            record.source_id,
        ),
    )
    result = {
        "normalization": prepared[0].normalization,
        "complete": not missing,
        "inventory_source_ids": len(inventory),
        "prepared_source_ids": len(prepared),
        "missing_source_ids": missing,
        "supported_source_ids": len(supported),
        "supported_parameter_records": sum(
            inventory_by_id[record.source_id].parameter_count
            for record in supported
        ),
        "supported_sources": [
            {
                "source_id": record.source_id,
                "parameter_records": inventory_by_id[
                    record.source_id
                ].parameter_count,
                "dimension": record.dimension,
                "disjuncts": record.disjuncts,
            }
            for record in ordered_supported
        ],
        "unsupported_source_ids": len(unsupported),
        "unsupported_parameter_records": sum(
            inventory_by_id[record.source_id].parameter_count
            for record in unsupported
        ),
        "error_source_ids": len(errors),
        "error_parameter_records": sum(
            inventory_by_id[record.source_id].parameter_count
            for record in errors
        ),
        "dimensions": dict(
            sorted(
                Counter(
                    record.dimension
                    for record in prepared
                    if record.error is None
                ).items()
            )
        ),
        "disjuncts": dict(
            sorted(
                Counter(
                    record.disjuncts
                    for record in prepared
                    if record.error is None
                ).items()
            )
        ),
        "distinct_unsupported_signatures": len(signature_sources),
        "unsupported_signatures": [
            {
                "heads": list(signature),
                "source_ids": signature_sources[signature],
                "parameter_records": signature_parameters[signature],
                **(
                    {"selected_leaves": signature_selected[signature]}
                    if selected is not None
                    else {}
                ),
            }
            for signature in ordered_signatures
        ],
        "unsupported_heads": [
            {
                "head": head,
                "source_ids": source_counts[head],
                "parameter_records": parameter_counts[head],
                **(
                    {"selected_leaves": selected_counts[head]}
                    if selected is not None
                    else {}
                ),
            }
            for head in ordered_heads
        ],
    }
    if selected is not None:
        result.update(
            {
                "selected_leaves": sum(selected.values()),
                "missing_selected_leaves": sum(
                    selected[source_id] for source_id in missing
                ),
                "supported_selected_leaves": sum(
                    selected[record.source_id] for record in supported
                ),
                "unsupported_selected_leaves": sum(
                    selected[record.source_id] for record in unsupported
                ),
                "error_selected_leaves": sum(
                    selected[record.source_id] for record in errors
                ),
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("prepared_log", type=Path)
    parser.add_argument("inventory_log", type=Path)
    parser.add_argument("--selected-log", type=Path)
    parser.add_argument("--top", type=int, default=25)
    args = parser.parse_args()
    if args.top < 0:
        parser.error("--top must be nonnegative")
    project_root = Path(__file__).resolve().parent.parent
    inventory_module = load_inventory_module(project_root)
    result = summarize(
        read_prepared(args.prepared_log),
        inventory_module.read_sources(args.inventory_log),
        read_selected(args.selected_log) if args.selected_log else None,
    )
    result["unsupported_heads"] = result["unsupported_heads"][: args.top]
    result["supported_sources"] = result["supported_sources"][: args.top]
    result["unsupported_signatures"] = result["unsupported_signatures"][
        : args.top
    ]
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
