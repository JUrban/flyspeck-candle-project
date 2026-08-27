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


def selector_matches(
    finding: dict[str, Any],
    selector: dict[str, Any],
    pointer_by_id: dict[str, dict[str, Any]],
    ffi_by_id: dict[str, dict[str, Any]],
) -> bool:
    categories = selector.get("categories", [])
    prefixes = selector.get("category_prefixes", [])
    syntax_match = finding["category"] in categories or any(finding["category"].startswith(prefix) for prefix in prefixes)
    if categories or prefixes:
        return syntax_match
    if "triage_dispositions" in selector:
        record = pointer_by_id.get(finding["finding_id"])
        return record is not None and record["ledger_disposition"] in selector["triage_dispositions"]
    if "ffi_ledger_ids" in selector:
        record = ffi_by_id.get(finding["finding_id"])
        return record is not None and record["ledger_id"] in selector["ffi_ledger_ids"]
    return False


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
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
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
    return summary, findings


def validate_source_provenance(
    ledger: dict[str, Any],
    summary: dict[str, Any],
    inventory_dir: Path,
    contract_path: Path,
    pin_delta_schema: Path,
) -> None:
    provenance = ledger["source_provenance"]
    selected = provenance["selected_direct_source"]
    development = provenance["separate_development_source"]
    artifacts = provenance["inventory_artifacts"]
    repository = selected["repository"]
    metadata = summary["repositories"][repository]
    require(selected["git_commit"] == metadata["commit"], "ledger selected source commit differs from inventory")
    require(selected["path_key"] == metadata["path_key"], "ledger selected source path differs from inventory")
    require(not development["included_in_selected_inventory"], "PFT development source entered selected inventory")
    require(development["git_commit"] != selected["git_commit"], "selected and PFT development pins are not separated")

    contract_raw = contract_path.read_bytes()
    contract = json.loads(contract_raw)
    require(artifacts["pin_contract_sha256"] == sha256(contract_raw), "pin contract digest mismatch")
    require(contract["selected_lane"]["git_commit"] == selected["git_commit"], "pin contract selected commit mismatch")
    require(contract["selected_lane"]["path_key"] == selected["path_key"], "pin contract selected path mismatch")
    require(contract["comparison_lane"]["git_commit"] == development["git_commit"], "pin contract PFT commit mismatch")

    filenames = {
        "findings_sha256": "inventory-findings.jsonl",
        "pointer_triage_sha256": "pointer-triage.json",
        "ffi_triage_sha256": "ffi-triage.json",
        "pin_delta_sha256": "inventory-pin-delta.json",
    }
    for field, filename in filenames.items():
        require(
            artifacts[field] == sha256((inventory_dir / filename).read_bytes()),
            f"ledger provenance digest mismatch for {filename}",
        )

    delta = json.loads((inventory_dir / "inventory-pin-delta.json").read_text(encoding="utf-8"))
    validate_with_json_schema(delta, pin_delta_schema)
    require(delta["contract_sha256"] == artifacts["pin_contract_sha256"], "pin delta contract digest mismatch")
    require(delta["selected_lane"]["flyspeck_commit"] == selected["git_commit"], "pin delta selected commit mismatch")
    require(delta["selected_lane"]["inventory_path_key"] == selected["path_key"], "pin delta selected path mismatch")
    require(
        delta["selected_lane"]["inventory_findings_sha256"] == summary["artifacts"]["findings_sha256"],
        "pin delta selected findings digest mismatch",
    )
    require(delta["selected_lane"]["totals"] == summary["totals"], "pin delta selected totals mismatch")
    require(delta["comparison_lane"]["flyspeck_commit"] == development["git_commit"], "pin delta PFT commit mismatch")

    occurrences = delta["stable_occurrences"]
    require(
        occurrences["matched"] + occurrences["comparison_only"]
        == delta["comparison_lane"]["totals"]["findings"],
        "pin delta comparison stable-occurrence arithmetic mismatch",
    )
    require(
        occurrences["matched"] + occurrences["selected_only"]
        == delta["selected_lane"]["totals"]["findings"],
        "pin delta selected stable-occurrence arithmetic mismatch",
    )
    require(
        occurrences["comparison_only"] == len(occurrences["comparison_only_records"])
        and occurrences["selected_only"] == len(occurrences["selected_only_records"]),
        "pin delta stable-occurrence record counts mismatch",
    )
    for section in delta["delta"].values():
        for name, counts in section.items():
            require(
                counts["selected"] - counts["comparison"] == counts["selected_minus_comparison"],
                f"pin delta arithmetic mismatch for {name}",
            )


def canonical_bytes(document: Any) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def validate_generated_counts(document: dict[str, Any], records: list[dict[str, Any]]) -> None:
    require(document["counts"]["total"] == len(records), f"{document['triage_kind']}: total count mismatch")
    if document["triage_kind"] == "pointer_equality_source_review":
        for field, count_key in (
            ("operator_resolution", "by_operator_resolution"),
            ("semantic_intent", "by_semantic_intent"),
            ("ledger_disposition", "by_ledger_disposition"),
            ("review_rule_id", "by_review_rule"),
        ):
            actual = dict(sorted(Counter(record[field] for record in records).items()))
            require(document["counts"][count_key] == actual, f"pointer triage {count_key} mismatch")
    actual_dependencies = dict(sorted(Counter(record["s3_dependency"]["status"] for record in records).items()))
    require(document["counts"]["by_s3_dependency_status"] == actual_dependencies, "triage dependency counts mismatch")


def load_and_validate_triage(
    inventory_dir: Path,
    pointer_schema: Path,
    ffi_schema: Path,
    pointer_rules: Path,
    ffi_review: Path,
    findings: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    raw_findings = (inventory_dir / "inventory-findings.jsonl").read_bytes()
    finding_by_id = {finding["finding_id"]: finding for finding in findings}
    documents = []
    for filename, schema in (("pointer-triage.json", pointer_schema), ("ffi-triage.json", ffi_schema)):
        path = inventory_dir / filename
        require(path.is_file(), f"missing generated triage artifact: {path}")
        document = json.loads(path.read_text(encoding="utf-8"))
        validate_with_json_schema(document, schema)
        require(document["inventory_findings_sha256"] == sha256(raw_findings), f"{filename}: inventory digest mismatch")
        validate_generated_counts(document, document["records"])
        documents.append(document)

    pointer, ffi = documents
    rules_document = json.loads(pointer_rules.read_text(encoding="utf-8"))
    review_document = json.loads(ffi_review.read_text(encoding="utf-8"))
    require(pointer["review_rules_sha256"] == sha256(canonical_bytes(rules_document)), "pointer review-rules digest mismatch")
    require(ffi["review_source_sha256"] == sha256(canonical_bytes(review_document)), "FFI review-source digest mismatch")

    pointer_by_id: dict[str, dict[str, Any]] = {}
    for record in pointer["records"]:
        finding_id = record["finding_id"]
        require(finding_id not in pointer_by_id, f"duplicate pointer triage finding: {finding_id}")
        require(finding_id in finding_by_id, f"pointer triage references unknown finding: {finding_id}")
        finding = finding_by_id[finding_id]
        require(finding["category"].startswith("pointer_equality."), f"{finding_id}: triage is not a pointer finding")
        for field in ("repository", "repository_commit", "source_path", "location", "category"):
            require(record[field] == finding[field], f"{finding_id}: triage {field} differs from inventory")
        require(record["operator"] == finding["details"]["operator"], f"{finding_id}: triage operator differs")
        pointer_by_id[finding_id] = record
    expected_pointer_ids = {finding["finding_id"] for finding in findings if finding["category"].startswith("pointer_equality.")}
    require(set(pointer_by_id) == expected_pointer_ids, "pointer triage does not cover every inventory pointer finding exactly once")

    ffi_by_id: dict[str, dict[str, Any]] = {}
    ledger_ids: set[str] = set()
    for record in ffi["records"]:
        finding_id = record["finding_id"]
        require(finding_id not in ffi_by_id, f"duplicate FFI triage finding: {finding_id}")
        require(record["ledger_id"] not in ledger_ids, f"duplicate FFI ledger ID: {record['ledger_id']}")
        require(finding_id in finding_by_id, f"FFI triage references unknown finding: {finding_id}")
        finding = finding_by_id[finding_id]
        require(finding["category"] == "ffi.custom_call", f"{finding_id}: triage is not a custom FFI call")
        for field in ("repository", "repository_commit", "source_path", "location"):
            require(record[field] == finding[field], f"{finding_id}: FFI triage {field} differs from inventory")
        require(record["command"] == finding["details"]["command_literal_raw"], f"{finding_id}: FFI command differs")
        reproducer = inventory_dir.parent / record["minimal_reproducer"].removeprefix("compatibility/")
        require(reproducer.is_file(), f"{finding_id}: missing FFI reproducer: {record['minimal_reproducer']}")
        ffi_by_id[finding_id] = record
        ledger_ids.add(record["ledger_id"])
    expected_ffi_ids = {finding["finding_id"] for finding in findings if finding["category"] == "ffi.custom_call"}
    require(set(ffi_by_id) == expected_ffi_ids, "FFI triage does not cover every customFFI finding exactly once")
    return pointer_by_id, ffi_by_id


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
    parser.add_argument("--pointer-triage-schema", type=Path, required=True)
    parser.add_argument("--ffi-triage-schema", type=Path, required=True)
    parser.add_argument("--pointer-rules", type=Path, required=True)
    parser.add_argument("--ffi-review", type=Path, required=True)
    parser.add_argument("--pin-contract", type=Path, required=True)
    parser.add_argument("--pin-delta-schema", type=Path, required=True)
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
        summary, findings = load_and_validate_inventory(
            args.inventory_dir,
            args.finding_schema,
            args.summary_schema,
            args.repos_root,
        )
        validate_source_provenance(
            ledger,
            summary,
            args.inventory_dir,
            args.pin_contract,
            args.pin_delta_schema,
        )
        pointer_by_id, ffi_by_id = load_and_validate_triage(
            args.inventory_dir,
            args.pointer_triage_schema,
            args.ffi_triage_schema,
            args.pointer_rules,
            args.ffi_review,
            findings,
        )
        for entry in ledger["entries"]:
            matched = [
                finding for finding in findings
                if selector_matches(finding, entry["inventory_selector"], pointer_by_id, ffi_by_id)
            ]
            require(matched, f"{entry['id']}: inventory selector matches no findings")
            if entry["affected_files_status"] == "enumerated":
                actual_files = {(finding["repository"], finding["source_path"]) for finding in matched}
                declared_files = {(item["repository"], item["path"]) for item in entry["affected_corpus_files"]}
                require(declared_files == actual_files, f"{entry['id']}: enumerated affected files differ from selector")
        print(
            f"ledger ok: {len(local_ids)} project entries, {len(imported_ids)} authoritative imported entry, "
            f"{len(findings)} inventory findings, {len(pointer_by_id)} pointer reviews, {len(ffi_by_id)} FFI reviews"
        )
    except (OSError, KeyError, TypeError, ValueError, subprocess.SubprocessError, ValidationError) as error:
        print(f"ledger validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
