#!/usr/bin/env python3
"""Reproduce the direct-S3 inventory delta from the prior PFT-head evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable


ARTIFACTS = (
    "inventory-findings.jsonl",
    "inventory-summary.json",
    "pointer-triage.json",
    "ffi-triage.json",
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def git_blob(project_root: Path, commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(project_root), "show", f"{commit}:{path}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def read_jsonl(raw: bytes) -> list[dict[str, Any]]:
    return [json.loads(line) for line in raw.splitlines()]


def stable_finding_key(record: dict[str, Any]) -> str:
    """Identify the same source occurrence while ignoring pin-derived fields."""
    stable = {
        key: value for key, value in record.items()
        if key not in {"finding_id", "repository_commit", "source_sha256"}
    }
    return json.dumps(stable, sort_keys=True, separators=(",", ":"))


def stable_triage_key(record: dict[str, Any]) -> str:
    stable = {
        key: value for key, value in record.items()
        if key not in {"finding_id", "repository_commit"}
    }
    return json.dumps(stable, sort_keys=True, separators=(",", ":"))


def count_delta(baseline: dict[str, int], selected: dict[str, int]) -> dict[str, dict[str, int]]:
    return {
        key: {
            "comparison": baseline.get(key, 0),
            "selected": selected.get(key, 0),
            "selected_minus_comparison": selected.get(key, 0) - baseline.get(key, 0),
        }
        for key in sorted(set(baseline) | set(selected))
    }


def multiset_delta(
    baseline: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    key: Callable[[dict[str, Any]], str],
) -> tuple[int, list[dict[str, Any]], list[dict[str, Any]]]:
    baseline_counts = Counter(key(record) for record in baseline)
    selected_counts = Counter(key(record) for record in selected)

    def records_for_delta(
        records: list[dict[str, Any]], delta: Counter[str]
    ) -> list[dict[str, Any]]:
        remaining = delta.copy()
        result = []
        for record in records:
            record_key = key(record)
            if remaining[record_key] > 0:
                result.append(record)
                remaining[record_key] -= 1
        return result

    matched = sum((baseline_counts & selected_counts).values())
    return (
        matched,
        records_for_delta(baseline, baseline_counts - selected_counts),
        records_for_delta(selected, selected_counts - baseline_counts),
    )


def concise_finding(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "repository": record["repository"],
        "source_path": record["source_path"],
        "location": record["location"],
        "category": record["category"],
        "lexeme": record["lexeme"],
    }


def git_source_delta(
    source_repo: Path, comparison_commit: str, selected_commit: str, extensions: list[str]
) -> list[dict[str, str]]:
    pathspecs = [f"*{extension}" for extension in extensions]
    raw = subprocess.run(
        [
            "git", "-C", str(source_repo), "diff", "--name-status",
            comparison_commit, selected_commit, "--", *pathspecs,
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout
    result = []
    for line in raw.splitlines():
        fields = line.split("\t")
        result.append({"status": fields[0], "path": fields[-1]})
    return result


def build_document(
    project_root: Path, repos_root: Path, inventory_dir: Path, contract_path: Path
) -> dict[str, Any]:
    contract_raw = contract_path.read_bytes()
    contract = json.loads(contract_raw)
    comparison = contract["comparison_lane"]
    selected_contract = contract["selected_lane"]
    project_commit = comparison["project_git_commit"]

    old_raw = {
        name: git_blob(project_root, project_commit, f"compatibility/generated/{name}")
        for name in ARTIFACTS
    }
    new_raw = {name: (inventory_dir / name).read_bytes() for name in ARTIFACTS}
    for name, expected in comparison["artifact_sha256"].items():
        actual = sha256(old_raw[name])
        if actual != expected:
            raise ValueError(f"comparison artifact digest mismatch for {name}: {actual}")

    old_summary = json.loads(old_raw["inventory-summary.json"])
    new_summary = json.loads(new_raw["inventory-summary.json"])
    repository = selected_contract["repository"]
    if old_summary["repositories"][repository]["commit"] != comparison["git_commit"]:
        raise ValueError("comparison inventory does not carry the contracted PFT source pin")
    selected_metadata = new_summary["repositories"][repository]
    if selected_metadata["commit"] != selected_contract["git_commit"]:
        raise ValueError("selected inventory does not carry the contracted direct S3 pin")
    if selected_metadata["path_key"] != selected_contract["path_key"]:
        raise ValueError("selected inventory is not sourced from the contracted clean worktree")

    old_findings = read_jsonl(old_raw["inventory-findings.jsonl"])
    new_findings = read_jsonl(new_raw["inventory-findings.jsonl"])
    finding_matched, finding_old_only, finding_new_only = multiset_delta(
        old_findings, new_findings, stable_finding_key
    )

    triage_delta = {}
    for kind, filename in (("pointer", "pointer-triage.json"), ("ffi", "ffi-triage.json")):
        old_document = json.loads(old_raw[filename])
        new_document = json.loads(new_raw[filename])
        matched, old_only, new_only = multiset_delta(
            old_document["records"], new_document["records"], stable_triage_key
        )
        triage_delta[kind] = {
            "comparison_artifact_sha256": sha256(old_raw[filename]),
            "selected_artifact_sha256": sha256(new_raw[filename]),
            "comparison_records": len(old_document["records"]),
            "selected_records": len(new_document["records"]),
            "selected_minus_comparison": len(new_document["records"]) - len(old_document["records"]),
            "stable_records_matched": matched,
            "comparison_only_records": len(old_only),
            "selected_only_records": len(new_only),
            "selected_counts": new_document["counts"],
        }

    totals = {
        key: {
            "comparison": old_summary["totals"][key],
            "selected": new_summary["totals"][key],
            "selected_minus_comparison": (
                new_summary["totals"][key] - old_summary["totals"][key]
            ),
        }
        for key in sorted(old_summary["totals"])
    }
    source_repo = (repos_root / selected_metadata["path_key"]).resolve()

    return {
        "schema_version": 1,
        "comparison_kind": "direct_s3_pin_correction_from_pft_development_evidence",
        "contract_sha256": sha256(contract_raw),
        "reproducible_command": "scripts/update-compatibility-inventory.sh /project/repos",
        "comparison_lane": {
            "role": comparison["role"],
            "project_git_commit": project_commit,
            "flyspeck_commit": comparison["git_commit"],
            "inventory_findings_sha256": sha256(old_raw["inventory-findings.jsonl"]),
            "totals": old_summary["totals"],
        },
        "selected_lane": {
            "role": selected_contract["role"],
            "flyspeck_commit": selected_contract["git_commit"],
            "inventory_path_key": selected_contract["path_key"],
            "inventory_findings_sha256": sha256(new_raw["inventory-findings.jsonl"]),
            "totals": new_summary["totals"],
        },
        "delta": {
            "totals": totals,
            "by_category": count_delta(
                old_summary["counts"]["by_category"], new_summary["counts"]["by_category"]
            ),
            "by_repository": count_delta(
                old_summary["counts"]["by_repository"], new_summary["counts"]["by_repository"]
            ),
        },
        "stable_occurrences": {
            "method": "All finding fields except finding_id, repository_commit, and source_sha256; this distinguishes content/coordinate changes from commit-derived identifier churn.",
            "matched": finding_matched,
            "comparison_only": len(finding_old_only),
            "selected_only": len(finding_new_only),
            "comparison_only_records": [concise_finding(record) for record in finding_old_only],
            "selected_only_records": [concise_finding(record) for record in finding_new_only],
        },
        "triage": triage_delta,
        "eligible_source_path_delta_comparison_to_selected": git_source_delta(
            source_repo,
            comparison["git_commit"],
            selected_contract["git_commit"],
            new_summary["extensions"],
        ),
        "evidence_boundary": "This artifact compares source inventory and reviewed triage records. It does not promote PFT-only sources into the selected S3 route or prove dynamic reachability or semantic compatibility.",
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--repos-root", type=Path, required=True)
    parser.add_argument("--inventory-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    document = build_document(
        args.project_root, args.repos_root, args.inventory_dir, args.contract
    )
    args.output.write_bytes(canonical_bytes(document))
    print(
        "pin delta: "
        f"{document['delta']['totals']['findings']['selected_minus_comparison']:+d} findings, "
        f"{document['stable_occurrences']['comparison_only']} comparison-only, "
        f"{document['stable_occurrences']['selected_only']} selected-only stable occurrences"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
