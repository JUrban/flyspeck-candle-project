#!/usr/bin/env python3
"""Fail-closed archival of two independently authorized Great100 schema-4 runs.

Schema 3 did not bind a run nonce, exact transcript bytes, the linked-record
bytes seen by each Candle process, the committed runner/launcher inputs, the
complete source closure, or an independent approval artifact. It is therefore
unconditionally non-promotable here. This program accepts exactly two schema-4
reports and an out-of-band receipt whose SHA-256 is supplied separately.

Every file used for acceptance is copied once through an O_NOFOLLOW descriptor
into a private archive staging directory. Validation and helper execution use
those staged bytes; the named source is never reread to populate the archive.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable


PROGRAM_PATH = Path(__file__).resolve()
GIT_REQUESTED_PATH = Path("/usr/bin/git")
PYTHON_PATH = Path(sys.executable).resolve()

REPORT_KEYS = {
    "schema", "generated_utc", "suite_started_utc", "suite", "test_count", "jobs",
    "timeout_policy", "wall_seconds", "sum_test_seconds", "counts",
    "candle_root", "candle_git_head", "candle_git_status",
    "candle_executable", "log_directory",
    "fingerprint_contract", "s1_evidence", "run_evidence",
    "execution_contract", "source_closure", "independent_approval",
    "linked_record", "results",
}
RESULT_KEYS = {
    "name", "files", "status", "timeout_kind", "boot_elapsed_seconds",
    "hol_elapsed_seconds", "test_elapsed_seconds",
    "fingerprint_elapsed_seconds", "total_elapsed_seconds",
    "peak_process_rss_kib", "peak_tree_rss_kib", "error_message",
    "log_path", "process_evidence", "fingerprints",
}
PROCESS_EVIDENCE_KEYS = {
    "suite_nonce", "process_nonce", "pid", "started_utc", "completed_utc",
    "exit_code", "markers", "linked_record_sha256", "transcript",
    "pre_runtime_state", "post_runtime_state", "resource_sampling",
}
RUN_EVIDENCE_KEYS = {
    "suite_nonce", "marker_contract", "linked_record_sha256",
    "source_closure_sha256", "independent_approval_sha256",
}
FINGERPRINT_KEYS = {
    "status", "mapping_status", "expected_identities_present", "serializer",
    "theorems", "post_state", "approval_sha256",
}
THEOREM_KEYS = {
    "name", "theorem_sha256", "hypotheses_sha256", "conclusion_sha256",
    "global_axioms_sha256", "hypothesis_count", "global_axiom_count",
}
POST_STATE_KEYS = {
    "kernel_state_sha256", "type_constants_sha256", "type_constant_count",
    "term_constants_sha256", "term_constant_count", "definitions_sha256",
    "definition_count", "global_axioms_sha256", "global_axiom_count",
}
RUNTIME_STATE_KEYS = {
    "candle_git_head", "candle_git_status", "linked_record_sha256",
    "candle_executable", "execution_contract_sha256", "source_closure_sha256",
}
RESOURCE_SAMPLING_KEYS = {
    "interval_seconds", "sample_count", "root_observed", "sampler_completed",
    "peak_process_rss_kib", "peak_tree_rss_kib",
}
MARKER_KEYS = {"suite_line", "start_line", "linked_line", "complete_line"}
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
EXECUTION_CONTRACT_PATHS = {
    "candle/cakeml_artifact_provenance.py": "100644",
    "candle/regression.py": "100644",
    "candle/top100_manifest.json": "100644",
    "candle/fingerprint.ml": "100644",
    "candle.sh": "100755",
}
REFERENCE_VALIDATOR_PATH = "candle/reference_fingerprints.py"
FINGERPRINT_CONTRACT = {
    "serializer": "candle/fingerprint.ml structural v2",
    "load_pass_is_fingerprint_match": False,
    "expected_identity_source": (
        "separate independently reviewed approval artifact, "
        "fail-closed through top100_manifest.json"
    ),
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
APPROVAL_KEYS = {
    "schema", "artifact_kind", "approval_status", "promotion_allowed",
    "inventory_contract_sha256", "serializer_sha256", "reference_policy",
    "review", "targets",
}
REFERENCE_POLICY_KEYS = {
    "historical_upstream_commit", "exact_source_reference_commit",
    "compatibility_deltas",
}
REFERENCE_DELTA_KEYS = {
    "path", "historical_sha256", "selected_sha256", "reason",
}
APPROVAL_REVIEW_KEYS = {"reviewer", "approved_utc", "review_commit", "decision"}
APPROVAL_TARGET_KEYS = {"name", "reference_runs", "expected_identity"}
APPROVAL_IDENTITY_KEYS = {"serializer_sha256", "theorems", "post_state"}
AUTHORIZATION_KEYS = {
    "schema", "kind", "issued_utc", "authority", "reports",
    "suite_nonces", "linked_record_sha256", "source_closure_sha256",
    "semantic_projection_sha256", "independent_approval", "project", "tools",
}
MARKER_CONTRACT = "candle-great100-process-markers-v1"
LINKED_PASS_WITNESS = "linked CakeML provenance PASS"
FINGERPRINT_MARKER = "CANDLE_FINGERPRINT_V2"
STATE_FINGERPRINT_MARKER = "CANDLE_STATE_FINGERPRINT_V2"
SHA256_RE = re.compile(r"[0-9a-f]{64}")
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
NONCE_RE = re.compile(r"[0-9a-f]{64}")
DECIMAL_RE = re.compile(r"(?:0|[1-9][0-9]*)")
EMPTY_HYPOTHESES_WIRE = b"4:list1:0"
EMPTY_HYPOTHESES_SHA256 = hashlib.sha256(EMPTY_HYPOTHESES_WIRE).hexdigest()

REFERENCE_REPLAY_CONTROLLER = r'''import json
from pathlib import Path
import sys
import types

sys.dont_write_bytecode = True


def load_exact(name, path):
    source_path = Path(path)
    source = source_path.read_bytes()
    module = types.ModuleType(name)
    module.__file__ = str(source_path)
    module.__package__ = ""
    sys.modules[name] = module
    exec(compile(source, str(source_path), "exec"), module.__dict__)
    return module


stage = Path(sys.argv[1])
instructions = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
sys.modules["pexpect"] = types.ModuleType("pexpect")
load_exact("regression", stage / instructions["regression"])
reference = load_exact(
    "reference_fingerprints", stage / instructions["validator"])
if (reference.PLAN_SCHEMA != "candle-s1-reference-plan-v6" or
        reference.CANDIDATE_SCHEMA != "candle-s1-reference-candidate-v6"):
    raise RuntimeError("captured reference validator is not v6 compatible")
for replay in instructions["replays"]:
    candidate = json.loads(
        (stage / replay["candidate"]).read_text(encoding="utf-8"))
    plan = json.loads((stage / replay["plan"]).read_text(encoding="utf-8"))
    request = (stage / replay["request"]).read_text(encoding="utf-8")
    transcript = (stage / replay["transcript"]).read_text(encoding="utf-8")
    expected_request = reference._request_source(
        replay["target"], plan["input"]["serializer"]["path"],
        candidate["session_nonce"])
    if request != expected_request:
        raise RuntimeError("request does not regenerate from target and nonce")
    reference.validate_candidate(candidate, plan, request, transcript)
print(f"reference candidate replay PASS: {len(instructions['replays'])}")
'''

# Test-only hook. Production callers cannot select it through the CLI.
_TEST_AFTER_CONTRACT_CAPTURE = None


class ValidationError(ValueError):
    """The proposed archive is incomplete, inconsistent, or unauthenticated."""


@dataclass(frozen=True)
class FileIdentity:
    bytes: int
    sha256: str

    def as_json(self) -> dict[str, object]:
        return {"bytes": self.bytes, "sha256": self.sha256}


@dataclass(frozen=True)
class Snapshot:
    source_path: Path
    archive_path: str
    identity: FileIdentity
    file_key: tuple[int, int]


@dataclass
class ValidatedRun:
    report_snapshot: Snapshot
    report: dict[str, Any]
    results: list[dict[str, Any]]
    log_snapshots: list[Snapshot]
    suite_nonce: str


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


def require_nonce(value: object, label: str) -> str:
    require(isinstance(value, str) and NONCE_RE.fullmatch(value) is not None,
            f"malformed nonce for {label}")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def compact_json_sha256(value: object) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def bytes_identity(value: bytes) -> FileIdentity:
    return FileIdentity(len(value), hashlib.sha256(value).hexdigest())


def lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(path))


def ordinary_file(path: Path, label: str) -> Path:
    path = lexical_absolute(path)
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise ValidationError(f"missing {label}: {path}") from error
    require(not path.is_symlink(), f"{label} is a symlink: {path}")
    require(stat.S_ISREG(metadata.st_mode), f"{label} is not an ordinary file: {path}")
    require(path.resolve(strict=True) == path, f"{label} path is not canonical: {path}")
    return path


def ordinary_directory(path: Path, label: str) -> Path:
    path = lexical_absolute(path)
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise ValidationError(f"missing {label}: {path}") from error
    require(not path.is_symlink(), f"{label} is a symlink: {path}")
    require(stat.S_ISDIR(metadata.st_mode), f"{label} is not an ordinary directory: {path}")
    require(path.resolve(strict=True) == path, f"{label} path is not canonical: {path}")
    return path


def safe_relative(value: str, label: str) -> str:
    require(isinstance(value, str) and value, f"empty {label}")
    path = PurePosixPath(value)
    require(not path.is_absolute() and value == path.as_posix() and
            all(part not in {"", ".", ".."} for part in path.parts),
            f"unsafe {label}: {value!r}")
    return value


def stable_file_identity(path: Path, label: str) -> FileIdentity:
    path = ordinary_file(path, label)
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as error:
        raise ValidationError(f"cannot open {label}: {path}") from error
    digest = hashlib.sha256()
    count = 0
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode), f"{label} is not ordinary: {path}")
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            digest.update(block)
            count += len(block)
        after = os.fstat(descriptor)
        named = path.stat(follow_symlinks=False)
        require(
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
             before.st_ctime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
             after.st_ctime_ns) and
            (named.st_dev, named.st_ino) == (after.st_dev, after.st_ino) and
            count == after.st_size,
            f"{label} changed while being read: {path}",
        )
    finally:
        os.close(descriptor)
    return FileIdentity(count, digest.hexdigest())


class Stager:
    """Copy each source once, then expose only the immutable staged bytes."""

    def __init__(self, root: Path):
        self.root = root
        self.records: dict[str, FileIdentity] = {}
        self.source_keys: dict[tuple[int, int], str] = {}

    def capture(self, source: Path, archive_path: str, label: str) -> Snapshot:
        source = ordinary_file(source, label)
        archive_path = safe_relative(archive_path, "archive path")
        destination = self.root / archive_path
        require(archive_path not in self.records and not os.path.lexists(destination),
                f"duplicate archive path: {archive_path}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            source_fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
        except OSError as error:
            raise ValidationError(f"cannot capture {label}: {source}") from error
        destination_fd = None
        digest = hashlib.sha256()
        count = 0
        try:
            before = os.fstat(source_fd)
            require(stat.S_ISREG(before.st_mode), f"{label} is not ordinary: {source}")
            key = (before.st_dev, before.st_ino)
            require(key not in self.source_keys,
                    f"evidence source hard-link reused by {label} and "
                    f"{self.source_keys.get(key)}")
            destination_fd = os.open(
                destination,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
            )
            while True:
                block = os.read(source_fd, 1024 * 1024)
                if not block:
                    break
                view = memoryview(block)
                while view:
                    written = os.write(destination_fd, view)
                    view = view[written:]
                digest.update(block)
                count += len(block)
            os.fsync(destination_fd)
            os.fchmod(destination_fd, 0o444)
            after = os.fstat(source_fd)
            named = source.stat(follow_symlinks=False)
            require(
                (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                 before.st_ctime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
                 after.st_ctime_ns) and
                (named.st_dev, named.st_ino) == (after.st_dev, after.st_ino) and
                count == after.st_size,
                f"{label} changed while being captured: {source}",
            )
            identity = FileIdentity(count, digest.hexdigest())
            require(stable_file_identity(destination, f"staged {label}") == identity,
                    f"staged bytes changed for {label}")
            self.source_keys[key] = label
            self.records[archive_path] = identity
            return Snapshot(source, archive_path, identity, key)
        finally:
            if destination_fd is not None:
                os.close(destination_fd)
            os.close(source_fd)

    def write(self, archive_path: str, value: bytes) -> FileIdentity:
        archive_path = safe_relative(archive_path, "generated archive path")
        destination = self.root / archive_path
        require(archive_path not in self.records and not os.path.lexists(destination),
                f"duplicate generated archive path: {archive_path}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        try:
            view = memoryview(value)
            while view:
                written = os.write(descriptor, view)
                view = view[written:]
            os.fsync(descriptor)
            os.fchmod(descriptor, 0o444)
        finally:
            os.close(descriptor)
        identity = bytes_identity(value)
        require(stable_file_identity(destination, "generated archive file") == identity,
                f"generated archive write mismatch: {archive_path}")
        self.records[archive_path] = identity
        return identity


def snapshot_bytes(stage: Path, snapshot: Snapshot) -> bytes:
    return (stage / snapshot.archive_path).read_bytes()


def parse_json_bytes(value: bytes, label: str) -> dict[str, Any]:
    try:
        decoded = value.decode("utf-8", errors="strict")
        result = json.loads(decoded, object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidationError(f"malformed JSON in {label}") from error
    require(isinstance(result, dict), f"{label} is not a JSON object")
    return result


def snapshot_json(stage: Path, snapshot: Snapshot, label: str) -> dict[str, Any]:
    return parse_json_bytes(snapshot_bytes(stage, snapshot), label)


def validate_file_record(value: object, label: str) -> dict[str, object]:
    require(isinstance(value, dict) and set(value) == {"bytes", "sha256"},
            f"malformed file record for {label}")
    require(is_int(value["bytes"]) and value["bytes"] >= 0,
            f"malformed byte count for {label}")
    require_sha256(value["sha256"], label)
    return value


def validate_file_reference(value: object, label: str) -> tuple[Path, FileIdentity]:
    require(isinstance(value, dict) and set(value) == {"path", "bytes", "sha256"},
            f"malformed file reference for {label}")
    record = validate_file_record(
        {"bytes": value["bytes"], "sha256": value["sha256"]}, label,
    )
    require(isinstance(value["path"], str), f"malformed path for {label}")
    return ordinary_file(Path(value["path"]), label), FileIdentity(
        record["bytes"], record["sha256"],
    )


def validate_root_file_reference(
    value: object, root: Path, label: str,
) -> tuple[str, Path, FileIdentity]:
    require(isinstance(value, dict) and set(value) == {"path", "bytes", "sha256"},
            f"malformed file reference for {label}")
    relative = safe_relative(value["path"], f"{label} repository path")
    record = validate_file_record(
        {"bytes": value["bytes"], "sha256": value["sha256"]}, label,
    )
    return relative, ordinary_file(root / relative, label), FileIdentity(
        record["bytes"], record["sha256"],
    )


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
    require(value["hypothesis_count"] == 0 and
            value["hypotheses_sha256"] == EMPTY_HYPOTHESES_SHA256,
            f"theorem is not closed for {label}")
    require(value["global_axiom_count"] == 3,
            f"theorem global axiom count is not three for {label}")
    return value


def validate_post_state(value: object, label: str) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == POST_STATE_KEYS,
            f"malformed post-state record for {label}")
    for field in (
        "kernel_state_sha256", "type_constants_sha256",
        "term_constants_sha256", "definitions_sha256",
        "global_axioms_sha256",
    ):
        require_sha256(value[field], f"{label}.{field}")
    for field in (
        "type_constant_count", "term_constant_count", "definition_count",
        "global_axiom_count",
    ):
        require(is_int(value[field]) and value[field] >= 0,
                f"malformed {field} for {label}")
    require(value["global_axiom_count"] == 3,
            f"post-state global axiom count is not three for {label}")
    return value


def git_environment() -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C",
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_OPTIONAL_LOCKS": "0",
    }


def git_command(root: Path, *arguments: str) -> list[str]:
    return [
        str(GIT_REQUESTED_PATH),
        "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false",
        "-c", "core.preloadIndex=false", "-c", "core.fileMode=true",
        "-C", str(root), *arguments,
    ]


def git_bytes(root: Path, *arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            git_command(root, *arguments), check=False,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=git_environment(), timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValidationError(f"Git command failed for {root}") from error
    require(completed.returncode == 0 and completed.stderr == b"",
            f"Git command failed for {root}: {arguments!r}")
    return completed.stdout


def validate_git_checkout(root: Path, expected_head: str, label: str) -> None:
    root = ordinary_directory(root, label)
    require_commit(expected_head, f"{label} head")
    top = git_bytes(root, "rev-parse", "--show-toplevel").decode().strip()
    require(Path(top) == root, f"{label} is not the exact Git top level")
    head = git_bytes(root, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    require(head == expected_head, f"{label} revision mismatch")
    status = git_bytes(
        root, "status", "--porcelain=v1", "-z", "--untracked-files=all",
    )
    require(status == b"", f"{label} worktree is not clean")


def validate_committed_snapshot(
    root: Path, relative: str, snapshot: Snapshot, stage: Path,
    expected_mode: str | None = None,
) -> None:
    relative = safe_relative(relative, "committed repository path")
    staged_line = git_bytes(
        root, "ls-files", "--stage", "--", relative,
    ).decode("utf-8", errors="strict").rstrip("\n")
    fields = staged_line.split(maxsplit=3)
    require(len(fields) == 4 and fields[2] == "0" and fields[3] == relative and
            fields[0] in {"100644", "100755"} and
            re.fullmatch(r"[0-9a-f]{40,64}", fields[1]) is not None,
            f"not one ordinary stage-0 committed file: {relative}")
    if expected_mode is not None:
        require(fields[0] == expected_mode,
                f"unexpected committed mode for {relative}")
    committed = git_bytes(root, "cat-file", "blob", f"HEAD:{relative}")
    observed = snapshot_bytes(stage, snapshot)
    require(committed == observed and bytes_identity(committed) == snapshot.identity,
            f"live bytes differ from HEAD for {relative}")


def validate_datetime(value: object, label: str) -> datetime:
    require(isinstance(value, str), f"malformed {label}")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValidationError(f"malformed {label}") from error
    require(parsed.tzinfo is not None, f"{label} lacks timezone")
    return parsed


def validate_timeout_policy(value: object) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == TIMEOUT_KEYS,
            "malformed timeout policy")
    inactivity = value["inactivity_timeout_seconds"]
    wall = value["total_wall_timeout_seconds"]
    require(is_number(inactivity) and inactivity > 0,
            "inactivity timeout must be positive")
    require(is_number(wall) and wall > 0,
            "Great100 promotion requires a positive total wall timeout")
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


def manifest_semantics(target: dict[str, Any]) -> dict[str, Any]:
    expected = target["fingerprint_request"]["expected_identities"]
    return {
        "name": target["name"],
        "expected_identity": {
            "serializer_sha256": expected["serializer_sha256"],
            "theorems": expected["theorems"],
            "post_state": expected["post_state"],
        },
    }


def approval_inventory_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    targets = []
    covered_sources: set[str] = set()
    theorem_request_count = 0
    for target in manifest["targets"]:
        request = target["fingerprint_request"]
        theorem_names = [item["name"] for item in request["theorems"]]
        theorem_request_count += len(theorem_names)
        covered_sources.update(target["load_files"])
        targets.append({
            "name": target["name"],
            "load_files": target["load_files"],
            "load_file_sha256": target["load_file_sha256"],
            "mapping_status": request["mapping_status"],
            "theorem_names": theorem_names,
        })
    return {
        "schema": "candle-great100-inventory-contract-v1",
        "target_count": len(targets),
        "covered_source_count": len(covered_sources),
        "theorem_request_count": theorem_request_count,
        "targets": targets,
    }


def validate_manifest_and_capture_closure(
    root: Path, manifest: dict[str, Any], manifest_snapshot: Snapshot,
    serializer_snapshot: Snapshot, stage: Path, stager: Stager,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    require(manifest.get("schema_version") == 1,
            "unsupported Great100 manifest schema")
    targets = manifest.get("targets")
    require(manifest.get("target_count") == 65 and isinstance(targets, list) and
            len(targets) == 65, "Great100 manifest must contain 65 targets")
    validate_committed_snapshot(
        root, "candle/top100_manifest.json", manifest_snapshot, stage, "100644",
    )
    validate_committed_snapshot(
        root, "candle/fingerprint.ml", serializer_snapshot, stage, "100644",
    )

    names: list[str] = []
    ordered_files: list[str] = []
    file_hashes: dict[str, str] = {}
    ordered_targets: list[dict[str, Any]] = []
    semantics: list[dict[str, Any]] = []
    request_count = 0
    serializer_hashes: set[str] = set()
    approval_hashes: set[str] = set()
    global_axioms: set[tuple[str, int]] = set()
    for index, target in enumerate(targets, 1):
        require(isinstance(target, dict), f"malformed manifest target {index}")
        name = target.get("name")
        require(isinstance(name, str) and name.startswith("100/"),
                f"malformed target name at {index}")
        names.append(name)
        files = target.get("load_files")
        require(isinstance(files, list) and files and
                all(isinstance(item, str) for item in files),
                f"malformed load files for {name}")
        files = [safe_relative(item, f"load file for {name}") for item in files]
        require(target.get("skip") is None, f"hidden Great100 skip for {name}")
        hashes = target.get("load_file_sha256")
        require(isinstance(hashes, dict) and set(hashes) == set(files),
                f"load-file identity mismatch for {name}")
        for relative in files:
            digest = require_sha256(hashes[relative], f"{name}:{relative}")
            if relative not in file_hashes:
                file_hashes[relative] = digest
                ordered_files.append(relative)
            else:
                require(file_hashes[relative] == digest,
                        f"inconsistent repeated source hash for {relative}")
        request = target.get("fingerprint_request")
        require(isinstance(request, dict) and request.get("mapping_status") == "audited",
                f"unaudited fingerprint mapping for {name}")
        requested = request.get("theorems")
        require(isinstance(requested, list) and requested,
                f"missing theorem request for {name}")
        theorem_names = []
        for theorem in requested:
            require(isinstance(theorem, dict) and set(theorem) in ({
                "name", "resolved_declaration", "shadowed_declarations",
            }, {
                "name", "resolved_declaration", "shadowed_declarations",
                "qualified_references",
            }), f"malformed theorem request for {name}")
            require(isinstance(theorem["name"], str) and theorem["name"],
                    f"malformed theorem name for {name}")
            for location_key in (
                "resolved_declaration", "shadowed_declarations",
                "qualified_references",
            ):
                if location_key not in theorem:
                    continue
                locations = theorem[location_key]
                if location_key == "resolved_declaration":
                    locations = [locations]
                require(isinstance(locations, list),
                        f"malformed {location_key} for {name}")
                for location in locations:
                    require(isinstance(location, dict) and
                            set(location) == {"path", "line"},
                            f"malformed {location_key} location for {name}")
                    location_path = safe_relative(
                        location["path"], f"{location_key} path for {name}",
                    )
                    require(location_path in files and
                            isinstance(location["line"], int) and
                            not isinstance(location["line"], bool) and
                            location["line"] > 0,
                            f"invalid {location_key} location for {name}")
            theorem_names.append(theorem["name"])
        request_count += len(theorem_names)
        expected = request.get("expected_identities")
        require(isinstance(expected, dict) and set(expected) == {
            "approval_sha256", "serializer_sha256", "theorems", "post_state",
        },
                f"missing independent approved identities for {name}")
        approval_hashes.add(require_sha256(
            expected["approval_sha256"], f"{name} approval",
        ))
        serializer_hashes.add(require_sha256(
            expected["serializer_sha256"], f"{name} serializer",
        ))
        expected_theorems = expected["theorems"]
        require(isinstance(expected_theorems, list) and
                len(expected_theorems) == len(theorem_names),
                f"expected theorem count mismatch for {name}")
        for theorem_index, theorem in enumerate(expected_theorems):
            record = validate_theorem_record(
                theorem, f"{name} theorem {theorem_index + 1}",
            )
            require(record["name"] == theorem_names[theorem_index],
                    f"expected theorem order mismatch for {name}")
            global_axioms.add((
                record["global_axioms_sha256"], record["global_axiom_count"],
            ))
        post_state = validate_post_state(expected["post_state"], f"{name} post-state")
        global_axioms.add((
            post_state["global_axioms_sha256"],
            post_state["global_axiom_count"],
        ))
        ordered_targets.append({
            "name": name, "load_files": files, "theorem_names": theorem_names,
        })
        semantics.append(manifest_semantics(target))

    require(len(set(names)) == 65, "duplicate Great100 target")
    require(len(ordered_files) == 66, "Great100 closure must contain 66 files")
    require(request_count == 97, "Great100 closure must contain 97 requests")
    require(len(serializer_hashes) == 1 and
            serializer_snapshot.identity.sha256 == next(iter(serializer_hashes)),
            "serializer does not match all approved identities")
    require(len(approval_hashes) == 1,
            "Great100 targets do not use one independent approval artifact")
    require(len(global_axioms) == 1 and next(iter(global_axioms))[1] == 3,
            "approved identities do not use one three-axiom set")

    file_records = []
    for index, relative in enumerate(ordered_files, 1):
        snapshot = stager.capture(
            root / relative, f"source-closure/files/{index:02d}/{relative}",
            f"Great100 source {relative}",
        )
        require(snapshot.identity.sha256 == file_hashes[relative],
                f"live source hash differs from manifest: {relative}")
        validate_committed_snapshot(root, relative, snapshot, stage)
        file_records.append({"path": relative, **snapshot.identity.as_json()})

    projection = {
        "target_count": 65,
        "source_file_count": 66,
        "fingerprint_request_count": 97,
        "ordered_targets": ordered_targets,
        "files": file_records,
    }
    return ({**projection, "sha256": compact_json_sha256(projection)}, semantics,
            next(iter(approval_hashes)))


def decode_wire_hex(value: str, label: str) -> bytes:
    require(re.fullmatch(r"(?:[0-9a-f]{2})*", value) is not None,
            f"malformed lowercase hexadecimal wire field: {label}")
    return bytes.fromhex(value)


def parse_wire_record(line: str, label: str) -> dict[str, Any]:
    fields = line.split("\t")
    require(len(fields) == 8 and fields[0] == FINGERPRINT_MARKER,
            f"malformed 8-field fingerprint wire record for {label}")
    name_bytes = decode_wire_hex(fields[1], f"{label}.name")
    try:
        name = name_bytes.decode("ascii", errors="strict")
    except UnicodeDecodeError as error:
        raise ValidationError(f"non-ASCII theorem name in {label}") from error
    require(name, f"empty theorem name in {label}")
    serialized = [
        decode_wire_hex(fields[index], f"{label}.{field}")
        for index, field in enumerate(
            ("theorem", "hypotheses", "conclusion", "global_axioms"), 2,
        )
    ]
    require(all(DECIMAL_RE.fullmatch(fields[index]) is not None
                for index in (6, 7)),
            f"non-canonical fingerprint count in {label}")
    require(serialized[1] == EMPTY_HYPOTHESES_WIRE and fields[6] == "0",
            f"theorem wire record is not closed for {label}")
    require(fields[7] == "3",
            f"theorem wire global axiom count is not three for {label}")
    return {
        "name": name,
        "theorem_sha256": hashlib.sha256(serialized[0]).hexdigest(),
        "hypotheses_sha256": hashlib.sha256(serialized[1]).hexdigest(),
        "conclusion_sha256": hashlib.sha256(serialized[2]).hexdigest(),
        "global_axioms_sha256": hashlib.sha256(serialized[3]).hexdigest(),
        "hypothesis_count": int(fields[6]),
        "global_axiom_count": int(fields[7]),
    }


def parse_state_wire_record(line: str, label: str) -> dict[str, Any]:
    fields = line.split("\t")
    require(len(fields) == 10 and fields[0] == STATE_FINGERPRINT_MARKER,
            f"malformed 10-field state fingerprint wire record for {label}")
    serialized = [
        decode_wire_hex(fields[index], f"{label}.{field}")
        for index, field in enumerate((
            "kernel_state", "type_constants", "term_constants", "definitions",
            "global_axioms",
        ), 1)
    ]
    require(all(DECIMAL_RE.fullmatch(fields[index]) is not None
                for index in (6, 7, 8, 9)),
            f"non-canonical state fingerprint count in {label}")
    result = {
        "kernel_state_sha256": hashlib.sha256(serialized[0]).hexdigest(),
        "type_constants_sha256": hashlib.sha256(serialized[1]).hexdigest(),
        "term_constants_sha256": hashlib.sha256(serialized[2]).hexdigest(),
        "definitions_sha256": hashlib.sha256(serialized[3]).hexdigest(),
        "global_axioms_sha256": hashlib.sha256(serialized[4]).hexdigest(),
        "type_constant_count": int(fields[6]),
        "term_constant_count": int(fields[7]),
        "definition_count": int(fields[8]),
        "global_axiom_count": int(fields[9]),
    }
    return validate_post_state(result, label)


def validate_runtime_state(
    value: object, label: str, root: Path, head: str, linked_sha256: str,
    executable_identity: FileIdentity, execution_contract_sha256: str,
    closure_sha256: str,
) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == RUNTIME_STATE_KEYS,
            f"malformed runtime state for {label}")
    require(value["candle_git_head"] == head and
            value["candle_git_status"] == [] and
            value["linked_record_sha256"] == linked_sha256 and
            value["execution_contract_sha256"] == execution_contract_sha256 and
            value["source_closure_sha256"] == closure_sha256,
            f"runtime state contract mismatch for {label}")
    require(value["candle_executable"] == {
        "path": str(root / "candle/build/cake"), **executable_identity.as_json(),
    }, f"runtime executable identity mismatch for {label}")
    return value


def validate_transcript(
    value: bytes, name: str, suite_nonce: str, process_nonce: str,
    linked_sha256: str, expected_theorems: list[dict[str, Any]],
    expected_post_state: dict[str, Any], expected_markers: dict[str, int],
) -> None:
    try:
        text = value.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValidationError(f"transcript for {name} is not strict UTF-8") from error
    lines = text.splitlines()
    suite_marker = f"CANDLE_GREAT100_SUITE_V1\t{suite_nonce}"
    start_marker = (
        f"CANDLE_GREAT100_PROCESS_V1\t{suite_nonce}\t{process_nonce}\tSTART"
    )
    complete_marker = (
        f"CANDLE_GREAT100_PROCESS_V1\t{suite_nonce}\t{process_nonce}\tCOMPLETE"
    )
    linked_marker = f"CANDLE_LINKED_PROVENANCE_V1\t{linked_sha256}"
    for marker, marker_label in (
        (suite_marker, "suite"), (start_marker, "process-start"),
        (complete_marker, "process-complete"), (linked_marker, "linked-record"),
        (LINKED_PASS_WITNESS, "linked PASS"),
    ):
        require(lines.count(marker) == 1,
                f"transcript for {name} lacks one exact {marker_label} marker")
    indices = {
        "suite_line": lines.index(suite_marker),
        "start_line": lines.index(start_marker),
        "linked_line": lines.index(linked_marker),
        "complete_line": lines.index(complete_marker),
    }
    require(indices == expected_markers,
            f"reported transcript marker offsets differ for {name}")
    suite = indices["suite_line"]
    start = indices["start_line"]
    linked = indices["linked_line"]
    complete = indices["complete_line"]
    require(suite < start < linked < complete,
            f"transcript marker order mismatch for {name}")
    wire_indices = [
        index for index, line in enumerate(lines)
        if line.startswith(FINGERPRINT_MARKER)
    ]
    require(len(wire_indices) == len(expected_theorems),
            f"fingerprint wire-record count mismatch for {name}")
    require(all(start < index < complete for index in wire_indices),
            f"fingerprint wire record outside process markers for {name}")
    parsed = [
        parse_wire_record(lines[index], f"{name} record {offset}")
        for offset, index in enumerate(wire_indices, 1)
    ]
    require(parsed == expected_theorems,
            f"parsed fingerprint wire records differ from report for {name}")
    state_indices = [
        index for index, line in enumerate(lines)
        if line.startswith(STATE_FINGERPRINT_MARKER)
    ]
    require(len(state_indices) == 1,
            f"state fingerprint wire-record count mismatch for {name}")
    require(linked < state_indices[0] < complete and
            all(linked < index < complete for index in wire_indices),
            f"fingerprint wire record precedes linked marker for {name}")
    parsed_state = parse_state_wire_record(
        lines[state_indices[0]], f"{name} post-state",
    )
    require(parsed_state == expected_post_state,
            f"parsed state fingerprint differs from report for {name}")
    require(not any(
        (line.startswith("CANDLE_FINGERPRINT_V") and
         not line.startswith(FINGERPRINT_MARKER)) or
        (line.startswith("CANDLE_STATE_FINGERPRINT_V") and
         not line.startswith(STATE_FINGERPRINT_MARKER))
        for line in lines
    ), f"unexpected fingerprint wire version in transcript for {name}")


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.]+", "_", name)


def execution_semantics(run: ValidatedRun) -> list[dict[str, Any]]:
    return [{
        "name": result["name"],
        "expected_identity": {
            "serializer_sha256": result["fingerprints"]["serializer"]["sha256"],
            "theorems": result["fingerprints"]["theorems"],
            "post_state": result["fingerprints"]["post_state"],
        },
    } for result in run.results]


def validate_report_and_capture_logs(
    report: dict[str, Any], report_snapshot: Snapshot, run_index: int,
    root: Path, manifest: dict[str, Any], closure: dict[str, Any],
    approval_relative: str, approval_identity: FileIdentity, linked_sha256: str,
    execution_contract: dict[str, dict[str, object]], stage: Path,
    stager: Stager,
) -> ValidatedRun:
    require(set(report) == REPORT_KEYS, "malformed schema-4 Great100 report")
    require(report["schema"] == 4 and report["suite"] == "top100",
            "only a schema-4 Great100 report is promotable")
    generated = validate_datetime(report["generated_utc"], "report generation time")
    suite_started = validate_datetime(
        report["suite_started_utc"], "suite start time",
    )
    require(generated > suite_started, "report generation does not follow suite start")
    require(report["test_count"] == 65, "Great100 report must contain 65 targets")
    require(is_int(report["jobs"]) and report["jobs"] > 0,
            "invalid Great100 worker count")
    validate_timeout_policy(report["timeout_policy"])
    for field in ("wall_seconds", "sum_test_seconds"):
        require(is_number(report[field]) and report[field] > 0,
                f"invalid report {field}")
    require(report["counts"] == {"PASS": 65, "FAIL": 0, "TIMEOUT": 0},
            "Great100 suite did not pass completely")
    require(report["candle_root"] == str(root), "report Candle root mismatch")
    require(report["candle_git_status"] == [],
            "Candle worktree was not clean during the run")
    require_commit(report["candle_git_head"], "report Candle head")
    require(report["fingerprint_contract"] == FINGERPRINT_CONTRACT,
            "unexpected fingerprint contract")
    require(isinstance(report["s1_evidence"], dict) and
            set(report["s1_evidence"]) == S1_KEYS and
            report["s1_evidence"] == S1_CLOSED,
            "Great100 S1 evidence is not closed")
    require(report["execution_contract"] == execution_contract,
            "report execution-contract bytes differ from committed bytes")
    require(report["source_closure"] == closure,
            "report source closure differs from live canonical closure")
    require(report["independent_approval"] == {
        "path": approval_relative, **approval_identity.as_json(),
    }, "report independent-approval binding mismatch")

    evidence = report["run_evidence"]
    require(isinstance(evidence, dict) and set(evidence) == RUN_EVIDENCE_KEYS,
            "malformed schema-4 run evidence")
    suite_nonce = require_nonce(evidence["suite_nonce"], "suite")
    require(evidence["marker_contract"] == MARKER_CONTRACT,
            "unexpected process-marker contract")
    require(evidence["linked_record_sha256"] == linked_sha256 and
            evidence["source_closure_sha256"] == closure["sha256"] and
            evidence["independent_approval_sha256"] == approval_identity.sha256,
            "run evidence does not bind linked/source/approval bytes")

    require(isinstance(report["log_directory"], str), "malformed log directory")
    log_directory = ordinary_directory(
        Path(report["log_directory"]), f"run {run_index} log directory",
    )
    executable_path, reported_executable = validate_file_reference(
        report["candle_executable"], "Candle executable",
    )
    executable = ordinary_file(executable_path, "Candle executable")
    require(executable == root / "candle/build/cake",
            "Candle executable is outside canonical build path")
    executable_identity = stable_file_identity(executable, "Candle executable")
    require(executable_identity == reported_executable,
            "live Candle executable differs from report")
    linked_relative, linked_path, linked_identity = validate_root_file_reference(
        report["linked_record"], root, "report linked record",
    )
    require(linked_relative == "candle/build/cakeml-build-provenance.json" and
            linked_path == root / linked_relative and
            linked_identity.sha256 == linked_sha256,
            "report linked-record file binding mismatch")
    execution_contract_sha256 = compact_json_sha256(execution_contract)
    results = report["results"]
    require(isinstance(results, list) and len(results) == 65,
            "malformed Great100 result table")
    targets = manifest["targets"]
    require([row.get("name") for row in results] ==
            [target["name"] for target in targets],
            "Great100 results are not in manifest order")

    process_nonces: list[str] = []
    logs: list[Snapshot] = []
    for result_index, (result, target) in enumerate(zip(results, targets), 1):
        name = target["name"]
        require(isinstance(result, dict) and set(result) == RESULT_KEYS,
                f"malformed result for {name}")
        require(result["status"] == "PASS" and result["timeout_kind"] is None and
                result["error_message"] == "", f"non-passing result for {name}")
        require(result["files"] == target["load_files"],
                f"load-file order mismatch for {name}")
        for field in (
            "boot_elapsed_seconds", "hol_elapsed_seconds", "test_elapsed_seconds",
            "fingerprint_elapsed_seconds", "total_elapsed_seconds",
        ):
            require(is_number(result[field]) and result[field] >= 0,
                    f"invalid {field} for {name}")
        require(result["total_elapsed_seconds"] > 0 and math.isclose(
            result["total_elapsed_seconds"],
            sum(result[field] for field in (
                "boot_elapsed_seconds", "hol_elapsed_seconds",
                "test_elapsed_seconds", "fingerprint_elapsed_seconds",
            )), rel_tol=1e-12, abs_tol=1e-9,
        ), f"elapsed phase accounting mismatch for {name}")
        for field in ("peak_process_rss_kib", "peak_tree_rss_kib"):
            require(is_int(result[field]) and result[field] > 0,
                    f"missing {field} for {name}")
        require(result["peak_tree_rss_kib"] >= result["peak_process_rss_kib"],
                f"tree RSS smaller than process RSS for {name}")

        fingerprints = result["fingerprints"]
        require(isinstance(fingerprints, dict) and
                set(fingerprints) == FINGERPRINT_KEYS,
                f"malformed fingerprints for {name}")
        require(fingerprints["status"] == "matched" and
                fingerprints["mapping_status"] == "audited" and
                fingerprints["expected_identities_present"] is True,
                f"unapproved fingerprint result for {name}")
        expected = target["fingerprint_request"]["expected_identities"]
        require(fingerprints["serializer"] == {
            "path": "candle/fingerprint.ml",
            "sha256": expected["serializer_sha256"],
        } and fingerprints["theorems"] == expected["theorems"] and
                fingerprints["post_state"] == expected["post_state"] and
                fingerprints["approval_sha256"] == expected["approval_sha256"] ==
                approval_identity.sha256,
                f"semantic fingerprint mismatch for {name}")
        for theorem_index, theorem in enumerate(fingerprints["theorems"], 1):
            validate_theorem_record(theorem, f"{name} theorem {theorem_index}")

        process = result["process_evidence"]
        require(isinstance(process, dict) and
                set(process) == PROCESS_EVIDENCE_KEYS,
                f"malformed process evidence for {name}")
        require(process["suite_nonce"] == suite_nonce,
                f"process for {name} uses wrong suite nonce")
        process_nonce = require_nonce(process["process_nonce"], f"process {name}")
        process_nonces.append(process_nonce)
        require(is_int(process["pid"]) and process["pid"] > 0 and
                process["exit_code"] == 0,
                f"invalid process identity or exit status for {name}")
        started = validate_datetime(process["started_utc"], f"{name} process start")
        completed = validate_datetime(
            process["completed_utc"], f"{name} process completion",
        )
        require(suite_started <= started < completed <= generated,
                f"process interval is outside suite/report bounds for {name}")
        require(process["linked_record_sha256"] == linked_sha256,
                f"process for {name} does not bind the linked record")
        markers = process["markers"]
        require(isinstance(markers, dict) and set(markers) == MARKER_KEYS and
                all(is_int(value) and value >= 0 for value in markers.values()),
                f"malformed marker offsets for {name}")
        transcript_path, transcript_identity = validate_file_reference(
            process["transcript"], f"transcript for {name}",
        )
        require(isinstance(result["log_path"], str), f"malformed log path for {name}")
        log_path = ordinary_file(Path(result["log_path"]), f"log for {name}")
        require(transcript_path == log_path and
                process["transcript"]["path"] == result["log_path"],
                f"process transcript path differs from log_path for {name}")
        require(log_path.parent == log_directory,
                f"log for {name} is outside reported log directory")
        pre_runtime = validate_runtime_state(
            process["pre_runtime_state"], f"{name} pre-runtime", root,
            report["candle_git_head"], linked_sha256, executable_identity,
            execution_contract_sha256, closure["sha256"],
        )
        post_runtime = validate_runtime_state(
            process["post_runtime_state"], f"{name} post-runtime", root,
            report["candle_git_head"], linked_sha256, executable_identity,
            execution_contract_sha256, closure["sha256"],
        )
        require(pre_runtime == post_runtime,
                f"runtime contract changed during process for {name}")
        resource = process["resource_sampling"]
        require(isinstance(resource, dict) and
                set(resource) == RESOURCE_SAMPLING_KEYS and
                is_number(resource["interval_seconds"]) and
                resource["interval_seconds"] > 0 and
                is_int(resource["sample_count"]) and resource["sample_count"] > 0 and
                resource["root_observed"] is True and
                resource["sampler_completed"] is True and
                resource["peak_process_rss_kib"] == result["peak_process_rss_kib"] and
                resource["peak_tree_rss_kib"] == result["peak_tree_rss_kib"],
                f"incomplete or inconsistent resource sampling for {name}")
        log = stager.capture(
            log_path,
            f"run-{run_index}/logs/{result_index:02d}-{safe_name(name)}.log",
            f"run {run_index} transcript for {name}",
        )
        require(log.identity == transcript_identity,
                f"report-bound transcript bytes differ for {name}")
        validate_transcript(
            snapshot_bytes(stage, log), name, suite_nonce, process_nonce,
            linked_sha256, fingerprints["theorems"], fingerprints["post_state"],
            markers,
        )
        logs.append(log)

    require(len(set(process_nonces)) == 65,
            f"duplicate process nonce within run {run_index}")
    require(math.isclose(
        report["sum_test_seconds"],
        sum(result["total_elapsed_seconds"] for result in results),
        rel_tol=1e-12, abs_tol=1e-6,
    ), "aggregate test time mismatch")
    return ValidatedRun(report_snapshot, report, results, logs, suite_nonce)


def run_captured_provenance_helper(
    stage: Path, helper: Snapshot, root: Path,
) -> None:
    helper_path = stage / helper.archive_path
    try:
        completed = subprocess.run(
            [str(PYTHON_PATH), "-I", "-S", str(helper_path), "check-linked",
             "--candle-root", str(root)],
            check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C"},
            timeout=1800,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValidationError("captured provenance helper could not run") from error
    require(completed.returncode == 0 and
            completed.stdout == (LINKED_PASS_WITNESS + "\n").encode() and
            completed.stderr == b"",
            "authoritative captured linked-provenance validation failed")


def validate_linked_and_capture(
    root: Path, head: str, expected_record: FileIdentity,
    expected_executable_sha256: str, helper: Snapshot,
    stage: Path, stager: Stager,
) -> tuple[dict[str, Any], Snapshot, Snapshot]:
    run_captured_provenance_helper(stage, helper, root)
    build = ordinary_directory(root / "candle/build", "Candle build directory")
    record_snapshot = stager.capture(
        build / "cakeml-build-provenance.json",
        "linked/cakeml-build-provenance.json", "linked provenance record",
    )
    require(record_snapshot.identity == expected_record,
            "current linked record differs from per-process binding")
    record = snapshot_json(stage, record_snapshot, "linked provenance record")
    require(set(record) == LINKED_RECORD_KEYS and record["schema"] == 6 and
            record["kind"] == "candle-linked-pinned-cakeml",
            "unsupported linked provenance record")
    require(record["candle_commit"] == head,
            "linked record does not bind reported Candle head")
    require_commit(record["cakeml_commit"], "linked CakeML commit")
    require_commit(record["hol4_commit"], "linked HOL4 commit")
    require_sha256(record["manifest_sha256"], "linked direct manifest")
    require_sha256(record["version_output_sha256"], "linked version output")
    outputs = record["outputs"]
    require(isinstance(outputs, dict) and set(outputs) == LINKED_OUTPUTS,
            "linked output set mismatch")
    output_snapshots: dict[str, Snapshot] = {}
    for name in sorted(LINKED_OUTPUTS):
        expected = validate_file_record(outputs[name], f"linked output {name}")
        captured = stager.capture(
            build / name, f"linked/outputs/{name}", f"linked output {name}",
        )
        require(captured.identity.as_json() == expected,
                f"linked output bytes changed: {name}")
        output_snapshots[name] = captured
    executable = output_snapshots["cake"]
    require(executable.identity.sha256 == expected_executable_sha256,
            "reported executable differs from archived linked executable")
    direct = stager.capture(
        root / "candle/flyspeck_manifest.json",
        "linked/flyspeck_manifest.json", "linked direct manifest",
    )
    require(direct.identity.sha256 == record["manifest_sha256"],
            "linked direct-manifest bytes changed")
    patch = stager.capture(
        root / "candle/cake.S.patch", "linked/cake.S.patch",
        "linked CakeML patch",
    )
    require(patch.identity.as_json() == validate_file_record(
        record["cake_patch"], "linked CakeML patch",
    ), "linked CakeML patch bytes changed")
    for field, name in (
        ("bootstrap_record", "bootstrap-provenance.json"),
        ("bootstrap_preflight", "bootstrap-preflight.json"),
        ("bootstrap_log", "bootstrap.log"),
    ):
        require(output_snapshots[name].identity.as_json() == validate_file_record(
            record[field], field,
        ), f"linked {field} bytes changed")
    return record, record_snapshot, executable


def snapshot_utf8(stage: Path, snapshot: Snapshot, label: str) -> str:
    try:
        return snapshot_bytes(stage, snapshot).decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValidationError(f"{label} is not UTF-8") from error


def prepare_reference_replay_root(
    stage: Path, stager: Stager, validator: Snapshot,
    contracts: dict[str, Snapshot], closure: dict[str, Any],
) -> dict[str, str]:
    runtime_root = "approval/replay/runtime-root"
    inputs = {
        REFERENCE_VALIDATOR_PATH: validator,
        "candle/regression.py": contracts["candle/regression.py"],
        "candle/fingerprint.ml": contracts["candle/fingerprint.ml"],
        "candle/top100_manifest.json": contracts["candle/top100_manifest.json"],
    }
    for relative, snapshot in inputs.items():
        identity = stager.write(
            f"{runtime_root}/{relative}", snapshot_bytes(stage, snapshot),
        )
        require(identity == snapshot.identity,
                f"reference replay mirror differs for {relative}")
    for index, source in enumerate(closure["files"], 1):
        relative = source["path"]
        archived = stage / f"source-closure/files/{index:02d}/{relative}"
        value = archived.read_bytes()
        identity = stager.write(f"{runtime_root}/{relative}", value)
        require(identity.as_json() == {
            "bytes": source["bytes"], "sha256": source["sha256"],
        }, f"reference replay source mirror differs for {relative}")
    return {
        "root": runtime_root,
        "validator": f"{runtime_root}/{REFERENCE_VALIDATOR_PATH}",
        "regression": f"{runtime_root}/candle/regression.py",
    }


def validate_reference_plan_bindings(
    plan: dict[str, Any], candidate: dict[str, Any], target: dict[str, Any],
    run: dict[str, Any], policy: dict[str, Any], source_contract: Snapshot,
    validator: Snapshot, serializer_sha256: str,
) -> None:
    name = target["name"]
    require(set(plan) == {
        "schema", "status", "session_nonce", "fresh_process_contract",
        "reference", "input", "request",
    } and plan["schema"] == "candle-s1-reference-plan-v6" and
            plan["status"] == "planned_not_executed",
            f"malformed v6 reference plan for {name}")
    nonce = run["session_nonce"]
    require(plan["session_nonce"] == candidate.get("session_nonce") == nonce,
            f"reference plan/candidate nonce mismatch for {name}")

    reference = plan["reference"]
    require(isinstance(reference, dict) and set(reference) == {
        "root", "git_head", "git_status", "runtime_executable",
        "runtime_interpreter", "runtime_stublib", "runtime_library_tree",
        "runtime_stub_files", "dynamic_libraries", "ocamlc", "findlib",
        "hol_ml", "generated_boot_files", "ocaml_library_tree",
    }, f"malformed v6 reference provenance for {name}")
    require(isinstance(reference["root"], str) and
            Path(reference["root"]).is_absolute() and
            reference["git_head"] == run["reference_git_head"] ==
            policy["exact_source_reference_commit"] and
            reference["git_status"] == [],
            f"reference plan head/status mismatch for {name}")

    fresh = plan["fresh_process_contract"]
    require(isinstance(fresh, dict) and set(fresh) == {
        "required", "preloaded_checkpoint_allowed", "working_directory",
        "environment_policy", "runtime_argv", "runtime_environment",
    } and fresh["required"] is True and
            fresh["preloaded_checkpoint_allowed"] is False and
            fresh["working_directory"] == reference["root"] and
            fresh["environment_policy"] ==
            "sanitized_allowlist_no_inherited_overrides" and
            isinstance(fresh["runtime_argv"], list) and
            isinstance(fresh["runtime_environment"], dict),
            f"reference plan fresh-process contract mismatch for {name}")

    inputs = plan["input"]
    require(isinstance(inputs, dict) and set(inputs) == {
        "collector", "collector_repository", "manifest",
        "manifest_schema_version", "target", "load_files", "theorem_names",
        "mapping_status", "serializer", "source_mode", "source_contract",
    }, f"malformed v6 reference input contract for {name}")
    require(inputs["target"] == name and inputs["manifest_schema_version"] == 1 and
            inputs["mapping_status"] == "audited" and
            inputs["source_mode"] == "manifest-exact",
            f"reference plan target/mode mismatch for {name}")
    theorem_names = [
        theorem["name"] for theorem in target["fingerprint_request"]["theorems"]
    ]
    require(inputs["theorem_names"] == theorem_names,
            f"reference plan theorem order mismatch for {name}")

    collector = inputs["collector"]
    repository = inputs["collector_repository"]
    require(isinstance(collector, dict) and set(collector) == {"path", "sha256"} and
            require_sha256(collector["sha256"], f"{name} collector") ==
            validator.identity.sha256 and
            isinstance(repository, dict) and set(repository) == {
                "root", "git_head", "git_status", "collector_relative_path",
                "collector_at_head_sha256", "collector_matches_head",
            } and isinstance(repository["root"], str) and
            Path(repository["root"]).is_absolute() and
            repository["collector_relative_path"] == REFERENCE_VALIDATOR_PATH and
            require_commit(repository["git_head"], f"{name} collector head") and
            repository["git_status"] == [] and
            repository["collector_at_head_sha256"] == validator.identity.sha256 and
            repository["collector_matches_head"] is True and
            collector["path"] == str(
                Path(repository["root"]) / REFERENCE_VALIDATOR_PATH),
            f"reference plan collector binding mismatch for {name}")

    serializer = inputs["serializer"]
    require(isinstance(serializer, dict) and set(serializer) == {"path", "sha256"} and
            serializer["sha256"] == serializer_sha256 and
            isinstance(serializer["path"], str) and
            Path(serializer["path"]).is_absolute() and
            serializer["path"] == str(
                Path(repository["root"]) / "candle/fingerprint.ml"),
            f"reference plan serializer binding mismatch for {name}")
    manifest_pin = inputs["manifest"]
    require(isinstance(manifest_pin, dict) and
            set(manifest_pin) == {"path", "sha256"} and
            isinstance(manifest_pin["path"], str) and
            Path(manifest_pin["path"]).is_absolute() and
            manifest_pin["path"] == str(
                Path(repository["root"]) / "candle/top100_manifest.json") and
            require_sha256(manifest_pin["sha256"], f"{name} reference manifest"),
            f"reference plan manifest binding mismatch for {name}")

    selected_sources = inputs["load_files"]
    require(isinstance(selected_sources, list) and
            len(selected_sources) == len(target["load_files"]),
            f"reference selected-source count mismatch for {name}")
    for selected, relative in zip(selected_sources, target["load_files"]):
        require(isinstance(selected, dict) and set(selected) == {
            "relative_path", "path", "sha256", "source_role",
        } and selected["relative_path"] == relative and
                selected["path"] == str(Path(reference["root"]) / relative) and
                selected["sha256"] == target["load_file_sha256"][relative] and
                selected["source_role"] == "selected-manifest-source",
                f"reference selected-source binding mismatch for {name}:{relative}")

    source = inputs["source_contract"]
    require(isinstance(source, dict) and set(source) == {
        "path", "sha256", "historical_upstream_commit",
        "exact_source_reference_commit", "compatibility_deltas",
    } and isinstance(source["path"], str) and Path(source["path"]).is_absolute() and
            source["path"] == str(
                Path(repository["root"]) / "candle/reference_source_contracts.json") and
            source["sha256"] == source_contract.identity.sha256 and
            {key: source[key] for key in REFERENCE_POLICY_KEYS} == policy,
            f"reference source-contract binding mismatch for {name}")

    request = plan["request"]
    require(isinstance(request, dict) and set(request) == {"source", "sha256"} and
            isinstance(request["source"], str) and
            hashlib.sha256(request["source"].encode("utf-8")).hexdigest() ==
            request["sha256"], f"malformed generated reference request for {name}")


def validate_candidate_identity_projection(
    candidate: dict[str, Any], target: dict[str, Any],
    expected_identity: dict[str, Any], serializer_sha256: str,
) -> None:
    name = target["name"]
    require(candidate.get("schema") == "candle-s1-reference-candidate-v6",
            f"legacy or unsupported reference candidate for {name}")
    identities = candidate.get("candidate_identities")
    require(isinstance(identities, dict) and set(identities) == FINGERPRINT_KEYS and
            identities["status"] == "observed_uncompared" and
            identities["mapping_status"] == "audited" and
            identities["expected_identities_present"] is False and
            identities["approval_sha256"] is None and
            identities["serializer"] == {
                "path": "candle/fingerprint.ml", "sha256": serializer_sha256,
            }, f"malformed replayable candidate identities for {name}")
    theorem_names = [
        theorem["name"] for theorem in target["fingerprint_request"]["theorems"]
    ]
    require(isinstance(identities["theorems"], list) and
            [validate_theorem_record(
                theorem, f"{name} reference candidate theorem {index}",
            )["name"] for index, theorem in enumerate(
                identities["theorems"], 1,
            )] == theorem_names,
            f"reference candidate theorem order mismatch for {name}")
    validate_post_state(identities["post_state"], f"{name} reference candidate")
    derived = {
        "serializer_sha256": identities["serializer"]["sha256"],
        "theorems": identities["theorems"],
        "post_state": identities["post_state"],
    }
    require(derived == expected_identity,
            f"reference candidate identity projection differs for {name}")


def run_captured_reference_replay(
    stage: Path, validator: Snapshot, regression: Snapshot,
    replay_runtime: dict[str, str], replays: list[dict[str, Any]], stager: Stager,
) -> dict[str, Any]:
    require(len(replays) == 130, "reference replay set must contain 130 runs")
    controller_identity = stager.write(
        "approval/replay/controller.py", REFERENCE_REPLAY_CONTROLLER.encode("utf-8"),
    )
    instructions = {
        "schema": "candle-great100-reference-replay-v1",
        "validator": replay_runtime["validator"],
        "regression": replay_runtime["regression"],
        "replays": replays,
    }
    instructions_identity = stager.write(
        "approval/replay/instructions.json", canonical_json_bytes(instructions),
    )
    controller_path = stage / "approval/replay/controller.py"
    instructions_path = stage / "approval/replay/instructions.json"
    try:
        completed = subprocess.run(
            [str(PYTHON_PATH), "-I", "-S", str(controller_path), str(stage),
             str(instructions_path)],
            check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C"},
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValidationError("captured v6 reference replay could not run") from error
    expected_stdout = f"reference candidate replay PASS: {len(replays)}\n".encode()
    require(completed.returncode == 0 and completed.stdout == expected_stdout and
            completed.stderr == b"",
            "captured v6 reference candidate replay failed")
    return {
        "validator": {
            "committed_archive_path": validator.archive_path,
            "executed_archive_path": replay_runtime["validator"],
            **validator.identity.as_json(),
        },
        "regression": {
            "committed_archive_path": regression.archive_path,
            "executed_archive_path": replay_runtime["regression"],
            **regression.identity.as_json(),
        },
        "controller": {
            "archive_path": "approval/replay/controller.py",
            **controller_identity.as_json(),
        },
        "instructions": {
            "archive_path": "approval/replay/instructions.json",
            **instructions_identity.as_json(),
        },
        "candidate_count": len(replays),
        "runtime_root": replay_runtime["root"],
    }


def validate_approval_and_capture(
    approval: dict[str, Any], approval_snapshot: Snapshot,
    root: Path, manifest: dict[str, Any], expected_semantics: list[dict[str, Any]],
    serializer_sha256: str, validator: Snapshot, regression: Snapshot,
    replay_runtime: dict[str, str], stage: Path, stager: Stager,
) -> dict[str, Any]:
    require(set(approval) == APPROVAL_KEYS and
            approval["schema"] == "candle-s1-identity-approval-v1" and
            approval["artifact_kind"] ==
            "independently-reviewed-ocaml-reference-identities" and
            approval["approval_status"] == "approved" and
            approval["promotion_allowed"] is True,
            "independent OCaml approval artifact is not approved")
    inventory = approval_inventory_contract(manifest)
    require((inventory["target_count"], inventory["covered_source_count"],
             inventory["theorem_request_count"]) == (65, 66, 97) and
            approval["inventory_contract_sha256"] == compact_json_sha256(inventory),
            "independent approval inventory contract mismatch")
    require(approval["serializer_sha256"] == serializer_sha256,
            "independent approval serializer mismatch")

    policy = approval["reference_policy"]
    require(isinstance(policy, dict) and set(policy) == REFERENCE_POLICY_KEYS,
            "malformed independent approval reference policy")
    require_commit(policy["historical_upstream_commit"], "historical reference")
    exact_reference = require_commit(
        policy["exact_source_reference_commit"], "exact source reference",
    )
    deltas = policy["compatibility_deltas"]
    require(isinstance(deltas, list) and len(deltas) == 3,
            "reference policy must contain exactly three compatibility deltas")
    expected_delta_paths = {
        "100/e_is_transcendental.ml", "100/euler.ml", "100/lagrange.ml",
    }
    observed_delta_paths = set()
    for delta in deltas:
        require(isinstance(delta, dict) and set(delta) == REFERENCE_DELTA_KEYS,
                "malformed independent approval compatibility delta")
        path = safe_relative(delta["path"], "approval compatibility-delta path")
        observed_delta_paths.add(path)
        require_sha256(delta["historical_sha256"], f"historical delta {path}")
        require_sha256(delta["selected_sha256"], f"selected delta {path}")
        require(isinstance(delta["reason"], str) and delta["reason"].strip(),
                f"missing approval compatibility-delta reason for {path}")
    require(observed_delta_paths == expected_delta_paths,
            "independent approval compatibility-delta path set mismatch")

    review = approval["review"]
    require(isinstance(review, dict) and set(review) == APPROVAL_REVIEW_KEYS and
            isinstance(review["reviewer"], str) and review["reviewer"].strip() and
            review["decision"] ==
            "two-reference-runs-identical-and-source-deltas-reviewed",
            "independent approval lacks an exact review decision")
    validate_datetime(review["approved_utc"], "independent approval review time")
    require_commit(review["review_commit"], "independent approval review commit")

    targets = approval["targets"]
    require(isinstance(targets, list) and len(targets) == 65,
            "independent approval does not cover 65 targets")
    artifact_cache: dict[str, tuple[str, Snapshot]] = {}
    replays: list[dict[str, Any]] = []
    for target_index, (target, approved, semantic) in enumerate(zip(
            manifest["targets"], targets, expected_semantics), 1):
        name = target["name"]
        require(isinstance(approved, dict) and set(approved) == APPROVAL_TARGET_KEYS and
                approved["name"] == name,
                f"malformed or reordered independent approval target {name}")
        expected_identity = approved["expected_identity"]
        require(isinstance(expected_identity, dict) and
                set(expected_identity) == APPROVAL_IDENTITY_KEYS and
                semantic == {"name": name, "expected_identity": expected_identity},
                f"independent approval identity mismatch for {name}")
        expected_identity_sha256 = compact_json_sha256(expected_identity)
        runs = approved["reference_runs"]
        require(isinstance(runs, list) and len(runs) == 2,
                f"independent approval lacks two reference runs for {name}")
        nonces: set[str] = set()
        distinct_run_artifacts = {
            name: set() for name in ("candidate", "plan", "request", "transcript")
        }
        for run_index, run in enumerate(runs, 1):
            require(isinstance(run, dict) and set(run) == {
                "artifacts", "reference_git_head", "session_nonce",
                "identity_sha256",
            }, f"malformed reference run for {name}")
            require(run["reference_git_head"] == exact_reference,
                    f"reference run head mismatch for {name}")
            nonce = require_nonce(run["session_nonce"], f"reference run {name}")
            nonces.add(nonce)
            require(run["identity_sha256"] == expected_identity_sha256,
                    f"reference identity digest mismatch for {name}")
            artifacts = run["artifacts"]
            require(isinstance(artifacts, dict) and set(artifacts) == {
                "candidate", "plan", "request", "transcript", "source_contract",
            }, f"incomplete reference artifacts for {name}")
            captured_artifacts: dict[str, Snapshot] = {}
            for artifact_name, artifact in sorted(artifacts.items()):
                relative, path, expected = validate_root_file_reference(
                    artifact, root, f"{name} reference {artifact_name}",
                )
                require(path != approval_snapshot.source_path,
                        f"approval artifact reused by {name} {artifact_name}")
                if artifact_name in distinct_run_artifacts:
                    distinct_run_artifacts[artifact_name].add(
                        (relative, expected.sha256),
                    )
                if relative in artifact_cache:
                    cached_kind, cached_snapshot = artifact_cache[relative]
                    require(artifact_name == cached_kind == "source_contract" and
                            cached_snapshot.identity == expected,
                            f"reference artifact path is reused for {name} {artifact_name}")
                    captured = cached_snapshot
                    require(snapshot_json(
                        stage, captured, f"{name} reference source contract",
                    ) == {
                        "schema": "candle-s1-reference-source-contract-v1",
                        **policy,
                    }, f"reference source contract differs from approval policy for {name}")
                else:
                    captured = stager.capture(
                        path,
                        (f"approval/reference-runs/{target_index:02d}/"
                         f"run-{run_index}/{artifact_name}-{Path(relative).name}"),
                        f"{name} reference {artifact_name} run {run_index}",
                    )
                    require(captured.identity == expected,
                            f"reference artifact bytes differ for {name} {artifact_name}")
                    if artifact_name == "source_contract":
                        require(snapshot_json(
                            stage, captured, f"{name} reference source contract",
                        ) == {
                            "schema": "candle-s1-reference-source-contract-v1",
                            **policy,
                        }, f"reference source contract differs from approval policy for {name}")
                    artifact_cache[relative] = (artifact_name, captured)
                captured_artifacts[artifact_name] = captured

            candidate = snapshot_json(
                stage, captured_artifacts["candidate"],
                f"{name} reference candidate run {run_index}",
            )
            plan = snapshot_json(
                stage, captured_artifacts["plan"],
                f"{name} reference plan run {run_index}",
            )
            request_source = snapshot_utf8(
                stage, captured_artifacts["request"],
                f"{name} reference request run {run_index}",
            )
            snapshot_utf8(
                stage, captured_artifacts["transcript"],
                f"{name} reference transcript run {run_index}",
            )
            validate_reference_plan_bindings(
                plan, candidate, target, run, policy,
                captured_artifacts["source_contract"], validator,
                serializer_sha256,
            )
            require(plan["request"]["source"] == request_source,
                    f"staged reference request differs from plan for {name}")
            validate_candidate_identity_projection(
                candidate, target, expected_identity, serializer_sha256,
            )
            replays.append({
                "name": name,
                "run": run_index,
                "candidate": captured_artifacts["candidate"].archive_path,
                "plan": captured_artifacts["plan"].archive_path,
                "request": captured_artifacts["request"].archive_path,
                "transcript": captured_artifacts["transcript"].archive_path,
                "target": {
                    "load_files": target["load_files"],
                    "fingerprint_request": {
                        "theorems": target["fingerprint_request"]["theorems"],
                    },
                },
            })
        require(len(nonces) == 2,
                f"reference runs do not use distinct session nonces for {name}")
        require(all(len(values) == 2 for values in distinct_run_artifacts.values()),
                f"reference run artifacts are not distinct for {name}")
    return run_captured_reference_replay(
        stage, validator, regression, replay_runtime, replays, stager,
    )


def preflight_finalizer() -> dict[str, Any]:
    program = ordinary_file(PROGRAM_PATH, "executing finalizer")
    project = ordinary_directory(program.parent.parent, "finalizer project root")
    head = git_bytes(project, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    validate_git_checkout(project, head, "finalizer project")
    program_identity = stable_file_identity(program, "executing finalizer")
    relative = program.relative_to(project).as_posix()
    committed = git_bytes(project, "cat-file", "blob", f"HEAD:{relative}")
    require(bytes_identity(committed) == program_identity,
            "executing finalizer is not exact committed project bytes")
    python = ordinary_file(PYTHON_PATH, "Python executable")
    git = ordinary_file(GIT_REQUESTED_PATH.resolve(strict=True), "Git executable")
    return {
        "project_root": project,
        "project_head": head,
        "program_path": program,
        "program_relative": relative,
        "program_identity": program_identity,
        "python_path": python,
        "python_identity": stable_file_identity(python, "Python executable"),
        "git_path": git,
        "git_identity": stable_file_identity(git, "Git executable"),
    }


def validate_authorization(
    receipt: dict[str, Any], receipt_digest: str,
    receipt_snapshot: Snapshot, runs: tuple[ValidatedRun, ValidatedRun],
    linked_sha256: str, closure_sha256: str, semantics_sha256: str,
    approval_identity: FileIdentity, finalizer: dict[str, Any],
) -> None:
    require(receipt_snapshot.identity.sha256 == receipt_digest,
            "external authorization receipt digest mismatch")
    require(set(receipt) == AUTHORIZATION_KEYS and receipt["schema"] == 1 and
            receipt["kind"] == "candle-great100-finalization-authorization",
            "malformed external authorization receipt")
    validate_datetime(receipt["issued_utc"], "authorization issue time")
    require(isinstance(receipt["authority"], str) and receipt["authority"].strip(),
            "authorization receipt lacks authority")
    require(receipt["reports"] == [
        run.report_snapshot.identity.as_json() for run in runs
    ], "authorization receipt does not bind exact report bytes")
    require(receipt["suite_nonces"] == [run.suite_nonce for run in runs],
            "authorization receipt does not bind suite nonces")
    require(receipt["linked_record_sha256"] == linked_sha256 and
            receipt["source_closure_sha256"] == closure_sha256 and
            receipt["semantic_projection_sha256"] == semantics_sha256 and
            receipt["independent_approval"] == approval_identity.as_json(),
            "authorization receipt does not bind accepted evidence")
    require(receipt["project"] == {
        "git_head": finalizer["project_head"],
        "finalizer": {
            "path": finalizer["program_relative"],
            **finalizer["program_identity"].as_json(),
        },
    }, "authorization receipt does not bind finalizer project/bytes")
    require(receipt["tools"] == {
        "python": {
            "path": str(finalizer["python_path"]),
            **finalizer["python_identity"].as_json(),
        },
        "git": {
            "path": str(finalizer["git_path"]),
            **finalizer["git_identity"].as_json(),
        },
    }, "authorization receipt does not bind exact finalizer tools")


def archive(
    report_paths: Iterable[Path], destination: Path,
    external_receipt: Path, external_receipt_sha256: str,
) -> None:
    paths = tuple(lexical_absolute(Path(path)) for path in report_paths)
    require(len(paths) == 2, "exactly two Great100 reports are required")
    require(paths[0] != paths[1], "the two Great100 reports must be distinct")
    require_sha256(external_receipt_sha256, "external authorization receipt")
    destination = lexical_absolute(Path(destination))
    require(not os.path.lexists(destination),
            f"archive destination already exists: {destination}")
    parent = ordinary_directory(destination.parent, "archive parent")
    finalizer = preflight_finalizer()
    require(not destination.is_relative_to(finalizer["project_root"]),
            "archive destination must be outside the finalizer project checkout")

    stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.tmp-", dir=parent))
    stager = Stager(stage)
    try:
        program_snapshot = stager.capture(
            finalizer["program_path"], "finalizer/finalize-top100-report.py",
            "executing finalizer",
        )
        python_snapshot = stager.capture(
            finalizer["python_path"], "finalizer/tools/python",
            "Python executable",
        )
        git_snapshot = stager.capture(
            finalizer["git_path"], "finalizer/tools/git", "Git executable",
        )
        require(program_snapshot.identity == finalizer["program_identity"] and
                python_snapshot.identity == finalizer["python_identity"] and
                git_snapshot.identity == finalizer["git_identity"],
                "finalizer or tool bytes changed after preflight")
        receipt_snapshot = stager.capture(
            lexical_absolute(Path(external_receipt)),
            "authorization/external-receipt.json", "external authorization receipt",
        )
        require(receipt_snapshot.identity.sha256 == external_receipt_sha256,
                "external authorization receipt digest mismatch")
        receipt = snapshot_json(stage, receipt_snapshot, "external authorization receipt")

        report_snapshots = tuple(
            stager.capture(
                path, f"run-{index}/report.json", f"Great100 report {index}",
            )
            for index, path in enumerate(paths, 1)
        )
        require(report_snapshots[0].file_key != report_snapshots[1].file_key,
                "the two reports are hard-link aliases")
        reports = tuple(
            snapshot_json(stage, snapshot, f"Great100 report {index}")
            for index, snapshot in enumerate(report_snapshots, 1)
        )
        for report in reports:
            require(report.get("schema") == 4,
                    "schema-3 and other legacy Great100 reports are non-promotable")
        roots = []
        for index, report in enumerate(reports, 1):
            require(isinstance(report.get("candle_root"), str),
                    f"malformed Candle root in report {index}")
            roots.append(ordinary_directory(
                Path(report["candle_root"]), f"report {index} Candle root",
            ))
        require(roots[0] == roots[1], "reports use different Candle roots")
        root = roots[0]
        require(not destination.is_relative_to(root),
                "archive destination must be outside the Candle checkout")
        heads = [require_commit(report.get("candle_git_head"), "Candle head")
                 for report in reports]
        require(heads[0] == heads[1], "reports use different Candle heads")
        validate_git_checkout(root, heads[0], "Candle checkout")

        contract_snapshots: dict[str, Snapshot] = {}
        for relative, mode in EXECUTION_CONTRACT_PATHS.items():
            snapshot = stager.capture(
                root / relative, f"execution-contract/{relative}",
                f"execution contract {relative}",
            )
            validate_committed_snapshot(root, relative, snapshot, stage, mode)
            contract_snapshots[relative] = snapshot
        reference_validator = stager.capture(
            root / REFERENCE_VALIDATOR_PATH,
            f"execution-contract/{REFERENCE_VALIDATOR_PATH}",
            "reference fingerprint validator",
        )
        validate_committed_snapshot(
            root, REFERENCE_VALIDATOR_PATH, reference_validator, stage, "100644",
        )
        if _TEST_AFTER_CONTRACT_CAPTURE is not None:
            _TEST_AFTER_CONTRACT_CAPTURE()
        execution_contract = {
            relative: snapshot.identity.as_json()
            for relative, snapshot in sorted(contract_snapshots.items())
        }
        manifest = snapshot_json(
            stage, contract_snapshots["candle/top100_manifest.json"],
            "Great100 manifest",
        )
        closure, approved_semantics, manifest_approval_sha256 = \
            validate_manifest_and_capture_closure(
            root, manifest, contract_snapshots["candle/top100_manifest.json"],
            contract_snapshots["candle/fingerprint.ml"], stage, stager,
        )
        replay_runtime = prepare_reference_replay_root(
            stage, stager, reference_validator, contract_snapshots, closure,
        )

        approval_references = [report.get("independent_approval") for report in reports]
        require(approval_references[0] == approval_references[1] and
                isinstance(approval_references[0], dict),
                "reports use different independent approval artifacts")
        approval_relative, approval_path, approval_expected = \
            validate_root_file_reference(
            approval_references[0], root, "independent approval artifact",
        )
        approval_snapshot = stager.capture(
            approval_path, "approval/approval.json", "independent approval artifact",
        )
        require(approval_snapshot.identity == approval_expected,
                "independent approval bytes differ from reports")
        validate_committed_snapshot(
            root, approval_relative, approval_snapshot, stage, "100644",
        )
        require(approval_snapshot.identity.sha256 == manifest_approval_sha256,
                "manifest identities do not bind the independent approval artifact")
        approval = snapshot_json(stage, approval_snapshot, "independent approval artifact")
        require(manifest.get("identity_approval") == {
            "path": approval_relative,
            "sha256": approval_snapshot.identity.sha256,
            "schema": "candle-s1-identity-approval-v1",
            "approval_status": "approved",
            "promotion_allowed": True,
        }, "manifest identity-approval metadata mismatch")
        approval_replay = validate_approval_and_capture(
            approval, approval_snapshot, root, manifest, approved_semantics,
            contract_snapshots["candle/fingerprint.ml"].identity.sha256,
            reference_validator, contract_snapshots["candle/regression.py"],
            replay_runtime, stage, stager,
        )

        linked_hashes = []
        for report in reports:
            evidence = report.get("run_evidence")
            require(isinstance(evidence, dict), "missing schema-4 run evidence")
            linked_hashes.append(require_sha256(
                evidence.get("linked_record_sha256"), "per-run linked record",
            ))
        require(linked_hashes[0] == linked_hashes[1],
                "reports bind different linked records")

        runs = tuple(
            validate_report_and_capture_logs(
                report, report_snapshot, run_index, root, manifest, closure,
                approval_relative, approval_snapshot.identity, linked_hashes[0],
                execution_contract, stage, stager,
            )
            for run_index, (report, report_snapshot) in enumerate(
                zip(reports, report_snapshots), 1,
            )
        )
        require(runs[0].suite_nonce != runs[1].suite_nonce,
                "the two reports do not identify distinct suite runs")
        all_process_nonces = [
            result["process_evidence"]["process_nonce"]
            for run in runs for result in run.results
        ]
        require(len(set(all_process_nonces)) == 130,
                "process nonces are reused across Great100 runs")
        require(reports[0]["generated_utc"] != reports[1]["generated_utc"],
                "the two reports use the same generation time")
        for field in (
            "candle_root", "candle_git_head", "candle_executable",
            "linked_record", "jobs", "timeout_policy",
            "fingerprint_contract", "execution_contract", "source_closure",
            "independent_approval",
        ):
            require(reports[0][field] == reports[1][field],
                    f"reports disagree on {field}")
        semantics = execution_semantics(runs[0])
        require(semantics == execution_semantics(runs[1]) == approved_semantics,
                "two-run or independent semantic projections differ")
        semantics_sha256 = compact_json_sha256(semantics)

        linked_record, linked_snapshot, executable_snapshot = \
            validate_linked_and_capture(
                root, heads[0], FileIdentity(
                    reports[0]["linked_record"]["bytes"], linked_hashes[0],
                ),
                reports[0]["candle_executable"]["sha256"],
                contract_snapshots["candle/cakeml_artifact_provenance.py"],
                stage, stager,
            )
        require(reports[0]["candle_executable"]["path"] == str(
            root / "candle/build/cake"), "reported executable path mismatch")

        validate_authorization(
            receipt, external_receipt_sha256, receipt_snapshot,
            (runs[0], runs[1]), linked_hashes[0], closure["sha256"],
            semantics_sha256, approval_snapshot.identity, finalizer,
        )
        semantic_identity = stager.write(
            "semantic-projection.json", canonical_json_bytes(semantics),
        )
        closure_identity = stager.write(
            "source-closure.json", canonical_json_bytes(closure),
        )

        run_inventory = []
        for run_index, run in enumerate(runs, 1):
            run_inventory.append({
                "run": run_index,
                "suite_nonce": run.suite_nonce,
                "source_report_path": str(run.report_snapshot.source_path),
                "archive_report_path": run.report_snapshot.archive_path,
                "report": run.report_snapshot.identity.as_json(),
                "logs": [{
                    "name": result["name"],
                    "process_nonce": result["process_evidence"]["process_nonce"],
                    "source_path": str(snapshot.source_path),
                    "archive_path": snapshot.archive_path,
                    **snapshot.identity.as_json(),
                } for result, snapshot in zip(run.results, run.log_snapshots)],
            })
        retained = {
            relative: identity.as_json()
            for relative, identity in sorted(stager.records.items())
        }
        metadata = {
            "schema": 2,
            "kind": "candle-great100-two-schema4-run-archive",
            "claim": "Great100 S1 evidence only; not S2 or S3 evidence",
            "authorization": {
                "archive_path": receipt_snapshot.archive_path,
                "externally_supplied_sha256": external_receipt_sha256,
                **receipt_snapshot.identity.as_json(),
            },
            "finalizer": {
                "project_git_head": finalizer["project_head"],
                "archive_path": program_snapshot.archive_path,
                **program_snapshot.identity.as_json(),
                "tools": {
                    "python": {"archive_path": python_snapshot.archive_path,
                               **python_snapshot.identity.as_json()},
                    "git": {"archive_path": git_snapshot.archive_path,
                            **git_snapshot.identity.as_json()},
                },
            },
            "candle": {
                "git_head": heads[0],
                "linked_record": {
                    "schema": linked_record["schema"],
                    "archive_path": linked_snapshot.archive_path,
                    **linked_snapshot.identity.as_json(),
                },
                "executable": {
                    "source_path": str(executable_snapshot.source_path),
                    "archive_path": executable_snapshot.archive_path,
                    **executable_snapshot.identity.as_json(),
                },
            },
            "source_closure": {
                "archive_path": "source-closure.json",
                "closure_sha256": closure["sha256"],
                **closure_identity.as_json(),
            },
            "independent_approval": {
                "archive_path": approval_snapshot.archive_path,
                **approval_snapshot.identity.as_json(),
            },
            "approval_replay": approval_replay,
            "comparison": {
                "runs": 2, "target_count": 65, "source_file_count": 66,
                "fingerprint_request_count": 97,
                "projection": "ordered {name,expected_identity}",
                "identical_and_independently_approved": True,
                "archive_path": "semantic-projection.json",
                "semantic_projection_sha256": semantics_sha256,
                **semantic_identity.as_json(),
            },
            "runs": run_inventory,
            "retained_files": retained,
            "trust_boundary": [
                "The externally supplied receipt digest and named authority are "
                "trusted authorization inputs.",
                "Kernel/filesystem/process semantics and pre-exec dynamic-loader "
                "behavior remain trusted.",
                "The semantics of the exact archived Python, Git, OCaml, HOL Light, "
                "CakeML, and host-runtime artifacts are not proved by this archive.",
            ],
        }
        bundle_identity = stager.write("bundle.json", canonical_json_bytes(metadata))
        checksum_rows = [
            (identity.sha256, relative)
            for relative, identity in stager.records.items()
            if relative != "bundle.json"
        ]
        checksum_rows.append((bundle_identity.sha256, "bundle.json"))
        checksum_rows.sort(key=lambda item: item[1])
        checksum_value = "".join(
            f"{digest}  {relative}\n" for digest, relative in checksum_rows
        ).encode("utf-8")
        # SHA256SUMS is intentionally not self-listed.
        stager.write("SHA256SUMS", checksum_value)

        validate_git_checkout(root, heads[0], "Candle checkout postflight")
        validate_git_checkout(
            finalizer["project_root"], finalizer["project_head"],
            "finalizer project postflight",
        )
        require(stable_file_identity(finalizer["program_path"], "finalizer postflight") ==
                finalizer["program_identity"] and
                stable_file_identity(finalizer["python_path"], "Python postflight") ==
                finalizer["python_identity"] and
                stable_file_identity(finalizer["git_path"], "Git postflight") ==
                finalizer["git_identity"],
                "finalizer or tool bytes changed before publication")
        require(not os.path.lexists(destination),
                f"archive destination appeared during creation: {destination}")
        os.rename(stage, destination)
        parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    except BaseException:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="archive exactly two authorized schema-4 Great100 runs",
    )
    parser.add_argument("report_one", type=Path)
    parser.add_argument("report_two", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--external-receipt", required=True, type=Path)
    parser.add_argument("--external-receipt-sha256", required=True)
    arguments = parser.parse_args()
    archive(
        (arguments.report_one, arguments.report_two), arguments.destination,
        arguments.external_receipt, arguments.external_receipt_sha256,
    )


if __name__ == "__main__":
    main()
