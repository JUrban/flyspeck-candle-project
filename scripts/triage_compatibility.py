#!/usr/bin/env python3
"""Apply reviewed G3/G4 classifications to the pinned lexical inventory.

The rules are deliberately source-coordinate based.  This program does not
infer semantic intent: it verifies that every pointer finding is owned by
exactly one reviewed rule, then materializes the per-finding audit records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def canonical_bytes(document: Any) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_findings(path: Path) -> tuple[bytes, list[dict[str, Any]]]:
    raw = path.read_bytes()
    return raw, [json.loads(line) for line in raw.splitlines()]


def selector_matches(finding: dict[str, Any], selector: dict[str, Any]) -> bool:
    if finding["repository"] != selector["repository"]:
        return False
    path = finding["source_path"]
    if "source_path" in selector and path != selector["source_path"]:
        return False
    if "source_path_prefix" in selector and not path.startswith(selector["source_path_prefix"]):
        return False
    if "categories" in selector and finding["category"] not in selector["categories"]:
        return False
    if "lines" in selector and finding["location"]["line"] not in selector["lines"]:
        return False
    return True


def pointer_record(finding: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "finding_id": finding["finding_id"],
        "repository": finding["repository"],
        "repository_commit": finding["repository_commit"],
        "source_path": finding["source_path"],
        "location": finding["location"],
        "category": finding["category"],
        "operator": finding["details"]["operator"],
        "operator_resolution": rule["operator_resolution"],
        "semantic_intent": rule["semantic_intent"],
        "semantic_confidence": rule["semantic_confidence"],
        "semantic_evidence": rule["semantic_evidence"],
        "s3_dependency": rule["s3_dependency"],
        "ledger_disposition": rule["ledger_disposition"],
        "review_rule_id": rule["id"],
    }


def build_pointer_document(
    findings_raw: bytes,
    findings: list[dict[str, Any]],
    rules_document: dict[str, Any],
) -> dict[str, Any]:
    pointer_findings = [item for item in findings if item["category"].startswith("pointer_equality.")]
    records = []
    used_rules: Counter[str] = Counter()
    for finding in pointer_findings:
        matches = [rule for rule in rules_document["rules"] if selector_matches(finding, rule["selector"])]
        if len(matches) != 1:
            ids = [rule["id"] for rule in matches]
            raise ValueError(f"{finding['finding_id']}: expected one review rule, found {ids}")
        rule = matches[0]
        used_rules[rule["id"]] += 1
        records.append(pointer_record(finding, rule))

    unused = [rule["id"] for rule in rules_document["rules"] if used_rules[rule["id"]] == 0]
    if unused:
        raise ValueError(f"review rules matched no findings: {unused}")

    records.sort(key=lambda item: (
        item["repository"], item["source_path"], item["location"]["line"],
        item["location"]["column"], item["finding_id"],
    ))
    return {
        "schema_version": 1,
        "triage_kind": "pointer_equality_source_review",
        "inventory_findings_sha256": sha256(findings_raw),
        "review_rules_sha256": sha256(canonical_bytes(rules_document)),
        "evidence_boundary": rules_document["evidence_boundary"],
        "reproduce": "scripts/update-compatibility-inventory.sh /project/repos",
        "counts": {
            "total": len(records),
            "by_operator_resolution": dict(sorted(Counter(item["operator_resolution"] for item in records).items())),
            "by_semantic_intent": dict(sorted(Counter(item["semantic_intent"] for item in records).items())),
            "by_s3_dependency_status": dict(sorted(Counter(item["s3_dependency"]["status"] for item in records).items())),
            "by_ledger_disposition": dict(sorted(Counter(item["ledger_disposition"] for item in records).items())),
            "by_review_rule": dict(sorted(used_rules.items())),
        },
        "records": records,
    }


def build_ffi_document(findings_raw: bytes, findings: list[dict[str, Any]], review: dict[str, Any]) -> dict[str, Any]:
    ffi_findings = [item for item in findings if item["category"] == "ffi.custom_call"]
    by_command = {item["command"]: item for item in review["calls"]}
    records = []
    for finding in ffi_findings:
        command = finding["details"]["command_literal_raw"]
        if command not in by_command:
            raise ValueError(f"{finding['finding_id']}: no FFI review for {command!r}")
        reviewed = by_command[command]
        expected = reviewed["expected_call_site"]
        actual = {
            "repository": finding["repository"],
            "source_path": finding["source_path"],
            "line": finding["location"]["line"],
        }
        if actual != expected:
            raise ValueError(f"{finding['finding_id']}: FFI call site moved: expected {expected}, got {actual}")
        record = {key: value for key, value in reviewed.items() if key != "expected_call_site"}
        record.update({
            "finding_id": finding["finding_id"],
            "repository": finding["repository"],
            "repository_commit": finding["repository_commit"],
            "source_path": finding["source_path"],
            "location": finding["location"],
        })
        records.append(record)
    missing = sorted(set(by_command) - {item["command"] for item in records})
    if missing:
        raise ValueError(f"reviewed FFI commands absent from inventory: {missing}")
    records.sort(key=lambda item: item["command"])
    return {
        "schema_version": 1,
        "triage_kind": "custom_ffi_source_review",
        "inventory_findings_sha256": sha256(findings_raw),
        "review_source_sha256": sha256(canonical_bytes(review)),
        "evidence_boundary": review["evidence_boundary"],
        "reproduce": "scripts/update-compatibility-inventory.sh /project/repos",
        "counts": {"total": len(records), "by_s3_dependency_status": dict(sorted(Counter(item["s3_dependency"]["status"] for item in records).items()))},
        "records": records,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--findings", type=Path, required=True)
    parser.add_argument("--pointer-rules", type=Path, required=True)
    parser.add_argument("--ffi-review", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        findings_raw, findings = load_findings(args.findings)
        rules = json.loads(args.pointer_rules.read_text(encoding="utf-8"))
        ffi_review = json.loads(args.ffi_review.read_text(encoding="utf-8"))
        pointer = build_pointer_document(findings_raw, findings, rules)
        ffi = build_ffi_document(findings_raw, findings, ffi_review)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "pointer-triage.json").write_bytes(canonical_bytes(pointer))
        (args.output_dir / "ffi-triage.json").write_bytes(canonical_bytes(ffi))
        print(f"triaged {pointer['counts']['total']} pointer findings and {ffi['counts']['total']} custom FFI calls")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"compatibility triage failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
