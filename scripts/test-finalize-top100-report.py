#!/usr/bin/env python3
"""Adversarial fixtures for the schema-4 Great100 evidence finalizer."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
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


def elf_evidence(roots: list[Path]) -> dict:
    """Build real host-backed ELF evidence for finalizer fixtures."""
    bash = MODULE.executable_route_record(Path("/bin/bash"), "fixture ELF bash")
    ldd = MODULE.executable_route_record(Path("/usr/bin/ldd"), "fixture ELF ldd")
    loaders = []
    for path in (
        Path("/lib/ld-linux.so.2"),
        Path("/lib64/ld-linux-x86-64.so.2"),
        Path("/libx32/ld-linux-x32.so.2"),
    ):
        if not os.path.lexists(path):
            loaders.append({"argument_path": str(path), "status": "absent"})
        else:
            loaders.append({
                "argument_path": str(path), "status": "present",
                "route": MODULE.executable_route_record(
                    path, f"fixture ELF loader {path}",
                ),
            })
    root_paths = sorted({str(path.resolve()) for path in roots})
    observations = []
    closure = {}
    mapped = re.compile(
        r"(?P<role>[^\s]+)\s+=>\s+(?P<path>/[^\s(]+)\s+"
        r"\(0x[0-9a-fA-F]+\)",
    )
    direct = re.compile(r"(?P<path>/[^\s(]+)\s+\(0x[0-9a-fA-F]+\)")
    virtual = re.compile(
        r"(?P<role>linux-(?:vdso|gate)\.so\.1)\s+"
        r"\(0x[0-9a-fA-F]+\)",
    )
    observation_roots = sorted(set(root_paths) | {
        bash["resolved_executable"]["path"],
    })
    for root in observation_roots:
        completed = subprocess.run(
            ["/bin/bash", "/usr/bin/ldd", root],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C"},
        )
        resolved_files = []
        virtual_objects = []
        for raw in completed.stdout.splitlines():
            line = raw.strip()
            match = mapped.fullmatch(line)
            if match is not None:
                role = match.group("role")
                reported = match.group("path")
            else:
                match = direct.fullmatch(line)
                if match is not None:
                    reported = match.group("path")
                    role = Path(reported).name
                else:
                    match = virtual.fullmatch(line)
                    if match is None:
                        raise RuntimeError(f"unexpected fixture ldd line: {line}")
                    virtual_objects.append(match.group("role"))
                    continue
            resolved = Path(reported).resolve()
            pin = {"path": str(resolved), "sha256": digest(resolved.read_bytes())}
            resolved_files.append({
                "role": role, "reported_path": reported, **pin,
            })
            closure[str(resolved)] = pin
        resolved_files.sort(
            key=lambda item: (item["role"], item["reported_path"], item["path"]),
        )
        normalized = re.sub(
            r"\(0x[0-9a-fA-F]+\)", "(0xADDRESS)", completed.stdout,
        )
        root_path = Path(root)
        observations.append({
            "root": {"path": root, "sha256": digest(root_path.read_bytes())},
            "argv": ["/bin/bash", "/usr/bin/ldd", root],
            "environment": {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C"},
            "return_code": 0,
            "stdout": completed.stdout,
            "stdout_sha256": digest(completed.stdout.encode()),
            "normalized_stdout": normalized,
            "normalized_stdout_sha256": digest(normalized.encode()),
            "stderr": completed.stderr,
            "stderr_sha256": digest(completed.stderr.encode()),
            "resolved_files": resolved_files,
            "virtual_objects": sorted(virtual_objects),
        })
    cache = Path("/etc/ld.so.cache")
    return {
        "policy": "authenticated_explicit_bash_ldd_closure_v1",
        "output_normalization":
            "strict_recognized_lines_replace_only_aslr_addresses_v1",
        "tools": {"bash": bash, "ldd": ldd},
        "hardcoded_loader_routes": loaders,
        "ld_so_cache": {"path": str(cache), "sha256": digest(cache.read_bytes())},
        "ld_so_preload": {"path": "/etc/ld.so.preload", "status": "absent"},
        "environment": {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C"},
        "requested_roots": [
            {"path": path, "sha256": digest(Path(path).read_bytes())}
            for path in root_paths
        ],
        "observations": observations,
        "closure": [closure[path] for path in sorted(closure)],
    }


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
        self._commit_candle_repository()
        self.collection_candle_head = self.candle_head
        self._create_approval()
        for target in self.manifest["targets"]:
            target["fingerprint_request"]["expected_identities"][
                "approval_sha256"
            ] = self.approval_identity["sha256"]
        self.manifest["identity_approval"] = {
            "path": "candle/top100_identity_approval.json",
            "sha256": self.approval_identity["sha256"],
            "schema": "candle-s1-identity-approval-v2",
            "approval_status": "approved",
            "promotion_allowed": True,
        }
        (self.candle / "top100_manifest.json").write_bytes(
            MODULE.canonical_json_bytes(self.manifest),
        )
        git(self.candle_root, "add", ".")
        git(self.candle_root, "commit", "-qm", "fixture approved Candle")
        self.candle_head = git(self.candle_root, "rev-parse", "HEAD")
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
        controller_path = (
            self.project_root / "scripts/run-top100-reference-sweeps.py"
        )
        controller_path.write_bytes(
            b"#!/usr/bin/python3\n# fixture collection controller\n"
        )
        controller_path.chmod(0o755)
        git(self.project_root, "init", "-q")
        git(self.project_root, "config", "user.email", "fixture@example.invalid")
        git(self.project_root, "config", "user.name", "fixture")
        git(self.project_root, "add", ".")
        git(self.project_root, "commit", "-qm", "fixture collection launch")
        self.collection_project_head = git(
            self.project_root, "rev-parse", "HEAD",
        )
        controller_record = record(controller_path)
        MODULE.COLLECTION_PROJECT_HEAD = self.collection_project_head
        MODULE.COLLECTION_CONTROLLER_BYTES = controller_record["bytes"]
        MODULE.COLLECTION_CONTROLLER_SHA256 = controller_record["sha256"]
        self._write(
            self.project_root, "docs/finalizer-revision.md",
            b"later finalizer authority fixture\n",
        )
        git(self.project_root, "add", ".")
        git(self.project_root, "commit", "-qm", "later fixture finalizer")
        self.project_head = git(self.project_root, "rev-parse", "HEAD")
        self.collection_project_root = self.root / "collection-launch-project"
        git(
            self.project_root, "worktree", "add", "--detach",
            str(self.collection_project_root), self.collection_project_head,
        )

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
        reviewed_delta_sources = (
            "100/e_is_transcendental.ml", "100/euler.ml", "100/lagrange.ml",
        )
        self._write(self.candle_root, extra, b"extra first-target source\n")
        for index in range(65):
            name = f"100/test-{index:02d}"
            source = (reviewed_delta_sources[index] if index < 3
                      else f"{name}.ml")
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
import subprocess
import tempfile

import regression

SESSION_MARKER = "CANDLE_REFERENCE_SESSION_V1"
COMPLETE_MARKER = "CANDLE_REFERENCE_COMPLETE_V1"
PLAN_SCHEMA = "candle-s1-reference-plan-v9"
CANDIDATE_SCHEMA = "candle-s1-reference-candidate-v9"


class CollectionError(Exception):
    pass


def _stable_elf_evidence(evidence):
    stable = json.loads(json.dumps(evidence))
    for observation in stable["observations"]:
        observation.pop("stdout")
        observation.pop("stdout_sha256")
    return stable


def validate_elf_closure_evidence_live(evidence, expected_roots):
    expected_roots = sorted(set(expected_roots))
    if sorted(item["path"] for item in evidence["requested_roots"]) != \
            expected_roots:
        raise CollectionError("fixture ELF root mismatch")
    mapped = re.compile(
        r"(?P<role>[^\s]+)\s+=>\s+(?P<path>/[^\s(]+)\s+"
        r"\(0x[0-9a-fA-F]+\)")
    direct = re.compile(r"(?P<path>/[^\s(]+)\s+\(0x[0-9a-fA-F]+\)")
    virtual = re.compile(
        r"(?P<role>linux-(?:vdso|gate)\.so\.1)\s+"
        r"\(0x[0-9a-fA-F]+\)")
    observations = []
    closure = {}
    observation_roots = sorted(set(expected_roots) | {
        evidence["tools"]["bash"]["resolved_executable"]["path"],
    })
    for root in observation_roots:
        completed = subprocess.run(
            ["/bin/bash", "/usr/bin/ldd", root], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C"},
        )
        if completed.stderr != "":
            raise CollectionError("fixture ldd stderr is not empty")
        resolved_files = []
        virtual_objects = []
        for raw in completed.stdout.splitlines():
            line = raw.strip()
            match = mapped.fullmatch(line)
            if match is not None:
                role, reported = match.group("role"), match.group("path")
            else:
                match = direct.fullmatch(line)
                if match is not None:
                    reported = match.group("path")
                    role = Path(reported).name
                else:
                    match = virtual.fullmatch(line)
                    if match is None:
                        raise CollectionError("fixture ldd output is malformed")
                    virtual_objects.append(match.group("role"))
                    continue
            resolved = Path(reported).resolve(strict=True)
            pin = {
                "path": str(resolved),
                "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
            }
            resolved_files.append({
                "role": role, "reported_path": reported, **pin,
            })
            closure[str(resolved)] = pin
        resolved_files.sort(key=lambda item: (
            item["role"], item["reported_path"], item["path"]))
        normalized = re.sub(
            r"\(0x[0-9a-fA-F]+\)", "(0xADDRESS)", completed.stdout)
        root_path = Path(root)
        observations.append({
            "root": {
                "path": root,
                "sha256": hashlib.sha256(root_path.read_bytes()).hexdigest(),
            },
            "argv": ["/bin/bash", "/usr/bin/ldd", root],
            "environment": {
                "PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C",
            },
            "return_code": 0,
            "normalized_stdout": normalized,
            "normalized_stdout_sha256": hashlib.sha256(
                normalized.encode()).hexdigest(),
            "stderr": "", "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "resolved_files": resolved_files,
            "virtual_objects": sorted(virtual_objects),
        })
    stable = _stable_elf_evidence(evidence)
    expected_stable = json.loads(json.dumps(stable))
    expected_stable["observations"] = observations
    expected_stable["closure"] = [closure[path] for path in sorted(closure)]
    if stable != expected_stable:
        raise CollectionError("fixture live ELF evidence differs from plan")
    return evidence


def _require_current_plan_pins(plan):
    reference = plan["reference"]
    runtime = Path(reference["runtime_executable"]["path"])
    first_line = runtime.read_bytes().split(b"\n", 1)[0]
    match = re.fullmatch(br"#!(/[^\x00-\x20]+)(?:[ \t]+.*)?", first_line)
    if match is None:
        raise CollectionError("fixture runtime shebang is malformed")
    interpreter = Path(match.group(1).decode()).resolve(strict=True)
    expected_interpreter = {
        "path": str(interpreter),
        "sha256": hashlib.sha256(interpreter.read_bytes()).hexdigest(),
    }
    if reference["runtime_interpreter"] != expected_interpreter:
        raise CollectionError("fixture runtime interpreter differs from live plan")
    hol_ml = Path(reference["root"]) / "hol.ml"
    expected_hol_ml = {
        "path": str(hol_ml.resolve(strict=True)),
        "sha256": hashlib.sha256(hol_ml.read_bytes()).hexdigest(),
    }
    if reference["hol_ml"] != expected_hol_ml:
        raise CollectionError("fixture hol.ml differs from live plan")
    roots = {
        Path(reference["runtime_stublib"]["path"]).parent,
        Path(reference["ocamlc"]["stdlib_directory"]) / "stublibs",
        *(Path(item["root"]) / "stublibs"
          for item in reference["findlib"]["package_roots"]),
    }
    observed = {}
    for root in roots:
        if root.is_dir():
            for path in root.glob("*.so"):
                resolved = path.resolve(strict=True)
                observed[str(resolved)] = {
                    "path": str(resolved),
                    "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
                }
    expected = [observed[path] for path in sorted(observed)]
    if reference["runtime_stub_files"] != expected:
        raise CollectionError("fixture runtime stubs differ from live plan")


def _rebuild_plan(plan):
    _require_current_plan_pins(plan)
    return json.loads(json.dumps(plan))


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
        self._write(
            self.candle_root, "candle/reference_protocol.py",
            b'"""Pinned reference protocol fixture."""\n',
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
        tools_root = self.root / "reference-tools"
        reference_root = tools_root / "reference"
        reference_root.mkdir(parents=True)
        self.reference_root = reference_root
        for relative in sorted({
            relative
            for target in self.manifest["targets"]
            for relative in target["load_files"]
        }):
            self._write(
                reference_root, relative,
                (self.candle_root / relative).read_bytes(),
            )
        delta_paths = (
            "100/e_is_transcendental.ml", "100/euler.ml", "100/lagrange.ml",
        )
        historical_values = {}
        for index, relative in enumerate(delta_paths):
            value = f"(* historical fixture delta {index} *)\n".encode()
            historical_values[relative] = value
            self._write(reference_root, relative, value)
        self._write(
            reference_root, ".gitignore",
            (b"/ocaml-hol\n/hol.ml\n/stublibs/\n/bin/\n/ocamlfind.conf\n"
             b"/ocaml/\n/hol_loader.cmo\n/pa_j.cmo\n"
             b"/load_camlp5_topfind.ml\n"),
        )
        git(reference_root, "init", "-q")
        git(reference_root, "config", "user.email", "fixture@example.invalid")
        git(reference_root, "config", "user.name", "fixture")
        git(reference_root, "add", ".")
        git(reference_root, "commit", "-qm", "historical fixture reference")
        self.historical_reference_head = git(
            reference_root, "rev-parse", "HEAD",
        )
        deltas = []
        for index, path in enumerate(delta_paths):
            selected = (self.candle_root / path).read_bytes()
            self._write(reference_root, path, selected)
            deltas.append({
                "path": path,
                "historical_sha256": digest(historical_values[path]),
                "selected_sha256": digest(selected),
                "reason": f"reviewed fixture delta {index}",
            })
        git(reference_root, "add", *delta_paths)
        git(reference_root, "commit", "-qm", "exact fixture reference")
        self.reference_head = git(reference_root, "rev-parse", "HEAD")
        reference_policy = {
            "historical_upstream_commit": self.historical_reference_head,
            "exact_source_reference_commit": self.reference_head,
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
        git(self.candle_root, "add", "candle/reference_source_contracts.json")
        git(self.candle_root, "commit", "-qm", "fixture collection source contract")
        self.collection_candle_head = git(
            self.candle_root, "rev-parse", "HEAD",
        )
        collector = self.candle / "reference_fingerprints.py"
        collector_sha256 = digest(collector.read_bytes())
        protocol = self.candle / "reference_protocol.py"
        protocol_sha256 = digest(protocol.read_bytes())
        manifest_pin = self.candle / "top100_manifest.json"
        runtime = self._write(
            reference_root, "ocaml-hol", b"#!/bin/sh\nexit 0\n")
        runtime.chmod(0o755)
        hol_ml = self._write(reference_root, "hol.ml", b"(* fixture hol *)\n")
        runtime_stublib = self._write(
            reference_root, "stublibs/dllzarith.so",
            Path("/lib/x86_64-linux-gnu/libdl.so.2").read_bytes())
        runtime_stub = self._write(
            reference_root, "stublibs/dllunix.so",
            Path("/lib/x86_64-linux-gnu/libpthread.so.0").read_bytes())
        ocamlc_path = self._write(
            reference_root, "bin/ocamlc", b"#!/bin/sh\nexit 0\n")
        ocamlc_path.chmod(0o755)
        ocamlfind_path = self._write(
            reference_root, "bin/ocamlfind", b"#!/bin/sh\nexit 0\n")
        ocamlfind_path.chmod(0o755)
        findlib_config = self._write(
            reference_root, "ocamlfind.conf", b"path=ocaml\n")
        self._write(reference_root, "ocaml/stdlib.cma", b"fixture stdlib\n")
        boot_files = [
            self._write(reference_root, "hol_loader.cmo", b"fixture loader\n"),
            self._write(reference_root, "pa_j.cmo", b"fixture parser\n"),
            self._write(
                reference_root, "load_camlp5_topfind.ml", b"fixture topfind\n"),
        ]
        gp_root = tools_root / "pari"
        gp_bin = gp_root / "usr/bin"
        gp_bin.mkdir(parents=True)
        gp_source = self._write(
            gp_root, "usr/bin/gp-fixture.c",
            (b"#include <stdio.h>\n#include <string.h>\n"
             b"int main(int argc, char **argv) {\n"
             b"  if (argc > 1 && strcmp(argv[1], \"--version-short\") == 0) "
             b"{ puts(\"2.15.4\"); return 0; }\n"
             b"  while (getchar() != EOF) {}\n"
             b"  puts(\"1\"); puts(\"[3, 1; 5, 1]\"); return 0;\n}\n"),
        )
        gp_executable = gp_root / "usr/bin/gp-2.15"
        subprocess.run(
            ["/usr/bin/cc", "-O0", "-o", str(gp_executable), str(gp_source)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        (gp_bin / "gp").symlink_to("gp-2.15")
        csdp_source = self._write(
            gp_root, "candle-csdp-source.tar.gz", b"fixture CSDP source\n",
        )
        csdp_source.chmod(0o444)
        csdp_probe_input = self._write(
            gp_root, "candle-csdp-theta1.dat-s", b"fixture theta1 input\n",
        )
        csdp_probe_input.chmod(0o444)
        csdp_program = self._write(
            gp_root, "usr/bin/csdp-fixture.c",
            (b'#include <stdio.h>\n'
             b'int main(int argc, char **argv) {\n'
             b'  if (argc != 3) return 2;\n'
             b'  FILE *out = fopen(argv[2], "wb");\n'
             b'  if (!out) return 3;\n'
             b'  fputs("fixture csdp solution\\n", out); fclose(out);\n'
             b'  puts("CSDP 6.2.0");\n'
             b'  puts("Success: SDP solved");\n'
             b'  puts("Primal objective value: 2.3000000e+01 ");\n'
             b'  puts("Dual objective value: 2.3000000e+01 ");\n'
             b'  puts("Elements time: 0.01 ");\n'
             b'  puts("Factor time: 0.02 ");\n'
             b'  puts("Other time: 0.03 ");\n'
             b'  puts("Total time: 0.06 ");\n'
             b'  return 0;\n}\n'),
        )
        csdp_executable = gp_root / "usr/bin/csdp"
        subprocess.run(
            ["/usr/bin/cc", "-O0", "-o", str(csdp_executable),
             str(csdp_program)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        csdp_executable.chmod(0o555)
        csdp_solution = b"fixture csdp solution\n"
        csdp_normalized_stdout = (
            "CSDP 6.2.0\n"
            "Success: SDP solved\n"
            "Primal objective value: 2.3000000e+01 \n"
            "Dual objective value: 2.3000000e+01 \n"
            "Elements time: <measured>\n"
            "Factor time: <measured>\n"
            "Other time: <measured>\n"
            "Total time: <measured>\n"
        )
        csdp_build_statement = {
            "schema": 1,
            "kind": MODULE.CSDP_BUILD_KIND,
            "source": {
                "archive": csdp_source.name,
                "bytes": csdp_source.stat().st_size,
                "sha256": digest(csdp_source.read_bytes()),
                "ubuntu_source_package":
                    "coinor-csdp 6.2.0-5build1 (Noble)",
                "upstream_tree": "Csdp-6.2.0",
            },
            "toolchain": deepcopy(MODULE.CSDP_TOOLCHAIN),
            "recipe": deepcopy(MODULE.CSDP_RECIPE),
            "outputs": {
                "csdp_path": "usr/bin/csdp",
                "csdp_bytes": csdp_executable.stat().st_size,
                "csdp_sha256": digest(csdp_executable.read_bytes()),
                "static_libsdp_sha256": MODULE.CSDP_STATIC_LIBSDP_SHA256,
            },
            "unit_probe": {
                "input_path": csdp_probe_input.name,
                "input_bytes": csdp_probe_input.stat().st_size,
                "input_sha256": digest(csdp_probe_input.read_bytes()),
                "exit_code": 0,
                "success_line": MODULE.CSDP_PROBE_SUCCESS,
                "primal_objective": MODULE.CSDP_PROBE_PRIMAL,
                "dual_objective": MODULE.CSDP_PROBE_DUAL,
                "maximum_allowed_dimacs_error": "1.0e-6",
            },
            "runtime_policy": {
                "single_process_solver": True,
                "single_thread_build": True,
                "external_shared_libraries_closed_separately": True,
            },
        }
        csdp_build_receipt = self._write(
            gp_root, "candle-csdp-build.json",
            MODULE.canonical_json_bytes(csdp_build_statement),
        )
        csdp_build_receipt.chmod(0o444)
        gprc = self._write(
            gp_root, "candle-gprc", b"\\\\ pinned fixture configuration\n",
        )
        gprc.chmod(0o444)
        data_root = gp_root / "candle-data"
        data_root.mkdir()
        data_root.chmod(0o555)
        package_archive = self._write(
            tools_root, "pari.deb", b"pinned package archive\n",
        )
        package_archive.chmod(0o444)
        shell = Path("/bin/sh")
        runtime_tree, _ = MODULE.tree_inventory(
            runtime_stublib.parent, "fixture runtime-library tree")
        ocaml_tree, _ = MODULE.tree_inventory(
            reference_root / "ocaml", "fixture OCaml-library tree")
        package_tree, _ = MODULE.tree_inventory(gp_root, "fixture GP tree")
        data_tree, _ = MODULE.tree_inventory(data_root, "fixture GP data tree")
        gp_stdout = "1\n[3, 1; 5, 1]\n"
        external_environment = {
            "HOME": str(reference_root),
            "PATH": str(gp_bin),
            "LC_ALL": "C",
            "GPRC": str(gprc),
            "GP_DATA_DIR": str(data_root),
            **MODULE.THREAD_CAP_ENVIRONMENT,
        }
        probe_source = (
            "echo 'print(default(nbthreads)); print(factorint(15))  \n quit' | gp")
        core_elf_runtime = elf_evidence([
            shell.resolve(), runtime_stub, runtime_stublib,
        ])
        external_elf_runtime = elf_evidence([
            shell.resolve(), gp_executable.resolve(), csdp_executable,
        ])
        external_runtime = {
            "policy": MODULE.EXTERNAL_RUNTIME_POLICY,
            "command_shell": MODULE.executable_route_record(shell, "fixture shell"),
            "pari_gp": MODULE.executable_route_record(
                gp_bin / "gp", "fixture PARI/GP",
            ),
            "pari_gp_version": {
                "stdout": "2.15.4\n", "sha256": digest(b"2.15.4\n"),
            },
            "csdp": MODULE.executable_route_record(
                csdp_executable, "fixture CSDP",
            ),
            "csdp_bytes": csdp_executable.stat().st_size,
            "package_archive": {
                "path": str(package_archive),
                "sha256": digest(package_archive.read_bytes()),
            },
            "package_tree": package_tree,
            "configuration": {
                "path": str(gprc), "sha256": digest(gprc.read_bytes()),
            },
            "data_tree": data_tree,
            "csdp_source_archive": {
                "path": str(csdp_source),
                "sha256": digest(csdp_source.read_bytes()),
                "bytes": csdp_source.stat().st_size,
            },
            "csdp_build": {
                "receipt": {
                    "path": str(csdp_build_receipt),
                    "sha256": digest(csdp_build_receipt.read_bytes()),
                },
                "statement": csdp_build_statement,
            },
            "csdp_probe_input": {
                "path": str(csdp_probe_input),
                "sha256": digest(csdp_probe_input.read_bytes()),
                "bytes": csdp_probe_input.stat().st_size,
            },
            "thread_policy": {
                "single_process_solver": True,
                "single_thread_build": True,
                "openmp_enabled": False,
                "native_cpu_flags": False,
                "environment": deepcopy(MODULE.THREAD_CAP_ENVIRONMENT),
                "forbidden_elf_dependency_name_fragments":
                    list(MODULE.CSDP_FORBIDDEN_ELF_FRAGMENTS),
            },
            "elf_runtime": external_elf_runtime,
            "probe": {
                "shell_argv": [str(shell), "-c", probe_source],
                "environment": external_environment,
                "return_code": 0, "stdout": gp_stdout,
                "stdout_sha256": digest(gp_stdout.encode()),
                "stderr": "", "stderr_sha256": digest(b""),
            },
            "csdp_probe": {
                "argv_template": [
                    str(csdp_executable), str(csdp_probe_input),
                    "<private-temporary-output>",
                ],
                "environment": deepcopy(external_environment),
                "return_code": 0,
                "normalized_stdout": csdp_normalized_stdout,
                "normalized_stdout_sha256": digest(
                    csdp_normalized_stdout.encode()),
                "stderr": "", "stderr_sha256": digest(b""),
                "solution": {
                    "bytes": len(csdp_solution),
                    "sha256": digest(csdp_solution),
                },
            },
        }
        collection_deadlines = {
            "collection_wall_seconds": 21600,
            "target_wall_seconds": 21660,
            "validation_wall_seconds": 900,
        }
        collection_rows = {1: [], 2: []}
        targets = []
        for target_index, semantic in enumerate(self.semantics):
            target = self.manifest["targets"][target_index]
            expected_identity = deepcopy(semantic["expected_identity"])
            identity_sha256 = MODULE.compact_json_sha256(expected_identity)
            runs = []
            for run_index in range(2):
                nonce = f"{5000 + target_index * 2 + run_index:064x}"
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
                    "schema": "candle-s1-reference-plan-v9",
                    "status": "planned_not_executed",
                    "session_nonce": nonce,
                    "fresh_process_contract": {
                        "required": True,
                        "preloaded_checkpoint_allowed": False,
                        "working_directory": str(reference_root),
                        "environment_policy":
                            "sanitized_allowlist_no_inherited_overrides",
                        "runtime_argv": [
                            str(runtime), "-init", str(hol_ml), "-I",
                            str(reference_root), "-noprompt",
                        ],
                        "runtime_environment": {
                            **external_environment,
                            "HOLLIGHT_DIR": str(reference_root),
                            "HOLLIGHT_USE_MODULE": "0",
                            "OCAMLRUNPARAM": "l=2000000000",
                            "CAML_LD_LIBRARY_PATH": str(runtime_stublib.parent),
                            "OCAML_TOPLEVEL_PATH": str(reference_root / "ocaml"),
                            "OCAMLFIND_CONF": str(findlib_config),
                        },
                    },
                    "reference": {
                        "root": str(reference_root),
                        "git_head": self.reference_head,
                        "git_status": [],
                        "runtime_executable": {
                            "path": str(runtime), "sha256": digest(runtime.read_bytes())},
                        "runtime_interpreter": {
                            "path": str(Path("/bin/sh").resolve()),
                            "sha256": digest(Path("/bin/sh").resolve().read_bytes())},
                        "runtime_stublib": {
                            "path": str(runtime_stublib),
                            "sha256": digest(runtime_stublib.read_bytes())},
                        "runtime_library_tree": runtime_tree,
                        "runtime_stub_files": sorted([
                            {"path": str(runtime_stub),
                             "sha256": digest(runtime_stub.read_bytes())},
                            {"path": str(runtime_stublib),
                             "sha256": digest(runtime_stublib.read_bytes())},
                        ], key=lambda value: value["path"]),
                        "elf_runtime": core_elf_runtime,
                        "ocamlc": {
                            "path": str(ocamlc_path),
                            "sha256": digest(ocamlc_path.read_bytes()),
                            "version": "4.14.1",
                            "stdlib_directory": str(reference_root / "ocaml")},
                        "findlib": {
                            "executable": {
                                "path": str(ocamlfind_path),
                                "sha256": digest(ocamlfind_path.read_bytes())},
                            "version": "1.9.6",
                            "configuration": {
                                "path": str(findlib_config),
                                "sha256": digest(findlib_config.read_bytes())},
                            "package_roots": [ocaml_tree]},
                        "hol_ml": {
                            "path": str(hol_ml), "sha256": digest(hol_ml.read_bytes())},
                        "generated_boot_files": [{
                            "path": str(path), "sha256": digest(path.read_bytes())}
                            for path in boot_files],
                        "ocaml_library_tree": ocaml_tree,
                        "external_runtime": external_runtime,
                    },
                    "input": {
                        "collector": {
                            "path": str(collector), "sha256": collector_sha256,
                        },
                        "collector_repository": {
                            "root": str(self.candle_root),
                            "git_head": self.collection_candle_head,
                            "git_status": [],
                            "collector_relative_path":
                                "candle/reference_fingerprints.py",
                            "collector_at_head_sha256": collector_sha256,
                            "collector_matches_head": True,
                            "support_relative_path":
                                "candle/reference_protocol.py",
                            "support_at_head_sha256": protocol_sha256,
                            "support_matches_head": True,
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
                    "schema": "candle-s1-reference-candidate-v9",
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
                sweep = run_index + 1
                directory = (
                    self.approval_root / f"sweep-{sweep}" /
                    f"target-{target_index + 1:03d}" / "attempt-0001")
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
                output_records = {}
                candidate_absolute = directory / "candidate.json"
                for field, filename, value in (
                    ("collector_stdout", "collect.stdout", (
                        f"unapproved reference candidate: "
                        f"{candidate_absolute}\n"
                    ).encode()),
                    ("collector_stderr", "collect.stderr", b""),
                    ("validator_stdout", "validate.stdout", (
                        "candidate and linked artifacts valid but unapproved: "
                        f"{candidate_absolute}\n"
                    ).encode()),
                    ("validator_stderr", "validate.stderr", b""),
                ):
                    output_path = directory / filename
                    output_path.write_bytes(value)
                    output_records[field] = {
                        "path": output_path.relative_to(
                            self.approval_root).as_posix(),
                        **record(output_path),
                    }
                    artifacts[field] = {
                        "path": output_path.relative_to(
                            self.candle_root).as_posix(),
                        **record(output_path),
                    }
                collected_artifacts = {
                    artifact_name: {
                        "path": (self.candle_root / artifact["path"]).relative_to(
                            self.approval_root).as_posix(),
                        "bytes": artifact["bytes"],
                        "sha256": artifact["sha256"],
                    }
                    for artifact_name, artifact in artifacts.items()
                    if artifact_name in {
                        "candidate", "plan", "request", "transcript"}
                }
                success = {
                    "schema": 1,
                    "kind": "candle-reference-attempt-success",
                    "sweep": sweep, "target_index": target_index + 1,
                    "target": target["name"], "session_nonce": nonce,
                    "artifacts": collected_artifacts,
                    **output_records,
                    "deadlines": collection_deadlines,
                    "approval_status": "candidate_unapproved",
                    "promotion_allowed": False,
                }
                success_path = directory / "success.json"
                success_path.write_bytes(MODULE.canonical_json_bytes(success))
                artifacts["controller_success"] = {
                    "path": success_path.relative_to(
                        self.candle_root).as_posix(),
                    **record(success_path),
                }
                runs.append({
                    "artifacts": artifacts,
                    "reference_git_head": self.reference_head,
                    "session_nonce": nonce,
                    "identity_sha256": identity_sha256,
                    "sweep": sweep,
                })
                relative_success = success_path.relative_to(
                    self.approval_root).as_posix()
                collection_rows[sweep].append({
                    "index": target_index + 1, "name": target["name"],
                    "state": "complete", "attempt_count": 1,
                    "success": {
                        "attempt": "attempt-0001",
                        "receipt_path": relative_success,
                        "receipt": {"path": relative_success,
                                    **record(success_path)},
                        "session_nonce": nonce,
                        "artifacts": collected_artifacts,
                    },
                    "attempts": [{"attempt": "attempt-0001",
                                  "state": "complete"}],
                })
            targets.append({
                "name": semantic["name"],
                "reference_runs": runs,
                "expected_identity": expected_identity,
            })
        collection_contract = {
            "schema": 4,
            "kind": "candle-great100-two-sweep-reference-collection",
            "approval_status": "candidate_collection_only_unapproved",
            "promotion_allowed": False,
            "sweep_count": 2, "target_count": 65,
            "total_target_runs": 130, "source_mode": "manifest-exact",
            "project": {
                "root": str(self.collection_project_root),
                "git_head": self.collection_project_head,
                "controller": {
                    "path": "scripts/run-top100-reference-sweeps.py",
                    **record(self.collection_project_root /
                              "scripts/run-top100-reference-sweeps.py"),
                },
            },
            "candle": {
                "root": str(self.candle_root),
                "git_head": self.collection_candle_head,
                "collector": {"path": "candle/reference_fingerprints.py",
                              **record(collector)},
                "protocol": {"path": "candle/reference_protocol.py",
                             **record(protocol)},
                "manifest": {"path": "candle/top100_manifest.json",
                             **record(manifest_pin)},
                "serializer": {"path": "candle/fingerprint.ml",
                               **record(self.serializer_path)},
                "source_contract": {
                    "path": "candle/reference_source_contracts.json",
                    **record(self.candle /
                              "reference_source_contracts.json")},
            },
            "reference": {"root": str(reference_root),
                          "git_head": self.reference_head,
                          "source_policy": reference_policy},
            "runtime": {
                "runtime": MODULE.runtime_file_record(
                    runtime, "fixture collection runtime"),
                "runtime_stublib": MODULE.runtime_file_record(
                    runtime_stublib, "fixture collection runtime stublib"),
                "ocamlc": MODULE.runtime_file_record(
                    ocamlc_path, "fixture collection ocamlc"),
                "ocamlfind": MODULE.runtime_file_record(
                    ocamlfind_path, "fixture collection ocamlfind"),
            },
            "external_runtime": {
                "policy": external_runtime["policy"],
                "command_shell": MODULE.runtime_file_record(
                    shell, "fixture contract shell"),
                "pari_gp": MODULE.runtime_file_record(
                    gp_bin / "gp", "fixture contract PARI/GP"),
                "csdp": MODULE.runtime_file_record(
                    csdp_executable, "fixture contract CSDP"),
                "package_archive": MODULE.runtime_file_record(
                    package_archive, "fixture contract package archive"),
                "package_tree": external_runtime["package_tree"],
                "configuration": MODULE.runtime_file_record(
                    gprc, "fixture contract configuration"),
                "data_tree": external_runtime["data_tree"],
                "csdp_source_archive": MODULE.runtime_file_record(
                    csdp_source, "fixture contract CSDP source"),
                "csdp_build": {
                    "receipt": MODULE.runtime_file_record(
                        csdp_build_receipt,
                        "fixture contract CSDP build receipt",
                    ),
                    "statement": deepcopy(csdp_build_statement),
                },
                "csdp_probe_input": MODULE.runtime_file_record(
                    csdp_probe_input, "fixture contract CSDP probe input"),
                "thread_policy": deepcopy(external_runtime["thread_policy"]),
                "csdp_probe": deepcopy(external_runtime["csdp_probe"]),
                "runtime_environment": {
                    key: external_environment[key]
                    for key in (
                        "PATH", "GPRC", "GP_DATA_DIR",
                        *MODULE.THREAD_CAP_ENVIRONMENT,
                    )},
            },
            "elf_oracle": MODULE.elf_oracle_projection(
                external_elf_runtime,
            ),
            "deadlines": collection_deadlines,
            "inventory": {
                "target_count": 65, "source_count": 66, "request_count": 97,
                "targets": [{
                    "index": index,
                    "name": target["name"],
                    "load_files": target["load_files"],
                    "load_file_sha256": {
                        relative: target["load_file_sha256"][relative]
                        for relative in target["load_files"]
                    },
                    "theorem_names": [
                        theorem["name"] for theorem in
                        target["fingerprint_request"]["theorems"]
                    ],
                } for index, target in enumerate(
                    self.manifest["targets"], 1,
                )],
            },
            "controller": {
                "path": str(self.collection_project_root /
                            "scripts/run-top100-reference-sweeps.py"),
                **record(self.collection_project_root /
                          "scripts/run-top100-reference-sweeps.py"),
                "python": MODULE.runtime_file_record(
                    Path("/usr/bin/python3"), "fixture collection Python"),
                "git": {
                    "path": "/usr/bin/git", **record(Path("/usr/bin/git")),
                },
            },
        }
        contract_path = self.approval_root / "collection-contract.json"
        contract_path.write_bytes(MODULE.canonical_json_bytes(collection_contract))
        collection_receipt = {
            "schema": 1,
            "kind": "candle-great100-two-sweep-reference-receipt",
            "contract_sha256": MODULE.compact_json_sha256(collection_contract),
            "contract": {"path": "collection-contract.json",
                         **record(contract_path)},
            "sweep_count": 2, "target_count": 65,
            "total_target_runs": 130, "completed_target_runs": 130,
            "pending_target_runs": 0, "failure_attempt_count": 0,
            "failures": [], "publication_interruptions": [],
            "outcome": "complete", "closed": True,
            "approval_status": "candidates_unapproved",
            "promotion_allowed": False,
            "sweeps": [{
                "sweep": sweep, "target_count": 65,
                "completed_count": 65, "pending_count": 0,
                "targets": collection_rows[sweep],
            } for sweep in (1, 2)],
        }
        receipt_path = self.approval_root / "receipt.json"
        receipt_path.write_bytes(MODULE.canonical_json_bytes(collection_receipt))
        self.approval = {
            "schema": "candle-s1-identity-approval-v2",
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
            "collection_evidence": {
                "contract": {
                    "path": contract_path.relative_to(
                        self.candle_root).as_posix(), **record(contract_path)},
                "receipt": {
                    "path": receipt_path.relative_to(
                        self.candle_root).as_posix(), **record(receipt_path)},
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

    def rewrite_all_reference_plans(self, mutate) -> None:
        """Rebind every causal layer after the same adversarial plan rewrite."""
        receipt_artifact = self.approval["collection_evidence"]["receipt"]
        receipt_path = self.candle_root / receipt_artifact["path"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        for target_index, approved in enumerate(self.approval["targets"]):
            for run_index, run in enumerate(approved["reference_runs"]):
                artifacts = run["artifacts"]
                plan_path = self.candle_root / artifacts["plan"]["path"]
                candidate_path = self.candle_root / artifacts["candidate"]["path"]
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                mutate(plan)
                plan_bytes = (json.dumps(plan, indent=2) + "\n").encode()
                plan_path.write_bytes(plan_bytes)
                artifacts["plan"].update(record(plan_path))

                candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
                candidate["plan_pins"] = {
                    "reference": deepcopy(plan["reference"]),
                    "input": deepcopy(plan["input"]),
                    "request_sha256": plan["request"]["sha256"],
                    "fresh_process_contract": deepcopy(
                        plan["fresh_process_contract"]),
                }
                candidate["artifact_hashes"]["plan_sha256"] = digest(plan_bytes)
                candidate_bytes = (json.dumps(candidate, indent=2) + "\n").encode()
                candidate_path.write_bytes(candidate_bytes)
                artifacts["candidate"].update(record(candidate_path))

                success_path = self.candle_root / artifacts[
                    "controller_success"]["path"]
                success = json.loads(success_path.read_text(encoding="utf-8"))
                for name, path in (("plan", plan_path),
                                   ("candidate", candidate_path)):
                    success["artifacts"][name] = {
                        "path": path.relative_to(self.approval_root).as_posix(),
                        **record(path),
                    }
                success_path.write_bytes(MODULE.canonical_json_bytes(success))
                artifacts["controller_success"].update(record(success_path))

                aggregate = receipt["sweeps"][run_index]["targets"][target_index][
                    "success"]
                aggregate["receipt"] = {
                    "path": success_path.relative_to(
                        self.approval_root).as_posix(),
                    **record(success_path),
                }
                for name in ("plan", "candidate"):
                    aggregate["artifacts"][name] = deepcopy(
                        success["artifacts"][name])
        receipt_path.write_bytes(MODULE.canonical_json_bytes(receipt))
        receipt_artifact.update(record(receipt_path))
        self._refresh_approval_bindings("adversarial all-plan rewrite fixture")

    def rewrite_all_reference_candidates(self, mutate) -> None:
        """Rebind collection receipts after an adversarial candidate rewrite."""
        receipt_artifact = self.approval["collection_evidence"]["receipt"]
        receipt_path = self.candle_root / receipt_artifact["path"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        for target_index, approved in enumerate(self.approval["targets"]):
            for run_index, run in enumerate(approved["reference_runs"]):
                artifacts = run["artifacts"]
                candidate_path = self.candle_root / artifacts["candidate"]["path"]
                candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
                mutate(candidate)
                candidate_bytes = (json.dumps(candidate, indent=2) + "\n").encode()
                candidate_path.write_bytes(candidate_bytes)
                artifacts["candidate"].update(record(candidate_path))

                success_path = self.candle_root / artifacts[
                    "controller_success"]["path"]
                success = json.loads(success_path.read_text(encoding="utf-8"))
                success["artifacts"]["candidate"] = {
                    "path": candidate_path.relative_to(
                        self.approval_root).as_posix(),
                    **record(candidate_path),
                }
                success_path.write_bytes(MODULE.canonical_json_bytes(success))
                artifacts["controller_success"].update(record(success_path))

                aggregate = receipt["sweeps"][run_index]["targets"][
                    target_index]["success"]
                aggregate["receipt"] = {
                    "path": success_path.relative_to(
                        self.approval_root).as_posix(),
                    **record(success_path),
                }
                aggregate["artifacts"]["candidate"] = deepcopy(
                    success["artifacts"]["candidate"],
                )
        receipt_path.write_bytes(MODULE.canonical_json_bytes(receipt))
        receipt_artifact.update(record(receipt_path))
        self._refresh_approval_bindings(
            "adversarial all-candidate rewrite fixture",
        )

    def replace_collection_artifact(self, name: str, value: bytes) -> None:
        artifact = self.approval["collection_evidence"][name]
        path = self.candle_root / artifact["path"]
        path.write_bytes(value)
        artifact.update(record(path))
        self._refresh_approval_bindings("mutated collection fixture")

    def replace_collection_documents(
        self, contract: dict, receipt: dict,
    ) -> None:
        contract_artifact = self.approval["collection_evidence"]["contract"]
        receipt_artifact = self.approval["collection_evidence"]["receipt"]
        contract_path = self.candle_root / contract_artifact["path"]
        receipt_path = self.candle_root / receipt_artifact["path"]
        contract_path.write_bytes(MODULE.canonical_json_bytes(contract))
        contract_artifact.update(record(contract_path))
        receipt["contract_sha256"] = MODULE.compact_json_sha256(contract)
        receipt["contract"] = {
            "path": "collection-contract.json", **record(contract_path),
        }
        receipt_path.write_bytes(MODULE.canonical_json_bytes(receipt))
        receipt_artifact.update(record(receipt_path))
        self._refresh_approval_bindings("mutated collection documents fixture")

    def collection_documents(self) -> tuple[dict, dict]:
        evidence = self.approval["collection_evidence"]
        return tuple(
            json.loads((self.candle_root / evidence[name]["path"]).read_text(
                encoding="utf-8",
            ))
            for name in ("contract", "receipt")
        )

    def _refresh_approval_bindings(self, commit_message: str) -> None:
        self.write_approval(update_reports=False)
        for target in self.manifest["targets"]:
            target["fingerprint_request"]["expected_identities"][
                "approval_sha256"] = self.approval_identity["sha256"]
        self.manifest["identity_approval"].update({
            "sha256": self.approval_identity["sha256"],
            "approval_status": "approved", "promotion_allowed": True,
        })
        manifest_path = self.candle / "top100_manifest.json"
        manifest_path.write_bytes(MODULE.canonical_json_bytes(self.manifest))
        git(self.candle_root, "add", "-A")
        git(self.candle_root, "commit", "-qm", commit_message)
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
        self.original_collection_project_head = MODULE.COLLECTION_PROJECT_HEAD
        self.original_collection_controller_bytes = \
            MODULE.COLLECTION_CONTROLLER_BYTES
        self.original_collection_controller_sha256 = \
            MODULE.COLLECTION_CONTROLLER_SHA256
        self.fixture = Fixture(Path(self.temporary.name))
        MODULE.PROGRAM_PATH = self.fixture.program_path
        MODULE._TEST_AFTER_CONTRACT_CAPTURE = None

    def tearDown(self) -> None:
        MODULE.PROGRAM_PATH = self.original_program
        MODULE._TEST_AFTER_CONTRACT_CAPTURE = self.original_hook
        MODULE.COLLECTION_PROJECT_HEAD = self.original_collection_project_head
        MODULE.COLLECTION_CONTROLLER_BYTES = \
            self.original_collection_controller_bytes
        MODULE.COLLECTION_CONTROLLER_SHA256 = \
            self.original_collection_controller_sha256
        self.temporary.cleanup()

    def assert_rejected(self, pattern: str | None = None) -> None:
        context = (self.assertRaisesRegex(MODULE.ValidationError, pattern)
                   if pattern else self.assertRaises(MODULE.ValidationError))
        with context:
            self.fixture.finalize()

    def test_git_checkout_accepts_clean_linked_worktree(self) -> None:
        linked = self.fixture.root / "linked-finalizer-project"
        git(
            self.fixture.project_root, "worktree", "add", "--detach",
            str(linked), self.fixture.project_head,
        )
        self.assertTrue((linked / ".git").is_file())
        MODULE.validate_git_checkout(
            linked, self.fixture.project_head, "linked finalizer fixture",
        )

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
        self.assertNotEqual(
            self.fixture.collection_project_head, self.fixture.project_head,
        )
        self.assertNotEqual(
            self.fixture.collection_project_root, self.fixture.project_root,
        )
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
        for component in ("validator", "protocol", "regression"):
            replay = bundle["approval_replay"][component]
            self.assertEqual(
                (self.fixture.destination /
                 replay["committed_archive_path"]).read_bytes(),
                (self.fixture.destination /
                 replay["executed_archive_path"]).read_bytes(),
            )
        external = bundle["approval_replay"]["external_runtime"]
        self.assertEqual(external["policy"],
                         MODULE.EXTERNAL_RUNTIME_POLICY)
        self.assertEqual(
            (self.fixture.destination /
             external["package_archive"]["archive_path"]).read_bytes(),
            (self.fixture.root / "reference-tools/pari.deb").read_bytes(),
        )
        self.assertTrue(external["package_tree"]["pin"]["entry_count"] > 0)
        self.assertEqual(external["data_tree"]["entry_count"], 0)
        for key in ("csdp", "csdp_source_archive", "csdp_build_receipt",
                    "csdp_probe_input"):
            self.assertTrue(
                (self.fixture.destination /
                 external[key]["archive_path"]).is_file(),
            )
        for artifact in external["csdp_probe_artifacts"].values():
            retained = self.fixture.destination / artifact["archive_path"]
            self.assertTrue(retained.is_file())
            self.assertEqual(digest(retained.read_bytes()), artifact["sha256"])
        self.assertEqual(
            external["thread_policy"]["environment"],
            MODULE.THREAD_CAP_ENVIRONMENT,
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

    def test_linked_pass_witness_order_is_closed(self) -> None:
        target = self.fixture.manifest["targets"][0]
        result = self.fixture.reports[0]["results"][0]
        process = result["process_evidence"]
        witness = (MODULE.LINKED_PASS_WITNESS + "\n").encode()
        transcript = Path(result["log_path"]).read_bytes()
        self.assertEqual(transcript.count(witness), 1)
        transcript = transcript.replace(
            witness, b"ordinary non-protocol output\n",
        ) + witness
        with self.assertRaisesRegex(MODULE.ValidationError, "marker order"):
            MODULE.validate_transcript(
                transcript, result["name"], process["suite_nonce"],
                process["process_nonce"], self.fixture.linked_sha256,
                target["fingerprint_request"]["expected_identities"][
                    "theorems"],
                target["fingerprint_request"]["expected_identities"][
                    "post_state"],
                process["markers"],
            )

    def test_source_closure_is_live_hashed_and_committed(self) -> None:
        relative = self.fixture.manifest["targets"][0]["load_files"][0]
        source = self.fixture.candle_root / relative
        source.write_bytes(source.read_bytes() + b"tamper\n")
        git(self.fixture.candle_root, "add", relative)
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
        self.assert_rejected("controller receipt does not bind")

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
        self.assert_rejected("controller receipt does not bind")

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
        self.assert_rejected("controller receipt does not bind")

    def test_reference_plan_target_is_bound(self) -> None:
        artifact = self.fixture.approval["targets"][0]["reference_runs"][0][
            "artifacts"]["plan"]
        plan_path = self.fixture.candle_root / artifact["path"]
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["input"]["target"] = "100/test-01"
        self.fixture.replace_reference_artifact(
            0, 0, "plan", MODULE.canonical_json_bytes(plan),
        )
        self.assert_rejected("controller receipt does not bind")

    def test_reference_plan_head_is_bound(self) -> None:
        artifact = self.fixture.approval["targets"][0]["reference_runs"][0][
            "artifacts"]["plan"]
        plan_path = self.fixture.candle_root / artifact["path"]
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["reference"]["git_head"] = "a" * 40
        self.fixture.replace_reference_artifact(
            0, 0, "plan", MODULE.canonical_json_bytes(plan),
        )
        self.assert_rejected("controller receipt does not bind")

    def test_reference_plan_protocol_support_is_bound(self) -> None:
        artifact = self.fixture.approval["targets"][0]["reference_runs"][0][
            "artifacts"]["plan"]
        plan_path = self.fixture.candle_root / artifact["path"]
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["input"]["collector_repository"][
            "support_at_head_sha256"] = "a" * 64
        self.fixture.replace_reference_artifact(
            0, 0, "plan", MODULE.canonical_json_bytes(plan),
        )
        self.assert_rejected("controller receipt does not bind")

    def test_reference_external_runtime_must_be_identical_across_runs(self) -> None:
        artifact = self.fixture.approval["targets"][0]["reference_runs"][0][
            "artifacts"]["plan"]
        plan_path = self.fixture.candle_root / artifact["path"]
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        version = "2.15.5\n"
        plan["reference"]["external_runtime"]["pari_gp_version"] = {
            "stdout": version, "sha256": digest(version.encode()),
        }
        self.fixture.replace_reference_artifact(
            0, 0, "plan", MODULE.canonical_json_bytes(plan),
        )
        self.assert_rejected("controller receipt does not bind")

    def test_schema_v8_reference_plans_are_nonpromotable(self) -> None:
        def downgrade(plan: dict) -> None:
            plan["schema"] = "candle-s1-reference-plan-v8"

        self.fixture.rewrite_all_reference_plans(downgrade)
        self.assert_rejected("malformed v9 reference plan")

    def test_forged_csdp_build_statement_rejects_after_full_rehash(self) -> None:
        def forge_recipe(plan: dict) -> None:
            plan["reference"]["external_runtime"]["csdp_build"]["statement"][
                "recipe"]["openmp_enabled"] = True

        self.fixture.rewrite_all_reference_plans(forge_recipe)
        self.assert_rejected("CSDP build statement")

    def test_csdp_build_boolean_type_confusion_rejects(self) -> None:
        def confuse_boolean(plan: dict) -> None:
            plan["reference"]["external_runtime"]["csdp_build"]["statement"][
                "recipe"]["openmp_enabled"] = 0

        self.fixture.rewrite_all_reference_plans(confuse_boolean)
        self.assert_rejected("CSDP build statement")

    def test_reference_probe_return_code_type_confusion_rejects(self) -> None:
        def confuse_return_codes(plan: dict) -> None:
            external = plan["reference"]["external_runtime"]
            external["probe"]["return_code"] = False
            external["csdp_probe"]["return_code"] = 0.0

        self.fixture.rewrite_all_reference_plans(confuse_return_codes)
        self.assert_rejected("PARI/GP probe|CSDP probe")

    def test_reference_thread_policy_type_confusion_rejects(self) -> None:
        def confuse_thread_policy(plan: dict) -> None:
            policy = plan["reference"]["external_runtime"]["thread_policy"]
            policy["single_process_solver"] = 1
            policy["openmp_enabled"] = 0

        self.fixture.rewrite_all_reference_plans(confuse_thread_policy)
        self.assert_rejected("CSDP thread policy")

    def test_candidate_exit_code_type_confusion_rejects(self) -> None:
        self.fixture.rewrite_all_reference_candidates(
            lambda candidate: candidate.update(process_exit_code=False),
        )
        self.assert_rejected("malformed candidate process exit code")

    def test_omitted_elf_dependency_is_rejected_after_complete_rehash(self) -> None:
        def omit_dependency(plan: dict) -> None:
            closure = plan["reference"]["external_runtime"]["elf_runtime"][
                "closure"]
            self.assertGreater(len(closure), 1)
            closure.pop(0)

        self.fixture.rewrite_all_reference_plans(omit_dependency)
        self.assert_rejected("captured v9 reference candidate replay failed")

    def test_omitted_runtime_stub_is_rejected_after_complete_rehash(self) -> None:
        def omit_stub_and_rebuild_elf(plan: dict) -> None:
            reference = plan["reference"]
            stubs = reference["runtime_stub_files"]
            self.assertGreater(len(stubs), 1)
            stubs.pop(0)
            reference["elf_runtime"] = elf_evidence([
                Path(reference["runtime_interpreter"]["path"]),
                *(Path(item["path"]) for item in stubs),
            ])

        self.fixture.rewrite_all_reference_plans(omit_stub_and_rebuild_elf)
        self.assert_rejected("captured v9 reference candidate replay failed")

    def test_rebound_runtime_interpreter_is_rejected_after_rehash(self) -> None:
        def rebind_interpreter(plan: dict) -> None:
            reference = plan["reference"]
            interpreter = Path("/bin/bash").resolve()
            reference["runtime_interpreter"] = {
                "path": str(interpreter),
                "sha256": digest(interpreter.read_bytes()),
            }
            reference["elf_runtime"] = elf_evidence([
                interpreter,
                *(Path(item["path"])
                  for item in reference["runtime_stub_files"]),
            ])

        self.fixture.rewrite_all_reference_plans(rebind_interpreter)
        self.assert_rejected("captured v9 reference candidate replay failed")

    def test_rebound_hol_init_script_is_rejected_after_rehash(self) -> None:
        alternate = self.fixture.root / "alternate-hol.ml"
        alternate.write_bytes(b"(* forged HOL initialization *)\n")

        def rebind_hol_ml(plan: dict) -> None:
            reference = plan["reference"]
            reference["hol_ml"] = {
                "path": str(alternate), "sha256": digest(alternate.read_bytes()),
            }
            plan["fresh_process_contract"]["runtime_argv"][2] = str(alternate)

        self.fixture.rewrite_all_reference_plans(rebind_hol_ml)
        self.assert_rejected("captured v9 reference candidate replay failed")

    def test_reference_external_package_is_live_rechecked(self) -> None:
        package = self.fixture.root / "reference-tools/pari.deb"
        package.chmod(0o644)
        package.write_bytes(b"mutated package archive\n")
        package.chmod(0o444)
        self.assert_rejected("package_archive changed|package archive differs")

    def test_reference_collection_receipt_must_be_closed(self) -> None:
        artifact = self.fixture.approval["collection_evidence"]["receipt"]
        path = self.fixture.candle_root / artifact["path"]
        receipt = json.loads(path.read_text())
        receipt["closed"] = False
        self.fixture.replace_collection_artifact(
            "receipt", MODULE.canonical_json_bytes(receipt))
        self.assert_rejected("not closed and exact")

    def test_collection_contract_integer_type_confusion_rejects(self) -> None:
        contract, receipt = self.fixture.collection_documents()
        for field in (
                "schema", "sweep_count", "target_count",
                "total_target_runs"):
            contract[field] = float(contract[field])
        self.fixture.replace_collection_documents(contract, receipt)
        self.assert_rejected("malformed reference collection contract")

    def test_collection_inventory_integer_type_confusion_rejects(self) -> None:
        contract, receipt = self.fixture.collection_documents()
        inventory = contract["inventory"]
        for field in ("target_count", "source_count", "request_count"):
            inventory[field] = float(inventory[field])
        inventory["targets"][0]["index"] = \
            float(inventory["targets"][0]["index"])
        self.fixture.replace_collection_documents(contract, receipt)
        self.assert_rejected("inventory differs from manifest")

    def test_collection_receipt_integer_type_confusion_rejects(self) -> None:
        contract, receipt = self.fixture.collection_documents()
        for field in (
                "schema", "sweep_count", "target_count", "total_target_runs",
                "completed_target_runs", "pending_target_runs",
                "failure_attempt_count"):
            receipt[field] = float(receipt[field])
        self.fixture.replace_collection_documents(contract, receipt)
        self.assert_rejected("not closed and exact")

    def test_collection_sweep_integer_type_confusion_rejects(self) -> None:
        contract, receipt = self.fixture.collection_documents()
        sweep = receipt["sweeps"][0]
        for field in (
                "sweep", "target_count", "completed_count", "pending_count"):
            sweep[field] = float(sweep[field])
        self.fixture.replace_collection_documents(contract, receipt)
        self.assert_rejected("malformed closed reference sweep")

    def test_collection_target_integer_type_confusion_rejects(self) -> None:
        contract, receipt = self.fixture.collection_documents()
        row = receipt["sweeps"][0]["targets"][0]
        row["index"] = float(row["index"])
        row["attempt_count"] = float(row["attempt_count"])
        self.fixture.replace_collection_documents(contract, receipt)
        self.assert_rejected("malformed reference collection target success")

    def test_collection_runtime_type_confusion_rejects(self) -> None:
        contract, receipt = self.fixture.collection_documents()
        external = contract["external_runtime"]
        external["csdp_probe"]["return_code"] = False
        external["thread_policy"]["single_process_solver"] = 1
        external["thread_policy"]["openmp_enabled"] = 0
        self.fixture.replace_collection_documents(contract, receipt)
        self.assert_rejected("external-runtime environment|CSDP probe")

    def test_fabricated_collection_contract_is_rejected_after_rehash(self) -> None:
        contract_path = self.fixture.candle_root / self.fixture.approval[
            "collection_evidence"]["contract"]["path"]
        receipt_path = self.fixture.candle_root / self.fixture.approval[
            "collection_evidence"]["receipt"]["path"]
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        contract["project"] = {
            "root": str(self.fixture.project_root),
            "git_head": self.fixture.project_head,
            "controller": {"fixture": True},
        }
        contract["runtime"] = {"fabricated": True}
        contract["controller"] = {"fabricated": True}
        self.fixture.replace_collection_documents(contract, receipt)
        self.assert_rejected("authorized launch commit")

    def test_alternate_committed_controller_is_rejected_after_rehash(self) -> None:
        alternate = self.fixture.root / "alternate-controller-project"
        controller_path = alternate / "scripts/run-top100-reference-sweeps.py"
        controller_path.parent.mkdir(parents=True)
        controller_path.write_bytes(
            (self.fixture.project_root /
             "scripts/run-top100-reference-sweeps.py").read_bytes(),
        )
        controller_path.chmod(0o755)
        git(alternate, "init", "-q")
        git(alternate, "config", "user.email", "fixture@example.invalid")
        git(alternate, "config", "user.name", "fixture")
        git(alternate, "add", ".")
        git(alternate, "commit", "-qm", "alternate controller authority")
        alternate_head = git(alternate, "rev-parse", "HEAD")

        contract_path = self.fixture.candle_root / self.fixture.approval[
            "collection_evidence"]["contract"]["path"]
        receipt_path = self.fixture.candle_root / self.fixture.approval[
            "collection_evidence"]["receipt"]["path"]
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        controller_record = {
            "path": "scripts/run-top100-reference-sweeps.py",
            **record(controller_path),
        }
        contract["project"] = {
            "root": str(alternate), "git_head": alternate_head,
            "controller": controller_record,
        }
        contract["controller"].update({
            "path": str(controller_path), **record(controller_path),
        })
        self.fixture.replace_collection_documents(contract, receipt)
        self.assert_rejected("authorized launch commit")

    def test_reference_checkout_and_sources_are_live_authenticated(self) -> None:
        source = self.fixture.reference_root / self.fixture.manifest[
            "targets"][0]["load_files"][0]
        source.write_bytes(b"forged selected reference source\n")
        self.assert_rejected("reference checkout.*not clean|source differs")

    def test_fabricated_aggregate_attempt_is_rejected_after_rehash(self) -> None:
        contract_path = self.fixture.candle_root / self.fixture.approval[
            "collection_evidence"]["contract"]["path"]
        receipt_path = self.fixture.candle_root / self.fixture.approval[
            "collection_evidence"]["receipt"]["path"]
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["sweeps"][0]["targets"][0]["attempts"] = [
            {"fabricated": True},
        ]
        self.fixture.replace_collection_documents(contract, receipt)
        self.assert_rejected("target success")

    def test_rebound_collection_core_runtime_is_rejected(self) -> None:
        contract_path = self.fixture.candle_root / self.fixture.approval[
            "collection_evidence"]["contract"]["path"]
        receipt_path = self.fixture.candle_root / self.fixture.approval[
            "collection_evidence"]["receipt"]["path"]
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        alternate = self.fixture.root / "reference-tools/alternate-runtime"
        original = Path(contract["runtime"]["runtime"]["path"])
        alternate.write_bytes(original.read_bytes())
        alternate.chmod(0o755)
        contract["runtime"]["runtime"] = MODULE.runtime_file_record(
            alternate, "rebound fixture runtime",
        )
        self.fixture.replace_collection_documents(contract, receipt)
        self.assert_rejected("core runtime")

    def test_fabricated_controller_output_is_rejected_after_rehash(self) -> None:
        run = self.fixture.approval["targets"][0]["reference_runs"][0]
        output_artifact = run["artifacts"]["collector_stdout"]
        output_path = self.fixture.candle_root / output_artifact["path"]
        output_path.write_bytes(b"fabricated collector output\n")
        output_artifact.update(record(output_path))

        success_artifact = run["artifacts"]["controller_success"]
        success_path = self.fixture.candle_root / success_artifact["path"]
        success = json.loads(success_path.read_text(encoding="utf-8"))
        success["collector_stdout"] = {
            "path": output_path.relative_to(
                self.fixture.approval_root,
            ).as_posix(),
            **record(output_path),
        }
        success_path.write_bytes(MODULE.canonical_json_bytes(success))
        success_artifact.update(record(success_path))

        receipt_artifact = self.fixture.approval[
            "collection_evidence"]["receipt"]
        receipt_path = self.fixture.candle_root / receipt_artifact["path"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["sweeps"][0]["targets"][0]["success"]["receipt"] = {
            "path": success_path.relative_to(
                self.fixture.approval_root,
            ).as_posix(),
            **record(success_path),
        }
        receipt_path.write_bytes(MODULE.canonical_json_bytes(receipt))
        receipt_artifact.update(record(receipt_path))
        self.fixture._refresh_approval_bindings(
            "fabricated controller output fixture",
        )
        self.assert_rejected("unexpected controller output")

    def test_reference_plan_nonce_is_bound(self) -> None:
        artifact = self.fixture.approval["targets"][0]["reference_runs"][0][
            "artifacts"]["plan"]
        plan_path = self.fixture.candle_root / artifact["path"]
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["session_nonce"] = "b" * 64
        self.fixture.replace_reference_artifact(
            0, 0, "plan", MODULE.canonical_json_bytes(plan),
        )
        self.assert_rejected("controller receipt does not bind")

    def test_reference_plan_source_contract_is_bound(self) -> None:
        artifact = self.fixture.approval["targets"][0]["reference_runs"][0][
            "artifacts"]["plan"]
        plan_path = self.fixture.candle_root / artifact["path"]
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["input"]["source_contract"]["sha256"] = "c" * 64
        self.fixture.replace_reference_artifact(
            0, 0, "plan", MODULE.canonical_json_bytes(plan),
        )
        self.assert_rejected("controller receipt does not bind")

    def test_reference_plan_selected_sources_are_bound(self) -> None:
        artifact = self.fixture.approval["targets"][0]["reference_runs"][0][
            "artifacts"]["plan"]
        plan_path = self.fixture.candle_root / artifact["path"]
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        plan["input"]["load_files"][0]["sha256"] = "d" * 64
        self.fixture.replace_reference_artifact(
            0, 0, "plan", MODULE.canonical_json_bytes(plan),
        )
        self.assert_rejected("controller receipt does not bind")

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
        self.assert_rejected("controller receipt does not bind")

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
