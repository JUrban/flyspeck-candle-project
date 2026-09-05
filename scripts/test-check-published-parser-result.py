#!/usr/bin/python3

from __future__ import annotations

import importlib.util
import marshal
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest


SUBJECT_PATH = Path(__file__).with_name("check-published-parser-result.py")
SPEC = importlib.util.spec_from_file_location("published_parser_result", SUBJECT_PATH)
assert SPEC is not None and SPEC.loader is not None
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


def receipt(count: int, outcome: str = "parse-ok"):
    return {
        "capability": {
            "stdout": {"path": "capability.stdout"},
            "stderr": {"path": "capability.stderr"},
        },
        "attempts": [
            {
                "index": index,
                "outcome": outcome,
                "stdout": {"path": f"attempts/{index:03d}.stdout"},
                "stderr": {"path": f"attempts/{index:03d}.stderr"},
            }
            for index in range(count)
        ],
    }


class PublishedParserResultTests(unittest.TestCase):
    def test_exact_transcript_closure(self):
        paths = subject.transcript_paths(receipt(20), 20)
        self.assertEqual(len(paths), 42)
        self.assertEqual(paths[:2], ["capability.stdout", "capability.stderr"])
        self.assertEqual(paths[-1], "attempts/019.stderr")

    def test_parse_failure_rejected(self):
        value = receipt(2)
        value["attempts"][1]["outcome"] = "parse-error"
        with self.assertRaisesRegex(subject.ResultError, "did not parse"):
            subject.transcript_paths(value, 2)

    def test_reordered_attempt_rejected(self):
        value = receipt(2)
        value["attempts"].reverse()
        with self.assertRaisesRegex(subject.ResultError, "malformed parser attempt"):
            subject.transcript_paths(value, 2)

    def test_relabeled_transcript_rejected(self):
        value = receipt(1)
        value["attempts"][0]["stdout"]["path"] = "attempts/000.stderr"
        with self.assertRaisesRegex(subject.ResultError, "stdout path"):
            subject.transcript_paths(value, 1)

    def test_resource_contract_is_exact(self):
        for profile, address_space_gib, heap_mib in (
            ("pilot", 16, 4096),
            ("all-inventory", 24, 16384),
        ):
            expected = subject.expected_resource_limits(profile)
            self.assertEqual(
                expected["address_space_bytes"], address_space_gib * subject.GIB,
            )
            self.assertEqual(
                expected["runtime_environment"]["CML_HEAP_SIZE"], str(heap_mib),
            )
            self.assertEqual(
                subject.validate_resource_limits(expected, profile), expected,
            )
            for field, replacement in (
                ("timeout_seconds", 601),
                ("address_space_bytes", 120 * subject.GIB),
                ("capture", "relabeled"),
            ):
                altered = dict(expected)
                altered[field] = replacement
                with self.assertRaisesRegex(subject.ResultError, "exact contract"):
                    subject.validate_resource_limits(altered, profile)

        with self.assertRaisesRegex(subject.ResultError, "unknown parser"):
            subject.expected_resource_limits("unknown")

    def test_resource_contract_rejects_runtime_environment_changes(self):
        expected = subject.expected_resource_limits("all-inventory")
        runtime_environment = expected["runtime_environment"]
        for environment in (
            {**runtime_environment, "CML_HEAP_SIZE": "4096"},
            {**runtime_environment, "UNEXPECTED": "1"},
            {"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        ):
            altered = dict(expected)
            altered["runtime_environment"] = environment
            with self.assertRaisesRegex(subject.ResultError, "exact contract"):
                subject.validate_resource_limits(altered, "all-inventory")

    def test_profile_substitution_is_rejected(self):
        pilot = subject.expected_resource_limits("pilot")
        with self.assertRaisesRegex(subject.ResultError, "exact contract"):
            subject.validate_resource_limits(pilot, "all-inventory")

    def test_loader_ignores_timestamp_valid_ignored_bytecode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "candle/__pycache__").mkdir(parents=True)
            source = root / "candle/flyspeck_parser_diagnostic.py"
            source.write_text(
                "import sys\nfrom pathlib import Path\n"
                "SOURCE_BYTES=Path(__file__).read_bytes()\nMARK='source'\n",
                encoding="utf-8",
            )
            (root / ".gitignore").write_text("__pycache__/\n", encoding="ascii")
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run([
                "git", "-C", str(root), "-c", "user.name=Result Test", "-c",
                "user.email=result@example.invalid", "commit", "-qm", "fixture",
            ], check=True)
            head = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
                text=True, stdout=subprocess.PIPE,
            ).stdout.strip()
            status = source.stat()
            hostile = compile(
                "import sys\nfrom pathlib import Path\n"
                "SOURCE_BYTES=Path(__file__).read_bytes()\n"
                "MARK='BYTECODE_SELECTED'\n",
                str(source), "exec",
            )
            pyc = root / "candle/__pycache__/flyspeck_parser_diagnostic.cpython-312.pyc"
            pyc.write_bytes(
                importlib.util.MAGIC_NUMBER +
                struct.pack("<III", 0, int(status.st_mtime), status.st_size) +
                marshal.dumps(hostile)
            )
            module = subject.load_controller(root, head)
            self.assertEqual(module.MARK, "source")

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


if __name__ == "__main__":
    unittest.main()
