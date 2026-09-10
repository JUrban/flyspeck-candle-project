#!/usr/bin/env python3
"""Derive or check the canonical schema-4 shape authority from two reports."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("great100_report_schema.py").resolve()
SPEC = importlib.util.spec_from_file_location(
    "_great100_report_schema_derivation", MODULE_PATH,
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Great100 report schema derivation")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "mechanically enumerate every object, array, and discriminant in "
            "two qualified Great100 schema-4 reports"
        ),
    )
    parser.add_argument("report_one", type=Path)
    parser.add_argument("report_two", type=Path)
    parser.add_argument("--check", type=Path)
    arguments = parser.parse_args()
    derived = MODULE.derive_authority([
        ("run-001", arguments.report_one.read_bytes()),
        ("run-002", arguments.report_two.read_bytes()),
    ])
    payload = canonical_json_bytes(derived)
    if arguments.check is None:
        print(payload.decode("utf-8"), end="")
        return
    expected = arguments.check.read_bytes()
    if expected != payload:
        raise SystemExit("Great100 schema authority differs from qualified reports")
    print(json.dumps({
        "state": "matched",
        "report_schema": derived["report_schema"],
        "source_reports": derived["derived_from"],
        "object_paths": len(derived["objects"]),
        "array_paths": len(derived["arrays"]),
        "scalar_paths": len(derived["scalars"]),
        "discriminant_paths": len(derived["discriminants"]),
        "named_shapes": sorted(derived["named_shape_paths"]),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
