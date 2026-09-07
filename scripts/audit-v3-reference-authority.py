#!/usr/bin/env python3
"""Independently replay and cross-check candidate V3 Great100 authority.

This tool emits a review report, never an identity approval.  It can audit the
completed prefix of a live two-sweep collection, but only a closed 130/130
collection can receive ``review_complete`` status.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


PROGRAM_PATH = Path(__file__).resolve()
SHA256_RE = re.compile(r"[0-9a-f]{64}")
SUCCESS_RE = re.compile(
    r"sweep-([12])/target-([0-9]{3})/attempt-0001/success[.]json")
V3_SERIALIZER_RELATIVE = "candle/fingerprint_v3.ml"
V3_SERIALIZER_SHA256 = (
    "444edaba460b2e9ab01c535fbfb18e9fe9932dcf6fe7f8996e2008b47991b110"
)
CONTRACT_FIELDS = {
    "schema", "kind", "approval_status", "promotion_allowed",
    "sweep_count", "target_count", "total_target_runs", "source_mode",
    "execution", "project", "candle", "reference", "runtime",
    "external_runtime", "elf_oracle", "deadlines", "inventory", "controller",
}
SUCCESS_FIELDS = {
    "schema", "kind", "sweep", "target_index", "target", "session_nonce",
    "artifacts", "collector_stdout", "collector_stderr", "validator_stdout",
    "validator_stderr", "deadlines", "approval_status", "promotion_allowed",
}
RECEIPT_FIELDS = {
    "schema", "kind", "contract_sha256", "contract", "sweep_count",
    "target_count", "total_target_runs", "completed_target_runs",
    "pending_target_runs", "failure_attempt_count", "failures",
    "publication_interruptions", "outcome", "closed", "approval_status",
    "promotion_allowed", "sweeps",
}


class AuditError(RuntimeError):
    """The candidate authority failed a review invariant."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuditError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AuditError(f"could not read exact {label}: {path}") from error
    require(isinstance(value, dict), f"{label} must be a JSON object")
    return value


def sha256_bytes(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8"))


def file_record(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(),
            f"review input is not an ordinary file: {path}")
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def verify_record(root: Path, record: Any, expected_relative: str,
                  label: str) -> Path:
    require(isinstance(record, dict) and set(record) == {
        "path", "bytes", "sha256"}, f"malformed {label} record")
    require(record["path"] == expected_relative,
            f"noncanonical {label} path")
    path = root / expected_relative
    observed = file_record(path)
    require(type(record["bytes"]) is int and
            record["bytes"] == observed["bytes"] and
            record["sha256"] == observed["sha256"] and
            SHA256_RE.fullmatch(record["sha256"]) is not None,
            f"changed {label} bytes")
    return path


def git(root: Path, *arguments: str) -> str:
    try:
        return subprocess.check_output(
            ["/usr/bin/git", "-C", str(root), *arguments],
            text=True, stderr=subprocess.STDOUT,
        ).strip()
    except subprocess.CalledProcessError as error:
        raise AuditError(
            f"git {' '.join(arguments)} failed in {root}: {error.output}"
        ) from error


def verify_git_root(root: Path, expected_head: str, label: str) -> None:
    require(root.is_absolute() and root.is_dir(), f"missing {label} root")
    require(re.fullmatch(r"[0-9a-f]{40}", expected_head) is not None,
            f"malformed {label} head")
    require(git(root, "rev-parse", "HEAD") == expected_head,
            f"{label} head changed")
    require(git(root, "status", "--porcelain=v1", "--untracked-files=all") == "",
            f"{label} worktree is not clean")


def diagnostic_projection(result: dict[str, Any]) -> dict[str, Any]:
    """Project one diagnostic V3 result into the approval identity shape."""
    try:
        fingerprints = result["v3_fingerprints"]
        serializer = fingerprints["serializer"]
        theorems = [{
            "name": theorem["name"],
            "theorem_sha256": theorem["theorem"]["sha256"],
            "hypotheses_sha256": theorem["hypotheses"]["sha256"],
            "conclusion_sha256": theorem["conclusion"]["sha256"],
            "global_axioms_sha256": theorem["global_axioms"]["sha256"],
            "hypothesis_count": theorem["hypothesis_count"],
            "global_axiom_count": theorem["global_axiom_count"],
        } for theorem in fingerprints["theorems"]]
        state = fingerprints["post_state"]
        post_state = {
            "kernel_state_sha256": state["kernel_state"]["sha256"],
            "type_constants_sha256": state["type_constants"]["sha256"],
            "type_constant_count": state["type_constant_count"],
            "term_constants_sha256": state["term_constants"]["sha256"],
            "term_constant_count": state["term_constant_count"],
            "definitions_sha256": state["definitions"]["sha256"],
            "definition_count": state["definition_count"],
            "global_axioms_sha256": state["global_axioms"]["sha256"],
            "global_axiom_count": state["global_axiom_count"],
        }
    except (KeyError, TypeError) as error:
        raise AuditError("malformed diagnostic V3 identity") from error
    require(result.get("status") == "PASS" and
            result.get("exact_state_status") ==
            "exact_theorem_and_state_matched" and
            fingerprints.get("status") ==
            "exact_theorem_and_state_matched" and
            fingerprints.get("promotion_eligible") is False and
            fingerprints.get("s1_evidence") is False,
            f"diagnostic result is not an exact nonpromotable pass: "
            f"{result.get('name')}")
    require(serializer.get("sha256") == V3_SERIALIZER_SHA256,
            "diagnostic used a different V3 serializer")
    hashes = [
        value for theorem in theorems for key, value in theorem.items()
        if key.endswith("_sha256")
    ] + [value for key, value in post_state.items()
         if key.endswith("_sha256")]
    require(all(isinstance(value, str) and
                SHA256_RE.fullmatch(value) is not None for value in hashes),
            "malformed diagnostic identity hash")
    require(all(type(theorem[key]) is int for theorem in theorems for key in (
        "hypothesis_count", "global_axiom_count")),
        "malformed diagnostic theorem count")
    return {
        "serializer": {
            "path": V3_SERIALIZER_RELATIVE,
            "sha256": V3_SERIALIZER_SHA256,
        },
        "theorems": theorems,
        "post_state": post_state,
    }


def candidate_projection(candidate: dict[str, Any]) -> dict[str, Any]:
    identities = candidate.get("candidate_identities")
    require(isinstance(identities, dict), "candidate lacks identities")
    require(identities.get("status") == "observed_uncompared" and
            identities.get("expected_identities_present") is False and
            identities.get("approval_sha256") is None,
            "candidate is not an unapproved observation")
    projection = {
        key: identities.get(key)
        for key in ("serializer", "theorems", "post_state")
    }
    require(projection["serializer"] == {
        "path": V3_SERIALIZER_RELATIVE,
        "sha256": V3_SERIALIZER_SHA256,
    }, "candidate used a different V3 serializer")
    return projection


def load_reviewer(candle_root: Path) -> tuple[Any, Any, dict[str, Any]]:
    head = git(candle_root, "rev-parse", "HEAD")
    verify_git_root(candle_root, head, "reviewer Candle")
    candle_dir = candle_root / "candle"
    sys.path.insert(0, str(candle_dir))
    try:
        reference = importlib.import_module("reference_fingerprints")
        manifest = importlib.import_module("top100_manifest")
    finally:
        sys.path.pop(0)
    records = {
        relative: file_record(candle_root / relative)
        for relative in (
            "candle/reference_fingerprints.py",
            "candle/reference_protocol.py",
            "candle/top100_manifest.py",
            V3_SERIALIZER_RELATIVE,
        )
    }
    require(records[V3_SERIALIZER_RELATIVE]["sha256"] == V3_SERIALIZER_SHA256,
            "reviewer has different V3 serializer bytes")
    return reference, manifest, {
        "root": str(candle_root), "git_head": head, "git_status": [],
        "files": records,
    }


def validate_contract(contract: dict[str, Any], collection_root: Path,
                      reviewer_manifest: Any) -> list[dict[str, Any]]:
    require(set(contract) == CONTRACT_FIELDS and contract.get("schema") == 5,
            "collection is not exact schema 5")
    require(contract.get("kind") ==
            "candle-great100-two-sweep-reference-collection" and
            contract.get("approval_status") ==
            "candidate_collection_only_unapproved" and
            contract.get("promotion_allowed") is False and
            contract.get("sweep_count") == 2 and
            contract.get("target_count") == 65 and
            contract.get("total_target_runs") == 130 and
            contract.get("source_mode") == "manifest-exact",
            "malformed collection boundary")
    try:
        reviewer_manifest._validate_schema5_collection_extensions(contract)
    except ValueError as error:
        raise AuditError(str(error)) from error
    inventory = contract.get("inventory")
    require(isinstance(inventory, dict) and
            inventory.get("target_count") == 65 and
            inventory.get("source_count") == 66 and
            inventory.get("request_count") == 97 and
            isinstance(inventory.get("targets"), list) and
            len(inventory["targets"]) == 65,
            "malformed collection inventory")
    targets = inventory["targets"]
    for index, target in enumerate(targets, 1):
        require(isinstance(target, dict) and target.get("index") == index and
                isinstance(target.get("name"), str) and
                isinstance(target.get("load_files"), list) and
                isinstance(target.get("load_file_sha256"), dict) and
                isinstance(target.get("theorem_names"), list),
                f"malformed collection inventory target {index}")

    for label in ("project", "candle", "reference"):
        item = contract[label]
        verify_git_root(Path(item["root"]), item["git_head"], label)
    project = contract["project"]
    project_controller = project["controller"]
    observed_controller = file_record(
        Path(project["root"]) / project_controller["path"])
    require(project_controller["bytes"] == observed_controller["bytes"] and
            project_controller["sha256"] == observed_controller["sha256"],
            "collection project controller changed")
    controller = contract["controller"]
    controller_file = file_record(Path(controller["path"]))
    require(controller["bytes"] == controller_file["bytes"] and
            controller["sha256"] == controller_file["sha256"] and
            controller["sha256"] == project_controller["sha256"],
            "collection controller pin mismatch")
    candle = contract["candle"]
    for key in ("collector", "protocol", "manifest", "serializer",
                "source_contract"):
        record = candle[key]
        observed = file_record(Path(candle["root"]) / record["path"])
        require(record["bytes"] == observed["bytes"] and
                record["sha256"] == observed["sha256"],
                f"collection Candle {key} changed")
    contract_path = collection_root / "collection-contract.json"
    require(contract_path.is_file(), "missing collection contract")
    return targets


def validate_source_policy(contract: dict[str, Any]) -> dict[str, Any]:
    reference = contract["reference"]
    root = Path(reference["root"])
    policy = reference["source_policy"]
    require(policy == load_json(
        Path(contract["candle"]["root"]) /
        contract["candle"]["source_contract"]["path"],
        "source policy"), "collection source-policy copies differ")
    historical = policy["historical_upstream_commit"]
    selected = policy["exact_source_reference_commit"]
    require(reference["git_head"] == selected and
            git(root, "rev-parse", f"{selected}^") == historical,
            "exact reference is not the reviewed one-commit child")
    changed = set(git(root, "diff-tree", "--no-commit-id", "--name-only",
                      "-r", selected).splitlines())
    deltas = policy["compatibility_deltas"]
    require(changed == {delta["path"] for delta in deltas} and
            len(deltas) == 3,
            "reference source-delta set differs")
    for delta in deltas:
        historical_bytes = subprocess.check_output([
            "/usr/bin/git", "-C", str(root), "show",
            f"{historical}:{delta['path']}",
        ])
        selected_bytes = subprocess.check_output([
            "/usr/bin/git", "-C", str(root), "show",
            f"{selected}:{delta['path']}",
        ])
        require(sha256_bytes(historical_bytes) == delta["historical_sha256"] and
                sha256_bytes(selected_bytes) == delta["selected_sha256"] and
                isinstance(delta.get("reason"), str) and delta["reason"],
                f"source delta differs: {delta['path']}")
    return policy


def validate_closed_receipt(receipt: dict[str, Any], contract: dict[str, Any],
                            collection_root: Path,
                            observed: dict[tuple[int, int], dict[str, Any]]) -> None:
    require(set(receipt) == RECEIPT_FIELDS and receipt.get("schema") == 1 and
            receipt.get("kind") ==
            "candle-great100-two-sweep-reference-receipt" and
            receipt.get("contract_sha256") == canonical_sha256(contract) and
            receipt.get("sweep_count") == 2 and
            receipt.get("target_count") == 65 and
            receipt.get("total_target_runs") == 130 and
            receipt.get("completed_target_runs") == 130 and
            receipt.get("pending_target_runs") == 0 and
            receipt.get("failure_attempt_count") == 0 and
            receipt.get("failures") == [] and
            receipt.get("publication_interruptions") == [] and
            receipt.get("outcome") == "complete" and
            receipt.get("closed") is True and
            receipt.get("approval_status") == "candidates_unapproved" and
            receipt.get("promotion_allowed") is False,
            "collection receipt is not an exact closed 130/130 receipt")
    contract_source = (collection_root / "collection-contract.json").read_bytes()
    contract_record = receipt["contract"]
    require(contract_record == {
        "path": "collection-contract.json",
        "bytes": len(contract_source),
        "sha256": sha256_bytes(contract_source),
    }, "receipt does not bind collection contract bytes")
    sweeps = receipt["sweeps"]
    require(isinstance(sweeps, list) and len(sweeps) == 2,
            "receipt lacks two sweeps")
    for sweep_number, sweep in enumerate(sweeps, 1):
        require(sweep.get("sweep") == sweep_number and
                sweep.get("target_count") == 65 and
                sweep.get("completed_count") == 65 and
                sweep.get("pending_count") == 0 and
                isinstance(sweep.get("targets"), list) and
                len(sweep["targets"]) == 65,
                f"malformed receipt sweep {sweep_number}")
        for index, row in enumerate(sweep["targets"], 1):
            item = observed[(sweep_number, index)]
            relative = item["success_relative"]
            success_record = item["success_record"]
            aggregate = row.get("success")
            require(row.get("index") == index and
                    row.get("name") == item["target"] and
                    row.get("state") == "complete" and
                    row.get("attempt_count") == 1 and
                    row.get("attempts") == [{
                        "attempt": "attempt-0001", "state": "complete"}] and
                    isinstance(aggregate, dict) and
                    aggregate.get("attempt") == "attempt-0001" and
                    aggregate.get("receipt_path") == relative and
                    aggregate.get("receipt") == {
                        "path": relative,
                        **success_record,
                    } and
                    aggregate.get("session_nonce") == item["session_nonce"] and
                    aggregate.get("artifacts") == item["success"]["artifacts"],
                    f"receipt does not bind sweep {sweep_number} target {index}")


def audit(arguments: argparse.Namespace) -> dict[str, Any]:
    collection_root = arguments.collection_root.resolve(strict=True)
    diagnostic_path = arguments.diagnostic_report.resolve(strict=True)
    reviewer_root = arguments.reviewer_candle_root.resolve(strict=True)
    reference, reviewer_manifest, reviewer = load_reviewer(reviewer_root)
    contract_path = collection_root / "collection-contract.json"
    contract = load_json(contract_path, "collection contract")
    targets = validate_contract(
        contract, collection_root, reviewer_manifest)
    source_policy = validate_source_policy(contract)

    diagnostic = load_json(diagnostic_path, "G100-S report")
    names = [target["name"] for target in targets]
    require(diagnostic.get("format") ==
            "candle-great100-v3-state-localizer-v1" and
            diagnostic.get("summary") == {
                "reported_target_count": 65,
                "exact_theorem_and_state_match_count": 65,
                "failure_count": 0,
                "timeout_count": 0,
                "diagnostic_g100_s_65_of_65": True,
            } and diagnostic.get("scope", {}).get(
                "complete_canonical_inventory") is True and
            diagnostic.get("scope", {}).get("requested_targets") == names and
            diagnostic.get("promotion", {}).get("eligible") is False and
            isinstance(diagnostic.get("results"), list) and
            [row.get("name") for row in diagnostic["results"]] == names,
            "diagnostic report is not the exact G100-S 65/65 boundary")
    diagnostic_by_name = {
        row["name"]: diagnostic_projection(row)
        for row in diagnostic["results"]
    }

    failures = sorted(collection_root.glob(
        "sweep-*/target-*/attempt-*/failure.json"))
    require(not failures, "reference collection contains a failure attempt")
    success_paths = sorted(collection_root.glob(
        "sweep-*/target-*/attempt-0001/success.json"))
    observed: dict[tuple[int, int], dict[str, Any]] = {}
    for success_path in success_paths:
        relative = success_path.relative_to(collection_root).as_posix()
        match = SUCCESS_RE.fullmatch(relative)
        require(match is not None, f"noncanonical success path: {relative}")
        sweep, index = map(int, match.groups())
        require(1 <= index <= 65 and (sweep, index) not in observed,
                f"duplicate or out-of-range success: {relative}")
        success = load_json(success_path, "attempt success")
        target = targets[index - 1]
        require(set(success) == SUCCESS_FIELDS and
                success["schema"] == 1 and
                success["kind"] == "candle-reference-attempt-success" and
                success["sweep"] == sweep and
                success["target_index"] == index and
                success["target"] == target["name"] and
                re.fullmatch(r"[0-9a-f]{64}", success["session_nonce"]) and
                success["deadlines"] == contract["deadlines"] and
                success["approval_status"] == "candidate_unapproved" and
                success["promotion_allowed"] is False and
                set(success["artifacts"]) == {
                    "candidate", "plan", "request", "transcript"},
                f"malformed attempt success: {relative}")
        base_relative = relative.removesuffix("/success.json")
        paths: dict[str, Path] = {}
        for key, filename in (
                ("candidate", "candidate.json"), ("plan", "plan.json"),
                ("request", "request.ml"), ("transcript", "transcript.log")):
            paths[key] = verify_record(
                collection_root, success["artifacts"][key],
                f"{base_relative}/{filename}", key)
        for key, filename in (
                ("collector_stdout", "collect.stdout"),
                ("collector_stderr", "collect.stderr"),
                ("validator_stdout", "validate.stdout"),
                ("validator_stderr", "validate.stderr")):
            paths[key] = verify_record(
                collection_root, success[key], f"{base_relative}/{filename}",
                key)
        candidate = load_json(paths["candidate"], "candidate")
        plan = load_json(paths["plan"], "plan")
        request_source = paths["request"].read_text(encoding="utf-8")
        transcript_source = paths["transcript"].read_text(encoding="utf-8")
        try:
            reference.validate_candidate(
                candidate, plan, request_source, transcript_source)
        except reference.CollectionError as error:
            raise AuditError(
                f"reviewer replay failed for {relative}: {error}") from error
        projection = candidate_projection(candidate)
        require(projection == diagnostic_by_name[target["name"]],
                f"native/Candle V3 identity mismatch: {target['name']}")
        require(plan["input"]["target"] == target["name"] and
                plan["input"]["theorem_names"] == target["theorem_names"] and
                plan["reference"]["git_head"] ==
                contract["reference"]["git_head"] and
                candidate["session_nonce"] == success["session_nonce"],
                f"candidate target/provenance mismatch: {relative}")
        success_source = success_path.read_bytes()
        observed[(sweep, index)] = {
            "target": target["name"],
            "session_nonce": success["session_nonce"],
            "identity": projection,
            "identity_sha256": canonical_sha256(projection),
            "success": success,
            "success_relative": relative,
            "success_record": {
                "bytes": len(success_source),
                "sha256": sha256_bytes(success_source),
            },
        }

    complete = len(observed) == 130
    require(arguments.allow_incomplete or complete,
            f"collection is incomplete: {len(observed)}/130 successes")
    paired = 0
    target_reports = []
    for index, target in enumerate(targets, 1):
        runs = [observed.get((sweep, index)) for sweep in (1, 2)]
        present = [run for run in runs if run is not None]
        if len(present) == 2:
            require(present[0]["session_nonce"] != present[1]["session_nonce"],
                    f"reference nonces repeat: {target['name']}")
            require(present[0]["identity"] == present[1]["identity"],
                    f"reference sweeps disagree: {target['name']}")
            paired += 1
        target_reports.append({
            "index": index,
            "name": target["name"],
            "completed_sweeps": [sweep for sweep in (1, 2)
                                  if (sweep, index) in observed],
            "two_sweeps_identical": len(present) == 2,
            "diagnostic_candle_identity_matched": bool(present),
            "identity_sha256": present[0]["identity_sha256"] if present else None,
            "identity": present[0]["identity"] if present else None,
            "runs": [{
                "sweep": sweep,
                "session_nonce": observed[(sweep, index)]["session_nonce"],
                "success": {
                    "path": observed[(sweep, index)]["success_relative"],
                    **observed[(sweep, index)]["success_record"],
                },
            } for sweep in (1, 2) if (sweep, index) in observed],
        })
    if complete:
        receipt = load_json(collection_root / "receipt.json", "collection receipt")
        validate_closed_receipt(receipt, contract, collection_root, observed)
    else:
        receipt = None

    return {
        "format": "candle-great100-v3-reference-authority-review-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_kind": "independent-v3-reference-review",
        "approval_status": (
            "review_complete_unapproved" if complete else
            "incremental_review_incomplete"),
        "promotion_allowed": False,
        "authority_approval_emitted": False,
        "reviewer": reviewer,
        "inputs": {
            "collection_root": str(collection_root),
            "collection_contract": file_record(contract_path),
            "collection_receipt": (
                file_record(collection_root / "receipt.json")
                if receipt is not None else None),
            "diagnostic_g100_s_report": file_record(diagnostic_path),
            "source_policy": source_policy,
            "serializer": {
                "path": V3_SERIALIZER_RELATIVE,
                "sha256": V3_SERIALIZER_SHA256,
            },
            "audit_program": file_record(PROGRAM_PATH),
        },
        "summary": {
            "completed_reference_runs": len(observed),
            "required_reference_runs": 130,
            "failed_reference_runs": 0,
            "targets_with_two_identical_sweeps": paired,
            "targets_cross_matched_to_candle_g100_s": len({
                index for _sweep, index in observed}),
            "collection_closed": complete,
            "review_complete": complete and paired == 65,
        },
        "targets": target_reports,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection-root", type=Path, required=True)
    parser.add_argument("--diagnostic-report", type=Path, required=True)
    parser.add_argument("--reviewer-candle-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--allow-incomplete", action="store_true",
        help="emit an explicitly incomplete prefix review while collection runs",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        report = audit(arguments)
        output = arguments.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        require(not output.exists(), f"refusing to overwrite review report: {output}")
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except (AuditError, KeyError, TypeError, ValueError) as error:
        print(f"authority review failed: {error}", file=sys.stderr)
        return 1
    print(f"V3 authority review: {report['summary']['completed_reference_runs']}/130")
    print(f"review report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
