#!/usr/bin/env python3
"""Static/adversarial tests for the resumable reference-sweep controller."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("run-top100-reference-sweeps.py")
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


FAKE_COLLECTOR = r'''#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "candle/top100_manifest.json"
FAIL_FIRST_TARGET = __FAIL_TARGET__


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
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    collect = sub.add_parser("collect")
    for name in ("target", "reference-root", "runtime", "runtime-stublib",
                 "ocamlc", "ocamlfind", "plan", "request", "source-mode",
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
        if (candidate["schema"] != "candle-s1-reference-candidate-v6" or
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
    plan = {
        "schema": "candle-s1-reference-plan-v6",
        "status": "planned_not_executed",
        "session_nonce": nonce,
        "reference": {
            "root": str(reference_root),
            "git_head": subprocess.check_output([
                "/usr/bin/git", "-C", str(reference_root), "rev-parse", "HEAD"
            ], text=True).strip(),
            "git_status": [],
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
            },
        },
        "request": {"source": request.decode(), "sha256": digest(request)},
        "fresh_process_contract": {"required": True},
    }
    plan_path.write_text(json.dumps(plan, indent=2) + "\n")
    Path(args.request).write_bytes(request)
    if FAIL_FIRST_TARGET and args.target == FAIL_FIRST_TARGET and \
            plan_path.parent.name == "attempt-0001" and \
            plan_path.parent.parent.parent.name == "sweep-1":
        print("injected first-attempt failure", file=sys.stderr)
        return 7
    transcript = f"TRANSCRIPT {args.target} {nonce}\n".encode()
    Path(args.transcript).write_bytes(transcript)
    candidate = {
        "schema": "candle-s1-reference-candidate-v6",
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
    def __init__(self, root: Path, fail_target: str | None = None):
        self.root = root.resolve()
        self.candle = self.root / "candle-repo"
        self.reference = self.root / "reference-repo"
        self.artifacts = self.root / "artifacts"
        self.tools = self.root / "tools"
        for directory in (self.candle / "candle", self.reference,
                          self.artifacts, self.tools):
            directory.mkdir(parents=True, exist_ok=True)
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
        ).encode()
        self.collector = self.candle / "candle/reference_fingerprints.py"
        self.collector.write_bytes(collector)
        self.collector.chmod(0o644)
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
        runtime = self.runtime_paths
        return argparse.Namespace(
            artifact_root=self.artifacts,
            candle_root=self.candle,
            candle_head=self.candle_head,
            manifest_sha256=sha256(self.manifest_path.read_bytes()),
            collector_sha256=sha256(self.collector.read_bytes()),
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
            collection_wall_seconds=10,
            target_wall_seconds=40,
            validation_wall_seconds=10,
        )


class ReferenceSweepControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="candle-reference-sweeps.")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def fixture(self, fail_target: str | None = None) -> Fixture:
        return Fixture(Path(self.temporary.name), fail_target)

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


if __name__ == "__main__":
    unittest.main()
