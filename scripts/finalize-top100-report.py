#!/usr/bin/env python3
"""Validate and archive two complete Candle Great 100 S1 runs.

The Candle runner deliberately distinguishes a load-only PASS from an approved
semantic match. This finalizer therefore accepts exactly two schema-3 reports
and requires both reports to close the runner's S1 evidence summary. It also
validates the current linked CakeML record, retains the small provenance and
contract files needed to interpret the reports, and binds every retained file
in a closed archive inventory.

The schema-3 report does not record the linked-record hash seen by each Candle
process. The strongest available retrospective check is consequently the exact
startup witness in every transcript plus validation and archival of the single
current linked record. The archive records that limitation explicitly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


REPORT_KEYS = {
    "schema", "generated_utc", "suite", "test_count", "jobs",
    "timeout_policy", "wall_seconds", "sum_test_seconds", "counts",
    "candle_root", "candle_git_head", "candle_git_status",
    "candle_executable", "candle_executable_sha256", "log_directory",
    "fingerprint_contract", "s1_evidence", "results",
}
RESULT_KEYS = {
    "name", "files", "status", "timeout_kind", "boot_elapsed_seconds",
    "hol_elapsed_seconds", "test_elapsed_seconds",
    "fingerprint_elapsed_seconds", "total_elapsed_seconds",
    "peak_process_rss_kib", "peak_tree_rss_kib", "error_message",
    "log_path", "fingerprints",
}
FINGERPRINT_KEYS = {
    "status", "mapping_status", "expected_identities_present", "serializer",
    "theorems",
}
THEOREM_KEYS = {
    "name", "theorem_sha256", "hypotheses_sha256", "conclusion_sha256",
    "global_axioms_sha256", "hypothesis_count", "global_axiom_count",
}
S1_KEYS = {
    "requested_target_count", "reported_target_count",
    "expected_identity_target_count", "manual_review_mapping_target_count",
    "matched_target_count", "observed_uncompared_target_count",
    "missing_or_failed_fingerprint_target_count", "suite_closed",
}
TIMEOUT_KEYS = {
    "inactivity_timeout_seconds", "inactivity_resets_on", "inactivity_scope",
    "total_wall_timeout_seconds", "total_wall_scope",
    "progress_extends_total_wall_deadline",
}
FINGERPRINT_CONTRACT = {
    "serializer": "candle/fingerprint.ml structural v1",
    "load_pass_is_fingerprint_match": False,
    "expected_identity_source": "top100_manifest.json",
    "expected_mismatch_result": "FAIL",
}
S1_CLOSED = {
    "requested_target_count": 65,
    "reported_target_count": 65,
    "expected_identity_target_count": 65,
    "manual_review_mapping_target_count": 0,
    "matched_target_count": 65,
    "observed_uncompared_target_count": 0,
    "missing_or_failed_fingerprint_target_count": 0,
    "suite_closed": True,
}
LINKED_RECORD_KEYS = {
    "schema", "kind", "candle_commit", "cakeml_commit", "hol4_commit",
    "manifest_sha256", "bootstrap_record", "bootstrap_preflight",
    "bootstrap_log", "cake_patch", "cake_patch_derivation",
    "native_link_derivation", "outputs", "runtime_elf_closure",
    "version_output_sha256",
}
LINKED_OUTPUTS = {
    "cake.S", "cake.S.bootstrap", "cake", "config_enc_str.txt",
    "candle_boot.ml", "basis_ffi.c", "Makefile", "types.txt", "insulate.ml",
    "bootstrap-preflight.json", "bootstrap-provenance.json", "bootstrap.log",
}
LINKED_PASS_WITNESS = "linked CakeML provenance PASS"
FINGERPRINT_MARKER = "CANDLE_FINGERPRINT_V1\t"
SHA256_RE = re.compile(r"[0-9a-f]{64}")
COMMIT_RE = re.compile(r"[0-9a-f]{40}")


class ValidationError(ValueError):
    """The proposed S1 bundle is incomplete, inconsistent, or unauthenticated."""


@dataclass(frozen=True)
class FileIdentity:
    bytes: int
    sha256: str

    def as_json(self) -> dict[str, object]:
        return {"bytes": self.bytes, "sha256": self.sha256}


@dataclass
class ValidatedRun:
    source_path: Path
    source_identity: FileIdentity
    report: dict[str, Any]
    results: list[dict[str, Any]]
    log_paths: list[Path]
    log_identities: list[FileIdentity]


@dataclass
class ValidatedBundle:
    runs: tuple[ValidatedRun, ValidatedRun]
    candle_root: Path
    executable: Path
    executable_identity: FileIdentity
    linked_record: dict[str, Any]
    retained_sources: dict[str, tuple[Path, FileIdentity]]
    semantics: list[dict[str, Any]]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def is_number(value: object) -> bool:
    return (((isinstance(value, int) and not isinstance(value, bool)) or
             isinstance(value, float)) and math.isfinite(value))


def require_sha256(value: object, label: str) -> str:
    require(isinstance(value, str) and SHA256_RE.fullmatch(value) is not None,
            f"malformed SHA-256 for {label}")
    return value


def require_commit(value: object, label: str) -> str:
    require(isinstance(value, str) and COMMIT_RE.fullmatch(value) is not None,
            f"malformed commit for {label}")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def ordinary_file(path: Path, label: str) -> Path:
    require(path.is_absolute(), f"{label} path is not absolute: {path}")
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise ValidationError(f"missing {label}: {path}") from error
    require(not path.is_symlink(), f"{label} is a symlink: {path}")
    require(stat.S_ISREG(metadata.st_mode), f"{label} is not an ordinary file: {path}")
    require(path.resolve(strict=True) == path, f"{label} path is not canonical: {path}")
    return path


def ordinary_directory(path: Path, label: str) -> Path:
    require(path.is_absolute(), f"{label} path is not absolute: {path}")
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise ValidationError(f"missing {label}: {path}") from error
    require(not path.is_symlink(), f"{label} is a symlink: {path}")
    require(stat.S_ISDIR(metadata.st_mode), f"{label} is not an ordinary directory: {path}")
    require(path.resolve(strict=True) == path, f"{label} path is not canonical: {path}")
    return path


def file_key(path: Path, label: str) -> tuple[int, int]:
    path = ordinary_file(path, label)
    metadata = path.stat()
    return metadata.st_dev, metadata.st_ino


def file_identity(path: Path, label: str) -> FileIdentity:
    path = ordinary_file(path, label)
    digest = hashlib.sha256()
    byte_count = 0
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            byte_count += len(block)
            digest.update(block)
    return FileIdentity(byte_count, digest.hexdigest())


def lexical_absolute(path: Path) -> Path:
    """Make a path absolute without resolving away a symlink component."""
    return Path(os.path.abspath(path))


def load_json(path: Path, label: str) -> tuple[dict[str, Any], FileIdentity]:
    path = ordinary_file(path, label)
    try:
        source_bytes = path.read_bytes()
        source_text = source_bytes.decode("utf-8", errors="strict")
        value = json.loads(
            source_text,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidationError(f"malformed JSON in {label}: {path}") from error
    require(isinstance(value, dict), f"{label} is not a JSON object: {path}")
    identity = FileIdentity(len(source_bytes), hashlib.sha256(source_bytes).hexdigest())
    return value, identity


def validate_file_record(value: object, label: str) -> dict[str, object]:
    require(isinstance(value, dict) and set(value) == {"bytes", "sha256"},
            f"malformed file record for {label}")
    require(is_int(value["bytes"]) and value["bytes"] >= 0,
            f"malformed byte count for {label}")
    require_sha256(value["sha256"], label)
    return value


def validate_theorem_record(value: object, label: str) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == THEOREM_KEYS,
            f"malformed theorem record for {label}")
    require(isinstance(value["name"], str) and value["name"],
            f"missing theorem name for {label}")
    for field in (
        "theorem_sha256", "hypotheses_sha256", "conclusion_sha256",
        "global_axioms_sha256",
    ):
        require_sha256(value[field], f"{label}.{field}")
    for field in ("hypothesis_count", "global_axiom_count"):
        require(is_int(value[field]) and value[field] >= 0,
                f"malformed {field} for {label}")
    return value


def validate_manifest(root: Path) -> tuple[dict[str, Any], FileIdentity, Path]:
    path = root / "candle/top100_manifest.json"
    manifest, identity = load_json(path, "Great 100 manifest")
    require(manifest.get("schema_version") == 1,
            "unsupported Great 100 manifest schema")
    targets = manifest.get("targets")
    require(manifest.get("target_count") == 65 and
            isinstance(targets, list) and len(targets) == 65,
            "Great 100 manifest does not contain exactly 65 targets")
    names: list[str] = []
    serializer_hashes: set[str] = set()
    global_axiom_identities: set[tuple[str, int]] = set()
    for index, target in enumerate(targets, 1):
        require(isinstance(target, dict), f"malformed manifest target {index}")
        name = target.get("name")
        require(isinstance(name, str) and name.startswith("100/"),
                f"malformed manifest target name at {index}")
        names.append(name)
        files = target.get("load_files")
        require(isinstance(files, list) and files and
                all(isinstance(item, str) and item for item in files),
                f"malformed load files for {name}")
        require(target.get("skip") is None, f"hidden Great 100 skip for {name}")
        load_hashes = target.get("load_file_sha256")
        require(isinstance(load_hashes, dict) and set(load_hashes) == set(files),
                f"load-file identity mismatch for {name}")
        for file_name, digest in load_hashes.items():
            require_sha256(digest, f"{name}:{file_name}")
        request = target.get("fingerprint_request")
        require(isinstance(request, dict) and request.get("mapping_status") == "audited",
                f"unaudited fingerprint mapping for {name}")
        requested = request.get("theorems")
        require(isinstance(requested, list) and requested,
                f"missing theorem request for {name}")
        requested_names: list[str] = []
        for theorem in requested:
            require(isinstance(theorem, dict) and
                    isinstance(theorem.get("name"), str),
                    f"malformed theorem request for {name}")
            requested_names.append(theorem["name"])
        expected = request.get("expected_identities")
        require(isinstance(expected, dict) and
                set(expected) == {"serializer_sha256", "theorems"},
                f"missing approved expected identities for {name}")
        require_sha256(expected["serializer_sha256"], f"{name} serializer")
        serializer_hashes.add(expected["serializer_sha256"])
        expected_theorems = expected.get("theorems")
        require(isinstance(expected_theorems, list) and
                len(expected_theorems) == len(requested_names),
                f"expected theorem count mismatch for {name}")
        for theorem_index, theorem in enumerate(expected_theorems):
            record = validate_theorem_record(theorem, f"{name} theorem {theorem_index + 1}")
            require(record["name"] == requested_names[theorem_index],
                    f"expected theorem order mismatch for {name}")
            global_axiom_identities.add((
                record["global_axioms_sha256"], record["global_axiom_count"]))
    require(len(set(names)) == 65, "duplicate Great 100 target in manifest")
    require(len(serializer_hashes) == 1,
            "Great 100 targets do not use one serializer identity")
    require(len(global_axiom_identities) == 1 and
            next(iter(global_axiom_identities))[1] == 3,
            "Great 100 expected identities do not use one three-axiom set")
    serializer = file_identity(root / "candle/fingerprint.ml", "fingerprint serializer")
    require(serializer.sha256 == next(iter(serializer_hashes)),
            "approved serializer does not match candle/fingerprint.ml")
    return manifest, identity, path


def validate_timeout_policy(value: object) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == TIMEOUT_KEYS,
            "malformed timeout policy")
    inactivity = value["inactivity_timeout_seconds"]
    wall = value["total_wall_timeout_seconds"]
    require(is_number(inactivity) and inactivity > 0,
            "inactivity timeout must be positive")
    require(is_number(wall) and wall > 0,
            "Great 100 promotion requires a positive total wall timeout")
    require(value["inactivity_resets_on"] == "each complete REPL output line",
            "unexpected inactivity reset policy")
    require(value["inactivity_scope"] ==
            "each REPL expect wait, including initial boot",
            "unexpected inactivity scope")
    require(value["total_wall_scope"] ==
            "process spawn through fingerprint capture",
            "unexpected total wall scope")
    require(value["progress_extends_total_wall_deadline"] is False,
            "progress must not extend the total wall deadline")
    return value


def validate_report(
    report: dict[str, Any], manifest: dict[str, Any], source_path: Path,
    source_identity: FileIdentity,
) -> ValidatedRun:
    require(set(report) == REPORT_KEYS, "malformed schema-3 Great 100 report")
    require(report["schema"] == 3 and report["suite"] == "top100",
            "not a schema-3 Great 100 report")
    require(isinstance(report["generated_utc"], str),
            "Great 100 report has malformed generation time")
    try:
        generated = datetime.fromisoformat(report["generated_utc"])
    except ValueError as error:
        raise ValidationError("Great 100 report has malformed generation time") from error
    require(generated.tzinfo is not None,
            "Great 100 report generation time lacks a timezone")
    require(report["test_count"] == 65,
            "Great 100 report must contain 65 test entries")
    require(is_int(report["jobs"]) and report["jobs"] > 0,
            "Great 100 report has invalid worker count")
    validate_timeout_policy(report["timeout_policy"])
    for field in ("wall_seconds", "sum_test_seconds"):
        require(is_number(report[field]) and report[field] > 0,
                f"Great 100 report has invalid {field}")
    require(report["counts"] == {"PASS": 65, "FAIL": 0, "TIMEOUT": 0},
            "Great 100 suite did not pass completely")
    require(report["candle_git_status"] == [],
            "Candle worktree was not clean during the suite")
    require_commit(report["candle_git_head"], "Candle report head")
    require_sha256(report["candle_executable_sha256"], "Candle executable")
    require(report["fingerprint_contract"] == FINGERPRINT_CONTRACT,
            "unexpected Great 100 fingerprint contract")
    require(isinstance(report["s1_evidence"], dict) and
            set(report["s1_evidence"]) == S1_KEYS and
            report["s1_evidence"] == S1_CLOSED,
            "Great 100 S1 evidence summary is not closed")

    require(isinstance(report["candle_root"], str), "malformed Candle root")
    require(isinstance(report["candle_executable"], str),
            "malformed Candle executable path")
    require(isinstance(report["log_directory"], str),
            "malformed Great 100 log directory")
    candle_root = ordinary_directory(Path(report["candle_root"]), "Candle root")
    executable = ordinary_file(
        Path(report["candle_executable"]), "Candle executable")
    require(executable == candle_root / "candle/build/cake",
            "Candle executable is outside the canonical build path")
    log_directory = ordinary_directory(
        Path(report["log_directory"]), "Great 100 log directory")

    results = report["results"]
    require(isinstance(results, list) and len(results) == 65,
            "malformed Great 100 result table")
    manifest_targets = manifest["targets"]
    require([result.get("name") for result in results] ==
            [target["name"] for target in manifest_targets],
            "Great 100 results are not in exact manifest order")

    log_paths: list[Path] = []
    log_identities: list[FileIdentity] = []
    for result, target in zip(results, manifest_targets):
        name = target["name"]
        require(isinstance(result, dict) and set(result) == RESULT_KEYS,
                f"malformed result record for {name}")
        require(result["status"] == "PASS" and result["timeout_kind"] is None and
                result["error_message"] == "",
                f"non-passing result for {name}")
        require(result["files"] == target["load_files"],
                f"load-file order mismatch for {name}")
        for field in (
            "boot_elapsed_seconds", "hol_elapsed_seconds", "test_elapsed_seconds",
            "fingerprint_elapsed_seconds", "total_elapsed_seconds",
        ):
            require(is_number(result[field]) and result[field] >= 0,
                    f"invalid {field} for {name}")
        require(result["total_elapsed_seconds"] > 0,
                f"missing elapsed time for {name}")
        require(math.isclose(
            result["total_elapsed_seconds"],
            sum(result[field] for field in (
                "boot_elapsed_seconds", "hol_elapsed_seconds",
                "test_elapsed_seconds", "fingerprint_elapsed_seconds")),
            rel_tol=1e-12, abs_tol=1e-9,
        ), f"elapsed phase accounting mismatch for {name}")
        for field in ("peak_process_rss_kib", "peak_tree_rss_kib"):
            require(is_int(result[field]) and result[field] > 0,
                    f"missing {field} for {name}")
        require(result["peak_tree_rss_kib"] >= result["peak_process_rss_kib"],
                f"tree RSS is smaller than process RSS for {name}")

        observed = result["fingerprints"]
        require(isinstance(observed, dict) and set(observed) == FINGERPRINT_KEYS,
                f"malformed fingerprint result for {name}")
        require(observed["status"] == "matched" and
                observed["mapping_status"] == "audited" and
                observed["expected_identities_present"] is True,
                f"unapproved fingerprint result for {name}")
        expected = target["fingerprint_request"]["expected_identities"]
        require(observed["serializer"] == {
            "path": "candle/fingerprint.ml",
            "sha256": expected["serializer_sha256"],
        }, f"serializer mismatch for {name}")
        observed_theorems = observed["theorems"]
        require(isinstance(observed_theorems, list) and
                observed_theorems == expected["theorems"],
                f"semantic fingerprint mismatch for {name}")
        for theorem_index, theorem in enumerate(observed_theorems):
            validate_theorem_record(theorem, f"{name} observed theorem {theorem_index + 1}")

        log_path = ordinary_file(Path(result["log_path"]), f"log for {name}")
        require(log_path.parent == log_directory,
                f"log for {name} is outside the reported log directory")
        log_paths.append(log_path)
        try:
            log_bytes = log_path.read_bytes()
            lines = log_bytes.decode("utf-8", errors="strict").splitlines()
        except UnicodeDecodeError as error:
            raise ValidationError(f"log for {name} is not strict UTF-8") from error
        log_identities.append(FileIdentity(
            len(log_bytes), hashlib.sha256(log_bytes).hexdigest()))
        require(lines.count(LINKED_PASS_WITNESS) == 1,
                f"log for {name} lacks one exact linked-provenance witness")
        require(sum(line.startswith(FINGERPRINT_MARKER) for line in lines) ==
                len(observed_theorems),
                f"log for {name} has the wrong fingerprint-record count")

    require(len(set(log_paths)) == 65, "duplicate Great 100 log path")
    require(len({file_key(path, "Great 100 log") for path in log_paths}) == 65,
            "Great 100 logs contain hard-link aliases")
    require(math.isclose(
        report["sum_test_seconds"],
        sum(result["total_elapsed_seconds"] for result in results),
        rel_tol=1e-12, abs_tol=1e-6,
    ), "Great 100 aggregate test time mismatch")
    return ValidatedRun(
        source_path, source_identity, report, results, log_paths, log_identities)


def validate_linked_runtime(
    root: Path, executable: Path, head: str, executable_sha256: str,
) -> tuple[dict[str, Any], dict[str, tuple[Path, FileIdentity]], FileIdentity]:
    build = ordinary_directory(root / "candle/build", "Candle build directory")
    helper = ordinary_file(
        root / "candle/cakeml_artifact_provenance.py", "provenance helper")
    completed = subprocess.run(
        ["/usr/bin/python3", "-I", str(helper), "check-linked",
         "--candle-root", str(root)],
        check=False,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
    )
    require(completed.returncode == 0 and
            completed.stdout == LINKED_PASS_WITNESS + "\n" and
            completed.stderr == "",
            "authoritative linked-provenance validation failed")

    record_path = build / "cakeml-build-provenance.json"
    record, _ = load_json(record_path, "linked provenance record")
    require(set(record) == LINKED_RECORD_KEYS and record["schema"] == 6 and
            record["kind"] == "candle-linked-pinned-cakeml",
            "unsupported linked provenance record")
    require(record["candle_commit"] == head,
            "linked record does not bind the reported Candle head")
    require_commit(record["cakeml_commit"], "linked CakeML commit")
    require_commit(record["hol4_commit"], "linked HOL4 commit")
    require_sha256(record["manifest_sha256"], "linked direct manifest")
    require_sha256(record["version_output_sha256"], "linked version output")

    outputs = record["outputs"]
    require(isinstance(outputs, dict) and set(outputs) == LINKED_OUTPUTS,
            "linked output set mismatch")
    observed_outputs: dict[str, FileIdentity] = {}
    for name in sorted(LINKED_OUTPUTS):
        expected = validate_file_record(outputs[name], f"linked output {name}")
        observed = file_identity(build / name, f"linked output {name}")
        observed_outputs[name] = observed
        require(observed.as_json() == expected,
                f"linked output changed: {name}")
    executable_identity = observed_outputs["cake"]
    require(executable_identity.sha256 == executable_sha256 and
            executable_identity.as_json() == outputs["cake"],
            "reported executable does not match linked provenance")

    direct_manifest = root / "candle/flyspeck_manifest.json"
    require(file_identity(direct_manifest, "direct manifest").sha256 ==
            record["manifest_sha256"],
            "linked direct-manifest identity mismatch")
    for field, name in (
        ("bootstrap_record", "bootstrap-provenance.json"),
        ("bootstrap_preflight", "bootstrap-preflight.json"),
        ("bootstrap_log", "bootstrap.log"),
    ):
        expected = validate_file_record(record[field], field)
        require(file_identity(build / name, field).as_json() == expected,
                f"linked {field} changed")
    require(file_identity(root / "candle/cake.S.patch", "CakeML assembly patch").as_json()
            == validate_file_record(record["cake_patch"], "CakeML assembly patch"),
            "linked CakeML assembly patch changed")

    retained_paths = {
        "contracts/top100_manifest.json": root / "candle/top100_manifest.json",
        "contracts/fingerprint.ml": root / "candle/fingerprint.ml",
        "contracts/flyspeck_manifest.json": direct_manifest,
        "controllers/regression.py": root / "candle/regression.py",
        "controllers/top100_manifest.py": root / "candle/top100_manifest.py",
        "controllers/cakeml_artifact_provenance.py": helper,
        "controllers/candle.sh": root / "candle.sh",
        "provenance/cakeml-build-provenance.json": record_path,
        "provenance/bootstrap-provenance.json": build / "bootstrap-provenance.json",
        "provenance/bootstrap-preflight.json": build / "bootstrap-preflight.json",
        "provenance/bootstrap.log": build / "bootstrap.log",
        "provenance/cake.S.patch": root / "candle/cake.S.patch",
    }
    retained = {
        relative: (path, file_identity(path, f"retained evidence {relative}"))
        for relative, path in retained_paths.items()
    }
    return record, retained, executable_identity


def validate_reports(report_paths: Iterable[Path]) -> ValidatedBundle:
    paths = tuple(lexical_absolute(Path(path)) for path in report_paths)
    require(len(paths) == 2, "exactly two Great 100 reports are required")
    require(paths[0] != paths[1], "the two Great 100 reports must be distinct")
    require(file_key(paths[0], "Great 100 report 1") !=
            file_key(paths[1], "Great 100 report 2"),
            "the two Great 100 reports are hard-link aliases")
    loaded: list[tuple[dict[str, Any], FileIdentity]] = [
        load_json(path, f"Great 100 report {index}")
        for index, path in enumerate(paths, 1)
    ]
    roots = []
    for index, value in enumerate(loaded, 1):
        root_value = value[0].get("candle_root")
        require(isinstance(root_value, str),
                f"malformed Candle root for report {index}")
        roots.append(ordinary_directory(
            Path(root_value), f"Candle root for report {index}"))
    require(roots[0] == roots[1], "Great 100 reports use different Candle roots")
    manifest, _, _ = validate_manifest(roots[0])
    runs = tuple(
        validate_report(report, manifest, path, identity)
        for path, (report, identity) in zip(paths, loaded)
    )

    first, second = (run.report for run in runs)
    require(first["generated_utc"] != second["generated_utc"],
            "the two Great 100 reports do not identify distinct runs")
    for field in (
        "candle_root", "candle_git_head", "candle_executable",
        "candle_executable_sha256", "jobs", "timeout_policy",
        "fingerprint_contract",
    ):
        require(first[field] == second[field],
                f"Great 100 reports disagree on {field}")
    semantics = [
        {"name": result["name"], "fingerprints": result["fingerprints"]}
        for result in runs[0].results
    ]
    second_semantics = [
        {"name": result["name"], "fingerprints": result["fingerprints"]}
        for result in runs[1].results
    ]
    require(semantics == second_semantics,
            "the two Great 100 semantic projections differ")
    all_logs = runs[0].log_paths + runs[1].log_paths
    require(len(set(all_logs)) == 130 and
            len({file_key(path, "Great 100 log") for path in all_logs}) == 130,
            "the two Great 100 runs reuse transcript files")

    root = roots[0]
    executable = Path(first["candle_executable"])
    linked, retained, executable_identity = validate_linked_runtime(
        root, executable, first["candle_git_head"],
        first["candle_executable_sha256"],
    )
    return ValidatedBundle(
        runs=(runs[0], runs[1]), candle_root=root, executable=executable,
        executable_identity=executable_identity, linked_record=linked,
        retained_sources=retained, semantics=semantics,
    )


def copy_verified(
    source: Path, destination: Path, label: str,
    expected: FileIdentity | None = None,
) -> FileIdentity:
    before = file_identity(source, label)
    if expected is not None:
        require(before == expected, f"source changed before archiving {label}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    require(not destination.exists() and not destination.is_symlink(),
            f"archive path already exists: {destination}")
    digest = hashlib.sha256()
    byte_count = 0
    with source.open("rb") as reader, destination.open("xb") as writer:
        for block in iter(lambda: reader.read(1024 * 1024), b""):
            writer.write(block)
            digest.update(block)
            byte_count += len(block)
    copied = FileIdentity(byte_count, digest.hexdigest())
    require(copied == before and file_identity(source, label) == before,
            f"source changed while archiving {label}")
    require(file_identity(destination.resolve(), f"archived {label}") == before,
            f"archived copy mismatch for {label}")
    return before


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_new(path: Path, value: bytes) -> FileIdentity:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(value)
    return file_identity(path.resolve(), f"generated archive file {path.name}")


def safe_name(name: str) -> str:
    return name.replace("/", "_").replace("-", "_")


def archive(report_paths: Iterable[Path], destination: Path) -> None:
    destination = lexical_absolute(Path(destination))
    require(not destination.exists() and not destination.is_symlink(),
            f"archive destination already exists: {destination}")
    parent = ordinary_directory(destination.parent, "archive parent")
    bundle = validate_reports(report_paths)

    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.tmp-", dir=parent))
    retained: dict[str, dict[str, object]] = {}
    run_inventory: list[dict[str, object]] = []
    try:
        for run_index, run in enumerate(bundle.runs, 1):
            report_relative = f"run-{run_index}/report.json"
            identity = copy_verified(
                run.source_path, stage / report_relative,
                f"Great 100 source report {run_index}", run.source_identity,
            )
            retained[report_relative] = identity.as_json()
            logs: list[dict[str, object]] = []
            for result_index, (result, log_path, log_expected) in enumerate(
                    zip(run.results, run.log_paths, run.log_identities), 1):
                log_relative = (
                    f"run-{run_index}/logs/{result_index:02d}-"
                    f"{safe_name(result['name'])}.log"
                )
                log_identity = copy_verified(
                    log_path, stage / log_relative,
                    f"run {run_index} log for {result['name']}", log_expected,
                )
                retained[log_relative] = log_identity.as_json()
                logs.append({
                    "name": result["name"],
                    "source_path": str(log_path),
                    "archive_path": log_relative,
                    **log_identity.as_json(),
                })
            run_inventory.append({
                "run": run_index,
                "source_report_path": str(run.source_path),
                "archive_report_path": report_relative,
                "source_report": identity.as_json(),
                "logs": logs,
            })

        for relative, (source, expected) in sorted(bundle.retained_sources.items()):
            identity = copy_verified(source, stage / relative, relative, expected)
            retained[relative] = identity.as_json()

        semantics_relative = "semantic-projection.json"
        semantics_identity = write_new(
            stage / semantics_relative, canonical_json_bytes(bundle.semantics))
        retained[semantics_relative] = semantics_identity.as_json()

        metadata = {
            "schema": 1,
            "kind": "candle-great100-two-clean-run-archive",
            "claim": "Great 100 S1 evidence bundle only; not S2 or S3 evidence",
            "candle_commit": bundle.runs[0].report["candle_git_head"],
            "candle_executable": {
                "source_path": str(bundle.executable),
                **bundle.executable_identity.as_json(),
            },
            "linked_provenance": {
                "schema": bundle.linked_record["schema"],
                "kind": bundle.linked_record["kind"],
                "archive_path": "provenance/cakeml-build-provenance.json",
                **retained["provenance/cakeml-build-provenance.json"],
                "per_process_binding": (
                    "schema-3 transcripts contain one exact successful validation "
                    "witness but do not record the linked-record SHA-256"
                ),
            },
            "comparison": {
                "runs": 2,
                "target_count": 65,
                "projection": "ordered {name,fingerprints}",
                "identical": True,
                "archive_path": semantics_relative,
                "sha256": semantics_identity.sha256,
            },
            "contracts": {
                "top100_manifest": {
                    "archive_path": "contracts/top100_manifest.json",
                    **retained["contracts/top100_manifest.json"],
                },
                "fingerprint_serializer": {
                    "archive_path": "contracts/fingerprint.ml",
                    **retained["contracts/fingerprint.ml"],
                },
            },
            "runs": run_inventory,
            "retained_files": dict(sorted(retained.items())),
        }
        bundle_relative = "bundle.json"
        bundle_identity = write_new(
            stage / bundle_relative, canonical_json_bytes(metadata))
        checksum_rows = [
            (record["sha256"], relative)
            for relative, record in retained.items()
        ]
        checksum_rows.append((bundle_identity.sha256, bundle_relative))
        checksum_rows.sort(key=lambda row: row[1])
        write_new(
            stage / "SHA256SUMS",
            "".join(f"{digest}  {relative}\n" for digest, relative in checksum_rows).encode(),
        )

        require(file_identity(bundle.executable, "Candle executable") ==
                bundle.executable_identity,
                "Candle executable changed while creating the archive")
        require(not destination.exists(),
                f"archive destination appeared during creation: {destination}")
        stage.rename(destination)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="validate and archive exactly two schema-3 Great 100 S1 runs")
    parser.add_argument("report_one", type=Path)
    parser.add_argument("report_two", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    archive(
        (args.report_one, args.report_two), args.destination,
    )


if __name__ == "__main__":
    main()
