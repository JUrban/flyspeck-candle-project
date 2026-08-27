#!/usr/bin/env python3
"""Cross-check the direct Dopen contract against independent inventory output."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def fail(message: str) -> None:
    raise SystemExit(f"direct Dopen corpus mismatch: {message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--findings", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    nodes = manifest["source_nodes"]
    contract = manifest["dopen_corpus_contract"]
    records: list[dict[str, Any]] = []
    stale: list[str] = []

    with args.findings.open(encoding="utf-8") as stream:
        for raw_line in stream:
            finding = json.loads(raw_line)
            if finding["category"] != "open.declaration":
                continue
            source = f'{finding["repository"]}:{finding["source_path"]}'
            node = nodes.get(source)
            if node is None:
                continue
            if finding["source_sha256"] != node["sha256"]:
                stale.append(source)
                continue
            details = finding["details"]
            records.append({
                "source": source,
                "line": finding["location"]["line"],
                "module_path": details["module_path"],
                "path_form": details["module_path_form"],
                "override_warning_suppression": (
                    details["override_warning_suppression"]
                ),
            })

    if stale:
        fail("stale selected inventory sources: " + ", ".join(sorted(set(stale))))
    records.sort(key=lambda entry: (
        entry["source"], entry["line"], entry["module_path"],
    ))
    digest = hashlib.sha256(json.dumps(
        records, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    forms = {
        form: sum(entry["path_form"] == form for entry in records)
        for form in ("simple", "dotted")
    }
    observed = {
        "occurrence_count": len(records),
        "source_file_count": len({entry["source"] for entry in records}),
        "module_path_count": len({entry["module_path"] for entry in records}),
        "path_form_counts": forms,
        "override_warning_suppression_count": sum(
            entry["override_warning_suppression"] for entry in records
        ),
        "site_sha256": digest,
    }
    for field, value in observed.items():
        if contract[field] != value:
            fail(f"{field}: manifest={contract[field]!r}, inventory={value!r}")
    print(
        "direct Dopen corpus ok: "
        f'{observed["occurrence_count"]} opens, '
        f'{observed["source_file_count"]} files, '
        f'{observed["module_path_count"]} module paths, {digest}'
    )


if __name__ == "__main__":
    main()
