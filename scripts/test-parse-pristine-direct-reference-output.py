#!/usr/bin/python3

from __future__ import annotations

import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest


def load_module(name: str, filename: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


subject = load_module(
    "parse_pristine_direct_reference_output",
    "parse-pristine-direct-reference-output.py",
)
fixture_module = load_module(
    "parse_pristine_direct_reference_fixture",
    "test-pristine-direct-reference-protocol.py",
)
protocol = fixture_module.subject


def replace_field(line: str, index: int, value: str) -> str:
    fields = line.split("\t")
    fields[index] = value
    return "\t".join(fields)


def marker_line(marker: str, *fields: object) -> str:
    return "\t".join((marker, *(str(field) for field in fields)))


def event_line(event: dict) -> str:
    return marker_line(
        subject.NATIVE_LOAD_MARKER,
        event["session_nonce"],
        event["index"],
        event["phase"],
        "-" if event["action_index"] is None else event["action_index"],
        event["logical_source"],
        event["basename"],
        event["bytes"],
        event["sha256"],
        event["md5"],
    )


def action_line(record: dict) -> str:
    return marker_line(
        protocol.MARKER_CONTRACT["action_complete"],
        record["session_nonce"],
        record["index"],
        record["selected_source"],
        record["source_sha256"],
    )


def lp_line(record: dict) -> str:
    return marker_line(
        protocol.MARKER_CONTRACT["lp_success"],
        record["session_nonce"],
        record["index"],
        record["action_index"],
        record["input_index"],
        record["class"],
        record["relative"],
        record["bytes"],
        record["sha256"],
        record["successful_deserialization_count"],
    )


def producer_lines(bundle: dict) -> list[str]:
    plan = bundle["plan"]
    transcript = bundle["transcript"]
    closure = bundle["native_execution_closure"]
    bindings = transcript["action_completions"]
    events = closure["loader_events"]
    lines = [
        "OCaml/HOL Light startup output retained verbatim",
        marker_line(
            protocol.MARKER_CONTRACT["session_start"],
            plan["session_nonce"],
            plan["reference_ordinal"],
            plan["boundary_id"],
        ),
    ]
    initial = bindings["initial_ledger_count"]
    lines.extend(event_line(event) for event in events[:initial])
    for record in bindings["records"]:
        start = record["ledger_start_index"]
        end = record["ledger_end_index"]
        lines.extend(event_line(event) for event in events[start:end])
        if record["index"] == protocol.LP_CONSUMER_ACTION_INDEX:
            lines.extend(lp_line(item) for item in transcript["lp_successes"]["records"])
        lines.append(action_line(record))
    lines.extend(event_line(event) for event in events[bindings["final_ledger_count"]:])
    lines.append(marker_line(
        protocol.MARKER_CONTRACT["session_complete"],
        plan["session_nonce"],
        plan["boundary_id"],
        protocol.FINAL_ACTION_COUNT,
        39,
        len(events),
    ))
    return lines


def encode(lines: list[str]) -> bytes:
    return ("\n".join(lines) + "\n").encode()


def marker_indices(lines: list[str], marker: str) -> list[int]:
    return [index for index, line in enumerate(lines)
            if line.startswith(marker + "\t")]


class PristineOutputParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = fixture_module.bundle_fixture()
        cls.plan = cls.bundle["plan"]
        cls.request = cls.bundle["request"]
        cls.lines = producer_lines(cls.bundle)
        cls.stdout = encode(cls.lines)
        cls.process_result = {"exit_code": 0, "timed_out": False}

    def parse(self, lines: list[str] | None = None, **overrides):
        arguments = {
            "stdout": self.stdout if lines is None else encode(lines),
            "stderr": b"",
            "process_result": copy.deepcopy(self.process_result),
            "plan": copy.deepcopy(self.plan),
            "request": copy.deepcopy(self.request),
        }
        arguments.update(overrides)
        return subject.rederive_raw_source_observations(**arguments)

    def assert_rejects(self, lines: list[str], pattern: str | None = None) -> None:
        context = self.assertRaises(subject.OutputProtocolError)
        if pattern is not None:
            context = self.assertRaisesRegex(subject.OutputProtocolError, pattern)
        with context:
            self.parse(lines)

    def test_producer_shaped_bytes_rederive_only_raw_source_evidence(self) -> None:
        result = self.parse()
        stdout_record = {
            "bytes": len(self.stdout),
            "sha256": hashlib.sha256(self.stdout).hexdigest(),
        }
        self.assertEqual(result["stdout"], stdout_record)
        self.assertEqual(result["stderr"], {
            "bytes": 0, "sha256": hashlib.sha256(b"").hexdigest(),
        })
        transcript = result["transcript"]
        closure = result["native_execution_closure"]
        self.assertIs(
            protocol.validate_raw_transcript(
                transcript, self.plan, self.request,
            ), transcript,
        )
        self.assertIs(
            protocol.validate_native_execution_closure(
                closure, self.plan, self.request, transcript,
            ), closure,
        )
        self.assertEqual(
            transcript["action_completions"]["record_count"], 297,
        )
        self.assertEqual(transcript["lp_successes"]["record_count"], 39)
        self.assertEqual(closure["loader_event_count"], 302)
        self.assertEqual(closure["loader_ledger_artifact"], stdout_record)
        self.assertEqual(closure["lp_success_artifact"], stdout_record)
        self.assertIsNone(result["semantic_projection"])
        self.assertIsNone(result["cross_runtime_coverage"])
        for field in (
            "candidate_included", "approval_included", "promotion_allowed",
            "pft_used", "s2_eligible", "s3_eligible", "s2_s3_evidence",
        ):
            self.assertIs(result[field], False)
        self.assertEqual(result["authentication_status"], "not-authenticated")

    def test_ordinary_bytes_are_retained_but_cannot_follow_completion(self) -> None:
        changed = copy.deepcopy(self.lines)
        changed.insert(2, "ordinary proof diagnostic")
        result = self.parse(changed)
        changed_bytes = encode(changed)
        self.assertEqual(
            result["stdout"]["sha256"], hashlib.sha256(changed_bytes).hexdigest(),
        )
        self.assertNotEqual(result["stdout"], self.parse()["stdout"])
        trailing = copy.deepcopy(self.lines)
        trailing.append("ordinary trailing output")
        self.assert_rejects(trailing, "nonterminal session-complete")

    def test_process_result_bytes_and_stderr_are_exact(self) -> None:
        cases = (
            {"stdout": bytearray(self.stdout)},
            {"stdout": self.stdout[:-1]},
            {"stdout": self.stdout.replace(b"\n", b"\r\n", 1)},
            {"stdout": self.stdout[:-2] + b"\xff\n"},
            {"stderr": b"warning\n"},
            {"process_result": {"exit_code": True, "timed_out": False}},
            {"process_result": {"exit_code": 0.0, "timed_out": False}},
            {"process_result": {"exit_code": 0, "timed_out": 0}},
            {"process_result": {"exit_code": 0, "timed_out": False, "x": 1}},
        )
        for case in cases:
            with self.subTest(case=case), self.assertRaises(
                subject.OutputProtocolError,
            ):
                self.parse(**case)

    def test_action_markers_reject_missing_duplicate_reorder_and_plan_tamper(self) -> None:
        indices = marker_indices(
            self.lines, protocol.MARKER_CONTRACT["action_complete"],
        )
        mutations: list[list[str]] = []
        missing = copy.deepcopy(self.lines)
        missing.pop(indices[0])
        mutations.append(missing)
        duplicate = copy.deepcopy(self.lines)
        duplicate.insert(indices[0] + 1, duplicate[indices[0]])
        mutations.append(duplicate)
        reordered = copy.deepcopy(self.lines)
        reordered[indices[0]], reordered[indices[1]] = (
            reordered[indices[1]], reordered[indices[0]],
        )
        mutations.append(reordered)
        noncanonical = copy.deepcopy(self.lines)
        noncanonical[indices[0]] = replace_field(
            noncanonical[indices[0]], 2, "00",
        )
        mutations.append(noncanonical)
        forged = copy.deepcopy(self.lines)
        forged[indices[0]] = replace_field(forged[indices[0]], 4, "0" * 64)
        mutations.append(forged)
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_rejects(mutation)

    def test_lp_markers_reject_missing_duplicate_reorder_and_wrong_consumer(self) -> None:
        indices = marker_indices(self.lines, protocol.MARKER_CONTRACT["lp_success"])
        mutations: list[list[str]] = []
        missing = copy.deepcopy(self.lines)
        missing.pop(indices[0])
        mutations.append(missing)
        duplicate = copy.deepcopy(self.lines)
        duplicate.insert(indices[0] + 1, duplicate[indices[0]])
        mutations.append(duplicate)
        reordered = copy.deepcopy(self.lines)
        reordered[indices[0]], reordered[indices[1]] = (
            reordered[indices[1]], reordered[indices[0]],
        )
        mutations.append(reordered)
        wrong_action = copy.deepcopy(self.lines)
        wrong_action[indices[0]] = replace_field(
            wrong_action[indices[0]], 3, str(protocol.LP_VERIFY_ACTION_INDEX),
        )
        mutations.append(wrong_action)
        bool_like_count = copy.deepcopy(self.lines)
        bool_like_count[indices[0]] = replace_field(
            bool_like_count[indices[0]], 9, "true",
        )
        mutations.append(bool_like_count)
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_rejects(mutation)

    def test_native_loader_rejects_missing_duplicate_reorder_and_selected_tamper(self) -> None:
        indices = marker_indices(self.lines, subject.NATIVE_LOAD_MARKER)
        action_event = next(
            index for index in indices
            if self.lines[index].split("\t")[3] == "action"
        )
        mutations: list[list[str]] = []
        missing = copy.deepcopy(self.lines)
        missing.pop(action_event)
        mutations.append(missing)
        duplicate = copy.deepcopy(self.lines)
        duplicate.insert(indices[0] + 1, duplicate[indices[0]])
        mutations.append(duplicate)
        reordered = copy.deepcopy(self.lines)
        reordered[indices[0]], reordered[indices[1]] = (
            reordered[indices[1]], reordered[indices[0]],
        )
        mutations.append(reordered)
        noncanonical = copy.deepcopy(self.lines)
        noncanonical[indices[0]] = replace_field(
            noncanonical[indices[0]], 2, "00",
        )
        mutations.append(noncanonical)
        tampered = copy.deepcopy(self.lines)
        tampered[action_event] = replace_field(
            tampered[action_event], 8, "0" * 64,
        )
        mutations.append(tampered)
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_rejects(mutation)

    def test_already_loaded_outcome_is_rederived_not_claimed(self) -> None:
        lines = copy.deepcopy(self.lines)
        action_event_index = next(
            index for index in marker_indices(lines, subject.NATIVE_LOAD_MARKER)
            if lines[index].split("\t")[3:5] == ["action", "0"]
        )
        lines[action_event_index] = replace_field(
            replace_field(lines[action_event_index], 3, "bootstrap"), 4, "-",
        )
        result = self.parse(lines)
        first = result["transcript"]["action_completions"]["records"][0]
        self.assertEqual(first["loader_outcome"], "already-loaded")
        self.assertLess(first["selected_ledger_index"], first["ledger_start_index"])
        self.assertEqual(first["ledger_start_index"], 4)
        self.assertEqual(first["ledger_end_index"], 4)

    def test_mixed_nonce_and_session_boundary_attacks_reject(self) -> None:
        action_index = marker_indices(
            self.lines, protocol.MARKER_CONTRACT["action_complete"],
        )[12]
        mixed = copy.deepcopy(self.lines)
        mixed[action_index] = replace_field(mixed[action_index], 1, "2" * 64)
        self.assert_rejects(mixed, "mixed nonce")

        for marker in (
            protocol.MARKER_CONTRACT["session_start"],
            protocol.MARKER_CONTRACT["session_complete"],
        ):
            indices = marker_indices(self.lines, marker)
            missing = copy.deepcopy(self.lines)
            missing.pop(indices[0])
            self.assert_rejects(missing)
            duplicate = copy.deepcopy(self.lines)
            duplicate.insert(indices[0] + 1, duplicate[indices[0]])
            self.assert_rejects(duplicate)

    def test_unknown_semantic_and_success_like_lines_fail_closed(self) -> None:
        complete_index = marker_indices(
            self.lines, protocol.MARKER_CONTRACT["session_complete"],
        )[0]
        hostile_lines = (
            "CANDLE_PRISTINE_DIRECT_SEMANTIC_V1\t" + self.plan["session_nonce"],
            "CANDLE_FINGERPRINT_V2\t00",
            "CANDLE_UNKNOWN_SUCCESS_V99\t1",
            "  SUCCESS: forged reference",
            "ERROR: caught exception",
        )
        for line in hostile_lines:
            forged = copy.deepcopy(self.lines)
            forged.insert(complete_index, line)
            with self.subTest(line=line):
                self.assert_rejects(forged, "stdout line")

    def test_complete_counts_and_marker_shape_are_exact(self) -> None:
        complete = marker_indices(
            self.lines, protocol.MARKER_CONTRACT["session_complete"],
        )[0]
        mutations: list[list[str]] = []
        for field, value in ((3, "0297"), (4, "38"), (5, "303")):
            forged = copy.deepcopy(self.lines)
            forged[complete] = replace_field(forged[complete], field, value)
            mutations.append(forged)
        extra = copy.deepcopy(self.lines)
        extra[complete] += "\textra"
        mutations.append(extra)
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_rejects(mutation)


if __name__ == "__main__":
    unittest.main()
