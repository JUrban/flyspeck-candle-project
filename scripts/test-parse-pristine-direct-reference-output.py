#!/usr/bin/python3

from __future__ import annotations

import copy
import hashlib
import importlib._bootstrap_external as bootstrap_external
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


def load_module(name: str, filename: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


loader_module = load_module(
    "load_pristine_direct_reference_output",
    "load-pristine-direct-reference-output.py",
)
subject = None
fixture_module = load_module(
    "parse_pristine_direct_reference_fixture",
    "test-pristine-direct-reference-protocol.py",
)
protocol = fixture_module.subject
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


def install_fixed_sources(root: Path) -> Path:
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for relative in (
        protocol.PROTOCOL_PATH, protocol.OUTPUT_PARSER_PATH,
        protocol.DIRECT_PROTOCOL_PATH,
    ):
        source = PROJECT_ROOT / relative
        (root / relative).write_bytes(source.read_bytes())
    return scripts


def replace_field(line: str, index: int, value: str) -> str:
    fields = line.split("\t")
    fields[index] = value
    return "\t".join(fields)


def marker_line(marker: str, *fields: object) -> str:
    return "\t".join((marker, *(str(field) for field in fields)))


def event_line(event: dict) -> str:
    return marker_line(
        protocol.MARKER_CONTRACT["native_load"],
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


def framed(value: bytes) -> bytes:
    return str(len(value)).encode() + b":" + value


def node(tag: bytes, children: list[bytes]) -> bytes:
    return (
        framed(tag) + framed(str(len(children)).encode()) +
        b"".join(framed(child) for child in children)
    )


def semantic_lines(plan: dict) -> list[str]:
    marker = plan_marker = protocol.MARKER_CONTRACT["semantic_observation"]
    nonce = plan["session_nonce"]
    hypotheses = node(b"list", [])
    global_axioms = node(b"list", [b"axiom-0", b"axiom-1", b"axiom-2"])
    lines = []
    for index, name in enumerate(subject.EXPECTED_FINAL_THEOREM_NAMES):
        conclusion = f"conclusion-{index}".encode()
        theorem = node(b"theorem", [hypotheses, conclusion])
        lines.append(marker_line(
            plan_marker, "THEOREM", nonce, index, name.encode().hex(),
            theorem.hex(), hypotheses.hex(), conclusion.hex(),
            global_axioms.hex(), 0, 3,
        ))
    type_constants = node(b"list", [b"type-0", b"type-1"])
    term_constants = node(b"list", [b"term-0"])
    definitions = node(b"list", [b"definition-0"])
    kernel_state = node(
        b"kernel-state",
        [type_constants, term_constants, definitions, global_axioms],
    )
    lines.append(marker_line(
        marker, "POST_STATE", nonce, kernel_state.hex(), type_constants.hex(),
        term_constants.hex(), definitions.hex(), global_axioms.hex(), 2, 1, 1, 3,
    ))
    for index, name in enumerate(subject.EXPECTED_FINAL_THEOREM_NAMES):
        lines.append(marker_line(
            marker, "DEPENDENCY", nonce, index, name.encode().hex(),
            f"{index + 1:032x}",
        ))
    lines.append(marker_line(
        marker, "COMPLETE", nonce, plan["boundary_id"], 4, 4,
    ))
    return lines


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
    lines.extend(semantic_lines(plan))
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
        global subject
        cls.bundle = fixture_module.bundle_fixture()
        subject = loader_module.load_trusted_output_parser(
            PROJECT_ROOT, cls.bundle["plan"],
        )
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

    def decode_semantic(self, lines: list[str], **overrides):
        arguments = {
            "data": encode(lines),
            "plan": copy.deepcopy(self.plan),
            "request": copy.deepcopy(self.request),
            "transcript": copy.deepcopy(self.bundle["transcript"]),
            "native_closure": copy.deepcopy(
                self.bundle["native_execution_closure"]
            ),
        }
        arguments.update(overrides)
        return subject.decode_semantic_v3_bytes(**arguments)

    def assert_rejects(self, lines: list[str], pattern: str | None = None) -> None:
        context = self.assertRaises(subject.OutputProtocolError)
        if pattern is not None:
            context = self.assertRaisesRegex(subject.OutputProtocolError, pattern)
        with context:
            self.parse(lines)

    def test_producer_shaped_bytes_rederive_complete_unapproved_source_evidence(self) -> None:
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
        for artifact in (result, transcript, closure):
            self.assertEqual(artifact["schema"], protocol.RAW_PROTOCOL_SCHEMA)
            self.assertTrue(artifact["kind"].endswith("-v3"))
        self.assertEqual(result["kind"], protocol.SOURCE_REDERIVATION_KIND)
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
        direct = protocol._direct_protocol()
        self.assertIs(
            direct.validate_semantic_projection(result["semantic_projection"]),
            result["semantic_projection"],
        )
        self.assertIs(
            protocol.validate_semantic_completion_observation(
                result["semantic_completion_observation"], self.plan,
                self.request, transcript, result["semantic_projection"],
            ), result["semantic_completion_observation"],
        )
        canonical = protocol.canonical_json_bytes(result)
        self.assertEqual(
            protocol.validate_canonical_source_rederivation_bytes(
                canonical, self.plan, self.request,
            ), result,
        )
        self.assertIsNone(result["cross_runtime_coverage"])
        self.assertEqual(
            result["semantic_status"], "complete-observed-unapproved",
        )
        self.assertEqual(
            result["coverage_status"],
            "not-derived-requires-authenticated-inventory-and-generated-inputs",
        )
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

    def test_final_source_rederivation_validator_rejects_nested_splices_and_types(self) -> None:
        result = self.parse()

        def splice_projection_serializer(item: dict) -> None:
            item["semantic_projection"]["serializer"]["sha256"] = "0" * 64
            item["semantic_completion_observation"]["semantic_projection"] = (
                protocol.content_record(item["semantic_projection"])
            )

        mutations = (
            ("schema bool", lambda item: item.update(schema=True)),
            ("extra top-level", lambda item: item.update(extra=False)),
            ("diagnostic relabel", lambda item: item.update(
                kind=protocol.INCOMPLETE_SOURCE_REDERIVATION_KIND,
            )),
            ("coverage object", lambda item: item.update(
                cross_runtime_coverage={},
            )),
            ("semantic status", lambda item: item.update(
                semantic_status="observed",
            )),
            ("candidate", lambda item: item.update(candidate_included=True)),
            ("stdout bool bytes", lambda item: item["stdout"].update(bytes=True)),
            ("exit bool", lambda item: item["process_result"].update(
                exit_code=False,
            )),
            ("transcript schema bool", lambda item: item["transcript"].update(
                schema=True,
            )),
            ("native count float", lambda item: item[
                "native_execution_closure"
            ].update(loader_event_count=302.0)),
            ("semantic theorem count bool", lambda item: item[
                "semantic_projection"
            ]["theorems"][0].update(global_axiom_count=True)),
            ("completion theorem count bool", lambda item: item[
                "semantic_completion_observation"
            ].update(theorem_count=True)),
            ("completion extra", lambda item: item[
                "semantic_completion_observation"
            ].update(extra=False)),
            ("completion projection splice", lambda item: item[
                "semantic_completion_observation"
            ]["semantic_projection"].update(sha256="0" * 64)),
            ("projection/native serializer splice", splice_projection_serializer),
        )
        for label, mutate in mutations:
            forged = copy.deepcopy(result)
            mutate(forged)
            with self.subTest(label=label), self.assertRaises(
                protocol.ProtocolError,
            ):
                protocol.validate_source_rederivation(
                    forged, self.plan, self.request,
                )

        forged = copy.deepcopy(result)
        forged["stderr"]["sha256"] = "0" * 64
        forged["transcript"]["stderr"]["sha256"] = "0" * 64
        transcript_record = protocol.content_record(forged["transcript"])
        forged["native_execution_closure"]["transcript"] = transcript_record
        forged["semantic_completion_observation"]["transcript"] = (
            transcript_record
        )
        with self.assertRaisesRegex(protocol.ProtocolError, "stderr"):
            protocol.validate_source_rederivation(
                forged, self.plan, self.request,
            )
        with self.assertRaisesRegex(protocol.ProtocolError, "stderr"):
            protocol.validate_canonical_source_rederivation_bytes(
                protocol.canonical_json_bytes(forged), self.plan, self.request,
            )

        canonical = protocol.canonical_json_bytes(result)
        with self.assertRaisesRegex(protocol.ProtocolError, "immutable bytes"):
            protocol.validate_canonical_source_rederivation_bytes(
                bytearray(canonical), self.plan, self.request,
            )
        with self.assertRaisesRegex(protocol.ProtocolError, "not canonical"):
            protocol.validate_canonical_source_rederivation_bytes(
                protocol.canonical_value_bytes(result), self.plan, self.request,
            )
        with self.assertRaisesRegex(protocol.ProtocolError, "duplicate JSON key"):
            protocol.validate_canonical_source_rederivation_bytes(
                b'{"schema":3,"schema":3}\n', self.plan, self.request,
            )

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

    def test_stdout_uses_only_the_exact_ascii_tab_lf_wire_alphabet(self) -> None:
        complete_index = marker_indices(
            self.lines, protocol.MARKER_CONTRACT["session_complete"],
        )[0]
        hostile_characters = (
            "\x7f",       # DEL
            "\u0085",     # C1 next-line
            "\ufeff",     # BOM / format control
            "\u200d",     # zero-width joiner / format control
            "\u202e",     # bidi override / format control
            "\u2028",     # Unicode line separator
            "\u2029",     # Unicode paragraph separator
            "\u00e9",     # printable non-ASCII is outside the v3 alphabet
        )
        for character in hostile_characters:
            forged = copy.deepcopy(self.lines)
            forged.insert(complete_index, "ordinary" + character + "output")
            with self.subTest(codepoint=ord(character)), self.assertRaisesRegex(
                subject.OutputProtocolError, "ASCII wire alphabet",
            ):
                self.parse(forged)

        start_index = marker_indices(
            self.lines, protocol.MARKER_CONTRACT["session_start"],
        )[0]
        bom_marker = copy.deepcopy(self.lines)
        bom_marker[start_index] = "\ufeff" + bom_marker[start_index]
        with self.assertRaisesRegex(
            subject.OutputProtocolError, "ASCII wire alphabet",
        ):
            self.parse(bom_marker)

    def test_every_stdout_line_rejects_pft_tokens_before_classification(self) -> None:
        complete_index = marker_indices(
            self.lines, protocol.MARKER_CONTRACT["session_complete"],
        )[0]
        hostile_lines = (
            "PFT",
            "PFT_USED\ttrue",
            "PFT_SUCCESS\ttrue",
            "pFt",
            "ordinary /PfT/result",
            "ordinary.pFt-result",
            "ordinary PFT success claim",
        )
        for line in hostile_lines:
            forged = copy.deepcopy(self.lines)
            forged.insert(complete_index, line)
            with self.subTest(line=line), self.assertRaisesRegex(
                subject.OutputProtocolError, "PFT namespace",
            ):
                self.parse(forged)

        benign = copy.deepcopy(self.lines)
        semantic_index = marker_indices(
            benign, protocol.MARKER_CONTRACT["semantic_observation"],
        )[0]
        benign.insert(semantic_index, "ordinary notpft diagnostic")
        self.assertEqual(
            self.parse(benign)["authentication_status"], "not-authenticated",
        )

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
        indices = marker_indices(
            self.lines, protocol.MARKER_CONTRACT["native_load"],
        )
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
            index for index in marker_indices(
                lines, protocol.MARKER_CONTRACT["native_load"],
            )
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
        semantic_index = marker_indices(
            self.lines, protocol.MARKER_CONTRACT["semantic_observation"],
        )[0]
        hostile_lines = (
            (
                protocol.MARKER_CONTRACT["semantic_observation"] +
                "\t" + self.plan["session_nonce"],
                "semantic session",
            ),
            (
                "CANDLE_PRISTINE_DIRECT_SEMANTIC_V1\t" +
                self.plan["session_nonce"], "stdout line",
            ),
            ("CANDLE_FINGERPRINT_V2\t00", "stdout line"),
            ("CANDLE_UNKNOWN_SUCCESS_V99\t1", "stdout line"),
            ("  SUCCESS: forged reference", "stdout line"),
            ("ERROR: caught exception", "stdout line"),
        )
        for line, pattern in hostile_lines:
            forged = copy.deepcopy(self.lines)
            forged.insert(semantic_index, line)
            with self.subTest(line=line):
                self.assert_rejects(forged, pattern)

    def test_pure_semantic_v3_decoder_derives_exact_common_projection(self) -> None:
        lines = semantic_lines(self.plan)
        projection = self.decode_semantic(lines)
        direct = protocol._direct_protocol()
        self.assertIs(direct.validate_semantic_projection(projection), projection)
        self.assertEqual(
            [record["name"] for record in projection["theorems"]],
            list(subject.EXPECTED_FINAL_THEOREM_NAMES),
        )
        self.assertEqual(
            projection["dependency_history"],
            [{
                "index": index,
                "name": name,
                "full_digest_md5": f"{index + 1:032x}",
            } for index, name in enumerate(subject.EXPECTED_FINAL_THEOREM_NAMES)],
        )
        final_serializer = self.bundle["native_execution_closure"]["loader_events"][-1]
        self.assertEqual(projection["serializer"], {
            "path": final_serializer["logical_source"].partition(":")[2],
            "sha256": final_serializer["sha256"],
        })
        hypotheses = node(b"list", [])
        self.assertEqual(
            projection["theorems"][0]["hypotheses_sha256"],
            hashlib.sha256(hypotheses).hexdigest(),
        )
        self.assertNotIn("session_nonce", projection)
        self.assertFalse(any(
            "candidate" in name or "approval" in name
            for name in projection
        ))

    def test_pure_decoder_rebinds_every_plan_to_trusted_activation(self) -> None:
        lines = semantic_lines(self.plan)
        mutations = (
            (
                "parser SHA",
                lambda plan: plan["authority"]["producer"]["output_parser"].update(
                    sha256="0" * 64,
                ),
                "output parser versus plan authority",
            ),
            (
                "protocol SHA",
                lambda plan: plan["authority"]["producer"]["protocol"].update(
                    sha256="0" * 64,
                ),
                "pristine protocol versus plan authority",
            ),
            (
                "direct protocol SHA",
                lambda plan: plan["authority"]["producer"]
                ["direct_release_protocol"].update(sha256="0" * 64),
                "direct-release protocol versus plan authority",
            ),
            (
                "project root",
                lambda plan: plan["authority"]["repositories"]["project"].update(
                    path="/project/alternate-project-root",
                ),
                "project root differs",
            ),
        )
        for label, mutate, message in mutations:
            plan = copy.deepcopy(self.plan)
            mutate(plan)
            request = fixture_module.make_request(plan)
            with self.subTest(label=label), self.assertRaisesRegex(
                subject.OutputProtocolError, message,
            ):
                self.decode_semantic(lines, plan=plan, request=request)

    def test_pure_decoder_requires_valid_transcript_and_final_serializer_event(self) -> None:
        lines = semantic_lines(self.plan)
        transcript = copy.deepcopy(self.bundle["transcript"])
        transcript["stdout"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(
            subject.OutputProtocolError, "semantic closure",
        ):
            self.decode_semantic(lines, transcript=transcript)

        closure = copy.deepcopy(self.bundle["native_execution_closure"])
        closure["loader_events"][-1]["sha256"] = "0" * 64
        closure["ordered_loader_event_sha256"] = protocol.canonical_sha256(
            closure["loader_events"]
        )
        with self.assertRaisesRegex(
            subject.OutputProtocolError, "semantic closure",
        ):
            self.decode_semantic(lines, native_closure=closure)

    def test_pure_decoder_rejects_order_nonce_version_and_shape_attacks(self) -> None:
        baseline = semantic_lines(self.plan)
        mutations: list[tuple[str, list[str]]] = []
        missing = copy.deepcopy(baseline)
        missing.pop(0)
        mutations.append(("missing", missing))
        duplicate = copy.deepcopy(baseline)
        duplicate.insert(1, duplicate[0])
        mutations.append(("duplicate", duplicate))
        reordered = copy.deepcopy(baseline)
        reordered[0], reordered[1] = reordered[1], reordered[0]
        mutations.append(("reordered", reordered))
        mixed_nonce = copy.deepcopy(baseline)
        mixed_nonce[4] = replace_field(mixed_nonce[4], 2, "2" * 64)
        mutations.append(("nonce", mixed_nonce))
        old_marker = copy.deepcopy(baseline)
        old_marker[0] = old_marker[0].replace(
            protocol.MARKER_CONTRACT["semantic_observation"],
            "CANDLE_PRISTINE_DIRECT_SEMANTIC_V2", 1,
        )
        mutations.append(("v2", old_marker))
        extra = copy.deepcopy(baseline)
        extra[9] += "\textra"
        mutations.append(("extra", extra))
        unknown = copy.deepcopy(baseline)
        unknown[5] = replace_field(unknown[5], 1, "UNKNOWN")
        mutations.append(("unknown", unknown))
        for label, lines in mutations:
            with self.subTest(label=label), self.assertRaises(
                subject.OutputProtocolError,
            ):
                self.decode_semantic(lines)

    def test_pure_decoder_rejects_hex_count_and_composite_splices(self) -> None:
        baseline = semantic_lines(self.plan)
        mutations: list[tuple[str, list[str]]] = []
        uppercase = copy.deepcopy(baseline)
        uppercase[0] = replace_field(uppercase[0], 4, uppercase[0].split("\t")[4].upper())
        mutations.append(("uppercase name hex", uppercase))
        odd = copy.deepcopy(baseline)
        odd[0] = replace_field(odd[0], 6, "0")
        mutations.append(("odd serialized hex", odd))
        padded = copy.deepcopy(baseline)
        padded[0] = replace_field(padded[0], 9, "00")
        mutations.append(("padded count", padded))
        nonempty_hypotheses = copy.deepcopy(baseline)
        changed_hypotheses = node(b"list", [b"assumption"])
        nonempty_hypotheses[0] = replace_field(
            replace_field(nonempty_hypotheses[0], 6, changed_hypotheses.hex()),
            9, "1",
        )
        mutations.append(("nonempty hypotheses", nonempty_hypotheses))
        theorem_splice = copy.deepcopy(baseline)
        theorem_splice[0] = replace_field(
            theorem_splice[0], 7, b"different-conclusion".hex(),
        )
        mutations.append(("theorem composite splice", theorem_splice))
        axiom_splice = copy.deepcopy(baseline)
        axiom_splice[1] = replace_field(
            axiom_splice[1], 8,
            node(b"list", [b"other-0", b"other-1", b"other-2"]).hex(),
        )
        mutations.append(("axiom splice", axiom_splice))
        uppercase_md5 = copy.deepcopy(baseline)
        uppercase_md5[5] = replace_field(uppercase_md5[5], 5, "A" * 32)
        mutations.append(("uppercase dependency", uppercase_md5))
        for label, lines in mutations:
            with self.subTest(label=label), self.assertRaises(
                subject.OutputProtocolError,
            ):
                self.decode_semantic(lines)

    def test_nine_digit_child_count_rejects_before_child_iteration(self) -> None:
        lines = semantic_lines(self.plan)
        # tag frame + a nine-digit canonical child-count frame, with no child
        # bytes.  100,000,000 is under the global frame cap but impossible for
        # the remaining zero bytes; the pre-loop remaining//2 guard must fire.
        hostile_list = b"4:list9:100000000"
        lines[0] = replace_field(lines[0], 6, hostile_list.hex())
        with self.assertRaisesRegex(
            subject.OutputProtocolError,
            "child count exceeds remaining framed bytes",
        ):
            self.decode_semantic(lines)

    def test_oversize_frame_token_rejects_before_integer_conversion(self) -> None:
        with mock.patch("builtins.int", side_effect=AssertionError(
            "integer conversion must not run",
        )):
            with self.assertRaisesRegex(
                subject.OutputProtocolError, "oversize hostile framed value",
            ):
                subject._framed_decimal(
                    b"536870913", "hostile framed value",
                )

        with mock.patch.object(
            subject, "_extract_bounded_payload",
            side_effect=AssertionError("payload extraction must not run"),
        ):
            with self.assertRaisesRegex(
                subject.OutputProtocolError, "frame exceeds remaining bytes",
            ):
                subject._read_frame(b"536870912:x", 0, "hostile payload")

        with mock.patch("builtins.int", side_effect=AssertionError(
            "integer conversion must not run before remaining-byte rejection",
        )):
            with self.assertRaisesRegex(
                subject.OutputProtocolError, "frame exceeds remaining bytes",
            ):
                subject._read_frame(b"2:x", 0, "small missing payload")

    def test_well_formed_dependency_substitution_is_only_raw_projection_drift(self) -> None:
        baseline = semantic_lines(self.plan)
        original = self.decode_semantic(baseline)
        substituted = copy.deepcopy(baseline)
        substituted[5] = replace_field(substituted[5], 5, "e" * 32)
        changed = self.decode_semantic(substituted)
        self.assertNotEqual(changed, original)
        self.assertEqual(
            changed["dependency_history"][0]["full_digest_md5"], "e" * 32,
        )
        self.assertNotIn("approved_reference_present", changed)

    def test_integrated_semantic_session_rejects_boundary_and_interruption_attacks(self) -> None:
        marker = protocol.MARKER_CONTRACT["semantic_observation"]
        indices = marker_indices(self.lines, marker)
        self.assertEqual(len(indices), 10)
        mutations: list[tuple[str, list[str], str]] = []

        missing = copy.deepcopy(self.lines)
        missing.pop(indices[0])
        mutations.append(("missing", missing, "semantic session"))

        duplicate = copy.deepcopy(self.lines)
        duplicate.insert(indices[-1] + 1, duplicate[indices[-1]])
        mutations.append(("duplicate", duplicate, "more than ten"))

        reordered = copy.deepcopy(self.lines)
        reordered[indices[0]], reordered[indices[1]] = (
            reordered[indices[1]], reordered[indices[0]],
        )
        mutations.append(("reordered", reordered, "theorem order"))

        ordinary = copy.deepcopy(self.lines)
        ordinary.insert(indices[3] + 1, "ordinary semantic interruption")
        mutations.append(("ordinary interruption", ordinary, "ordinary stdout interrupts"))

        native = copy.deepcopy(self.lines)
        native.insert(indices[3] + 1, next(
            line for line in native
            if line.startswith(protocol.MARKER_CONTRACT["native_load"] + "\t")
        ))
        mutations.append(("marker interruption", native, "protocol marker interrupts"))

        for label, marker_name in (
            ("action interruption", "action_complete"),
            ("LP interruption", "lp_success"),
        ):
            interrupted = copy.deepcopy(self.lines)
            interrupted.insert(indices[3] + 1, next(
                line for line in interrupted
                if line.startswith(
                    protocol.MARKER_CONTRACT[marker_name] + "\t"
                )
            ))
            mutations.append((label, interrupted, "protocol marker interrupts"))

        early = copy.deepcopy(self.lines)
        block = early[indices[0]:indices[-1] + 1]
        del early[indices[0]:indices[-1] + 1]
        post_indices = [
            index for index, line in enumerate(early)
            if line.startswith(protocol.MARKER_CONTRACT["native_load"] + "\t") and
            line.split("\t")[3] == "post-action"
        ]
        early[post_indices[-1]:post_indices[-1]] = block
        mutations.append(("before serializer", early, "exact final-target/serializer"))

        for label, lines, pattern in mutations:
            with self.subTest(label=label):
                self.assert_rejects(lines, pattern)

    def test_native_marker_is_request_bound_and_v2_wire_rejects(self) -> None:
        native = protocol.MARKER_CONTRACT["native_load"]
        self.assertEqual(
            self.request["marker_contract"]["native_load"], native,
        )
        forged = [
                line.replace(
                native, "CANDLE_PRISTINE_DIRECT_NATIVE_LOAD_V2", 1,
            ) if line.startswith(native + "\t") else line
            for line in self.lines
        ]
        self.assert_rejects(forged, "unsupported success-like")

    def test_executing_parser_bytes_must_match_plan_authority(self) -> None:
        expected = fixture_module.named_file(protocol.OUTPUT_PARSER_PATH)
        self.assertEqual(
            self.plan["authority"]["producer"]["output_parser"], expected,
        )
        plan = copy.deepcopy(self.plan)
        plan["authority"]["producer"]["output_parser"]["sha256"] = "0" * 64
        request = fixture_module.make_request(plan)
        with self.assertRaisesRegex(
            subject.OutputProtocolError,
            "output parser versus plan authority mismatch",
        ):
            self.parse(plan=plan, request=request)

        plan = copy.deepcopy(self.plan)
        plan["authority"]["producer"]["protocol"]["sha256"] = "0" * 64
        request = fixture_module.make_request(plan)
        with self.assertRaisesRegex(
            subject.OutputProtocolError,
            "pristine protocol versus plan authority mismatch",
        ):
            self.parse(plan=plan, request=request)

        plan = copy.deepcopy(self.plan)
        plan["authority"]["producer"]["direct_release_protocol"][
            "sha256"
        ] = "0" * 64
        request = fixture_module.make_request(plan)
        with self.assertRaisesRegex(
            subject.OutputProtocolError,
            "direct-release protocol versus plan authority mismatch",
        ):
            self.parse(plan=plan, request=request)

    def test_trusted_loader_binds_fixed_sources_and_ignores_bytecode(self) -> None:
        forged = copy.deepcopy(self.plan)
        forged["authority"]["producer"]["protocol"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(
            loader_module.LoaderError, "protocol source differs",
        ):
            loader_module.load_trusted_output_parser(PROJECT_ROOT, forged)

        untrusted = load_module(
            "untrusted_pristine_output_parser",
            "parse-pristine-direct-reference-output.py",
        )
        with self.assertRaisesRegex(
            untrusted.OutputProtocolError, "trusted fixed-path.*required",
        ):
            untrusted._protocol()

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            scripts = root / "scripts"
            scripts.mkdir()
            for relative in (
                protocol.PROTOCOL_PATH, protocol.OUTPUT_PARSER_PATH,
                protocol.DIRECT_PROTOCOL_PATH,
            ):
                source = PROJECT_ROOT / relative
                (root / relative).write_bytes(source.read_bytes())
            cache = scripts / "__pycache__"
            cache.mkdir()
            parser_cache = Path(importlib.util.cache_from_source(
                str(root / protocol.OUTPUT_PARSER_PATH)
            ))
            parser_cache.write_bytes(
                b"hostile bytecode must not execute"
            )
            direct_source = root / protocol.DIRECT_PROTOCOL_PATH
            direct_stat = direct_source.stat()
            hostile_code = compile(
                "raise RuntimeError('hostile PFT projection bytecode ran')\n",
                str(direct_source), "exec",
            )
            direct_cache = Path(importlib.util.cache_from_source(
                str(direct_source)
            ))
            direct_cache.write_bytes(
                bootstrap_external._code_to_timestamp_pyc(
                    hostile_code, int(direct_stat.st_mtime),
                    direct_stat.st_size,
                )
            )
            plan = copy.deepcopy(self.plan)
            plan["authority"]["repositories"]["project"]["path"] = str(root)
            loaded = loader_module.load_trusted_output_parser(root, plan)
            self.assertEqual(loaded._TRUSTED_PROJECT_ROOT, str(root))
            self.assertEqual(
                loaded._executing_parser_source_record(loaded._protocol()),
                plan["authority"]["producer"]["output_parser"],
            )
            self.assertEqual(
                loaded._executing_direct_protocol_source_record(
                    loaded._protocol()
                ),
                plan["authority"]["producer"]["direct_release_protocol"],
            )

    def test_trusted_loader_rejects_permissive_pft_direct_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            scripts = root / "scripts"
            scripts.mkdir()
            for relative in (
                protocol.PROTOCOL_PATH, protocol.OUTPUT_PARSER_PATH,
                protocol.DIRECT_PROTOCOL_PATH,
            ):
                source = PROJECT_ROOT / relative
                (root / relative).write_bytes(source.read_bytes())
            (root / protocol.DIRECT_PROTOCOL_PATH).write_bytes(
                b"PFT_USED = True\n"
                b"def validate_semantic_projection(value): return value\n"
                b"def validate_cross_runtime_coverage_projection(value): "
                b"return value\n"
            )
            plan = copy.deepcopy(self.plan)
            plan["authority"]["repositories"]["project"]["path"] = str(root)
            with self.assertRaisesRegex(
                loader_module.LoaderError,
                "direct release protocol source differs from plan authority",
            ):
                loader_module.load_trusted_output_parser(root, plan)

    def test_trusted_loader_rejects_redirected_path_components(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            actual_root = parent / "actual-root"
            actual_scripts = actual_root / "scripts"
            actual_scripts.mkdir(parents=True)
            linked_root = parent / "linked-root"
            linked_root.symlink_to(actual_root, target_is_directory=True)
            with self.assertRaisesRegex(
                loader_module.LoaderError, "project root.*exact",
            ):
                loader_module.load_trusted_output_parser(
                    linked_root, self.plan,
                )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            actual_scripts = root / "actual-scripts"
            actual_scripts.mkdir()
            (root / "scripts").symlink_to(
                actual_scripts, target_is_directory=True,
            )
            plan = copy.deepcopy(self.plan)
            plan["authority"]["repositories"]["project"]["path"] = str(root)
            with self.assertRaisesRegex(
                loader_module.LoaderError, "cannot pin fixed.*sources",
            ):
                loader_module.load_trusted_output_parser(root, plan)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            scripts = root / "scripts"
            scripts.mkdir()
            for relative in (
                protocol.PROTOCOL_PATH, protocol.OUTPUT_PARSER_PATH,
            ):
                source = PROJECT_ROOT / relative
                (root / relative).write_bytes(source.read_bytes())
            redirected = root / "redirected-direct-release-protocol.py"
            redirected.write_bytes(
                (PROJECT_ROOT / protocol.DIRECT_PROTOCOL_PATH).read_bytes()
            )
            (root / protocol.DIRECT_PROTOCOL_PATH).symlink_to(redirected)
            plan = copy.deepcopy(self.plan)
            plan["authority"]["repositories"]["project"]["path"] = str(root)
            with self.assertRaisesRegex(
                loader_module.LoaderError, "cannot pin fixed.*sources",
            ):
                loader_module.load_trusted_output_parser(root, plan)

    def test_trusted_loader_rejects_project_root_entry_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            outer = Path(temporary).resolve()
            named_parent = outer / "named-parent"
            root = named_parent / "project-root"
            scripts = install_fixed_sources(root)
            replacement_parent = outer / "replacement-parent"
            (replacement_parent / "project-root").mkdir(parents=True)
            displaced_parent = outer / "displaced-parent"
            plan = copy.deepcopy(self.plan)
            plan["authority"]["repositories"]["project"]["path"] = str(root)

            held_descriptors = [
                os.open(root, os.O_RDONLY | os.O_DIRECTORY),
                os.open(scripts, os.O_RDONLY | os.O_DIRECTORY),
                *(os.open(root / relative, os.O_RDONLY) for relative in (
                    protocol.PROTOCOL_PATH, protocol.OUTPUT_PARSER_PATH,
                    protocol.DIRECT_PROTOCOL_PATH,
                )),
            ]
            held_before = [
                loader_module._descriptor_identity(os.fstat(descriptor))
                for descriptor in held_descriptors
            ]
            original_compile = loader_module._compile_exact_module
            mutation_ran = False

            def replace_root(*args, **kwargs):
                nonlocal mutation_ran
                if not mutation_ran:
                    mutation_ran = True
                    named_parent.rename(displaced_parent)
                    replacement_parent.rename(named_parent)
                return original_compile(*args, **kwargs)

            loader_module._compile_exact_module = replace_root
            try:
                with self.assertRaisesRegex(
                    loader_module.LoaderError,
                    "named project path component .*named-parent no longer "
                    "identifies its held descriptor",
                ):
                    loader_module.load_trusted_output_parser(root, plan)
                self.assertTrue(mutation_ran)
                self.assertEqual(
                    held_before,
                    [loader_module._descriptor_identity(os.fstat(descriptor))
                     for descriptor in held_descriptors],
                    "root-path replacement must leave every old held fstat "
                    "unchanged",
                )
            finally:
                loader_module._compile_exact_module = original_compile
                for descriptor in held_descriptors:
                    os.close(descriptor)

    def test_trusted_loader_rejects_scripts_entry_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            scripts = install_fixed_sources(root)
            replacement = root / "replacement-scripts"
            replacement.mkdir()
            displaced = root / "displaced-scripts"
            plan = copy.deepcopy(self.plan)
            plan["authority"]["repositories"]["project"]["path"] = str(root)
            original_compile = loader_module._compile_exact_module
            mutation_ran = False

            def replace_scripts(*args, **kwargs):
                nonlocal mutation_ran
                if not mutation_ran:
                    mutation_ran = True
                    scripts.rename(displaced)
                    replacement.rename(scripts)
                return original_compile(*args, **kwargs)

            loader_module._compile_exact_module = replace_scripts
            try:
                with self.assertRaisesRegex(
                    loader_module.LoaderError,
                    "named scripts directory no longer identifies its held "
                    "descriptor",
                ):
                    loader_module.load_trusted_output_parser(root, plan)
                self.assertTrue(mutation_ran)
            finally:
                loader_module._compile_exact_module = original_compile

    def test_trusted_loader_rejects_source_entry_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            scripts = install_fixed_sources(root)
            direct = root / protocol.DIRECT_PROTOCOL_PATH
            replacement = scripts / "replacement-direct-release-protocol.py"
            replacement.write_bytes(direct.read_bytes())
            displaced = scripts / "displaced-direct-release-protocol.py"
            plan = copy.deepcopy(self.plan)
            plan["authority"]["repositories"]["project"]["path"] = str(root)
            original_compile = loader_module._compile_exact_module
            mutation_ran = False

            def replace_source(*args, **kwargs):
                nonlocal mutation_ran
                if not mutation_ran:
                    mutation_ran = True
                    direct.rename(displaced)
                    replacement.rename(direct)
                return original_compile(*args, **kwargs)

            loader_module._compile_exact_module = replace_source
            try:
                with self.assertRaisesRegex(
                    loader_module.LoaderError,
                    "named scripts/direct_release_protocol.py no longer "
                    "identifies its held descriptor",
                ):
                    loader_module.load_trusted_output_parser(root, plan)
                self.assertTrue(mutation_ran)
            finally:
                loader_module._compile_exact_module = original_compile

    def test_incompatible_protocol_sibling_fails_closed(self) -> None:
        sibling = subject._protocol()
        for name, replacement in (
            ("RAW_PROTOCOL_SCHEMA", 1),
            ("REFERENCE_ROLE", "forged-reference-role"),
        ):
            original = getattr(sibling, name)
            try:
                setattr(sibling, name, replacement)
                with self.subTest(name=name), self.assertRaisesRegex(
                    subject.OutputProtocolError, "incompatible.*sibling",
                ):
                    self.parse()
            finally:
                setattr(sibling, name, original)
        original_contract = copy.deepcopy(sibling.MARKER_CONTRACT)
        try:
            sibling.MARKER_CONTRACT["nonce_in_every_marker"] = 1
            with self.assertRaisesRegex(
                subject.OutputProtocolError,
                "marker contract compatibility mismatch",
            ):
                self.parse()
        finally:
            sibling.MARKER_CONTRACT = original_contract
        self.assertIs(subject._protocol(), sibling)

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

    def test_decimal_fields_are_bounded_before_integer_conversion(self) -> None:
        action = marker_indices(
            self.lines, protocol.MARKER_CONTRACT["action_complete"],
        )[0]
        forged = copy.deepcopy(self.lines)
        forged[action] = replace_field(forged[action], 2, "9" * 5000)
        with self.assertRaisesRegex(
            subject.OutputProtocolError, "overlong completed action index",
        ):
            self.parse(forged)
        for value in ("+1", "-1", "1.0", "1e0", " 1"):
            with self.subTest(value=value), self.assertRaisesRegex(
                subject.OutputProtocolError, "noncanonical hostile decimal",
            ):
                subject._decimal(value, "hostile decimal")


if __name__ == "__main__":
    unittest.main()
