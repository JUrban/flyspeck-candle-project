#!/usr/bin/env python3
"""Run two resumable, review-only Great100 reference-identity sweeps.

The controller never approves a candidate.  It preserves every attempt under an
external artifact root, validates completed candidates with the exact committed
Candle collector, and rewrites only deterministic aggregate status/receipt files.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import subprocess
import sys
from typing import Any


PROGRAM_PATH = Path(__file__).resolve()
PYTHON_ARGUMENT_PATH = Path("/usr/bin/python3")
PYTHON_PATH = PYTHON_ARGUMENT_PATH.resolve(strict=True)
GIT_PATH = Path("/usr/bin/git")
COLLECTOR_RELATIVE = "candle/reference_fingerprints.py"
PROTOCOL_RELATIVE = "candle/reference_protocol.py"
MANIFEST_RELATIVE = "candle/top100_manifest.json"
SERIALIZER_RELATIVE = "candle/fingerprint.ml"
SOURCE_CONTRACT_RELATIVE = "candle/reference_source_contracts.json"
CONTROLLER_RELATIVE = "scripts/run-top100-reference-sweeps.py"
LOCK_FD_ENV = "CANDLE_REFERENCE_CONTROLLER_LOCK_FD"
EXPECTED_TARGETS = 65
EXPECTED_SOURCES = 66
EXPECTED_REQUESTS = 97
SWEEP_COUNT = 2
SHA256_RE = re.compile(r"[0-9a-f]{64}")
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
NONCE_RE = SHA256_RE
ATTEMPT_RE = re.compile(r"attempt-([0-9]{4})")
TARGET_RE = re.compile(r"target-([0-9]{3})")
ARTIFACT_NAMES = {
    "plan": "plan.json",
    "request": "request.ml",
    "transcript": "transcript.log",
    "candidate": "candidate.json",
}
ATTEMPT_FILES = {
    *ARTIFACT_NAMES.values(),
    "collect.stdout", "collect.stderr", "validate.stdout", "validate.stderr",
    "success.json", "failure.json",
}
HANDLED_SIGNALS = (signal.SIGTERM, signal.SIGHUP)
ACTIVE_PROCESS: subprocess.Popen[bytes] | None = None
PENDING_SIGNAL: int | None = None
STARTUP_ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C"}


class CollectionFailure(RuntimeError):
    """The collection contract, evidence, or environment failed closed."""


class ControllerInterrupted(BaseException):
    """A handled termination signal interrupted the controller."""

    def __init__(self, signum: int):
        super().__init__(signum)
        self.signum = signum


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CollectionFailure(message)


def is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def require_sha256(value: object, label: str) -> str:
    require(isinstance(value, str) and SHA256_RE.fullmatch(value) is not None,
            f"malformed SHA-256 for {label}")
    return value


def require_commit(value: object, label: str) -> str:
    require(isinstance(value, str) and COMMIT_RE.fullmatch(value) is not None,
            f"malformed commit for {label}")
    return value


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def compact_json_sha256(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(path))


def ordinary_directory(path: Path, label: str) -> Path:
    path = lexical_absolute(path)
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise CollectionFailure(f"missing {label}: {path}") from error
    require(stat.S_ISDIR(metadata.st_mode) and not path.is_symlink(),
            f"{label} is not an ordinary directory: {path}")
    require(path.resolve(strict=True) == path,
            f"{label} path is not canonical: {path}")
    return path


def private_directory(path: Path, label: str) -> Path:
    path = ordinary_directory(path, label)
    metadata = path.lstat()
    require(metadata.st_uid == os.geteuid(),
            f"{label} is not owned by the current effective user: {path}")
    require(stat.S_IMODE(metadata.st_mode) == 0o700,
            f"{label} mode is not exactly 0700: {path}")
    return path


def ordinary_file(path: Path, label: str, *, single_link: bool = False) -> Path:
    path = lexical_absolute(path)
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise CollectionFailure(f"missing {label}: {path}") from error
    require(stat.S_ISREG(metadata.st_mode) and not path.is_symlink(),
            f"{label} is not an ordinary file: {path}")
    require(path.resolve(strict=True) == path,
            f"{label} path is not canonical: {path}")
    require(not single_link or metadata.st_nlink == 1,
            f"{label} is not a single-link artifact: {path}")
    return path


def stable_bytes(path: Path, label: str, *, single_link: bool = False) -> bytes:
    path = ordinary_file(path, label, single_link=single_link)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        chunks = []
        size = 0
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            chunks.append(block)
            size += len(block)
        after = os.fstat(descriptor)
        named = path.stat(follow_symlinks=False)
        require(
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
             before.st_ctime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
             after.st_ctime_ns) and
            (named.st_dev, named.st_ino) == (after.st_dev, after.st_ino) and
            size == after.st_size,
            f"{label} changed while being read: {path}",
        )
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def bytes_record(value: bytes) -> dict[str, object]:
    return {"bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}


def file_record(path: Path, label: str, *, single_link: bool = False) -> dict[str, object]:
    return bytes_record(stable_bytes(path, label, single_link=single_link))


def runtime_file_record(path: Path, label: str) -> dict[str, object]:
    """Pin both the supplied runtime pathname and its exact resolved file."""
    argument_path = lexical_absolute(path)
    try:
        resolved = argument_path.resolve(strict=True)
    except (FileNotFoundError, RuntimeError, OSError) as error:
        raise CollectionFailure(f"could not resolve {label}: {argument_path}") from error
    resolved = ordinary_file(resolved, f"resolved {label}")
    return {
        "argument_path": str(argument_path), "path": str(resolved),
        **file_record(resolved, label),
    }


def parse_json_bytes(value: bytes, label: str) -> dict[str, Any]:
    try:
        decoded = value.decode("utf-8", errors="strict")
        parsed = json.loads(decoded, object_pairs_hook=reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CollectionFailure(f"malformed JSON in {label}") from error
    require(isinstance(parsed, dict), f"{label} is not a JSON object")
    return parsed


def load_json(path: Path, label: str, *, single_link: bool = False) -> dict[str, Any]:
    return parse_json_bytes(
        stable_bytes(path, label, single_link=single_link), label,
    )


def safe_relative(value: object, label: str) -> str:
    require(isinstance(value, str) and value, f"empty {label}")
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value and
            all(part not in {"", ".", ".."} for part in path.parts),
            f"unsafe {label}: {value!r}")
    return value


def exclusive_write(path: Path, value: bytes, label: str) -> None:
    require(not os.path.lexists(path), f"{label} already exists: {path}")
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
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
    require(file_record(path, label, single_link=True) == bytes_record(value),
            f"{label} write verification failed")


def atomic_write(path: Path, value: bytes, label: str) -> None:
    if os.path.lexists(path):
        ordinary_file(path, label, single_link=True)
    temporary = path.with_name(f".{path.name}.new")
    require(not os.path.lexists(temporary),
            f"unrecovered temporary {label}: {temporary}")
    exclusive_write(temporary, value, f"temporary {label}")
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def ensure_new_directory(path: Path, label: str) -> Path:
    require(not os.path.lexists(path), f"{label} already exists: {path}")
    path.mkdir(mode=0o700)
    return private_directory(path, label)


def git_environment() -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C",
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_REPLACE_OBJECTS": "1",
    }


def git_bytes(root: Path, *arguments: str) -> bytes:
    command = [
        str(GIT_PATH), "-c", "core.fsmonitor=false",
        "-c", "core.untrackedCache=false", "-c", "core.preloadIndex=false",
        "-C", str(root), *arguments,
    ]
    try:
        completed = subprocess.run(
            command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=git_environment(), timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise CollectionFailure(f"Git command failed for {root}") from error
    require(completed.returncode == 0 and completed.stderr == b"",
            f"Git command failed for {root}: {arguments!r}")
    return completed.stdout


def git_common_directory(root: Path, label: str) -> Path:
    dot_git = root / ".git"
    try:
        metadata = dot_git.lstat()
    except OSError as error:
        raise CollectionFailure(f"{label} has no readable .git metadata") from error
    if stat.S_ISDIR(metadata.st_mode) and not dot_git.is_symlink():
        git_directory = ordinary_directory(dot_git, f"{label} Git directory")
    else:
        require(stat.S_ISREG(metadata.st_mode) and not dot_git.is_symlink(),
                f"{label} has unsupported .git metadata")
        try:
            line = stable_bytes(dot_git, f"{label} .git file").decode(
                "utf-8", errors="strict",
            )
        except UnicodeDecodeError as error:
            raise CollectionFailure(f"{label} has malformed .git metadata") from error
        require(line.startswith("gitdir: ") and line.endswith("\n") and
                line.count("\n") == 1,
                f"{label} has malformed .git metadata")
        git_value = Path(line[len("gitdir: "):-1])
        if not git_value.is_absolute():
            git_value = root / git_value
        git_directory = ordinary_directory(
            git_value.resolve(strict=True), f"{label} Git directory",
        )
    common_file = git_directory / "commondir"
    if not os.path.lexists(common_file):
        return git_directory
    try:
        common_value = stable_bytes(
            common_file, f"{label} Git common-directory file",
        ).decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise CollectionFailure(
            f"{label} has malformed Git common-directory metadata",
        ) from error
    require(common_value.endswith("\n") and common_value.count("\n") == 1,
            f"{label} has malformed Git common-directory metadata")
    common_path = Path(common_value[:-1])
    if not common_path.is_absolute():
        common_path = git_directory / common_path
    return ordinary_directory(
        common_path.resolve(strict=True), f"{label} Git common directory",
    )


def validate_git_repository(root: Path, head: str, label: str) -> None:
    root = ordinary_directory(root, label)
    common_path = git_common_directory(root, label)
    grafts = common_path / "info/grafts"
    require(not os.path.lexists(grafts), f"{label} has a Git grafts file")
    top = git_bytes(root, "rev-parse", "--show-toplevel").decode().strip()
    require(Path(top) == root, f"{label} is not the exact Git top level")
    observed = git_bytes(root, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    require(observed == head, f"{label} HEAD changed")
    status = git_bytes(
        root, "status", "--porcelain=v1", "-z", "--untracked-files=all",
    )
    require(status == b"", f"{label} worktree is not clean")
    replace_refs = git_bytes(
        root, "for-each-ref", "--format=%(refname)", "refs/replace",
    )
    require(replace_refs == b"", f"{label} has Git replacement objects")
    tracked = git_bytes(root, "ls-files", "-v", "-z")
    for record in tracked.split(b"\0"):
        if record:
            require(record.startswith(b"H "),
                    f"{label} has assume-unchanged or skip-worktree index flags")


def validate_committed_file(root: Path, relative: str, expected_mode: str) -> dict[str, object]:
    relative = safe_relative(relative, "committed path")
    path = ordinary_file(root / relative, f"committed {relative}")
    fields = git_bytes(root, "ls-files", "--stage", "--", relative).decode().strip().split()
    require(len(fields) == 4 and fields[0] == expected_mode and fields[2] == "0" and
            fields[3] == relative,
            f"{relative} is not one exact stage-0 committed file")
    live = stable_bytes(path, f"committed {relative}")
    committed = git_bytes(root, "cat-file", "blob", f"HEAD:{relative}")
    require(live == committed, f"live {relative} differs from HEAD")
    return {"path": relative, **bytes_record(live)}


def validate_manifest(value: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    require(value.get("schema_version") == 1,
            "unsupported Great100 manifest schema")
    targets = value.get("targets")
    require(value.get("target_count") == EXPECTED_TARGETS and
            isinstance(targets, list) and len(targets) == EXPECTED_TARGETS,
            "Great100 manifest is not a 65-target inventory")
    names = []
    sources: set[str] = set()
    request_count = 0
    projection = []
    for index, target in enumerate(targets, 1):
        require(isinstance(target, dict), f"malformed target {index}")
        name = target.get("name")
        require(isinstance(name, str) and name.startswith("100/") and
                name not in names, f"malformed or duplicate target {index}")
        require(target.get("skip") is None, f"hidden skip for {name}")
        files = target.get("load_files")
        hashes = target.get("load_file_sha256")
        require(isinstance(files, list) and files and
                all(isinstance(path, str) for path in files) and
                isinstance(hashes, dict) and set(hashes) == set(files),
                f"malformed source inventory for {name}")
        files = [safe_relative(path, f"{name} source") for path in files]
        for path in files:
            require_sha256(hashes[path], f"{name}:{path}")
            sources.add(path)
        request = target.get("fingerprint_request")
        theorems = request.get("theorems") if isinstance(request, dict) else None
        require(isinstance(request, dict) and request.get("mapping_status") == "audited" and
                request.get("expected_identities") is None and
                isinstance(theorems, list) and theorems,
                f"target is not collection-ready and unapproved: {name}")
        theorem_names = []
        for theorem in theorems:
            require(isinstance(theorem, dict) and
                    isinstance(theorem.get("name"), str) and theorem["name"],
                    f"malformed theorem request for {name}")
            theorem_names.append(theorem["name"])
        request_count += len(theorem_names)
        names.append(name)
        projection.append({
            "index": index, "name": name, "load_files": files,
            "load_file_sha256": {path: hashes[path] for path in files},
            "theorem_names": theorem_names,
        })
    require((len(sources), request_count) == (EXPECTED_SOURCES, EXPECTED_REQUESTS),
            "Great100 manifest is not the canonical 65/66/97 inventory")
    return targets, {
        "target_count": len(targets), "source_count": len(sources),
        "request_count": request_count, "targets": projection,
    }


def validate_source_policy(
    candle_root: Path, reference_root: Path, reference_head: str,
    inventory: dict[str, Any],
) -> dict[str, Any]:
    policy = load_json(
        candle_root / SOURCE_CONTRACT_RELATIVE, "reference source contract",
    )
    require(set(policy) == {
        "schema", "historical_upstream_commit", "exact_source_reference_commit",
        "compatibility_deltas",
    } and policy["schema"] == "candle-s1-reference-source-contract-v1",
            "malformed reference source contract")
    historical = require_commit(
        policy["historical_upstream_commit"], "historical reference commit",
    )
    exact = require_commit(
        policy["exact_source_reference_commit"], "exact reference commit",
    )
    require(exact == reference_head,
            "reference HEAD differs from the exact source contract")
    parent = git_bytes(
        reference_root, "rev-parse", "--verify", "HEAD^1^{commit}",
    ).decode().strip()
    require(parent == historical,
            "exact reference is not the direct child of the historical commit")
    deltas = policy["compatibility_deltas"]
    require(isinstance(deltas, list) and len(deltas) == 3,
            "reference source contract does not contain three deltas")
    expected_paths = {
        "100/e_is_transcendental.ml", "100/euler.ml", "100/lagrange.ml",
    }
    selected_hashes = {
        path: digest
        for target in inventory["targets"]
        for path, digest in target["load_file_sha256"].items()
    }
    observed_paths = set()
    for delta in deltas:
        require(isinstance(delta, dict) and set(delta) == {
            "path", "historical_sha256", "selected_sha256", "reason",
        }, "malformed reference compatibility delta")
        path = safe_relative(delta["path"], "reference delta path")
        require(path not in observed_paths and path in expected_paths,
                "unexpected or duplicate reference delta path")
        require(require_sha256(
            delta["historical_sha256"], f"historical {path}",
        ) != require_sha256(
            delta["selected_sha256"], f"selected {path}",
        ), f"reference delta does not change bytes: {path}")
        require(delta["selected_sha256"] == selected_hashes.get(path),
                f"reference delta differs from manifest: {path}")
        require(isinstance(delta["reason"], str) and delta["reason"],
                f"reference delta lacks rationale: {path}")
        observed_paths.add(path)
    require(observed_paths == expected_paths,
            "reference source delta inventory mismatch")
    changed = git_bytes(
        reference_root, "diff", "--name-only", "-z", "--no-renames",
        f"{historical}..{exact}", "--", "100",
    )
    changed_paths = {item.decode("utf-8") for item in changed.split(b"\0") if item}
    require(changed_paths == expected_paths,
            "reference Great100 delta differs from the source contract")
    for path, expected in selected_hashes.items():
        observed = file_record(reference_root / path, f"reference source {path}")
        require(observed["sha256"] == expected,
                f"reference source differs from manifest: {path}")
    return policy


def build_contract(arguments: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    project_root = ordinary_directory(arguments.project_root, "project repository")
    candle_root = ordinary_directory(arguments.candle_root, "Candle collector repository")
    reference_root = ordinary_directory(arguments.reference_root, "reference repository")
    project_head = require_commit(arguments.project_head, "project head")
    candle_head = require_commit(arguments.candle_head, "Candle collector head")
    reference_head = require_commit(arguments.reference_head, "reference head")
    validate_git_repository(project_root, project_head, "project repository")
    validate_git_repository(candle_root, candle_head, "Candle collector repository")
    validate_git_repository(reference_root, reference_head, "reference repository")
    require(PROGRAM_PATH == project_root / CONTROLLER_RELATIVE,
            "running controller is not the committed project controller path")
    controller = validate_committed_file(project_root, CONTROLLER_RELATIVE, "100755")
    require(controller["sha256"] == require_sha256(
        arguments.controller_sha256, "pinned controller"),
        "committed controller differs from command-line pin")
    collector = validate_committed_file(candle_root, COLLECTOR_RELATIVE, "100644")
    protocol = validate_committed_file(candle_root, PROTOCOL_RELATIVE, "100644")
    manifest_record = validate_committed_file(candle_root, MANIFEST_RELATIVE, "100644")
    serializer = validate_committed_file(candle_root, SERIALIZER_RELATIVE, "100644")
    source_contract = validate_committed_file(
        candle_root, SOURCE_CONTRACT_RELATIVE, "100644",
    )
    require(collector["sha256"] == require_sha256(
        arguments.collector_sha256, "pinned collector"),
        "committed collector differs from command-line pin")
    require(protocol["sha256"] == require_sha256(
        arguments.protocol_sha256, "pinned reference protocol"),
        "committed reference protocol differs from command-line pin")
    require(manifest_record["sha256"] == require_sha256(
        arguments.manifest_sha256, "pinned manifest"),
        "committed manifest differs from command-line pin")
    manifest = load_json(candle_root / MANIFEST_RELATIVE, "Great100 manifest")
    targets, inventory = validate_manifest(manifest)
    source_policy = validate_source_policy(
        candle_root, reference_root, reference_head, inventory,
    )
    runtime_arguments = (
        ("runtime", arguments.runtime, arguments.runtime_sha256),
        ("runtime_stublib", arguments.runtime_stublib,
         arguments.runtime_stublib_sha256),
        ("ocamlc", arguments.ocamlc, arguments.ocamlc_sha256),
        ("ocamlfind", arguments.ocamlfind, arguments.ocamlfind_sha256),
    )
    runtime = {}
    for name, supplied_path, supplied_sha256 in runtime_arguments:
        identity = runtime_file_record(supplied_path, name)
        require(identity["sha256"] == require_sha256(
            supplied_sha256, f"pinned {name}"), f"{name} differs from command-line pin")
        runtime[name] = identity
    require(is_int(arguments.collection_wall_seconds) and
            arguments.collection_wall_seconds > 0 and
            is_int(arguments.target_wall_seconds) and
            arguments.target_wall_seconds >= arguments.collection_wall_seconds + 30 and
            is_int(arguments.validation_wall_seconds) and
            arguments.validation_wall_seconds > 0,
            "deadlines must be positive and target deadline needs 30 seconds grace")
    python = runtime_file_record(PYTHON_ARGUMENT_PATH, "Python executable")
    git_tool = file_record(GIT_PATH, "Git executable")
    require(python["sha256"] == require_sha256(
        arguments.python_sha256, "pinned Python"),
        "Python executable differs from command-line pin")
    require(git_tool["sha256"] == require_sha256(
        arguments.git_sha256, "pinned Git"),
        "Git executable differs from command-line pin")
    contract = {
        "schema": 1,
        "kind": "candle-great100-two-sweep-reference-collection",
        "approval_status": "candidate_collection_only_unapproved",
        "promotion_allowed": False,
        "sweep_count": SWEEP_COUNT,
        "target_count": EXPECTED_TARGETS,
        "total_target_runs": SWEEP_COUNT * EXPECTED_TARGETS,
        "source_mode": "manifest-exact",
        "project": {
            "root": str(project_root), "git_head": project_head,
            "controller": controller,
        },
        "candle": {
            "root": str(candle_root), "git_head": candle_head,
            "collector": collector, "protocol": protocol,
            "manifest": manifest_record,
            "serializer": serializer, "source_contract": source_contract,
        },
        "reference": {
            "root": str(reference_root), "git_head": reference_head,
            "source_policy": source_policy,
        },
        "runtime": runtime,
        "deadlines": {
            "collection_wall_seconds": arguments.collection_wall_seconds,
            "target_wall_seconds": arguments.target_wall_seconds,
            "validation_wall_seconds": arguments.validation_wall_seconds,
        },
        "inventory": inventory,
        "controller": {
            "path": str(PROGRAM_PATH),
            "sha256": controller["sha256"], "bytes": controller["bytes"],
            "python": python,
            "git": {"path": str(GIT_PATH), **git_tool},
        },
    }
    return contract, targets


def validate_environment(contract: dict[str, Any]) -> None:
    project = contract["project"]
    candle = contract["candle"]
    reference = contract["reference"]
    project_root = Path(project["root"])
    candle_root = Path(candle["root"])
    reference_root = Path(reference["root"])
    validate_git_repository(project_root, project["git_head"], "project repository")
    validate_git_repository(candle_root, candle["git_head"], "Candle collector repository")
    validate_git_repository(reference_root, reference["git_head"], "reference repository")
    for relative, key in (
        (COLLECTOR_RELATIVE, "collector"), (PROTOCOL_RELATIVE, "protocol"),
        (MANIFEST_RELATIVE, "manifest"),
        (SERIALIZER_RELATIVE, "serializer"),
        (SOURCE_CONTRACT_RELATIVE, "source_contract"),
    ):
        observed = file_record(candle_root / relative, f"current {relative}")
        require(observed == {
            "bytes": candle[key]["bytes"], "sha256": candle[key]["sha256"],
        }, f"pinned Candle file changed: {relative}")
    for name, expected in contract["runtime"].items():
        require(runtime_file_record(
            Path(expected["argument_path"]), f"current {name}",
        ) == expected, f"pinned runtime input changed: {name}")
    observed_controller = validate_committed_file(
        project_root, CONTROLLER_RELATIVE, "100755",
    )
    require(observed_controller == project["controller"] and
            PROGRAM_PATH == project_root / CONTROLLER_RELATIVE,
            "pinned committed controller changed")
    controller = contract["controller"]
    require(runtime_file_record(
        PYTHON_ARGUMENT_PATH, "current Python",
    ) == controller["python"], "pinned Python changed")
    for path, expected, label in (
        (PROGRAM_PATH, controller, "controller"),
        (GIT_PATH, controller["git"], "Git"),
    ):
        require(file_record(path, f"current {label}") == {
            "bytes": expected["bytes"], "sha256": expected["sha256"],
        }, f"pinned {label} changed")


def subprocess_environment(lock_fd: int) -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C",
        LOCK_FD_ENV: str(lock_fd),
    }


def signal_process_group(process: subprocess.Popen[bytes], signum: int) -> None:
    if process.poll() is None:
        try:
            os.killpg(process.pid, signum)
        except ProcessLookupError:
            pass


def terminate_and_wait(
    process: subprocess.Popen[bytes], signum: int,
) -> tuple[bytes, bytes]:
    signal_process_group(process, signum)
    try:
        return process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        signal_process_group(process, signal.SIGKILL)
        return process.communicate()


def controller_signal_handler(signum: int, _frame: object) -> None:
    global PENDING_SIGNAL
    process = ACTIVE_PROCESS
    if PENDING_SIGNAL is None:
        PENDING_SIGNAL = signum
        if process is not None:
            signal_process_group(process, signum)
        raise ControllerInterrupted(signum)
    if process is not None:
        signal_process_group(process, signal.SIGKILL)


def run_process(
    command: list[str], timeout: int, lock_fd: int,
) -> tuple[int | None, bytes, bytes, bool]:
    global ACTIVE_PROCESS
    process: subprocess.Popen[bytes] | None = None
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, HANDLED_SIGNALS)
    try:
        try:
            def restore_child_signal_mask() -> None:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)

            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=subprocess_environment(lock_fd), start_new_session=True,
                pass_fds=(lock_fd,), preexec_fn=restore_child_signal_mask,
            )
            ACTIVE_PROCESS = process
        except OSError as error:
            raise CollectionFailure(f"could not start process: {command[0]}") from error
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
    except ControllerInterrupted:
        if process is not None:
            terminate_and_wait(process, PENDING_SIGNAL or signal.SIGTERM)
        ACTIVE_PROCESS = None
        raise
    try:
        require(process is not None, "child process was not created")
        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, stdout, stderr, False
    except subprocess.TimeoutExpired:
        stdout, stderr = terminate_and_wait(process, signal.SIGKILL)
        return None, stdout, stderr, True
    except ControllerInterrupted:
        terminate_and_wait(process, PENDING_SIGNAL or signal.SIGTERM)
        raise
    except BaseException:
        terminate_and_wait(process, signal.SIGKILL)
        raise
    finally:
        ACTIVE_PROCESS = None


def artifact_relative(root: Path, path: Path) -> str:
    relative = path.relative_to(root).as_posix()
    return safe_relative(relative, "artifact path")


def recorded_artifact(root: Path, path: Path, label: str) -> dict[str, object]:
    return {
        "path": artifact_relative(root, path),
        **file_record(path, label, single_link=True),
    }


def seal_artifact(path: Path, label: str) -> None:
    """Remove write bits without following or swapping the named artifact."""
    path = ordinary_file(path, label, single_link=True)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        os.fchmod(descriptor, stat.S_IMODE(before.st_mode) & ~0o222)
        after = os.fstat(descriptor)
        named = path.stat(follow_symlinks=False)
        require(
            stat.S_ISREG(after.st_mode) and after.st_nlink == 1 and
            (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino) and
            (named.st_dev, named.st_ino) == (after.st_dev, after.st_ino),
            f"{label} changed while being sealed: {path}",
        )
    finally:
        os.close(descriptor)


def validate_recorded_artifact(
    root: Path, value: object, expected_path: Path, label: str,
) -> dict[str, object]:
    require(isinstance(value, dict) and set(value) == {"path", "bytes", "sha256"},
            f"malformed artifact record for {label}")
    require(value["path"] == artifact_relative(root, expected_path) and
            is_int(value["bytes"]) and value["bytes"] >= 0,
            f"artifact path/size mismatch for {label}")
    require_sha256(value["sha256"], label)
    observed = recorded_artifact(root, expected_path, label)
    require(observed == value, f"artifact bytes changed for {label}")
    return value


def collector_command(
    contract: dict[str, Any], target: str, attempt: Path,
) -> list[str]:
    candle = contract["candle"]
    runtime = contract["runtime"]
    return [
        str(PYTHON_ARGUMENT_PATH), "-I", "-S",
        str(Path(candle["root"]) / COLLECTOR_RELATIVE),
        "collect", "--target", target,
        "--reference-root", contract["reference"]["root"],
        "--runtime", runtime["runtime"]["argument_path"],
        "--runtime-stublib", runtime["runtime_stublib"]["argument_path"],
        "--ocamlc", runtime["ocamlc"]["argument_path"],
        "--ocamlfind", runtime["ocamlfind"]["argument_path"],
        "--plan", str(attempt / ARTIFACT_NAMES["plan"]),
        "--request", str(attempt / ARTIFACT_NAMES["request"]),
        "--source-mode", "manifest-exact",
        "--transcript", str(attempt / ARTIFACT_NAMES["transcript"]),
        "--candidate", str(attempt / ARTIFACT_NAMES["candidate"]),
        "--wall-timeout", str(contract["deadlines"]["collection_wall_seconds"]),
    ]


def validator_command(contract: dict[str, Any], attempt: Path) -> list[str]:
    collector = Path(contract["candle"]["root"]) / COLLECTOR_RELATIVE
    return [
        str(PYTHON_ARGUMENT_PATH), "-I", "-S", str(collector), "validate",
        str(attempt / ARTIFACT_NAMES["candidate"]),
        "--plan", str(attempt / ARTIFACT_NAMES["plan"]),
        "--request", str(attempt / ARTIFACT_NAMES["request"]),
        "--transcript", str(attempt / ARTIFACT_NAMES["transcript"]),
    ]


def reference_json_sha256(value: object) -> str:
    return hashlib.sha256(
        (json.dumps(value, indent=2) + "\n").encode("utf-8"),
    ).hexdigest()


def validate_artifact_semantics(
    root: Path, attempt: Path, target: dict[str, Any], contract: dict[str, Any],
) -> tuple[dict[str, dict[str, object]], str]:
    paths = {name: attempt / filename for name, filename in ARTIFACT_NAMES.items()}
    artifacts = {
        name: recorded_artifact(root, path, f"{target['name']} {name}")
        for name, path in paths.items()
    }
    plan_bytes = stable_bytes(paths["plan"], "reference plan", single_link=True)
    candidate_bytes = stable_bytes(
        paths["candidate"], "reference candidate", single_link=True,
    )
    request_bytes = stable_bytes(paths["request"], "reference request", single_link=True)
    transcript_bytes = stable_bytes(
        paths["transcript"], "reference transcript", single_link=True,
    )
    plan = parse_json_bytes(plan_bytes, "reference plan")
    candidate = parse_json_bytes(candidate_bytes, "reference candidate")
    require(plan.get("schema") == "candle-s1-reference-plan-v6" and
            plan.get("status") == "planned_not_executed" and
            plan.get("session_nonce") and
            NONCE_RE.fullmatch(plan["session_nonce"]) is not None,
            f"unsupported reference plan for {target['name']}")
    inputs = plan.get("input")
    reference = plan.get("reference")
    require(isinstance(inputs, dict) and inputs.get("target") == target["name"] and
            inputs.get("mapping_status") == "audited" and
            inputs.get("source_mode") == "manifest-exact" and
            inputs.get("theorem_names") == target["theorem_names"],
            f"reference plan target/request mismatch for {target['name']}")
    expected_loads = [{
        "relative_path": relative,
        "sha256": target["load_file_sha256"][relative],
        "source_role": "selected-manifest-source",
    } for relative in target["load_files"]]
    loads = inputs.get("load_files")
    require(isinstance(loads, list) and len(loads) == len(expected_loads) and
            all(isinstance(observed, dict) and
                {key: observed.get(key) for key in expected} == expected
                for observed, expected in zip(loads, expected_loads)),
            f"reference plan source mismatch for {target['name']}")
    candle = contract["candle"]
    collector = inputs.get("collector")
    repository = inputs.get("collector_repository")
    require(isinstance(collector, dict) and
            collector.get("sha256") == candle["collector"]["sha256"] and
            isinstance(repository, dict) and
            repository.get("root") == candle["root"] and
            repository.get("git_head") == candle["git_head"] and
            repository.get("git_status") == [] and
            repository.get("collector_relative_path") == COLLECTOR_RELATIVE and
            repository.get("collector_at_head_sha256") ==
            candle["collector"]["sha256"] and
            repository.get("collector_matches_head") is True,
            f"reference plan collector mismatch for {target['name']}")
    require(repository.get("support_relative_path") == PROTOCOL_RELATIVE and
            repository.get("support_at_head_sha256") ==
            candle["protocol"]["sha256"] and
            repository.get("support_matches_head") is True,
            f"reference plan protocol mismatch for {target['name']}")
    require(isinstance(reference, dict) and
            reference.get("root") == contract["reference"]["root"] and
            reference.get("git_head") == contract["reference"]["git_head"] and
            reference.get("git_status") == [],
            f"reference plan repository mismatch for {target['name']}")
    require(plan.get("request") == {
        "source": request_bytes.decode("utf-8", errors="strict"),
        "sha256": hashlib.sha256(request_bytes).hexdigest(),
    }, f"reference request differs from plan for {target['name']}")
    require(set(candidate) == {
        "schema", "artifact_kind", "approval_status", "promotion_allowed",
        "warning", "plan_pins", "session_nonce", "process_exit_code",
        "artifact_hashes", "candidate_identities",
    } and candidate["schema"] == "candle-s1-reference-candidate-v6" and
            candidate["artifact_kind"] == "reference_identity_candidate" and
            candidate["approval_status"] == "candidate_unapproved" and
            candidate["promotion_allowed"] is False and
            candidate["process_exit_code"] == 0 and
            candidate["session_nonce"] == plan["session_nonce"],
            f"candidate is not exact unapproved v6 for {target['name']}")
    hashes = candidate["artifact_hashes"]
    require(isinstance(hashes, dict) and hashes == {
        "plan_sha256": reference_json_sha256(plan),
        "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
        "transcript_sha256": hashlib.sha256(transcript_bytes).hexdigest(),
    }, f"candidate artifact hashes differ for {target['name']}")
    identities = candidate["candidate_identities"]
    require(isinstance(identities, dict) and
            identities.get("status") == "observed_uncompared" and
            identities.get("expected_identities_present") is False and
            identities.get("approval_sha256") is None,
            f"candidate identities are not explicitly unapproved for {target['name']}")
    return artifacts, plan["session_nonce"]


def run_validation(
    root: Path, attempt: Path, target: dict[str, Any], contract: dict[str, Any],
    lock_fd: int, *, retain_output: bool,
) -> tuple[dict[str, dict[str, object]], str]:
    artifacts, nonce = validate_artifact_semantics(root, attempt, target, contract)
    validate_environment(contract)
    command = validator_command(contract, attempt)
    return_code, stdout, stderr, timed_out = run_process(
        command, contract["deadlines"]["validation_wall_seconds"], lock_fd,
    )
    if retain_output:
        exclusive_write(attempt / "validate.stdout", stdout, "validation stdout")
        exclusive_write(attempt / "validate.stderr", stderr, "validation stderr")
    validate_environment(contract)
    expected_stdout = (
        f"candidate and linked artifacts valid but unapproved: "
        f"{attempt / ARTIFACT_NAMES['candidate']}\n"
    ).encode()
    require(not timed_out and return_code == 0 and stdout == expected_stdout and
            stderr == b"", f"collector validation failed for {target['name']}")
    return artifacts, nonce


def failure_artifacts(root: Path, attempt: Path) -> dict[str, dict[str, object]]:
    result = {}
    for name in sorted(ATTEMPT_FILES - {"success.json", "failure.json"}):
        path = attempt / name
        if os.path.lexists(path):
            seal_artifact(path, f"failed artifact {name}")
            result[name] = recorded_artifact(root, path, f"failed artifact {name}")
    return result


def write_failure(
    root: Path, attempt: Path, sweep: int, target: dict[str, Any],
    stage: str, kind: str, detail: str, return_code: int | None,
) -> None:
    receipt = {
        "schema": 1, "kind": "candle-reference-attempt-failure",
        "sweep": sweep, "target_index": target["index"],
        "target": target["name"], "stage": stage, "failure_kind": kind,
        "detail": detail, "return_code": return_code,
        "artifacts": failure_artifacts(root, attempt),
        "approval_status": "candidate_unapproved",
        "promotion_allowed": False,
    }
    exclusive_write(attempt / "failure.json", canonical_json(receipt), "failure receipt")


def collect_target(
    root: Path, attempt: Path, sweep: int, target: dict[str, Any],
    contract: dict[str, Any], lock_fd: int,
) -> tuple[dict[str, dict[str, object]], str]:
    validate_environment(contract)
    command = collector_command(contract, target["name"], attempt)
    return_code, stdout, stderr, timed_out = run_process(
        command, contract["deadlines"]["target_wall_seconds"], lock_fd,
    )
    exclusive_write(attempt / "collect.stdout", stdout, "collection stdout")
    exclusive_write(attempt / "collect.stderr", stderr, "collection stderr")
    try:
        validate_environment(contract)
        if timed_out:
            raise CollectionFailure(f"target wall deadline expired for {target['name']}")
        require(return_code == 0, f"collector exited {return_code} for {target['name']}")
        expected_stdout = (
            f"unapproved reference candidate: "
            f"{attempt / ARTIFACT_NAMES['candidate']}\n"
        ).encode()
        require(stdout == expected_stdout and stderr == b"",
                f"unexpected collector transcript for {target['name']}")
        artifacts, nonce = run_validation(
            root, attempt, target, contract, lock_fd, retain_output=True,
        )
    except CollectionFailure as error:
        write_failure(
            root, attempt, sweep, target,
            "collect" if return_code != 0 or timed_out else "validate",
            "timeout" if timed_out else "failure", str(error), return_code,
        )
        raise
    success = {
        "schema": 1, "kind": "candle-reference-attempt-success",
        "sweep": sweep, "target_index": target["index"],
        "target": target["name"], "session_nonce": nonce,
        "artifacts": artifacts,
        "collector_stdout": recorded_artifact(
            root, attempt / "collect.stdout", "collection stdout"),
        "collector_stderr": recorded_artifact(
            root, attempt / "collect.stderr", "collection stderr"),
        "validator_stdout": recorded_artifact(
            root, attempt / "validate.stdout", "validation stdout"),
        "validator_stderr": recorded_artifact(
            root, attempt / "validate.stderr", "validation stderr"),
        "deadlines": contract["deadlines"],
        "approval_status": "candidate_unapproved",
        "promotion_allowed": False,
    }
    for filename in ATTEMPT_FILES - {"success.json", "failure.json"}:
        path = attempt / filename
        if os.path.lexists(path):
            seal_artifact(path, f"completed artifact {filename}")
    exclusive_write(attempt / "success.json", canonical_json(success), "success receipt")
    return artifacts, nonce


def target_directory(root: Path, sweep: int, index: int) -> Path:
    return root / f"sweep-{sweep}" / f"target-{index:03d}"


def validate_attempt_entries(attempt: Path) -> None:
    private_directory(attempt, "attempt directory")
    for entry in attempt.iterdir():
        require(entry.name in ATTEMPT_FILES,
                f"unexpected entry in attempt directory: {entry}")
        ordinary_file(entry, f"attempt entry {entry.name}", single_link=True)


def validate_success_receipt(
    root: Path, attempt: Path, sweep: int, target: dict[str, Any],
    contract: dict[str, Any], validation_cache: set[str], lock_fd: int,
) -> tuple[dict[str, Any], str]:
    path = attempt / "success.json"
    value = load_json(path, "success receipt", single_link=True)
    require(set(value) == {
        "schema", "kind", "sweep", "target_index", "target", "session_nonce",
        "artifacts", "collector_stdout", "collector_stderr",
        "validator_stdout", "validator_stderr", "deadlines",
        "approval_status", "promotion_allowed",
    } and value["schema"] == 1 and
            value["kind"] == "candle-reference-attempt-success" and
            value["sweep"] == sweep and value["target_index"] == target["index"] and
            value["target"] == target["name"] and
            value["deadlines"] == contract["deadlines"] and
            value["approval_status"] == "candidate_unapproved" and
            value["promotion_allowed"] is False,
            f"malformed success receipt for {target['name']}")
    artifacts = value["artifacts"]
    require(isinstance(artifacts, dict) and set(artifacts) == set(ARTIFACT_NAMES),
            f"malformed success artifacts for {target['name']}")
    for name, filename in ARTIFACT_NAMES.items():
        validate_recorded_artifact(
            root, artifacts[name], attempt / filename, f"{target['name']} {name}",
        )
    for field, filename in (
        ("collector_stdout", "collect.stdout"),
        ("collector_stderr", "collect.stderr"),
        ("validator_stdout", "validate.stdout"),
        ("validator_stderr", "validate.stderr"),
    ):
        validate_recorded_artifact(
            root, value[field], attempt / filename, f"{target['name']} {field}",
        )
    relative = artifact_relative(root, path)
    if relative not in validation_cache:
        observed, nonce = run_validation(
            root, attempt, target, contract, lock_fd, retain_output=False,
        )
        require(observed == artifacts and nonce == value["session_nonce"],
                f"resumed candidate differs for {target['name']}")
        validation_cache.add(relative)
    require(NONCE_RE.fullmatch(value["session_nonce"]) is not None,
            f"malformed success nonce for {target['name']}")
    return value, relative


def validate_failure_receipt(
    root: Path, attempt: Path, sweep: int, target: dict[str, Any],
) -> dict[str, Any]:
    value = load_json(attempt / "failure.json", "failure receipt", single_link=True)
    require(set(value) == {
        "schema", "kind", "sweep", "target_index", "target", "stage",
        "failure_kind", "detail", "return_code", "artifacts",
        "approval_status", "promotion_allowed",
    } and value["schema"] == 1 and
            value["kind"] == "candle-reference-attempt-failure" and
            value["sweep"] == sweep and
            value["target_index"] == target["index"] and
            value["target"] == target["name"] and
            value["stage"] in {"collect", "validate"} and
            value["failure_kind"] in {"failure", "timeout"} and
            isinstance(value["detail"], str) and value["detail"] and
            (value["return_code"] is None or is_int(value["return_code"])) and
            value["approval_status"] == "candidate_unapproved" and
            value["promotion_allowed"] is False and
            isinstance(value["artifacts"], dict),
            f"malformed failure receipt for {target['name']}")
    actual = {
        path.name for path in attempt.iterdir()
        if path.name not in {"success.json", "failure.json"}
    }
    require(set(value["artifacts"]) == actual,
            f"failure receipt omits artifacts for {target['name']}")
    for filename, record in value["artifacts"].items():
        require(filename in ATTEMPT_FILES - {"success.json", "failure.json"},
                f"unknown failed artifact for {target['name']}")
        validate_recorded_artifact(
            root, record, attempt / filename, f"failed {target['name']} {filename}",
        )
    return value


def scan_target(
    root: Path, sweep: int, target: dict[str, Any], contract: dict[str, Any],
    validation_cache: set[str], lock_fd: int,
) -> dict[str, Any]:
    directory = target_directory(root, sweep, target["index"])
    if not os.path.lexists(directory):
        return {"attempts": [], "success": None, "failures": []}
    private_directory(directory, f"target directory {target['name']}")
    attempts = sorted(directory.iterdir(), key=lambda path: path.name)
    numbers = []
    results = []
    success = None
    failures = []
    for attempt in attempts:
        match = ATTEMPT_RE.fullmatch(attempt.name)
        require(match is not None, f"unexpected target entry: {attempt}")
        numbers.append(int(match.group(1)))
        validate_attempt_entries(attempt)
        has_success = os.path.lexists(attempt / "success.json")
        has_failure = os.path.lexists(attempt / "failure.json")
        require(not (has_success and has_failure),
                f"attempt has conflicting terminal receipts: {attempt}")
        if has_success:
            require(success is None, f"multiple successful attempts for {target['name']}")
            value, relative = validate_success_receipt(
                root, attempt, sweep, target, contract, validation_cache, lock_fd,
            )
            success = {
                "attempt": attempt.name, "receipt_path": relative,
                "receipt": recorded_artifact(root, attempt / "success.json",
                                              "success receipt"),
                "session_nonce": value["session_nonce"],
                "artifacts": value["artifacts"],
            }
            results.append({"attempt": attempt.name, "state": "complete"})
        elif has_failure:
            value = validate_failure_receipt(root, attempt, sweep, target)
            summary = {
                "attempt": attempt.name, "state": "failed",
                "stage": value.get("stage"), "failure_kind": value.get("failure_kind"),
                "detail": value.get("detail"), "return_code": value.get("return_code"),
                "receipt": recorded_artifact(root, attempt / "failure.json",
                                              "failure receipt"),
            }
            failures.append(summary)
            results.append(summary)
        else:
            partial_artifacts = {}
            for entry in sorted(attempt.iterdir(), key=lambda path: path.name):
                seal_artifact(entry, f"interrupted artifact {entry.name}")
                partial_artifacts[entry.name] = recorded_artifact(
                    root, entry, f"interrupted artifact {entry.name}",
                )
            summary = {
                "attempt": attempt.name, "state": "interrupted",
                "artifacts": partial_artifacts,
            }
            failures.append(summary)
            results.append(summary)
        require(success is None or attempt.name == success["attempt"],
                f"attempt exists after success for {target['name']}")
    require(numbers == list(range(1, len(numbers) + 1)),
            f"attempt numbering is not contiguous for {target['name']}")
    return {"attempts": results, "success": success, "failures": failures}


def scan_all(
    root: Path, contract: dict[str, Any], validation_cache: set[str], lock_fd: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    inventory = contract["inventory"]["targets"]
    sweeps = []
    completed = 0
    failures = []
    nonces: set[str] = set()
    open_seen = False
    for sweep in range(1, SWEEP_COUNT + 1):
        rows = []
        sweep_complete = 0
        for target in inventory:
            state = scan_target(
                root, sweep, target, contract, validation_cache, lock_fd,
            )
            success = state["success"]
            if success is None:
                open_seen = True
                row_state = "pending"
            else:
                require(not open_seen,
                        f"completed target appears after an unresolved gap: {target['name']}")
                require(success["session_nonce"] not in nonces,
                        f"reference session nonce reused: {target['name']}")
                nonces.add(success["session_nonce"])
                row_state = "complete"
                completed += 1
                sweep_complete += 1
            for failure in state["failures"]:
                failures.append({
                    "sweep": sweep, "target_index": target["index"],
                    "target": target["name"], **failure,
                })
            rows.append({
                "index": target["index"], "name": target["name"],
                "state": row_state, "attempt_count": len(state["attempts"]),
                "success": success, "attempts": state["attempts"],
            })
        sweeps.append({
            "sweep": sweep, "target_count": EXPECTED_TARGETS,
            "completed_count": sweep_complete,
            "pending_count": EXPECTED_TARGETS - sweep_complete,
            "targets": rows,
        })
    total = SWEEP_COUNT * EXPECTED_TARGETS
    outcome = ("complete" if completed == total else
               "open_with_failures" if failures else "open")
    receipt = {
        "schema": 1, "kind": "candle-great100-two-sweep-reference-receipt",
        "contract_sha256": compact_json_sha256(contract),
        "contract": recorded_artifact(
            root, root / "collection-contract.json", "collection contract",
        ),
        "sweep_count": SWEEP_COUNT, "target_count": EXPECTED_TARGETS,
        "total_target_runs": total, "completed_target_runs": completed,
        "pending_target_runs": total - completed,
        "failure_attempt_count": len(failures), "failures": failures,
        "outcome": outcome, "closed": completed == total,
        "approval_status": "candidates_unapproved",
        "promotion_allowed": False, "sweeps": sweeps,
    }
    status = {
        key: receipt[key] for key in (
            "schema", "contract_sha256", "sweep_count", "target_count",
            "total_target_runs", "completed_target_runs", "pending_target_runs",
            "failure_attempt_count", "outcome", "closed", "approval_status",
            "promotion_allowed",
        )
    }
    status["kind"] = "candle-great100-two-sweep-reference-status"
    status["failures"] = failures
    return receipt, status


def write_aggregate(root: Path, receipt: dict[str, Any], status: dict[str, Any]) -> None:
    receipt_bytes = canonical_json(receipt)
    atomic_write(root / "receipt.json", receipt_bytes, "aggregate receipt")
    status = dict(status)
    status["receipt"] = {
        "path": "receipt.json", **bytes_record(receipt_bytes),
    }
    atomic_write(root / "status.json", canonical_json(status), "aggregate status")


def validate_root_entries(root: Path) -> None:
    allowed = {
        ".controller.lock", "collection-contract.json", "receipt.json",
        "status.json", "sweep-1", "sweep-2",
    }
    for entry in root.iterdir():
        require(entry.name in allowed, f"unexpected artifact-root entry: {entry}")
        if entry.name.startswith("sweep-"):
            private_directory(entry, entry.name)
        else:
            ordinary_file(entry, entry.name, single_link=True)


def recover_atomic_temporaries(root: Path) -> None:
    for name in (".receipt.json.new", ".status.json.new"):
        path = root / name
        if os.path.lexists(path):
            ordinary_file(path, f"controller-owned temporary {name}", single_link=True)
            path.unlink()


def ensure_sweep_directories(root: Path) -> None:
    for sweep in range(1, SWEEP_COUNT + 1):
        path = root / f"sweep-{sweep}"
        if not os.path.lexists(path):
            ensure_new_directory(path, f"sweep {sweep} directory")
        private_directory(path, f"sweep {sweep} directory")
        for entry in path.iterdir():
            match = TARGET_RE.fullmatch(entry.name)
            require(match is not None and 1 <= int(match.group(1)) <= EXPECTED_TARGETS,
                    f"unexpected sweep entry: {entry}")
            private_directory(entry, "target directory")


def next_pending(
    receipt: dict[str, Any], contract: dict[str, Any], root: Path,
) -> tuple[int, dict[str, Any], int] | None:
    target_by_index = {
        target["index"]: target for target in contract["inventory"]["targets"]
    }
    for sweep in receipt["sweeps"]:
        for row in sweep["targets"]:
            if row["state"] == "pending":
                return sweep["sweep"], target_by_index[row["index"]], \
                    row["attempt_count"] + 1
    return None


def run(arguments: argparse.Namespace) -> int:
    artifact_root = private_directory(arguments.artifact_root, "artifact root")
    project_root = ordinary_directory(arguments.project_root, "project repository")
    candle_root = ordinary_directory(arguments.candle_root, "Candle collector repository")
    reference_root = ordinary_directory(arguments.reference_root, "reference repository")
    require(not artifact_root.is_relative_to(project_root) and
            not project_root.is_relative_to(artifact_root) and
            not artifact_root.is_relative_to(candle_root) and
            not artifact_root.is_relative_to(reference_root) and
            not candle_root.is_relative_to(artifact_root) and
            not reference_root.is_relative_to(artifact_root),
            "artifact root must be external to both repositories")
    lock_path = artifact_root / ".controller.lock"
    if not os.path.lexists(lock_path):
        exclusive_write(lock_path, b"candle-reference-controller-lock-v1\n", "lock file")
    lock_path = ordinary_file(lock_path, "lock file", single_link=True)
    lock_fd = os.open(lock_path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise CollectionFailure("another collection controller owns the artifact root") \
                from error
        recover_atomic_temporaries(artifact_root)
        validate_root_entries(artifact_root)
        contract, _targets = build_contract(arguments)
        contract_path = artifact_root / "collection-contract.json"
        expected_contract_bytes = canonical_json(contract)
        if os.path.lexists(contract_path):
            observed = stable_bytes(
                contract_path, "collection contract", single_link=True,
            )
            require(observed == expected_contract_bytes,
                    "current inputs differ from the retained collection contract")
        else:
            exclusive_write(
                contract_path, expected_contract_bytes, "collection contract",
            )
        ensure_sweep_directories(artifact_root)
        validation_cache: set[str] = set()
        receipt, status = scan_all(
            artifact_root, contract, validation_cache, lock_fd,
        )
        write_aggregate(artifact_root, receipt, status)
        while not receipt["closed"]:
            pending = next_pending(receipt, contract, artifact_root)
            require(pending is not None, "open receipt has no pending target")
            sweep, target, attempt_number = pending
            directory = target_directory(
                artifact_root, sweep, target["index"],
            )
            if not os.path.lexists(directory):
                ensure_new_directory(directory, f"target directory {target['name']}")
            attempt = ensure_new_directory(
                directory / f"attempt-{attempt_number:04d}",
                f"attempt for {target['name']}",
            )
            try:
                collect_target(
                    artifact_root, attempt, sweep, target, contract, lock_fd,
                )
                validation_cache.add(artifact_relative(
                    artifact_root, attempt / "success.json",
                ))
            except CollectionFailure:
                receipt, status = scan_all(
                    artifact_root, contract, validation_cache, lock_fd,
                )
                write_aggregate(artifact_root, receipt, status)
                return 1
            receipt, status = scan_all(
                artifact_root, contract, validation_cache, lock_fd,
            )
            write_aggregate(artifact_root, receipt, status)
        validate_environment(contract)
        return 0
    finally:
        os.close(lock_fd)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--artifact-root", type=Path, required=True)
    result.add_argument("--project-root", type=Path, required=True)
    result.add_argument("--project-head", required=True)
    result.add_argument("--controller-sha256", required=True)
    result.add_argument("--python-sha256", required=True)
    result.add_argument("--git-sha256", required=True)
    result.add_argument("--candle-root", type=Path, required=True)
    result.add_argument("--candle-head", required=True)
    result.add_argument("--manifest-sha256", required=True)
    result.add_argument("--collector-sha256", required=True)
    result.add_argument("--protocol-sha256", required=True)
    result.add_argument("--reference-root", type=Path, required=True)
    result.add_argument("--reference-head", required=True)
    result.add_argument("--runtime", type=Path, required=True)
    result.add_argument("--runtime-sha256", required=True)
    result.add_argument("--runtime-stublib", type=Path, required=True)
    result.add_argument("--runtime-stublib-sha256", required=True)
    result.add_argument("--ocamlc", type=Path, required=True)
    result.add_argument("--ocamlc-sha256", required=True)
    result.add_argument("--ocamlfind", type=Path, required=True)
    result.add_argument("--ocamlfind-sha256", required=True)
    result.add_argument("--collection-wall-seconds", type=int, required=True)
    result.add_argument("--target-wall-seconds", type=int, required=True)
    result.add_argument("--validation-wall-seconds", type=int, required=True)
    return result


def validate_startup() -> None:
    require(lexical_absolute(Path(sys.executable)) == PYTHON_ARGUMENT_PATH,
            "controller was not launched by exact /usr/bin/python3")
    require(sys.argv and Path(sys.argv[0]).is_absolute() and
            lexical_absolute(Path(sys.argv[0])) == PROGRAM_PATH,
            "controller script argument is not its absolute committed path")
    flags = sys.flags
    require(flags.isolated == 1 and flags.ignore_environment == 1 and
            flags.no_site == 1 and flags.no_user_site == 1 and
            getattr(flags, "safe_path", False) and flags.optimize == 0 and
            flags.debug == 0 and flags.inspect == 0 and flags.interactive == 0,
            "controller requires exact isolated/no-site Python startup")
    require(dict(os.environ) == STARTUP_ENVIRONMENT,
            "controller startup environment is not the exact allowlist")


def parse_arguments() -> argparse.Namespace:
    argument_parser = parser()
    option_names = {
        option
        for action in argument_parser._actions
        if action.required
        for option in action.option_strings
    }
    raw = sys.argv[1:]
    require(len(raw) == 2 * len(option_names),
            "controller requires each CLI option exactly once")
    observed = raw[::2]
    require(all(option in option_names for option in observed) and
            len(set(observed)) == len(option_names) and
            set(observed) == option_names,
            "controller CLI option set/order is malformed or duplicated")
    return argument_parser.parse_args(raw)


def main() -> int:
    global ACTIVE_PROCESS, PENDING_SIGNAL
    old_umask = os.umask(0o077)
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, HANDLED_SIGNALS)
    previous_handlers = {
        signum: signal.getsignal(signum) for signum in HANDLED_SIGNALS
    }
    for signum in HANDLED_SIGNALS:
        signal.signal(signum, controller_signal_handler)
    try:
        try:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
            validate_startup()
            return run(parse_arguments())
        except CollectionFailure as error:
            print(f"reference sweep failed: {error}", file=sys.stderr)
            return 1
        except ControllerInterrupted as error:
            print(
                f"reference sweep interrupted by signal {error.signum}",
                file=sys.stderr,
            )
            return 128 + error.signum
    finally:
        signal.pthread_sigmask(signal.SIG_BLOCK, HANDLED_SIGNALS)
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
        ACTIVE_PROCESS = None
        PENDING_SIGNAL = None
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        os.umask(old_umask)


if __name__ == "__main__":
    raise SystemExit(main())
