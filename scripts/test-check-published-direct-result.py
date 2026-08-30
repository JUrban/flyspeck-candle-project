#!/usr/bin/python3

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


SUBJECT_PATH = Path(__file__).with_name("check-published-direct-result.py")
SPEC = importlib.util.spec_from_file_location("published_direct_result", SUBJECT_PATH)
assert SPEC is not None and SPEC.loader is not None
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


class FakePlanModule:
    HOST_MATERIALIZATION = "host-materialization.json"
    PLAN_ROOT_MODE = 0o555
    PLAN_FILE_MODE = 0o444

    @staticmethod
    def json_bytes(value):
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()

    @staticmethod
    def make_host_schedule(plan, plan_sha256):
        return {"kind": "test-schedule", "plan": plan, "plan_sha256": plan_sha256}


class FakeController:
    flyspeck_stratum_plan = FakePlanModule()
    SOURCE_DIGEST_RELATIVE = Path("candle/flyspeck_source_digests.ml")
    SETUP_RELATIVE = Path("candle/flyspeck_stratum_setup.ml")
    CHECK_RELATIVE = Path("candle/flyspeck_stratum_check.ml")
    FINGERPRINT_RELATIVE = Path("candle/fingerprint.ml")
    L2_TARGET_RELATIVE = Path("candle/flyspeck_l2_target.ml")
    LINKED_RECORD_RELATIVE = Path("candle/build/cakeml-build-provenance.json")
    DIRECT_INPUT_FIELDS = frozenset({"plan"})

    @staticmethod
    def json_bytes(value):
        return FakePlanModule.json_bytes(value)

    @staticmethod
    def canonical_sha256(value):
        data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        return subject.hashlib.sha256(data).hexdigest()


class FakeCaptureProtocol:
    AUTHENTICATED_CAPTURE_POLICY = "test-content-bound-capture-v1"
    COMPARISON_CANDIDATE_AUTHORITY_POLICY = "test-candidate-authority-v1"
    COMPILED_COMPARISON_AUTHENTICATOR = "test-compiled-consumer"
    AUTHENTICATED_COMPARISON_DESCRIPTOR_KIND = "test-comparison-candidate-v1"
    COMPILED_COMPARISON_ROLE = "test-compiled-role"
    COMPILED_COMPARISON_NONCE_KIND = "test-attempt-nonce-v1"

    @staticmethod
    def canonical_json_bytes(value):
        return (json.dumps(
            value, indent=2, sort_keys=True, allow_nan=False,
        ) + "\n").encode()

    @classmethod
    def build_authenticated_schema6_capture(cls, receipt, plan, authority):
        return {
            "receipt": subject.data_record(cls.canonical_json_bytes(receipt)),
            "authenticated_plan":
                subject.data_record(cls.canonical_json_bytes(plan)),
            "semantic_projection": {"test": "semantic"},
            "coverage_projection": {"test": "coverage"},
            "authority": authority,
            "promotion": False,
            "approval_included": False,
            "direct_s2_execution_approved": False,
            "direct_s3_coverage_approved": False,
            "v1_3_s3_release_approved": False,
            "pft_used": False,
            "s2_s3_evidence": False,
        }

    @classmethod
    def _validate_authenticated_comparison_descriptor(
        cls, descriptor, *, role, ordinal,
    ):
        if (descriptor.get("kind") !=
                cls.AUTHENTICATED_COMPARISON_DESCRIPTOR_KIND or
                role != cls.COMPILED_COMPARISON_ROLE or ordinal != 0):
            raise ValueError("bad fake comparison descriptor")
        return descriptor


def make_record(data: bytes, *, path: str | None = None):
    result = subject.data_record(data)
    if path is not None:
        result = {"path": path, **result}
    return result


def restore_writable(root: Path) -> None:
    if not root.exists():
        return
    for current, directories, files in os.walk(root, topdown=False):
        for name in files:
            os.chmod(Path(current) / name, 0o644, follow_symlinks=False)
        for name in directories:
            path = Path(current) / name
            if not path.is_symlink():
                os.chmod(path, 0o755)
    os.chmod(root, 0o755)


class PublishedDirectResultTests(unittest.TestCase):
    def test_comparison_candidate_requires_schema6(self):
        arguments = [
            str(SUBJECT_PATH),
            "--project-root", "/project",
            "--project-head", "0" * 40,
            "--plan-root", "/plan",
            "--plan-sha256", "1" * 64,
            "--result-root", "/result",
            "--boundary", "boundary",
            "--candle-root", "/candle",
            "--candle-head", "2" * 40,
            "--cakeml-head", "3" * 40,
            "--hol4-head", "4" * 40,
            "--flyspeck-root", "/flyspeck",
            "--flyspeck-head", "5" * 40,
            "--timeout-seconds", "1",
            "--max-cpu-seconds", "1",
            "--max-address-space-gib", "1",
            "--max-output-file-gib", "1",
            "--comparison-candidate",
        ]
        with mock.patch.object(sys, "argv", arguments), self.assertRaisesRegex(
            subject.ResultError, "requires evidence schema 6",
        ):
            subject.main()

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(subject.ResultError, "duplicate JSON key"):
            subject.decode_object(b'{"schema":5,"schema":4}', "receipt")

    def test_stable_file_size_cap(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "log"
            path.write_bytes(b"1234")
            with self.assertRaisesRegex(subject.ResultError, "size cap"):
                subject.stable_file_bytes(path, "log", max_bytes=3)

    def test_resource_contract_requires_exact_runtime_sizes(self):
        receipt = {
            "timeout_seconds": 10,
            "resource_limits": {
                "cpu_seconds": 9,
                "address_space_bytes": 48 * subject.GIB,
                "output_file_bytes": 8 * subject.GIB,
            },
            "runtime_environment": {
                **subject.RUNTIME_BASE_ENVIRONMENT,
                "CML_HEAP_SIZE": "4096",
            },
        }
        subject.validate_resource_contract(receipt, 10, 9, 48, 8, "4096", None)
        with self.assertRaisesRegex(subject.ResultError, "runtime environment"):
            subject.validate_resource_contract(receipt, 10, 9, 48, 8, "8192", None)
        with self.assertRaisesRegex(subject.ResultError, "malformed explicit"):
            subject.validate_resource_contract(receipt, 10, 9, 48, 8, "04096", None)

    def test_exact_source_module_replaces_module_collision(self):
        name = "_published_direct_collision_test"
        sys.modules[name] = types.SimpleNamespace(MARK="hostile")
        try:
            module = subject.exact_source_module(
                name, Path("/authenticated/controller.py"), b"MARK = 'source'\n",
            )
            self.assertEqual(module.MARK, "source")
            self.assertIs(sys.modules[name], module)
        finally:
            sys.modules.pop(name, None)

    def test_named_directory_replacement_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            root = parent / "result"
            root.mkdir()
            descriptor, identity = subject.open_pinned_directory(root, "result")
            try:
                root.rename(parent / "old-result")
                root.mkdir()
                with self.assertRaisesRegex(subject.ResultError, "identity changed"):
                    subject.require_named_directory_identity(
                        descriptor, root, identity, "result",
                    )
            finally:
                os.close(descriptor)

    def test_open_pinned_directory_closes_descriptor_on_identity_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "result"
            root.mkdir()
            real_open = os.open
            opened = []

            def record_open(*args, **kwargs):
                descriptor = real_open(*args, **kwargs)
                opened.append(descriptor)
                return descriptor

            with mock.patch.object(subject.os, "open", side_effect=record_open), \
                    mock.patch.object(
                        subject, "require",
                        side_effect=subject.ResultError("forced identity failure"),
                    ):
                with self.assertRaisesRegex(
                    subject.ResultError, "forced identity failure",
                ):
                    subject.open_pinned_directory(root, "result")
            self.assertEqual(len(opened), 1)
            with self.assertRaises(OSError):
                os.fstat(opened[0])

    def test_held_lock_rejects_build_directory_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            candle = Path(temporary) / "candle-root"
            build = candle / "candle/build"
            build.mkdir(parents=True)
            descriptor = os.open(build, os.O_RDONLY | os.O_DIRECTORY)
            opened = os.fstat(descriptor)
            lock = types.SimpleNamespace(
                fd=descriptor,
                record={
                    "path": str(build), "object": "directory_inode",
                    "mode": "shared", "device": opened.st_dev,
                    "inode": opened.st_ino,
                },
            )
            try:
                subject.validate_held_runtime_lock(lock, candle)
                build.rename(candle / "candle/old-build")
                build.mkdir()
                with self.assertRaisesRegex(subject.ResultError, "lock object"):
                    subject.validate_held_runtime_lock(lock, candle)
            finally:
                os.close(descriptor)

    def test_malformed_receipt_input_closure_is_clean_rejection(self):
        with self.assertRaisesRegex(subject.ResultError, "input closure"):
            subject.validate_current_bindings(
                FakeController(), {}, {}, Path("/candle"), {}, "boundary",
                "0" * 40, "1" * 40, "2" * 40,
            )

    def test_gate_result_separates_scheduling_from_promotion(self):
        arguments = types.SimpleNamespace(
            boundary="d0", project_head="0" * 40,
        )
        diagnostic = subject.build_gate_result(
            arguments, {"actions": [1], "diagnostic_only": True},
            Path("/result"),
        )
        self.assertFalse(diagnostic["scheduling_authority"])
        self.assertFalse(diagnostic["promotion"])
        self.assertFalse(diagnostic["s2_s3_evidence"])
        ordinary = subject.build_gate_result(
            arguments, {"actions": [1], "diagnostic_only": False},
            Path("/result"),
        )
        self.assertTrue(ordinary["scheduling_authority"])
        self.assertFalse(ordinary["promotion"])

    def test_schema6_capture_binds_exact_held_source_bytes(self):
        receipt = {"schema": 6, "state": "completed"}
        plan = {"schema": 1, "action_count": 297}
        receipt_data = FakeCaptureProtocol.canonical_json_bytes(receipt)
        plan_data = FakeCaptureProtocol.canonical_json_bytes(plan)
        arguments = types.SimpleNamespace(
            evidence_schema=6,
            project_head="1" * 40,
            candle_head="2" * 40,
            cakeml_head="3" * 40,
            hol4_head="4" * 40,
            flyspeck_head="5" * 40,
        )
        capture = subject.build_schema6_capture_result(
            FakeCaptureProtocol, arguments, receipt, plan,
            receipt_data, plan_data,
        )
        self.assertEqual(capture["receipt"], subject.data_record(receipt_data))
        self.assertEqual(
            capture["authenticated_plan"], subject.data_record(plan_data),
        )
        self.assertEqual(
            capture["authority"]["consumer_project_commit"], "1" * 40,
        )
        self.assertFalse(capture["approval_included"])
        self.assertFalse(capture["direct_s2_execution_approved"])
        self.assertFalse(capture["direct_s3_coverage_approved"])
        self.assertFalse(capture["v1_3_s3_release_approved"])
        with self.assertRaisesRegex(subject.ResultError, "canonical JSON"):
            subject.build_schema6_capture_result(
                FakeCaptureProtocol, arguments, receipt, plan,
                receipt_data + b" ", plan_data,
            )

    def test_compiled_descriptor_derives_its_authenticated_source_authority(
        self,
    ):
        receipt = {"attempt_nonce": "9" * 32}
        capture = {
            "authenticated_plan": make_record(b"plan\n"),
            "semantic_projection": {"test": "semantic"},
            "coverage_projection": {"test": "coverage"},
        }
        arguments = types.SimpleNamespace(
            project_head="1" * 40, candle_head="2" * 40,
        )
        sources = {
            "scripts/direct_release_protocol.py": b"protocol\n",
            "scripts/check-published-direct-result.py": b"consumer\n",
        }
        descriptor = subject._assemble_compiled_comparison_descriptor(
            FakeCaptureProtocol, arguments, capture, receipt,
            "scripts/check-published-direct-result.py", sources,
        )
        authority = descriptor["candidate_authority"]
        self.assertEqual(authority["project_commit"], "1" * 40)
        self.assertEqual(authority["runtime_commit"], "2" * 40)
        self.assertEqual(
            [record["path"] for record in authority["sources"]],
            sorted(sources),
        )
        self.assertEqual(
            authority["entrypoint"],
            {
                "path": "scripts/check-published-direct-result.py",
                **subject.data_record(b"consumer\n"),
            },
        )
        self.assertEqual(
            descriptor["candidate"],
            subject.data_record(FakeCaptureProtocol.canonical_json_bytes(capture)),
        )
        with self.assertRaisesRegex(
            subject.ResultError, "entrypoint is not authenticated",
        ):
            subject._assemble_compiled_comparison_descriptor(
                FakeCaptureProtocol, arguments, capture, receipt,
                "scripts/not-the-consumer.py", sources,
            )

    def test_pinned_plan_rejects_extra_file_and_wrong_digest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "plan"
            root.mkdir()
            prefix = b"#use \"source.hl\";;\n"
            prefix_record = make_record(prefix, path="prefix.ml")
            plan = {
                "boundaries": [{"cumulative_prefix": prefix_record}],
                "diagnostic_cutpoints": [],
            }
            plan_data = FakePlanModule.json_bytes(plan)
            materialization = {"kind": "test-materialization"}
            materialization_data = FakePlanModule.json_bytes(materialization)
            schedule_data = FakePlanModule.json_bytes(
                FakePlanModule.make_host_schedule(
                    plan, subject.data_record(plan_data)["sha256"],
                )
            )
            for relative, data in (
                ("plan.json", plan_data),
                ("host-materialization.json", materialization_data),
                ("host-schedule-template.json", schedule_data),
                ("prefix.ml", prefix),
            ):
                path = root / relative
                path.write_bytes(data)
                path.chmod(0o444)
            root.chmod(0o555)
            prepared = {
                "plan": plan,
                "plan_record": subject.data_record(plan_data),
                "materialization_record": subject.data_record(materialization_data),
            }
            descriptor, _identity = subject.open_pinned_directory(root, "plan")
            try:
                pinned = Path(f"/proc/self/fd/{descriptor}")
                subject.validate_pinned_plan_tree(
                    FakeController(), pinned, prepared,
                    prepared["plan_record"]["sha256"],
                )
                with self.assertRaisesRegex(subject.ResultError, "explicit direct plan"):
                    subject.validate_pinned_plan_tree(
                        FakeController(), pinned, prepared, "0" * 64,
                    )
                root.chmod(0o755)
                extra = root / "extra"
                extra.write_bytes(b"extra")
                extra.chmod(0o444)
                root.chmod(0o555)
                with self.assertRaisesRegex(subject.ResultError, "tree closure"):
                    subject.validate_pinned_plan_tree(
                        FakeController(), pinned, prepared,
                        prepared["plan_record"]["sha256"],
                    )
            finally:
                os.close(descriptor)
                restore_writable(root)

    def test_result_tree_requires_exact_modes_and_closure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "result"
            snapshot_root = root / "snapshot"
            control_root = root / "control"
            snapshot_root.mkdir(parents=True)
            control_root.mkdir()
            payload = b"payload"
            (snapshot_root / "payload").write_bytes(payload)
            snapshot = {"files": [{"path": "payload", **make_record(payload)}]}
            snapshot_data = FakeController.json_bytes(snapshot)
            attempt_data = b"{}\n"
            log_data = b"success\n"
            control_data = {
                field: (field + "\n").encode() for field in subject.CONTROL_INPUT_PATHS
            }
            for field, relative in subject.CONTROL_INPUT_PATHS.items():
                (root / relative).write_bytes(control_data[field])
            (root / "snapshot.json").write_bytes(snapshot_data)
            (root / "attempt.json").write_bytes(attempt_data)
            (root / "candle.log").write_bytes(log_data)
            receipt = {
                "inputs": {
                    **{field: make_record(control_data[field])
                       for field in subject.CONTROL_INPUT_PATHS},
                    "runtime_snapshot": make_record(snapshot_data),
                },
                "initial_attempt": make_record(attempt_data),
                "log": make_record(log_data),
            }
            receipt_data = FakeController.json_bytes(receipt)
            (root / "receipt.json").write_bytes(receipt_data)
            for path in root.rglob("*"):
                if path.is_file():
                    path.chmod(0o444)
            snapshot_root.chmod(0o555)
            control_root.chmod(0o555)
            try:
                subject.validate_closed_result_tree(
                    root, receipt, receipt_data, snapshot, FakeController(),
                )
                (root / "control/stdin.ml").chmod(0o644)
                with self.assertRaisesRegex(subject.ResultError, "mode mismatch"):
                    subject.validate_closed_result_tree(
                        root, receipt, receipt_data, snapshot, FakeController(),
                    )
            finally:
                restore_writable(root)

    def test_result_tree_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "target").write_bytes(b"x")
            (root / "link").symlink_to("target")
            with self.assertRaisesRegex(subject.ResultError, "non-ordinary"):
                subject._ordinary_tree(root)

    def test_result_tree_rejects_hard_link(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "first").write_bytes(b"x")
            os.link(root / "first", root / "second")
            with self.assertRaisesRegex(subject.ResultError, "multiply linked"):
                subject._ordinary_tree(root)

    def test_snapshot_inventory_is_reconstructed_from_current_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            candle = Path(temporary) / "candle-root"
            build = candle / "candle/build"
            build.mkdir(parents=True)
            current_files = {
                "config_enc_str.txt": b"config",
                "candle_boot.ml": b"boot",
                "cakeml-build-provenance.json": b"{}\n",
            }
            for relative, data in current_files.items():
                (build / relative).write_bytes(data)
            elf = Path(temporary) / "libc.so"
            elf.write_bytes(b"elf")
            source = make_record(b"source")
            harness = {
                relative.as_posix(): make_record((relative.as_posix() + "\n").encode())
                for relative in (
                    FakeController.SOURCE_DIGEST_RELATIVE,
                    FakeController.SETUP_RELATIVE,
                    FakeController.CHECK_RELATIVE,
                    FakeController.FINGERPRINT_RELATIVE,
                    FakeController.L2_TARGET_RELATIVE,
                )
            }
            # The digest harness deliberately collides with the source record,
            # just as the producer merges classifications for duplicate paths.
            harness[FakeController.SOURCE_DIGEST_RELATIVE.as_posix()] = source
            prepared = {
                "source_runtime": [{
                    "repository": "candle",
                    "path": FakeController.SOURCE_DIGEST_RELATIVE.as_posix(),
                    **source,
                }],
                "harness_records": harness,
                "linked_record": make_record(current_files[
                    "cakeml-build-provenance.json"
                ]),
                "normalized_runtime": [],
                "generated_runtime": [],
                "process_runtime": [],
                "prefix_record": make_record(b"prefix", path="prefix.ml"),
            }
            linked = {
                "outputs": {
                    name: make_record(data)
                    for name, data in current_files.items()
                    if name != "cakeml-build-provenance.json"
                },
                "runtime_elf_closure": {
                    "files": {str(elf): make_record(b"elf")},
                },
            }
            retained = {
                "local_sources": [],
                "python_runtime": {"executable": make_record(b"python", path="controller/python-runtime/python"), "elf_objects": []},
                "host_tools": [],
            }
            records = subject.reconstruct_snapshot_records(
                FakeController(), candle, prepared, linked, retained,
            )
            self.assertEqual(records[0]["classes"], [
                "source:candle", "runtime-harness",
            ])
            snapshot = {
                "files": records,
                "file_count": len(records),
                "ordered_file_sha256": FakeController.canonical_sha256(records),
            }
            subject.validate_snapshot_against_current_authority(
                FakeController(), snapshot, candle, prepared, linked, retained,
            )
            snapshot["files"] = [dict(item) for item in records]
            snapshot["files"][-1]["sha256"] = "0" * 64
            with self.assertRaisesRegex(subject.ResultError, "current authority"):
                subject.validate_snapshot_against_current_authority(
                    FakeController(), snapshot, candle, prepared, linked, retained,
                )


if __name__ == "__main__":
    unittest.main()
