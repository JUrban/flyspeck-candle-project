#!/usr/bin/python3

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest
from unittest import mock


SUBJECT_PATH = Path(__file__).with_name("pristine_direct_reference_protocol.py")
SPEC = importlib.util.spec_from_file_location(
    "pristine_direct_reference_protocol", SUBJECT_PATH,
)
assert SPEC is not None and SPEC.loader is not None
subject = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = subject
SPEC.loader.exec_module(subject)

DIRECT_TEST_PATH = Path(__file__).with_name("test-direct-release-protocol.py")
DIRECT_SPEC = importlib.util.spec_from_file_location(
    "pristine_reference_direct_fixture", DIRECT_TEST_PATH,
)
assert DIRECT_SPEC is not None and DIRECT_SPEC.loader is not None
direct_fixture = importlib.util.module_from_spec(DIRECT_SPEC)
sys.modules[DIRECT_SPEC.name] = direct_fixture
DIRECT_SPEC.loader.exec_module(direct_fixture)
subject._DIRECT_PROTOCOL = direct_fixture.subject


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def content(text: str, *, empty: bool = False) -> dict[str, object]:
    return {"bytes": 0 if empty else len(text) + 1, "sha256": hash_text(text)}


def named(path: str, text: str) -> dict[str, object]:
    return {"path": path, **content(text)}


def named_value(path: str, value: object) -> dict[str, object]:
    return {"path": path, **subject.content_record(value)}


def named_file(path: str) -> dict[str, object]:
    data = Path(__file__).parent.parent.joinpath(path).read_bytes()
    return {
        "path": path,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def executable(path: str, text: str) -> dict[str, object]:
    return {
        "argument_path": path,
        "resolved_path": path,
        **content(text),
        "mode": "100755",
    }


def common_projections() -> tuple[dict, dict]:
    fingerprints, dependency = direct_fixture.fixture()
    semantic = direct_fixture.subject.project_authenticated_semantic_observations(
        fingerprints, dependency,
    )
    receipt, plan = direct_fixture.schema6_fixture()
    coverage = direct_fixture.subject.cross_runtime_coverage_projection_from_schema6(
        receipt, plan,
    )
    replacements = {
        subject.LP_WRAPPER_AFTER_ACTION_INDEX: (
            subject.LP_CERTIFICATE_SOURCE,
            "../formal_lp/hypermap/main/lp_certificate.hl",
        ),
        subject.LP_VERIFY_ACTION_INDEX: (
            subject.LP_VERIFY_SOURCE,
            "../formal_lp/hypermap/verify_all.hl",
        ),
        subject.LP_CONSUMER_ACTION_INDEX: (
            subject.LP_CONSUMER_SOURCE,
            "tame/linear_programming_results.hl",
        ),
    }
    inventory = coverage["original_source_inventory"]
    closure = coverage["selected_logical_source_closure"]
    for index, (new_key, new_target) in replacements.items():
        action = coverage["actions"]["records"][index]
        old_key = action["selected_source"]
        action["selected_source"] = new_key
        action["target"] = new_target
        source = next(record for record in inventory["records"]
                      if record["key"] == old_key)
        repository, path = new_key.split(":", 1)
        source.update(key=new_key, repository=repository, path=path)
        logical = next(record for record in closure["records"]
                       if record["key"] == old_key)
        logical["key"] = new_key
    for new_key in (subject.HOL_LIGHT_SOURCE, subject.STRICTBUILD_SOURCE):
        source = next(
            record for record in inventory["records"]
            if record["key"].startswith("flyspeck:fixture/extra-")
        )
        repository, path = new_key.split(":", 1)
        source.update(key=new_key, repository=repository, path=path)
        closure["records"].append({
            "index": len(closure["records"]),
            "key": new_key,
            "original_bytes": source["original_bytes"],
            "original_sha256": source["original_sha256"],
            "original_md5": source["original_md5"],
            "candle_plan_execution_selection": copy.deepcopy(
                source["candle_plan_execution_selection"]
            ),
        })
    coverage["actions"]["ordered_record_sha256"] = subject.canonical_sha256(
        coverage["actions"]["records"]
    )
    for container in (inventory, closure):
        container["records"].sort(key=lambda record: record["key"])
        for index, record in enumerate(container["records"]):
            record["index"] = index
        container["record_count"] = len(container["records"])
        container["ordered_record_sha256"] = subject.canonical_sha256(
            container["records"]
        )
    direct_fixture.subject.validate_cross_runtime_coverage_projection(coverage)
    return semantic, coverage


def make_authority(
    semantic: dict, coverage: dict, *, authority_seed: str = "a",
) -> dict:
    final = next(
        record for record in coverage["original_source_inventory"]["records"]
        if record["key"] == subject.FINAL_TARGET_SOURCE
    )
    return {
        "policy": subject.AUTHORITY_POLICY,
        "producer": {
            "entrypoint": named(
                subject.PRODUCER_ENTRYPOINT_PATH,
                f"collector-{authority_seed}",
            ),
            "protocol": named_file(subject.PROTOCOL_PATH),
            "output_parser": named_file(subject.OUTPUT_PARSER_PATH),
            "direct_release_protocol": named_file(subject.DIRECT_PROTOCOL_PATH),
        },
        "repositories": {
            "project": {
                "path": str(Path(__file__).parent.parent.resolve()),
                "git_head": "1" * 40,
                "git_status": "",
            },
            "hol_light": {
                "path": "/project/reference-hol-light",
                "git_head": "2" * 40,
                "git_status": "",
            },
            "flyspeck": {
                "path": "/project/reference-flyspeck",
                "git_head": "3" * 40,
                "git_status": "",
            },
        },
        "runtime": {
            "ocaml_hol": executable("/project/bin/ocaml-hol", "ocaml-hol"),
            "gp": executable("/usr/bin/gp", "gp"),
            "csdp": executable("/project/bin/csdp", "csdp"),
            "runtime_elf_closure": content(f"elf-{authority_seed}"),
        },
        "inputs": {
            "action_plan": named("plan-actions.json", "pending-plan-actions"),
            "source_inventory": named_value(
                "source-inventory.json", coverage["original_source_inventory"],
            ),
            "generated_inputs": named_value(
                "generated-inputs.json", coverage["generated_inputs"],
            ),
            "serializer": {
                "path": "candle/fingerprint.ml",
                "bytes": 101,
                "sha256": semantic["serializer"]["sha256"],
                "md5": "b" * 32,
            },
            "final_target": {
                "path": "candle/flyspeck_l2_target.ml",
                "bytes": final["original_bytes"],
                "sha256": final["original_sha256"],
            },
        },
    }


def make_plan(
    ordinal: int, nonce: str, semantic: dict, coverage: dict,
    *, authority_seed: str = "a",
) -> dict:
    action_records = []
    for record in coverage["actions"]["records"]:
        action_records.append({
            field: copy.deepcopy(record[field]) for field in (
                "index", "selected_source", "target", "stratum",
                "original_bytes", "original_sha256", "original_md5",
                "candle_plan_execution_selection",
            )
        })
    actions = {
        "policy": subject.ACTION_POLICY,
        "execution_selection_semantics":
            subject.EXECUTION_SELECTION_SEMANTICS,
        "record_count": len(action_records),
        "ordered_record_sha256": subject.canonical_sha256(action_records),
        "records": action_records,
    }
    lp_records = []
    for record in coverage["lp_certificate_consumption"]["records"]:
        lp_records.append({
            field: copy.deepcopy(record[field]) for field in (
                "index", "class", "relative", "bytes", "sha256",
            )
        })
    lp_inputs = {
        "schema": 1,
        "kind": subject.LP_INPUT_KIND,
        "order": "canonical-relative-path-lexicographic-v1",
        "record_count": len(lp_records),
        "ordered_record_sha256": subject.canonical_sha256(lp_records),
        "records": lp_records,
    }
    plan = {
        "schema": subject.RAW_PROTOCOL_SCHEMA,
        "kind": subject.PLAN_KIND,
        "role": subject.REFERENCE_ROLE,
        "reference_ordinal": ordinal,
        "nonce_kind": subject.REFERENCE_NONCE_KIND,
        "session_nonce": nonce,
        "boundary_id": subject.FINAL_BOUNDARY_ID,
        "fresh_process_replay_from_action_zero": True,
        "process_state_checkpoint": None,
        "serialization_environment": {
            "key": subject.SERIALIZATION_ENVIRONMENT_KEY,
            "present": False,
        },
        "environment_policy": subject.ENVIRONMENT_POLICY,
        "thread_count": 1,
        "authority": make_authority(
            semantic, coverage, authority_seed=authority_seed,
        ),
        "actions": actions,
        "lp_certificate_inputs": lp_inputs,
        "retained_stdout_max_bytes": subject.RETAINED_STDOUT_MAX_BYTES,
        "retained_stderr_max_bytes": subject.RETAINED_STDERR_MAX_BYTES,
        "retained_input_artifact_root": "/project/reference-inputs",
        "approval_included": False,
        "pft_used": False,
        "s2_s3_evidence": False,
    }
    plan["authority"]["inputs"]["action_plan"] = named_value(
        "plan-actions.json", plan["actions"],
    )
    return plan


def make_request(plan: dict) -> dict:
    return {
        "schema": subject.RAW_PROTOCOL_SCHEMA,
        "kind": subject.REQUEST_KIND,
        "role": plan["role"],
        "reference_ordinal": plan["reference_ordinal"],
        "nonce_kind": plan["nonce_kind"],
        "session_nonce": plan["session_nonce"],
        "boundary_id": plan["boundary_id"],
        "plan": subject.content_record(plan),
        "request_source": named(
            "request.ml", f"request-{plan['reference_ordinal']}-{plan['session_nonce']}",
        ),
        "entrypoint_sequence": copy.deepcopy(list(subject.ENTRYPOINT_SEQUENCE)),
        "marker_contract": copy.deepcopy(subject.MARKER_CONTRACT),
        "action_count": subject.FINAL_ACTION_COUNT,
        "serialization_environment": copy.deepcopy(
            plan["serialization_environment"]
        ),
        "fresh_process_replay_from_action_zero": True,
        "process_state_checkpoint": None,
        "retained_stdout_max_bytes": plan["retained_stdout_max_bytes"],
        "retained_stderr_max_bytes": plan["retained_stderr_max_bytes"],
        "retained_input_artifact_root": plan["retained_input_artifact_root"],
        "approval_included": False,
        "pft_used": False,
        "s2_s3_evidence": False,
    }


def make_lp_successes(plan: dict) -> dict:
    records = []
    inputs = plan["lp_certificate_inputs"]["records"]
    for index, input_index in enumerate(reversed(range(39))):
        source = inputs[input_index]
        records.append({
            "index": index,
            "session_nonce": plan["session_nonce"],
            "action_index": subject.LP_CONSUMER_ACTION_INDEX,
            "input_index": input_index,
            "class": source["class"],
            "relative": source["relative"],
            "bytes": source["bytes"],
            "sha256": source["sha256"],
            "successful_deserialization_count": 1,
        })
    return {
        "schema": 1,
        "kind": subject.LP_SUCCESS_KIND,
        "order": subject.LP_ORDER,
        "record_count": len(records),
        "ordered_record_sha256": subject.canonical_sha256(records),
        "records": records,
    }


def make_loader_event(
    index: int, phase: str, action_index: int | None, key: str,
    size: int, sha256: str, md5: str, session_nonce: str,
) -> dict:
    return {
        "index": index,
        "session_nonce": session_nonce,
        "phase": phase,
        "action_index": action_index,
        "logical_source": key,
        "basename": PurePathName(key),
        "bytes": size,
        "sha256": sha256,
        "md5": md5,
    }


def PurePathName(key: str) -> str:
    return key.partition(":")[2].rsplit("/", 1)[-1]


def make_transcript(
    plan: dict, request: dict, coverage: dict,
) -> tuple[dict, list[dict]]:
    inventory = {
        record["key"]: record for record in
        coverage["original_source_inventory"]["records"]
    }
    events = [
        make_loader_event(
            0, "bootstrap", None, subject.HOL_LIGHT_SOURCE,
            inventory[subject.HOL_LIGHT_SOURCE]["original_bytes"],
            inventory[subject.HOL_LIGHT_SOURCE]["original_sha256"],
            inventory[subject.HOL_LIGHT_SOURCE]["original_md5"],
            plan["session_nonce"],
        ),
        make_loader_event(
            1, "bootstrap", None, subject.STRICTBUILD_SOURCE,
            inventory[subject.STRICTBUILD_SOURCE]["original_bytes"],
            inventory[subject.STRICTBUILD_SOURCE]["original_sha256"],
            inventory[subject.STRICTBUILD_SOURCE]["original_md5"],
            plan["session_nonce"],
        ),
        make_loader_event(
            2, "bootstrap", None, "flyspeck:b.hl",
            inventory["flyspeck:b.hl"]["original_bytes"],
            inventory["flyspeck:b.hl"]["original_sha256"],
            inventory["flyspeck:b.hl"]["original_md5"],
            plan["session_nonce"],
        ),
    ]
    completions = []
    cursor = len(events)
    for action in plan["actions"]["records"]:
        event = make_loader_event(
            cursor, "action", action["index"], action["selected_source"],
            action["original_bytes"], action["original_sha256"],
            action["original_md5"], plan["session_nonce"],
        )
        events.append(event)
        completions.append({
            "index": action["index"],
            "session_nonce": plan["session_nonce"],
            "selected_source": action["selected_source"],
            "source_sha256": action["original_sha256"],
            "completion_status": "completed-observed-unapproved",
            "ledger_start_index": cursor,
            "ledger_end_index": cursor + 1,
            "ordered_ledger_delta_sha256": subject.canonical_sha256([event]),
            "loader_outcome": "loaded",
            "selected_ledger_index": cursor,
        })
        cursor += 1
    final = plan["authority"]["inputs"]["final_target"]
    serializer = plan["authority"]["inputs"]["serializer"]
    events.append(make_loader_event(
        cursor, "post-action", None, subject.FINAL_TARGET_SOURCE,
        final["bytes"], final["sha256"],
        inventory[subject.FINAL_TARGET_SOURCE]["original_md5"],
        plan["session_nonce"],
    ))
    cursor += 1
    events.append(make_loader_event(
        cursor, "post-action", None, subject.SERIALIZER_SOURCE,
        serializer["bytes"], serializer["sha256"], serializer["md5"],
        plan["session_nonce"],
    ))
    actions = {
        "record_count": len(completions),
        "ordered_record_sha256": subject.canonical_sha256(completions),
        "initial_ledger_count": 3,
        "final_ledger_count": 3 + subject.FINAL_ACTION_COUNT,
        "records": completions,
    }
    transcript = {
        "schema": subject.RAW_PROTOCOL_SCHEMA,
        "kind": subject.TRANSCRIPT_KIND,
        "role": plan["role"],
        "reference_ordinal": plan["reference_ordinal"],
        "nonce_kind": plan["nonce_kind"],
        "session_nonce": plan["session_nonce"],
        "boundary_id": plan["boundary_id"],
        "plan": subject.content_record(plan),
        "request": subject.content_record(request),
        "marker_protocol": subject.MARKER_PROTOCOL,
        "stdout": content(f"stdout-{plan['session_nonce']}"),
        "stderr": content("", empty=True),
        "exit_code": 0,
        "timed_out": False,
        "session_started": True,
        "session_completed": True,
        "action_completions": actions,
        "lp_successes": make_lp_successes(plan),
        "status": "process-complete-unapproved",
        "approval_included": False,
        "pft_used": False,
        "s2_s3_evidence": False,
    }
    return transcript, events


def make_closure(
    plan: dict, request: dict, transcript: dict, events: list[dict],
) -> dict:
    final = transcript["action_completions"]["final_ledger_count"]
    return {
        "schema": subject.RAW_PROTOCOL_SCHEMA,
        "kind": subject.NATIVE_CLOSURE_KIND,
        "role": plan["role"],
        "reference_ordinal": plan["reference_ordinal"],
        "nonce_kind": plan["nonce_kind"],
        "session_nonce": plan["session_nonce"],
        "boundary_id": plan["boundary_id"],
        "plan": subject.content_record(plan),
        "request": subject.content_record(request),
        "transcript": subject.content_record(transcript),
        "loader_policy": subject.LOADER_LEDGER_POLICY,
        "loader_order": subject.LOADER_LEDGER_ORDER,
        "loader_parentage_observed": False,
        "loader_cache_outcomes_observed": False,
        "loader_ledger_artifact": content(
            f"loader-ledger-{plan['session_nonce']}"
        ),
        "loader_event_count": len(events),
        "ordered_loader_event_sha256": subject.canonical_sha256(events),
        "loader_events": events,
        "pre_action_event_count": 3,
        "post_action_event_count": len(events) - final,
        "action_bindings": copy.deepcopy(transcript["action_completions"]),
        "lp_success_artifact": content(
            f"lp-success-{plan['session_nonce']}"
        ),
        "lp_successes": copy.deepcopy(transcript["lp_successes"]),
        "raw_lp_order_retained": True,
        "unsupported_identity_count": 0,
        "status": "native-observation-complete-unapproved",
        "approval_included": False,
        "pft_used": False,
        "s2_s3_evidence": False,
    }


def make_candidate(
    plan: dict, request: dict, transcript: dict, closure: dict,
    semantic: dict, coverage: dict,
) -> dict:
    return {
        "schema": subject.RAW_PROTOCOL_SCHEMA,
        "kind": subject.RAW_CANDIDATE_KIND,
        "role": plan["role"],
        "reference_ordinal": plan["reference_ordinal"],
        "nonce_kind": plan["nonce_kind"],
        "session_nonce": plan["session_nonce"],
        "boundary_id": plan["boundary_id"],
        "status": "complete-unapproved",
        "authentication_status": "not-authenticated",
        "authority_sha256": subject.canonical_sha256(plan["authority"]),
        "artifacts": {
            "plan": subject.content_record(plan),
            "request": subject.content_record(request),
            "transcript": subject.content_record(transcript),
            "native_execution_closure": subject.content_record(closure),
            "semantic_projection": subject.content_record(semantic),
            "cross_runtime_coverage": subject.content_record(coverage),
        },
        "action_count": subject.FINAL_ACTION_COUNT,
        "loader_event_count": closure["loader_event_count"],
        "lp_success_count": 39,
        "exit_code": 0,
        "timed_out": False,
        "validation_error": None,
        "fresh_process_replay_from_action_zero": True,
        "process_state_checkpoint": None,
        "serialization_environment": copy.deepcopy(
            plan["serialization_environment"]
        ),
        "approved_reference_present": False,
        "promotion_allowed": False,
        "pft_used": False,
        "s2_eligible": False,
        "s3_eligible": False,
        "s2_s3_evidence": False,
    }


def bundle_fixture(
    ordinal: int = 1, nonce: str = "1" * 64, *,
    authority_seed: str = "a", common: tuple[dict, dict] | None = None,
) -> dict:
    semantic, coverage = common if common is not None else common_projections()
    plan = make_plan(
        ordinal, nonce, semantic, coverage, authority_seed=authority_seed,
    )
    request = make_request(plan)
    transcript, events = make_transcript(plan, request, coverage)
    closure = make_closure(plan, request, transcript, events)
    candidate = make_candidate(
        plan, request, transcript, closure, semantic, coverage,
    )
    return {
        "plan": plan,
        "request": request,
        "transcript": transcript,
        "native_execution_closure": closure,
        "semantic_projection": semantic,
        "cross_runtime_coverage": coverage,
        "candidate": candidate,
    }


class PristineDirectReferenceProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.common = common_projections()
        cls.bundle = bundle_fixture(common=cls.common)

    def test_v3_core_artifacts_validate_but_candidate_and_bundle_fail_closed(self) -> None:
        bundle = copy.deepcopy(self.bundle)
        self.assertIs(subject.validate_raw_plan(bundle["plan"]), bundle["plan"])
        self.assertIs(
            subject.validate_raw_request(bundle["request"], bundle["plan"]),
            bundle["request"],
        )
        self.assertIs(
            subject.validate_raw_transcript(
                bundle["transcript"], bundle["plan"], bundle["request"],
            ), bundle["transcript"],
        )
        self.assertIs(
            subject.validate_native_execution_closure(
                bundle["native_execution_closure"], bundle["plan"],
                bundle["request"], bundle["transcript"],
            ), bundle["native_execution_closure"],
        )
        self.assertEqual(bundle["plan"]["schema"], subject.RAW_PROTOCOL_SCHEMA)
        self.assertEqual(bundle["request"]["schema"], subject.RAW_PROTOCOL_SCHEMA)
        self.assertEqual(
            bundle["plan"]["authority"]["producer"]["output_parser"],
            named_file(subject.OUTPUT_PARSER_PATH),
        )
        self.assertEqual(
            bundle["plan"]["authority"]["producer"]["direct_release_protocol"],
            named_file(subject.DIRECT_PROTOCOL_PATH),
        )
        self.assertEqual(
            bundle["request"]["marker_contract"]["native_load"],
            subject.MARKER_CONTRACT["native_load"],
        )
        arguments = (
            bundle["candidate"], bundle["plan"], bundle["request"],
            bundle["transcript"], bundle["native_execution_closure"],
            bundle["semantic_projection"], bundle["cross_runtime_coverage"],
        )
        with self.assertRaisesRegex(subject.ProtocolError, "future held collector"):
            subject.validate_raw_candidate(*arguments)
        with self.assertRaisesRegex(subject.ProtocolError, "descriptor-rooted"):
            subject.validate_reference_bundle(bundle)
        self.assertFalse(any(
            name.startswith("build_authenticated") or "descriptor" in name
            for name in dir(subject)
        ))

    def test_v4_identity_reservation_is_exact_and_disjoint(self) -> None:
        self.assertEqual(subject.RAW_PROTOCOL_SCHEMA, 3)
        self.assertEqual(
            subject.PLAN_KIND,
            "candle-flyspeck-pristine-direct-reference-raw-plan-v3",
        )
        self.assertEqual(
            subject.REQUEST_KIND,
            "candle-flyspeck-pristine-direct-reference-request-v3",
        )
        self.assertEqual(
            subject.TRANSCRIPT_KIND,
            "candle-flyspeck-pristine-direct-reference-transcript-v3",
        )
        self.assertEqual(
            subject.MARKER_PROTOCOL,
            "candle-flyspeck-pristine-direct-reference-markers-v3",
        )
        self.assertEqual(subject.V4_RAW_PROTOCOL_SCHEMA, 4)
        self.assertEqual(subject.V4_PLAN_KIND,
                         "candle-flyspeck-pristine-direct-reference-raw-plan-v4")
        self.assertEqual(subject.V4_REQUEST_KIND,
                         "candle-flyspeck-pristine-direct-reference-request-v4")
        self.assertEqual(
            subject.V4_TRANSCRIPT_KIND,
            "candle-flyspeck-pristine-direct-reference-transcript-v4",
        )
        self.assertEqual(
            subject.V4_NATIVE_CLOSURE_KIND,
            "candle-flyspeck-pristine-direct-native-execution-closure-v4",
        )
        self.assertEqual(subject.V4_BUNDLE_SCHEMA, 4)
        self.assertEqual(subject.V4_PAIR_SCHEMA, 4)
        self.assertEqual(subject.V4_KERNEL_PROFILE_SCHEMA, 2)
        self.assertEqual(subject.V4_PREFLIGHT_SCHEMA, 2)
        self.assertNotEqual(subject.V4_PLAN_KIND, subject.PLAN_KIND)
        self.assertNotEqual(subject.V4_REQUEST_KIND, subject.REQUEST_KIND)
        self.assertNotEqual(subject.V4_MARKER_PROTOCOL, subject.MARKER_PROTOCOL)
        self.assertEqual(subject.V4_MARKER_CONTRACT, {
            "protocol": "candle-flyspeck-pristine-direct-reference-markers-v4",
            "session_start": "CANDLE_PRISTINE_DIRECT_REFERENCE_START_V4",
            "native_load": "CANDLE_PRISTINE_DIRECT_NATIVE_LOAD_V4",
            "startup_baseline": "CANDLE_PRISTINE_DIRECT_STARTUP_BASELINE_V4",
            "strictbuild_complete":
                "CANDLE_PRISTINE_DIRECT_STRICTBUILD_COMPLETE_V4",
            "action_complete": "CANDLE_PRISTINE_DIRECT_ACTION_COMPLETE_V4",
            "lp_success": "CANDLE_PRISTINE_DIRECT_LP_SUCCESS_V4",
            "semantic_observation": "CANDLE_PRISTINE_DIRECT_SEMANTIC_V4",
            "session_complete":
                "CANDLE_PRISTINE_DIRECT_REFERENCE_COMPLETE_V4",
            "nonce_in_every_marker": True,
        })
        self.assertEqual(subject.V4_CONTROL_MAX_BYTES, 67_108_864)
        self.assertEqual(subject.V4_CONTROL_READ_MAX_BYTES, 67_108_865)
        self.assertEqual(subject.V4_AUTHORITY_CAPSULE_MAX_BYTES, 587_202_560)
        self.assertEqual(
            subject.V4_AUTHORITY_CAPSULE_READ_MAX_BYTES, 587_202_561,
        )
        self.assertEqual(subject.V4_POSTFLIGHT_RESULT_MAX_BYTES, 1_073_741_824)
        self.assertEqual(
            subject.V4_POSTFLIGHT_RESULT_READ_MAX_BYTES, 1_073_741_825,
        )
        self.assertEqual(
            subject.V4_TRACE_CHUNK_COUNT_MAX * subject.V4_TRACE_CHUNK_MAX_BYTES,
            subject.V4_TRACE_TOTAL_MAX_BYTES,
        )
        self.assertEqual(subject.V4_TRACE_CHUNK_COUNT_MIN, 1)

    def test_all_reserved_v4_consumers_fail_before_decoding(self) -> None:
        one_value = (
            subject.validate_v4_raw_candidate,
            subject.validate_v4_capture_envelope,
            subject.validate_v4_pending_candidate,
            subject.validate_v4_capture_completion,
            subject.validate_v4_reference_bundle,
            subject.validate_v4_distinct_reference_pair,
            subject.validate_v4_postflight_result,
        )
        canonical = (
            subject.validate_canonical_v4_raw_candidate_bytes,
            subject.validate_canonical_v4_capture_envelope_bytes,
            subject.validate_canonical_v4_pending_candidate_bytes,
            subject.validate_canonical_v4_capture_completion_bytes,
            subject.validate_canonical_v4_reference_bundle_bytes,
            subject.validate_canonical_v4_distinct_reference_pair_bytes,
            subject.validate_canonical_postflight_result_bytes,
        )
        for validator in one_value:
            with self.subTest(validator=validator.__name__), self.assertRaisesRegex(
                subject.ProtocolError, "V4 .* consumption is disabled",
            ):
                validator(object())
        with mock.patch.object(
            subject, "decode_object", side_effect=AssertionError("decoded"),
        ):
            for validator in canonical:
                with self.subTest(
                    validator=validator.__name__,
                ), self.assertRaisesRegex(
                    subject.ProtocolError, "V4 .* consumption is disabled",
                ):
                    validator(b'{"schema":4}')
    def test_v4_auxiliary_reservations_are_exact(self) -> None:
        identities = {
            "V4_POSTFLIGHT_RESULT_KIND":
                "candle-flyspeck-pristine-postflight-result-v1",
            "V4_GENERATION_AUTHORITY_KIND":
                "candle-flyspeck-pristine-request-generation-authority-v1",
            "V4_GENERATION_RECEIPT_KIND":
                "candle-flyspeck-pristine-request-generation-receipt-v1",
            "V4_COLLECTION_AUTHORITY_KIND":
                "candle-flyspeck-pristine-full-run-collection-authority-v1",
            "V4_COLLECTION_RECEIPT_KIND":
                "candle-flyspeck-pristine-full-run-collection-authority-receipt-v1",
            "V4_NATIVE_SOURCE_TREE_KIND":
                "candle-flyspeck-native-source-tree-v1",
            "V4_NATIVE_BUILD_RECEIPT_KIND":
                "candle-flyspeck-isolated-native-build-receipt-v1",
            "V4_PYTHON_RUNTIME_CLOSURE_KIND":
                "candle-flyspeck-python-runtime-closure-v1",
            "V4_NATIVE_RUNTIME_CLOSURE_KIND":
                "candle-flyspeck-native-runtime-closure-v1",
            "V4_SECCOMP_FILTER_AUTHORITY_KIND":
                "candle-flyspeck-seccomp-filter-authority-v1",
            "V4_GLIBC_STUB_PROVENANCE_KIND":
                "candle-flyspeck-glibc-posix-spawn-stub-provenance-v1",
            "V4_AUTHORITY_CAPSULE_KIND":
                "candle-flyspeck-pristine-authority-capsule-v1",
            "V4_POSITIONAL_REQUEST_BINDING_KIND":
                "candle-flyspeck-pristine-positional-request-binding-v1",
            "V4_EMPTY_STDIN_BINDING_KIND":
                "candle-flyspeck-pristine-empty-stdin-binding-v1",
            "V4_SOURCE_CONSUMPTION_JOINS_KIND":
                "candle-flyspeck-pristine-source-consumption-joins-v1",
            "V4_LP_DESERIALIZER_JOINS_KIND":
                "candle-flyspeck-pristine-lp-deserializer-joins-v1",
            "V4_NAMESPACE_REVALIDATION_KIND":
                "candle-flyspeck-v4-namespace-revalidation-v1",
            "V4_POSTFLIGHT_RUNTIME_ROOT_RECEIPT_KIND":
                "candle-flyspeck-postflight-runtime-root-receipt-v1",
        }
        for name, expected in identities.items():
            with self.subTest(name=name):
                self.assertEqual(getattr(subject, name), expected)

        schemas = (
            "V4_POSTFLIGHT_RESULT_SCHEMA",
            "V4_GENERATION_AUTHORITY_SCHEMA",
            "V4_GENERATION_RECEIPT_SCHEMA",
            "V4_COLLECTION_AUTHORITY_SCHEMA",
            "V4_COLLECTION_RECEIPT_SCHEMA",
        )
        for name in schemas:
            with self.subTest(name=name):
                self.assertEqual(getattr(subject, name), 1)

        policies = {
            "V4_REQUEST_EXECUTION_POLICY":
                "private-root-positional-ocaml-script-empty-stdin-v1",
            "V4_STDIN_POLICY": "supervisor-pipe-exact-eof-v1",
            "V4_STDOUT_POLICY":
                "supervisor-pipe-bounded-opaque-with-reserved-markers-v1",
            "V4_STDERR_POLICY": "supervisor-pipe-exact-empty-v1",
            "V4_GENERATION_AUTHORITY_POLICY":
                "captured-fixed-loader-isolated-python-exact-source-v1",
            "V4_COLLECTION_AUTHORITY_POLICY":
                "single-native-supervisor-seize-trace-and-postexit-finalize-v1",
            "V4_AUTHORITY_CAPSULE_POLICY":
                "retained-inline-canonical-authority-objects-v1",
            "V4_INVENTORY_NORMALIZATION_POLICY":
                "preserve-bytes-strip-write-bits-v1",
            "V4_POSITIONAL_REQUEST_BINDING_POLICY":
                "same-exec-argv-open-private-immutable-object-v1",
            "V4_LP_WRAPPER_CONTRACT":
                "original-deserializer-return-before-marker-v1",
            "V4_NAMESPACE_REVALIDATION_POLICY":
                "reopen-all-control-and-authority-inventory-edges-v1",
            "V4_POSTFLIGHT_RUNTIME_ROOT_POLICY":
                "retained-python-closure-read-only-pivot-root-v1",
        }
        for name, expected in policies.items():
            with self.subTest(name=name):
                self.assertEqual(getattr(subject, name), expected)
        self.assertEqual(subject.V4_REQUEST_SCRIPT_ROLE,
                         "positional-request-script")
        self.assertEqual(subject.V4_REQUEST_SCRIPT_PATH,
                         "/candle-pristine/request.ml")
        self.assertEqual(subject.V4_REQUEST_SCRIPT_MODE, "100444")
        self.assertEqual(
            subject.V4_REQUEST_SCRIPT_INVENTORY_POLICY,
            "private-root-read-only-object-v1",
        )
        self.assertEqual(subject.V4_PUBLICATION_POLICIES, (
            "publish-envelope-v2",
            "publish-pending-candidate-v2",
            "publish-completion-v2",
        ))

        statuses = {
            subject.V4_GENERATION_RECEIPT_STATUS:
                "generated-and-captured-unapproved",
            subject.V4_COLLECTION_RECEIPT_STATUS:
                "captured-current-host-collection-authority-unapproved",
            subject.V4_NATIVE_CLOSURE_STATUS:
                "full-run-observation-complete-unapproved",
            subject.V4_SOURCE_REDERIVATION_STATUS: "complete-unapproved",
            subject.V4_CAPTURE_ENVELOPE_STATUS:
                "captured-awaiting-postflight-unapproved",
            subject.V4_PENDING_CANDIDATE_STATUS:
                "pending-postflight-unapproved",
            subject.V4_CAPTURE_COMPLETION_STATUS:
                "capture-complete-unapproved",
            subject.V4_POSTFLIGHT_RESULT_STATUS: "validated-unapproved",
            subject.V4_AUTHENTICATION_STATUS: "not-authenticated",
        }
        for actual, expected in statuses.items():
            self.assertEqual(actual, expected)

        caps = {
            "V4_AUTHORITY_OBJECT_MAX_BYTES": 33_554_432,
            "V4_AUTHORITY_OBJECT_READ_MAX_BYTES": 33_554_433,
            "V4_FIXED_SOURCE_MAX_BYTES": 16_777_216,
            "V4_STARTUP_DESIGN_MAX_BYTES": 1_048_576,
            "V4_AUTHORITY_CAPSULE_DECODED_MAX_BYTES": 437_256_192,
            "V4_REQUEST_RESULT_HEADER_BYTES": 38,
            "V4_COLLECTION_FRAME_MAX_BYTES": 402_653_396,
            "V4_SOURCE_TREE_MEMBER_MAX": 65_536,
            "V4_SOURCE_TREE_TOTAL_MAX_BYTES": 4_294_967_296,
            "V4_INVENTORY_OBJECT_MAX": 131_072,
            "V4_INVENTORY_TOTAL_MAX_BYTES": 68_719_476_736,
            "V4_NAMESPACE_EDGE_MAX": 16_384,
            "V4_POSTFLIGHT_MAPPING_MAX": 262_144,
            "V4_EMPTY_STDIN_EVENT_MAX": 4_096,
        }
        for name, expected in caps.items():
            with self.subTest(name=name):
                self.assertEqual(getattr(subject, name), expected)

        self.assertEqual(subject.V4_BUNDLE_FIELDS, frozenset({
            "schema", "kind", "role", "reference_ordinal", "nonce_kind",
            "session_nonce", "boundary_id", "plan", "request",
            "request_generation_receipt", "collection_authority_receipt",
            "capture_envelope", "source_rederivation", "coverage",
            "pending_candidate", "capture_completion", "approval_included",
            "pft_used", "s2_eligible", "s3_eligible", "s2_s3_evidence",
        }))
        self.assertEqual(subject.V4_PAIR_FIELDS, frozenset({
            "schema", "kind", "role", "first", "second",
            "shared_authority", "shared_evidence_contracts",
            "distinct_attempt_roots", "distinct_ordinals",
            "distinct_nonces", "semantic_equal", "coverage_equal",
            "approval_included", "pft_used", "s2_eligible", "s3_eligible",
            "s2_s3_evidence",
        }))

    def test_complete_v4_constant_table_fingerprint(self) -> None:
        def normalize(value: object) -> object:
            if isinstance(value, frozenset):
                return {"frozenset": sorted(normalize(item) for item in value)}
            if isinstance(value, tuple):
                return {"tuple": [normalize(item) for item in value]}
            if isinstance(value, dict):
                return {
                    key: normalize(item)
                    for key, item in sorted(value.items())
                }
            return value

        values = {
            name: normalize(getattr(subject, name))
            for name in dir(subject)
            if name.startswith("V4_") and name.isupper()
        }
        encoded = json.dumps(
            values, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode()
        self.assertEqual(len(values), 139)
        self.assertEqual(
            hashlib.sha256(encoded).hexdigest(),
            "4e5da349f39c4d60cd2fad6bc2fbb38f8c9f9d5473b87d471cddcb47598062de",
        )

    def test_four_available_v3_artifact_schemas_are_canonical(self) -> None:
        bundle = self.bundle
        cases = (
            (
                "plan", subject.validate_canonical_raw_plan_bytes,
                (bundle["plan"],),
            ),
            (
                "request", subject.validate_canonical_raw_request_bytes,
                (bundle["request"], bundle["plan"]),
            ),
            (
                "transcript", subject.validate_canonical_raw_transcript_bytes,
                (bundle["transcript"], bundle["plan"], bundle["request"]),
            ),
            (
                "closure", subject.validate_canonical_native_closure_bytes,
                (
                    bundle["native_execution_closure"], bundle["plan"],
                    bundle["request"], bundle["transcript"],
                ),
            ),
        )
        for label, validator, arguments in cases:
            value, *dependencies = arguments
            encoded = subject.canonical_json_bytes(value)
            with self.subTest(label=label):
                self.assertEqual(validator(encoded, *dependencies), value)
                with self.assertRaisesRegex(subject.ProtocolError, "immutable bytes"):
                    validator(bytearray(encoded), *dependencies)
                with self.assertRaisesRegex(subject.ProtocolError, "not canonical"):
                    validator(subject.canonical_value_bytes(value), *dependencies)

    def test_duplicate_nonfinite_and_nonobject_json_reject(self) -> None:
        for label, encoded, message in (
            ("duplicate", b'{"schema":1,"schema":1}', "duplicate JSON key"),
            ("nonfinite", b'{"schema":NaN}', "non-finite"),
            ("nonobject", b'[]', "not a JSON object"),
        ):
            with self.subTest(label=label), self.assertRaisesRegex(
                subject.ProtocolError, message,
            ):
                subject.decode_object(encoded, "hostile value")
        with self.assertRaises(ValueError):
            subject.canonical_json_bytes({"value": math.nan})

    def test_schema_v2_artifact_chain_is_disjoint_and_rejected(self) -> None:
        bundle = self.bundle
        cases = (
            ("plan", subject.validate_raw_plan, ()),
            ("request", subject.validate_raw_request, (bundle["plan"],)),
            (
                "transcript", subject.validate_raw_transcript,
                (bundle["plan"], bundle["request"]),
            ),
            (
                "native_execution_closure",
                subject.validate_native_execution_closure,
                (bundle["plan"], bundle["request"], bundle["transcript"]),
            ),
        )
        for name, validator, dependencies in cases:
            for field in ("schema", "kind"):
                forged = copy.deepcopy(bundle[name])
                if field == "schema":
                    forged[field] = 2
                else:
                    self.assertTrue(forged[field].endswith("-v3"))
                    forged[field] = forged[field][:-1] + "2"
                with self.subTest(name=name, field=field), self.assertRaises(
                    subject.ProtocolError,
                ):
                    validator(forged, *dependencies)

    def test_plan_rejects_type_role_environment_action_and_lp_attacks(self) -> None:
        mutations = (
            ("schema v1", lambda item: item.update(schema=1)),
            (
                "authority policy v2",
                lambda item: item["authority"].update(
                    policy="exact-clean-project-hol-light-flyspeck-runtime-"
                    "tool-and-input-authority-v2"
                ),
            ),
            ("bool schema", lambda item: item.update(schema=True)),
            ("float schema", lambda item: item.update(schema=1.0)),
            ("bad ordinal", lambda item: item.update(reference_ordinal=3)),
            ("bool ordinal", lambda item: item.update(reference_ordinal=True)),
            ("short nonce", lambda item: item.update(session_nonce="1" * 63)),
            ("checkpoint", lambda item: item.update(process_state_checkpoint={})),
            (
                "serialization present",
                lambda item: item["serialization_environment"].update(present=True),
            ),
            ("thread bool", lambda item: item.update(thread_count=True)),
            ("stdout cap bool", lambda item: item.update(
                retained_stdout_max_bytes=True,
            )),
            ("stdout cap drift", lambda item: item.update(
                retained_stdout_max_bytes=subject.RETAINED_STDOUT_MAX_BYTES - 1,
            )),
            ("stderr cap float", lambda item: item.update(
                retained_stderr_max_bytes=0.0,
            )),
            ("stderr cap drift", lambda item: item.update(
                retained_stderr_max_bytes=1,
            )),
            ("relative retained root", lambda item: item.update(
                retained_input_artifact_root="reference-inputs",
            )),
            ("root retained root", lambda item: item.update(
                retained_input_artifact_root="/",
            )),
            ("double-slash retained root", lambda item: item.update(
                retained_input_artifact_root="//project/reference-inputs",
            )),
            (
                "dirty project",
                lambda item: item["authority"]["repositories"]["project"].update(
                    git_status=" M protocol.py"
                ),
            ),
            (
                "forged tool mode",
                lambda item: item["authority"]["runtime"]["gp"].update(
                    mode="100644"
                ),
            ),
            (
                "PFT authority path",
                lambda item: item["authority"]["producer"]["entrypoint"].update(
                    path="scripts/pft-collector.py"
                ),
            ),
            (
                "arbitrary producer path",
                lambda item: item["authority"]["producer"]["entrypoint"].update(
                    path="scripts/arbitrary-reference-producer.py"
                ),
            ),
            (
                "missing output parser authority",
                lambda item: item["authority"]["producer"].pop("output_parser"),
            ),
            (
                "output parser path drift",
                lambda item: item["authority"]["producer"]["output_parser"].update(
                    path="scripts/other-output-parser.py"
                ),
            ),
            (
                "output parser bool bytes",
                lambda item: item["authority"]["producer"]["output_parser"].update(
                    bytes=True
                ),
            ),
            (
                "missing direct-release protocol authority",
                lambda item: item["authority"]["producer"].pop(
                    "direct_release_protocol"
                ),
            ),
            (
                "direct-release protocol path drift",
                lambda item: item["authority"]["producer"]
                ["direct_release_protocol"].update(
                    path="scripts/permissive-direct-release-protocol.py"
                ),
            ),
            (
                "direct-release protocol bool bytes",
                lambda item: item["authority"]["producer"]
                ["direct_release_protocol"].update(bytes=True),
            ),
            (
                "root repository path",
                lambda item: item["authority"]["repositories"]["project"].update(
                    path="/"
                ),
            ),
            (
                "missing action",
                lambda item: item["actions"]["records"].pop(),
            ),
            (
                "bool action bytes",
                lambda item: item["actions"]["records"][0].update(
                    original_bytes=True
                ),
            ),
            (
                "LP wrapper position drift",
                lambda item: item["actions"]["records"][177].update(
                    selected_source="flyspeck:text_formalization/fixture/drift.hl",
                    target="fixture/drift.hl",
                ),
            ),
            (
                "missing LP input",
                lambda item: item["lp_certificate_inputs"]["records"].pop(),
            ),
            (
                "bool LP bytes",
                lambda item: item["lp_certificate_inputs"]["records"][0].update(
                    bytes=True
                ),
            ),
            ("PFT bit", lambda item: item.update(pft_used=True)),
            ("approval bit", lambda item: item.update(approval_included=True)),
        )
        for label, mutate in mutations:
            forged = copy.deepcopy(self.bundle["plan"])
            mutate(forged)
            with self.subTest(label=label), self.assertRaises(subject.ProtocolError):
                subject.validate_raw_plan(forged)

    def test_request_rejects_splices_and_entrypoint_drift(self) -> None:
        plan = self.bundle["plan"]
        mutations = (
            ("schema v1", lambda item: item.update(schema=1)),
            ("plan content", lambda item: item["plan"].update(sha256="0" * 64)),
            ("nonce", lambda item: item.update(session_nonce="2" * 64)),
            (
                "entrypoint",
                lambda item: item["entrypoint_sequence"][4].update(
                    after_action_index=178
                ),
            ),
            (
                "entrypoint bool index",
                lambda item: item["entrypoint_sequence"][0].update(index=False),
            ),
            (
                "entrypoint integer success flag",
                lambda item: item["entrypoint_sequence"][4].update(
                    emit_only_after_success=1
                ),
            ),
            (
                "serialization",
                lambda item: item["serialization_environment"].update(present=True),
            ),
            (
                "serialization integer false",
                lambda item: item["serialization_environment"].update(present=0),
            ),
            (
                "marker integer true",
                lambda item: item["marker_contract"].update(
                    nonce_in_every_marker=1
                ),
            ),
            ("action bool", lambda item: item.update(action_count=True)),
            ("stdout cap bool", lambda item: item.update(
                retained_stdout_max_bytes=True,
            )),
            ("stdout cap drift", lambda item: item.update(
                retained_stdout_max_bytes=subject.RETAINED_STDOUT_MAX_BYTES - 1,
            )),
            ("stderr cap float", lambda item: item.update(
                retained_stderr_max_bytes=0.0,
            )),
            ("retained root drift", lambda item: item.update(
                retained_input_artifact_root="/project/other-inputs",
            )),
            ("checkpoint", lambda item: item.update(process_state_checkpoint={})),
            ("approval", lambda item: item.update(approval_included=True)),
            (
                "missing native marker",
                lambda item: item["marker_contract"].pop("native_load"),
            ),
            (
                "v1 native marker",
                lambda item: item["marker_contract"].update(
                    native_load="CANDLE_PRISTINE_DIRECT_NATIVE_LOAD_V1"
                ),
            ),
            ("extra", lambda item: item.update(extra=False)),
        )
        for label, mutate in mutations:
            forged = copy.deepcopy(self.bundle["request"])
            mutate(forged)
            with self.subTest(label=label), self.assertRaises(subject.ProtocolError):
                subject.validate_raw_request(forged, plan)

    def test_transcript_rejects_process_action_and_lp_attacks(self) -> None:
        plan = self.bundle["plan"]
        request = self.bundle["request"]

        def recompute_actions(item: dict) -> None:
            records = item["action_completions"]["records"]
            item["action_completions"]["record_count"] = len(records)
            item["action_completions"]["ordered_record_sha256"] = (
                subject.canonical_sha256(records)
            )

        def recompute_lp(item: dict) -> None:
            records = item["lp_successes"]["records"]
            item["lp_successes"]["record_count"] = len(records)
            item["lp_successes"]["ordered_record_sha256"] = (
                subject.canonical_sha256(records)
            )

        def omit_action(item: dict) -> None:
            item["action_completions"]["records"].pop()
            recompute_actions(item)

        def omit_lp(item: dict) -> None:
            item["lp_successes"]["records"].pop()
            recompute_lp(item)

        mutations = (
            ("exit bool", lambda item: item.update(exit_code=False)),
            ("exit float", lambda item: item.update(exit_code=0.0)),
            ("timeout", lambda item: item.update(timed_out=True)),
            ("no complete", lambda item: item.update(session_completed=False)),
            ("request splice", lambda item: item["request"].update(sha256="0" * 64)),
            ("missing action", omit_action),
            (
                "reordered action",
                lambda item: item["action_completions"]["records"].__setitem__(
                    slice(0, 2), list(reversed(
                        item["action_completions"]["records"][:2]
                    ))
                ),
            ),
            (
                "ledger discontinuity",
                lambda item: item["action_completions"]["records"][1].update(
                    ledger_start_index=999
                ),
            ),
            (
                "action marker nonce",
                lambda item: item["action_completions"]["records"][0].update(
                    session_nonce="0" * 64
                ),
            ),
            ("missing LP", omit_lp),
            (
                "LP input duplicate",
                lambda item: item["lp_successes"]["records"][1].update(
                    input_index=item["lp_successes"]["records"][0]["input_index"]
                ),
            ),
            (
                "LP success bool",
                lambda item: item["lp_successes"]["records"][0].update(
                    successful_deserialization_count=True
                ),
            ),
            (
                "LP marker nonce",
                lambda item: item["lp_successes"]["records"][0].update(
                    session_nonce="0" * 64
                ),
            ),
            ("approval", lambda item: item.update(approval_included=True)),
        )
        for label, mutate in mutations:
            forged = copy.deepcopy(self.bundle["transcript"])
            mutate(forged)
            with self.subTest(label=label), self.assertRaises(subject.ProtocolError):
                subject.validate_raw_transcript(forged, plan, request)

    def test_native_closure_rejects_controls_splices_and_ledger_forgery(self) -> None:
        plan = self.bundle["plan"]
        request = self.bundle["request"]
        transcript = self.bundle["transcript"]

        def rehash_events(item: dict) -> None:
            item["ordered_loader_event_sha256"] = subject.canonical_sha256(
                item["loader_events"]
            )

        def reverse_final_observations(item: dict) -> None:
            final_target, serializer = item["loader_events"][-2:]
            for field in ("logical_source", "basename", "bytes", "sha256", "md5"):
                final_target[field], serializer[field] = (
                    serializer[field], final_target[field]
                )
            rehash_events(item)

        def reverse_bootstrap_anchors(item: dict) -> None:
            hol_light, strictbuild = item["loader_events"][:2]
            for field in ("logical_source", "basename", "bytes", "sha256", "md5"):
                hol_light[field], strictbuild[field] = (
                    strictbuild[field], hol_light[field]
                )
            rehash_events(item)

        def mutate_serializer_md5(item: dict) -> None:
            item["loader_events"][-1]["md5"] = "c" * 32
            rehash_events(item)

        mutations = [
            ("transcript splice", lambda item: item["transcript"].update(
                sha256="0" * 64
            )),
            ("parentage overclaim", lambda item: item.update(
                loader_parentage_observed=True
            )),
            ("cache overclaim", lambda item: item.update(
                loader_cache_outcomes_observed=True
            )),
            ("action binding", lambda item: item["action_bindings"]["records"][0].update(
                selected_ledger_index=0
            )),
            (
                "action binding bool index",
                lambda item: item["action_bindings"]["records"][0].update(
                    index=False
                ),
            ),
            ("event count bool", lambda item: item.update(loader_event_count=True)),
            ("loader event nonce", lambda item: item["loader_events"][0].update(
                session_nonce="0" * 64
            )),
            ("missing post event", lambda item: item["loader_events"].pop()),
            ("reversed bootstrap anchors", reverse_bootstrap_anchors),
            ("reversed final observations", reverse_final_observations),
            ("serializer MD5", mutate_serializer_md5),
            ("LP stream", lambda item: item["lp_successes"]["records"][0].update(
                successful_deserialization_count=0
            )),
            ("unsupported identity", lambda item: item.update(
                unsupported_identity_count=1
            )),
        ]
        for excluded in subject.CANDLE_ONLY_REFERENCE_EXCLUSIONS:
            def replace(item: dict, key: str = excluded) -> None:
                event = item["loader_events"][0]
                event["logical_source"] = key
                event["basename"] = PurePathName(key)
                rehash_events(item)
            mutations.append((f"excluded {excluded}", replace))
        for label, mutate in mutations:
            forged = copy.deepcopy(self.bundle["native_execution_closure"])
            mutate(forged)
            with self.subTest(label=label), self.assertRaises(subject.ProtocolError):
                subject.validate_native_execution_closure(
                    forged, plan, request, transcript,
                )

    def test_candidate_surface_is_unconditionally_unavailable_in_this_slice(self) -> None:
        bundle = self.bundle
        arguments = (
            bundle["plan"], bundle["request"], bundle["transcript"],
            bundle["native_execution_closure"], bundle["semantic_projection"],
            bundle["cross_runtime_coverage"],
        )
        for label, candidate in (
            ("legacy-shaped", copy.deepcopy(bundle["candidate"])),
            ("empty", {}),
            ("approval relabel", {"approved_reference_present": True}),
        ):
            with self.subTest(label=label), self.assertRaisesRegex(
                subject.ProtocolError, "future held collector",
            ):
                subject.validate_raw_candidate(candidate, *arguments)
        encoded = subject.canonical_json_bytes(bundle["candidate"])
        for label, data in (
            ("canonical legacy shape", encoded),
            ("malformed", b"not-json"),
            ("nested coercion", b'{"candidate":{"schema":true}}\n'),
            ("mutable bytes", bytearray(encoded)),
        ):
            with self.subTest(label=label), self.assertRaisesRegex(
                subject.ProtocolError, "decoding is disabled",
            ):
                subject.validate_canonical_raw_candidate_bytes(data, *arguments)
        with mock.patch.object(
            subject, "decode_object",
            side_effect=AssertionError("disabled surface must not decode"),
        ):
            with self.assertRaisesRegex(subject.ProtocolError, "decoding is disabled"):
                subject.validate_canonical_raw_candidate_bytes(encoded, *arguments)

    def test_value_only_pair_consumption_is_unavailable(self) -> None:
        first = bundle_fixture(1, "1" * 64, common=self.common)
        second = bundle_fixture(2, "2" * 64, common=self.common)
        with self.assertRaisesRegex(subject.ProtocolError, "descriptor-rooted"):
            subject.validate_distinct_reference_pair(first, second)


if __name__ == "__main__":
    unittest.main()
