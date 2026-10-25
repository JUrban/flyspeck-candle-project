#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check-long-run-hazards.py"
SPEC = importlib.util.spec_from_file_location("long_run_gate", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
GATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATE
SPEC.loader.exec_module(GATE)


class LongRunHazardGateTests(unittest.TestCase):
    def test_ledger_has_only_registered_checks(self) -> None:
        ledger = json.loads(
            (ROOT / "docs/long-run-hazard-ledger.json").read_text(encoding="utf-8")
        )
        hazards = ledger["hazards"]
        self.assertEqual(len({item["id"] for item in hazards}), len(hazards))
        self.assertGreaterEqual(len(hazards), 19)
        for item in hazards:
            self.assertIn(item["check_id"], GATE.CHECKS)
            profiles = item.get("profiles", ["theorem", "support-stage"])
            self.assertTrue(profiles)
            self.assertTrue(
                set(profiles).issubset({"theorem", "support-stage"})
            )

    def test_parse_receipt_splits_only_first_equals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "receipt"
            path.write_text("status=0\nmarker=a=b\n", encoding="utf-8")
            self.assertEqual(GATE.parse_receipt(path), {"status": "0", "marker": "a=b"})

    def test_controller_target_must_be_literal_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            good = root / "good.sh"
            bad = root / "bad.sh"
            good.write_text("run=/project/example-run\n", encoding="utf-8")
            bad.write_text("run=$base/example-run\n", encoding="utf-8")
            self.assertEqual(
                GATE.controller_run_target(good), pathlib.Path("/project/example-run")
            )
            self.assertIsNone(GATE.controller_run_target(bad))

    def test_stage_output_is_a_run_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "stage.sh"
            path.write_text("output=/project/stage-output\n", encoding="utf-8")
            self.assertEqual(
                GATE.controller_run_target(path), pathlib.Path("/project/stage-output")
            )

    def test_stage_controller_timeout_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "stage.sh"
            path.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "# check-long-run-hazards.py\n"
                "export FAST_NL_PHASE_TIMEOUT_SECONDS=3300\n",
                encoding="utf-8",
            )
            result = GATE.check_bounded_controller(
                {"maximum_support_stage_seconds": 3600}, path
            )
            self.assertTrue(result.ok, result.detail)

            path.write_text(
                path.read_text(encoding="utf-8").replace("3300", "7200"),
                encoding="utf-8",
            )
            result = GATE.check_bounded_controller(
                {"maximum_support_stage_seconds": 3600}, path
            )
            self.assertFalse(result.ok)

    def test_existing_controller_retains_exact_theorem_contract(self) -> None:
        controller = ROOT / "scripts/run-fast-nl-v664-first-theorem-controller.sh"
        result = GATE.check_theorem_controller_contract({}, controller)
        self.assertTrue(result.ok, result.detail)

    def test_short_probe_is_bound_to_exact_candidate_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            candidate = root / "support.ml"
            candidate.write_text("print_endline \"ready\";;\n", encoding="utf-8")
            predecessor = root / "checkpoint.receipt"
            predecessor.write_text(
                "checkpoint_sha256=predecessor-digest\n", encoding="utf-8"
            )
            receipt = root / "probe.receipt"
            _, manifest_sha = GATE.short_probe_input_manifest([candidate])
            runtime_sha = "runtime-digest"
            receipt.write_text(
                "\n".join(
                    [
                        "receipt_kind=development-fast-nl-short-runtime-probe-v1",
                        "release_evidence=false",
                        "status=0",
                        f"runtime_sha256={runtime_sha}",
                        "predecessor_checkpoint_sha256=predecessor-digest",
                        f"input_manifest_sha256={manifest_sha}",
                        "ready_marker_count=1",
                        "source_error_count=0",
                        "pending_source_id_count=0",
                        "elapsed_seconds=12.5",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            config = {
                "runtime_sha256": runtime_sha,
                "short_runtime_probe": {
                    "receipt": str(receipt),
                    "maximum_elapsed_seconds": 60,
                    "predecessor_checkpoint_receipt": str(predecessor),
                    "required_files": [str(candidate)],
                },
            }
            result = GATE.check_short_runtime_probe(config, root / "unused.sh")
            self.assertTrue(result.ok, result.detail)

            candidate.write_text("print_endline \"changed\";;\n", encoding="utf-8")
            result = GATE.check_short_runtime_probe(config, root / "unused.sh")
            self.assertFalse(result.ok)
            self.assertIn("input_manifest_sha256", result.detail)

    def test_short_probe_fails_closed_without_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            candidate = root / "support.ml"
            candidate.write_text("();;\n", encoding="utf-8")
            predecessor = root / "checkpoint.receipt"
            predecessor.write_text("checkpoint_sha256=x\n", encoding="utf-8")
            config = {
                "runtime_sha256": "runtime-digest",
                "short_runtime_probe": {
                    "receipt": str(root / "missing.receipt"),
                    "maximum_elapsed_seconds": 60,
                    "predecessor_checkpoint_receipt": str(predecessor),
                    "required_files": [str(candidate)],
                },
            }
            result = GATE.check_short_runtime_probe(config, root / "unused.sh")
            self.assertFalse(result.ok)
            self.assertIn("short_probe_receipt_missing", result.detail)

    def test_predecessor_must_descend_from_complete_identity_setup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            setup = root / "setup.ml"
            setup.write_text("let identities = 283;;\n", encoding="utf-8")
            data = root / "data.ml"
            data.write_text("let rows = [];;\n", encoding="utf-8")
            checkpoint = root / "base.dmtcp"
            source_receipt = root / "checkpoint.receipt"
            source_receipt.write_text(
                "authenticated_fast_nl_source_count=283\n"
                f"checkpoint={checkpoint}\n",
                encoding="utf-8",
            )
            (root / "input-files.sha256").write_text(
                f"{GATE.sha256(setup)}  {setup.resolve()}\n"
                f"{GATE.sha256(data)}  {data.resolve()}\n",
                encoding="utf-8",
            )
            predecessor = root / "action49.receipt"
            predecessor.write_text(
                f"base_checkpoint={checkpoint}\n", encoding="utf-8"
            )
            config = {
                "required_authenticated_fast_nl_source_count": 283,
                "short_runtime_probe": {
                    "predecessor_checkpoint_receipt": str(predecessor),
                    "source_configuration_receipt": str(source_receipt),
                    "source_configuration_inputs": [str(setup), str(data)],
                },
            }
            result = GATE.check_predecessor_identity_coverage(
                config, root / "unused.sh"
            )
            self.assertTrue(result.ok, result.detail)

            source_receipt.write_text(
                "authenticated_fast_nl_source_count=218\n"
                f"checkpoint={checkpoint}\n",
                encoding="utf-8",
            )
            result = GATE.check_predecessor_identity_coverage(
                config, root / "unused.sh"
            )
            self.assertFalse(result.ok)
            self.assertIn("authenticated_fast_nl_source_count", result.detail)


if __name__ == "__main__":
    unittest.main()
