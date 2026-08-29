#!/usr/bin/env python3
"""Adversarial tests for the two-run Great 100 evidence finalizer."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


SCRIPT = Path(__file__).with_name("finalize-top100-report.py")
SPEC = importlib.util.spec_from_file_location("finalize_top100_report", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

HEAD = "1" * 40
CAKEML = "2" * 40
HOL4 = "3" * 40


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": digest(data)}


class Fixture:
    def __init__(self, parent: Path):
        self.root = parent / "candle-root"
        self.candle = self.root / "candle"
        self.build = self.candle / "build"
        self.build.mkdir(parents=True)
        self.run_dirs = [parent / "run-one-logs", parent / "run-two-logs"]
        for path in self.run_dirs:
            path.mkdir()
        self.report_paths = [parent / "run-one.json", parent / "run-two.json"]
        self.destination = parent / "archive"
        self._create_runtime()
        self.serializer = digest((self.candle / "fingerprint.ml").read_bytes())
        self.manifest = self._create_manifest()
        self.reports = [self._create_report(index) for index in range(2)]
        self.write_reports()

    @staticmethod
    def _theorem(index: int) -> dict[str, object]:
        return {
            "name": f"THEOREM_{index:02d}",
            "theorem_sha256": f"{index + 10:064x}",
            "hypotheses_sha256": f"{index + 100:064x}",
            "conclusion_sha256": f"{index + 200:064x}",
            "global_axioms_sha256": "a" * 64,
            "hypothesis_count": 0,
            "global_axiom_count": 3,
        }

    def _write(self, relative: str, data: bytes = b"fixture\n") -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def _create_runtime(self) -> None:
        helper = self._write(
            "candle/cakeml_artifact_provenance.py",
            (
                "import pathlib, sys\n"
                "expected = ['check-linked', '--candle-root', "
                "str(pathlib.Path(__file__).resolve().parent.parent)]\n"
                "if sys.argv[1:] != expected:\n"
                "    raise SystemExit(17)\n"
                "print('linked CakeML provenance PASS')\n"
            ).encode(),
        )
        del helper
        self._write("candle/regression.py")
        self._write("candle/top100_manifest.py")
        self._write("candle/fingerprint.ml", b"serializer fixture\n")
        self._write("candle.sh", b"#!/bin/sh\n")
        self._write("candle/cake.S.patch", b"patch fixture\n")
        direct_manifest = self._write(
            "candle/flyspeck_manifest.json", b'{"fixture": true}\n')

        for name in MODULE.LINKED_OUTPUTS:
            self._write(f"candle/build/{name}", f"{name} fixture\n".encode())
        outputs = {
            name: record(self.build / name) for name in MODULE.LINKED_OUTPUTS
        }
        linked = {
            "schema": 6,
            "kind": "candle-linked-pinned-cakeml",
            "candle_commit": HEAD,
            "cakeml_commit": CAKEML,
            "hol4_commit": HOL4,
            "manifest_sha256": digest(direct_manifest.read_bytes()),
            "bootstrap_record": record(self.build / "bootstrap-provenance.json"),
            "bootstrap_preflight": record(self.build / "bootstrap-preflight.json"),
            "bootstrap_log": record(self.build / "bootstrap.log"),
            "cake_patch": record(self.candle / "cake.S.patch"),
            "cake_patch_derivation": {"fixture": True},
            "native_link_derivation": {"fixture": True},
            "outputs": outputs,
            "runtime_elf_closure": {"fixture": True},
            "version_output_sha256": "b" * 64,
        }
        (self.build / "cakeml-build-provenance.json").write_text(
            json.dumps(linked), encoding="utf-8")

    def _create_manifest(self) -> dict[str, object]:
        targets = []
        for index in range(65):
            name = f"100/test-{index:02d}"
            file_name = f"{name}.ml"
            theorem = self._theorem(index)
            targets.append({
                "name": name,
                "load_files": [file_name],
                "load_file_sha256": {file_name: f"{index + 300:064x}"},
                "skip": None,
                "fingerprint_request": {
                    "mapping_status": "audited",
                    "theorems": [{"name": theorem["name"]}],
                    "expected_identities": {
                        "serializer_sha256": self.serializer,
                        "theorems": [theorem],
                    },
                },
            })
        manifest = {
            "schema_version": 1,
            "target_count": 65,
            "targets": targets,
        }
        (self.candle / "top100_manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8")
        return manifest

    def _create_report(self, run_index: int) -> dict[str, object]:
        results = []
        for index, target in enumerate(self.manifest["targets"]):
            theorem = target["fingerprint_request"]["expected_identities"]["theorems"][0]
            log = self.run_dirs[run_index] / f"target-{index:02d}.log"
            log.write_text(
                "linked CakeML provenance PASS\n"
                "CANDLE_FINGERPRINT_V1\tfixture\n",
                encoding="utf-8",
            )
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
                "fingerprints": {
                    "status": "matched",
                    "mapping_status": "audited",
                    "expected_identities_present": True,
                    "serializer": {
                        "path": "candle/fingerprint.ml",
                        "sha256": self.serializer,
                    },
                    "theorems": [deepcopy(theorem)],
                },
            })
        cake = self.build / "cake"
        return {
            "schema": 3,
            "generated_utc": f"2026-08-29T00:00:0{run_index}+00:00",
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
            "candle_root": str(self.root),
            "candle_git_head": HEAD,
            "candle_git_status": [],
            "candle_executable": str(cake),
            "candle_executable_sha256": digest(cake.read_bytes()),
            "log_directory": str(self.run_dirs[run_index]),
            "fingerprint_contract": deepcopy(MODULE.FINGERPRINT_CONTRACT),
            "s1_evidence": deepcopy(MODULE.S1_CLOSED),
            "results": results,
        }

    def write_reports(self) -> None:
        for path, report_value in zip(self.report_paths, self.reports):
            path.write_text(json.dumps(report_value), encoding="utf-8")


class FinalizeTop100Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="candle-top100-finalizer.")
        self.fixture = Fixture(Path(self.temporary.name))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def assert_rejected(self, pattern: str | None = None) -> None:
        context = (self.assertRaisesRegex(MODULE.ValidationError, pattern)
                   if pattern else self.assertRaises(MODULE.ValidationError))
        with context:
            MODULE.validate_reports(self.fixture.report_paths)

    def test_two_clean_runs_archive_with_closed_inventory(self) -> None:
        MODULE.archive(self.fixture.report_paths, self.fixture.destination)
        bundle = json.loads(
            (self.fixture.destination / "bundle.json").read_text(encoding="utf-8"))
        self.assertEqual(bundle["kind"], "candle-great100-two-clean-run-archive")
        self.assertEqual(bundle["comparison"]["runs"], 2)
        self.assertEqual(bundle["comparison"]["target_count"], 65)
        self.assertTrue(bundle["comparison"]["identical"])
        self.assertEqual(len(bundle["runs"]), 2)
        self.assertEqual([len(run["logs"]) for run in bundle["runs"]], [65, 65])
        self.assertIn(
            "do not record the linked-record SHA-256",
            bundle["linked_provenance"]["per_process_binding"],
        )

        checksums = {}
        for line in (self.fixture.destination / "SHA256SUMS").read_text().splitlines():
            checksum, relative = line.split("  ", 1)
            checksums[relative] = checksum
            self.assertEqual(
                digest((self.fixture.destination / relative).read_bytes()), checksum)
        expected = set(bundle["retained_files"]) | {"bundle.json"}
        self.assertEqual(set(checksums), expected)
        self.assertEqual(
            set(path.relative_to(self.fixture.destination).as_posix()
                for path in self.fixture.destination.rglob("*") if path.is_file()),
            expected | {"SHA256SUMS"},
        )
        self.assertEqual(
            (self.fixture.destination / "run-1/report.json").read_bytes(),
            self.fixture.report_paths[0].read_bytes(),
        )
        with self.assertRaisesRegex(MODULE.ValidationError, "already exists"):
            MODULE.archive(self.fixture.report_paths, self.fixture.destination)

    def test_rejects_report_and_s1_false_greens(self) -> None:
        mutations = {
            "old schema": lambda: self.fixture.reports[0].__setitem__("schema", 1),
            "extra report field": lambda: self.fixture.reports[0].__setitem__("extra", 1),
            "failed aggregate": lambda: self.fixture.reports[0].__setitem__(
                "counts", {"PASS": 64, "FAIL": 1, "TIMEOUT": 0}),
            "dirty tree": lambda: self.fixture.reports[0].__setitem__(
                "candle_git_status", [" M candle/kernel.ml"]),
            "suite not closed": lambda: self.fixture.reports[0]["s1_evidence"].__setitem__(
                "suite_closed", False),
            "identity coverage short": lambda: self.fixture.reports[0]["s1_evidence"].__setitem__(
                "expected_identity_target_count", 64),
            "load-only pass": lambda: self.fixture.reports[0]["results"][0]["fingerprints"].__setitem__(
                "status", "observed_uncompared"),
            "missing expected identity": lambda: self.fixture.reports[0]["results"][0]["fingerprints"].__setitem__(
                "expected_identities_present", False),
            "unbounded wall": lambda: self.fixture.reports[0]["timeout_policy"].__setitem__(
                "total_wall_timeout_seconds", None),
            "zero RSS": lambda: self.fixture.reports[0]["results"][0].__setitem__(
                "peak_tree_rss_kib", 0),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                original = deepcopy(self.fixture.reports)
                mutate()
                self.fixture.write_reports()
                self.assert_rejected()
                self.fixture.reports = original
                self.fixture.write_reports()

    def test_rejects_order_semantics_and_runtime_disagreement(self) -> None:
        mutations = {
            "result order": lambda: self.fixture.reports[0]["results"].__setitem__(
                slice(0, 2), list(reversed(self.fixture.reports[0]["results"][0:2]))),
            "semantic divergence": lambda: self.fixture.reports[1]["results"][0]["fingerprints"]["theorems"][0].__setitem__(
                "theorem_sha256", "f" * 64),
            "head divergence": lambda: self.fixture.reports[1].__setitem__(
                "candle_git_head", "9" * 40),
            "executable divergence": lambda: self.fixture.reports[1].__setitem__(
                "candle_executable_sha256", "8" * 64),
            "timeout divergence": lambda: self.fixture.reports[1]["timeout_policy"].__setitem__(
                "total_wall_timeout_seconds", 20000),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                original = deepcopy(self.fixture.reports)
                mutate()
                self.fixture.write_reports()
                self.assert_rejected()
                self.fixture.reports = original
                self.fixture.write_reports()

    def test_rejects_log_path_and_witness_attacks(self) -> None:
        first_log = Path(self.fixture.reports[0]["results"][0]["log_path"])
        original_text = first_log.read_text()

        first_log.write_text("CANDLE_FINGERPRINT_V1\tfixture\n")
        self.assert_rejected("linked-provenance witness")
        first_log.write_text(original_text + "linked CakeML provenance PASS\n")
        self.assert_rejected("linked-provenance witness")
        first_log.write_text("linked CakeML provenance PASS\n")
        self.assert_rejected("fingerprint-record count")
        first_log.write_text(original_text)

        self.fixture.reports[0]["results"][1]["log_path"] = str(first_log)
        self.fixture.write_reports()
        self.assert_rejected()
        self.fixture.reports[0]["results"][1]["log_path"] = str(
            self.fixture.run_dirs[0] / "target-01.log")

        outside = Path(self.temporary.name) / "outside.log"
        outside.write_text(original_text)
        self.fixture.reports[0]["results"][0]["log_path"] = str(outside)
        self.fixture.write_reports()
        self.assert_rejected("outside")
        self.fixture.reports[0]["results"][0]["log_path"] = str(first_log)
        self.fixture.write_reports()

        first_log.unlink()
        first_log.symlink_to(self.fixture.run_dirs[1] / "target-00.log")
        self.assert_rejected("symlink")

    def test_rejects_manifest_and_linked_provenance_drift(self) -> None:
        manifest_path = self.fixture.candle / "top100_manifest.json"
        original_manifest = manifest_path.read_bytes()
        manifest = json.loads(original_manifest)
        manifest["targets"][0]["fingerprint_request"]["expected_identities"] = None
        manifest_path.write_text(json.dumps(manifest))
        self.assert_rejected("missing approved")
        manifest_path.write_bytes(original_manifest)

        serializer = self.fixture.candle / "fingerprint.ml"
        serializer.write_bytes(serializer.read_bytes() + b"tamper")
        self.assert_rejected("approved serializer")
        serializer.write_bytes(b"serializer fixture\n")

        record_path = self.fixture.build / "cakeml-build-provenance.json"
        original_record = record_path.read_bytes()
        linked = json.loads(original_record)
        linked["schema"] = 5
        record_path.write_text(json.dumps(linked))
        self.assert_rejected("unsupported linked")
        record_path.write_bytes(original_record)

        linked = json.loads(original_record)
        linked["candle_commit"] = "8" * 40
        record_path.write_text(json.dumps(linked))
        self.assert_rejected("reported Candle head")
        record_path.write_bytes(original_record)

        cake = self.fixture.build / "cake"
        cake.write_bytes(cake.read_bytes() + b"tamper")
        self.assert_rejected("linked output changed")

    def test_rejects_failed_authoritative_linked_check(self) -> None:
        helper = self.fixture.candle / "cakeml_artifact_provenance.py"
        helper.write_text("raise SystemExit(1)\n")
        self.assert_rejected("authoritative linked-provenance")

    def test_rejects_duplicate_json_keys_and_report_alias(self) -> None:
        self.fixture.report_paths[0].write_text('{"schema":3,"schema":3}\n')
        self.assert_rejected("duplicate JSON key")
        self.fixture.write_reports()
        with self.assertRaisesRegex(MODULE.ValidationError, "must be distinct"):
            MODULE.validate_reports(
                [self.fixture.report_paths[0], self.fixture.report_paths[0]])

        report_hardlink = Path(self.temporary.name) / "report-hardlink.json"
        os.link(self.fixture.report_paths[0], report_hardlink)
        with self.assertRaisesRegex(MODULE.ValidationError, "hard-link aliases"):
            MODULE.validate_reports([self.fixture.report_paths[0], report_hardlink])

        report_alias = Path(self.temporary.name) / "report-alias.json"
        report_alias.symlink_to(self.fixture.report_paths[0])
        with self.assertRaisesRegex(MODULE.ValidationError, "symlink"):
            MODULE.validate_reports([report_alias, self.fixture.report_paths[1]])

    def test_rejects_cross_run_log_reuse_and_time_accounting(self) -> None:
        first_log = Path(self.fixture.reports[0]["results"][0]["log_path"])
        second_log = Path(self.fixture.reports[1]["results"][0]["log_path"])
        second_log.unlink()
        os.link(first_log, second_log)
        self.assert_rejected("reuse transcript files")

        second_log.unlink()
        second_log.write_bytes(first_log.read_bytes())
        self.fixture.reports[0]["sum_test_seconds"] = 1.0
        self.fixture.write_reports()
        self.assert_rejected("aggregate test time")

    def test_refuses_destination_alias_and_changed_validated_source(self) -> None:
        destination_alias = Path(self.temporary.name) / "archive-alias"
        destination_alias.symlink_to(Path(self.temporary.name) / "missing-target")
        with self.assertRaisesRegex(MODULE.ValidationError, "already exists"):
            MODULE.archive(self.fixture.report_paths, destination_alias)

        source = Path(self.temporary.name) / "copy-source"
        source.write_bytes(b"before")
        expected = MODULE.file_identity(source, "copy fixture")
        source.write_bytes(b"after")
        with self.assertRaisesRegex(MODULE.ValidationError, "changed before"):
            MODULE.copy_verified(
                source, Path(self.temporary.name) / "copy-destination",
                "copy fixture", expected,
            )

    def test_cli_requires_exactly_two_reports_and_destination(self) -> None:
        completed = subprocess.run(
            ["/usr/bin/python3", "-I", str(SCRIPT),
             str(self.fixture.report_paths[0]), str(self.fixture.destination)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("report_two", completed.stderr)


if __name__ == "__main__":
    unittest.main()
