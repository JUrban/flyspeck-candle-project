#!/usr/bin/python3

from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import struct
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
        unbounded_v3 = copy.deepcopy(bundle["plan"])
        unbounded_v3["authority"]["producer"]["output_parser"]["bytes"] = 10**20
        self.assertIs(subject.validate_raw_plan(unbounded_v3), unbounded_v3)
        self.assertEqual(
            subject.validate_canonical_raw_plan_bytes(
                subject.canonical_json_bytes(unbounded_v3),
            ),
            unbounded_v3,
        )
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
        self.assertEqual(subject.V4_AUTHORITY_CAPSULE_MAX_BYTES, 721_420_288)
        self.assertEqual(
            subject.V4_AUTHORITY_CAPSULE_READ_MAX_BYTES, 721_420_289,
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
            "V4_AUTHORITY_CAPSULE_DECODED_MAX_BYTES": 537_919_488,
            "V4_REQUEST_RESULT_HEADER_BYTES": 38,
            "V4_COLLECTION_FRAME_MAX_BYTES": 402_653_396,
            "V4_SOURCE_TREE_MEMBER_MAX": 65_536,
            "V4_SOURCE_TREE_TOTAL_MAX_BYTES": 4_294_967_296,
            "V4_BUILD_INPUT_CLOSURE_ENTRY_MAX": 196_608,
            "V4_BUILD_INPUT_CLOSURE_FILE_MAX_BYTES": 1_073_741_824,
            "V4_BUILD_INPUT_CLOSURE_TOTAL_MAX_BYTES": 68_719_476_736,
            "V4_BUILD_EXECUTION_TASK_MAX": 4_096,
            "V4_BUILD_EXECUTION_EVENT_MAX": 131_072,
            "V4_BUILD_SOURCE_JOIN_MAX": 4_096,
            "V4_BUILD_OUTPUT_JOIN_MAX": 4_096,
            "V4_BUILD_OUTPUT_GENERATION_MAX": 4_096,
            "V4_BUILD_FD_PER_TABLE_MAX": 4_096,
            "V4_BUILD_VMA_PER_ADDRESS_SPACE_MAX": 65_536,
            "V4_BUILD_TRANSITION_PER_EVENT_MAX": 8_194,
            "V4_BUILD_TRANSITION_TOTAL_MAX": 524_288,
            "V4_NATIVE_BUILD_RECEIPT_MAX_BYTES": 134_217_728,
            "V4_NATIVE_BUILD_RECEIPT_READ_MAX_BYTES": 134_217_729,
            "V4_INVENTORY_OBJECT_MAX": 131_072,
            "V4_INVENTORY_TOTAL_MAX_BYTES": 68_719_476_736,
            "V4_NAMESPACE_EDGE_MAX": 16_384,
            "V4_POSTFLIGHT_MAPPING_MAX": 262_144,
            "V4_EMPTY_STDIN_EVENT_MAX": 4_096,
        }
        for name, expected in caps.items():
            with self.subTest(name=name):
                self.assertEqual(getattr(subject, name), expected)

        self.assertEqual(subject.V4_BUILD_FILTER_ERRNO, 1)
        self.assertTrue({16, 40, 275, 276, 278, 317, 326}.issubset({
            number for number, _ in subject.V4_BUILD_FILTER_DENIED_SYSCALLS
        }))
        self.assertEqual(subject.V4_BUILD_FILTER_CLONE_SYSCALL, 56)
        self.assertEqual(
            subject.V4_BUILD_FILTER_CLONE_REJECT_MASK, 0xFEDFBE80,
        )
        self.assertEqual(
            subject.V4_BUILD_FILTER_CLONE_ALLOWED_LOW_MASK, 0x0120417F,
        )
        self.assertEqual(
            subject.V4_BUILD_FILTER_CLONE_REJECT_MASK
            ^ subject.V4_BUILD_FILTER_CLONE_ALLOWED_LOW_MASK,
            0xFFFF_FFFF,
        )
        for hostile_flag in (
            0x0000_0800,  # CLONE_SIGHAND
            0x0000_1000,  # CLONE_PIDFD
            0x0001_0000,  # CLONE_THREAD
            0x0010_0000,  # CLONE_PARENT_SETTID
        ):
            self.assertEqual(
                hostile_flag & subject.V4_BUILD_FILTER_CLONE_REJECT_MASK,
                hostile_flag,
            )
        for profile in subject.V4_BUILD_CLONE_PROFILES:
            self.assertEqual(
                (profile[1] & 0xFFFF_FFFF)
                & subject.V4_BUILD_FILTER_CLONE_REJECT_MASK,
                0,
            )
        self.assertEqual(
            tuple(number for number, _ in subject.V4_BUILD_FILTER_DENIED_SYSCALLS),
            tuple(sorted(
                number
                for number, _ in subject.V4_BUILD_FILTER_DENIED_SYSCALLS
            )),
        )
        self.assertEqual(subject.V4_BUILD_PTRACE_OPTIONS, (
            "PTRACE_O_TRACESYSGOOD",
            "PTRACE_O_TRACEFORK",
            "PTRACE_O_TRACEVFORK",
            "PTRACE_O_TRACECLONE",
            "PTRACE_O_TRACEVFORKDONE",
            "PTRACE_O_TRACEEXEC",
            "PTRACE_O_TRACEEXIT",
            "PTRACE_O_EXITKILL",
        ))
        self.assertEqual(subject.V4_BUILD_EXECUTION_OBSERVATION_SCHEMA, 4)
        self.assertEqual(subject.V4_BUILD_FILTER_SCHEMA, 5)
        self.assertEqual(subject.V4_BUILD_SYSCALL_DISPOSITION_SCHEMA, 4)
        self.assertNotIn(
            "max_fds", subject.V4_BUILD_INITIAL_FD_TABLE_CONTAINER_FIELDS,
        )
        self.assertFalse(hasattr(
            subject, "enumerate_isolated_native_build_filter_v1",
        ))
        self.assertFalse(hasattr(
            subject, "enumerate_isolated_native_build_filter_v2",
        ))
        self.assertFalse(hasattr(
            subject, "enumerate_isolated_native_build_filter_v3",
        ))
        self.assertFalse(hasattr(
            subject, "enumerate_isolated_native_build_filter_v4",
        ))
        self.assertTrue({
            "paired_event_index", "object_edges", "fd_transitions",
            "mapping_transitions", "fs_transitions", "task_transitions",
        }.issubset(subject.V4_BUILD_EVENT_FIELDS))
        self.assertNotIn("exec-tid-rebase", subject.V4_BUILD_EVENT_KINDS)
        self.assertEqual(
            subject.V4_BUILD_EVENT_TAGGED_NONNULL_FIELDS["namespace-clone"],
            (
                "subject_task_identity", "return_value",
            ),
        )
        self.assertTrue(set(
            subject.V4_BUILD_EVENT_ALWAYS_NONNULL_FIELDS
        ).issubset(subject.V4_BUILD_EVENT_NONNULL_FIELDS["syscall-exit"]))
        self.assertEqual(
            set(subject.V4_BUILD_ENTRY_CAPTURE_FIELDS),
            {
                "scalar-entry", "path-entry", "exec-entry", "fd-io-entry",
                "mapping-entry", "fd-control-entry", "task-create-entry",
                "seccomp-install-entry", "query-entry", "mount-entry",
            },
        )
        self.assertIn("query-exit", subject.V4_BUILD_EXIT_CAPTURE_FIELDS)
        self.assertIn(
            "paired_event_index",
            subject.V4_BUILD_EVENT_TAGGED_NONNULL_FIELDS["exit"],
        )
        self.assertEqual(
            set(subject.V4_BUILD_TASK_TRANSITION_FIELDS),
            {
                "builder-create", "observer-attached-stop", "child-create",
                "child-attached-stop", "vfork-hold", "vfork-release",
                "group-listen", "exec-image", "exit-stop", "wait-consumed",
                "credential-update", "capability-sets-update",
                "no-new-privileges-change", "seccomp-change",
                "signal-disposition-change", "signal-mask-change",
                "signal-altstack-change", "tls-base-change",
                "child-tid-registration-change", "robust-list-change",
                "rseq-registration-change", "tracee-wait-consume",
            },
        )
        self.assertEqual(
            subject.V4_BUILD_PEER_SHARED_STATE_KINDS,
            ("address-space", "fd-table", "fs-state"),
        )
        self.assertEqual(
            tuple(item[0] for item in subject.V4_BUILD_OUTPUT_MUTATING_SYSCALLS),
            tuple(sorted(
                item[0] for item in subject.V4_BUILD_OUTPUT_MUTATING_SYSCALLS
            )),
        )
        self.assertEqual(
            tuple(
                (item[0], item[1])
                for item in subject.V4_BUILD_OUTPUT_OPERATION_CAPTURE_POLICY
            ),
            tuple(
                (item[0], item[1])
                for item in subject.V4_BUILD_OUTPUT_MUTATING_SYSCALLS
            ),
        )
        self.assertEqual(
            len(subject.V4_BUILD_OUTPUT_OPERATION_CAPTURE_POLICY_FIELDS), 9,
        )
        modeled_numbers = {
            item[0]
            for item in subject.V4_BUILD_OUTPUT_OPERATION_CAPTURE_POLICY
        } | {
            item[0]
            for item in subject.V4_BUILD_STATE_OPERATION_CAPTURE_POLICY
        }
        stateless_numbers = {
            item[0] for item in subject.V4_BUILD_STATELESS_ALLOWED_SYSCALLS
        }
        exec_numbers = {item[0] for item in subject.V4_BUILD_EXEC_SYSCALLS}
        control_numbers = {
            item[0] for item in subject.V4_BUILD_CONTROL_OPERATION_CAPTURE_POLICY
        }
        nonreturning_numbers = {
            item[0] for item in subject.V4_BUILD_NONRETURNING_SYSCALLS
        }
        filter_result_numbers = {
            item[0]
            for item in subject.V4_BUILD_FILTER_RESULT_OPERATION_CAPTURE_POLICY
        }
        self.assertFalse(modeled_numbers & stateless_numbers)
        self.assertFalse(modeled_numbers & exec_numbers)
        self.assertFalse(modeled_numbers & control_numbers)
        self.assertFalse(modeled_numbers & nonreturning_numbers)
        self.assertFalse(stateless_numbers & exec_numbers)
        self.assertFalse(stateless_numbers & control_numbers)
        self.assertFalse(stateless_numbers & nonreturning_numbers)
        self.assertFalse(exec_numbers & nonreturning_numbers)
        self.assertFalse(control_numbers & nonreturning_numbers)
        self.assertFalse(filter_result_numbers & modeled_numbers)
        self.assertFalse(filter_result_numbers & stateless_numbers)
        self.assertFalse(filter_result_numbers & exec_numbers)
        self.assertFalse(filter_result_numbers & control_numbers)
        self.assertFalse(filter_result_numbers & nonreturning_numbers)
        self.assertEqual(filter_result_numbers, {435})
        self.assertEqual(
            subject.V4_BUILD_FILTER_RESULT_OPERATION_CAPTURE_POLICY[0][2:5],
            ("scalar-entry", "scalar-exit", -38),
        )
        self.assertEqual(
            control_numbers, {13, 14, 61, 73, 131, 158, 218, 273, 334},
        )
        self.assertEqual(
            {item[0] for item in subject.V4_BUILD_REJECTED_CONTROL_SYSCALLS},
            {15, 62, 202, 219, 234},
        )
        self.assertEqual(
            {item[0] for item in subject.V4_BUILD_PRCTL_ALLOWED_OPERATIONS},
            {21, 39},
        )
        self.assertEqual(nonreturning_numbers, {60, 231})
        self.assertTrue({0, 3, 8, 17, 19, 28, 32, 33, 72, 80, 81, 95,
                         217, 292, 295, 327, 436}.issubset(modeled_numbers))
        self.assertEqual(
            tuple(item[0] for item in subject.V4_BUILD_STATE_OPERATION_CAPTURE_POLICY),
            tuple(sorted(
                item[0]
                for item in subject.V4_BUILD_STATE_OPERATION_CAPTURE_POLICY
            )),
        )
        self.assertEqual(
            tuple(item[0] for item in subject.V4_BUILD_STATELESS_ALLOWED_SYSCALLS),
            tuple(sorted(
                item[0] for item in subject.V4_BUILD_STATELESS_ALLOWED_SYSCALLS
            )),
        )
        self.assertEqual(
            tuple(
                (item[0], item[1])
                for item in subject.V4_BUILD_STATELESS_OPERATION_CAPTURE_POLICY
            ),
            subject.V4_BUILD_STATELESS_ALLOWED_SYSCALLS,
        )
        self.assertIn(277, stateless_numbers)
        self.assertNotIn(60, stateless_numbers)
        self.assertNotIn(231, stateless_numbers)
        for table in (
            subject.V4_BUILD_STATELESS_OPERATION_CAPTURE_POLICY,
            subject.V4_BUILD_CONTROL_OPERATION_CAPTURE_POLICY,
        ):
            for row in table:
                for regions in (row[5], row[6]):
                    for region in regions:
                        self.assertEqual(
                            len(region),
                            len(subject.V4_BUILD_QUERY_ABI_REGION_POLICY_FIELDS),
                        )
                        self.assertIn(
                            region[2], subject.V4_BUILD_QUERY_ABI_LENGTH_KINDS,
                        )
                        self.assertIn(
                            region[4], subject.V4_BUILD_QUERY_ABI_CONDITIONS,
                        )
                        self.assertIn(
                            region[5],
                            subject.V4_BUILD_QUERY_ABI_POST_LENGTH_KINDS,
                        )
        for _, input_regions, output_regions in (
            subject.V4_BUILD_SETUP_QUERY_REGION_POLICY
        ):
            for region in input_regions + output_regions:
                self.assertEqual(
                    len(region),
                    len(subject.V4_BUILD_QUERY_ABI_REGION_POLICY_FIELDS),
                )
        for table, cardinality_start in (
            (subject.V4_BUILD_OUTPUT_OPERATION_CAPTURE_POLICY, 4),
            (subject.V4_BUILD_STATE_OPERATION_CAPTURE_POLICY, 4),
            (subject.V4_BUILD_PTRACE_EVENT_TRANSITION_POLICY, 1),
            (subject.V4_BUILD_STATELESS_OPERATION_CAPTURE_POLICY, 7),
            (subject.V4_BUILD_CONTROL_OPERATION_CAPTURE_POLICY, 7),
            (subject.V4_BUILD_NONRETURNING_CAPTURE_POLICY, 4),
            (subject.V4_BUILD_SETUP_OPERATION_CAPTURE_POLICY, 5),
            (subject.V4_BUILD_STATE_CHANGING_FAILURE_POLICY, 4),
        ):
            for row in table:
                for cardinality in row[cardinality_start:]:
                    self.assertIn(
                        cardinality[0], {"exact-values", "inclusive-range"},
                    )
                    self.assertEqual(
                        len(cardinality),
                        2 if cardinality[0] == "exact-values" else 3,
                    )
        self.assertTrue({216, 329}.issubset({
            item[0]
            for item in subject.V4_BUILD_REJECTED_OUTPUT_MUTATION_SYSCALLS
        }))
        self.assertEqual(
            {item[0] for item in subject.V4_BUILD_PTRACE_EVENT_TRANSITION_POLICY},
            set(subject.V4_BUILD_EVENT_KINDS) - {"syscall-entry", "syscall-exit"},
        )
        self.assertIn(
            "open-description-offset-change",
            subject.V4_BUILD_FD_TRANSITION_FIELDS,
        )
        self.assertEqual(
            subject.V4_BUILD_OBJECT_EDGE_DOMAINS,
            ("input-root-entry", "output-generation", "output-root"),
        )
        self.assertEqual(
            subject.V4_BUILD_OUTPUT_GENERATION_FINAL_STATES,
            ("published", "deleted"),
        )
        self.assertIn(
            "st_nlink", subject.V4_BUILD_INPUT_CLOSURE_ENTRY_FIELDS,
        )
        self.assertIn(
            "st_nlink", subject.V4_BUILD_INPUT_CLOSURE_OBSERVED_ENTRY_FIELDS,
        )
        self.assertEqual(
            subject.V4_BUILD_INITIAL_STATE_CAPTURE_BOUNDARY,
            "held-interrupt-stop-after-id-maps-before-builder-gate-release-v1",
        )
        self.assertIn(
            "initial_object_edges", subject.V4_BUILD_INITIAL_STATE_SEED_FIELDS,
        )
        self.assertIn(
            "builder_interrupt_stop_event_index",
            subject.V4_BUILD_INITIAL_STATE_SEED_FIELDS,
        )
        self.assertIn(
            "securebits", subject.V4_BUILD_INITIAL_CREDENTIAL_FIELDS,
        )
        securebits_policy = next(
            row for row in subject.V4_BUILD_CREDENTIAL_SCALAR_POLICY
            if row[0] == "securebits"
        )
        self.assertEqual(securebits_policy[2], ("exact-values", 0))
        self.assertIn("clone-newuser", securebits_policy[3])
        self.assertEqual(
            subject.V4_BUILD_INITIAL_STATE_DIGEST_DOMAIN,
            "candle-flyspeck-v4-initial-state-seed-v2",
        )
        self.assertEqual(
            subject.V4_BUILD_INITIAL_STATE_DIGEST_PREIMAGE,
            "ascii-domain-nul-canonical-json-array-of-ordered-field-values-v1",
        )
        self.assertEqual(
            subject.V4_BUILD_SETUP_STATE_DIGEST_PREIMAGE,
            "ascii-domain-nul-canonical-json-array-of-ordered-field-values-v1",
        )
        self.assertEqual(
            subject.V4_BUILD_NESTED_VALUE_POLICY_FIELDS,
            ("name", "fields", "exact_rules"),
        )
        self.assertEqual(
            {row[0] for row in subject.V4_BUILD_NESTED_VALUE_POLICY},
            {
                "lock-state", "supplementary-groups", "capability-set",
                "capability-sets", "signal-set", "signal-action",
                "signal-altstack", "robust-list-registration",
                "rseq-registration", "mount-propagation",
            },
        )
        self.assertEqual(subject.V4_BUILD_SIGNAL_DISPOSITION_COUNT, 64)
        self.assertEqual(subject.V4_BUILD_SUPPLEMENTARY_GROUP_MAX, 65_536)
        self.assertEqual(
            {row[0] for row in subject.V4_BUILD_INITIAL_STATE_CONTAINER_POLICY},
            {
                "initial_object_edges", "parent_fd_table",
                "parent_open_descriptions", "parent_mappings",
                "parent_mount_graph", "builder_mount_graph",
            },
        )
        self.assertIn(
            "mount-namespace-create", subject.V4_BUILD_FS_TRANSITION_FIELDS,
        )
        self.assertEqual(
            subject.V4_BUILD_MOUNT_GRAPH_ENTRY_FIELDS[-2:],
            ("propagation", "user_namespace_locked"),
        )
        self.assertIn(
            "mountinfo_payload_base64",
            subject.V4_BUILD_MOUNT_GRAPH_CONTAINER_FIELDS,
        )
        self.assertEqual(
            {row[0] for row in subject.V4_BUILD_MOUNT_PROPAGATION_COPY_POLICY},
            {"private", "shared", "slave", "shared-slave", "unbindable"},
        )
        self.assertIn("nsfs", subject.V4_BUILD_MOUNT_NAMESPACE_FILE_POLICY)
        self.assertIn("shared-to-slave", subject.V4_BUILD_MOUNT_USERNS_COPY_POLICY)
        self.assertIn(
            "only-null-normalized-parent",
            subject.V4_BUILD_MOUNT_ROOT_PARENT_POLICY,
        )
        namespace_clone = next(
            row for row in subject.V4_BUILD_PTRACE_EVENT_TRANSITION_POLICY
            if row[0] == "namespace-clone"
        )
        self.assertEqual(namespace_clone[4], ("exact-values", 2))
        self.assertEqual(subject.V4_BUILD_SETUP_FINAL_FDS, (0, 1, 2))
        self.assertEqual(
            dict(subject.V4_BUILD_SETUP_CREDENTIAL_TARGETS)["select-mapped-uid"],
            ("real_uid", "effective_uid", "saved_uid", "fsuid"),
        )
        self.assertEqual(
            dict(subject.V4_BUILD_SETUP_CAPABILITY_TARGETS)["drop-capabilities"],
            ("effective", "permitted", "inheritable"),
        )
        self.assertEqual(len(subject.V4_BUILD_SETUP_SEQUENCE_FIELDS), 4)
        self.assertEqual(
            tuple(step[0] for step in subject.V4_BUILD_SETUP_SEQUENCE),
            tuple(range(len(subject.V4_BUILD_SETUP_SEQUENCE))),
        )
        self.assertEqual(subject.V4_BUILD_SETUP_SEQUENCE[-1][1],
                         "install-build-filter")
        self.assertEqual(
            tuple(row[0] for row in subject.V4_BUILD_SETUP_OPERATION_CAPTURE_POLICY),
            tuple(step[1] for step in subject.V4_BUILD_SETUP_SEQUENCE),
        )
        for row in subject.V4_BUILD_SETUP_OPERATION_CAPTURE_POLICY:
            self.assertIn(
                row[4][0], subject.V4_BUILD_SETUP_OCCURRENCE_SPEC_TAGS,
            )
        self.assertEqual(subject.V4_BUILD_MREMAP_ALLOWED_FLAGS, (0, 1, 3))
        self.assertIn(4, subject.V4_BUILD_MREMAP_REJECTED_FLAGS)
        self.assertIn("reject-zero", subject.V4_BUILD_MREMAP_OLD_SIZE_POLICY)
        self.assertEqual(
            tuple(row[1] for row in subject.V4_BUILD_CLONE_PROFILES),
            (0x11, 0x01200011, 0x00004111),
        )
        self.assertTrue(all(
            len(row) == len(subject.V4_BUILD_TASK_CONTROL_DERIVATION_FIELDS)
            for row in subject.V4_BUILD_CLONE_TASK_CONTROL_DERIVATIONS
        ))
        self.assertEqual(
            len(subject.V4_BUILD_EXEC_TASK_CONTROL_DERIVATION),
            len(subject.V4_BUILD_TASK_CONTROL_DERIVATION_FIELDS),
        )
        self.assertEqual(
            tuple(row[1] for row in subject.V4_BUILD_CLONE_TASK_CONTROL_DERIVATIONS),
            tuple(row[0] for row in subject.V4_BUILD_CLONE_PROFILES),
        )
        self.assertIn(
            "preserve-sig-ign",
            subject.V4_BUILD_EXEC_TASK_CONTROL_DERIVATION[2],
        )
        self.assertEqual(
            subject.V4_BUILD_EXIT_GROUP_POLICY,
            "exactly-one-live-thread-group-member-reject-before-resume-v1",
        )
        self.assertIn("thread_group_identity", subject.V4_BUILD_TASK_FIELDS)
        self.assertIn(
            "personality", subject.V4_BUILD_INITIAL_TASK_CONTROL_STATE_FIELDS,
        )
        self.assertEqual(subject.V4_BUILD_PERSONALITY_STICKY_TIMEOUTS, 0x04000000)
        self.assertEqual(
            subject.V4_BUILD_RENAME_EQUAL_OPERAND_POLICY,
            "reject-before-resume-v1",
        )
        self.assertEqual(
            subject.V4_BUILD_STATE_CHANGING_FAILURE_POLICY[0][:3],
            (3, "close", "negative-except-ebadf-after-valid-entry-fd"),
        )
        self.assertTrue(all(
            row[4] != "all-unused-arguments-zero-or-pinned-scalar-abi-exact"
            for row in subject.V4_BUILD_STATELESS_OPERATION_CAPTURE_POLICY
        ))
        self.assertEqual(
            {
                row[0]
                for row in subject.V4_BUILD_SETUP_QUERY_REGION_POLICY
            },
            {
                row[0]
                for row in subject.V4_BUILD_SETUP_OPERATION_CAPTURE_POLICY
                if row[2] == "query-entry"
            },
        )
        mremap = next(
            row for row in subject.V4_BUILD_OUTPUT_OPERATION_CAPTURE_POLICY
            if row[0] == 25
        )
        self.assertEqual(mremap[6], ("inclusive-range", 1, 2))
        self.assertNotIn(
            317,
            {row[0] for row in subject.V4_BUILD_STATE_OPERATION_CAPTURE_POLICY},
        )
        ppoll = next(
            row for row in subject.V4_BUILD_STATELESS_OPERATION_CAPTURE_POLICY
            if row[0] == 271
        )
        self.assertEqual(
            ppoll[6],
            (
                (0, "output", "nfds-times-pollfd-8", 1,
                 "if-nonnull-after-exit", "same-as-entry"),
                (2, "output", "fixed-bytes", 16,
                 "if-valid-nonzero-ppoll-timeout-nonnull", "fixed"),
            ),
        )
        self.assertNotIn(
            23, {row[0] for row in subject.V4_BUILD_STATELESS_ALLOWED_SYSCALLS},
        )
        self.assertEqual(
            subject.V4_BUILD_REJECTED_STATELESS_SYSCALLS,
            ((23, "select-unobservable-kernel-fdtable-capacity"),),
        )
        self.assertIn(
            "reject-at-exit", subject.V4_BUILD_STATELESS_NEGATIVE_RESULT_POLICY,
        )
        self.assertEqual(
            {row[0] for row in subject.V4_BUILD_RLIMIT_RESOURCE_POLICY},
            set(range(16)),
        )
        self.assertEqual(
            {row[0] for row in subject.V4_BUILD_RUSAGE_WHO_POLICY}, {-1, 0, 1},
        )
        self.assertEqual(subject.V4_BUILD_STATX_ALLOWED_MASK, 0x3FFF)
        self.assertEqual(
            {row[0] for row in subject.V4_BUILD_CLOCK_ID_POLICY},
            set(range(10)) | {11},
        )
        self.assertEqual(
            subject.V4_BUILD_RAW_RESTART_RESULTS,
            (
                (-512, "ERESTARTSYS"), (-513, "ERESTARTNOINTR"),
                (-514, "ERESTARTNOHAND"),
                (-516, "ERESTART_RESTARTBLOCK"),
            ),
        )
        self.assertEqual(
            subject.V4_BUILD_NETWORK_LOOPBACK_FIXED_FIELDS,
            {
                "list_index": 0, "ifindex": 1, "name": "lo",
                "mtu": 65_536, "flags": 0x8, "operstate": "down",
            },
        )

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

    def test_v4_ordered_field_digest_framing_is_exact(self) -> None:
        fixtures = (
            (
                subject.V4_BUILD_INITIAL_STATE_DIGEST_FIELDS,
                subject.V4_BUILD_INITIAL_STATE_DIGEST_DOMAIN,
                "bb40e16801e82b82d79b448967fc665ab998355fe61a2067f3006ddf5fce2ef1",
            ),
            (
                subject.V4_BUILD_SETUP_REPLAY_STATE_FIELDS,
                subject.V4_BUILD_SETUP_STATE_DIGEST_DOMAIN,
                "83218cf241caf0f5fac3cc50030de1f56eec683c00e436d33a3a47323ebfef62",
            ),
        )
        for fields, domain, expected in fixtures:
            value = {field: index for index, field in enumerate(fields)}
            self.assertEqual(
                subject.v4_ordered_field_digest(value, fields, domain), expected,
            )
            wrong_order = tuple(reversed(fields))
            self.assertNotEqual(
                subject.v4_ordered_field_digest(value, wrong_order, domain),
                expected,
            )
        with self.assertRaisesRegex(subject.ProtocolError, "domain"):
            subject.v4_ordered_field_digest({"a": 1}, ("a",), "bad\x00domain")
        with self.assertRaisesRegex(subject.ProtocolError, "absent"):
            subject.v4_ordered_field_digest({}, ("a",), "domain")

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
        self.assertEqual(len(values), 378)
        self.assertEqual(
            hashlib.sha256(encoded).hexdigest(),
            "7a41529006e36858f38da8bf88361a72997f7d53e64288bd15e1b239a5182184",
        )

    def test_v4_native_source_tree_leaf_validator(self) -> None:
        class AlwaysEqual:
            def __eq__(self, other: object) -> bool:
                return True

        files = [
            {
                "index": 0,
                "relative": "bin/run.sh",
                "mode": subject.V4_SOURCE_TREE_EXECUTABLE_MODE,
                "bytes": 9,
                "sha256": "1" * 64,
            },
            {
                "index": 1,
                "relative": "src/main.c",
                "mode": subject.V4_SOURCE_TREE_DATA_MODE,
                "bytes": 17,
                "sha256": "2" * 64,
            },
        ]
        tree = {
            "schema": subject.V4_NATIVE_SOURCE_TREE_SCHEMA,
            "kind": subject.V4_NATIVE_SOURCE_TREE_KIND,
            "authority_role": "attempt-supervisor",
            "root_policy": subject.V4_NATIVE_SOURCE_TREE_ROOT_POLICY,
            "file_count": len(files),
            "total_bytes": sum(record["bytes"] for record in files),
            "ordered_file_sha256": subject.canonical_sha256(files),
            "files": files,
        }
        self.assertIs(subject.validate_native_source_tree(tree), tree)
        encoded = subject.canonical_json_bytes(tree)
        self.assertEqual(
            subject.validate_canonical_native_source_tree_bytes(encoded), tree,
        )
        with self.assertRaisesRegex(subject.ProtocolError, "not immutable"):
            subject.validate_canonical_native_source_tree_bytes(bytearray(encoded))
        hostile_json = (
            b'{"x":' + (b"9" * 5000) + b"}",
            b'{"x":' + (b"[" * 1100) + b"0" + (b"]" * 1100) + b"}",
            b'{"x":1e999}',
        )
        for payload in hostile_json:
            with self.subTest(hostile=payload[:20]), self.assertRaises(
                subject.ProtocolError,
            ):
                subject.validate_canonical_native_source_tree_bytes(payload)
        with self.assertRaises(subject.ProtocolError):
            subject.decode_object(b'{"x":1e999}', "hostile exponent")
        with self.assertRaisesRegex(subject.ProtocolError, "not canonical"):
            subject.validate_canonical_native_source_tree_bytes(
                subject.canonical_value_bytes(tree),
            )
        with mock.patch.object(
            subject, "V4_AUTHORITY_OBJECT_MAX_BYTES", len(encoded) - 1,
        ), self.assertRaisesRegex(subject.ProtocolError, "exceeds retained cap"):
            subject.validate_canonical_native_source_tree_bytes(encoded)

        mutations = (
            ("unknown key", lambda item: item.update(extra=False)),
            ("bool schema", lambda item: item.update(schema=True)),
            ("non-JSON kind", lambda item: item.update(kind=AlwaysEqual())),
            (
                "non-JSON role",
                lambda item: item.update(authority_role=AlwaysEqual()),
            ),
            (
                "non-JSON root policy",
                lambda item: item.update(root_policy=AlwaysEqual()),
            ),
            ("wrong kind", lambda item: item.update(kind="source-tree-v0")),
            ("wrong role", lambda item: item.update(authority_role="caller")),
            ("wrong root policy", lambda item: item.update(root_policy="open")),
            ("count mismatch", lambda item: item.update(file_count=3)),
            ("total mismatch", lambda item: item.update(total_bytes=27)),
            (
                "digest mismatch",
                lambda item: item.update(ordered_file_sha256="0" * 64),
            ),
            ("bool index", lambda item: item["files"][0].update(index=True)),
            ("permission-only mode", lambda item: item["files"][0].update(
                mode=365,
            )),
            ("bool mode", lambda item: item["files"][0].update(mode=True)),
            ("zero bytes", lambda item: item["files"][0].update(bytes=0)),
            (
                "oversize file",
                lambda item: item["files"][0].update(
                    bytes=subject.V4_SOURCE_TREE_FILE_MAX_BYTES + 1,
                ),
            ),
            (
                "uppercase digest",
                lambda item: item["files"][0].update(sha256="A" * 64),
            ),
            (
                "duplicate relative",
                lambda item: item["files"][1].update(relative="bin/run.sh"),
            ),
        )
        for label, mutate in mutations:
            forged = copy.deepcopy(tree)
            mutate(forged)
            with self.subTest(label=label), self.assertRaises(
                subject.ProtocolError,
            ):
                subject.validate_native_source_tree(forged)

        with self.assertRaises(subject.ProtocolError):
            subject.validate_native_source_tree(type("Tree", (dict,), {})(tree))

        forged = copy.deepcopy(tree)
        forged["files"] = type("Files", (list,), {})(forged["files"])
        with self.assertRaises(subject.ProtocolError):
            subject.validate_native_source_tree(forged)

        forged = copy.deepcopy(tree)
        forged["files"][0] = type("File", (dict,), {})(forged["files"][0])
        with self.assertRaises(subject.ProtocolError):
            subject.validate_native_source_tree(forged)

        forged = copy.deepcopy(tree)
        forged["files"][0]["relative"] = type("Relative", (str,), {})(
            forged["files"][0]["relative"],
        )
        with self.assertRaises(subject.ProtocolError):
            subject.validate_native_source_tree(forged)

        empty = copy.deepcopy(tree)
        empty["file_count"] = 0
        empty["total_bytes"] = 0
        empty["files"] = []
        empty["ordered_file_sha256"] = subject.canonical_sha256([])
        with self.assertRaises(subject.ProtocolError):
            subject.validate_native_source_tree(empty)

        for relative in (
            "", "/absolute", "a\\b", ".", "a/../b", "a//b",
            "x" * 256, ("a/" * 2048) + "a",
        ):
            forged = copy.deepcopy(tree)
            forged["files"][0]["relative"] = relative
            with self.subTest(relative=relative[:40]), self.assertRaises(
                subject.ProtocolError,
            ):
                subject.validate_native_source_tree(forged)

        for relative in ("pft/solver.c", "src/PFT_bridge.c"):
            forged = copy.deepcopy(tree)
            forged["files"][0]["relative"] = relative
            forged["ordered_file_sha256"] = subject.canonical_sha256(
                forged["files"],
            )
            with self.subTest(relative=relative), self.assertRaisesRegex(
                subject.ProtocolError, "PFT namespace",
            ):
                subject.validate_native_source_tree(forged)

        forged = copy.deepcopy(tree)
        forged["files"].reverse()
        for index, record in enumerate(forged["files"]):
            record["index"] = index
        forged["ordered_file_sha256"] = subject.canonical_sha256(
            forged["files"],
        )
        with self.assertRaisesRegex(subject.ProtocolError, "unordered"):
            subject.validate_native_source_tree(forged)

    def test_v4_native_build_runtime_input_role_classifier(self) -> None:
        cases = {
            "usr/include/stdio.h": "header",
            "usr/include/c++/vector.hpp": "header",
            "usr/lib/crt1.o": "startup-object",
            "usr/lib/layout.lds": "linker-script",
            "usr/lib/libc.a": "static-library",
            "lib/x86_64-linux-gnu/libc.so.6": "shared-library",
            "usr/bin/as": "runtime-data",
            "usr/lib/ordinary.o": "runtime-data",
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(
                    subject.classify_isolated_native_build_runtime_input_v1(
                        path,
                    ),
                    expected,
                )
        for path in (
            "", "/usr/include/a.h", "usr/../include/a.h", "pft/tool.h",
            type("Path", (str,), {})("usr/include/a.h"),
        ):
            with self.subTest(path=path), self.assertRaises(
                subject.ProtocolError,
            ):
                subject.classify_isolated_native_build_runtime_input_v1(path)

    def test_v4_isolated_native_build_root_enumerator(self) -> None:
        compiler = {
            "argument_path": "/usr/bin/cc",
            "resolved_path": "/usr/bin/cc",
            "bytes": 101,
            "sha256": "a" * 64,
            "mode": 0o100755,
            "version": "cc 1.0",
        }
        linker = {
            "argument_path": "/usr/bin/ld",
            "resolved_path": "/usr/bin/ld",
            "bytes": 102,
            "sha256": "b" * 64,
            "mode": 0o100755,
            "version": "ld 1.0",
        }
        files = [{
            "index": 0,
            "relative": "main.c",
            "mode": subject.V4_SOURCE_TREE_DATA_MODE,
            "bytes": 17,
            "sha256": "c" * 64,
        }]
        source_tree = {
            "schema": subject.V4_NATIVE_SOURCE_TREE_SCHEMA,
            "kind": subject.V4_NATIVE_SOURCE_TREE_KIND,
            "authority_role": "attempt-supervisor",
            "root_policy": subject.V4_NATIVE_SOURCE_TREE_ROOT_POLICY,
            "file_count": 1,
            "total_bytes": 17,
            "ordered_file_sha256": subject.canonical_sha256(files),
            "files": files,
        }
        inputs = [
            {
                "index": 0,
                "role": "header",
                "mode": subject.V4_SOURCE_TREE_DATA_MODE,
                "content": {
                    "path": "usr/include/stdio.h",
                    "bytes": 19,
                    "sha256": "d" * 64,
                },
            },
            {
                "index": 1,
                "role": "shared-library",
                "mode": subject.V4_SOURCE_TREE_EXECUTABLE_MODE,
                "content": {
                    "path": "lib/libc.so.6",
                    "bytes": 23,
                    "sha256": "e" * 64,
                },
            },
            {
                "index": 2,
                "role": "runtime-data",
                "mode": subject.V4_SOURCE_TREE_EXECUTABLE_MODE,
                "content": {
                    "path": "usr/bin/as",
                    "bytes": 29,
                    "sha256": "f" * 64,
                },
            },
        ]
        entries = subject.enumerate_isolated_native_build_root_v1(
            compiler, linker, source_tree, inputs,
        )
        self.assertEqual(
            [entry["index"] for entry in entries], list(range(len(entries))),
        )
        by_path = {entry["relative"]: entry for entry in entries}
        self.assertEqual(
            by_path[subject.V4_BUILD_OUTPUT_DIRECTORY]["mode"],
            subject.V4_DIRECTORY_0700_MODE,
        )
        self.assertEqual(
            by_path[subject.V4_BUILD_OLD_ROOT_DIRECTORY]["mode"],
            subject.V4_BUILD_READONLY_DIRECTORY_MODE,
        )
        self.assertEqual(by_path["usr/bin/cc"]["mode"], 0o100555)
        self.assertEqual(
            by_path["usr/bin/cc"]["selector"], {"kind": "build-compiler"},
        )
        self.assertEqual(
            by_path["candle-source/main.c"]["selector"],
            {"kind": "source-tree-member", "member_index": 0},
        )
        self.assertEqual(
            by_path["lib/libc.so.6"]["selector"],
            {"kind": "build-runtime-input", "input_index": 1},
        )
        self.assertTrue(all(
            entry["sha256"] == subject.EMPTY_BYTES_SHA256
            for entry in entries if entry["object_type"] == "directory"
        ))

        mutations = (
            (
                "misclassified input",
                lambda c, l, s, items: items[0].update(role="runtime-data"),
            ),
            (
                "reserved input path",
                lambda c, l, s, items: items[0]["content"].update(
                    path="candle-output/header.h",
                ),
            ),
            (
                "unordered input",
                lambda c, l, s, items: items.reverse(),
            ),
            (
                "compiler/output collision",
                lambda c, l, s, items: c.update(
                    argument_path="/candle-output/cc",
                    resolved_path="/candle-output/cc",
                ),
            ),
            (
                "runtime/old-root collision",
                lambda c, l, s, items: items[0]["content"].update(
                    path=".candle-old-root/helper",
                ),
            ),
            (
                "compiler/linker collision",
                lambda c, l, s, items: l.update(
                    argument_path=c["argument_path"],
                    resolved_path=c["resolved_path"],
                ),
            ),
            (
                "file ancestor collision",
                lambda c, l, s, items: c.update(
                    argument_path="/usr",
                    resolved_path="/usr",
                ),
            ),
        )
        for label, mutate in mutations:
            forged = (
                copy.deepcopy(compiler), copy.deepcopy(linker),
                copy.deepcopy(source_tree), copy.deepcopy(inputs),
            )
            mutate(*forged)
            with self.subTest(label=label), self.assertRaises(
                subject.ProtocolError,
            ):
                subject.enumerate_isolated_native_build_root_v1(*forged)

        forged_inputs = type("Inputs", (list,), {})(copy.deepcopy(inputs))
        with self.assertRaises(subject.ProtocolError):
            subject.enumerate_isolated_native_build_root_v1(
                compiler, linker, source_tree, forged_inputs,
            )

        prefixed_oversize = copy.deepcopy(source_tree)
        prefixed_oversize["files"][0]["relative"] = "/".join(
            ["a" * 255] * 16,
        )
        prefixed_oversize["ordered_file_sha256"] = subject.canonical_sha256(
            prefixed_oversize["files"],
        )
        with self.assertRaises(subject.ProtocolError):
            subject.enumerate_isolated_native_build_root_v1(
                compiler, linker, prefixed_oversize, inputs,
            )

        deep_compiler = copy.deepcopy(compiler)
        deep_compiler["argument_path"] = "/" + "/".join(["a"] * 100) + "/cc"
        deep_compiler["resolved_path"] = deep_compiler["argument_path"]
        with mock.patch.object(
            subject, "V4_BUILD_INPUT_CLOSURE_ENTRY_MAX", 16,
        ), self.assertRaisesRegex(subject.ProtocolError, "entry count"):
            subject.enumerate_isolated_native_build_root_v1(
                deep_compiler, linker, source_tree, inputs,
            )
        with mock.patch.object(
            subject, "V4_BUILD_ROOT_DERIVATION_MAX_BYTES", 50,
        ), self.assertRaisesRegex(subject.ProtocolError, "derivation work"):
            subject.enumerate_isolated_native_build_root_v1(
                compiler, linker, source_tree, inputs,
            )

    def test_v4_isolated_native_build_filter_enumerator(self) -> None:
        authority = subject.enumerate_isolated_native_build_filter_v5()
        self.assertEqual(set(authority), {
            "schema", "kind", "policy", "architecture", "audit_arch",
            "instruction_count", "instructions_bytes", "instructions_sha256",
            "instructions_payload_base64", "decoded_rule_count",
            "decoded_policy", "policy_sha256",
        })
        self.assertEqual(authority["schema"], 5)
        self.assertEqual(authority["kind"], subject.V4_BUILD_FILTER_KIND)
        self.assertEqual(authority["policy"], subject.V4_BUILD_FILTER_POLICY)
        self.assertEqual(
            authority["instruction_count"],
            subject.V4_BUILD_FILTER_INSTRUCTION_COUNT,
        )
        self.assertEqual(
            authority["decoded_rule_count"],
            subject.V4_BUILD_FILTER_DECODED_RULE_COUNT,
        )
        payload = base64.b64decode(
            authority["instructions_payload_base64"], validate=True,
        )
        self.assertEqual(len(payload), subject.V4_BUILD_FILTER_INSTRUCTIONS_BYTES)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            authority["instructions_sha256"],
        )
        self.assertEqual(
            authority["instructions_sha256"],
            "ac16fd851e4e8dfc4704364f835bcb01cd4942432807b73f205b2e2db8ff2f8b",
        )
        instructions = [
            struct.unpack("<HBBI", payload[offset:offset + 8])
            for offset in range(0, len(payload), 8)
        ]
        self.assertEqual(instructions[0], (0x20, 0, 0, 4))
        self.assertEqual(
            instructions[1],
            (0x15, 1, 0, subject.V4_BUILD_FILTER_AUDIT_ARCH),
        )
        self.assertEqual(
            instructions[4],
            (0x45, 0, 1, subject.V4_BUILD_FILTER_X32_SYSCALL_BIT),
        )
        self.assertEqual(
            instructions[5],
            (0x06, 0, 0, subject.V4_BUILD_FILTER_RET_ENOSYS),
        )
        self.assertEqual(
            instructions[-1],
            (0x06, 0, 0, subject.V4_BUILD_FILTER_RET_ALLOW),
        )
        decoded = authority["decoded_policy"]
        self.assertEqual(decoded[0]["decision"], "kill-process")
        self.assertEqual(decoded[1]["ret_data"], 38)
        self.assertEqual(decoded[-1]["decision"], "allow")
        syscall_rules = {
            record["syscall_number"]: record
            for record in decoded[1:-1] if record["syscall_number"] >= 0
        }
        self.assertEqual(
            set(syscall_rules),
            {
                number
                for number, _ in subject.V4_BUILD_FILTER_DENIED_SYSCALLS
            } | {subject.V4_BUILD_FILTER_CLONE_SYSCALL},
        )
        self.assertEqual(
            syscall_rules[subject.V4_BUILD_FILTER_CLONE_SYSCALL][
                "argument_policy"
            ],
            [{
                "index": 0,
                "argument_index": 0,
                "operation": "masked-nonzero",
                "mask": subject.V4_BUILD_FILTER_CLONE_REJECT_MASK,
                "value": None,
            }],
        )
        self.assertEqual(syscall_rules[435]["ret_data"], 38)
        self.assertEqual(
            authority["policy_sha256"], subject.canonical_sha256(decoded),
        )
        self.assertEqual(
            authority["policy_sha256"],
            "10d3cb1cfed09d14413f01066a71180359b9252f04daa131978b370d94460ebb",
        )
        self.assertEqual(
            subject.enumerate_isolated_native_build_filter_v5(), authority,
        )
        self.assertIs(
            subject.validate_isolated_native_build_filter(authority), authority,
        )
        for label, forge in (
            ("dict subclass", type("Filter", (dict,), {})(authority)),
            (
                "list subclass",
                {
                    **authority,
                    "decoded_policy": type("Rules", (list,), {})(
                        authority["decoded_policy"],
                    ),
                },
            ),
            (
                "string subclass",
                {
                    **authority,
                    "kind": type("Kind", (str,), {})(authority["kind"]),
                },
            ),
            (
                "mutated payload",
                {**authority, "instructions_sha256": "0" * 64},
            ),
        ):
            with self.subTest(label=label), self.assertRaises(
                subject.ProtocolError,
            ):
                subject.validate_isolated_native_build_filter(forge)
        deeply_nested: object = None
        for _ in range(subject.V4_EXACT_JSON_TYPE_DEPTH_MAX + 1):
            deeply_nested = [deeply_nested]
        with self.assertRaisesRegex(subject.ProtocolError, "depth exceeds cap"):
            subject.validate_isolated_native_build_filter({
                **authority, "decoded_policy": deeply_nested,
            })
        cyclic: list[object] = []
        cyclic.append(cyclic)
        with self.assertRaisesRegex(subject.ProtocolError, "depth exceeds cap"):
            subject.validate_isolated_native_build_filter({
                **authority, "decoded_policy": cyclic,
            })
        with self.assertRaisesRegex(
            subject.ProtocolError, "node count exceeds cap",
        ):
            subject.validate_isolated_native_build_filter({
                **authority,
                "decoded_policy": (
                    [None] * subject.V4_EXACT_JSON_TYPE_NODE_MAX
                ),
            })

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
