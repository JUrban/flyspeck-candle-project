#!/usr/bin/env python3

import argparse
import hashlib
import importlib.util
import json
import stat
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "run-nonpromotable-parser-development.py"
SPEC = importlib.util.spec_from_file_location("development_parser_runner", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)

COMMIT_A = "a" * 40
COMMIT_B = "b" * 40
COMMIT_C = "c" * 40


class DevelopmentParserRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.plan_root = self.root / "plan"
        self.plan_root.mkdir()
        self.runtime = self.root / "runtime"
        self.runtime.write_text(
            "#!/usr/bin/python3\n"
            "import sys\n"
            "cap = '--candle-parser-diagnostic-capability-v1'\n"
            "run = '--candle-parser-diagnostic-v1'\n"
            "if sys.argv[1] == cap:\n"
            " sys.stdout.buffer.write(b'CANDLE_CAMLPARSER_DIAGNOSTIC_CAPABILITY_V1\\t'"
            "+ b'caml_parser$run\\tstdin-exact-bytes\\tparser-only\\t'"
            "+ b'no-inference\\tno-evaluation\\n')\n"
            "elif sys.argv[1] == run:\n"
            " nonce = sys.argv[2].encode()\n"
            " assert len(nonce) == 64 and all(c in b'0123456789abcdef' for c in nonce)\n"
            " data = sys.stdin.buffer.read()\n"
            " if data == b'bad':\n"
            "  sys.stdout.buffer.write(b'CANDLE_CAMLPARSER_DIAGNOSTIC_V1\\t' + nonce + b'\\tPARSE_ERROR\\n')\n"
            "  sys.stderr.buffer.write(b'test parse error\\n')\n"
            "  raise SystemExit(65)\n"
            " sys.stdout.buffer.write(b'CANDLE_CAMLPARSER_DIAGNOSTIC_V1\\t' + nonce + b'\\tOK\\n')\n"
            "else:\n"
            " raise SystemExit(2)\n"
        )
        self.runtime.chmod(0o755)
        self.runtime_link_receipt = self.root / "DEVELOPMENT-NONPROMOTABLE.json"
        self.write_runtime_link_receipt()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_plan(self, bad_index=None) -> dict:
        inputs = []
        for index in range(20):
            data = b"bad" if index == bad_index else f"input {index}\n".encode()
            relative = f"inputs/{index:03d}.ml"
            path = self.plan_root / relative
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(data)
            inputs.append({
                "index": index,
                "source_key": f"test:{index}",
                "status": "ready",
                "prepared_input": {
                    "path": relative,
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                },
            })
        plan = {
            "schema": 2,
            "kind": "candle-flyspeck-caml-parser-diagnostic-plan",
            "promotion": {
                "eligible": False,
                "s1_evidence": False,
                "s2_evidence": False,
                "s3_evidence": False,
            },
            "repositories": {
                "candle_commit": COMMIT_B,
                "cakeml_commit": COMMIT_A,
                "hol4_commit": COMMIT_C,
                "flyspeck_commit": "d" * 40,
            },
            "input_count": 20,
            "ready_count": 20,
            "unsupported_count": 0,
            "inputs": inputs,
        }
        (self.plan_root / "plan.json").write_bytes(subject.json_bytes(plan))
        return plan

    def write_runtime_link_receipt(self) -> None:
        data = self.runtime.read_bytes()
        receipt = {
            "schema": 1,
            "kind": "nonpromotable-candle-development-link",
            "promotion_allowed": False,
            "s1_evidence": False,
            "s2_evidence": False,
            "s3_evidence": False,
            "ordinary_linked_provenance_produced": False,
            "repositories": {
                "cakeml": {
                    "commit": COMMIT_A, "root": "/fixture/cakeml",
                    "tracked_worktree_clean": True,
                },
                "candle": {
                    "commit": COMMIT_B, "root": "/fixture/candle",
                    "tracked_worktree_clean": True,
                },
                "hol4": {
                    "commit": COMMIT_C, "root": "/fixture/hol4",
                    "tracked_worktree_clean": True,
                },
            },
            "products": {
                "cake": {
                    "path": "cake", "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                },
            },
        }
        self.runtime_link_receipt.write_bytes(subject.json_bytes(receipt))

    def arguments(self, name="result"):
        return argparse.Namespace(
            profile="pilot",
            plan_root=self.plan_root,
            runtime=self.runtime,
            runtime_link_receipt=self.runtime_link_receipt,
            output_root=self.root / name,
            timeout_seconds=10,
            max_cpu_seconds=10,
            max_address_space_gib=1,
            max_output_mib=1,
        )

    def test_pass_is_published_but_never_promotable(self) -> None:
        self.write_plan()
        receipt = subject.run(self.arguments())
        self.assertEqual(receipt["outcome"], "development-parse-pass")
        self.assertEqual(receipt["parse_ok_count"], 20)
        self.assertEqual(receipt["outcome_counts"], {"parse-ok": 20})
        for field in ("promotion_allowed", "s1_evidence", "s2_evidence", "s3_evidence"):
            self.assertFalse(receipt[field])
        self.assertFalse(receipt["ordinary_linked_provenance_consumed"])
        result = self.root / "result"
        published = json.loads((result / "DEVELOPMENT-NONPROMOTABLE.json").read_text())
        self.assertEqual(published, receipt)
        self.assertEqual(stat.S_IMODE(result.stat().st_mode), 0o555)
        self.assertEqual(
            stat.S_IMODE((result / "attempts/000.stdout").stat().st_mode), 0o444,
        )

    def test_parse_error_is_retained_as_development_failure(self) -> None:
        self.write_plan(bad_index=7)
        receipt = subject.run(self.arguments())
        self.assertEqual(receipt["outcome"], "development-parse-fail")
        self.assertEqual(receipt["parse_ok_count"], 19)
        self.assertEqual(
            receipt["outcome_counts"], {"parse-error": 1, "parse-ok": 19},
        )
        self.assertEqual(receipt["attempts"][7]["exit_code"], 65)
        self.assertEqual(receipt["attempts"][7]["outcome"], "parse-error")

    def test_prepared_input_drift_is_rejected_before_publication(self) -> None:
        self.write_plan()
        (self.plan_root / "inputs/003.ml").write_bytes(b"changed")
        with self.assertRaisesRegex(subject.ContractError, "identity mismatch"):
            subject.run(self.arguments())
        self.assertFalse((self.root / "result").exists())

    def test_capability_mismatch_is_rejected_before_publication(self) -> None:
        self.write_plan()
        self.runtime.write_text("#!/bin/sh\nprintf 'wrong\\n'\n")
        self.runtime.chmod(0o755)
        self.write_runtime_link_receipt()
        with self.assertRaisesRegex(subject.ContractError, "capability handshake"):
            subject.run(self.arguments())
        self.assertFalse((self.root / "result").exists())

    def test_runtime_link_identity_mismatch_is_rejected_before_publication(self) -> None:
        self.write_plan()
        self.runtime.write_bytes(self.runtime.read_bytes() + b"# drift\n")
        with self.assertRaisesRegex(subject.ContractError, "runtime identity"):
            subject.run(self.arguments())
        self.assertFalse((self.root / "result").exists())


if __name__ == "__main__":
    unittest.main()
