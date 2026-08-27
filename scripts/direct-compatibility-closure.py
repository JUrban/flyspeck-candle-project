#!/usr/bin/env python3
"""Project the compatibility inventory onto the exact direct-source manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


CATEGORIES = [
    "ffi.custom_call",
    "ffi.ocaml_external_declaration",
    "module.declaration_alias",
    "module.declaration_first_class_unpack",
    "module.declaration_functor",
    "module.declaration_other",
    "module.declaration_structure",
    "module.first_class_pack",
    "module.first_class_unpack",
    "module.include",
    "module.type_declaration",
    "open.declaration",
    "open.local_let",
    "open.local_parenthesized",
    "pointer_equality.infix_use",
    "pointer_equality.operator_binding",
    "pointer_equality.operator_reference",
]


def canonical_bytes(document: Any) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_findings(path: Path) -> tuple[bytes, list[dict[str, Any]]]:
    raw = path.read_bytes()
    return raw, [json.loads(line) for line in raw.splitlines()]


def project(
    manifest_raw: bytes,
    manifest: dict[str, Any],
    findings_raw: bytes,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes = manifest["source_nodes"]
    strata = [item["name"] for item in manifest["build_strata"]]
    stratum_index = {name: index for index, name in enumerate(strata)}
    node_strata = manifest["source_node_strata"]
    records: list[dict[str, Any]] = []
    stale: set[str] = set()

    for finding in findings:
        source = f'{finding["repository"]}:{finding["source_path"]}'
        node = nodes.get(source)
        if node is None:
            continue
        if finding["source_sha256"] != node["sha256"]:
            stale.add(source)
            continue
        owned_strata = node_strata[source]
        if not owned_strata:
            raise ValueError(f"selected source has no stratum: {source}")
        earliest = min(owned_strata, key=stratum_index.__getitem__)
        record = {
            "category": finding["category"],
            "column": finding["location"]["column"],
            "earliest_stratum": earliest,
            "end_column": finding["location"]["end_column"],
            "end_line": finding["location"]["end_line"],
            "finding_id": finding["finding_id"],
            "lexeme": finding["lexeme"],
            "line": finding["location"]["line"],
            "source": source,
        }
        if finding["category"] == "open.local_parenthesized":
            body_form = finding.get("details", {}).get("body_form")
            if body_form not in ("operator_reference", "general_expression"):
                raise ValueError(
                    f"selected parenthesized local open lacks body classification: "
                    f'{finding["finding_id"]}'
                )
            record["body_form"] = body_form
            if body_form == "operator_reference":
                operator = finding["details"].get("operator")
                if not operator:
                    raise ValueError(
                        f"selected operator local open lacks operator: "
                        f'{finding["finding_id"]}'
                    )
                record["operator"] = operator
        records.append(record)

    if stale:
        raise ValueError("stale selected inventory sources: " + ", ".join(sorted(stale)))
    records.sort(key=lambda item: (
        item["source"], item["line"], item["column"],
        item["category"], item["finding_id"],
    ))

    by_category = Counter(item["category"] for item in records)
    by_repository = Counter(item["source"].split(":", 1)[0] for item in records)
    by_stratum = Counter(item["earliest_stratum"] for item in records)
    by_category_and_stratum: dict[str, Counter[str]] = defaultdict(Counter)
    paths_by_category: dict[str, set[str]] = defaultdict(set)
    for item in records:
        by_category_and_stratum[item["category"]][item["earliest_stratum"]] += 1
        paths_by_category[item["category"]].add(item["source"])

    selected_local_opens = [
        item for item in records
        if item["category"] == "open.local_parenthesized"
    ]
    local_open_body_forms = Counter(
        item["body_form"] for item in selected_local_opens
    )
    local_open_operators = Counter(
        item["operator"] for item in selected_local_opens
        if item["body_form"] == "operator_reference"
    )

    normalized_sources = sorted(
        source for source, node in nodes.items()
        if "execution_normalization" in node
    )
    p0_non_dopen = sum(
        count for category, count in by_category.items()
        if category != "open.declaration"
    )
    record_digest = sha256(json.dumps(
        records, sort_keys=True, separators=(",", ":"),
    ).encode())
    return {
        "schema_version": 1,
        "artifact_kind": "direct_source_compatibility_closure",
        "manifest": {
            "sha256": sha256(manifest_raw),
            "source_node_count": len(nodes),
            "normalization_source_count": len(normalized_sources),
            "normalization_sources": normalized_sources,
        },
        "inventory": {
            "sha256": sha256(findings_raw),
            "finding_count": len(findings),
        },
        "selected": {
            "finding_count": len(records),
            "source_files_with_findings": len({item["source"] for item in records}),
            "non_dopen_review_occurrences": p0_non_dopen,
            "site_sha256": record_digest,
            "by_category": {category: by_category[category] for category in CATEGORIES},
            "source_files_by_category": {
                category: len(paths_by_category[category]) for category in CATEGORIES
            },
            "source_paths_by_category": {
                category: sorted(paths_by_category[category]) for category in CATEGORIES
            },
            "local_parenthesized_body_forms": dict(
                sorted(local_open_body_forms.items())
            ),
            "local_parenthesized_operators": dict(
                sorted(local_open_operators.items())
            ),
            "by_repository": dict(sorted(by_repository.items())),
            "by_earliest_stratum": {name: by_stratum[name] for name in strata},
            "by_category_and_earliest_stratum": {
                category: {
                    name: by_category_and_stratum[category][name] for name in strata
                }
                for category in CATEGORIES
            },
        },
        "evidence_boundary": {
            "source_membership": "exact manifest node and SHA-256 match",
            "finding_semantics": "lexical inventory plus separately reviewed triage only",
            "dynamic_reachability_proved": False,
            "compatibility_proved": False,
            "notes": [
                "A selected occurrence is a review obligation, not proof that the expression executes.",
                "Dopen has a separate exact 3,180-site semantic/proof contract.",
                "Repository findings outside the 400-node manifest do not enter this artifact.",
                "Parenthesized local-open body forms are lexical shapes, not a general parser or semantics proof.",
            ],
        },
        "reproduce": (
            "scripts/direct-compatibility-closure.py --manifest "
            "../worktrees/candle-loader-v13/candle/flyspeck_manifest.json "
            "--findings compatibility/generated/inventory-findings.jsonl "
            "--output compatibility/generated/direct-closure-summary.json"
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--findings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest_raw = args.manifest.read_bytes()
        manifest = json.loads(manifest_raw)
        findings_raw, findings = load_findings(args.findings)
        output = canonical_bytes(project(
            manifest_raw, manifest, findings_raw, findings,
        ))
        if args.check:
            if args.output.read_bytes() != output:
                raise ValueError(f"generated closure artifact is stale: {args.output}")
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(output)
        document = json.loads(output)
        print(
            "direct compatibility closure: "
            f'{document["selected"]["finding_count"]} findings, '
            f'{document["selected"]["source_files_with_findings"]} files, '
            f'{document["selected"]["site_sha256"]}'
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"direct compatibility closure failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
