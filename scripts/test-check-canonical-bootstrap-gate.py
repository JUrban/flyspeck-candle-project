#!/usr/bin/python3

from __future__ import annotations

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
        (replay / "finished_utc").write_text("2026-08-29T00:00:00Z\n", encoding="ascii")
        (replay / "controller_pid").write_text("999999\n", encoding="ascii")
        for relative in subject.TIME_RECEIPTS:
            (replay / relative).write_text("receipt\n", encoding="ascii")

        candle, candle_head = self.make_git_root(parent, "candle")
        cakeml, cakeml_head = self.make_git_root(parent, "cakeml")
        hol4, hol4_head = self.make_git_root(parent, "hol4")
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
            "candle_root": candle,
            "candle_head": candle_head,
            "cakeml_root": cakeml,
            "cakeml_head": arguments_cakeml_head,
            "hol4_root": hol4,
            "hol4_head": hol4_head,
            "attempt_root": parent / "attempt-001",
            "minimum_mem_available_gib": 120,
            "proc_root": proc,
        })()
        return arguments

    def test_complete_fresh_gate_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            result = subject.validate_gate(arguments)
            self.assertEqual(result["gate"], "canonical-cakeml-bootstrap-ready")
            self.assertEqual(result["live_holmake_pids"], [])

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


if __name__ == "__main__":
    unittest.main()
