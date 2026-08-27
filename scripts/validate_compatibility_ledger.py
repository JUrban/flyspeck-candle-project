#!/usr/bin/env python3
"""Validate the project compatibility ledger, imports, and inventory links."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ENTRY_REQUIRED = {
    "id", "entry_kind", "divergence_state", "priority", "status", "summary",
    "semantic_category", "minimal_reproducer", "ocaml_reference",
    "candle_outcome", "chosen_remedy", "proof_obligation", "regression_ids",
    "affected_corpus_files", "affected_files_status", "inventory_selector", "notes",
}
STATUS_VALUES = {
    "inventory_pending", "reproducer_pending", "oracle_pending", "remedy_pending",
    "proof_pending", "regression_pending", "resolved", "deferred",
}
DIVERGENCE_VALUES = {
    "review_candidate", "confirmed_divergence", "equivalent_behavior",
    "outside_dependency_closure",
}


class ValidationError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(repo: Path, commit: str, artifact_path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{commit}:{artifact_path}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        diagnostic = result.stderr.decode("utf-8", "replace").strip()
        raise ValidationError(f"cannot read {repo}@{commit}:{artifact_path}: {diagnostic}")
    return result.stdout


def validate_with_json_schema(document: Any, schema_path: Path) -> None:
    try:
        import jsonschema
    except ImportError:
        # The project validator below enforces lifecycle invariants without an
        # external package.  JSON Schema validation is additive when available.
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.Draft202012Validator(schema).validate(document)
    except jsonschema.ValidationError as error:
        location = "/".join(str(part) for part in error.absolute_path)
        raise ValidationError(f"JSON schema failure at {location or '<root>'}: {error.message}") from error


def validate_local_entry(entry: dict[str, Any]) -> None:
    entry_id = entry.get("id", "<missing>")
    require(set(entry) == ENTRY_REQUIRED, f"{entry_id}: fields differ from required v1.3 entry schema")
    require(re.fullmatch(r"[A-Z][A-Z0-9-]+", entry_id) is not None, f"{entry_id}: invalid ID")
    require(entry["status"] in STATUS_VALUES, f"{entry_id}: invalid status")
    require(entry["divergence_state"] in DIVERGENCE_VALUES, f"{entry_id}: invalid divergence_state")
    require(entry["priority"] in {"P0", "P1", "P2"}, f"{entry_id}: invalid priority")
    require(entry["affected_files_status"] in {"inventory_query", "enumerated"}, f"{entry_id}: invalid affected_files_status")

    confirmed = entry["divergence_state"] == "confirmed_divergence"
    if confirmed:
        require(entry["entry_kind"] == "confirmed_divergence", f"{entry_id}: confirmed state needs confirmed entry kind")
        require(entry["minimal_reproducer"]["status"] == "ready", f"{entry_id}: confirmed divergence needs reproducer")
        require(entry["ocaml_reference"]["status"] == "observed", f"{entry_id}: confirmed divergence needs OCaml outcome")
        require(entry["candle_outcome"]["status"] == "observed", f"{entry_id}: confirmed divergence needs Candle outcome")
        require(entry["affected_files_status"] == "enumerated", f"{entry_id}: confirmed divergence needs enumerated files")
        require(bool(entry["affected_corpus_files"]), f"{entry_id}: confirmed divergence needs affected files")

    if entry["status"] == "resolved":
        require(confirmed, f"{entry_id}: only a confirmed divergence can be resolved")
        require(entry["chosen_remedy"]["status"] == "implemented", f"{entry_id}: resolved entry needs implemented remedy")
        require(entry["proof_obligation"]["status"] in {"discharged", "not_applicable_documented"}, f"{entry_id}: unresolved proof obligation")
        require(bool(entry["regression_ids"]), f"{entry_id}: resolved entry needs stable regression IDs")
        require(bool(entry["ocaml_reference"]["evidence"]), f"{entry_id}: resolved entry needs OCaml evidence")
        require(bool(entry["candle_outcome"]["evidence"]), f"{entry_id}: resolved entry needs Candle evidence")


def selector_matches(finding: dict[str, Any], selector: dict[str, Any]) -> bool:
    categories = selector.get("categories", [])
    prefixes = selector.get("category_prefixes", [])
    return finding["category"] in categories or any(finding["category"].startswith(prefix) for prefix in prefixes)


def git_text(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout


def validate_inventory_sources_and_counts(
    summary: dict[str, Any],
    findings: list[dict[str, Any]],
    lexical_notes: list[dict[str, Any]],
    repos_root: Path,
) -> None:
    extensions = set(summary["extensions"])
    source_cache: dict[tuple[str, str], str] = {}
    for repository, metadata in summary["repositories"].items():
        repo = repos_root / metadata["path_key"]
        require(repo.exists(), f"inventory repository missing: {repo}")
        head = git_text(repo, "rev-parse", "HEAD").strip()
        require(head == metadata["commit"], f"{repository}: inventory HEAD mismatch")
        dirty = bool(git_text(repo, "status", "--porcelain", "--untracked-files=no"))
        require(dirty == metadata["dirty"], f"{repository}: inventory dirty-state mismatch")
        raw_paths = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "-z"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        paths = sorted(
            path.decode("utf-8", "surrogateescape")
            for path in raw_paths.split(b"\0")
            if path and Path(path.decode("utf-8", "surrogateescape")).suffix in extensions
        )
        require(len(paths) == metadata["source_files_scanned"], f"{repository}: scanned file count mismatch")
        require(
            sum((repo / path).stat().st_size for path in paths) == metadata["source_bytes_scanned"],
            f"{repository}: scanned byte count mismatch",
        )

    for finding in findings:
        repository = finding["repository"]
        require(repository in summary["repositories"], f"unknown finding repository: {repository}")
        metadata = summary["repositories"][repository]
        require(finding["repository_commit"] == metadata["commit"], f"{finding['finding_id']}: commit mismatch")
        key = (repository, finding["source_path"])
        if key not in source_cache:
            path = repos_root / metadata["path_key"] / finding["source_path"]
            require(path.is_file(), f"{finding['finding_id']}: source file missing: {path}")
            source_cache[key] = sha256(path.read_bytes())
        require(source_cache[key] == finding["source_sha256"], f"{finding['finding_id']}: source digest mismatch")

    expected_categories = summary["counts"]["by_category"]
    actual_categories = Counter(finding["category"] for finding in findings)
    require(
        expected_categories == {category: actual_categories[category] for category in expected_categories},
        "inventory category counts do not match findings",
    )
    actual_repositories = Counter(finding["repository"] for finding in findings)
    require(summary["counts"]["by_repository"] == dict(sorted(actual_repositories.items())), "repository finding counts mismatch")
    actual_dialects = Counter(finding["source_dialect"] for finding in findings)
    require(summary["counts"]["by_source_dialect"] == dict(sorted(actual_dialects.items())), "source-dialect counts mismatch")

    for category, repository_counts in summary["counts"]["by_category_and_repository"].items():
        actual = {
            repository: sum(
                finding["category"] == category and finding["repository"] == repository
                for finding in findings
            )
            for repository in repository_counts
        }
        require(repository_counts == actual, f"{category}: per-repository counts mismatch")
        files = len({
            (finding["repository"], finding["source_path"])
            for finding in findings if finding["category"] == category
        })
        require(summary["counts"]["files_with_findings_by_category"][category] == files, f"{category}: file count mismatch")

    actual_path_forms = Counter(
        finding["details"].get("module_path_form")
        for finding in findings
        if finding["details"].get("module_path_form") is not None
    )
    require(
        summary["counts"]["by_module_path_form"]
        == {form: actual_path_forms[form] for form in summary["counts"]["by_module_path_form"]},
        "module-path form counts mismatch",
    )
    pointer_findings = [finding for finding in findings if finding["category"].startswith("pointer_equality.")]
    require(
        summary["counts"]["pointer_by_token"]
        == dict(sorted(Counter(finding["details"]["token_category"] for finding in pointer_findings).items())),
        "pointer token counts mismatch",
    )
    require(
        summary["counts"]["pointer_by_syntactic_role"]
        == dict(sorted(Counter(finding["details"]["syntactic_role"] for finding in pointer_findings).items())),
        "pointer role counts mismatch",
    )
    infix_findings = [finding for finding in pointer_findings if finding["category"] == "pointer_equality.infix_use"]
    require(
        summary["counts"]["pointer_by_static_operand_category"]
        == dict(sorted(Counter(finding["details"]["static_operand_category"] for finding in infix_findings).items())),
        "pointer operand counts mismatch",
    )
    ffi_findings = [finding for finding in findings if finding["category"] == "ffi.custom_call"]
    require(
        summary["counts"]["custom_ffi_by_command_form"]
        == dict(sorted(Counter(finding["details"]["command_form"] for finding in ffi_findings).items())),
        "custom FFI command-form counts mismatch",
    )
    require(
        summary["counts"]["lexical_notes_by_kind"]
        == dict(sorted(Counter(note["kind"] for note in lexical_notes).items())),
        "lexical-note counts mismatch",
    )


def load_and_validate_inventory(
    inventory_dir: Path,
    finding_schema: Path,
    summary_schema: Path,
    repos_root: Path,
) -> list[dict[str, Any]]:
    summary_path = inventory_dir / "inventory-summary.json"
    findings_path = inventory_dir / "inventory-findings.jsonl"
    require(summary_path.is_file(), f"missing inventory summary: {summary_path}")
    require(findings_path.is_file(), f"missing inventory findings: {findings_path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    validate_with_json_schema(summary, summary_schema)
    raw_findings = findings_path.read_bytes()
    require(
        sha256(raw_findings) == summary["artifacts"]["findings_sha256"],
        "inventory findings digest does not match summary",
    )
    findings: list[dict[str, Any]] = []
    ids: set[str] = set()
    for line_number, raw_line in enumerate(raw_findings.splitlines(), 1):
        try:
            finding = json.loads(raw_line)
        except json.JSONDecodeError as error:
            raise ValidationError(f"inventory JSONL line {line_number}: {error}") from error
        validate_with_json_schema(finding, finding_schema)
        require(finding["finding_id"] not in ids, f"duplicate finding ID: {finding['finding_id']}")
        ids.add(finding["finding_id"])
        findings.append(finding)
    require(len(findings) == summary["totals"]["findings"], "inventory finding count does not match summary")
    lexical_notes_path = inventory_dir / summary["artifacts"]["lexical_notes_json"]
    require(lexical_notes_path.is_file(), f"missing lexical notes: {lexical_notes_path}")
    lexical_notes = json.loads(lexical_notes_path.read_text(encoding="utf-8"))
    require(len(lexical_notes) == summary["totals"]["lexical_notes"], "lexical-note count does not match summary")
    validate_inventory_sources_and_counts(summary, findings, lexical_notes, repos_root)
    return findings


def validate_imports(ledger: dict[str, Any], repos_root: Path) -> set[str]:
    imported_ids: set[str] = set()
    for source in ledger["imports"]:
        repo = repos_root / source["repository_path_key"]
        raw = git_blob(repo, source["git_commit"], source["artifact_path"])
        require(sha256(raw) == source["artifact_sha256"], f"{source['id']}: imported ledger digest mismatch")
        document = json.loads(raw)
        require(document.get("schema_version") == source["source_schema_version"], f"{source['id']}: source schema mismatch")
        require(document.get("compatibility_specification") == ledger["compatibility_specification"], f"{source['id']}: compatibility specification mismatch")
        entries = document.get("entries")
        require(isinstance(entries, list), f"{source['id']}: imported entries is not a list")
        actual_ids = [entry.get("id") for entry in entries]
        require(actual_ids == source["entry_ids"], f"{source['id']}: declared imported IDs/order mismatch")
        source_fields = set(source["field_map"].values())
        for entry in entries:
            entry_id = entry["id"]
            require(entry_id.startswith(source["authoritative_id_prefix"]), f"{source['id']}: ID prefix mismatch: {entry_id}")
            require(source_fields <= set(entry), f"{source['id']}:{entry_id}: projection field missing")
            require(entry_id not in imported_ids, f"duplicate imported entry ID: {entry_id}")
            imported_ids.add(entry_id)
    return imported_ids


def validate_related_artifacts(ledger: dict[str, Any], repos_root: Path) -> None:
    for artifact in ledger["related_artifacts"]:
        repo = repos_root / artifact["repository_path_key"]
        raw = git_blob(repo, artifact["git_commit"], artifact["artifact_path"])
        require(sha256(raw) == artifact["artifact_sha256"], f"{artifact['id']}: artifact digest mismatch")
        document = json.loads(raw)
        if "declared_target_count" in artifact:
            require(document.get("target_count") == artifact["declared_target_count"], f"{artifact['id']}: target count mismatch")
        if "declared_source_count" in artifact:
            require(document.get("covered_source_count") == artifact["declared_source_count"], f"{artifact['id']}: source count mismatch")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--finding-schema", type=Path, required=True)
    parser.add_argument("--summary-schema", type=Path, required=True)
    parser.add_argument("--repos-root", type=Path, required=True)
    parser.add_argument("--inventory-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
        validate_with_json_schema(ledger, args.schema)
        local_ids: set[str] = set()
        for entry in ledger["entries"]:
            validate_local_entry(entry)
            require(entry["id"] not in local_ids, f"duplicate local entry ID: {entry['id']}")
            local_ids.add(entry["id"])
        imported_ids = validate_imports(ledger, args.repos_root)
        require(local_ids.isdisjoint(imported_ids), "local entry duplicates authoritative imported entry")
        validate_related_artifacts(ledger, args.repos_root)
        findings = load_and_validate_inventory(
            args.inventory_dir,
            args.finding_schema,
            args.summary_schema,
            args.repos_root,
        )
        for entry in ledger["entries"]:
            if entry["affected_files_status"] == "inventory_query":
                count = sum(selector_matches(finding, entry["inventory_selector"]) for finding in findings)
                require(count > 0, f"{entry['id']}: inventory selector matches no findings")
        print(
            f"ledger ok: {len(local_ids)} project review entries, "
            f"{len(imported_ids)} authoritative imported entry, {len(findings)} inventory findings"
        )
    except (OSError, KeyError, TypeError, ValueError, subprocess.SubprocessError, ValidationError) as error:
        print(f"ledger validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
