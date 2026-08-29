#!/usr/bin/env python3
"""Adversarial fixtures for the schema-4 Great100 evidence finalizer."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("finalize-top100-report.py")
SPEC = importlib.util.spec_from_file_location("finalize_top100_report", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

CAKEML = "2" * 40
HOL4 = "3" * 40
REFERENCE = "4" * 40


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def record(path: Path) -> dict[str, object]:
    value = path.read_bytes()
    return {"bytes": len(value), "sha256": digest(value)}


def file_reference(path: Path) -> dict[str, object]:
    return {"path": str(path), **record(path)}


def git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["/usr/bin/git", "-C", str(root), *arguments],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    return completed.stdout.strip()


class Fixture:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.candle_root = self.root / "candle-repository"
        self.candle = self.candle_root / "candle"
        self.build = self.candle / "build"
        self.runs_root = self.root / "runs"
        self.run_dirs = [self.runs_root / "run-1", self.runs_root / "run-2"]
        self.report_paths = [directory / "report.json" for directory in self.run_dirs]
        self.approval_root = self.candle_root / "reference-evidence"
        self.approval_path = self.candle / "top100_identity_approval.json"
        self.authorization_path = self.root / "external-authorization.json"
        self.destination = self.root / "archive"
        self.project_root = self.root / "finalizer-project"
        self.program_path = self.project_root / "scripts/finalize-top100-report.py"
        for directory in (
            self.candle, self.build, *self.run_dirs, self.approval_root,
            self.program_path.parent,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        self._create_finalizer_project()
        self.serializer_path = self._write(
            self.candle_root, "candle/fingerprint.ml", b"serializer fixture\n",
        )
        self.serializer_sha256 = digest(self.serializer_path.read_bytes())
        self.raw_records: dict[str, list[str]] = {}
        self.raw_states: dict[str, str] = {}
        self.manifest = self._create_manifest_and_sources()
        self._create_execution_sources()
        self.closure = self._source_closure()
        self.semantics = [MODULE.manifest_semantics(target)
                          for target in self.manifest["targets"]]
        self._create_approval()
        for target in self.manifest["targets"]:
            target["fingerprint_request"]["expected_identities"][
                "approval_sha256"
            ] = self.approval_identity["sha256"]
        self.manifest["identity_approval"] = {
            "path": "candle/top100_identity_approval.json",
            "sha256": self.approval_identity["sha256"],
            "schema": "candle-s1-identity-approval-v1",
            "approval_status": "approved",
            "promotion_allowed": True,
        }
        (self.candle / "top100_manifest.json").write_bytes(
            MODULE.canonical_json_bytes(self.manifest),
        )
        self._commit_candle_repository()
        self._create_linked_runtime()
        self.execution_contract = {
            relative: record(self.candle_root / relative)
            for relative in sorted(MODULE.EXECUTION_CONTRACT_PATHS)
        }
        self.reports = [self._create_report(index) for index in range(2)]
        self.write_reports()

    @staticmethod
    def _write(base: Path, relative: str, value: bytes) -> Path:
        path = base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
        return path

    def _create_finalizer_project(self) -> None:
        self.program_path.write_bytes(SCRIPT.read_bytes())
        self.program_path.chmod(0o755)
        git(self.project_root, "init", "-q")
        git(self.project_root, "config", "user.email", "fixture@example.invalid")
        git(self.project_root, "config", "user.name", "fixture")
        git(self.project_root, "add", ".")
        git(self.project_root, "commit", "-qm", "fixture finalizer")
        self.project_head = git(self.project_root, "rev-parse", "HEAD")

    @staticmethod
    def _wire_record(name: str, index: int, theorem_index: int) -> tuple[str, dict]:
        theorem = f"theorem-{index}-{theorem_index}".encode()
        hypotheses = MODULE.EMPTY_HYPOTHESES_WIRE
        conclusion = f"conclusion-{index}-{theorem_index}".encode()
        axioms = b"three-global-axioms"
        line = "\t".join([
            MODULE.FINGERPRINT_MARKER, name.encode().hex(), theorem.hex(),
            hypotheses.hex(), conclusion.hex(), axioms.hex(), "0", "3",
        ])
        identity = {
            "name": name,
            "theorem_sha256": digest(theorem),
            "hypotheses_sha256": digest(hypotheses),
            "conclusion_sha256": digest(conclusion),
            "global_axioms_sha256": digest(axioms),
            "hypothesis_count": 0,
            "global_axiom_count": 3,
        }
        return line, identity

    @staticmethod
    def _state_wire_record(index: int) -> tuple[str, dict]:
        values = [
            f"kernel-state-{index}".encode(),
            f"type-constants-{index}".encode(),
            f"term-constants-{index}".encode(),
            f"definitions-{index}".encode(),
            b"three-global-axioms",
        ]
        line = "\t".join([
            MODULE.STATE_FINGERPRINT_MARKER,
            *(value.hex() for value in values),
            str(100 + index), str(200 + index), str(300 + index), "3",
        ])
        identity = {
            "kernel_state_sha256": digest(values[0]),
            "type_constants_sha256": digest(values[1]),
            "type_constant_count": 100 + index,
            "term_constants_sha256": digest(values[2]),
            "term_constant_count": 200 + index,
            "definitions_sha256": digest(values[3]),
            "definition_count": 300 + index,
            "global_axioms_sha256": digest(values[4]),
            "global_axiom_count": 3,
        }
        return line, identity

    def _create_manifest_and_sources(self) -> dict:
        targets = []
        extra = "100/shared-extra.ml"
        self._write(self.candle_root, extra, b"extra first-target source\n")
        for index in range(65):
            name = f"100/test-{index:02d}"
            source = f"{name}.ml"
            self._write(
                self.candle_root, source,
                f"(* canonical source {index} *)\n".encode(),
            )
            files = [source, extra] if index == 0 else [source]
            theorem_count = 2 if index < 32 else 1
            theorem_names = [f"THEOREM_{index:02d}_{item}"
                             for item in range(theorem_count)]
            wires = []
            identities = []
            for theorem_index, theorem_name in enumerate(theorem_names):
                wire, identity = self._wire_record(
                    theorem_name, index, theorem_index,
                )
                wires.append(wire)
                identities.append(identity)
            self.raw_records[name] = wires
            state_wire, post_state = self._state_wire_record(index)
            self.raw_states[name] = state_wire
            targets.append({
                "name": name,
                "load_files": files,
                "load_file_sha256": {
                    item: digest((self.candle_root / item).read_bytes())
                    for item in files
                },
                "skip": None,
                "fingerprint_request": {
                    "mapping_status": "audited",
                    "theorems": [{
                        "name": item,
                        "resolved_declaration": {
                            "path": source,
                            "line": theorem_index + 1,
                        },
                        "shadowed_declarations": [],
                    } for theorem_index, item in enumerate(theorem_names)],
                    "expected_identities": {
                        "approval_sha256": "0" * 64,
                        "serializer_sha256": self.serializer_sha256,
                        "theorems": identities,
                        "post_state": post_state,
                    },
                },
            })
        manifest = {"schema_version": 1, "target_count": 65, "targets": targets}
        self._write(
            self.candle_root, "candle/top100_manifest.json",
            (json.dumps(manifest, indent=2) + "\n").encode(),
        )
        return manifest

    def _create_execution_sources(self) -> None:
        helper = (
            "import pathlib, sys\n"
            "if sys.argv[1:] != ['check-linked', '--candle-root', sys.argv[-1]]:\n"
            "    raise SystemExit(17)\n"
            "if not pathlib.Path(sys.argv[-1]).is_dir():\n"
            "    raise SystemExit(18)\n"
            "print('linked CakeML provenance PASS')\n"
        ).encode()
        self._write(
            self.candle_root, "candle/cakeml_artifact_provenance.py", helper,
        )
        regression = r'''import hashlib
import json
from pathlib import Path

FINGERPRINT_MARKER = "CANDLE_FINGERPRINT_V2"
STATE_FINGERPRINT_MARKER = "CANDLE_STATE_FINGERPRINT_V2"
CANDLE_ROOT = Path(__file__).resolve().parent.parent
FINGERPRINT_HELPER = CANDLE_ROOT / "candle/fingerprint.ml"

_manifest = json.loads(
    (CANDLE_ROOT / "candle/top100_manifest.json").read_text(encoding="utf-8"))
for _target in _manifest["targets"]:
    for _relative in _target["load_files"]:
        _source = CANDLE_ROOT / _relative
        if (not _source.is_file() or
                hashlib.sha256(_source.read_bytes()).hexdigest() !=
                _target["load_file_sha256"][_relative]):
            raise RuntimeError("staged regression source closure is incomplete")


class LoadFailure(Exception):
    pass


def _fingerprint_request_source(theorem_names):
    return "THEOREMS " + ",".join(theorem_names) + "\n"


def _decode(value, label):
    try:
        return bytes.fromhex(value)
    except ValueError as error:
        raise LoadFailure(f"malformed {label}") from error


def _read_fingerprint_records(path, theorem_names, mapping_status,
                              expected_identities=None):
    records = {}
    states = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith(FINGERPRINT_MARKER + "\t"):
            fields = line.split("\t")
            if len(fields) != 8:
                raise LoadFailure("malformed theorem wire")
            name = _decode(fields[1], "name").decode("ascii")
            values = [_decode(value, "theorem field") for value in fields[2:6]]
            if name in records:
                raise LoadFailure("duplicate theorem")
            records[name] = {
                "name": name,
                "theorem_sha256": hashlib.sha256(values[0]).hexdigest(),
                "hypotheses_sha256": hashlib.sha256(values[1]).hexdigest(),
                "conclusion_sha256": hashlib.sha256(values[2]).hexdigest(),
                "global_axioms_sha256": hashlib.sha256(values[3]).hexdigest(),
                "hypothesis_count": int(fields[6]),
                "global_axiom_count": int(fields[7]),
            }
        if line.startswith(STATE_FINGERPRINT_MARKER + "\t"):
            fields = line.split("\t")
            if len(fields) != 10:
                raise LoadFailure("malformed state wire")
            values = [_decode(value, "state field") for value in fields[1:6]]
            states.append({
                "kernel_state_sha256": hashlib.sha256(values[0]).hexdigest(),
                "type_constants_sha256": hashlib.sha256(values[1]).hexdigest(),
                "term_constants_sha256": hashlib.sha256(values[2]).hexdigest(),
                "definitions_sha256": hashlib.sha256(values[3]).hexdigest(),
                "global_axioms_sha256": hashlib.sha256(values[4]).hexdigest(),
                "type_constant_count": int(fields[6]),
                "term_constant_count": int(fields[7]),
                "definition_count": int(fields[8]),
                "global_axiom_count": int(fields[9]),
            })
    if list(records) != list(theorem_names) or len(states) != 1:
        raise LoadFailure("fingerprint request mismatch")
    post_state = states[0]
    ordered = [records[name] for name in theorem_names]
    if (post_state["global_axiom_count"] != 3 or
            any(record["global_axioms_sha256"] !=
                post_state["global_axioms_sha256"] for record in ordered)):
        raise LoadFailure("global axiom mismatch")
    return {
        "status": "observed_uncompared",
        "mapping_status": mapping_status,
        "expected_identities_present": False,
        "serializer": {
            "path": "candle/fingerprint.ml",
            "sha256": hashlib.sha256(FINGERPRINT_HELPER.read_bytes()).hexdigest(),
        },
        "theorems": ordered,
        "post_state": post_state,
        "approval_sha256": None,
    }
'''.encode()
        self._write(self.candle_root, "candle/regression.py", regression)
        reference_validator = r'''import hashlib
import json
from pathlib import Path
import re
import tempfile

import regression

SESSION_MARKER = "CANDLE_REFERENCE_SESSION_V1"
COMPLETE_MARKER = "CANDLE_REFERENCE_COMPLETE_V1"
PLAN_SCHEMA = "candle-s1-reference-plan-v6"
CANDIDATE_SCHEMA = "candle-s1-reference-candidate-v6"


class CollectionError(Exception):
    pass


def _json_sha256(value):
    return hashlib.sha256(
        (json.dumps(value, indent=2) + "\n").encode("utf-8")).hexdigest()


def _request_source(target, serializer_path, nonce):
    names = [item["name"] for item in
             target["fingerprint_request"]["theorems"]]
    lines = [
        f"{SESSION_MARKER}\t{nonce}",
        f"SERIALIZER {Path(serializer_path).resolve()}",
        *(f"LOAD {path}" for path in target["load_files"]),
        regression._fingerprint_request_source(names).rstrip(),
        f"{COMPLETE_MARKER}\t{nonce}",
    ]
    return "\n".join(lines) + "\n"


def _stable_plan_pins(plan):
    return {
        "reference": plan["reference"],
        "input": plan["input"],
        "request_sha256": plan["request"]["sha256"],
        "fresh_process_contract": plan["fresh_process_contract"],
    }


def candidate_from_transcript(plan, transcript, exit_code=0):
    if plan.get("schema") != PLAN_SCHEMA or exit_code != 0:
        raise CollectionError("unsupported or failed reference plan")
    nonce = plan["session_nonce"]
    start = f"{SESSION_MARKER}\t{nonce}"
    complete = f"{COMPLETE_MARKER}\t{nonce}"
    lines = transcript.splitlines()
    if lines.count(start) != 1 or lines.count(complete) != 1:
        raise CollectionError("missing or duplicate reference session markers")
    start_index = lines.index(start)
    complete_index = lines.index(complete)
    if start_index >= complete_index:
        raise CollectionError("reference marker order mismatch")
    session = "\n".join(lines[start_index + 1:complete_index]) + "\n"
    with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False) as output:
        output.write(session)
        path = Path(output.name)
    try:
        identities = regression._read_fingerprint_records(
            path, tuple(plan["input"]["theorem_names"]),
            plan["input"]["mapping_status"])
    finally:
        path.unlink()
    return {
        "schema": CANDIDATE_SCHEMA,
        "artifact_kind": "reference_identity_candidate",
        "approval_status": "candidate_unapproved",
        "promotion_allowed": False,
        "warning": (
            "Review provenance and identities independently; this artifact is "
            "not an EXPECTED_IDENTITIES value and no automatic promotion exists."
        ),
        "plan_pins": _stable_plan_pins(plan),
        "session_nonce": nonce,
        "process_exit_code": exit_code,
        "artifact_hashes": {
            "plan_sha256": _json_sha256(plan),
            "request_sha256": plan["request"]["sha256"],
            "transcript_sha256": hashlib.sha256(
                transcript.encode("utf-8")).hexdigest(),
        },
        "candidate_identities": identities,
    }


def validate_candidate(candidate, plan=None, request=None, transcript=None):
    required = {
        "schema", "artifact_kind", "approval_status", "promotion_allowed",
        "warning", "plan_pins", "session_nonce", "process_exit_code",
        "artifact_hashes", "candidate_identities",
    }
    if set(candidate) != required or candidate["schema"] != CANDIDATE_SCHEMA:
        raise CollectionError("malformed or unsupported reference candidate")
    if (candidate["artifact_kind"] != "reference_identity_candidate" or
            candidate["approval_status"] != "candidate_unapproved" or
            candidate["promotion_allowed"] is not False or
            candidate["process_exit_code"] != 0 or
            re.fullmatch(r"[0-9a-f]{64}", candidate["session_nonce"]) is None):
        raise CollectionError("reference candidate is not fail-closed")
    hashes = candidate["artifact_hashes"]
    if set(hashes) != {"plan_sha256", "request_sha256", "transcript_sha256"}:
        raise CollectionError("malformed candidate hashes")
    if candidate["candidate_identities"].get("status") != "observed_uncompared":
        raise CollectionError("reference candidate is not incomparable")
    if hashes["plan_sha256"] != _json_sha256(plan):
        raise CollectionError("candidate plan artifact hash mismatch")
    if (request != plan["request"]["source"] or
            hashlib.sha256(request.encode()).hexdigest() !=
            hashes["request_sha256"]):
        raise CollectionError("candidate request artifact mismatch")
    if hashlib.sha256(transcript.encode()).hexdigest() != \
            hashes["transcript_sha256"]:
        raise CollectionError("candidate transcript artifact hash mismatch")
    if candidate_from_transcript(plan, transcript, 0) != candidate:
        raise CollectionError("candidate does not replay from linked artifacts")
    return candidate
'''.encode()
        self._write(
            self.candle_root, "candle/reference_fingerprints.py",
            reference_validator,
        )
        launcher = self._write(
            self.candle_root, "candle.sh", b"#!/bin/sh\nexit 0\n",
        )
        launcher.chmod(0o755)
        self._write(
            self.candle_root, "candle/flyspeck_manifest.json",
            b'{"fixture":true}\n',
        )
        self._write(self.candle_root, "candle/cake.S.patch", b"patch fixture\n")
        self._write(self.candle_root, ".gitignore", b"candle/build/\n")

    def _commit_candle_repository(self) -> None:
        git(self.candle_root, "init", "-q")
        git(self.candle_root, "config", "user.email", "fixture@example.invalid")
        git(self.candle_root, "config", "user.name", "fixture")
        git(self.candle_root, "add", ".")
        git(self.candle_root, "commit", "-qm", "fixture Candle")
        self.candle_head = git(self.candle_root, "rev-parse", "HEAD")

    def _create_linked_runtime(self) -> None:
        for name in MODULE.LINKED_OUTPUTS:
            self._write(
                self.candle_root, f"candle/build/{name}",
                f"linked {name} fixture\n".encode(),
            )
        outputs = {name: record(self.build / name) for name in MODULE.LINKED_OUTPUTS}
        linked = {
            "schema": 6,
            "kind": "candle-linked-pinned-cakeml",
            "candle_commit": self.candle_head,
            "cakeml_commit": CAKEML,
            "hol4_commit": HOL4,
            "manifest_sha256": digest(
                (self.candle / "flyspeck_manifest.json").read_bytes()),
            "bootstrap_record": outputs["bootstrap-provenance.json"],
            "bootstrap_preflight": outputs["bootstrap-preflight.json"],
            "bootstrap_log": outputs["bootstrap.log"],
            "cake_patch": record(self.candle / "cake.S.patch"),
            "cake_patch_derivation": {"fixture": True},
            "native_link_derivation": {"fixture": True},
            "outputs": outputs,
            "runtime_elf_closure": {"fixture": True},
            "version_output_sha256": "5" * 64,
        }
        self.linked_path = self.build / "cakeml-build-provenance.json"
        self.linked_path.write_text(json.dumps(linked), encoding="utf-8")
        self.linked_sha256 = digest(self.linked_path.read_bytes())

    def _source_closure(self) -> dict:
        ordered_files = []
        targets = []
        for target in self.manifest["targets"]:
            for source in target["load_files"]:
                if source not in ordered_files:
                    ordered_files.append(source)
            targets.append({
                "name": target["name"],
                "load_files": target["load_files"],
                "theorem_names": [
                    item["name"]
                    for item in target["fingerprint_request"]["theorems"]
                ],
            })
        projection = {
            "target_count": 65,
            "source_file_count": 66,
            "fingerprint_request_count": 97,
            "ordered_targets": targets,
            "files": [
                {"path": source, **record(self.candle_root / source)}
                for source in ordered_files
            ],
        }
        return {**projection, "sha256": MODULE.compact_json_sha256(projection)}

    def _create_approval(self) -> None:
        deltas = []
        for index, path in enumerate((
            "100/e_is_transcendental.ml", "100/euler.ml", "100/lagrange.ml",
        )):
            deltas.append({
                "path": path,
                "historical_sha256": f"{7000 + index:064x}",
                "selected_sha256": f"{8000 + index:064x}",
                "reason": f"reviewed fixture delta {index}",
            })
        reference_policy = {
            "historical_upstream_commit": "6" * 40,
            "exact_source_reference_commit": REFERENCE,
            "compatibility_deltas": deltas,
        }
        shared_source_contract = self.approval_root / "source-contract.json"
        source_contract_value = {
            "schema": "candle-s1-reference-source-contract-v1",
            **reference_policy,
        }
        shared_source_contract.write_bytes(
            MODULE.canonical_json_bytes(source_contract_value),
        )
        self._write(
            self.candle_root, "candle/reference_source_contracts.json",
            shared_source_contract.read_bytes(),
        )
        collector = self.candle / "reference_fingerprints.py"
        collector_sha256 = digest(collector.read_bytes())
        manifest_pin = self.candle / "top100_manifest.json"
        targets = []
        for target_index, semantic in enumerate(self.semantics):
            target = self.manifest["targets"][target_index]
            expected_identity = deepcopy(semantic["expected_identity"])
            identity_sha256 = MODULE.compact_json_sha256(expected_identity)
            runs = []
            for run_index in range(2):
                nonce = f"{5000 + target_index * 2 + run_index:064x}"
                reference_root = Path("/reference") / f"run-{run_index + 1}"
                request_source = "\n".join([
                    f"CANDLE_REFERENCE_SESSION_V1\t{nonce}",
                    f"SERIALIZER {self.serializer_path.resolve()}",
                    *(f"LOAD {path}" for path in target["load_files"]),
                    "THEOREMS " + ",".join(
                        theorem["name"]
                        for theorem in target["fingerprint_request"]["theorems"]
                    ),
                    f"CANDLE_REFERENCE_COMPLETE_V1\t{nonce}",
                    "",
                ])
                plan = {
                    "schema": "candle-s1-reference-plan-v6",
                    "status": "planned_not_executed",
                    "session_nonce": nonce,
                    "fresh_process_contract": {
                        "required": True,
                        "preloaded_checkpoint_allowed": False,
                        "working_directory": str(reference_root),
                        "environment_policy":
                            "sanitized_allowlist_no_inherited_overrides",
                        "runtime_argv": ["/reference/ocaml", "-noprompt"],
                        "runtime_environment": {
                            "PATH": "/usr/bin:/bin", "LC_ALL": "C",
                        },
                    },
                    "reference": {
                        "root": str(reference_root),
                        "git_head": REFERENCE,
                        "git_status": [],
                        "runtime_executable": {"fixture": True},
                        "runtime_interpreter": {"fixture": True},
                        "runtime_stublib": {"fixture": True},
                        "runtime_library_tree": {"fixture": True},
                        "runtime_stub_files": [],
                        "dynamic_libraries": [],
                        "ocamlc": {"fixture": True},
                        "findlib": {"fixture": True},
                        "hol_ml": {"fixture": True},
                        "generated_boot_files": [],
                        "ocaml_library_tree": {"fixture": True},
                    },
                    "input": {
                        "collector": {
                            "path": str(collector), "sha256": collector_sha256,
                        },
                        "collector_repository": {
                            "root": str(self.candle_root),
                            "git_head": "8" * 40,
                            "git_status": [],
                            "collector_relative_path":
                                "candle/reference_fingerprints.py",
                            "collector_at_head_sha256": collector_sha256,
                            "collector_matches_head": True,
                        },
                        "manifest": {
                            "path": str(manifest_pin),
                            "sha256": digest(manifest_pin.read_bytes()),
                        },
                        "manifest_schema_version": 1,
                        "target": target["name"],
                        "load_files": [{
                            "relative_path": relative,
                            "path": str(reference_root / relative),
                            "sha256": target["load_file_sha256"][relative],
                            "source_role": "selected-manifest-source",
                        } for relative in target["load_files"]],
                        "theorem_names": [
                            theorem["name"]
                            for theorem in target["fingerprint_request"]["theorems"]
                        ],
                        "mapping_status": "audited",
                        "serializer": {
                            "path": str(self.serializer_path),
                            "sha256": self.serializer_sha256,
                        },
                        "source_mode": "manifest-exact",
                        "source_contract": {
                            "path": str(
                                self.candle / "reference_source_contracts.json"),
                            "sha256": digest(shared_source_contract.read_bytes()),
                            **reference_policy,
                        },
                    },
                    "request": {
                        "source": request_source,
                        "sha256": digest(request_source.encode()),
                    },
                }
                transcript = "\n".join([
                    "reference fixture preface",
                    f"CANDLE_REFERENCE_SESSION_V1\t{nonce}",
                    *self.raw_records[target["name"]],
                    self.raw_states[target["name"]],
                    f"CANDLE_REFERENCE_COMPLETE_V1\t{nonce}",
                    "reference fixture epilogue",
                    "",
                ])
                candidate_identities = {
                    "status": "observed_uncompared",
                    "mapping_status": "audited",
                    "expected_identities_present": False,
                    "serializer": {
                        "path": "candle/fingerprint.ml",
                        "sha256": self.serializer_sha256,
                    },
                    "theorems": deepcopy(expected_identity["theorems"]),
                    "post_state": deepcopy(expected_identity["post_state"]),
                    "approval_sha256": None,
                }
                candidate = {
                    "schema": "candle-s1-reference-candidate-v6",
                    "artifact_kind": "reference_identity_candidate",
                    "approval_status": "candidate_unapproved",
                    "promotion_allowed": False,
                    "warning": (
                        "Review provenance and identities independently; this "
                        "artifact is not an EXPECTED_IDENTITIES value and no "
                        "automatic promotion exists."
                    ),
                    "plan_pins": {
                        "reference": deepcopy(plan["reference"]),
                        "input": deepcopy(plan["input"]),
                        "request_sha256": plan["request"]["sha256"],
                        "fresh_process_contract": deepcopy(
                            plan["fresh_process_contract"]),
                    },
                    "session_nonce": nonce,
                    "process_exit_code": 0,
                    "artifact_hashes": {
                        "plan_sha256": digest(
                            (json.dumps(plan, indent=2) + "\n").encode()),
                        "request_sha256": plan["request"]["sha256"],
                        "transcript_sha256": digest(transcript.encode()),
                    },
                    "candidate_identities": candidate_identities,
                }
                directory = (self.approval_root / f"target-{target_index:02d}" /
                             f"run-{run_index + 1}")
                directory.mkdir(parents=True, exist_ok=True)
                values = {
                    "candidate": (json.dumps(candidate, indent=2) + "\n").encode(),
                    "plan": (json.dumps(plan, indent=2) + "\n").encode(),
                    "request": request_source.encode(),
                    "transcript": transcript.encode(),
                }
                artifacts = {}
                for artifact_name, value in values.items():
                    suffix = "json" if artifact_name in {"candidate", "plan"} else "txt"
                    path = directory / f"{artifact_name}.{suffix}"
                    path.write_bytes(value)
                    artifacts[artifact_name] = {
                        "path": path.relative_to(self.candle_root).as_posix(),
                        **record(path),
                    }
                artifacts["source_contract"] = {
                    "path": shared_source_contract.relative_to(
                        self.candle_root).as_posix(),
                    **record(shared_source_contract),
                }
                runs.append({
                    "artifacts": artifacts,
                    "reference_git_head": REFERENCE,
                    "session_nonce": nonce,
                    "identity_sha256": identity_sha256,
                })
            targets.append({
                "name": semantic["name"],
                "reference_runs": runs,
                "expected_identity": expected_identity,
            })
        self.approval = {
            "schema": "candle-s1-identity-approval-v1",
            "artifact_kind": "independently-reviewed-ocaml-reference-identities",
            "approval_status": "approved",
            "promotion_allowed": True,
            "inventory_contract_sha256": MODULE.compact_json_sha256(
                MODULE.approval_inventory_contract(self.manifest),
            ),
            "serializer_sha256": self.serializer_sha256,
            "reference_policy": reference_policy,
            "review": {
                "reviewer": "independent fixture reviewer",
                "approved_utc": "2026-08-29T01:00:00+00:00",
                "review_commit": "9" * 40,
                "decision": (
                    "two-reference-runs-identical-and-source-deltas-reviewed"
                ),
            },
            "targets": targets,
        }
        self.write_approval(update_reports=False)

    def write_approval(self, update_reports: bool = True) -> None:
        self.approval_path.write_bytes(MODULE.canonical_json_bytes(self.approval))
        self.approval_identity = record(self.approval_path)
        if update_reports and hasattr(self, "reports"):
            for report_value in self.reports:
                report_value["independent_approval"] = {
                    "path": "candle/top100_identity_approval.json",
                    **self.approval_identity,
                }
                report_value["run_evidence"]["independent_approval_sha256"] = \
                    self.approval_identity["sha256"]
            self.write_reports()

    def replace_reference_artifact(
        self, target_index: int, run_index: int, artifact_name: str, value: bytes,
    ) -> None:
        artifact = self.approval["targets"][target_index]["reference_runs"][
            run_index]["artifacts"][artifact_name]
        path = self.candle_root / artifact["path"]
        path.write_bytes(value)
        artifact.update(record(path))
        self.write_approval(update_reports=False)
        for target in self.manifest["targets"]:
            target["fingerprint_request"]["expected_identities"][
                "approval_sha256"] = self.approval_identity["sha256"]
        self.manifest["identity_approval"].update({
            "sha256": self.approval_identity["sha256"],
            "approval_status": "approved",
            "promotion_allowed": True,
        })
        manifest_path = self.candle / "top100_manifest.json"
        manifest_path.write_bytes(MODULE.canonical_json_bytes(self.manifest))
        git(self.candle_root, "add", "-A")
        git(self.candle_root, "commit", "-qm", "mutated approval fixture")
        new_head = git(self.candle_root, "rev-parse", "HEAD")
        new_contract = {
            relative: record(self.candle_root / relative)
            for relative in sorted(MODULE.EXECUTION_CONTRACT_PATHS)
        }
        for report_value in self.reports:
            report_value["candle_git_head"] = new_head
            report_value["execution_contract"] = deepcopy(new_contract)
            report_value["independent_approval"] = {
                "path": "candle/top100_identity_approval.json",
                **self.approval_identity,
            }
            report_value["run_evidence"]["independent_approval_sha256"] = \
                self.approval_identity["sha256"]
        self.write_reports()

    def _transcript(
        self, run_index: int, target_index: int, suite_nonce: str,
        process_nonce: str,
    ) -> bytes:
        target = self.manifest["targets"][target_index]
        lines = [
            f"CANDLE_GREAT100_SUITE_V1\t{suite_nonce}",
            (f"CANDLE_GREAT100_PROCESS_V1\t{suite_nonce}\t{process_nonce}"
             "\tSTART"),
            MODULE.LINKED_PASS_WITNESS,
            f"CANDLE_LINKED_PROVENANCE_V1\t{self.linked_sha256}",
            *self.raw_records[target["name"]],
            self.raw_states[target["name"]],
            (f"CANDLE_GREAT100_PROCESS_V1\t{suite_nonce}\t{process_nonce}"
             "\tCOMPLETE"),
            "",
        ]
        return "\n".join(lines).encode()

    def _create_report(self, run_index: int) -> dict:
        suite_nonce = f"{run_index + 1:064x}"
        results = []
        for target_index, target in enumerate(self.manifest["targets"]):
            process_nonce = f"{1000 + run_index * 65 + target_index:064x}"
            log = self.run_dirs[run_index] / f"target-{target_index:02d}.log"
            log.write_bytes(self._transcript(
                run_index, target_index, suite_nonce, process_nonce,
            ))
            expected = target["fingerprint_request"]["expected_identities"]
            marker_lines = {
                "suite_line": 0,
                "start_line": 1,
                "linked_line": 3,
                "complete_line": 5 + len(self.raw_records[target["name"]]),
            }
            executable_identity = record(self.build / "cake")
            runtime_state = {
                "candle_git_head": self.candle_head,
                "candle_git_status": [],
                "linked_record_sha256": self.linked_sha256,
                "candle_executable": {
                    "path": str(self.build / "cake"), **executable_identity,
                },
                "execution_contract_sha256": MODULE.compact_json_sha256(
                    self.execution_contract,
                ),
                "source_closure_sha256": self.closure["sha256"],
            }
            results.append({
                "name": target["name"],
                "files": target["load_files"],
                "status": "PASS",
                "timeout_kind": None,
                "boot_elapsed_seconds": 1.0,
                "hol_elapsed_seconds": 2.0,
                "test_elapsed_seconds": 3.0,
                "fingerprint_elapsed_seconds": 1.0,
                "total_elapsed_seconds": 7.0,
                "peak_process_rss_kib": 1000,
                "peak_tree_rss_kib": 1200,
                "error_message": "",
                "log_path": str(log),
                "process_evidence": {
                    "suite_nonce": suite_nonce,
                    "process_nonce": process_nonce,
                    "pid": 10000 + run_index * 65 + target_index,
                    "started_utc": (
                        f"2026-08-29T01:{run_index}{target_index % 6}:00+00:00"
                    ),
                    "completed_utc": (
                        f"2026-08-29T01:{run_index}{target_index % 6}:01+00:00"
                    ),
                    "exit_code": 0,
                    "markers": marker_lines,
                    "linked_record_sha256": self.linked_sha256,
                    "transcript": file_reference(log),
                    "pre_runtime_state": deepcopy(runtime_state),
                    "post_runtime_state": deepcopy(runtime_state),
                    "resource_sampling": {
                        "interval_seconds": 0.1,
                        "sample_count": 3,
                        "root_observed": True,
                        "sampler_completed": True,
                        "peak_process_rss_kib": 1000,
                        "peak_tree_rss_kib": 1200,
                    },
                },
                "fingerprints": {
                    "status": "matched",
                    "mapping_status": "audited",
                    "expected_identities_present": True,
                    "serializer": {
                        "path": "candle/fingerprint.ml",
                        "sha256": self.serializer_sha256,
                    },
                    "theorems": deepcopy(expected["theorems"]),
                    "post_state": deepcopy(expected["post_state"]),
                    "approval_sha256": expected["approval_sha256"],
                },
            })
        executable = self.build / "cake"
        return {
            "schema": 4,
            "generated_utc": f"2026-08-29T02:00:0{run_index}+00:00",
            "suite_started_utc": f"2026-08-29T00:59:0{run_index}+00:00",
            "suite": "top100",
            "test_count": 65,
            "jobs": 1,
            "timeout_policy": {
                "inactivity_timeout_seconds": 1800,
                "inactivity_resets_on": "each complete REPL output line",
                "inactivity_scope": "each REPL expect wait, including initial boot",
                "total_wall_timeout_seconds": 21600,
                "total_wall_scope": "process spawn through fingerprint capture",
                "progress_extends_total_wall_deadline": False,
            },
            "wall_seconds": 1000.0 + run_index,
            "sum_test_seconds": 455.0,
            "counts": {"PASS": 65, "FAIL": 0, "TIMEOUT": 0},
            "candle_root": str(self.candle_root),
            "candle_git_head": self.candle_head,
            "candle_git_status": [],
            "candle_executable": file_reference(executable),
            "log_directory": str(self.run_dirs[run_index]),
            "fingerprint_contract": deepcopy(MODULE.FINGERPRINT_CONTRACT),
            "s1_evidence": deepcopy(MODULE.S1_CLOSED),
            "run_evidence": {
                "suite_nonce": suite_nonce,
                "marker_contract": MODULE.MARKER_CONTRACT,
                "linked_record_sha256": self.linked_sha256,
                "source_closure_sha256": self.closure["sha256"],
                "independent_approval_sha256": self.approval_identity["sha256"],
            },
            "execution_contract": deepcopy(self.execution_contract),
            "source_closure": deepcopy(self.closure),
            "independent_approval": {
                "path": "candle/top100_identity_approval.json",
                **self.approval_identity,
            },
            "linked_record": {
                "path": "candle/build/cakeml-build-provenance.json",
                **record(self.linked_path),
            },
            "results": results,
        }

    def write_reports(self, refresh_authorization: bool = True) -> None:
        for path, report_value in zip(self.report_paths, self.reports):
            path.write_bytes(MODULE.canonical_json_bytes(report_value))
        if refresh_authorization:
            self.refresh_authorization()

    def refresh_transcript_identity(self, run_index: int, target_index: int) -> None:
        result = self.reports[run_index]["results"][target_index]
        result["process_evidence"]["transcript"] = file_reference(
            Path(result["log_path"]),
        )

    def refresh_authorization(self) -> None:
        project_program = record(self.program_path)
        semantics_sha256 = MODULE.compact_json_sha256(self.semantics)
        receipt = {
            "schema": 1,
            "kind": "candle-great100-finalization-authorization",
            "issued_utc": "2026-08-29T03:00:00+00:00",
            "authority": "out-of-band fixture authority",
            "reports": [record(path) for path in self.report_paths],
            "suite_nonces": [
                report_value["run_evidence"]["suite_nonce"]
                for report_value in self.reports
            ],
            "linked_record_sha256": self.linked_sha256,
            "source_closure_sha256": self.closure["sha256"],
            "semantic_projection_sha256": semantics_sha256,
            "independent_approval": self.approval_identity,
            "project": {
                "git_head": self.project_head,
                "finalizer": {
                    "path": "scripts/finalize-top100-report.py",
                    **project_program,
                },
            },
            "tools": {
                "python": {
                    "path": str(MODULE.PYTHON_PATH),
                    **record(MODULE.PYTHON_PATH),
                },
                "git": {
                    "path": str(MODULE.GIT_REQUESTED_PATH.resolve(strict=True)),
                    **record(MODULE.GIT_REQUESTED_PATH.resolve(strict=True)),
                },
            },
        }
        self.authorization = receipt
        self.authorization_path.write_bytes(MODULE.canonical_json_bytes(receipt))
        self.authorization_sha256 = digest(self.authorization_path.read_bytes())

    def write_authorization(self) -> None:
        self.authorization_path.write_bytes(
            MODULE.canonical_json_bytes(self.authorization),
        )
        self.authorization_sha256 = digest(self.authorization_path.read_bytes())

    def finalize(self, destination: Path | None = None) -> None:
        MODULE.archive(
            self.report_paths, destination or self.destination,
            self.authorization_path, self.authorization_sha256,
        )


class FinalizeTop100Schema4Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="candle-top100-schema4-finalizer.",
        )
        self.original_program = MODULE.PROGRAM_PATH
        self.original_hook = MODULE._TEST_AFTER_CONTRACT_CAPTURE
        self.fixture = Fixture(Path(self.temporary.name))
        MODULE.PROGRAM_PATH = self.fixture.program_path
        MODULE._TEST_AFTER_CONTRACT_CAPTURE = None

    def tearDown(self) -> None:
        MODULE.PROGRAM_PATH = self.original_program
        MODULE._TEST_AFTER_CONTRACT_CAPTURE = self.original_hook
        self.temporary.cleanup()

    def assert_rejected(self, pattern: str | None = None) -> None:
        context = (self.assertRaisesRegex(MODULE.ValidationError, pattern)
                   if pattern else self.assertRaises(MODULE.ValidationError))
        with context:
            self.fixture.finalize()

    def test_positive_hypothesis_theorem_and_wire_are_rejected(self):
        _, theorem = self.fixture._wire_record("EGCD", 0, 0)
        theorem["hypothesis_count"] = 1
        with self.assertRaisesRegex(MODULE.ValidationError,
                                    "theorem is not closed"):
            MODULE.validate_theorem_record(theorem, "EGCD")
        line, _ = self.fixture._wire_record("EGCD", 0, 0)
        fields = line.split("\t")
        fields[3] = b"nonempty-hypothesis".hex()
        fields[6] = "1"
        with self.assertRaisesRegex(MODULE.ValidationError,
                                    "wire record is not closed"):
            MODULE.parse_wire_record("\t".join(fields), "EGCD")

    def test_archives_two_complete_schema4_runs_and_exact_inventory(self) -> None:
        self.fixture.finalize()
        bundle_path = self.fixture.destination / "bundle.json"
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        self.assertEqual(bundle["schema"], 2)
        self.assertEqual(
            bundle["kind"], "candle-great100-two-schema4-run-archive",
        )
        self.assertTrue(
            bundle["comparison"]["identical_and_independently_approved"],
        )
        self.assertEqual(len(bundle["runs"]), 2)
        self.assertEqual([len(run["logs"]) for run in bundle["runs"]], [65, 65])
        self.assertEqual(bundle["source_closure"]["closure_sha256"],
                         self.fixture.closure["sha256"])
        self.assertEqual(bundle["approval_replay"]["candidate_count"], 130)
        for component in ("validator", "regression"):
            replay = bundle["approval_replay"][component]
            self.assertEqual(
                (self.fixture.destination /
                 replay["committed_archive_path"]).read_bytes(),
                (self.fixture.destination /
                 replay["executed_archive_path"]).read_bytes(),
            )
        executable = self.fixture.destination / \
            bundle["candle"]["executable"]["archive_path"]
        self.assertEqual(executable.read_bytes(), (self.fixture.build / "cake").read_bytes())
        checksums = {}
        for line in (self.fixture.destination / "SHA256SUMS").read_text().splitlines():
            checksum, relative = line.split("  ", 1)
            checksums[relative] = checksum
            self.assertEqual(digest((self.fixture.destination / relative).read_bytes()),
                             checksum)
        expected = set(bundle["retained_files"]) | {"bundle.json"}
        self.assertEqual(set(checksums), expected)
        actual = {
            path.relative_to(self.fixture.destination).as_posix()
            for path in self.fixture.destination.rglob("*") if path.is_file()
        }
        self.assertEqual(actual, expected | {"SHA256SUMS"})
        with self.assertRaisesRegex(MODULE.ValidationError, "already exists"):
            self.fixture.finalize()

    def test_schema3_is_unconditionally_non_promotable(self) -> None:
        self.fixture.reports[0]["schema"] = 3
        self.fixture.write_reports()
        self.assert_rejected("schema-3.*non-promotable")

    def test_copied_run_cannot_satisfy_two_distinct_runs(self) -> None:
        clone = deepcopy(self.fixture.reports[0])
        clone["generated_utc"] = "2026-08-29T02:00:09+00:00"
        clone["log_directory"] = str(self.fixture.run_dirs[1])
        for index, result in enumerate(clone["results"]):
            source = Path(result["log_path"])
            target = self.fixture.run_dirs[1] / f"clone-{index:02d}.log"
            target.write_bytes(source.read_bytes())
            result["log_path"] = str(target)
            result["process_evidence"]["transcript"] = file_reference(target)
        self.fixture.reports[1] = clone
        self.fixture.write_reports()
        self.assert_rejected("distinct suite runs")

    def test_report_bound_transcript_bytes_reject_post_report_mutation(self) -> None:
        log = Path(self.fixture.reports[0]["results"][0]["log_path"])
        log.write_bytes(log.read_bytes() + b"post-report mutation\n")
        self.assert_rejected("report-bound transcript bytes")

    def test_marker_count_is_not_a_wire_parser(self) -> None:
        result = self.fixture.reports[0]["results"][0]
        log = Path(result["log_path"])
        lines = log.read_text().splitlines()
        wire_index = next(index for index, line in enumerate(lines)
                          if line.startswith(MODULE.FINGERPRINT_MARKER))
        lines[wire_index] = MODULE.FINGERPRINT_MARKER + "\tfixture"
        log.write_text("\n".join(lines) + "\n")
        self.fixture.refresh_transcript_identity(0, 0)
        self.fixture.write_reports()
        self.assert_rejected("8-field fingerprint wire")

    def test_recomputed_transcript_hash_cannot_change_wire_semantics(self) -> None:
        result = self.fixture.reports[0]["results"][0]
        log = Path(result["log_path"])
        lines = log.read_text().splitlines()
        wire_index = next(index for index, line in enumerate(lines)
                          if line.startswith(MODULE.FINGERPRINT_MARKER))
        fields = lines[wire_index].split("\t")
        fields[2] = b"different theorem serialization".hex()
        lines[wire_index] = "\t".join(fields)
        log.write_text("\n".join(lines) + "\n")
        self.fixture.refresh_transcript_identity(0, 0)
        self.fixture.write_reports()
        self.assert_rejected("parsed fingerprint wire records")

    def test_state_wire_and_marker_offsets_are_not_report_assertions(self) -> None:
        result = self.fixture.reports[0]["results"][0]
        log = Path(result["log_path"])
        lines = log.read_text().splitlines()
        state_index = next(index for index, line in enumerate(lines)
                           if line.startswith(MODULE.STATE_FINGERPRINT_MARKER))
        fields = lines[state_index].split("\t")
        fields[1] = b"forged kernel state".hex()
        lines[state_index] = "\t".join(fields)
        log.write_text("\n".join(lines) + "\n")
        self.fixture.refresh_transcript_identity(0, 0)
        self.fixture.write_reports()
        self.assert_rejected("parsed state fingerprint")

        MODULE.PROGRAM_PATH = self.original_program
        self.temporary.cleanup()
        self.temporary = tempfile.TemporaryDirectory(
            prefix="candle-top100-schema4-finalizer-marker.",
        )
        self.fixture = Fixture(Path(self.temporary.name))
        MODULE.PROGRAM_PATH = self.fixture.program_path
        self.fixture.reports[0]["results"][0]["process_evidence"]["markers"][
            "linked_line"
        ] += 1
        self.fixture.write_reports()
        self.assert_rejected("marker offsets differ")

    def test_process_runtime_and_resource_contracts_fail_closed(self) -> None:
        process = self.fixture.reports[0]["results"][0]["process_evidence"]
        process["post_runtime_state"]["candle_git_status"] = [" M candle/kernel.ml"]
        self.fixture.write_reports()
        self.assert_rejected("runtime state contract mismatch")

        MODULE.PROGRAM_PATH = self.original_program
        self.temporary.cleanup()
        self.temporary = tempfile.TemporaryDirectory(
            prefix="candle-top100-schema4-finalizer-resource.",
        )
        self.fixture = Fixture(Path(self.temporary.name))
        MODULE.PROGRAM_PATH = self.fixture.program_path
        process = self.fixture.reports[0]["results"][0]["process_evidence"]
        process["resource_sampling"]["sampler_completed"] = False
        self.fixture.write_reports()
        self.assert_rejected("resource sampling")

    def test_per_process_linked_hash_must_match_current_record(self) -> None:
        fake = "f" * 64
        report_value = self.fixture.reports[0]
        old = self.fixture.linked_sha256
        report_value["run_evidence"]["linked_record_sha256"] = fake
        for result in report_value["results"]:
            result["process_evidence"]["linked_record_sha256"] = fake
            log = Path(result["log_path"])
            log.write_text(log.read_text().replace(
                f"CANDLE_LINKED_PROVENANCE_V1\t{old}",
                f"CANDLE_LINKED_PROVENANCE_V1\t{fake}",
            ))
            result["process_evidence"]["transcript"] = file_reference(log)
        self.fixture.write_reports()
        self.assert_rejected("different linked records")

    def test_post_complete_conflicting_protocol_records_fail_closed(self) -> None:
        result = self.fixture.reports[0]["results"][0]
        process = result["process_evidence"]
        log = Path(result["log_path"])
        conflicting = (
            f"CANDLE_LINKED_PROVENANCE_V1\t{'f' * 64}\n"
            f"CANDLE_GREAT100_PROCESS_V1\t{process['suite_nonce']}\t"
            f"{process['process_nonce']}\tFAIL\n"
        ).encode()
        log.write_bytes(log.read_bytes() + conflicting)
        self.fixture.refresh_transcript_identity(0, 0)
        self.fixture.write_reports()
        self.assert_rejected("unexpected or conflicting process protocol record")

    def test_unsupported_fingerprint_protocol_namespace_fails_closed(self) -> None:
        result = self.fixture.reports[0]["results"][0]
        log = Path(result["log_path"])
        log.write_bytes(log.read_bytes() + (
            b"CANDLE_FINGERPRINT_V3\tunsupported\n"
            b"CANDLE_STATE_FINGERPRINT_V3\tunsupported\n"
        ))
        self.fixture.refresh_transcript_identity(0, 0)
        self.fixture.write_reports()
        self.assert_rejected("unexpected fingerprint wire version")

    def test_transcript_protocol_namespace_is_closed(self) -> None:
        target = self.fixture.manifest["targets"][0]
        result = self.fixture.reports[0]["results"][0]
        process = result["process_evidence"]
        base = Path(result["log_path"]).read_bytes()
        cases = (
            (b"CANDLE_GREAT100_SUITE_V2\tunsupported\n", "suite protocol"),
            (b"CANDLE_GREAT100_PROCESS_V2\tunsupported\n", "process protocol"),
            (b"CANDLE_LINKED_PROVENANCE_V2\tunsupported\n", "linked protocol"),
            ((MODULE.LINKED_PASS_WITNESS + "\n").encode(), "linked PASS witness"),
            (b"CANDLE_FINGERPRINT_V3\tunsupported\n", "wire version"),
            (b"CANDLE_STATE_FINGERPRINT_V3\tunsupported\n", "wire version"),
        )
        for suffix, error_pattern in cases:
            with self.subTest(suffix=suffix):
                with self.assertRaisesRegex(MODULE.ValidationError, error_pattern):
                    MODULE.validate_transcript(
                        base + suffix, result["name"], process["suite_nonce"],
                        process["process_nonce"], self.fixture.linked_sha256,
                        target["fingerprint_request"]["expected_identities"][
                            "theorems"],
                        target["fingerprint_request"]["expected_identities"][
                            "post_state"],
                        process["markers"],
                    )

    def test_source_closure_is_live_hashed_and_committed(self) -> None:
        source = self.fixture.candle_root / "100/test-00.ml"
        source.write_bytes(source.read_bytes() + b"tamper\n")
        git(self.fixture.candle_root, "add", "100/test-00.ml")
        git(self.fixture.candle_root, "commit", "-qm", "changed source fixture")
        new_head = git(self.fixture.candle_root, "rev-parse", "HEAD")
        for report_value in self.fixture.reports:
            report_value["candle_git_head"] = new_head
        self.fixture.write_reports()
        self.assert_rejected("live source hash differs from manifest")

    def test_candidate_or_self_approval_is_not_promotable(self) -> None:
        self.fixture.approval["approval_status"] = "candidate_unapproved"
        self.fixture.approval["promotion_allowed"] = False
        self.fixture.approval_path.write_bytes(
            MODULE.canonical_json_bytes(self.fixture.approval),
        )
        new_approval = record(self.fixture.approval_path)
        for target in self.fixture.manifest["targets"]:
            target["fingerprint_request"]["expected_identities"][
                "approval_sha256"
            ] = new_approval["sha256"]
        self.fixture.manifest["identity_approval"].update({
            "sha256": new_approval["sha256"],
            "approval_status": "candidate_unapproved",
            "promotion_allowed": False,
        })
        manifest_path = self.fixture.candle / "top100_manifest.json"
        manifest_path.write_bytes(MODULE.canonical_json_bytes(self.fixture.manifest))
        git(self.fixture.candle_root, "add", "candle/top100_identity_approval.json",
            "candle/top100_manifest.json")
        git(self.fixture.candle_root, "commit", "-qm", "candidate self approval")
        new_head = git(self.fixture.candle_root, "rev-parse", "HEAD")
        new_contract = deepcopy(self.fixture.execution_contract)
        new_contract["candle/top100_manifest.json"] = record(manifest_path)
        for report_value in self.fixture.reports:
            report_value["candle_git_head"] = new_head
            report_value["execution_contract"] = deepcopy(new_contract)
            report_value["independent_approval"] = {
                "path": "candle/top100_identity_approval.json", **new_approval,
            }
            report_value["run_evidence"]["independent_approval_sha256"] = \
                new_approval["sha256"]
        self.fixture.approval_identity = new_approval
        self.fixture.write_reports()
        self.assert_rejected("identity-approval metadata mismatch")

    def test_external_receipt_binds_finalizer_project_and_tools(self) -> None:
        self.fixture.authorization["project"]["finalizer"]["sha256"] = "0" * 64
        self.fixture.write_authorization()
        self.assert_rejected("does not bind finalizer")

    def test_external_receipt_digest_is_out_of_band(self) -> None:
        expected_digest = self.fixture.authorization_sha256
        self.fixture.authorization_path.write_bytes(
            self.fixture.authorization_path.read_bytes() + b" \n",
        )
        self.fixture.authorization_sha256 = expected_digest
        self.assert_rejected("receipt digest mismatch")

    def test_helper_mutation_after_capture_cannot_change_executed_bytes(self) -> None:
        helper = self.fixture.candle / "cakeml_artifact_provenance.py"

        def mutate() -> None:
            helper.write_text("print('forged helper')\n")

        MODULE._TEST_AFTER_CONTRACT_CAPTURE = mutate
        self.assert_rejected("worktree is not clean")

    def test_arbitrary_or_legacy_candidate_attachment_is_not_evidence(self) -> None:
        self.fixture.replace_reference_artifact(
            0, 0, "candidate", b"arbitrary legacy candidate text\n",
        )
        self.assert_rejected("malformed JSON")

        MODULE.PROGRAM_PATH = self.original_program
        self.temporary.cleanup()
        self.temporary = tempfile.TemporaryDirectory(
            prefix="candle-top100-schema4-finalizer-legacy-candidate.",
        )
        self.fixture = Fixture(Path(self.temporary.name))
        MODULE.PROGRAM_PATH = self.fixture.program_path
        artifact = self.fixture.approval["targets"][0]["reference_runs"][0][
            "artifacts"]["candidate"]
        candidate_path = self.fixture.candle_root / artifact["path"]
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate["schema"] = "candle-s1-reference-candidate-v5"
        self.fixture.replace_reference_artifact(
            0, 0, "candidate", MODULE.canonical_json_bytes(candidate),
        )
        self.assert_rejected("legacy or unsupported reference candidate")

    def test_reference_transcript_must_replay_to_candidate(self) -> None:
        artifact = self.fixture.approval["targets"][0]["reference_runs"][0][
            "artifacts"]["transcript"]
        transcript_path = self.fixture.candle_root / artifact["path"]
        lines = transcript_path.read_text(encoding="utf-8").splitlines()
        wire_index = next(index for index, line in enumerate(lines)
                          if line.startswith(MODULE.FINGERPRINT_MARKER))
        fields = lines[wire_index].split("\t")
        fields[2] = b"forged reference theorem".hex()
        lines[wire_index] = "\t".join(fields)
        self.fixture.replace_reference_artifact(
            0, 0, "transcript", ("\n".join(lines) + "\n").encode(),
        )
        self.assert_rejected("captured v6 reference candidate replay failed")

    def test_reference_request_must_regenerate_from_target_and_nonce(self) -> None:
        run = self.fixture.approval["targets"][0]["reference_runs"][0]
        request_value = b"arbitrary but internally linked request\n"
        self.fixture.replace_reference_artifact(
            0, 0, "request", request_value,
        )
        plan_artifact = run["artifacts"]["plan"]
        plan_path = self.fixture.candle_root / plan_artifact["path"]
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["request"] = {
            "source": request_value.decode(), "sha256": digest(request_value),
        }
        self.fixture.replace_reference_artifact(
            0, 0, "plan", MODULE.canonical_json_bytes(plan),
        )
        self.assert_rejected("captured v6 reference candidate replay failed")

    def test_reference_plan_target_is_bound(self) -> None:
        artifact = self.fixture.approval["targets"][0]["reference_runs"][0][
            "artifacts"]["plan"]
        plan_path = self.fixture.candle_root / artifact["path"]
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["input"]["target"] = "100/test-01"
        self.fixture.replace_reference_artifact(
            0, 0, "plan", MODULE.canonical_json_bytes(plan),
        )
        self.assert_rejected("reference plan target/mode mismatch")

    def test_reference_plan_head_is_bound(self) -> None:
        artifact = self.fixture.approval["targets"][0]["reference_runs"][0][
            "artifacts"]["plan"]
        plan_path = self.fixture.candle_root / artifact["path"]
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["reference"]["git_head"] = "a" * 40
        self.fixture.replace_reference_artifact(
            0, 0, "plan", MODULE.canonical_json_bytes(plan),
        )
        self.assert_rejected("reference plan head/status mismatch")

    def test_reference_plan_nonce_is_bound(self) -> None:
        artifact = self.fixture.approval["targets"][0]["reference_runs"][0][
            "artifacts"]["plan"]
        plan_path = self.fixture.candle_root / artifact["path"]
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["session_nonce"] = "b" * 64
        self.fixture.replace_reference_artifact(
            0, 0, "plan", MODULE.canonical_json_bytes(plan),
        )
        self.assert_rejected("plan/candidate nonce mismatch")

    def test_reference_plan_source_contract_is_bound(self) -> None:
        artifact = self.fixture.approval["targets"][0]["reference_runs"][0][
            "artifacts"]["plan"]
        plan_path = self.fixture.candle_root / artifact["path"]
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["input"]["source_contract"]["sha256"] = "c" * 64
        self.fixture.replace_reference_artifact(
            0, 0, "plan", MODULE.canonical_json_bytes(plan),
        )
        self.assert_rejected("reference source-contract binding mismatch")

    def test_reference_plan_selected_sources_are_bound(self) -> None:
        artifact = self.fixture.approval["targets"][0]["reference_runs"][0][
            "artifacts"]["plan"]
        plan_path = self.fixture.candle_root / artifact["path"]
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["input"]["load_files"][0]["sha256"] = "d" * 64
        self.fixture.replace_reference_artifact(
            0, 0, "plan", MODULE.canonical_json_bytes(plan),
        )
        self.assert_rejected("reference selected-source binding mismatch")

    def test_reference_candidate_projection_must_equal_approval(self) -> None:
        artifact = self.fixture.approval["targets"][0]["reference_runs"][0][
            "artifacts"]["candidate"]
        candidate_path = self.fixture.candle_root / artifact["path"]
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate["candidate_identities"]["theorems"][0][
            "theorem_sha256"] = "f" * 64
        self.fixture.replace_reference_artifact(
            0, 0, "candidate", MODULE.canonical_json_bytes(candidate),
        )
        self.assert_rejected("candidate identity projection differs")

    def test_symlink_log_and_duplicate_process_nonce_fail_closed(self) -> None:
        log = Path(self.fixture.reports[0]["results"][0]["log_path"])
        target = Path(self.fixture.reports[1]["results"][0]["log_path"])
        log.unlink()
        log.symlink_to(target)
        self.assert_rejected("symlink")

        # A fresh fixture exercises nonce reuse independently of the symlink.
        MODULE.PROGRAM_PATH = self.original_program
        self.temporary.cleanup()
        self.temporary = tempfile.TemporaryDirectory(
            prefix="candle-top100-schema4-finalizer-nonce.",
        )
        self.fixture = Fixture(Path(self.temporary.name))
        MODULE.PROGRAM_PATH = self.fixture.program_path
        duplicate = self.fixture.reports[0]["results"][0]["process_evidence"][
            "process_nonce"
        ]
        result = self.fixture.reports[0]["results"][1]
        old = result["process_evidence"]["process_nonce"]
        result["process_evidence"]["process_nonce"] = duplicate
        log = Path(result["log_path"])
        log.write_text(log.read_text().replace(old, duplicate))
        result["process_evidence"]["transcript"] = file_reference(log)
        self.fixture.write_reports()
        self.assert_rejected("duplicate process nonce")

    def test_cli_requires_receipt_and_digest(self) -> None:
        completed = subprocess.run(
            [str(MODULE.PYTHON_PATH), "-I", str(SCRIPT),
             str(self.fixture.report_paths[0]), str(self.fixture.report_paths[1]),
             str(self.fixture.destination)],
            check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("--external-receipt", completed.stderr)


if __name__ == "__main__":
    unittest.main()
