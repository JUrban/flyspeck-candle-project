#!/usr/bin/env python3
"""Static/adversarial tests for the resumable reference-sweep controller."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("run-top100-reference-sweeps.py")
SYSTEM_PYTHON = Path("/usr/bin/python3")
SYSTEM_GIT = Path("/usr/bin/git")
SPEC = importlib.util.spec_from_file_location("top100_reference_sweeps", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["/usr/bin/git", "-C", str(root), *arguments], check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    return completed.stdout.strip()


def wait_for(path: Path, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            return
        time.sleep(0.02)
    raise AssertionError(f"timed out waiting for {path}")


def process_is_live(pid: int) -> bool:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().split()
    except FileNotFoundError:
        return False
    return len(fields) > 2 and fields[2] != "Z"


def wait_not_live(pid: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not process_is_live(pid):
            return
        time.sleep(0.02)
    raise AssertionError(f"process {pid} remained live")


def lock_is_available(path: Path) -> bool:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        return True
    finally:
        os.close(descriptor)


FAKE_COLLECTOR = r'''#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "candle/top100_manifest.json"
FAIL_FIRST_TARGET = __FAIL_TARGET__
HANG_FIRST_SECONDS = __HANG_SECONDS__


def digest(value):
    return hashlib.sha256(value).hexdigest()


def file_sha(path):
    return digest(Path(path).read_bytes())


def git(*args):
    return subprocess.check_output(
        ["/usr/bin/git", "-C", str(ROOT), *args], text=True).strip()


def json_sha(value):
    return digest((json.dumps(value, indent=2) + "\n").encode())


def main():
    lock_value = os.environ.get("CANDLE_REFERENCE_CONTROLLER_LOCK_FD", "")
    if not re.fullmatch(r"[1-9][0-9]*", lock_value):
        raise SystemExit(12)
    try:
        lock_metadata = os.fstat(int(lock_value))
    except OSError:
        raise SystemExit(13)
    if not stat.S_ISREG(lock_metadata.st_mode):
        raise SystemExit(14)
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    collect = sub.add_parser("collect")
    for name in ("target", "reference-root", "runtime", "runtime-stublib",
                 "ocamlc", "ocamlfind", "pari-gp-root", "pari-gp-package",
                 "command-shell", "csdp-source", "csdp-build-receipt",
                 "csdp-probe-input", "plan", "request", "source-mode",
                 "transcript", "candidate", "wall-timeout"):
        collect.add_argument("--" + name, required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("candidate")
    for name in ("plan", "request", "transcript"):
        validate.add_argument("--" + name, required=True)
    args = parser.parse_args()
    if args.command == "validate":
        candidate = json.loads(Path(args.candidate).read_text())
        plan = json.loads(Path(args.plan).read_text())
        request = Path(args.request).read_bytes()
        transcript = Path(args.transcript).read_bytes()
        hashes = candidate["artifact_hashes"]
        if (candidate["schema"] != "candle-s1-reference-candidate-v9" or
                hashes != {
                    "plan_sha256": json_sha(plan),
                    "request_sha256": digest(request),
                    "transcript_sha256": digest(transcript),
                } or candidate["session_nonce"] != plan["session_nonce"]):
            raise SystemExit(9)
        print(f"candidate and linked artifacts valid but unapproved: {args.candidate}")
        return 0

    manifest = json.loads(MANIFEST.read_text())
    target = next(item for item in manifest["targets"] if item["name"] == args.target)
    plan_path = Path(args.plan)
    nonce = digest(str(plan_path).encode())
    collector_sha = file_sha(__file__)
    request = f"REQUEST {args.target} {nonce}\n".encode()
    reference_root = Path(args.reference_root).resolve()
    contract = json.loads(
        (plan_path.parents[3] / "collection-contract.json").read_text())
    external_contract = contract["external_runtime"]
    elf_oracle = contract["elf_oracle"]
    def elf_runtime(roots):
        return {
            **elf_oracle,
            "requested_roots": [
                {"path": str(Path(path).resolve()), "sha256": file_sha(path)}
                for path in sorted(roots, key=lambda item: str(Path(item).resolve()))
            ],
            "observations": [],
            "closure": [],
        }
    def route(value):
        return {
            "argument_path": value["argument_path"],
            "argument_parent": {}, "argument": {},
            "resolved_executable": {
                "path": value["path"], "sha256": value["sha256"],
                "mode": 0o755,
            },
        }
    external_runtime = {
        "policy": external_contract["policy"],
        "command_shell": route(external_contract["command_shell"]),
        "pari_gp": route(external_contract["pari_gp"]),
        "csdp": route(external_contract["csdp"]),
        "csdp_bytes": external_contract["csdp"]["bytes"],
        "pari_gp_version": {"stdout": "2.15.4\n", "sha256": "0" * 64},
        "package_archive": {
            "path": external_contract["package_archive"]["path"],
            "sha256": external_contract["package_archive"]["sha256"],
        },
        "package_tree": external_contract["package_tree"],
        "configuration": {
            "path": external_contract["configuration"]["path"],
            "sha256": external_contract["configuration"]["sha256"],
        },
        "data_tree": external_contract["data_tree"],
        "csdp_source_archive": {
            key: external_contract["csdp_source_archive"][key]
            for key in ("path", "sha256", "bytes")
        },
        "csdp_build": {
            "receipt": {
                key: external_contract["csdp_build"]["receipt"][key]
                for key in ("path", "sha256")
            },
            "statement": external_contract["csdp_build"]["statement"],
        },
        "csdp_probe_input": {
            key: external_contract["csdp_probe_input"][key]
            for key in ("path", "sha256", "bytes")
        },
        "thread_policy": external_contract["thread_policy"],
        "csdp_probe": external_contract["csdp_probe"],
        "elf_runtime": elf_runtime([
            external_contract["command_shell"]["path"],
            external_contract["pari_gp"]["path"],
            external_contract["csdp"]["path"],
        ]),
        "probe": {
            "shell_argv": [
                "/bin/sh", "-c",
                "echo 'print(default(nbthreads)); print(factorint(15))  \n quit' | gp",
            ],
            "environment": {
                "HOME": str(reference_root),
                "PATH": external_contract["runtime_environment"]["PATH"],
                "LC_ALL": "C",
                "GPRC": external_contract["runtime_environment"]["GPRC"],
                "GP_DATA_DIR":
                    external_contract["runtime_environment"]["GP_DATA_DIR"],
                **{
                    key: external_contract["runtime_environment"][key]
                    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                                "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
                                "NUMEXPR_NUM_THREADS")
                },
            },
            "return_code": 0,
            "stdout": "1\n[3, 1; 5, 1]\n",
            "stdout_sha256": digest(b"1\n[3, 1; 5, 1]\n"),
            "stderr": "", "stderr_sha256": digest(b""),
        },
    }
    plan = {
        "schema": "candle-s1-reference-plan-v9",
        "status": "planned_not_executed",
        "session_nonce": nonce,
        "reference": {
            "root": str(reference_root),
            "git_head": subprocess.check_output([
                "/usr/bin/git", "-C", str(reference_root), "rev-parse", "HEAD"
            ], text=True).strip(),
            "git_status": [],
            "elf_runtime": elf_runtime([Path(args.runtime).resolve()]),
            "external_runtime": external_runtime,
        },
        "input": {
            "target": args.target,
            "mapping_status": "audited",
            "source_mode": args.source_mode,
            "theorem_names": [
                item["name"] for item in target["fingerprint_request"]["theorems"]
            ],
            "load_files": [{
                "relative_path": relative,
                "path": str(reference_root / relative),
                "sha256": target["load_file_sha256"][relative],
                "source_role": "selected-manifest-source",
            } for relative in target["load_files"]],
            "collector": {"path": str(Path(__file__).resolve()),
                          "sha256": collector_sha},
            "collector_repository": {
                "root": str(ROOT), "git_head": git("rev-parse", "HEAD"),
                "git_status": [],
                "collector_relative_path": "candle/reference_fingerprints.py",
                "collector_at_head_sha256": collector_sha,
                "collector_matches_head": True,
                "support_relative_path": "candle/reference_protocol.py",
                "support_at_head_sha256": file_sha(
                    ROOT / "candle/reference_protocol.py"),
                "support_matches_head": True,
            },
        },
        "request": {"source": request.decode(), "sha256": digest(request)},
        "fresh_process_contract": {
            "required": True,
            "preloaded_checkpoint_allowed": False,
            "working_directory": str(reference_root),
            "environment_policy": "sanitized_allowlist_no_inherited_overrides",
            "runtime_argv": [str(Path(args.runtime).resolve()), "-noprompt"],
            "runtime_environment": {
                "HOME": str(reference_root),
                "PATH": external_contract["runtime_environment"]["PATH"],
                "LC_ALL": "C",
                "GPRC": external_contract["runtime_environment"]["GPRC"],
                "GP_DATA_DIR":
                    external_contract["runtime_environment"]["GP_DATA_DIR"],
                **{
                    key: external_contract["runtime_environment"][key]
                    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                                "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
                                "NUMEXPR_NUM_THREADS")
                },
                "HOLLIGHT_DIR": str(reference_root),
                "HOLLIGHT_USE_MODULE": "0",
                "OCAMLRUNPARAM": "l=2000000000",
                "CAML_LD_LIBRARY_PATH": str(Path(args.runtime_stublib).parent),
                "OCAML_TOPLEVEL_PATH": str(reference_root),
                "OCAMLFIND_CONF": str(reference_root / "ocamlfind.conf"),
            },
        },
    }
    plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    Path(args.request).write_bytes(request)
    if HANG_FIRST_SECONDS and args.target == "100/test-00" and \
            plan_path.parent.name == "attempt-0001" and \
            plan_path.parent.parent.parent.name == "sweep-1":
        runtime_process = subprocess.Popen(
            [sys.executable, "-I", "-S", "-c",
             f"import time; time.sleep({HANG_FIRST_SECONDS + 2})"],
            pass_fds=(int(lock_value),),
        )
        Path(args.transcript).write_text(
            f"HANGING {os.getpid()} {runtime_process.pid}\n")
        time.sleep(HANG_FIRST_SECONDS)
    if FAIL_FIRST_TARGET and args.target == FAIL_FIRST_TARGET and \
            plan_path.parent.name == "attempt-0001" and \
            plan_path.parent.parent.parent.name == "sweep-1":
        print("injected first-attempt failure", file=sys.stderr)
        return 7
    transcript = f"TRANSCRIPT {args.target} {nonce}\n".encode()
    Path(args.transcript).write_bytes(transcript)
    candidate = {
        "schema": "candle-s1-reference-candidate-v9",
        "artifact_kind": "reference_identity_candidate",
        "approval_status": "candidate_unapproved",
        "promotion_allowed": False,
        "warning": "fixture remains unapproved",
        "plan_pins": {"fixture": True},
        "session_nonce": nonce,
        "process_exit_code": 0,
        "artifact_hashes": {
            "plan_sha256": json_sha(plan),
            "request_sha256": digest(request),
            "transcript_sha256": digest(transcript),
        },
        "candidate_identities": {
            "status": "observed_uncompared",
            "expected_identities_present": False,
            "approval_sha256": None,
        },
    }
    Path(args.candidate).write_text(json.dumps(candidate, indent=2) + "\n")
    print(f"unapproved reference candidate: {args.candidate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


class Fixture:
    def __init__(
        self, root: Path, fail_target: str | None = None,
        hang_first_seconds: int = 0,
    ):
        self.root = root.resolve()
        self.candle = self.root / "candle-repo"
        self.reference = self.root / "reference-repo"
        self.project = self.root / "project-repo"
        self.artifacts = self.root / "artifacts"
        self.tools = self.root / "tools"
        for directory in (self.candle / "candle", self.reference,
                          self.project / "scripts",
                          self.artifacts, self.tools):
            directory.mkdir(parents=True, exist_ok=True)
        self.artifacts.chmod(0o700)
        self.controller = self.project / \
            "scripts/run-top100-reference-sweeps.py"
        self.controller.write_bytes(SCRIPT.read_bytes())
        self.controller.chmod(0o755)
        self.project_head = self._commit(self.project, "fixture project")
        self._create_sources()
        self.historical_head = self._commit(
            self.reference, "fixture historical reference",
        )
        delta_paths = (
            "100/e_is_transcendental.ml", "100/euler.ml", "100/lagrange.ml",
        )
        historical_hashes = {
            path: sha256((self.reference / path).read_bytes()) for path in delta_paths
        }
        for path in delta_paths:
            with (self.reference / path).open("a") as output:
                output.write("selected compatibility delta\n")
        selected_hashes = {
            path: sha256((self.reference / path).read_bytes()) for path in delta_paths
        }
        manifest = json.loads(self.manifest_path.read_text())
        for target in manifest["targets"]:
            for path in target["load_files"]:
                if path in selected_hashes:
                    target["load_file_sha256"][path] = selected_hashes[path]
        self.manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        self.reference_head = self._commit(
            self.reference, "fixture exact reference",
        )
        collector = FAKE_COLLECTOR.replace(
            "__FAIL_TARGET__", repr(fail_target),
        ).replace("__HANG_SECONDS__", str(hang_first_seconds)).encode()
        self.collector = self.candle / "candle/reference_fingerprints.py"
        self.collector.write_bytes(collector)
        self.collector.chmod(0o644)
        self.protocol = self.candle / "candle/reference_protocol.py"
        self.protocol.write_text("fixture protocol\n")
        (self.candle / "candle/fingerprint.ml").write_text("serializer\n")
        (self.candle / "candle/reference_source_contracts.json").write_text(
            json.dumps({
                "schema": "candle-s1-reference-source-contract-v1",
                "historical_upstream_commit": self.historical_head,
                "exact_source_reference_commit": self.reference_head,
                "compatibility_deltas": [{
                    "path": path,
                    "historical_sha256": historical_hashes[path],
                    "selected_sha256": selected_hashes[path],
                    "reason": "fixture compatibility delta",
                } for path in delta_paths],
            }, indent=2) + "\n")
        (self.candle / ".gitignore").write_text("__pycache__/\n")
        self.candle_head = self._commit(self.candle, "fixture Candle")
        self.runtime_paths = {}
        for name in ("runtime", "runtime-stublib", "ocamlc", "ocamlfind"):
            path = self.tools / name
            path.write_text(f"{name} fixture\n")
            self.runtime_paths[name] = path
        ocamlc_real = self.tools / "ocamlc-real"
        self.runtime_paths["ocamlc"].rename(ocamlc_real)
        self.runtime_paths["ocamlc"].symlink_to(ocamlc_real.name)
        self.pari_gp_root = self.tools / "pari-gp"
        pari_bin = self.pari_gp_root / "usr/bin"
        pari_bin.mkdir(parents=True)
        pari_executable = pari_bin / "gp-2.15"
        pari_executable.write_text("fixture PARI/GP executable\n")
        pari_executable.chmod(0o755)
        (pari_bin / "gp").symlink_to(pari_executable.name)
        self.csdp = pari_bin / "csdp"
        self.csdp.write_text(
            "#!/bin/sh\n"
            "test \"$#\" -eq 2 || exit 2\n"
            "printf 'fixture-solution\\n' >\"$2\"\n"
            "printf '%s\\n' 'CSDP 6.2.0' 'Success: SDP solved' "
            "'Primal objective value: 2.3000000e+01 ' "
            "'Dual objective value: 2.3000000e+01 ' "
            "'DIMACS error measures: 0 0 0 0 0 0' "
            "'Elements time: 0.001000 ' 'Factor time: 0.002000 ' "
            "'Other time: 0.003000 ' 'Total time: 0.006000 '\n")
        self.csdp.chmod(0o555)
        self.pari_gp_gprc = self.pari_gp_root / "candle-gprc"
        self.pari_gp_gprc.write_text("\\\\ fixture deterministic config\n")
        self.pari_gp_gprc.chmod(0o444)
        self.pari_gp_data = self.pari_gp_root / "candle-data"
        self.pari_gp_data.mkdir()
        self.pari_gp_data.chmod(0o555)
        self.csdp_source = self.pari_gp_root / "candle-csdp-source.tar.gz"
        self.csdp_source.write_bytes(b"fixture CSDP source archive\n")
        self.csdp_probe_input = self.pari_gp_root / \
            "candle-csdp-theta1.dat-s"
        self.csdp_probe_input.write_bytes(b"fixture theta1 problem\n")
        self.csdp_build_receipt = self.pari_gp_root / "candle-csdp-build.json"
        self.csdp_build_receipt.write_text(json.dumps({
            "schema": 1,
            "kind": "candle-hol-light-csdp-single-thread-build",
            "source": {
                "archive": self.csdp_source.name,
                "bytes": self.csdp_source.stat().st_size,
                "sha256": sha256(self.csdp_source.read_bytes()),
                "upstream_tree": "Csdp-6.2.0",
            },
            "toolchain": {"fixture": True},
            "recipe": {
                "cflags": "-O2 -ansi -DBIT64",
                "openmp_enabled": False,
                "native_cpu_flags": False,
            },
            "outputs": {
                "csdp_path": "usr/bin/csdp",
                "csdp_bytes": self.csdp.stat().st_size,
                "csdp_sha256": sha256(self.csdp.read_bytes()),
            },
            "unit_probe": {
                "input_path": self.csdp_probe_input.name,
                "input_bytes": self.csdp_probe_input.stat().st_size,
                "input_sha256": sha256(self.csdp_probe_input.read_bytes()),
                "exit_code": 0,
                "success_line": "Success: SDP solved",
                "primal_objective": "2.3000000e+01",
                "dual_objective": "2.3000000e+01",
                "maximum_allowed_dimacs_error": "1.0e-6",
            },
            "runtime_policy": {
                "single_process_solver": True,
                "single_thread_build": True,
                "external_shared_libraries_closed_separately": True,
            },
        }, indent=2) + "\n")
        for pin in (self.csdp_source, self.csdp_probe_input,
                    self.csdp_build_receipt):
            pin.chmod(0o444)
        self.pari_gp_package = self.tools / "pari-gp.deb"
        self.pari_gp_package.write_text("fixture hash-pinned package archive\n")
        self.pari_gp_package.chmod(0o444)

    def _create_sources(self) -> None:
        targets = []
        shared = "100/shared.ml"
        (self.candle / "100").mkdir()
        (self.reference / "100").mkdir()
        for repository in (self.candle, self.reference):
            (repository / shared).write_text("shared source\n")
        for index in range(65):
            relative = (
                ("100/e_is_transcendental.ml", "100/euler.ml", "100/lagrange.ml")[index]
                if index < 3 else f"100/test-{index:02d}.ml"
            )
            value = f"source {index}\n"
            for repository in (self.candle, self.reference):
                (repository / relative).write_text(value)
            files = [relative, shared] if index == 0 else [relative]
            theorem_count = 2 if index < 32 else 1
            targets.append({
                "name": f"100/test-{index:02d}",
                "load_files": files,
                "load_file_sha256": {
                    path: sha256((self.candle / path).read_bytes()) for path in files
                },
                "skip": None,
                "fingerprint_request": {
                    "mapping_status": "audited",
                    "theorems": [
                        {"name": f"THEOREM_{index:02d}_{offset}"}
                        for offset in range(theorem_count)
                    ],
                    "expected_identities": None,
                },
            })
        self.manifest_path = self.candle / "candle/top100_manifest.json"
        self.manifest_path.write_text(json.dumps({
            "schema_version": 1, "target_count": 65, "targets": targets,
        }, indent=2) + "\n")

    @staticmethod
    def _commit(root: Path, message: str) -> str:
        git(root, "init", "-q")
        git(root, "config", "user.email", "fixture@example.invalid")
        git(root, "config", "user.name", "fixture")
        git(root, "add", ".")
        git(root, "commit", "-qm", message)
        return git(root, "rev-parse", "HEAD")

    def arguments(self) -> argparse.Namespace:
        MODULE.PROGRAM_PATH = self.controller.resolve()
        runtime = self.runtime_paths
        pari_tree = MODULE.tree_record(
            self.pari_gp_root, "fixture PARI/GP package tree")
        pari_data_tree = MODULE.tree_record(
            self.pari_gp_data, "fixture PARI/GP data tree")
        return argparse.Namespace(
            artifact_root=self.artifacts,
            project_root=self.project,
            project_head=self.project_head,
            controller_sha256=sha256(self.controller.read_bytes()),
            python_sha256=sha256(SYSTEM_PYTHON.read_bytes()),
            git_sha256=sha256(SYSTEM_GIT.read_bytes()),
            candle_root=self.candle,
            candle_head=self.candle_head,
            manifest_sha256=sha256(self.manifest_path.read_bytes()),
            collector_sha256=sha256(self.collector.read_bytes()),
            protocol_sha256=sha256(self.protocol.read_bytes()),
            reference_root=self.reference,
            reference_head=self.reference_head,
            runtime=runtime["runtime"],
            runtime_sha256=sha256(runtime["runtime"].read_bytes()),
            runtime_stublib=runtime["runtime-stublib"],
            runtime_stublib_sha256=sha256(
                runtime["runtime-stublib"].read_bytes()),
            ocamlc=runtime["ocamlc"],
            ocamlc_sha256=sha256(runtime["ocamlc"].read_bytes()),
            ocamlfind=runtime["ocamlfind"],
            ocamlfind_sha256=sha256(runtime["ocamlfind"].read_bytes()),
            pari_gp_root=self.pari_gp_root,
            pari_gp_sha256=sha256(
                (self.pari_gp_root / "usr/bin/gp-2.15").read_bytes()),
            csdp_sha256=sha256(self.csdp.read_bytes()),
            pari_gp_package=self.pari_gp_package,
            pari_gp_package_sha256=sha256(self.pari_gp_package.read_bytes()),
            pari_gp_gprc_sha256=sha256(self.pari_gp_gprc.read_bytes()),
            pari_gp_tree_sha256=pari_tree["inventory_sha256"],
            pari_gp_data_tree_sha256=pari_data_tree["inventory_sha256"],
            csdp_source=self.csdp_source,
            csdp_source_sha256=sha256(self.csdp_source.read_bytes()),
            csdp_build_receipt=self.csdp_build_receipt,
            csdp_build_receipt_sha256=sha256(
                self.csdp_build_receipt.read_bytes()),
            csdp_probe_input=self.csdp_probe_input,
            csdp_probe_input_sha256=sha256(
                self.csdp_probe_input.read_bytes()),
            command_shell=Path("/bin/sh"),
            command_shell_sha256=sha256(Path("/bin/sh").resolve().read_bytes()),
            elf_bash_sha256=sha256(Path("/bin/bash").resolve().read_bytes()),
            elf_ldd_sha256=sha256(Path("/usr/bin/ldd").resolve().read_bytes()),
            elf_cache_sha256=sha256(Path("/etc/ld.so.cache").read_bytes()),
            elf_loader_sha256=sha256(next(
                path.resolve().read_bytes()
                for path in MODULE.ELF_LOADER_PATHS
                if path.exists()
            )),
            collection_wall_seconds=10,
            target_wall_seconds=40,
            validation_wall_seconds=10,
        )

    def command(self) -> list[str]:
        arguments = self.arguments()
        values = (
            ("artifact-root", arguments.artifact_root),
            ("project-root", arguments.project_root),
            ("project-head", arguments.project_head),
            ("controller-sha256", arguments.controller_sha256),
            ("python-sha256", arguments.python_sha256),
            ("git-sha256", arguments.git_sha256),
            ("candle-root", arguments.candle_root),
            ("candle-head", arguments.candle_head),
            ("manifest-sha256", arguments.manifest_sha256),
            ("collector-sha256", arguments.collector_sha256),
            ("protocol-sha256", arguments.protocol_sha256),
            ("reference-root", arguments.reference_root),
            ("reference-head", arguments.reference_head),
            ("runtime", arguments.runtime),
            ("runtime-sha256", arguments.runtime_sha256),
            ("runtime-stublib", arguments.runtime_stublib),
            ("runtime-stublib-sha256", arguments.runtime_stublib_sha256),
            ("ocamlc", arguments.ocamlc),
            ("ocamlc-sha256", arguments.ocamlc_sha256),
            ("ocamlfind", arguments.ocamlfind),
            ("ocamlfind-sha256", arguments.ocamlfind_sha256),
            ("pari-gp-root", arguments.pari_gp_root),
            ("pari-gp-sha256", arguments.pari_gp_sha256),
            ("csdp-sha256", arguments.csdp_sha256),
            ("pari-gp-package", arguments.pari_gp_package),
            ("pari-gp-package-sha256", arguments.pari_gp_package_sha256),
            ("pari-gp-gprc-sha256", arguments.pari_gp_gprc_sha256),
            ("pari-gp-tree-sha256", arguments.pari_gp_tree_sha256),
            ("pari-gp-data-tree-sha256",
             arguments.pari_gp_data_tree_sha256),
            ("csdp-source", arguments.csdp_source),
            ("csdp-source-sha256", arguments.csdp_source_sha256),
            ("csdp-build-receipt", arguments.csdp_build_receipt),
            ("csdp-build-receipt-sha256",
             arguments.csdp_build_receipt_sha256),
            ("csdp-probe-input", arguments.csdp_probe_input),
            ("csdp-probe-input-sha256",
             arguments.csdp_probe_input_sha256),
            ("command-shell", arguments.command_shell),
            ("command-shell-sha256", arguments.command_shell_sha256),
            ("elf-bash-sha256", arguments.elf_bash_sha256),
            ("elf-ldd-sha256", arguments.elf_ldd_sha256),
            ("elf-cache-sha256", arguments.elf_cache_sha256),
            ("elf-loader-sha256", arguments.elf_loader_sha256),
            ("collection-wall-seconds", arguments.collection_wall_seconds),
            ("target-wall-seconds", arguments.target_wall_seconds),
            ("validation-wall-seconds", arguments.validation_wall_seconds),
        )
        command = [
            "/usr/bin/env", "-i", "PATH=/usr/bin:/bin", "LC_ALL=C", "LANG=C",
            "/usr/bin/python3", "-I", "-S", str(self.controller.resolve()),
        ]
        for name, value in values:
            command.extend((f"--{name}", str(value)))
        return command


class ReferenceSweepControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="candle-reference-sweeps.")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def fixture(
        self, fail_target: str | None = None, hang_first_seconds: int = 0,
    ) -> Fixture:
        return Fixture(
            Path(self.temporary.name), fail_target, hang_first_seconds,
        )

    def publication_directory(self, name: str) -> Path:
        path = Path(self.temporary.name) / name
        path.mkdir(mode=0o700)
        return path

    def test_two_sweeps_close_in_manifest_order_and_remain_unapproved(self) -> None:
        fixture = self.fixture()
        self.assertEqual(MODULE.run(fixture.arguments()), 0)
        receipt_path = fixture.artifacts / "receipt.json"
        receipt = json.loads(receipt_path.read_text())
        self.assertEqual(receipt["target_count"], 65)
        self.assertEqual(receipt["total_target_runs"], 130)
        self.assertEqual(receipt["completed_target_runs"], 130)
        self.assertEqual(receipt["failure_attempt_count"], 0)
        self.assertTrue(receipt["closed"])
        self.assertFalse(receipt["promotion_allowed"])
        self.assertEqual(
            [row["name"] for row in receipt["sweeps"][0]["targets"]],
            [f"100/test-{index:02d}" for index in range(65)],
        )
        nonces = {
            row["success"]["session_nonce"]
            for sweep in receipt["sweeps"] for row in sweep["targets"]
        }
        self.assertEqual(len(nonces), 130)
        candidates = list(fixture.artifacts.glob(
            "sweep-*/target-*/attempt-*/candidate.json"))
        self.assertEqual(len(candidates), 130)
        self.assertTrue(all(
            json.loads(path.read_text())["promotion_allowed"] is False
            for path in candidates
        ))
        self.assertEqual(
            receipt_path.read_bytes(), MODULE.canonical_json(receipt),
        )

    def test_failure_is_retained_and_resume_uses_a_new_attempt(self) -> None:
        fixture = self.fixture("100/test-01")
        arguments = fixture.arguments()
        self.assertEqual(MODULE.run(arguments), 1)
        first = json.loads((fixture.artifacts / "status.json").read_text())
        self.assertEqual(first["completed_target_runs"], 1)
        self.assertEqual(first["failure_attempt_count"], 1)
        failed = fixture.artifacts / "sweep-1/target-002/attempt-0001"
        self.assertTrue((failed / "failure.json").is_file())
        self.assertEqual(MODULE.run(arguments), 0)
        receipt = json.loads((fixture.artifacts / "receipt.json").read_text())
        self.assertTrue(receipt["closed"])
        self.assertEqual(receipt["failure_attempt_count"], 1)
        self.assertTrue((failed.parent / "attempt-0002/success.json").is_file())
        self.assertTrue((failed / "failure.json").is_file())

    def test_resume_revalidates_completed_candidate_before_skipping(self) -> None:
        fixture = self.fixture("100/test-01")
        arguments = fixture.arguments()
        self.assertEqual(MODULE.run(arguments), 1)
        candidate = fixture.artifacts / \
            "sweep-1/target-001/attempt-0001/candidate.json"
        candidate.chmod(0o600)
        candidate.write_bytes(candidate.read_bytes() + b" \n")
        candidate.chmod(0o444)
        with self.assertRaisesRegex(MODULE.CollectionFailure,
                                    "artifact bytes changed"):
            MODULE.run(arguments)
        self.assertFalse((fixture.artifacts /
                          "sweep-1/target-002/attempt-0002").exists())

    def test_runtime_and_repository_pin_changes_fail_closed(self) -> None:
        fixture = self.fixture()
        arguments = fixture.arguments()
        fixture.runtime_paths["runtime"].write_text("changed runtime\n")
        with self.assertRaisesRegex(MODULE.CollectionFailure,
                                    "differs from command-line pin"):
            MODULE.run(arguments)

        self.temporary.cleanup()
        self.temporary = tempfile.TemporaryDirectory(
            prefix="candle-reference-sweeps-dirty.")
        fixture = self.fixture()
        (fixture.reference / "dirty.txt").write_text("dirty\n")
        with self.assertRaisesRegex(MODULE.CollectionFailure,
                                    "worktree is not clean"):
            MODULE.run(fixture.arguments())

        self.temporary.cleanup()
        self.temporary = tempfile.TemporaryDirectory(
            prefix="candle-reference-sweeps-gp-data.")
        fixture = self.fixture()
        fixture.pari_gp_data.chmod(0o755)
        (fixture.pari_gp_data / "unreviewed-table").write_text("unexpected\n")
        fixture.pari_gp_data.chmod(0o555)
        with self.assertRaisesRegex(MODULE.CollectionFailure,
                                    "optional-data tree must be empty"):
            MODULE.run(fixture.arguments())

    def test_private_root_git_flags_replacements_and_grafts_reject(self) -> None:
        fixture = self.fixture()
        arguments = fixture.arguments()
        fixture.artifacts.chmod(0o750)
        with self.assertRaisesRegex(MODULE.CollectionFailure, "exactly 0700"):
            MODULE.run(arguments)

        self.temporary.cleanup()
        self.temporary = tempfile.TemporaryDirectory(
            prefix="candle-reference-sweeps-index.")
        fixture = self.fixture()
        git(fixture.reference, "update-index", "--assume-unchanged",
            "100/test-03.ml")
        with self.assertRaisesRegex(MODULE.CollectionFailure,
                                    "assume-unchanged or skip-worktree"):
            MODULE.run(fixture.arguments())

        self.temporary.cleanup()
        self.temporary = tempfile.TemporaryDirectory(
            prefix="candle-reference-sweeps-skip.")
        fixture = self.fixture()
        git(fixture.reference, "update-index", "--skip-worktree",
            "100/test-03.ml")
        with self.assertRaisesRegex(MODULE.CollectionFailure,
                                    "assume-unchanged or skip-worktree"):
            MODULE.run(fixture.arguments())

        self.temporary.cleanup()
        self.temporary = tempfile.TemporaryDirectory(
            prefix="candle-reference-sweeps-replace.")
        fixture = self.fixture()
        git(fixture.reference, "replace", fixture.reference_head,
            fixture.historical_head)
        with self.assertRaisesRegex(MODULE.CollectionFailure,
                                    "replacement objects"):
            MODULE.run(fixture.arguments())

        self.temporary.cleanup()
        self.temporary = tempfile.TemporaryDirectory(
            prefix="candle-reference-sweeps-graft.")
        fixture = self.fixture()
        grafts = fixture.reference / ".git/info/grafts"
        grafts.write_text(
            f"{fixture.reference_head} {fixture.historical_head}\n")
        with self.assertRaisesRegex(MODULE.CollectionFailure, "grafts file"):
            MODULE.run(fixture.arguments())

    def test_outer_startup_flags_environment_and_cli_are_exact(self) -> None:
        fixture = self.fixture()
        command = fixture.command()
        hostile = fixture.tools / "hostile-python"
        hostile.mkdir()
        shadow_marker = hostile / "shadow-ran"
        shadow = hostile / "python3"
        shadow.write_text(
            f"#!/bin/sh\n: > {shadow_marker}\nexit 99\n",
        )
        shadow.chmod(0o755)
        hostile_path = list(command)
        hostile_path[2] = f"PATH={hostile}:/usr/bin:/bin"
        completed = subprocess.run(
            hostile_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertFalse(shadow_marker.exists())
        self.assertIn(b"environment is not the exact allowlist", completed.stderr)
        self.assertFalse((fixture.artifacts / "collection-contract.json").exists())

        site_directory = fixture.tools / "hostile-site"
        site_directory.mkdir()
        site_marker = site_directory / "sitecustomize-ran"
        (site_directory / "sitecustomize.py").write_text(
            f"from pathlib import Path\nPath({str(site_marker)!r}).touch()\n",
        )
        hostile_site = command[:5] + [f"PYTHONPATH={site_directory}"] + command[5:]
        completed = subprocess.run(
            hostile_site, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertFalse(site_marker.exists())
        self.assertIn(b"environment is not the exact allowlist", completed.stderr)
        self.assertFalse((fixture.artifacts / "collection-contract.json").exists())

        without_no_site = [item for item in command if item != "-S"]
        completed = subprocess.run(
            without_no_site, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn(b"isolated/no-site", completed.stderr)

        with_extra_environment = command[:5] + ["EXTRA=hostile"] + command[5:]
        completed = subprocess.run(
            with_extra_environment, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=10,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn(b"environment is not the exact allowlist", completed.stderr)

        duplicated = command + ["--git-sha256", "0" * 64]
        completed = subprocess.run(
            duplicated, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn(b"each CLI option exactly once", completed.stderr)

        wrong_controller = list(command)
        controller_index = wrong_controller.index("--controller-sha256") + 1
        wrong_controller[controller_index] = "0" * 64
        completed = subprocess.run(
            wrong_controller, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn(b"controller differs from command-line pin", completed.stderr)

        wrong_python = list(command)
        python_index = wrong_python.index("--python-sha256") + 1
        wrong_python[python_index] = "0" * 64
        completed = subprocess.run(
            wrong_python, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn(b"Python executable differs", completed.stderr)

        with fixture.controller.open("a") as output:
            output.write("\n# hostile post-commit mutation\n")
        completed = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
        )
        self.assertEqual(completed.returncode, 1)
        self.assertIn(b"project repository worktree is not clean", completed.stderr)
        self.assertFalse((fixture.artifacts / "collection-contract.json").exists())

    def test_term_and_hup_kill_active_group_and_allow_resume(self) -> None:
        for signum in (signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signal=signum), tempfile.TemporaryDirectory(
                prefix=f"candle-reference-signal-{signum}.",
            ) as root:
                fixture = Fixture(Path(root), hang_first_seconds=30)
                command = fixture.command()
                controller = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                transcript = fixture.artifacts / \
                    "sweep-1/target-001/attempt-0001/transcript.log"
                wait_for(transcript)
                words = transcript.read_text().split()
                collector_pid, runtime_pid = map(int, words[1:])
                controller.send_signal(signum)
                _stdout, stderr = controller.communicate(timeout=15)
                self.assertEqual(controller.returncode, 128 + signum)
                self.assertIn(
                    f"interrupted by signal {signum}".encode(), stderr,
                )
                wait_not_live(collector_pid)
                wait_not_live(runtime_pid)
                self.assertTrue(lock_is_available(
                    fixture.artifacts / ".controller.lock"))

                resumed = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                success = fixture.artifacts / \
                    "sweep-1/target-001/attempt-0002/success.json"
                try:
                    wait_for(success)
                finally:
                    if resumed.poll() is None:
                        resumed.send_signal(signal.SIGTERM)
                resumed.communicate(timeout=15)
                self.assertEqual(resumed.returncode, 128 + signal.SIGTERM)

    def test_sigkill_orphans_keep_lock_until_exit_then_resume(self) -> None:
        fixture = self.fixture(hang_first_seconds=3)
        command = fixture.command()
        controller = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        transcript = fixture.artifacts / \
            "sweep-1/target-001/attempt-0001/transcript.log"
        wait_for(transcript)
        words = transcript.read_text().split()
        collector_pid, runtime_pid = map(int, words[1:])
        controller.kill()
        self.assertEqual(controller.wait(timeout=5), -signal.SIGKILL)
        self.assertTrue(process_is_live(collector_pid))
        self.assertTrue(process_is_live(runtime_pid))

        probe = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
        )
        self.assertEqual(probe.returncode, 1)
        self.assertIn(b"another collection controller owns", probe.stderr)
        self.assertFalse(lock_is_available(fixture.artifacts / ".controller.lock"))
        wait_not_live(collector_pid, timeout=10)
        wait_not_live(runtime_pid, timeout=10)
        controller.communicate(timeout=2)
        self.assertTrue(lock_is_available(fixture.artifacts / ".controller.lock"))

        resumed = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        success = fixture.artifacts / \
            "sweep-1/target-001/attempt-0002/success.json"
        try:
            wait_for(success)
        finally:
            if resumed.poll() is None:
                resumed.send_signal(signal.SIGTERM)
        resumed.communicate(timeout=15)
        self.assertEqual(resumed.returncode, 128 + signal.SIGTERM)

    def test_pending_contract_and_truncated_terminals_recover_fail_closed(self) -> None:
        root = self.publication_directory("contract-publication")
        expected = b'{"contract":"exact"}\n'
        partial = root / (".collection-contract.json.pending." + "1" * 64)
        partial.write_bytes(b'{"contract":')
        partial.chmod(0o600)
        MODULE.recover_contract_publication(root, expected)
        self.assertFalse((root / "collection-contract.json").exists())
        self.assertEqual(partial.read_bytes(), b'{"contract":')
        self.assertEqual(partial.stat().st_mode & 0o777, 0o400)
        MODULE.publish_terminal(
            root / "collection-contract.json", expected, "collection contract",
            pending_name=".collection-contract.json.pending." + "2" * 64,
        )
        MODULE.recover_contract_publication(root, expected)
        interruptions = MODULE.contract_publication_interruptions(root)
        self.assertEqual([item["path"] for item in interruptions], [partial.name])

        complete_root = self.publication_directory("complete-contract")
        complete = complete_root / (
            ".collection-contract.json.pending." + "3" * 64
        )
        MODULE.exclusive_write(complete, expected, "complete pending contract")
        MODULE.recover_contract_publication(complete_root, expected)
        terminal = complete_root / "collection-contract.json"
        self.assertEqual(terminal.read_bytes(), expected)
        self.assertFalse(complete.exists())
        self.assertEqual(terminal.stat().st_nlink, 1)

        duplicate_root = self.publication_directory("duplicate-contract")
        for digit in ("4", "5"):
            MODULE.exclusive_write(
                duplicate_root / (
                    ".collection-contract.json.pending." + digit * 64
                ), expected, "duplicate complete pending contract",
            )
        with self.assertRaisesRegex(MODULE.CollectionFailure,
                                    "multiple complete"):
            MODULE.recover_contract_publication(duplicate_root, expected)

        truncated_contract_root = self.publication_directory("truncated-contract")
        truncated_contract = truncated_contract_root / "collection-contract.json"
        MODULE.exclusive_write(truncated_contract, b"{", "truncated contract")
        with self.assertRaisesRegex(MODULE.CollectionFailure,
                                    "differs from current inputs"):
            MODULE.recover_contract_publication(
                truncated_contract_root, expected,
            )
        self.assertEqual(truncated_contract.read_bytes(), b"{")

        for terminal_name in ("success.json", "failure.json"):
            attempt = self.publication_directory(f"truncated-{terminal_name}")
            terminal = attempt / terminal_name
            MODULE.exclusive_write(terminal, b"{", f"truncated {terminal_name}")
            MODULE.recover_attempt_publication(
                attempt, terminal_name, terminal_name,
            )
            with self.assertRaisesRegex(MODULE.CollectionFailure, "malformed JSON"):
                MODULE.load_json(terminal, terminal_name, single_link=True)
            self.assertEqual(terminal.read_bytes(), b"{")

    def test_attempt_pending_is_interrupted_and_never_prelink_promoted(self) -> None:
        for terminal_name in ("success.json", "failure.json"):
            attempt = self.publication_directory(f"pending-{terminal_name}")
            pending = attempt / f".{terminal_name}.pending"
            MODULE.exclusive_write(pending, b'{"complete":true}\n', "pending")
            MODULE.recover_attempt_publication(
                attempt, terminal_name, terminal_name,
            )
            self.assertTrue(pending.is_file())
            self.assertFalse((attempt / terminal_name).exists())
            self.assertEqual(pending.stat().st_nlink, 1)

            partial_attempt = self.publication_directory(
                f"partial-{terminal_name}",
            )
            partial = partial_attempt / f".{terminal_name}.pending"
            partial.write_bytes(b"partial")
            partial.chmod(0o600)
            MODULE.recover_attempt_publication(
                partial_attempt, terminal_name, terminal_name,
            )
            self.assertEqual(partial.stat().st_mode & 0o777, 0o400)
            self.assertFalse((partial_attempt / terminal_name).exists())

        for terminal_name, pending_name in (
            ("success.json", ".failure.json.pending"),
            ("failure.json", ".success.json.pending"),
        ):
            conflict = self.publication_directory(
                f"cross-{terminal_name}",
            )
            MODULE.exclusive_write(
                conflict / terminal_name, b"{}\n", "cross terminal",
            )
            MODULE.exclusive_write(
                conflict / pending_name, b"{}\n", "cross pending",
            )
            with self.assertRaisesRegex(MODULE.CollectionFailure, "conflicts"):
                MODULE.reject_cross_type_publications(conflict)

        double_pending = self.publication_directory("double-pending")
        for name in (".success.json.pending", ".failure.json.pending"):
            MODULE.exclusive_write(
                double_pending / name, b"{}\n", "double pending",
            )
        with self.assertRaisesRegex(MODULE.CollectionFailure, "both success and failure"):
            MODULE.reject_cross_type_publications(double_pending)

    def test_publication_crash_windows_and_link_invariants(self) -> None:
        class SimulatedCrash(BaseException):
            pass

        phases = (
            ("post-file-fsync", 1, False, False),
            ("post-link", 2, False, True),
            ("post-link-dir-fsync", 2, True, True),
            ("post-unlink", 3, False, True),
        )
        value = b'{"receipt":"exact"}\n'
        for phase, target_call, after_fsync, terminal_expected in phases:
            with self.subTest(phase=phase):
                attempt = self.publication_directory(phase)
                terminal = attempt / "success.json"
                pending = attempt / ".success.json.pending"
                original = MODULE.fsync_directory
                calls = 0

                def injected_fsync(descriptor: int) -> None:
                    nonlocal calls
                    calls += 1
                    if calls == target_call and not after_fsync:
                        raise SimulatedCrash()
                    original(descriptor)
                    if calls == target_call and after_fsync:
                        raise SimulatedCrash()

                with mock.patch.object(MODULE, "fsync_directory", injected_fsync):
                    with self.assertRaises(SimulatedCrash):
                        MODULE.publish_terminal(
                            terminal, value, "success receipt",
                            pending_name=pending.name,
                        )
                self.assertEqual(terminal.exists(), terminal_expected)
                MODULE.recover_attempt_publication(
                    attempt, "success.json", "success receipt",
                )
                if terminal_expected:
                    self.assertEqual(terminal.read_bytes(), value)
                    self.assertFalse(pending.exists())
                    self.assertEqual(terminal.stat().st_nlink, 1)
                else:
                    self.assertFalse(terminal.exists())
                    self.assertTrue(pending.exists())
                    self.assertEqual(pending.stat().st_nlink, 1)

        collision = self.publication_directory("collision")
        terminal = collision / "success.json"
        pending = collision / ".success.json.pending"
        MODULE.exclusive_write(terminal, b"original\n", "existing terminal")
        with self.assertRaisesRegex(MODULE.CollectionFailure, "already exists"):
            MODULE.publish_terminal(
                terminal, value, "success receipt", pending_name=pending.name,
            )
        self.assertEqual(terminal.read_bytes(), b"original\n")
        self.assertFalse(pending.exists())

        raced = self.publication_directory("link-race")
        raced_terminal = raced / "success.json"
        raced_pending = raced / ".success.json.pending"
        original_link = MODULE.os.link

        def create_conflicting_terminal(*args, **kwargs):
            MODULE.exclusive_write(
                raced_terminal, b"racing terminal\n", "racing terminal",
            )
            return original_link(*args, **kwargs)

        with mock.patch.object(MODULE.os, "link", create_conflicting_terminal):
            with self.assertRaisesRegex(MODULE.CollectionFailure,
                                        "appeared during no-overwrite"):
                MODULE.publish_terminal(
                    raced_terminal, value, "success receipt",
                    pending_name=raced_pending.name,
                )
        self.assertEqual(raced_terminal.read_bytes(), b"racing terminal\n")
        self.assertEqual(raced_pending.read_bytes(), value)
        self.assertEqual(raced_terminal.stat().st_nlink, 1)
        self.assertEqual(raced_pending.stat().st_nlink, 1)
        with self.assertRaisesRegex(MODULE.CollectionFailure, "conflicting"):
            MODULE.recover_attempt_publication(
                raced, "success.json", "success receipt",
            )

        wrong_mode = self.publication_directory("wrong-mode")
        wrong_pending = wrong_mode / ".success.json.pending"
        wrong_pending.write_bytes(value)
        wrong_pending.chmod(0o644)
        with self.assertRaisesRegex(MODULE.CollectionFailure, "unexpected interrupted mode"):
            MODULE.recover_attempt_publication(
                wrong_mode, "success.json", "success receipt",
            )

        symlink_dir = self.publication_directory("symlink")
        symlink = symlink_dir / ".success.json.pending"
        symlink.symlink_to("elsewhere")
        with self.assertRaisesRegex(MODULE.CollectionFailure, "ordinary file"):
            MODULE.recover_attempt_publication(
                symlink_dir, "success.json", "success receipt",
            )

        third_link = self.publication_directory("third-link")
        third_terminal = third_link / "success.json"
        third_pending = third_link / ".success.json.pending"
        extra = third_link / "extra-hardlink"
        original_link = MODULE.os.link

        def add_third_link(*args, **kwargs):
            result = original_link(*args, **kwargs)
            original_link(third_pending, extra, follow_symlinks=False)
            return result

        with mock.patch.object(MODULE.os, "link", add_third_link):
            with self.assertRaisesRegex(MODULE.CollectionFailure,
                                        "unexpected link count 3"):
                MODULE.publish_terminal(
                    third_terminal, value, "success receipt",
                    pending_name=third_pending.name,
                )
        self.assertEqual(third_pending.stat().st_nlink, 3)
        with self.assertRaisesRegex(MODULE.CollectionFailure,
                                    "unexpected link count"):
            MODULE.recover_attempt_publication(
                third_link, "success.json", "success receipt",
            )

    def test_actual_sigkill_and_async_signals_during_publication(self) -> None:
        value = b'{"receipt":"exact"}\n'
        for phase in ("partial-write", "post-link"):
            directory = self.publication_directory(f"kill-{phase}")
            terminal = directory / "success.json"
            pending = directory / ".success.json.pending"
            read_fd, write_fd = os.pipe()
            child = os.fork()
            if child == 0:
                try:
                    os.close(read_fd)
                    if phase == "partial-write":
                        original_write = MODULE.os.write
                        notified = False

                        def slow_write(descriptor, data):
                            nonlocal notified
                            written = original_write(descriptor, data[:1])
                            if not notified:
                                notified = True
                                original_write(write_fd, b"R")
                                time.sleep(30)
                            return written

                        MODULE.os.write = slow_write
                    else:
                        original_fsync = MODULE.fsync_directory
                        calls = 0

                        def slow_fsync(descriptor):
                            nonlocal calls
                            calls += 1
                            original_fsync(descriptor)
                            if calls == 2:
                                os.write(write_fd, b"R")
                                time.sleep(30)

                        MODULE.fsync_directory = slow_fsync
                    MODULE.publish_terminal(
                        terminal, value, "success receipt",
                        pending_name=pending.name,
                    )
                    os._exit(0)
                except BaseException:
                    os._exit(90)
            os.close(write_fd)
            try:
                self.assertEqual(os.read(read_fd, 1), b"R")
                os.kill(child, signal.SIGKILL)
                waited, status = os.waitpid(child, 0)
                self.assertEqual(waited, child)
                self.assertTrue(os.WIFSIGNALED(status))
                self.assertEqual(os.WTERMSIG(status), signal.SIGKILL)
            finally:
                os.close(read_fd)
            MODULE.recover_attempt_publication(
                directory, "success.json", "success receipt",
            )
            if phase == "partial-write":
                self.assertFalse(terminal.exists())
                self.assertTrue(pending.exists())
                self.assertEqual(pending.stat().st_mode & 0o777, 0o400)
            else:
                self.assertEqual(terminal.read_bytes(), value)
                self.assertFalse(pending.exists())
                self.assertEqual(terminal.stat().st_nlink, 1)

        original_link = MODULE.os.link
        for signum in (signal.SIGTERM, signal.SIGHUP):
            for terminal_name in (
                "collection-contract.json", "success.json", "failure.json",
            ):
                with self.subTest(signal=signum, terminal=terminal_name):
                    directory = self.publication_directory(
                        f"signal-{signum}-{terminal_name}",
                    )
                    terminal = directory / terminal_name
                    pending_name = (
                        ".collection-contract.json.pending." + "a" * 64
                        if terminal_name == "collection-contract.json" else
                        f".{terminal_name}.pending"
                    )
                    old_handlers = {
                        item: signal.getsignal(item)
                        for item in MODULE.HANDLED_SIGNALS
                    }
                    previous_mask = signal.pthread_sigmask(
                        signal.SIG_BLOCK, MODULE.HANDLED_SIGNALS,
                    )
                    for item in MODULE.HANDLED_SIGNALS:
                        signal.signal(item, MODULE.controller_signal_handler)
                    MODULE.PENDING_SIGNAL = None
                    MODULE.ACTIVE_PROCESS = None

                    def signal_then_link(*args, **kwargs):
                        os.kill(os.getpid(), signum)
                        return original_link(*args, **kwargs)

                    try:
                        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
                        with mock.patch.object(MODULE.os, "link", signal_then_link):
                            with self.assertRaises(MODULE.ControllerInterrupted):
                                MODULE.publish_terminal(
                                    terminal, value, terminal_name,
                                    pending_name=pending_name,
                                )
                    finally:
                        signal.pthread_sigmask(
                            signal.SIG_BLOCK, MODULE.HANDLED_SIGNALS,
                        )
                        for item, handler in old_handlers.items():
                            signal.signal(item, handler)
                        MODULE.PENDING_SIGNAL = None
                        MODULE.ACTIVE_PROCESS = None
                        signal.pthread_sigmask(
                            signal.SIG_SETMASK, previous_mask,
                        )
                    self.assertEqual(terminal.read_bytes(), value)
                    self.assertEqual(terminal.stat().st_nlink, 1)
                    self.assertFalse((directory / pending_name).exists())


if __name__ == "__main__":
    unittest.main()
