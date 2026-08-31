#!/usr/bin/python3

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


SUBJECT_PATH = Path(__file__).with_name("check-canonical-bootstrap-gate.py")
SPEC = importlib.util.spec_from_file_location("canonical_bootstrap_gate", SUBJECT_PATH)
assert SPEC is not None and SPEC.loader is not None
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


class CanonicalBootstrapGateTests(unittest.TestCase):
    def make_git_root(self, parent: Path, name: str) -> tuple[Path, str]:
        root = parent / name
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / "tracked").write_text(name, encoding="ascii")
        subprocess.run(["git", "-C", str(root), "add", "tracked"], check=True)
        subprocess.run([
            "git", "-C", str(root), "-c", "user.name=Gate Test", "-c",
            "user.email=gate@example.invalid", "commit", "-qm", "fixture",
        ], check=True)
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
            text=True, stdout=subprocess.PIPE,
        ).stdout.strip()
        return root, head

    def fixture(self, parent: Path):
        replay = parent / "replay"
        replay.mkdir()
        (replay / "stage").write_text("complete\n", encoding="ascii")
        (replay / "started_utc").write_text("2026-08-28T23:59:59Z\n", encoding="ascii")
        (replay / "finished_utc").write_text("2026-08-29T00:00:00Z\n", encoding="ascii")
        (replay / "controller_pid").write_text("999999\n", encoding="ascii")
        candle, candle_head = self.make_git_root(parent, "candle")
        cakeml, cakeml_head = self.make_git_root(parent, "cakeml")
        hol4, hol4_head = self.make_git_root(parent, "hol4")
        project, _project_initial_head = self.make_git_root(parent, "project")
        controller = project / subject.REPLAY_CONTROLLER_RELATIVE
        controller.parent.mkdir()
        controller.write_bytes(
            Path(__file__).with_name("run-canonical-bootstrap-replay.sh").read_bytes()
        )
        subprocess.run([
            "git", "-C", str(project), "add", subject.REPLAY_CONTROLLER_RELATIVE,
        ], check=True)
        subprocess.run([
            "git", "-C", str(project), "-c", "user.name=Gate Test", "-c",
            "user.email=gate@example.invalid", "commit", "-qm", "controller",
        ], check=True)
        project_head = subprocess.run(
            ["git", "-C", str(project), "rev-parse", "HEAD"], check=True,
            text=True, stdout=subprocess.PIPE,
        ).stdout.strip()
        (replay / "controller_project_root").write_text(
            f"{project}\n", encoding="utf-8",
        )
        (replay / "controller_project_head").write_text(
            f"{project_head}\n", encoding="ascii",
        )
        (replay / "controller_script_relative").write_text(
            f"{subject.REPLAY_CONTROLLER_RELATIVE}\n", encoding="ascii",
        )
        (replay / "controller_script_sha256").write_text(
            f"{hashlib.sha256(controller.read_bytes()).hexdigest()}\n",
            encoding="ascii",
        )
        (replay / "cakeml_ignored_products_preflight").write_text(
            "none\n", encoding="ascii",
        )
        for relative, target in zip(
            subject.TIME_RECEIPTS, subject.TIME_TARGETS, strict=True,
        ):
            values = [
                f'"{hol4}/bin/Holmake -j1 --mt=1 {target}"',
                "1.00", "0.10", "100%", "0:01.10",
                *("0" for _ in range(16)), "4096", "0",
            ]
            self.assertEqual(len(values), len(subject.TIME_FIELDS))
            (replay / relative).write_text("".join(
                f"\t{field}: {value}\n"
                for field, value in zip(subject.TIME_FIELDS, values, strict=True)
            ), encoding="utf-8")
        for relative in subject.CAKEML_POSTCONDITIONS:
            path = cakeml / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("output\n", encoding="ascii")
        subprocess.run(["git", "-C", str(cakeml), "add", "."], check=True)
        subprocess.run([
            "git", "-C", str(cakeml), "-c", "user.name=Gate Test", "-c",
            "user.email=gate@example.invalid", "commit", "-qm", "outputs",
        ], check=True)
        arguments_cakeml_head = subprocess.run(
            ["git", "-C", str(cakeml), "rev-parse", "HEAD"], check=True,
            text=True, stdout=subprocess.PIPE,
        ).stdout.strip()

        proc = parent / "proc"
        proc.mkdir()
        (proc / "meminfo").write_text(
            "MemAvailable: 130000000 kB\n", encoding="ascii",
        )
        arguments = type("Arguments", (), {
            "replay_root": replay,
            "replay_controller_pid": 999999,
            "replay_process_group": 999999,
            "candle_root": candle,
            "candle_head": candle_head,
            "cakeml_root": cakeml,
            "cakeml_head": arguments_cakeml_head,
            "hol4_root": hol4,
            "hol4_head": hol4_head,
            "attempt_root": parent / "attempt-001",
            "minimum_mem_available_gib": 120,
            "proc_root": proc,
            "project_root": project,
            "project_head": project_head,
        })()
        return arguments

    def test_complete_fresh_gate_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            result = subject.validate_gate(arguments)
            self.assertEqual(result["gate"], "canonical-cakeml-bootstrap-ready")
            self.assertEqual(result["live_holmake_pids"], [])
            self.assertEqual(result["live_replay_process_group_members"], [])

    def test_incomplete_replay_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            (arguments.replay_root / "stage").write_text(
                "compiler64ProgTheory.uo\n", encoding="ascii",
            )
            with self.assertRaisesRegex(subject.GateError, "not completed"):
                subject.validate_gate(arguments)

    def test_live_holmake_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            process = arguments.proc_root / "123"
            process.mkdir()
            (process / "comm").write_text("Holmake\n", encoding="ascii")
            (process / "exe").symlink_to("/tool/Holmake")
            with self.assertRaisesRegex(subject.GateError, "Holmake is still live"):
                subject.validate_gate(arguments)

    def test_existing_attempt_root_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            arguments.attempt_root.mkdir()
            with self.assertRaisesRegex(subject.GateError, "already exists"):
                subject.validate_gate(arguments)

    def test_nonempty_ignored_product_preflight_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            (arguments.replay_root / "cakeml_ignored_products_preflight").write_text(
                "present\n", encoding="ascii",
            )
            with self.assertRaisesRegex(subject.GateError, "empty ignored-product"):
                subject.validate_gate(arguments)

    def test_replay_controller_digest_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            (arguments.replay_root / "controller_script_sha256").write_text(
                f"{'0' * 64}\n", encoding="ascii",
            )
            with self.assertRaisesRegex(subject.GateError, "digest mismatch"):
                subject.validate_gate(arguments)

    def test_nonzero_time_receipt_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            receipt = arguments.replay_root / subject.TIME_RECEIPTS[3]
            receipt.write_text(
                receipt.read_text(encoding="utf-8").replace(
                    "\tExit status: 0", "\tExit status: 1",
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(subject.GateError, "exit zero"):
                subject.validate_gate(arguments)

    def test_orphaned_replay_process_group_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            process = arguments.proc_root / "123"
            process.mkdir()
            (process / "stat").write_text(
                "123 (child with spaces) S 1 999999 999999 0 0 0 0 0 0 0 0 "
                "0 0 0 0 0 0 0 100\n",
                encoding="ascii",
            )
            with self.assertRaisesRegex(subject.GateError, "process group"):
                subject.validate_gate(arguments)

    def test_symlinked_time_receipt_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            receipt = arguments.replay_root / subject.TIME_RECEIPTS[0]
            target = arguments.replay_root / "relabeled-time"
            receipt.rename(target)
            receipt.symlink_to(target.name)
            with self.assertRaisesRegex(subject.GateError, "ordinary"):
                subject.validate_gate(arguments)

    def test_truncated_time_receipt_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            receipt = arguments.replay_root / subject.TIME_RECEIPTS[0]
            receipt.write_text("".join(
                receipt.read_text(encoding="utf-8").splitlines(keepends=True)[:2]
            ), encoding="utf-8")
            with self.assertRaisesRegex(subject.GateError, "field count"):
                subject.validate_gate(arguments)

    def test_malformed_time_numeric_field_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            receipt = arguments.replay_root / subject.TIME_RECEIPTS[0]
            receipt.write_text(
                receipt.read_text(encoding="utf-8").replace(
                    "\tUser time (seconds): 1.00",
                    "\tUser time (seconds): one",
                ), encoding="utf-8",
            )
            with self.assertRaisesRegex(subject.GateError, "CPU fields"):
                subject.validate_gate(arguments)

    def test_reordered_time_fields_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            receipt = arguments.replay_root / subject.TIME_RECEIPTS[0]
            lines = receipt.read_text(encoding="utf-8").splitlines(keepends=True)
            lines[1], lines[2] = lines[2], lines[1]
            receipt.write_text("".join(lines), encoding="utf-8")
            with self.assertRaisesRegex(subject.GateError, "field mismatch"):
                subject.validate_gate(arguments)

    def test_trailing_time_junk_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            receipt = arguments.replay_root / subject.TIME_RECEIPTS[0]
            with receipt.open("a", encoding="utf-8") as output:
                output.write("trailing junk\n")
            with self.assertRaisesRegex(subject.GateError, "field count"):
                subject.validate_gate(arguments)

    def test_pinned_replay_pid_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            arguments.replay_controller_pid = 888888
            with self.assertRaisesRegex(subject.GateError, "pinned launch"):
                subject.validate_gate(arguments)


if __name__ == "__main__":
    unittest.main()
