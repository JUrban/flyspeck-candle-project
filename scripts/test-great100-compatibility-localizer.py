#!/usr/bin/env python3
"""Tests for the explicitly nonpromotable Great-100 compact localizer."""

import hashlib
import importlib.util
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name(
    "run-great100-compatibility-localizer.py")
SPEC = importlib.util.spec_from_file_location(
    "great100_compatibility_localizer_under_test", SCRIPT)
SUBJECT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SUBJECT
SPEC.loader.exec_module(SUBJECT)


def identity(value):
    return {
        "md5": hashlib.md5(value, usedforsecurity=False).hexdigest(),
        "bytes": len(value),
    }


class LocalFailure(Exception):
    pass


class FakeRegression:
    OCAML_VALUE_PATH_RE = re.compile(
        r"^[A-Za-z][A-Za-z0-9_']*(?:\.[A-Za-z][A-Za-z0-9_']*)*$")


class CompatibilityLocalizerTest(unittest.TestCase):
    def test_exact_normalization_is_materialized_without_changing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            candle_root = root / "candle"
            log_dir = root / "logs"
            source_path = candle_root / "100" / "sample.ml"
            source_path.parent.mkdir(parents=True)
            log_dir.mkdir()
            source = b"before unique fragment after\n"
            source_path.write_bytes(source)
            specification = SUBJECT.SourceNormalization(
                targets=("100/sample",),
                source="100/sample.ml",
                expected_sha256=hashlib.sha256(source).hexdigest(),
                replacements=((b"unique fragment", b"normalized fragment"),),
                rationale="test",
            )
            setup, contract = SUBJECT._materialize_normalizations(
                candle_root, log_dir, [SimpleNamespace(name="100/sample")],
                (specification,))

            self.assertEqual(source_path.read_bytes(), source)
            normalized = log_dir / "normalizations" / "100" / "sample.ml"
            self.assertEqual(
                normalized.read_bytes(), b"before normalized fragment after\n")
            self.assertTrue(contract["active"])
            self.assertFalse(contract["promotion_eligible"])
            self.assertEqual(contract["sources"][0]["replacement_count"], 1)
            setup_source = setup.read_text(encoding="ascii")
            self.assertIn('"100/sample.ml"', setup_source)
            self.assertIn(str(normalized), setup_source)
            self.assertIn("configureNormalizationOverlay", setup_source)
            self.assertEqual(
                contract["sources"][0]["runtime_original"],
                "100/sample.ml")

    def test_normalization_rejects_wrong_source_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            candle_root = root / "candle"
            log_dir = root / "logs"
            source_path = candle_root / "100" / "sample.ml"
            source_path.parent.mkdir(parents=True)
            log_dir.mkdir()
            source_path.write_bytes(b"source\n")
            specification = SUBJECT.SourceNormalization(
                targets=("100/sample",), source="100/sample.ml",
                expected_sha256="0" * 64,
                replacements=((b"source", b"normalized"),), rationale="test")
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                SUBJECT._materialize_normalizations(
                    candle_root, log_dir,
                    [SimpleNamespace(name="100/sample")], (specification,))
            self.assertFalse((log_dir / "normalizations").exists())

    def test_normalization_setup_loads_once_between_hol_and_target(self):
        calls = []

        def original_load(repl, file):
            calls.append(str(file))

        repl = SimpleNamespace()
        wrapped = SUBJECT._load_after_normalization_setup(
            original_load, "/tmp/normalization-setup.ml")
        wrapped(repl, "hol.ml")
        wrapped(repl, "100/sample.ml")
        wrapped(repl, "candle/fingerprint.ml")
        self.assertEqual(calls, [
            "hol.ml", "/tmp/normalization-setup.ml", "100/sample.ml",
            "candle/fingerprint.ml",
        ])

    def test_csdp_target_setup_precedes_target_load(self):
        calls = []

        def original_load(repl, file):
            calls.append(str(file))

        bridge = {
            "target": "100/ceva",
            "directory": Path("/tmp/ceva-csdp"),
            "setup": Path("/tmp/ceva-csdp/setup.ml"),
        }
        handler = object()
        repl = SimpleNamespace()
        wrapped = SUBJECT._load_after_normalization_setup(
            original_load, "/tmp/normalization-setup.ml",
            {"100/ceva.ml": bridge}, handler)
        wrapped(repl, "hol.ml")
        wrapped(repl, "100/ceva.ml")
        self.assertEqual(calls, [
            "hol.ml", "/tmp/normalization-setup.ml",
            "/tmp/ceva-csdp/setup.ml", "100/ceva.ml",
        ])
        self.assertIs(repl._great100_csdp_bridge, bridge)
        self.assertIs(repl._progress_line_handler, handler)

    def test_csdp_request_runs_fixed_argv_and_returns_status(self):
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name).resolve()
            input_path = directory / "sos.dat-s"
            output_path = directory / "sos.out"
            input_path.write_text("problem", encoding="ascii")
            (directory / "param.csdp").write_text(
                "printlevel=1\n", encoding="ascii")
            sent = []
            repl = SimpleNamespace(
                _great100_csdp_bridge={
                    "target": "100/ceva", "directory": directory},
                process=SimpleNamespace(sendline=sent.append))
            requests = []

            def fake_run(argv, **kwargs):
                self.assertEqual(argv[0], "/fixed/csdp")
                self.assertEqual(argv[1:], [str(input_path), str(output_path)])
                self.assertEqual(kwargs["cwd"], directory)
                output_path.write_text("solution", encoding="ascii")
                return SimpleNamespace(returncode=3)

            handler = SUBJECT._csdp_progress_handler(
                Path("/fixed/csdp"), requests, LocalFailure)
            with mock.patch.object(SUBJECT.subprocess, "run", fake_run):
                handler(
                    repl,
                    f"{SUBJECT.CSDP_REQUEST_MARKER}\t"
                    f"{input_path}\t{output_path}")

            self.assertEqual(sent, ["3"])
            self.assertEqual(len(requests), 1)
            self.assertEqual(requests[0]["returncode"], 3)
            self.assertEqual(requests[0]["target"], "100/ceva")

    def test_normalization_accepts_selected_load_and_canonical_finish(self):
        repl = SimpleNamespace()

        def selected_then_canonical(_repl):
            raise AssertionError(
                "Expected to finish loading /derived/sample.ml. "
                "Actual: 100/sample.ml")

        wrapped = SUBJECT._check_output_with_normalizations(
            selected_then_canonical,
            {"/derived/sample.ml": "100/sample.ml"})
        self.assertIsNone(wrapped(repl))

        unexpected = SUBJECT._check_output_with_normalizations(
            selected_then_canonical,
            {"/derived/other.ml": "100/other.ml"})
        with self.assertRaisesRegex(AssertionError, "sample.ml"):
            unexpected(repl)

    def test_completed_session_uses_clean_eof_not_missing_exit_binding(self):
        class Process:
            exitstatus = 0
            signalstatus = None

            def __init__(self):
                self.eof_sent = False
                self.closed = False

            def sendeof(self):
                self.eof_sent = True

            def expect(self, patterns, timeout):
                self.patterns = patterns
                self.timeout = timeout
                return 0

            def close(self):
                self.closed = True

        process = Process()
        regression = SimpleNamespace(
            _effective_expect_timeout=lambda inactivity, deadline:
                (inactivity, False),
            pexpect=SimpleNamespace(EOF=object(), TIMEOUT=object()),
            WallTimeout=RuntimeError,
            InactivityTimeout=RuntimeError,
            LoadFailure=RuntimeError,
        )
        repl = SimpleNamespace(
            inactivity_timeout=3600.0, wall_deadline=None, process=process)
        status = SUBJECT._finish_candle_at_eof(regression, repl)
        self.assertEqual(status, 0)
        self.assertTrue(process.eof_sent)
        self.assertTrue(process.closed)
        self.assertEqual(process.timeout, 300.0)

    def test_reference_wire_is_rechecked_and_compacted(self):
        theorem = b"theorem-wire"
        hypotheses = b"4:list1:0"
        conclusion = b"conclusion-wire"
        axioms = b"axiom-wire"
        state_parts = (
            b"state-wire", b"type-wire", b"constant-wire",
            b"definition-wire", axioms,
        )
        theorem_fields = [
            SUBJECT.FINGERPRINT_MARKER, b"THM".hex().encode("ascii"),
            theorem.hex().encode("ascii"), hypotheses.hex().encode("ascii"),
            conclusion.hex().encode("ascii"), axioms.hex().encode("ascii"),
            b"0", b"3",
        ]
        state_fields = [
            SUBJECT.STATE_MARKER,
            *(part.hex().encode("ascii") for part in state_parts),
            b"11", b"22", b"33", b"3",
        ]
        approved = {
            "approval_sha256": "a" * 64,
            "serializer_sha256": "b" * 64,
            "theorems": [{
                "name": "THM",
                "theorem_sha256": hashlib.sha256(theorem).hexdigest(),
                "hypotheses_sha256": hashlib.sha256(hypotheses).hexdigest(),
                "conclusion_sha256": hashlib.sha256(conclusion).hexdigest(),
                "global_axioms_sha256": hashlib.sha256(axioms).hexdigest(),
                "hypothesis_count": 0,
                "global_axiom_count": 3,
            }],
            "post_state": {
                "kernel_state_sha256": hashlib.sha256(state_parts[0]).hexdigest(),
                "type_constants_sha256": hashlib.sha256(state_parts[1]).hexdigest(),
                "term_constants_sha256": hashlib.sha256(state_parts[2]).hexdigest(),
                "definitions_sha256": hashlib.sha256(state_parts[3]).hexdigest(),
                "global_axioms_sha256": hashlib.sha256(state_parts[4]).hexdigest(),
                "type_constant_count": 11,
                "term_constant_count": 22,
                "definition_count": 33,
                "global_axiom_count": 3,
            },
        }
        with tempfile.NamedTemporaryFile(delete=False) as transcript:
            transcript.write(b"ordinary output\n")
            transcript.write(b"\t".join(theorem_fields) + b"\n")
            transcript.write(b"\t".join(state_fields) + b"\n")
            path = Path(transcript.name)
        try:
            theorems, state, record = SUBJECT._derive_reference_transcript(
                path, ("THM",), approved)
        finally:
            path.unlink()
        self.assertEqual(theorems[0]["theorem"], identity(theorem))
        self.assertEqual(theorems[0]["global_axioms"], identity(axioms))
        self.assertEqual(state["definitions"], identity(state_parts[3]))
        self.assertEqual(record["bytes"], len(b"ordinary output\n") +
                         len(b"\t".join(theorem_fields) + b"\n") +
                         len(b"\t".join(state_fields) + b"\n"))

    def test_reference_wire_sha256_mismatch_is_rejected(self):
        fields = [
            SUBJECT.FINGERPRINT_MARKER, b"THM".hex().encode(),
            b"actual".hex().encode(), b"4:list1:0".hex().encode(),
            b"conclusion".hex().encode(), b"axioms".hex().encode(),
            b"0", b"3",
        ]
        state = [
            SUBJECT.STATE_MARKER,
            *(value.hex().encode() for value in
              (b"state", b"types", b"terms", b"defs", b"axioms")),
            b"1", b"2", b"3", b"3",
        ]
        approved = {
            "theorems": [{
                "name": "THM", "theorem_sha256": "0" * 64,
                "hypotheses_sha256": hashlib.sha256(b"4:list1:0").hexdigest(),
                "conclusion_sha256": hashlib.sha256(b"conclusion").hexdigest(),
                "global_axioms_sha256": hashlib.sha256(b"axioms").hexdigest(),
                "hypothesis_count": 0, "global_axiom_count": 3,
            }],
            "post_state": {
                "kernel_state_sha256": hashlib.sha256(b"state").hexdigest(),
                "type_constants_sha256": hashlib.sha256(b"types").hexdigest(),
                "term_constants_sha256": hashlib.sha256(b"terms").hexdigest(),
                "definitions_sha256": hashlib.sha256(b"defs").hexdigest(),
                "global_axioms_sha256": hashlib.sha256(b"axioms").hexdigest(),
                "type_constant_count": 1, "term_constant_count": 2,
                "definition_count": 3, "global_axiom_count": 3,
            },
        }
        with tempfile.NamedTemporaryFile(delete=False) as transcript:
            transcript.write(b"\t".join(fields) + b"\n")
            transcript.write(b"\t".join(state) + b"\n")
            path = Path(transcript.name)
        try:
            with self.assertRaisesRegex(ValueError, "does not match approval"):
                SUBJECT._derive_reference_transcript(
                    path, ("THM",), approved)
        finally:
            path.unlink()

    def test_compact_match_passes_while_state_mismatch_remains_explicit(self):
        theorem = {
            "name": "THM",
            "theorem": identity(b"theorem"),
            "hypotheses": identity(b"hypotheses"),
            "conclusion": identity(b"conclusion"),
            "global_axioms": identity(b"axioms"),
            "hypothesis_count": 0,
            "global_axiom_count": 3,
        }
        reference_state = {
            "kernel_state": identity(b"reference-state"),
            "type_constants": identity(b"types"),
            "term_constants": identity(b"terms"),
            "definitions": identity(b"defs"),
            "global_axioms": identity(b"axioms"),
            "type_constant_count": 1,
            "term_constant_count": 2,
            "definition_count": 3,
            "global_axiom_count": 3,
        }
        observed_state = dict(reference_state)
        observed_state["kernel_state"] = identity(b"observed-state")
        reference = SUBJECT.ReferenceTarget(
            name="target", theorem_names=("THM",), approved={"approved": True},
            compact_theorems=(theorem,), compact_state=reference_state,
            transcript={"path": "reference"}, success={"path": "success"})
        theorem_line = [
            SUBJECT.COMPACT_FINGERPRINT_MARKER, b"THM".hex().encode(),
            *(theorem[key]["md5"].encode() for key in
              ("theorem", "hypotheses", "conclusion", "global_axioms")),
            *(str(theorem[key]["bytes"]).encode() for key in
              ("theorem", "hypotheses", "conclusion", "global_axioms")),
            b"0", b"3",
        ]
        state_line = [
            SUBJECT.COMPACT_STATE_MARKER,
            *(observed_state[key]["md5"].encode() for key in
              ("kernel_state", "type_constants", "term_constants",
               "definitions", "global_axioms")),
            *(str(observed_state[key]["bytes"]).encode() for key in
              ("kernel_state", "type_constants", "term_constants",
               "definitions", "global_axioms")),
            b"1", b"2", b"3", b"3",
        ]
        with tempfile.NamedTemporaryFile(delete=False) as log:
            log.write(b"\t".join(theorem_line) + b"\n")
            log.write(b"\t".join(state_line) + b"\n")
            path = Path(log.name)
        try:
            result = SUBJECT._parse_compact_log(
                path, ("THM",), reference, LocalFailure)
        finally:
            path.unlink()
        self.assertEqual(result["status"], "theorems_matched")
        self.assertFalse(result["promotion_eligible"])
        self.assertFalse(result["s1_evidence"])
        self.assertEqual(result["post_state"]["status"], "mismatched")
        self.assertFalse(
            result["post_state"]["component_matches"]["kernel_state"])

    def test_compact_theorem_mismatch_fails(self):
        expected = {
            "name": "THM",
            "theorem": identity(b"expected"),
            "hypotheses": identity(b"hypotheses"),
            "conclusion": identity(b"conclusion"),
            "global_axioms": identity(b"axioms"),
            "hypothesis_count": 0,
            "global_axiom_count": 3,
        }
        observed = dict(expected)
        observed["theorem"] = identity(b"observed")
        state = {
            key: identity(key.encode()) for key in
            ("kernel_state", "type_constants", "term_constants",
             "definitions", "global_axioms")
        }
        state.update({"type_constant_count": 1, "term_constant_count": 2,
                      "definition_count": 3, "global_axiom_count": 3})
        reference = SUBJECT.ReferenceTarget(
            "target", ("THM",), {}, (expected,), state, {}, {})
        theorem_line = [
            SUBJECT.COMPACT_FINGERPRINT_MARKER, b"THM".hex().encode(),
            *(observed[key]["md5"].encode() for key in
              ("theorem", "hypotheses", "conclusion", "global_axioms")),
            *(str(observed[key]["bytes"]).encode() for key in
              ("theorem", "hypotheses", "conclusion", "global_axioms")),
            b"0", b"3",
        ]
        state_line = [
            SUBJECT.COMPACT_STATE_MARKER,
            *(state[key]["md5"].encode() for key in
              ("kernel_state", "type_constants", "term_constants",
               "definitions", "global_axioms")),
            *(str(state[key]["bytes"]).encode() for key in
              ("kernel_state", "type_constants", "term_constants",
               "definitions", "global_axioms")),
            b"1", b"2", b"3", b"3",
        ]
        with tempfile.NamedTemporaryFile(delete=False) as log:
            log.write(b"\t".join(theorem_line) + b"\n")
            log.write(b"\t".join(state_line) + b"\n")
            path = Path(log.name)
        try:
            with self.assertRaisesRegex(LocalFailure, "identity mismatch"):
                SUBJECT._parse_compact_log(
                    path, ("THM",), reference, LocalFailure)
        finally:
            path.unlink()

    def test_request_is_compact_and_refuses_suite_markers(self):
        request = SUBJECT._compact_request_source(
            FakeRegression, ("THM", "Module.THM2"))
        self.assertIn("Digest.string", request)
        self.assertIn("CANDLE_COMPATIBILITY_STATE_MD5_V1", request)
        self.assertNotIn("candle_s1_emit_state_fingerprint", request)
        with self.assertRaisesRegex(ValueError, "cannot emit suite evidence"):
            SUBJECT._compact_request_source(
                FakeRegression, ("THM",), "a" * 64, "b" * 64)


if __name__ == "__main__":
    unittest.main()
