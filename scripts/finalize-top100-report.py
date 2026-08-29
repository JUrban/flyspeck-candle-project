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
REFERENCE_PROTOCOL_PATH = "candle/reference_protocol.py"
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
    "review", "collection_evidence", "targets",
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
COLLECTION_EVIDENCE_KEYS = {"contract", "receipt"}
COLLECTION_CONTROLLER_PATH = "scripts/run-top100-reference-sweeps.py"
COLLECTION_PROJECT_HEAD = "95bb84fffade845406af92305baea0a9686ef21f"
COLLECTION_CONTROLLER_BYTES = 109742
COLLECTION_CONTROLLER_SHA256 = \
    "a703c01f1153bd8774f2f1ab4342950469011cbfee6d7f605485cc71d87f6301"
COLLECTION_CANDLE_PATHS = {
    "collector": ("candle/reference_fingerprints.py", "100644"),
    "protocol": ("candle/reference_protocol.py", "100644"),
    "manifest": ("candle/top100_manifest.json", "100644"),
    "serializer": ("candle/fingerprint.ml", "100644"),
    "source_contract": ("candle/reference_source_contracts.json", "100644"),
}
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
REFERENCE_PLAN_SCHEMA = "candle-s1-reference-plan-v9"
REFERENCE_CANDIDATE_SCHEMA = "candle-s1-reference-candidate-v9"
EXTERNAL_RUNTIME_POLICY = \
    "single_private_path_gp_csdp_with_pinned_shell_v3"
THREAD_CAP_ENVIRONMENT = {
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
}
CSDP_BUILD_KIND = "candle-hol-light-csdp-single-thread-build"
CSDP_STATIC_LIBSDP_SHA256 = (
    "ede58dd5bf3620aa08045aa767fd1280fefe1e76d6ece276e8a674d6156bca25"
)
CSDP_TOOLCHAIN = {
    "archiver_argument": "/usr/bin/ar",
    "archiver_resolved": "/usr/bin/x86_64-linux-gnu-ar",
    "archiver_sha256":
        "534681ac11c18868cfc4fdf98770aa0ba8973eedc90c231e94e6ba96e1a04f27",
    "binutils_version_first_line": "GNU ld (GNU Binutils for Ubuntu) 2.42",
    "compiler_argument": "/usr/bin/gcc",
    "compiler_resolved": "/usr/bin/x86_64-linux-gnu-gcc-13",
    "compiler_sha256":
        "1b99826121ae6682a634e5efe09bd3e3df58ce58e0b28f849114ab5b89139c26",
    "compiler_version_first_line":
        "gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0",
}
CSDP_RECIPE = {
    "cflags": (
        "-m64 -O2 -fno-ident -ansi -Wall -DBIT64 -DUSESIGTERM "
        "-DUSEGETTIME -I../include"
    ),
    "commands": [
        "make -C lib clean libsdp.a CC=/usr/bin/gcc CFLAGS=<cflags>",
        (
            "make -C solver clean csdp CC=/usr/bin/gcc CFLAGS=<cflags> "
            "LIBS=<library_flags>"
        ),
    ],
    "library_flags": (
        "-L../lib -Wl,-Bstatic -lsdp -Wl,-Bdynamic -llapack -lblas "
        "-lm -lgfortran"
    ),
    "native_cpu_flags": False,
    "openmp_enabled": False,
}
CSDP_PROBE_SUCCESS = "Success: SDP solved"
CSDP_PROBE_PRIMAL = "2.3000000e+01"
CSDP_PROBE_DUAL = "2.3000000e+01"
CSDP_FORBIDDEN_ELF_FRAGMENTS = (
    "libgomp", "libomp", "libiomp", "libopenblas", "libpthread",
)

REFERENCE_REPLAY_CONTROLLER = r'''import hashlib
import json
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
if (reference.PLAN_SCHEMA != "candle-s1-reference-plan-v9" or
        reference.CANDIDATE_SCHEMA != "candle-s1-reference-candidate-v9"):
    raise RuntimeError("captured reference validator is not v9 compatible")
runtime_root = stage / instructions["runtime_root"]
reference.ROOT = runtime_root
reference.MANIFEST = runtime_root / "candle/top100_manifest.json"
reference.SERIALIZER = runtime_root / "candle/fingerprint.ml"
reference.SOURCE_CONTRACT = \
    runtime_root / "candle/reference_source_contracts.json"

def stable_runtime_projection(plan):
    projection = {
        key: plan["reference"][key] for key in (
            "runtime_executable", "runtime_interpreter", "runtime_stublib",
            "runtime_library_tree", "runtime_stub_files", "elf_runtime",
            "ocamlc", "findlib", "hol_ml", "generated_boot_files",
            "ocaml_library_tree", "external_runtime",
        )
    }
    projection["elf_runtime"] = reference._stable_elf_evidence(
        projection["elf_runtime"])
    external = dict(projection["external_runtime"])
    external["elf_runtime"] = reference._stable_elf_evidence(
        external["elf_runtime"])
    projection["external_runtime"] = external
    return {
        "reference": projection,
        "fresh_process_contract": plan["fresh_process_contract"],
    }

validated_elf = set()
validated_current_plan = False
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
    if not validated_current_plan:
        target = json.loads(json.dumps(replay["target"]))
        target["fingerprint_request"]["expected_identities"] = None

        def authenticated_target(name):
            if name != target["name"]:
                raise RuntimeError("unexpected reconstruction target")
            return {
                "schema_version": 1,
                "target_count": 1,
                "targets": [target],
            }, target

        reference._target_from_manifest = authenticated_target
        reference._collector_repository_pin = lambda: \
            plan["input"]["collector_repository"]
        rebuilt = reference._rebuild_plan(plan)
        if stable_runtime_projection(rebuilt) != stable_runtime_projection(plan):
            raise RuntimeError("live reference runtime differs from plan")
        validated_current_plan = True
    core = plan["reference"]["elf_runtime"]
    external = plan["reference"]["external_runtime"]["elf_runtime"]
    for evidence, roots in (
        (core, [
            plan["reference"]["runtime_interpreter"]["path"],
            *(item["path"] for item in
              plan["reference"]["runtime_stub_files"]),
        ]),
        (external, [
            plan["reference"]["external_runtime"]["command_shell"]
                ["resolved_executable"]["path"],
            plan["reference"]["external_runtime"]["pari_gp"]
                ["resolved_executable"]["path"],
            plan["reference"]["external_runtime"]["csdp"]
                ["resolved_executable"]["path"],
        ]),
    ):
        stable = reference._stable_elf_evidence(evidence)
        key = hashlib.sha256(json.dumps(
            stable, sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest()
        if key not in validated_elf:
            reference.validate_elf_closure_evidence_live(evidence, roots)
            validated_elf.add(key)
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


def validate_csdp_build_statement(
    statement: object, source: dict[str, object], csdp: dict[str, object],
    probe_input: dict[str, object],
) -> dict[str, Any]:
    """Require the exact reviewed portable, single-thread CSDP build claim."""
    expected = {
        "schema": 1,
        "kind": CSDP_BUILD_KIND,
        "source": {
            "archive": Path(str(source["path"])).name,
            "bytes": source["bytes"],
            "sha256": source["sha256"],
            "ubuntu_source_package": "coinor-csdp 6.2.0-5build1 (Noble)",
            "upstream_tree": "Csdp-6.2.0",
        },
        "toolchain": CSDP_TOOLCHAIN,
        "recipe": CSDP_RECIPE,
        "outputs": {
            "csdp_path": "usr/bin/csdp",
            "csdp_bytes": csdp["bytes"],
            "csdp_sha256": csdp["sha256"],
            "static_libsdp_sha256": CSDP_STATIC_LIBSDP_SHA256,
        },
        "unit_probe": {
            "input_path": Path(str(probe_input["path"])).name,
            "input_bytes": probe_input["bytes"],
            "input_sha256": probe_input["sha256"],
            "exit_code": 0,
            "success_line": CSDP_PROBE_SUCCESS,
            "primal_objective": CSDP_PROBE_PRIMAL,
            "dual_objective": CSDP_PROBE_DUAL,
            "maximum_allowed_dimacs_error": "1.0e-6",
        },
        "runtime_policy": {
            "single_process_solver": True,
            "single_thread_build": True,
            "external_shared_libraries_closed_separately": True,
        },
    }
    require(isinstance(statement, dict) and
            canonical_json_bytes(statement) == canonical_json_bytes(expected),
            "CSDP build statement differs from exact reviewed contract")
    return statement


def normalize_csdp_probe_stdout(stdout: str) -> str:
    """Remove exactly CSDP's four measured wall-time values."""
    timing = re.compile(
        r"^(Elements|Factor|Other|Total) time: [0-9]+\.[0-9]+ \n$")
    normalized: list[str] = []
    seen: list[str] = []
    for line in stdout.splitlines(keepends=True):
        match = timing.fullmatch(line)
        if match is None:
            normalized.append(line)
        else:
            seen.append(match.group(1))
            normalized.append(f"{match.group(1)} time: <measured>\n")
    require(seen == ["Elements", "Factor", "Other", "Total"],
            "CSDP probe has malformed timing records")
    return "".join(normalized)


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


def stable_file_bytes(path: Path, label: str) -> bytes:
    """Read an ordinary file while rejecting replacement or concurrent edits."""
    path = ordinary_file(path, label)
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as error:
        raise ValidationError(f"cannot open {label}: {path}") from error
    chunks = []
    count = 0
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode), f"{label} is not ordinary: {path}")
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            chunks.append(block)
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
    return b"".join(chunks)


def executable_route_record(path: Path, label: str) -> dict[str, Any]:
    """Reproduce the collector's lexical and resolved executable route pin."""
    argument = lexical_absolute(path)
    try:
        metadata = argument.lstat()
        parent_metadata = argument.parent.lstat()
        resolved = argument.resolve(strict=True)
        resolved_metadata = resolved.lstat()
    except (FileNotFoundError, RuntimeError, OSError) as error:
        raise ValidationError(f"could not resolve {label}: {argument}") from error
    require(stat.S_ISREG(resolved_metadata.st_mode) and
            stat.S_IMODE(resolved_metadata.st_mode) & 0o111 != 0,
            f"resolved {label} is not executable: {resolved}")

    def component(route: Path, route_metadata: os.stat_result) -> dict[str, Any]:
        if stat.S_ISLNK(route_metadata.st_mode):
            kind = "symlink"
            extra = {"target": os.readlink(route)}
        elif stat.S_ISDIR(route_metadata.st_mode):
            kind = "directory"
            extra = {}
        elif stat.S_ISREG(route_metadata.st_mode):
            kind = "file"
            extra = {}
        else:
            raise ValidationError(f"unsupported {label} route component: {route}")
        return {
            "path": str(route), "kind": kind,
            "mode": stat.S_IMODE(route_metadata.st_mode),
            **extra, "resolved_path": str(route.resolve(strict=True)),
        }

    identity = stable_file_identity(resolved, f"resolved {label}")
    return {
        "argument_path": str(argument),
        "argument_parent": component(argument.parent, parent_metadata),
        "argument": component(argument, metadata),
        "resolved_executable": {
            "path": str(resolved), "sha256": identity.sha256,
            "mode": stat.S_IMODE(resolved_metadata.st_mode),
        },
    }


def runtime_file_record(path: Path, label: str) -> dict[str, Any]:
    """Reproduce the collection controller's argument/resolved file record."""
    argument = lexical_absolute(path)
    try:
        resolved = argument.resolve(strict=True)
    except (FileNotFoundError, RuntimeError, OSError) as error:
        raise ValidationError(f"could not resolve {label}: {argument}") from error
    identity = stable_file_identity(resolved, f"resolved {label}")
    return {
        "argument_path": str(argument), "path": str(resolved),
        **identity.as_json(),
    }


def tree_inventory(
    path: Path, label: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Reproduce the collector's path/kind/mode/link/content tree pin."""
    root = ordinary_directory(path, label)
    records: list[dict[str, Any]] = []
    for entry in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = entry.relative_to(root).as_posix()
        metadata = entry.lstat()
        mode = stat.S_IMODE(metadata.st_mode)
        if stat.S_ISLNK(metadata.st_mode):
            try:
                resolved = entry.resolve(strict=True)
            except (FileNotFoundError, RuntimeError, OSError) as error:
                raise ValidationError(f"broken symlink in {label}: {entry}") from error
            record: dict[str, Any] = {
                "path": relative, "kind": "symlink", "mode": mode,
                "target": os.readlink(entry), "resolved_path": str(resolved),
            }
            if resolved.is_file():
                record["resolved_sha256"] = stable_file_identity(
                    resolved, f"{label} resolved symlink",
                ).sha256
            else:
                require(resolved.is_dir(),
                        f"unsupported symlink target in {label}: {entry}")
            records.append(record)
        elif stat.S_ISREG(metadata.st_mode):
            records.append({
                "path": relative, "kind": "file", "mode": mode,
                "sha256": stable_file_identity(entry, f"{label} file").sha256,
            })
        elif stat.S_ISDIR(metadata.st_mode):
            records.append({
                "path": relative, "kind": "directory", "mode": mode,
            })
        else:
            raise ValidationError(f"unsupported filesystem entry in {label}: {entry}")
    digest = hashlib.sha256()
    for record in records:
        digest.update(json.dumps(
            record, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8"))
        digest.update(b"\n")
    return ({
        "root": str(root), "root_mode": stat.S_IMODE(root.lstat().st_mode),
        "entry_count": len(records), "inventory_sha256": digest.hexdigest(),
        "inventory_policy":
            "relative_path_kind_mode_link_target_and_content_v1",
    }, records)


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


def git_common_directory(root: Path, label: str) -> Path:
    dot_git = root / ".git"
    if dot_git.is_dir():
        git_directory = ordinary_directory(dot_git, f"{label} Git directory")
    else:
        try:
            value = stable_file_bytes(dot_git, f"{label} .git file").decode(
                "utf-8", errors="strict",
            )
        except UnicodeDecodeError as error:
            raise ValidationError(f"{label} has malformed .git metadata") from error
        require(value.startswith("gitdir: ") and value.endswith("\n") and
                value.count("\n") == 1,
                f"{label} has malformed .git metadata")
        git_path = Path(value[len("gitdir: "):-1])
        if not git_path.is_absolute():
            git_path = root / git_path
        git_directory = ordinary_directory(
            git_path.resolve(strict=True), f"{label} Git directory",
        )
    common_file = git_directory / "commondir"
    if not os.path.lexists(common_file):
        return git_directory
    try:
        value = stable_file_bytes(
            common_file, f"{label} Git common-directory file",
        ).decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValidationError(
            f"{label} has malformed Git common-directory metadata",
        ) from error
    require(value.endswith("\n") and value.count("\n") == 1,
            f"{label} has malformed Git common-directory metadata")
    common_path = Path(value[:-1])
    if not common_path.is_absolute():
        common_path = git_directory / common_path
    return ordinary_directory(
        common_path.resolve(strict=True), f"{label} Git common directory",
    )


def validate_git_checkout(root: Path, expected_head: str, label: str) -> None:
    root = ordinary_directory(root, label)
    require_commit(expected_head, f"{label} head")
    common_path = git_common_directory(root, label)
    require(not os.path.lexists(common_path / "info/grafts"),
            f"{label} has a Git grafts file")
    top = git_bytes(root, "rev-parse", "--show-toplevel").decode().strip()
    require(Path(top) == root, f"{label} is not the exact Git top level")
    head = git_bytes(root, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    require(head == expected_head, f"{label} revision mismatch")
    status = git_bytes(
        root, "status", "--porcelain=v1", "-z", "--untracked-files=all",
    )
    require(status == b"", f"{label} worktree is not clean")
    require(git_bytes(
        root, "for-each-ref", "--format=%(refname)", "refs/replace",
    ) == b"", f"{label} has Git replacement objects")
    for record in git_bytes(root, "ls-files", "-v", "-z").split(b"\0"):
        if record:
            require(record.startswith(b"H "),
                    f"{label} has assume-unchanged or skip-worktree index flags")


def committed_file_at(
    root: Path, head: str, relative: str, expected_mode: str, label: str,
) -> tuple[dict[str, Any], bytes]:
    """Authenticate one ordinary blob directly from a named Git commit."""
    root = ordinary_directory(root, f"{label} repository")
    head = require_commit(head, f"{label} commit")
    relative = safe_relative(relative, f"{label} committed path")
    top = git_bytes(root, "rev-parse", "--show-toplevel").decode().strip()
    require(Path(top) == root, f"{label} repository is not an exact Git top level")
    require(git_bytes(
        root, "for-each-ref", "--format=%(refname)", "refs/replace",
    ) == b"", f"{label} repository has Git replacement objects")
    line = git_bytes(root, "ls-tree", head, "--", relative).decode().rstrip("\n")
    fields = line.split(maxsplit=3)
    require(len(fields) == 4 and fields[0] == expected_mode and
            fields[1] == "blob" and fields[3] == relative and
            re.fullmatch(r"[0-9a-f]{40,64}", fields[2]) is not None,
            f"{label} is not one exact committed ordinary file")
    source = git_bytes(root, "cat-file", "blob", f"{head}:{relative}")
    return {"path": relative, **bytes_identity(source).as_json()}, source


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
    suite_records = [
        line for line in lines if line.startswith("CANDLE_GREAT100_SUITE_")
    ]
    process_records = [
        line for line in lines if line.startswith("CANDLE_GREAT100_PROCESS_")
    ]
    linked_records = [
        line for line in lines if line.startswith("CANDLE_LINKED_PROVENANCE_")
    ]
    linked_witnesses = [
        line for line in lines if line.startswith("linked CakeML provenance ")
    ]
    require(suite_records == [suite_marker],
            f"unexpected or conflicting suite protocol record for {name}")
    require(process_records == [start_marker, complete_marker],
            f"unexpected or conflicting process protocol record for {name}")
    require(linked_records == [linked_marker],
            f"unexpected or conflicting linked protocol record for {name}")
    require(linked_witnesses == [LINKED_PASS_WITNESS],
            f"unexpected or conflicting linked PASS witness for {name}")
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
    linked_pass = lines.index(LINKED_PASS_WITNESS)
    require(suite < start < linked_pass < linked < complete,
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
         not line.startswith(FINGERPRINT_MARKER + "\t")) or
        (line.startswith("CANDLE_STATE_FINGERPRINT_V") and
         not line.startswith(STATE_FINGERPRINT_MARKER + "\t"))
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
    stage: Path, stager: Stager, validator: Snapshot, protocol: Snapshot,
    source_contract: Snapshot, contracts: dict[str, Snapshot],
    closure: dict[str, Any],
) -> dict[str, str]:
    runtime_root = "approval/replay/runtime-root"
    inputs = {
        REFERENCE_VALIDATOR_PATH: validator,
        REFERENCE_PROTOCOL_PATH: protocol,
        "candle/regression.py": contracts["candle/regression.py"],
        "candle/fingerprint.ml": contracts["candle/fingerprint.ml"],
        "candle/top100_manifest.json": contracts["candle/top100_manifest.json"],
        "candle/reference_source_contracts.json": source_contract,
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
        "protocol": f"{runtime_root}/{REFERENCE_PROTOCOL_PATH}",
        "regression": f"{runtime_root}/candle/regression.py",
    }


def validate_elf_runtime_structure(
    evidence: Any, expected_roots: list[str], label: str,
) -> dict[str, Any]:
    """Validate the closed ELF evidence envelope and file pins."""
    require(isinstance(evidence, dict) and set(evidence) == {
        "policy", "output_normalization", "tools",
        "hardcoded_loader_routes", "ld_so_cache", "ld_so_preload",
        "environment", "requested_roots", "observations", "closure",
    } and evidence["policy"] ==
            "authenticated_explicit_bash_ldd_closure_v1" and
            evidence["output_normalization"] ==
            "strict_recognized_lines_replace_only_aslr_addresses_v1" and
            evidence["environment"] == {
                "PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C",
            } and evidence["ld_so_preload"] == {
                "path": "/etc/ld.so.preload", "status": "absent",
            }, f"malformed {label} ELF evidence")

    def route(value: Any, argument_path: str, route_label: str) -> None:
        require(isinstance(value, dict) and set(value) == {
            "argument_path", "argument_parent", "argument",
            "resolved_executable",
        } and value["argument_path"] == argument_path and
                isinstance(value["resolved_executable"], dict) and
                set(value["resolved_executable"]) == {"path", "sha256", "mode"} and
                isinstance(value["resolved_executable"]["path"], str) and
                Path(value["resolved_executable"]["path"]).is_absolute() and
                SHA256_RE.fullmatch(
                    value["resolved_executable"]["sha256"],
                ) is not None and is_int(value["resolved_executable"]["mode"]),
                f"malformed {label} {route_label} route")

    tools = evidence["tools"]
    require(isinstance(tools, dict) and set(tools) == {"bash", "ldd"},
            f"malformed {label} ELF tools")
    route(tools["bash"], "/bin/bash", "bash")
    route(tools["ldd"], "/usr/bin/ldd", "ldd")
    loader_paths = (
        "/lib/ld-linux.so.2", "/lib64/ld-linux-x86-64.so.2",
        "/libx32/ld-linux-x32.so.2",
    )
    loaders = evidence["hardcoded_loader_routes"]
    require(isinstance(loaders, list) and len(loaders) == len(loader_paths),
            f"malformed {label} ELF loader routes")
    present = 0
    for expected, loader in zip(loader_paths, loaders):
        require(isinstance(loader, dict) and
                loader.get("argument_path") == expected and
                loader.get("status") in {"absent", "present"},
                f"malformed {label} ELF loader route")
        if loader["status"] == "absent":
            require(set(loader) == {"argument_path", "status"},
                    f"malformed {label} absent ELF loader")
        else:
            require(set(loader) == {"argument_path", "status", "route"},
                    f"malformed {label} present ELF loader")
            route(loader["route"], expected, "loader")
            present += 1
    require(present >= 1, f"{label} has no present ELF loader")
    cache = evidence["ld_so_cache"]
    require(isinstance(cache, dict) and set(cache) == {"path", "sha256"} and
            cache["path"] == "/etc/ld.so.cache" and
            SHA256_RE.fullmatch(cache["sha256"]) is not None,
            f"malformed {label} loader cache")

    roots = evidence["requested_roots"]
    expected_roots = sorted(set(expected_roots))
    require(isinstance(roots, list) and
            [item.get("path") if isinstance(item, dict) else None
             for item in roots] == expected_roots,
            f"{label} ELF requested roots differ")
    for pin in roots:
        require(set(pin) == {"path", "sha256"} and
                SHA256_RE.fullmatch(pin["sha256"]) is not None,
                f"malformed {label} ELF root pin")
    observations = evidence["observations"]
    expected_observations = sorted(set(expected_roots) | {
        tools["bash"]["resolved_executable"]["path"],
    })
    require(isinstance(observations, list) and
            [item.get("root", {}).get("path")
             if isinstance(item, dict) else None for item in observations] ==
            expected_observations,
            f"{label} ELF observation roots differ")
    for observation in observations:
        require(set(observation) == {
            "root", "argv", "environment", "return_code", "stdout",
            "stdout_sha256", "normalized_stdout", "normalized_stdout_sha256",
            "stderr", "stderr_sha256", "resolved_files", "virtual_objects",
        } and observation["environment"] == evidence["environment"] and
                is_int(observation["return_code"]) and
                observation["return_code"] == 0 and
                isinstance(observation["stdout"], str) and
                hashlib.sha256(observation["stdout"].encode()).hexdigest() ==
                observation["stdout_sha256"] and
                isinstance(observation["normalized_stdout"], str) and
                hashlib.sha256(
                    observation["normalized_stdout"].encode(),
                ).hexdigest() == observation["normalized_stdout_sha256"] and
                observation["stderr"] == "" and
                observation["stderr_sha256"] == hashlib.sha256(b"").hexdigest() and
                isinstance(observation["resolved_files"], list) and
                isinstance(observation["virtual_objects"], list),
                f"malformed {label} ELF observation")
    closure = evidence["closure"]
    require(isinstance(closure, list) and closure and
            [item.get("path") if isinstance(item, dict) else None
             for item in closure] == sorted({
                 item.get("path") for item in closure if isinstance(item, dict)
             }), f"malformed {label} ELF closure order")
    for pin in closure:
        require(set(pin) == {"path", "sha256"} and
                isinstance(pin["path"], str) and Path(pin["path"]).is_absolute() and
                SHA256_RE.fullmatch(pin["sha256"]) is not None,
                f"malformed {label} ELF closure pin")
    return evidence


def stable_elf_runtime(evidence: dict[str, Any]) -> dict[str, Any]:
    stable = json.loads(json.dumps(evidence))
    for observation in stable["observations"]:
        observation.pop("stdout")
        observation.pop("stdout_sha256")
    return stable


def elf_oracle_projection(evidence: dict[str, Any]) -> dict[str, Any]:
    return {key: evidence[key] for key in (
        "policy", "output_normalization", "tools", "hardcoded_loader_routes",
        "ld_so_cache", "ld_so_preload", "environment",
    )}


def validate_reference_plan_bindings(
    plan: dict[str, Any], candidate: dict[str, Any], target: dict[str, Any],
    run: dict[str, Any], policy: dict[str, Any], source_contract: Snapshot,
    root: Path, validator: Snapshot, protocol: Snapshot, serializer_sha256: str,
) -> None:
    name = target["name"]
    require(set(plan) == {
        "schema", "status", "session_nonce", "fresh_process_contract",
        "reference", "input", "request",
    } and plan["schema"] == REFERENCE_PLAN_SCHEMA and
            plan["status"] == "planned_not_executed",
            f"malformed v9 reference plan for {name}")
    nonce = run["session_nonce"]
    require(plan["session_nonce"] == candidate.get("session_nonce") == nonce,
            f"reference plan/candidate nonce mismatch for {name}")

    reference = plan["reference"]
    require(isinstance(reference, dict) and set(reference) == {
        "root", "git_head", "git_status", "runtime_executable",
        "runtime_interpreter", "runtime_stublib", "runtime_library_tree",
        "runtime_stub_files", "elf_runtime", "ocamlc", "findlib",
        "hol_ml", "generated_boot_files", "ocaml_library_tree",
        "external_runtime",
    }, f"malformed v9 reference provenance for {name}")
    require(isinstance(reference["root"], str) and
            Path(reference["root"]).is_absolute() and
            reference["git_head"] == run["reference_git_head"] ==
            policy["exact_source_reference_commit"] and
            reference["git_status"] == [],
            f"reference plan head/status mismatch for {name}")

    def file_pin(value: Any, label: str) -> None:
        require(isinstance(value, dict) and set(value) == {"path", "sha256"} and
                isinstance(value["path"], str) and
                Path(value["path"]).is_absolute() and
                SHA256_RE.fullmatch(value["sha256"]) is not None,
                f"malformed reference {label} for {name}")

    def tree_pin(value: Any, label: str) -> None:
        require(isinstance(value, dict) and set(value) == {
            "root", "root_mode", "entry_count", "inventory_sha256",
            "inventory_policy",
        } and isinstance(value["root"], str) and
                Path(value["root"]).is_absolute() and
                is_int(value["root_mode"]) and is_int(value["entry_count"]) and
                value["entry_count"] >= 0 and
                SHA256_RE.fullmatch(value["inventory_sha256"]) is not None and
                value["inventory_policy"] ==
                "relative_path_kind_mode_link_target_and_content_v1",
                f"malformed reference {label} for {name}")

    for key in ("runtime_executable", "runtime_interpreter", "runtime_stublib",
                "hol_ml"):
        file_pin(reference[key], key.replace("_", " "))
    for key in ("runtime_library_tree", "ocaml_library_tree"):
        tree_pin(reference[key], key.replace("_", " "))
    for key in ("runtime_stub_files",):
        values = reference[key]
        require(isinstance(values, list) and values,
                f"empty reference {key.replace('_', ' ')} for {name}")
        for value in values:
            file_pin(value, key.replace("_", " "))
        require([value["path"] for value in values] ==
                sorted({value["path"] for value in values}),
                f"unsorted reference {key.replace('_', ' ')} for {name}")
    validate_elf_runtime_structure(
        reference["elf_runtime"], [
            reference["runtime_interpreter"]["path"],
            *(value["path"] for value in reference["runtime_stub_files"]),
        ], f"{name} core",
    )
    require(reference["runtime_library_tree"]["root"] ==
            str(Path(reference["runtime_stublib"]["path"]).parent),
            f"runtime library tree mismatch for {name}")
    ocamlc = reference["ocamlc"]
    require(isinstance(ocamlc, dict) and set(ocamlc) == {
        "path", "sha256", "version", "stdlib_directory",
    }, f"malformed reference OCaml compiler for {name}")
    file_pin({key: ocamlc[key] for key in ("path", "sha256")},
             "OCaml compiler")
    require(isinstance(ocamlc["version"], str) and ocamlc["version"] and
            isinstance(ocamlc["stdlib_directory"], str) and
            Path(ocamlc["stdlib_directory"]).is_absolute(),
            f"malformed reference OCaml compiler metadata for {name}")
    findlib = reference["findlib"]
    require(isinstance(findlib, dict) and set(findlib) == {
        "executable", "version", "configuration", "package_roots",
    }, f"malformed reference findlib for {name}")
    file_pin(findlib["executable"], "findlib executable")
    file_pin(findlib["configuration"], "findlib configuration")
    require(isinstance(findlib["version"], str) and findlib["version"] and
            isinstance(findlib["package_roots"], list) and
            findlib["package_roots"],
            f"malformed reference findlib metadata for {name}")
    for root_pin in findlib["package_roots"]:
        tree_pin(root_pin, "findlib package root")
    require([value["root"] for value in findlib["package_roots"]] ==
            sorted({value["root"] for value in findlib["package_roots"]}) and
            reference["ocaml_library_tree"] in findlib["package_roots"],
            f"reference findlib tree closure mismatch for {name}")
    boot_files = reference["generated_boot_files"]
    require(isinstance(boot_files, list) and len(boot_files) == 3,
            f"malformed reference boot files for {name}")
    for value in boot_files:
        file_pin(value, "generated boot file")
    require([value["path"] for value in boot_files] == [
        str(Path(reference["root"]) / "hol_loader.cmo"),
        str(Path(reference["root"]) / "pa_j.cmo"),
        str(Path(reference["root"]) / "load_camlp5_topfind.ml"),
    ], f"reference boot-file set mismatch for {name}")

    fresh = plan["fresh_process_contract"]
    require(isinstance(fresh, dict) and set(fresh) == {
        "required", "preloaded_checkpoint_allowed", "working_directory",
        "environment_policy", "runtime_argv", "runtime_environment",
    } and fresh["required"] is True and
            fresh["preloaded_checkpoint_allowed"] is False and
            fresh["working_directory"] == reference["root"] and
            fresh["environment_policy"] ==
            "sanitized_allowlist_no_inherited_overrides" and
            fresh["runtime_argv"] == [
                reference["runtime_executable"]["path"], "-init",
                reference["hol_ml"]["path"], "-I", reference["root"],
                "-noprompt"] and
            isinstance(fresh["runtime_environment"], dict),
            f"reference plan fresh-process contract mismatch for {name}")

    external = reference["external_runtime"]
    require(isinstance(external, dict) and set(external) == {
        "policy", "command_shell", "pari_gp", "pari_gp_version",
        "package_archive", "package_tree", "configuration", "data_tree",
        "csdp", "csdp_bytes", "csdp_source_archive", "csdp_build",
        "csdp_probe_input", "thread_policy", "elf_runtime", "probe",
        "csdp_probe",
    } and external["policy"] == EXTERNAL_RUNTIME_POLICY,
            f"malformed reference external-runtime provenance for {name}")
    for key in ("command_shell", "pari_gp", "csdp"):
        route = external[key]
        require(isinstance(route, dict) and set(route) == {
            "argument_path", "argument_parent", "argument",
            "resolved_executable",
        } and isinstance(route["argument_path"], str) and
                Path(route["argument_path"]).is_absolute() and
                isinstance(route["argument_parent"], dict) and
                isinstance(route["argument"], dict) and
                isinstance(route["resolved_executable"], dict) and
                set(route["resolved_executable"]) == {"path", "sha256", "mode"} and
                Path(route["resolved_executable"]["path"]).is_absolute() and
                require_sha256(route["resolved_executable"]["sha256"],
                               f"{name} {key} executable") and
                is_int(route["resolved_executable"]["mode"]),
                f"malformed reference {key} route for {name}")
        for component_name in ("argument_parent", "argument"):
            component = route[component_name]
            require(isinstance(component, dict) and
                    component.get("kind") in {"symlink", "directory", "file"} and
                    set(component) == ({
                        "path", "kind", "mode", "resolved_path", "target",
                    } if component.get("kind") == "symlink" else {
                        "path", "kind", "mode", "resolved_path",
                    }) and
                    isinstance(component["path"], str) and
                    Path(component["path"]).is_absolute() and
                    is_int(component["mode"]) and
                    isinstance(component["resolved_path"], str) and
                    Path(component["resolved_path"]).is_absolute() and
                    (component.get("kind") != "symlink" or
                     isinstance(component.get("target"), str)),
                    f"malformed reference {key} {component_name} for {name}")
    version = external["pari_gp_version"]
    require(isinstance(version, dict) and set(version) == {"stdout", "sha256"} and
            isinstance(version["stdout"], str) and
            re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+\n", version["stdout"]) and
            hashlib.sha256(version["stdout"].encode()).hexdigest() ==
            version["sha256"], f"malformed PARI/GP version for {name}")
    for key in ("package_archive", "configuration"):
        value = external[key]
        require(isinstance(value, dict) and set(value) == {"path", "sha256"} and
                isinstance(value["path"], str) and Path(value["path"]).is_absolute() and
                require_sha256(value["sha256"], f"{name} {key}"),
                f"malformed reference {key} for {name}")
    for key in ("package_tree", "data_tree"):
        value = external[key]
        require(isinstance(value, dict) and set(value) == {
            "root", "root_mode", "entry_count", "inventory_sha256",
            "inventory_policy",
        } and isinstance(value["root"], str) and Path(value["root"]).is_absolute() and
                is_int(value["root_mode"]) and
                is_int(value["entry_count"]) and
                value["entry_count"] >= 0 and
                require_sha256(value["inventory_sha256"], f"{name} {key}") and
                value["inventory_policy"] ==
                "relative_path_kind_mode_link_target_and_content_v1",
                f"malformed reference {key} for {name}")
    require(external["data_tree"]["root_mode"] == 0o555,
            f"reference PARI/GP data root is writable for {name}")
    package_root = Path(external["package_tree"]["root"])
    require(external["command_shell"]["argument_path"] == "/bin/sh" and
            external["pari_gp"]["argument_path"] ==
            str(package_root / "usr/bin/gp") and
            external["csdp"]["argument_path"] ==
            str(package_root / "usr/bin/csdp") and
            external["csdp"]["argument"]["kind"] == "file" and
            external["csdp"]["resolved_executable"]["mode"] == 0o555 and
            external["configuration"]["path"] ==
            str(package_root / "candle-gprc") and
            external["data_tree"]["root"] ==
            str(package_root / "candle-data") and
            external["data_tree"]["entry_count"] == 0,
            f"reference GP/CSDP package paths are not exact for {name}")
    validate_elf_runtime_structure(
        external["elf_runtime"], [
            external["command_shell"]["resolved_executable"]["path"],
            external["pari_gp"]["resolved_executable"]["path"],
            external["csdp"]["resolved_executable"]["path"],
        ], f"{name} external",
    )
    require(not any(
        fragment in Path(item["path"]).name.lower()
        for item in external["elf_runtime"]["closure"]
        for fragment in CSDP_FORBIDDEN_ELF_FRAGMENTS
    ), f"reference CSDP ELF closure is threaded for {name}")
    source = external["csdp_source_archive"]
    probe_input = external["csdp_probe_input"]
    for value, label in ((source, "CSDP source"),
                         (probe_input, "CSDP probe input")):
        require(isinstance(value, dict) and set(value) == {
            "path", "sha256", "bytes",
        } and isinstance(value["path"], str) and
                Path(value["path"]).is_absolute() and
                require_sha256(value["sha256"], f"{name} {label}") and
                is_int(value["bytes"]) and value["bytes"] > 0,
                f"malformed reference {label} for {name}")
    build = external["csdp_build"]
    require(is_int(external["csdp_bytes"]) and external["csdp_bytes"] > 0 and
            isinstance(build, dict) and set(build) == {
        "receipt", "statement",
    } and isinstance(build["receipt"], dict) and
            set(build["receipt"]) == {"path", "sha256"} and
            isinstance(build["receipt"]["path"], str) and
            Path(build["receipt"]["path"]).is_absolute() and
            require_sha256(build["receipt"]["sha256"],
                           f"{name} CSDP build receipt") and
            validate_csdp_build_statement(
                build["statement"], source, {
                    "bytes": external["csdp_bytes"],
                    "sha256": external["csdp"]["resolved_executable"]["sha256"],
                }, probe_input,
            ), f"malformed reference CSDP build for {name}")
    thread_policy = external["thread_policy"]
    expected_thread_policy = {
        "single_process_solver": True,
        "single_thread_build": True,
        "openmp_enabled": False,
        "native_cpu_flags": False,
        "environment": THREAD_CAP_ENVIRONMENT,
        "forbidden_elf_dependency_name_fragments":
            list(CSDP_FORBIDDEN_ELF_FRAGMENTS),
    }
    require(thread_policy == expected_thread_policy and
            canonical_json_bytes(thread_policy) ==
            canonical_json_bytes(expected_thread_policy),
            f"malformed reference CSDP thread policy for {name}")
    probe = external["probe"]
    probe_source = \
        "echo 'print(default(nbthreads)); print(factorint(15))  \n quit' | gp"
    require(isinstance(probe, dict) and set(probe) == {
        "shell_argv", "environment", "return_code", "stdout",
        "stdout_sha256", "stderr", "stderr_sha256",
    } and is_int(probe["return_code"]) and probe["return_code"] == 0 and
            isinstance(probe["stdout"], str) and
            re.search(r"(?:^|\n)1\n", probe["stdout"]) is not None and
            "[3, 1; 5, 1]" in probe["stdout"] and
            hashlib.sha256(probe["stdout"].encode()).hexdigest() ==
            probe["stdout_sha256"] and
            isinstance(probe["stderr"], str) and
            probe["stderr"] in {"", (
                f"Reading GPRC: {external['configuration']['path']}\n"
                "GPRC Done.\n\n")} and
            hashlib.sha256(probe["stderr"].encode()).hexdigest() ==
            probe["stderr_sha256"] and
            probe["shell_argv"] == [
                external["command_shell"]["argument_path"], "-c", probe_source,
            ] and
            isinstance(probe["environment"], dict) and
            set(probe["environment"]) == {
                "HOME", "PATH", "LC_ALL", "GPRC", "GP_DATA_DIR",
                *THREAD_CAP_ENVIRONMENT,
            } and probe["environment"].get("HOME") == reference["root"] and
            probe["environment"].get("LC_ALL") == "C" and
            probe["environment"].get("PATH") ==
            str(Path(external["pari_gp"]["argument_path"]).parent) and
            probe["environment"].get("GPRC") == external["configuration"]["path"] and
            probe["environment"].get("GP_DATA_DIR") == external["data_tree"]["root"] and
            all(probe["environment"].get(key) == value
                for key, value in THREAD_CAP_ENVIRONMENT.items()),
            f"malformed reference PARI/GP probe for {name}")
    csdp_probe = external["csdp_probe"]
    require(isinstance(csdp_probe, dict) and set(csdp_probe) == {
        "argv_template", "environment", "return_code", "normalized_stdout",
        "normalized_stdout_sha256", "stderr", "stderr_sha256", "solution",
    } and csdp_probe["argv_template"] == [
        external["csdp"]["argument_path"], probe_input["path"],
        "<private-temporary-output>",
    ] and csdp_probe["environment"] == probe["environment"] and
            is_int(csdp_probe["return_code"]) and
            csdp_probe["return_code"] == 0 and
            isinstance(csdp_probe["normalized_stdout"], str) and
            f"{CSDP_PROBE_SUCCESS}\n" in csdp_probe["normalized_stdout"] and
            f"Primal objective value: {CSDP_PROBE_PRIMAL} \n" in
            csdp_probe["normalized_stdout"] and
            f"Dual objective value: {CSDP_PROBE_DUAL} \n" in
            csdp_probe["normalized_stdout"] and
            hashlib.sha256(csdp_probe["normalized_stdout"].encode()).hexdigest() ==
            csdp_probe["normalized_stdout_sha256"] and
            csdp_probe["stderr"] == "" and
            csdp_probe["stderr_sha256"] == hashlib.sha256(b"").hexdigest() and
            isinstance(csdp_probe["solution"], dict) and
            set(csdp_probe["solution"]) == {"bytes", "sha256"} and
            is_int(csdp_probe["solution"]["bytes"]) and
            csdp_probe["solution"]["bytes"] > 0 and
            require_sha256(csdp_probe["solution"]["sha256"],
                           f"{name} CSDP probe solution"),
            f"malformed reference CSDP probe for {name}")
    runtime_environment = fresh["runtime_environment"]
    require(set(runtime_environment) == {
        "HOME", "PATH", "LC_ALL", "GPRC", "GP_DATA_DIR", "HOLLIGHT_DIR",
        "HOLLIGHT_USE_MODULE", "OCAMLRUNPARAM", "CAML_LD_LIBRARY_PATH",
        "OCAML_TOPLEVEL_PATH", "OCAMLFIND_CONF", *THREAD_CAP_ENVIRONMENT,
    } and all(runtime_environment.get(key) == probe["environment"].get(key)
              for key in ("HOME", "PATH", "LC_ALL", "GPRC", "GP_DATA_DIR")) and
            runtime_environment["HOLLIGHT_DIR"] == reference["root"] and
            runtime_environment["HOLLIGHT_USE_MODULE"] == "0" and
            runtime_environment["OCAMLRUNPARAM"] == "l=2000000000" and
            all(isinstance(runtime_environment[key], str) and
                Path(runtime_environment[key]).is_absolute()
                for key in ("CAML_LD_LIBRARY_PATH", "OCAML_TOPLEVEL_PATH",
                            "OCAMLFIND_CONF")),
            f"reference runtime differs from exact environment for {name}")
    require(runtime_environment["CAML_LD_LIBRARY_PATH"] ==
            reference["runtime_library_tree"]["root"] and
            runtime_environment["OCAML_TOPLEVEL_PATH"] ==
            ocamlc["stdlib_directory"] and
            runtime_environment["OCAMLFIND_CONF"] ==
            findlib["configuration"]["path"],
            f"reference OCaml environment mismatch for {name}")

    inputs = plan["input"]
    require(isinstance(inputs, dict) and set(inputs) == {
        "collector", "collector_repository", "manifest",
        "manifest_schema_version", "target", "load_files", "theorem_names",
        "mapping_status", "serializer", "source_mode", "source_contract",
    }, f"malformed v9 reference input contract for {name}")
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
                "support_relative_path", "support_at_head_sha256",
                "support_matches_head",
            } and repository["root"] == str(root) and
            repository["collector_relative_path"] == REFERENCE_VALIDATOR_PATH and
            repository["support_relative_path"] == REFERENCE_PROTOCOL_PATH and
            require_commit(repository["git_head"], f"{name} collector head") and
            repository["git_status"] == [] and
            repository["collector_at_head_sha256"] == validator.identity.sha256 and
            repository["collector_matches_head"] is True and
            repository["support_at_head_sha256"] == protocol.identity.sha256 and
            repository["support_matches_head"] is True and
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


def capture_elf_runtime(
    evidence: dict[str, Any], stage: Path, stager: Stager, label: str,
) -> dict[str, Any]:
    """Retain all authenticated observer inputs and discovered ELF objects."""
    require(not os.path.lexists("/etc/ld.so.preload"),
            f"{label} live /etc/ld.so.preload is not absent")

    def retain_pin(pin: dict[str, Any], archive_path: str,
                   item_label: str, *, require_elf: bool = True) -> dict[str, Any]:
        source = ordinary_file(Path(pin["path"]), item_label)
        if require_elf:
            with source.open("rb") as stream:
                require(stream.read(4) == b"\x7fELF",
                        f"{item_label} is not ELF")
        metadata = source.lstat()
        key = (metadata.st_dev, metadata.st_ino)
        if key in stager.source_keys:
            identity = stable_file_identity(source, item_label)
            retained = {
                "source_path": str(source),
                "retained_by": stager.source_keys[key],
                **identity.as_json(),
            }
        else:
            snapshot = stager.capture(source, archive_path, item_label)
            retained = {
                "source_path": str(snapshot.source_path),
                "archive_path": snapshot.archive_path,
                **snapshot.identity.as_json(),
            }
        require(retained["sha256"] == pin["sha256"],
                f"{item_label} differs from plan")
        return retained

    tools = evidence["tools"]
    for key in ("bash", "ldd"):
        require(tools[key] == executable_route_record(
            Path(tools[key]["argument_path"]), f"{label} ELF observer {key}",
        ), f"live {label} ELF observer {key} route differs")
    loaders = []
    for item in evidence["hardcoded_loader_routes"]:
        path = Path(item["argument_path"])
        if item["status"] == "absent":
            require(not os.path.lexists(path),
                    f"absent {label} ELF loader appeared: {path}")
            loaders.append(dict(item))
            continue
        require(item["route"] == executable_route_record(
            path, f"{label} ELF loader {path}",
        ), f"live {label} ELF loader route differs: {path}")
        loaders.append({
            **item,
            "retained": retain_pin(
                item["route"]["resolved_executable"],
                f"approval/reference-runtime/{label}/loaders/{path.name}",
                f"{label} ELF loader {path}",
            ),
        })
    cache = retain_pin(
        evidence["ld_so_cache"],
        f"approval/reference-runtime/{label}/ld.so.cache",
        f"{label} dynamic-loader cache",
        require_elf=False,
    )
    retained_tools = {
        key: retain_pin(
            tools[key]["resolved_executable"],
            f"approval/reference-runtime/{label}/observer/{key}",
            f"{label} ELF observer {key}",
            require_elf=(key == "bash"),
        ) for key in ("bash", "ldd")
    }
    roots = [
        retain_pin(
            pin,
            f"approval/reference-runtime/{label}/roots/{index:02d}",
            f"{label} ELF requested root {pin['path']}",
        ) for index, pin in enumerate(evidence["requested_roots"], 1)
    ]
    closure = [
        retain_pin(
            pin,
            (f"approval/reference-runtime/{label}/closure/"
             f"{index:02d}-{pin['sha256'][:16]}-{Path(pin['path']).name}"),
            f"{label} ELF dependency {pin['path']}",
        ) for index, pin in enumerate(evidence["closure"], 1)
    ]
    return {
        "policy": evidence["policy"],
        "output_normalization": evidence["output_normalization"],
        "stable_projection_sha256": compact_json_sha256(
            stable_elf_runtime(evidence)),
        "tools": retained_tools,
        "hardcoded_loader_routes": loaders,
        "ld_so_cache": cache,
        "ld_so_preload": evidence["ld_so_preload"],
        "environment": evidence["environment"],
        "requested_roots": roots,
        "closure": closure,
        "observation_count": len(evidence["observations"]),
    }


def capture_reference_external_runtime(
    external: dict[str, Any], stage: Path, stager: Stager,
) -> dict[str, Any]:
    """Retain and reauthenticate the complete shell/GP collection closure."""
    require(external["command_shell"] == executable_route_record(
        Path(external["command_shell"]["argument_path"]), "Sys.command shell",
    ), "live Sys.command shell route differs from reference plans")
    require(external["pari_gp"] == executable_route_record(
        Path(external["pari_gp"]["argument_path"]), "PARI/GP executable",
    ), "live PARI/GP route differs from reference plans")
    require(external["csdp"] == executable_route_record(
        Path(external["csdp"]["argument_path"]), "CSDP executable",
    ) and external["csdp"]["argument"]["kind"] == "file" and
            external["csdp"]["resolved_executable"]["mode"] == 0o555,
            "live CSDP route differs from reference plans")

    package_pin, package_entries = tree_inventory(
        Path(external["package_tree"]["root"]), "PARI/GP package tree",
    )
    data_pin, data_entries = tree_inventory(
        Path(external["data_tree"]["root"]), "PARI/GP optional-data tree",
    )
    require(package_pin == external["package_tree"],
            "live PARI/GP package tree differs from reference plans")
    require(data_pin == external["data_tree"] and not data_entries and
            data_pin["entry_count"] == 0 and data_pin["root_mode"] == 0o555,
            "PARI/GP optional-data tree is not the pinned empty 0555 tree")

    probe_environment = dict(external["probe"]["environment"])
    version = subprocess.run(
        [external["pari_gp"]["argument_path"], "--version-short"],
        env=probe_environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=30, check=False,
    )
    observed_version = {
        "stdout": version.stdout,
        "sha256": hashlib.sha256(version.stdout.encode()).hexdigest(),
    }
    require(version.returncode == 0 and version.stderr == "" and
            observed_version == external["pari_gp_version"],
            "live PARI/GP version differs from reference plans")
    probe = subprocess.run(
        external["probe"]["shell_argv"], env=probe_environment,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        timeout=30, check=False,
    )
    observed_probe = {
        "shell_argv": external["probe"]["shell_argv"],
        "environment": probe_environment,
        "return_code": probe.returncode,
        "stdout": probe.stdout,
        "stdout_sha256": hashlib.sha256(probe.stdout.encode()).hexdigest(),
        "stderr": probe.stderr,
        "stderr_sha256": hashlib.sha256(probe.stderr.encode()).hexdigest(),
    }
    require(observed_probe == external["probe"],
            "live PARI/GP shell probe differs from reference plans")
    build_receipt = ordinary_file(
        Path(external["csdp_build"]["receipt"]["path"]),
        "CSDP build receipt",
    )
    build_statement = parse_json_bytes(
        build_receipt.read_bytes(), "CSDP build receipt",
    )
    require(validate_csdp_build_statement(
        build_statement, external["csdp_source_archive"], {
            "bytes": external["csdp_bytes"],
            "sha256": external["csdp"]["resolved_executable"]["sha256"],
        }, external["csdp_probe_input"],
    ) == external["csdp_build"]["statement"],
            "live CSDP build receipt differs from reference plans")
    with tempfile.TemporaryDirectory(
            prefix="candle-finalizer-csdp-") as directory:
        solution = Path(directory) / "theta1.sol"
        completed_csdp = subprocess.run(
            [external["csdp"]["argument_path"],
             external["csdp_probe_input"]["path"], str(solution)],
            env=external["csdp_probe"]["environment"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=30, check=False,
        )
        solution_identity = stable_file_identity(
            solution, "CSDP probe solution",
        )
        solution_snapshot = stager.capture(
            solution,
            "approval/reference-runtime/csdp-live-probe/solution",
            "CSDP live-probe solution",
        )
        require(solution_snapshot.identity == solution_identity,
                "CSDP live-probe solution changed during capture")
    normalized_csdp = normalize_csdp_probe_stdout(completed_csdp.stdout)
    csdp_stdout_identity = stager.write(
        "approval/reference-runtime/csdp-live-probe/stdout",
        completed_csdp.stdout.encode(),
    )
    csdp_stderr_identity = stager.write(
        "approval/reference-runtime/csdp-live-probe/stderr",
        completed_csdp.stderr.encode(),
    )
    observed_csdp_probe = {
        "argv_template": [
            external["csdp"]["argument_path"],
            external["csdp_probe_input"]["path"],
            "<private-temporary-output>",
        ],
        "environment": external["csdp_probe"]["environment"],
        "return_code": completed_csdp.returncode,
        "normalized_stdout": normalized_csdp,
        "normalized_stdout_sha256": hashlib.sha256(
            normalized_csdp.encode()).hexdigest(),
        "stderr": completed_csdp.stderr,
        "stderr_sha256": hashlib.sha256(
            completed_csdp.stderr.encode()).hexdigest(),
        "solution": solution_identity.as_json(),
    }
    require(observed_csdp_probe == external["csdp_probe"],
            "live CSDP probe differs from reference plans")

    package_root = Path(package_pin["root"])
    retained_entries: list[dict[str, Any]] = []
    package_files: dict[str, Snapshot] = {}
    for entry in package_entries:
        retained = dict(entry)
        if entry["kind"] == "file":
            relative = safe_relative(entry["path"], "PARI/GP package-tree file")
            snapshot = stager.capture(
                package_root / relative,
                f"approval/reference-runtime/package-tree/files/{relative}",
                f"PARI/GP package-tree file {relative}",
            )
            require(snapshot.identity.sha256 == entry["sha256"],
                    f"PARI/GP package file changed during capture: {relative}")
            retained.update({
                "archive_path": snapshot.archive_path,
                "bytes": snapshot.identity.bytes,
            })
            package_files[relative] = snapshot
        retained_entries.append(retained)
    package_post, package_post_entries = tree_inventory(
        package_root, "PARI/GP package tree postflight",
    )
    require(package_post == package_pin and package_post_entries == package_entries,
            "PARI/GP package tree changed during capture")

    archive_path = ordinary_file(
        Path(external["package_archive"]["path"]), "PARI/GP package archive",
    )
    require(stat.S_IMODE(archive_path.lstat().st_mode) == 0o444,
            "PARI/GP package archive mode is not 0444")
    package_archive = stager.capture(
        archive_path, "approval/reference-runtime/package.deb",
        "PARI/GP package archive",
    )
    require(package_archive.identity.sha256 == external["package_archive"]["sha256"],
            "PARI/GP package archive differs from reference plans")

    configuration_path = Path(external["configuration"]["path"])
    require(configuration_path.is_relative_to(package_root),
            "PARI/GP configuration is outside the package tree")
    configuration_relative = configuration_path.relative_to(package_root).as_posix()
    configuration = package_files.get(configuration_relative)
    require(configuration is not None and
            configuration.identity.sha256 == external["configuration"]["sha256"] and
            stat.S_IMODE(configuration_path.lstat().st_mode) == 0o444,
            "retained PARI/GP configuration differs from reference plans")

    gp_path = Path(external["pari_gp"]["resolved_executable"]["path"])
    require(gp_path.is_relative_to(package_root),
            "resolved PARI/GP executable is outside the package tree")
    gp_relative = gp_path.relative_to(package_root).as_posix()
    gp_snapshot = package_files.get(gp_relative)
    require(gp_snapshot is not None and
            gp_snapshot.identity.sha256 ==
            external["pari_gp"]["resolved_executable"]["sha256"],
            "retained PARI/GP executable differs from reference plans")

    def retained_package_file(
        path: str, sha256: str, expected_bytes: int | None, label: str,
    ) -> Snapshot:
        source = Path(path)
        require(source.is_relative_to(package_root),
                f"{label} is outside the package tree")
        relative = source.relative_to(package_root).as_posix()
        snapshot = package_files.get(relative)
        require(snapshot is not None and snapshot.identity.sha256 == sha256 and
                (expected_bytes is None or
                 snapshot.identity.bytes == expected_bytes),
                f"retained {label} differs from reference plans")
        return snapshot

    csdp_snapshot = retained_package_file(
        external["csdp"]["resolved_executable"]["path"],
        external["csdp"]["resolved_executable"]["sha256"],
        external["csdp_bytes"], "CSDP executable",
    )
    csdp_source = retained_package_file(
        external["csdp_source_archive"]["path"],
        external["csdp_source_archive"]["sha256"],
        external["csdp_source_archive"]["bytes"], "CSDP source archive",
    )
    csdp_receipt = retained_package_file(
        external["csdp_build"]["receipt"]["path"],
        external["csdp_build"]["receipt"]["sha256"], None,
        "CSDP build receipt",
    )
    csdp_probe_input = retained_package_file(
        external["csdp_probe_input"]["path"],
        external["csdp_probe_input"]["sha256"],
        external["csdp_probe_input"]["bytes"], "CSDP probe input",
    )

    shell_path = Path(external["command_shell"]["resolved_executable"]["path"])
    shell = stager.capture(
        shell_path, "approval/reference-runtime/shell/resolved-executable",
        "Sys.command shell executable",
    )
    require(shell.identity.sha256 ==
            external["command_shell"]["resolved_executable"]["sha256"],
            "retained Sys.command shell differs from reference plans")

    elf_runtime = capture_elf_runtime(
        external["elf_runtime"], stage, stager, "external",
    )

    inventory_identity = stager.write(
        "approval/reference-runtime/package-tree/inventory.json",
        canonical_json_bytes({
            "schema": "candle-reference-pari-gp-package-tree-v1",
            "pin": package_pin, "entries": retained_entries,
        }),
    )
    return {
        "policy": external["policy"],
        "plan_projection_sha256": compact_json_sha256(external),
        "package_archive": {
            "source_path": str(package_archive.source_path),
            "archive_path": package_archive.archive_path,
            **package_archive.identity.as_json(),
        },
        "package_tree": {
            "pin": package_pin,
            "inventory_archive_path":
                "approval/reference-runtime/package-tree/inventory.json",
            **inventory_identity.as_json(),
        },
        "configuration": {
            "source_path": str(configuration.source_path),
            "archive_path": configuration.archive_path,
            **configuration.identity.as_json(),
        },
        "pari_gp": {
            "source_path": str(gp_snapshot.source_path),
            "archive_path": gp_snapshot.archive_path,
            **gp_snapshot.identity.as_json(),
        },
        "csdp": {
            "source_path": str(csdp_snapshot.source_path),
            "archive_path": csdp_snapshot.archive_path,
            **csdp_snapshot.identity.as_json(),
        },
        "csdp_source_archive": {
            "source_path": str(csdp_source.source_path),
            "archive_path": csdp_source.archive_path,
            **csdp_source.identity.as_json(),
        },
        "csdp_build_receipt": {
            "source_path": str(csdp_receipt.source_path),
            "archive_path": csdp_receipt.archive_path,
            **csdp_receipt.identity.as_json(),
        },
        "csdp_probe_input": {
            "source_path": str(csdp_probe_input.source_path),
            "archive_path": csdp_probe_input.archive_path,
            **csdp_probe_input.identity.as_json(),
        },
        "command_shell": {
            "source_path": str(shell.source_path),
            "archive_path": shell.archive_path,
            **shell.identity.as_json(),
        },
        "elf_runtime": elf_runtime,
        "data_tree": data_pin,
        "version": observed_version,
        "probe": observed_probe,
        "csdp_build_statement": build_statement,
        "thread_policy": external["thread_policy"],
        "csdp_probe": observed_csdp_probe,
        "csdp_probe_artifacts": {
            "solution": {
                "archive_path": solution_snapshot.archive_path,
                **solution_snapshot.identity.as_json(),
            },
            "stdout": {
                "archive_path":
                    "approval/reference-runtime/csdp-live-probe/stdout",
                **csdp_stdout_identity.as_json(),
            },
            "stderr": {
                "archive_path":
                    "approval/reference-runtime/csdp-live-probe/stderr",
                **csdp_stderr_identity.as_json(),
            },
        },
    }


def capture_reference_core_runtime(
    reference: dict[str, Any], stage: Path, stager: Stager,
) -> dict[str, Any]:
    """Retain and reauthenticate the complete HOL/OCaml runtime projection."""
    def capture_pin(pin: dict[str, Any], archive_path: str,
                    label: str) -> dict[str, Any]:
        source = ordinary_file(Path(pin["path"]), label)
        metadata = source.lstat()
        key = (metadata.st_dev, metadata.st_ino)
        if key in stager.source_keys:
            identity = stable_file_identity(source, label)
            require(identity.sha256 == pin["sha256"],
                    f"live {label} differs from reference plans")
            return {
                "source_path": str(source),
                "retained_by": stager.source_keys[key],
                **identity.as_json(),
            }
        snapshot = stager.capture(source, archive_path, label)
        require(snapshot.identity.sha256 == pin["sha256"],
                f"live {label} differs from reference plans")
        return {
            "source_path": str(snapshot.source_path),
            "archive_path": snapshot.archive_path,
            **snapshot.identity.as_json(),
        }

    tree_cache: dict[str, dict[str, Any]] = {}
    def capture_tree(pin: dict[str, Any], index: int,
                     label: str) -> dict[str, Any]:
        root = Path(pin["root"])
        if str(root) in tree_cache:
            require(tree_cache[str(root)]["pin"] == pin,
                    f"conflicting duplicate {label} tree pin")
            return tree_cache[str(root)]
        observed, entries = tree_inventory(root, label)
        require(observed == pin, f"live {label} differs from reference plans")
        retained = []
        for entry_index, entry in enumerate(entries, 1):
            value = dict(entry)
            if entry["kind"] == "file":
                relative = safe_relative(entry["path"], f"{label} file")
                retained_file = capture_pin(
                    {"path": str(root / relative), "sha256": entry["sha256"]},
                    ("approval/reference-runtime/core/trees/"
                     f"{index:02d}/files/{relative}"),
                    f"{label} file {relative}",
                )
                value["retention"] = retained_file
            elif entry["kind"] == "symlink" and "resolved_sha256" in entry:
                resolved = Path(entry["resolved_path"])
                retained_file = capture_pin(
                    {"path": str(resolved),
                     "sha256": entry["resolved_sha256"]},
                    ("approval/reference-runtime/core/trees/"
                     f"{index:02d}/resolved/{entry_index:06d}-{resolved.name}"),
                    f"{label} resolved symlink {entry['path']}",
                )
                value["resolved_retention"] = retained_file
            retained.append(value)
        post, post_entries = tree_inventory(root, f"{label} postflight")
        require(post == observed and post_entries == entries,
                f"{label} changed during capture")
        inventory_path = (
            f"approval/reference-runtime/core/trees/{index:02d}/inventory.json")
        inventory = stager.write(
            inventory_path,
            canonical_json_bytes({
                "schema": "candle-reference-runtime-tree-v1",
                "pin": pin, "entries": retained,
            }),
        )
        result = {
            "pin": pin, "inventory_archive_path": inventory_path,
            **inventory.as_json(),
        }
        tree_cache[str(root)] = result
        return result

    files = {}
    for index, key in enumerate((
            "runtime_executable", "runtime_interpreter", "runtime_stublib",
            "hol_ml"), 1):
        files[key] = capture_pin(
            reference[key],
            f"approval/reference-runtime/core/files/{index:02d}-{key}",
            key.replace("_", " "),
        )
    ocamlc = dict(reference["ocamlc"])
    files["ocamlc"] = capture_pin(
        {key: ocamlc[key] for key in ("path", "sha256")},
        "approval/reference-runtime/core/files/05-ocamlc", "OCaml compiler",
    )
    findlib = reference["findlib"]
    files["findlib_executable"] = capture_pin(
        findlib["executable"],
        "approval/reference-runtime/core/files/06-ocamlfind", "findlib executable",
    )
    files["findlib_configuration"] = capture_pin(
        findlib["configuration"],
        "approval/reference-runtime/core/files/07-ocamlfind-conf",
        "findlib configuration",
    )
    files["generated_boot_files"] = [
        capture_pin(
            pin,
            f"approval/reference-runtime/core/boot/{index:02d}-{Path(pin['path']).name}",
            f"generated boot file {Path(pin['path']).name}",
        ) for index, pin in enumerate(reference["generated_boot_files"], 1)
    ]
    files["runtime_stub_files"] = [
        capture_pin(
            pin,
            f"approval/reference-runtime/core/stubs/{index:02d}-{Path(pin['path']).name}",
            f"runtime stub {Path(pin['path']).name}",
        ) for index, pin in enumerate(reference["runtime_stub_files"], 1)
    ]
    elf_runtime = capture_elf_runtime(
        reference["elf_runtime"], stage, stager, "core",
    )
    tree_pins = [reference["runtime_library_tree"],
                 reference["ocaml_library_tree"],
                 *findlib["package_roots"]]
    trees = [capture_tree(pin, index, f"reference runtime tree {index}")
             for index, pin in enumerate(tree_pins, 1)]
    projection = {
        key: reference[key] for key in (
            "runtime_executable", "runtime_interpreter", "runtime_stublib",
            "runtime_library_tree", "runtime_stub_files", "elf_runtime",
            "ocamlc", "findlib", "hol_ml", "generated_boot_files",
            "ocaml_library_tree")
    }
    return {
        "plan_projection_sha256": compact_json_sha256(projection),
        "files": files, "trees": trees, "elf_runtime": elf_runtime,
    }


def validate_candidate_identity_projection(
    candidate: dict[str, Any], target: dict[str, Any],
    expected_identity: dict[str, Any], serializer_sha256: str,
) -> None:
    name = target["name"]
    require(candidate.get("schema") == REFERENCE_CANDIDATE_SCHEMA,
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
    stage: Path, validator: Snapshot, protocol: Snapshot, regression: Snapshot,
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
        "runtime_root": replay_runtime["root"],
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
        raise ValidationError("captured v9 reference replay could not run") from error
    expected_stdout = f"reference candidate replay PASS: {len(replays)}\n".encode()
    require(completed.returncode == 0 and completed.stdout == expected_stdout and
            completed.stderr == b"",
            "captured v9 reference candidate replay failed")
    return {
        "validator": {
            "committed_archive_path": validator.archive_path,
            "executed_archive_path": replay_runtime["validator"],
            **validator.identity.as_json(),
        },
        "protocol": {
            "committed_archive_path": protocol.archive_path,
            "executed_archive_path": replay_runtime["protocol"],
            **protocol.identity.as_json(),
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


def authenticate_collection_contract(
    contract: dict[str, Any], reference_policy: dict[str, Any],
    inventory: dict[str, Any], trusted_project_root: Path,
    trusted_project_head: str, stage: Path, stager: Stager,
) -> dict[str, Any]:
    """Authenticate the controller, repositories, and launch-time runtimes."""
    def retain_live(path: Path, archive_path: str, label: str) -> dict[str, Any]:
        source = ordinary_file(path, label)
        metadata = source.lstat()
        key = (metadata.st_dev, metadata.st_ino)
        if key in stager.source_keys:
            identity = stable_file_identity(source, label)
            return {
                "source_path": str(source),
                "retained_by": stager.source_keys[key],
                **identity.as_json(),
            }
        snapshot = stager.capture(source, archive_path, label)
        return {
            "source_path": str(snapshot.source_path),
            "archive_path": snapshot.archive_path,
            **snapshot.identity.as_json(),
        }

    project = contract["project"]
    require(isinstance(project, dict) and set(project) == {
        "root", "git_head", "controller",
    } and isinstance(project["root"], str) and
            Path(project["root"]).is_absolute(),
            "malformed collection project contract")
    project_root = Path(project["root"])
    require(project["git_head"] == COLLECTION_PROJECT_HEAD,
            "collection controller is not the authorized launch commit")
    validate_git_checkout(
        project_root, COLLECTION_PROJECT_HEAD,
        "collection controller checkout",
    )
    try:
        ancestry = subprocess.run(
            git_command(
                trusted_project_root, "merge-base", "--is-ancestor",
                COLLECTION_PROJECT_HEAD, trusted_project_head,
            ),
            env=git_environment(), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=120, check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValidationError(
            "collection/finalizer ancestry check could not run",
        ) from error
    require(ancestry.returncode == 0 and ancestry.stdout == b"" and
            ancestry.stderr == b"",
            "collection launch commit is not an ancestor of the finalizer")
    controller_record, controller_source = committed_file_at(
        project_root, project["git_head"], COLLECTION_CONTROLLER_PATH,
        "100755", "collection controller",
    )
    require(project["controller"] == controller_record and
            controller_record["bytes"] == COLLECTION_CONTROLLER_BYTES and
            controller_record["sha256"] == COLLECTION_CONTROLLER_SHA256,
            "collection controller does not match its committed project")
    controller = contract["controller"]
    require(isinstance(controller, dict) and set(controller) == {
        "path", "sha256", "bytes", "python", "git",
    } and controller["path"] ==
            str(project_root / COLLECTION_CONTROLLER_PATH) and
            {key: controller[key] for key in ("path", "bytes", "sha256")} == {
                "path": str(project_root / COLLECTION_CONTROLLER_PATH),
                "bytes": controller_record["bytes"],
                "sha256": controller_record["sha256"],
            }, "collection controller projection is not exact")
    controller_identity = stager.write(
        "approval/reference-collection/controller.py", controller_source,
    )
    require(controller_identity.as_json() == {
        key: controller_record[key] for key in ("bytes", "sha256")
    }, "retained collection controller differs")

    python = controller["python"]
    git_tool = controller["git"]
    require(isinstance(python, dict) and set(python) == {
        "argument_path", "path", "bytes", "sha256",
    } and python == runtime_file_record(
        Path(python["argument_path"]), "collection Python",
    ), "collection Python runtime changed or is malformed")
    require(isinstance(git_tool, dict) and set(git_tool) == {
        "path", "bytes", "sha256",
    } and git_tool["path"] == str(GIT_REQUESTED_PATH) and
            {"path": str(GIT_REQUESTED_PATH), **stable_file_identity(
                GIT_REQUESTED_PATH, "collection Git",
            ).as_json()} == git_tool,
            "collection Git runtime changed or is malformed")
    python_retained = retain_live(
        Path(python["path"]), "approval/reference-collection/runtime/python",
        "collection Python",
    )
    git_retained = retain_live(
        GIT_REQUESTED_PATH, "approval/reference-collection/runtime/git",
        "collection Git",
    )
    require({key: python_retained[key] for key in ("bytes", "sha256")} == {
        key: python[key] for key in ("bytes", "sha256")
    } and {key: git_retained[key] for key in ("bytes", "sha256")} == {
        key: git_tool[key] for key in ("bytes", "sha256")
    }, "retained collection controller runtime differs")

    candle = contract["candle"]
    require(isinstance(candle, dict) and set(candle) == {
        "root", "git_head", *COLLECTION_CANDLE_PATHS,
    } and isinstance(candle["root"], str) and
            Path(candle["root"]).is_absolute(),
            "malformed collection Candle contract")
    candle_root = Path(candle["root"])
    retained_candle = {}
    for key, (relative, mode) in COLLECTION_CANDLE_PATHS.items():
        record, source = committed_file_at(
            candle_root, candle["git_head"], relative, mode,
            f"collection Candle {key}",
        )
        require(candle[key] == record,
                f"collection Candle {key} does not match its commit")
        identity = stager.write(
            f"approval/reference-collection/candle/{relative}", source,
        )
        require(identity.as_json() == {
            field: record[field] for field in ("bytes", "sha256")
        }, f"retained collection Candle {key} differs")
        retained_candle[key] = {
            "archive_path": f"approval/reference-collection/candle/{relative}",
            **identity.as_json(),
        }

    reference = contract["reference"]
    require(isinstance(reference, dict) and set(reference) == {
        "root", "git_head", "source_policy",
    } and isinstance(reference["root"], str) and
            Path(reference["root"]).is_absolute() and
            COMMIT_RE.fullmatch(reference["git_head"]) is not None and
            reference["source_policy"] == reference_policy,
            "malformed or unauthorized collection reference contract")
    reference_root = Path(reference["root"])
    reference_head = reference["git_head"]
    require(reference_head == reference_policy["exact_source_reference_commit"],
            "collection reference head differs from approved exact source")
    validate_git_checkout(
        reference_root, reference_head, "collection reference checkout",
    )
    historical_head = reference_policy["historical_upstream_commit"]
    parent = git_bytes(
        reference_root, "rev-parse", "--verify", f"{reference_head}^{{commit}}^",
    ).decode("utf-8", errors="strict").strip()
    require(parent == historical_head,
            "exact reference is not a direct child of the historical commit")
    changed_lines = git_bytes(
        reference_root, "diff", "--name-status", "--no-renames",
        "--no-ext-diff", "--no-textconv",
        historical_head, reference_head, "--",
    ).decode("utf-8", errors="strict").splitlines()
    expected_delta_paths = sorted(
        value["path"] for value in reference_policy["compatibility_deltas"])
    require(changed_lines == [f"M\t{path}" for path in expected_delta_paths],
            "exact reference commit has an unauthorized source delta")

    selected_hashes: dict[str, str] = {}
    for target in inventory["targets"]:
        for relative, sha256 in target["load_file_sha256"].items():
            previous = selected_hashes.setdefault(relative, sha256)
            require(previous == sha256,
                    f"conflicting selected reference hash for {relative}")
    require(len(selected_hashes) == inventory["source_count"] == 66,
            "collection reference source inventory is not exact")
    retained_sources = {}
    for index, (relative, expected_sha256) in enumerate(
            sorted(selected_hashes.items()), 1):
        record, committed = committed_file_at(
            reference_root, reference_head, relative, "100644",
            f"collection reference source {relative}",
        )
        require(record["sha256"] == expected_sha256,
                f"committed reference source differs for {relative}")
        live = ordinary_file(
            reference_root / relative, f"live reference source {relative}",
        )
        require(stable_file_identity(
            live, f"live reference source {relative}",
        ) == bytes_identity(committed),
                f"live reference source differs from commit for {relative}")
        archive_path = (
            f"approval/reference-collection/reference-sources/{index:02d}/"
            f"{relative}"
        )
        identity = stager.write(archive_path, committed)
        retained_sources[relative] = {
            "archive_path": archive_path, **identity.as_json(),
        }

    retained_deltas = []
    for index, delta in enumerate(reference_policy["compatibility_deltas"], 1):
        relative = delta["path"]
        historical_record, historical = committed_file_at(
            reference_root, historical_head, relative, "100644",
            f"historical reference delta {relative}",
        )
        selected_record, selected = committed_file_at(
            reference_root, reference_head, relative, "100644",
            f"selected reference delta {relative}",
        )
        require(historical_record["sha256"] == delta["historical_sha256"] and
                selected_record["sha256"] == delta["selected_sha256"],
                f"reference compatibility delta differs for {relative}")
        live = ordinary_file(
            reference_root / relative, f"live selected delta {relative}",
        )
        require(stable_file_identity(
            live, f"live selected delta {relative}",
        ) == bytes_identity(selected),
                f"live selected reference delta differs for {relative}")
        historical_archive = (
            "approval/reference-collection/reference-deltas/"
            f"{index:02d}-historical-{Path(relative).name}"
        )
        historical_identity = stager.write(historical_archive, historical)
        selected_capture = retained_sources.get(relative)
        if selected_capture is None:
            selected_archive = (
                "approval/reference-collection/reference-deltas/"
                f"{index:02d}-selected-{Path(relative).name}"
            )
            selected_identity = stager.write(selected_archive, selected)
            selected_capture = {
                "archive_path": selected_archive, **selected_identity.as_json(),
            }
        retained_deltas.append({
            "path": relative,
            "historical": {
                "archive_path": historical_archive,
                **historical_identity.as_json(),
            },
            "selected": selected_capture,
        })

    deadlines = contract["deadlines"]
    require(isinstance(deadlines, dict) and set(deadlines) == {
        "collection_wall_seconds", "target_wall_seconds",
        "validation_wall_seconds",
    } and is_int(deadlines["collection_wall_seconds"]) and
            deadlines["collection_wall_seconds"] > 0 and
            is_int(deadlines["target_wall_seconds"]) and
            deadlines["target_wall_seconds"] >=
            deadlines["collection_wall_seconds"] + 30 and
            is_int(deadlines["validation_wall_seconds"]) and
            deadlines["validation_wall_seconds"] > 0,
            "malformed collection deadlines")

    runtimes = contract["runtime"]
    require(isinstance(runtimes, dict) and set(runtimes) == {
        "runtime", "runtime_stublib", "ocamlc", "ocamlfind",
    }, "malformed collection core-runtime contract")
    retained_runtimes = {}
    for key, record in sorted(runtimes.items()):
        require(isinstance(record, dict) and set(record) == {
            "argument_path", "path", "bytes", "sha256",
        } and record == runtime_file_record(
            Path(record["argument_path"]), f"collection {key}",
        ), f"collection {key} changed or is malformed")
        retained = retain_live(
            Path(record["path"]),
            f"approval/reference-collection/runtime/{key}",
            f"collection {key}",
        )
        require({field: retained[field] for field in ("bytes", "sha256")} == {
            field: record[field] for field in ("bytes", "sha256")
        }, f"retained collection {key} differs")
        retained_runtimes[key] = retained

    external = contract["external_runtime"]
    require(isinstance(external, dict) and set(external) == {
        "policy", "command_shell", "pari_gp", "csdp", "package_archive",
        "package_tree", "configuration", "data_tree", "csdp_source_archive",
        "csdp_build", "csdp_probe_input", "thread_policy", "csdp_probe",
        "runtime_environment",
    } and external["policy"] == EXTERNAL_RUNTIME_POLICY,
            "malformed collection external-runtime contract")
    for key in ("command_shell", "pari_gp", "csdp", "package_archive",
                "configuration", "csdp_source_archive", "csdp_probe_input"):
        record = external[key]
        require(isinstance(record, dict) and set(record) == {
            "argument_path", "path", "bytes", "sha256",
        } and is_int(record["bytes"]) and record["bytes"] > 0 and
                record == runtime_file_record(
            Path(record["argument_path"]), f"collection external {key}",
        ), f"collection external {key} changed or is malformed")
    for key, label in (
        ("package_tree", "collection PARI/GP package tree"),
        ("data_tree", "collection PARI/GP optional-data tree"),
    ):
        pin, _ = tree_inventory(Path(external[key]["root"]), label)
        require(is_int(external[key].get("root_mode")) and
                is_int(external[key].get("entry_count")) and
                external[key] == pin,
                f"{label} changed or is malformed")
    build = external["csdp_build"]
    require(isinstance(build, dict) and set(build) == {
        "receipt", "statement",
    } and isinstance(build["receipt"], dict) and
            set(build["receipt"]) == {
                "argument_path", "path", "bytes", "sha256",
            } and is_int(build["receipt"]["bytes"]) and
            build["receipt"]["bytes"] > 0 and
            build["receipt"] == runtime_file_record(
                Path(build["receipt"]["argument_path"]),
                "collection CSDP build receipt",
            ) and validate_csdp_build_statement(
                build["statement"], external["csdp_source_archive"],
                external["csdp"], external["csdp_probe_input"],
            ), "collection CSDP build contract changed or is malformed")
    package_root = Path(external["package_tree"]["root"])
    expected_thread_policy = {
        "single_process_solver": True,
        "single_thread_build": True,
        "openmp_enabled": False,
        "native_cpu_flags": False,
        "environment": THREAD_CAP_ENVIRONMENT,
        "forbidden_elf_dependency_name_fragments":
            list(CSDP_FORBIDDEN_ELF_FRAGMENTS),
    }
    require(external["data_tree"]["root_mode"] == 0o555 and
            external["data_tree"]["entry_count"] == 0 and
            external["command_shell"]["argument_path"] == "/bin/sh" and
            external["pari_gp"]["argument_path"] ==
            str(package_root / "usr/bin/gp") and
            external["csdp"]["argument_path"] ==
            str(package_root / "usr/bin/csdp") and
            stat.S_IMODE(Path(external["csdp"]["path"]).lstat().st_mode) ==
            0o555 and
            external["configuration"]["argument_path"] ==
            str(package_root / "candle-gprc") and
            external["csdp_source_archive"]["argument_path"] ==
            str(package_root / "candle-csdp-source.tar.gz") and
            external["csdp_build"]["receipt"]["argument_path"] ==
            str(package_root / "candle-csdp-build.json") and
            external["csdp_probe_input"]["argument_path"] ==
            str(package_root / "candle-csdp-theta1.dat-s") and
            external["thread_policy"] == expected_thread_policy and
            canonical_json_bytes(external["thread_policy"]) ==
            canonical_json_bytes(expected_thread_policy) and
            external["runtime_environment"] == {
                "PATH": str(Path(external["pari_gp"]["argument_path"]).parent),
                "GPRC": external["configuration"]["path"],
                "GP_DATA_DIR": external["data_tree"]["root"],
                **THREAD_CAP_ENVIRONMENT,
            }, "collection external-runtime environment is not exact")
    csdp_probe = external["csdp_probe"]
    require(isinstance(csdp_probe, dict) and set(csdp_probe) == {
        "argv_template", "environment", "return_code", "normalized_stdout",
        "normalized_stdout_sha256", "stderr", "stderr_sha256", "solution",
    } and csdp_probe["argv_template"] == [
        external["csdp"]["argument_path"],
        external["csdp_probe_input"]["argument_path"],
        "<private-temporary-output>",
    ] and csdp_probe["environment"] == {
        "HOME": reference["root"], "LC_ALL": "C",
        **external["runtime_environment"],
    } and is_int(csdp_probe["return_code"]) and
            csdp_probe["return_code"] == 0 and
            isinstance(csdp_probe["normalized_stdout"], str) and
            hashlib.sha256(csdp_probe["normalized_stdout"].encode()).hexdigest() ==
            csdp_probe["normalized_stdout_sha256"] and
            f"{CSDP_PROBE_SUCCESS}\n" in csdp_probe["normalized_stdout"] and
            f"Primal objective value: {CSDP_PROBE_PRIMAL} \n" in
            csdp_probe["normalized_stdout"] and
            f"Dual objective value: {CSDP_PROBE_DUAL} \n" in
            csdp_probe["normalized_stdout"] and
            csdp_probe["stderr"] == "" and
            csdp_probe["stderr_sha256"] == hashlib.sha256(b"").hexdigest() and
            isinstance(csdp_probe["solution"], dict) and
            set(csdp_probe["solution"]) == {"bytes", "sha256"} and
            is_int(csdp_probe["solution"]["bytes"]) and
            csdp_probe["solution"]["bytes"] > 0 and
            require_sha256(csdp_probe["solution"]["sha256"],
                           "collection CSDP probe solution"),
            "malformed collection CSDP probe")
    oracle = contract["elf_oracle"]
    require(isinstance(oracle, dict) and set(oracle) == {
        "policy", "output_normalization", "tools",
        "hardcoded_loader_routes", "ld_so_cache", "ld_so_preload",
        "environment",
    } and oracle["policy"] ==
            "authenticated_explicit_bash_ldd_closure_v1" and
            oracle["output_normalization"] ==
            "strict_recognized_lines_replace_only_aslr_addresses_v1" and
            oracle["environment"] == {
                "PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C",
            } and oracle["ld_so_preload"] == {
                "path": "/etc/ld.so.preload", "status": "absent",
            } and not os.path.lexists("/etc/ld.so.preload"),
            "malformed collection ELF observer contract")
    require(isinstance(oracle["tools"], dict) and
            set(oracle["tools"]) == {"bash", "ldd"},
            "malformed collection ELF observer tools")
    for key, path in (("bash", "/bin/bash"), ("ldd", "/usr/bin/ldd")):
        require(oracle["tools"][key] == executable_route_record(
            Path(path), f"collection ELF observer {key}",
        ), f"collection ELF observer {key} changed")
    loader_paths = (
        "/lib/ld-linux.so.2", "/lib64/ld-linux-x86-64.so.2",
        "/libx32/ld-linux-x32.so.2",
    )
    require(isinstance(oracle["hardcoded_loader_routes"], list) and
            len(oracle["hardcoded_loader_routes"]) == len(loader_paths),
            "malformed collection ELF loader routes")
    for expected, loader in zip(
            loader_paths, oracle["hardcoded_loader_routes"]):
        require(isinstance(loader, dict) and
                loader.get("argument_path") == expected and
                loader.get("status") in {"absent", "present"},
                "malformed collection ELF loader route")
        if loader["status"] == "absent":
            require(set(loader) == {"argument_path", "status"} and
                    not os.path.lexists(expected),
                    "absent collection ELF loader changed")
        else:
            require(set(loader) == {"argument_path", "status", "route"} and
                    loader["route"] == executable_route_record(
                        Path(expected), f"collection ELF loader {expected}",
                    ), "present collection ELF loader changed")
    cache_identity = stable_file_identity(
        Path("/etc/ld.so.cache"), "collection dynamic-loader cache",
    )
    require(oracle["ld_so_cache"] == {
        "path": "/etc/ld.so.cache", "sha256": cache_identity.sha256,
    }, "collection dynamic-loader cache changed")
    return {
        "controller": {
            "archive_path": "approval/reference-collection/controller.py",
            **controller_identity.as_json(),
        },
        "controller_runtime": {
            "python": python_retained,
            "git": git_retained,
        },
        "candle": retained_candle,
        "reference": {
            "root": str(reference_root), "git_head": reference_head,
            "historical_upstream_commit": historical_head,
            "sources": retained_sources,
            "compatibility_deltas": retained_deltas,
        },
        "runtime": retained_runtimes,
    }


def capture_collection_evidence(
    approval: dict[str, Any], root: Path, manifest: dict[str, Any],
    trusted_project_root: Path, trusted_project_head: str,
    stage: Path, stager: Stager,
) -> tuple[
    dict[str, Any], dict[tuple[int, int], dict[str, Any]], dict[str, Any], Path,
]:
    evidence = approval["collection_evidence"]
    require(isinstance(evidence, dict) and set(evidence) ==
            COLLECTION_EVIDENCE_KEYS,
            "malformed reference collection evidence")
    captured: dict[str, Snapshot] = {}
    source_paths: dict[str, Path] = {}
    for name in sorted(COLLECTION_EVIDENCE_KEYS):
        _, path, expected = validate_root_file_reference(
            evidence[name], root, f"reference collection {name}")
        source_paths[name] = path
        snapshot = stager.capture(
            path, f"approval/reference-collection/{name}.json",
            f"reference collection {name}",
        )
        require(snapshot.identity == expected,
                f"reference collection {name} bytes differ")
        captured[name] = snapshot
    require(source_paths["contract"].name == "collection-contract.json" and
            source_paths["receipt"].name == "receipt.json" and
            source_paths["contract"].parent == source_paths["receipt"].parent,
            "reference collection evidence is not one exact controller root")
    collection_root = source_paths["contract"].parent
    contract = snapshot_json(
        stage, captured["contract"], "reference collection contract")
    receipt = snapshot_json(
        stage, captured["receipt"], "reference collection receipt")
    require(isinstance(contract, dict) and set(contract) == {
        "schema", "kind", "approval_status", "promotion_allowed",
        "sweep_count", "target_count", "total_target_runs", "source_mode",
            "project", "candle", "reference", "runtime", "external_runtime",
            "elf_oracle",
            "deadlines", "inventory", "controller",
    } and all(is_int(contract[field]) for field in (
        "schema", "sweep_count", "target_count", "total_target_runs",
    )) and contract["schema"] == 4 and
            contract["kind"] ==
            "candle-great100-two-sweep-reference-collection" and
            contract["approval_status"] ==
            "candidate_collection_only_unapproved" and
            contract["promotion_allowed"] is False and
            contract["sweep_count"] == 2 and contract["target_count"] == 65 and
            contract["total_target_runs"] == 130 and
            contract["source_mode"] == "manifest-exact",
            "malformed reference collection contract")
    inventory = contract["inventory"]
    targets = manifest["targets"]
    inventory_targets = []
    inventory_sources: set[str] = set()
    inventory_requests = 0
    for index, target in enumerate(targets, 1):
        load_files = target["load_files"]
        theorem_names = [
            theorem["name"]
            for theorem in target["fingerprint_request"]["theorems"]
        ]
        inventory_sources.update(load_files)
        inventory_requests += len(theorem_names)
        inventory_targets.append({
            "index": index, "name": target["name"],
            "load_files": load_files,
            "load_file_sha256": {
                relative: target["load_file_sha256"][relative]
                for relative in load_files
            },
            "theorem_names": theorem_names,
        })
    expected_inventory = {
        "target_count": 65, "source_count": len(inventory_sources),
        "request_count": inventory_requests, "targets": inventory_targets,
    }
    require(expected_inventory["source_count"] == 66 and
            expected_inventory["request_count"] == 97 and
            inventory == expected_inventory and
            canonical_json_bytes(inventory) ==
            canonical_json_bytes(expected_inventory),
            "reference collection inventory differs from manifest")
    authenticated_contract = authenticate_collection_contract(
        contract, approval["reference_policy"], inventory,
        trusted_project_root, trusted_project_head, stage, stager,
    )
    require(isinstance(receipt, dict) and set(receipt) == {
        "schema", "kind", "contract_sha256", "contract", "sweep_count",
        "target_count", "total_target_runs", "completed_target_runs",
        "pending_target_runs", "failure_attempt_count", "failures",
        "publication_interruptions", "outcome", "closed", "approval_status",
        "promotion_allowed", "sweeps",
    } and all(is_int(receipt[field]) for field in (
        "schema", "sweep_count", "target_count", "total_target_runs",
        "completed_target_runs", "pending_target_runs",
        "failure_attempt_count",
    )) and receipt["schema"] == 1 and
            receipt["kind"] ==
            "candle-great100-two-sweep-reference-receipt" and
            receipt["contract_sha256"] == compact_json_sha256(contract) and
            isinstance(receipt["contract"], dict) and
            receipt["contract"].get("path") == "collection-contract.json" and
            is_int(receipt["contract"].get("bytes")) and
            receipt["contract"].get("bytes") == captured["contract"].identity.bytes and
            receipt["contract"].get("sha256") ==
            captured["contract"].identity.sha256 and
            receipt["sweep_count"] == 2 and receipt["target_count"] == 65 and
            receipt["total_target_runs"] == 130 and
            receipt["completed_target_runs"] == 130 and
            receipt["pending_target_runs"] == 0 and
            receipt["outcome"] == "complete" and receipt["closed"] is True and
            receipt["approval_status"] == "candidates_unapproved" and
            receipt["promotion_allowed"] is False and
            receipt["failure_attempt_count"] == 0 and
            receipt["failures"] == [] and
            receipt["publication_interruptions"] == [],
            "reference collection receipt is not closed and exact")
    sweeps = receipt["sweeps"]
    require(isinstance(sweeps, list) and len(sweeps) == 2,
            "reference collection receipt lacks two sweeps")
    successes: dict[tuple[int, int], dict[str, Any]] = {}
    for sweep_index, sweep in enumerate(sweeps, 1):
        require(isinstance(sweep, dict) and set(sweep) == {
            "sweep", "target_count", "completed_count", "pending_count",
            "targets",
        } and all(is_int(sweep[field]) for field in (
            "sweep", "target_count", "completed_count", "pending_count",
        )) and sweep["sweep"] == sweep_index and
                sweep["target_count"] == 65 and
                sweep["completed_count"] == 65 and
                sweep["pending_count"] == 0 and
                isinstance(sweep["targets"], list) and
                len(sweep["targets"]) == 65,
                "malformed closed reference sweep")
        for target_index, (target, row) in enumerate(
                zip(targets, sweep["targets"]), 1):
            require(isinstance(row, dict) and set(row) == {
                "index", "name", "state", "attempt_count", "success",
                "attempts",
            } and is_int(row["index"]) and is_int(row["attempt_count"]) and
                    row["index"] == target_index and
                    row["name"] == target["name"] and
                    row["state"] == "complete" and
                    row["attempt_count"] == 1 and
                    row["attempts"] == [{
                        "attempt": "attempt-0001", "state": "complete",
                    }] and
                    isinstance(row["success"], dict),
                    "malformed reference collection target success")
            success = row["success"]
            require(set(success) == {
                "attempt", "receipt_path", "receipt", "session_nonce",
                "artifacts",
            } and success["attempt"] == "attempt-0001" and
                    success["receipt_path"] ==
                    (f"sweep-{sweep_index}/target-{target_index:03d}/"
                     f"{success['attempt']}/success.json") and
                    require_nonce(success["session_nonce"],
                                  "collection success nonce") ==
                    success["session_nonce"] and
                    isinstance(success["receipt"], dict) and
                    isinstance(success["artifacts"], dict),
                    "malformed aggregate collection success")
            successes[(sweep_index, target_index)] = success
    collection_capture = {
        name: {
            "archive_path": snapshot.archive_path,
            **snapshot.identity.as_json(),
        } for name, snapshot in captured.items()
    }
    collection_capture["authenticated_contract"] = authenticated_contract
    return contract, successes, collection_capture, collection_root


def validate_approval_and_capture(
    approval: dict[str, Any], approval_snapshot: Snapshot,
    root: Path, manifest: dict[str, Any], expected_semantics: list[dict[str, Any]],
    serializer_sha256: str, validator: Snapshot, protocol: Snapshot,
    regression: Snapshot,
    replay_runtime: dict[str, str], trusted_project_root: Path,
    trusted_project_head: str, stage: Path, stager: Stager,
) -> dict[str, Any]:
    require(set(approval) == APPROVAL_KEYS and
            approval["schema"] == "candle-s1-identity-approval-v2" and
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

    (collection_contract, collection_successes, collection_capture,
     collection_root) = \
        capture_collection_evidence(
            approval, root, manifest,
            trusted_project_root, trusted_project_head, stage, stager,
        )

    targets = approval["targets"]
    require(isinstance(targets, list) and len(targets) == 65,
            "independent approval does not cover 65 targets")
    artifact_cache: dict[str, tuple[str, Snapshot]] = {}
    replays: list[dict[str, Any]] = []
    external_runtime: dict[str, Any] | None = None
    core_runtime: dict[str, Any] | None = None
    external_runtime_stable: dict[str, Any] | None = None
    core_runtime_stable: dict[str, Any] | None = None
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
            name: set() for name in (
                "candidate", "plan", "request", "transcript",
                "controller_success", "collector_stdout", "collector_stderr",
                "validator_stdout", "validator_stderr")
        }
        for run_index, run in enumerate(runs, 1):
            require(isinstance(run, dict) and set(run) == {
                "artifacts", "reference_git_head", "session_nonce",
                "identity_sha256", "sweep",
            }, f"malformed reference run for {name}")
            require(is_int(run["sweep"]) and run["sweep"] == run_index,
                    f"reference run sweep mismatch for {name}")
            require(run["reference_git_head"] == exact_reference,
                    f"reference run head mismatch for {name}")
            nonce = require_nonce(run["session_nonce"], f"reference run {name}")
            nonces.add(nonce)
            require(run["identity_sha256"] == expected_identity_sha256,
                    f"reference identity digest mismatch for {name}")
            artifacts = run["artifacts"]
            require(isinstance(artifacts, dict) and set(artifacts) == {
                "candidate", "plan", "request", "transcript", "source_contract",
                "controller_success", "collector_stdout", "collector_stderr",
                "validator_stdout", "validator_stderr",
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
            require(isinstance(candidate, dict) and
                    is_int(candidate.get("process_exit_code")) and
                    candidate["process_exit_code"] == 0,
                    f"malformed candidate process exit code for {name}")
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
            success_receipt = snapshot_json(
                stage, captured_artifacts["controller_success"],
                f"{name} controller success run {run_index}",
            )
            aggregate_success = collection_successes[(run_index, target_index)]
            aggregate_receipt = aggregate_success["receipt"]
            require(isinstance(aggregate_receipt, dict) and
                    set(aggregate_receipt) == {"path", "bytes", "sha256"} and
                    aggregate_receipt["path"] ==
                    aggregate_success["receipt_path"] and
                    is_int(aggregate_receipt.get("bytes")) and
                    aggregate_receipt.get("bytes") ==
                    captured_artifacts["controller_success"].identity.bytes and
                    aggregate_receipt.get("sha256") ==
                    captured_artifacts["controller_success"].identity.sha256 and
                    root / artifacts["controller_success"]["path"] ==
                    collection_root / aggregate_success["receipt_path"] and
                    aggregate_success["session_nonce"] == run["session_nonce"],
                    f"aggregate receipt does not bind {name} run {run_index}")
            require(isinstance(success_receipt, dict) and set(success_receipt) == {
                "schema", "kind", "sweep", "target_index", "target",
                "session_nonce", "artifacts", "collector_stdout",
                "collector_stderr", "validator_stdout", "validator_stderr",
                "deadlines", "approval_status", "promotion_allowed",
            } and all(is_int(success_receipt[field]) for field in (
                "schema", "sweep", "target_index",
            )) and success_receipt["schema"] == 1 and
                    success_receipt["kind"] ==
                    "candle-reference-attempt-success" and
                    success_receipt["sweep"] == run_index and
                    success_receipt["target_index"] == target_index and
                    success_receipt["target"] == name and
                    success_receipt["session_nonce"] == run["session_nonce"] and
                    success_receipt["deadlines"] ==
                    collection_contract["deadlines"] and
                    success_receipt["approval_status"] ==
                    "candidate_unapproved" and
                    success_receipt["promotion_allowed"] is False and
                    isinstance(success_receipt["artifacts"], dict) and
                    set(success_receipt["artifacts"]) == {
                        "candidate", "plan", "request", "transcript"},
                    f"malformed controller success for {name} run {run_index}")
            for artifact_name in ("candidate", "plan", "request", "transcript"):
                record = success_receipt["artifacts"][artifact_name]
                aggregate_record = aggregate_success["artifacts"].get(artifact_name)
                snapshot = captured_artifacts[artifact_name]
                require(isinstance(record, dict) and set(record) == {
                    "path", "bytes", "sha256"} and
                        collection_root / record["path"] ==
                        root / artifacts[artifact_name]["path"] and
                        is_int(record.get("bytes")) and
                        record.get("bytes") == snapshot.identity.bytes and
                        record.get("sha256") == snapshot.identity.sha256 and
                        aggregate_record == record,
                        f"controller receipt does not bind {name} {artifact_name}")
            for artifact_name in (
                    "collector_stdout", "collector_stderr", "validator_stdout",
                    "validator_stderr"):
                record = success_receipt[artifact_name]
                snapshot = captured_artifacts[artifact_name]
                require(isinstance(record, dict) and set(record) == {
                    "path", "bytes", "sha256"} and
                        collection_root / record["path"] ==
                        root / artifacts[artifact_name]["path"] and
                        is_int(record.get("bytes")) and
                        record.get("bytes") == snapshot.identity.bytes and
                        record.get("sha256") == snapshot.identity.sha256,
                        f"controller receipt does not bind {name} {artifact_name}")
            candidate_path = collection_root / success_receipt["artifacts"][
                "candidate"]["path"]
            expected_outputs = {
                "collector_stdout": (
                    f"unapproved reference candidate: {candidate_path}\n"
                ).encode(),
                "collector_stderr": b"",
                "validator_stdout": (
                    "candidate and linked artifacts valid but unapproved: "
                    f"{candidate_path}\n"
                ).encode(),
                "validator_stderr": b"",
            }
            for artifact_name, expected_output in expected_outputs.items():
                require(snapshot_bytes(
                    stage, captured_artifacts[artifact_name],
                ) == expected_output,
                        f"unexpected controller output for {name} "
                        f"{artifact_name}")
            validate_reference_plan_bindings(
                plan, candidate, target, run, policy,
                captured_artifacts["source_contract"], root, validator, protocol,
                serializer_sha256,
            )
            candle_contract = collection_contract["candle"]
            reference_contract = collection_contract["reference"]
            external_contract = collection_contract["external_runtime"]
            external_plan = plan["reference"]["external_runtime"]
            require(plan["input"]["collector"]["sha256"] ==
                    candle_contract["collector"]["sha256"] and
                    plan["input"]["collector_repository"]["git_head"] ==
                    candle_contract["git_head"] and
                    plan["input"]["collector_repository"][
                        "support_at_head_sha256"] ==
                    candle_contract["protocol"]["sha256"] and
                    plan["input"]["manifest"]["sha256"] ==
                    candle_contract["manifest"]["sha256"] and
                    plan["input"]["serializer"]["sha256"] ==
                    candle_contract["serializer"]["sha256"] and
                    plan["reference"]["root"] == reference_contract["root"] and
                    plan["reference"]["git_head"] ==
                    reference_contract["git_head"],
                    f"collection contract does not bind {name} plan")
            require(external_plan["policy"] == external_contract["policy"] and
                    all(external_plan[key]["argument_path"] ==
                        external_contract[key]["argument_path"] and
                        external_plan[key]["resolved_executable"]["path"] ==
                        external_contract[key]["path"] and
                        external_plan[key]["resolved_executable"]["sha256"] ==
                        external_contract[key]["sha256"]
                        for key in ("command_shell", "pari_gp", "csdp")) and
                    external_plan["csdp_bytes"] ==
                    external_contract["csdp"]["bytes"] and
                    external_plan["package_archive"] == {
                        "path": external_contract["package_archive"]["path"],
                        "sha256":
                            external_contract["package_archive"]["sha256"]} and
                    external_plan["package_tree"] ==
                    external_contract["package_tree"] and
                    external_plan["configuration"] == {
                        "path": external_contract["configuration"]["path"],
                        "sha256": external_contract["configuration"]["sha256"]} and
                    external_plan["data_tree"] ==
                    external_contract["data_tree"] and
                    external_plan["csdp_source_archive"] == {
                        key: external_contract["csdp_source_archive"][key]
                        for key in ("path", "sha256", "bytes")
                    } and external_plan["csdp_build"] == {
                        "receipt": {
                            key: external_contract["csdp_build"]["receipt"][key]
                            for key in ("path", "sha256")
                        },
                        "statement": external_contract["csdp_build"]["statement"],
                    } and external_plan["csdp_probe_input"] == {
                        key: external_contract["csdp_probe_input"][key]
                        for key in ("path", "sha256", "bytes")
                    } and external_plan["thread_policy"] ==
                    external_contract["thread_policy"] and
                    external_plan["csdp_probe"] ==
                    external_contract["csdp_probe"] and
                    all(plan["fresh_process_contract"]["runtime_environment"].get(
                        key) == value for key, value in
                        external_contract["runtime_environment"].items()),
                    f"collection contract does not bind {name} external runtime")
            runtime_contract = collection_contract["runtime"]
            runtime_plan = {
                "runtime": plan["reference"]["runtime_executable"],
                "runtime_stublib": plan["reference"]["runtime_stublib"],
                "ocamlc": {
                    key: plan["reference"]["ocamlc"][key]
                    for key in ("path", "sha256")
                },
                "ocamlfind": plan["reference"]["findlib"]["executable"],
            }
            require(all({
                "path": runtime_contract[key]["path"],
                "sha256": runtime_contract[key]["sha256"],
            } == runtime_plan[key] for key in runtime_plan),
                    f"collection contract does not bind {name} core runtime")
            require(elf_oracle_projection(plan["reference"]["elf_runtime"]) ==
                    collection_contract["elf_oracle"] and
                    elf_oracle_projection(external_plan["elf_runtime"]) ==
                    collection_contract["elf_oracle"],
                    f"collection contract does not bind {name} ELF observer")
            observed_external = plan["reference"]["external_runtime"]
            observed_external_stable = dict(observed_external)
            observed_external_stable["elf_runtime"] = stable_elf_runtime(
                observed_external["elf_runtime"])
            if external_runtime is None:
                external_runtime = observed_external
                external_runtime_stable = observed_external_stable
            else:
                require(observed_external_stable == external_runtime_stable,
                        "reference runs use different external-runtime closures")
            observed_core = {
                key: plan["reference"][key] for key in (
                    "runtime_executable", "runtime_interpreter",
                    "runtime_stublib", "runtime_library_tree",
                    "runtime_stub_files", "elf_runtime", "ocamlc",
                    "findlib", "hol_ml", "generated_boot_files",
                    "ocaml_library_tree")
            }
            observed_core_stable = dict(observed_core)
            observed_core_stable["elf_runtime"] = stable_elf_runtime(
                observed_core["elf_runtime"])
            if core_runtime is None:
                core_runtime = observed_core
                core_runtime_stable = observed_core_stable
            else:
                require(observed_core_stable == core_runtime_stable,
                        "reference runs use different HOL/OCaml runtime closures")
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
                "target": target,
            })
        require(len(nonces) == 2,
                f"reference runs do not use distinct session nonces for {name}")
        require(all(len(values) == 2 for values in distinct_run_artifacts.values()),
                f"reference run artifacts are not distinct for {name}")
    require(external_runtime is not None,
            "reference approval has no external-runtime closure")
    require(core_runtime is not None,
            "reference approval has no HOL/OCaml runtime closure")
    replay = run_captured_reference_replay(
        stage, validator, protocol, regression, replay_runtime, replays, stager,
    )
    replay["external_runtime"] = capture_reference_external_runtime(
        external_runtime, stage, stager,
    )
    reference_projection = {
        **core_runtime,
        "external_runtime": external_runtime,
    }
    replay["core_runtime"] = capture_reference_core_runtime(
        reference_projection, stage, stager,
    )
    replay["collection_evidence"] = collection_capture
    return replay


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
        reference_protocol = stager.capture(
            root / REFERENCE_PROTOCOL_PATH,
            f"execution-contract/{REFERENCE_PROTOCOL_PATH}",
            "reference fingerprint protocol",
        )
        validate_committed_snapshot(
            root, REFERENCE_PROTOCOL_PATH, reference_protocol, stage, "100644",
        )
        reference_source_contract = stager.capture(
            root / "candle/reference_source_contracts.json",
            "execution-contract/candle/reference_source_contracts.json",
            "reference source contract",
        )
        validate_committed_snapshot(
            root, "candle/reference_source_contracts.json",
            reference_source_contract, stage, "100644",
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
            stage, stager, reference_validator, reference_protocol,
            reference_source_contract, contract_snapshots, closure,
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
            "schema": "candle-s1-identity-approval-v2",
            "approval_status": "approved",
            "promotion_allowed": True,
        }, "manifest identity-approval metadata mismatch")
        approval_replay = validate_approval_and_capture(
            approval, approval_snapshot, root, manifest, approved_semantics,
            contract_snapshots["candle/fingerprint.ml"].identity.sha256,
            reference_validator, reference_protocol,
            contract_snapshots["candle/regression.py"],
            replay_runtime, finalizer["project_root"],
            finalizer["project_head"], stage, stager,
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
