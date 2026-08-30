#!/usr/bin/python3

from __future__ import annotations

import copy
import hashlib
import importlib.util
import math
from pathlib import Path
import sys
import unittest


SUBJECT_PATH = Path(__file__).with_name("direct_release_protocol.py")
SPEC = importlib.util.spec_from_file_location("direct_release_protocol", SUBJECT_PATH)
assert SPEC is not None and SPEC.loader is not None
subject = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = subject
SPEC.loader.exec_module(subject)


def fixture() -> tuple[dict, dict]:
    theorem_records = []
    for index, name in enumerate(subject.FINAL_THEOREM_NAMES):
        theorem_records.append({
            "name": name,
            "theorem_sha256": f"{index + 1:x}" * 64,
            "hypotheses_sha256": f"{index + 5:x}" * 64,
            "conclusion_sha256": f"{index + 9:x}" * 64,
            "global_axioms_sha256": "d" * 64,
            "hypothesis_count": 0,
            "global_axiom_count": 3,
        })
    fingerprints = {
        "status": "observed_uncompared",
        "approved_reference_present": False,
        "serializer": {
            "path": subject.FINGERPRINT_SERIALIZER_PATH,
            "sha256": "e" * 64,
        },
        "theorems": theorem_records,
        "post_state": {
            "kernel_state_sha256": "1" * 64,
            "type_constants_sha256": "2" * 64,
            "term_constants_sha256": "3" * 64,
            "definitions_sha256": "4" * 64,
            "global_axioms_sha256": "d" * 64,
            "type_constant_count": 10,
            "term_constant_count": 20,
            "definition_count": 30,
            "global_axiom_count": 3,
        },
    }
    records = [
        {"index": index, "name": name, "full_digest_md5": f"{index + 1:x}" * 32}
        for index, name in enumerate(subject.FINAL_THEOREM_NAMES)
    ]
    dependency = {
        "schema": 1,
        "kind": "candle-flyspeck-dependency-history-observation",
        "policy": subject.DEPENDENCY_HISTORY_POLICY,
        "status": "observed_uncompared",
        "boundary_id": subject.FINAL_BOUNDARY_ID,
        "record_count": 4,
        "ordered_request_sha256": subject.canonical_sha256(
            list(subject.FINAL_THEOREM_NAMES)
        ),
        "ordered_record_sha256": subject.canonical_sha256(records),
        "records": records,
        "approved_reference_present": False,
        "dependency_history_is_kernel_trace": False,
        "pft_used": False,
        "s2_s3_evidence": False,
    }
    return fingerprints, dependency


def coverage_fixture() -> dict:
    actions = [
        {
            "index": index,
            "source_sha256": f"{index % 15 + 1:x}" * 64,
            "logical_source_delta_sha256": f"{(index + 1) % 15 + 1:x}" * 64,
            "outcome": "load",
        }
        for index in range(subject.FINAL_ACTION_COUNT)
    ]
    logical_records = [
        {
            "index": 0,
            "key": "candle:candle/build/insulate.ml",
            "classification": "generated-executed-control",
            "source_sha256": "a" * 64,
            "source_md5": "a" * 32,
            "execution_normalization": None,
        },
        {
            "index": 1,
            "key": subject.LOGICAL_DERIVATION_KEY,
            "classification": "derivation-only-input",
            "source_sha256": "b" * 64,
            "source_md5": "b" * 32,
            "execution_normalization": None,
        },
        {
            "index": 2,
            "key": subject.LOGICAL_FINAL_TARGET_KEY,
            "classification": "expected-nested-source",
            "source_sha256": "c" * 64,
            "source_md5": "c" * 32,
            "execution_normalization": None,
        },
        {
            "index": 3,
            "key": "candle:candle/flyspeck_source_digests.ml",
            "classification": "generated-executed-control",
            "source_sha256": "d" * 64,
            "source_md5": "d" * 32,
            "execution_normalization": None,
        },
        {
            "index": 4,
            "key": "flyspeck:b.hl",
            "classification": "observed-outer-source",
            "source_sha256": "e" * 64,
            "source_md5": "e" * 32,
            "execution_normalization": {
                "id": "NORM-1",
                "normalized_sha256": "f" * 64,
                "normalized_md5": "f" * 32,
            },
        },
    ]
    events = [
        {"event": "request", "id": 0, "parent": None, "kind": "#use",
         "key": "control:runtime-setup", "cache_before": "fresh-cache"},
        {"event": "request", "id": 1, "parent": 0, "kind": "#use",
         "key": "candle:candle/flyspeck_source_digests.ml",
         "cache_before": "fresh-cache"},
        {"event": "outcome", "id": 1, "outcome": "evaluated"},
        {"event": "request", "id": 2, "parent": 0, "kind": "loads",
         "key": "candle:candle/build/insulate.ml",
         "cache_before": "fresh-cache"},
        {"event": "outcome", "id": 2, "outcome": "evaluated"},
        {"event": "outcome", "id": 0, "outcome": "evaluated"},
        {"event": "request", "id": 3, "parent": None, "kind": "#use",
         "key": "control:instrumented-prefix", "cache_before": "fresh-cache"},
        {"event": "request", "id": 4, "parent": 3, "kind": "needs",
         "key": "flyspeck:b.hl", "cache_before": "fresh-cache"},
        {"event": "outcome", "id": 4, "outcome": "evaluated"},
        {"event": "outcome", "id": 3, "outcome": "evaluated"},
        {"event": "request", "id": 5, "parent": None, "kind": "#use",
         "key": "control:stratum-check", "cache_before": "fresh-cache"},
        {"event": "outcome", "id": 5, "outcome": "evaluated"},
        {"event": "request", "id": 6, "parent": None, "kind": "#use",
         "key": "control:postlude", "cache_before": "fresh-cache"},
        {"event": "request", "id": 7, "parent": 6, "kind": "#use",
         "key": subject.LOGICAL_FINAL_TARGET_KEY,
         "cache_before": "fresh-cache"},
        {"event": "outcome", "id": 7, "outcome": "evaluated"},
        {"event": "request", "id": 8, "parent": 6, "kind": "#use",
         "key": "control:fingerprint-serializer",
         "cache_before": "fresh-cache"},
        {"event": "outcome", "id": 8, "outcome": "evaluated"},
        {"event": "outcome", "id": 6, "outcome": "evaluated"},
        {"event": "terminal", "request_count": 9},
    ]
    observed_keys = sorted({
        event["key"] for event in events if event["event"] == "request"
    })
    generated = []
    for index in range(38):
        generated.append({
            "class": "lp-certificate",
            "path": f"formal_lp/glpk/binary/cert-{index:02d}.dat",
            "bytes": index + 1,
            "sha256": f"{index % 15 + 1:x}" * 64,
        })
    generated.append({
        "class": "lp-certificate-prepared",
        "path": "formal_lp/glpk/binary/hard_7.dat",
        "bytes": 100,
        "sha256": "f" * 64,
    })
    for index, class_name in enumerate((
        "lp-certificate-archive", "lp-archive", "nonlinear-preparation",
        "nonlinear-case-log",
    )):
        generated.append({
            "class": class_name,
            "path": f"generated/other-{index}",
            "bytes": 200 + index,
            "sha256": f"{index + 1:x}" * 64,
        })
    runtime_certificates = sorted(
        generated[:39], key=lambda record: Path(record["path"]).name,
    )
    consumption = [
        {
            "index": index,
            "class": record["class"],
            "relative": record["path"],
            "bytes": record["bytes"],
            "sha256": record["sha256"],
            "event_count": 1,
            "ordered_nonce_free_event_sha256": f"{index + 1:064x}",
        }
        for index, record in enumerate(runtime_certificates)
    ]
    return {
        "schema": 1,
        "kind": subject.COVERAGE_PROJECTION_KIND,
        "boundary_id": subject.FINAL_BOUNDARY_ID,
        "completed_action_count": subject.FINAL_ACTION_COUNT,
        "action_events": {
            "record_count": len(actions),
            "ordered_record_sha256": subject.canonical_sha256(actions),
            "records": actions,
        },
        "logical_source_coverage": {
            "schema": 1,
            "kind": subject.LOGICAL_COVERAGE_KIND,
            "policy": subject.SOURCE_CLOSURE_POLICY,
            "order": subject.SOURCE_CLOSURE_ORDER,
            "record_count": len(logical_records),
            "ordered_record_sha256": subject.canonical_sha256(logical_records),
            "records": logical_records,
            "execution_observation": subject.SOURCE_CLOSURE_OBSERVATION,
            "self_certifies_nested_execution": False,
        },
        "physical_source_coverage": {
            "schema": 1,
            "kind": subject.PHYSICAL_COVERAGE_KIND,
            "protocol": subject.SOURCE_TRACE_PROTOCOL,
            "event_count": len(events),
            "ordered_event_sha256": subject.canonical_sha256(events),
            "events": events,
            "request_count": 9,
            "cache_skip_count": 0,
            "observed_key_count": len(observed_keys),
            "ordered_observed_key_sha256":
                subject.canonical_sha256(observed_keys),
            "observed_keys": observed_keys,
            "status": "closed-loader-owned-session",
        },
        "generated_inputs": {
            "contract_sha256": "a" * 64,
            "receipt_sha256": "b" * 64,
            "entry_count": len(generated),
            "ordered_binding_sha256": subject.canonical_sha256(generated),
            "bindings": generated,
        },
        "mathematical_coverage": {
            "structural_fingerprint_requests": list(subject.FINAL_THEOREM_NAMES),
            "dependency_history_requests": list(subject.FINAL_THEOREM_NAMES),
            "source": "loader-observed-exact-unapproved",
            "lp": "observed-uncompared",
            "nonlinear": "observed-uncompared",
            "final_implication": "observed-uncompared",
            "lp_certificate_consumption_trace_included": True,
            "dependency_history_is_kernel_trace": False,
            "approved_reference_present": False,
        },
        "lp_certificate_consumption": {
            "schema": 1,
            "kind": subject.CERTIFICATE_CONSUMPTION_KIND,
            "policy": subject.CERTIFICATE_CONSUMPTION_POLICY,
            "order": subject.CERTIFICATE_CONSUMPTION_ORDER,
            "status": "consumption-observed-unapproved",
            "record_count": len(consumption),
            "ordered_record_sha256": subject.canonical_sha256(consumption),
            "records": consumption,
            "unmatched_event_count": 0,
            "pft_used": False,
        },
        "pft_used": False,
    }


def schema6_fixture() -> tuple[dict, dict]:
    coverage = coverage_fixture()
    nonce = "9" * 32
    logical_by_key = {
        record["key"]: record
        for record in coverage["logical_source_coverage"]["records"]
    }
    action_keys = [
        ("flyspeck:jHOLLight/caml/ssreflect.hl" if index == 126 else
         "flyspeck:formal_graph/archive/archive_all.ml" if index == 154 else
         "flyspeck:formal_lp/hypermap/verify_all.hl" if index == 183 else
         f"flyspeck:text_formalization/fixture/action-{index:03d}.hl")
        for index in range(subject.FINAL_ACTION_COUNT)
    ]
    source_keys = set(action_keys) | set(logical_by_key)
    extra_index = 0
    while len(source_keys) < 400:
        source_keys.add(f"flyspeck:fixture/extra-{extra_index:03d}.hl")
        extra_index += 1
    normalized_keys = {"flyspeck:b.hl", *action_keys[:17]}
    source_bindings = []
    for key in sorted(source_keys):
        repository, path = key.split(":", 1)
        if key in logical_by_key:
            logical = logical_by_key[key]
            source_sha256 = logical["source_sha256"]
            source_md5 = logical["source_md5"]
        elif key in action_keys:
            action_index = action_keys.index(key)
            source_sha256 = coverage["action_events"]["records"][
                action_index
            ]["source_sha256"]
            source_md5 = f"{action_index % 15 + 1:x}" * 32
        else:
            encoded = key.encode()
            source_sha256 = hashlib.sha256(encoded).hexdigest()
            source_md5 = hashlib.md5(
                encoded, usedforsecurity=False,
            ).hexdigest()
        binding = {
            "key": key,
            "repository": repository,
            "path": path,
            "bytes": len(key) + 1,
            "sha256": source_sha256,
            "md5": source_md5,
        }
        if key in normalized_keys:
            if key == "flyspeck:b.hl":
                logical_normalization = logical_by_key[key][
                    "execution_normalization"
                ]
                assert logical_normalization is not None
                normalization_id = logical_normalization["id"]
                normalized_sha256 = logical_normalization[
                    "normalized_sha256"
                ]
                normalized_md5 = logical_normalization["normalized_md5"]
            else:
                normalization_index = action_keys.index(key)
                normalization_id = f"FIXTURE-NORM-{normalization_index:03d}"
                normalized_sha256 = f"{normalization_index + 1:064x}"
                normalized_md5 = f"{normalization_index + 1:032x}"
            binding["execution_normalization"] = {
                "id": normalization_id,
                "kind": "exact_bytes_replace_sequence",
                "normalized_bytes": binding["bytes"] + 1,
                "normalized_sha256": normalized_sha256,
                "normalized_md5": normalized_md5,
                "operation_count": 1,
            }
        source_bindings.append(binding)
    source_by_key = {binding["key"]: binding for binding in source_bindings}
    plan_actions = []
    for index, key in enumerate(action_keys):
        source = source_by_key[key]
        action = {
            "index": index,
            "selected_source": key,
            "target": (
                "../jHOLLight/caml/ssreflect.hl" if index == 126 else
                "../formal_graph/archive/archive_all.ml" if index == 154 else
                "../formal_lp/hypermap/verify_all.hl" if index == 183 else
                f"fixture/action-{index:03d}.hl"
            ),
            "stratum": subject.ACTION_STRATA[index % len(subject.ACTION_STRATA)],
            "source_bytes": source["bytes"],
            "source_sha256": source["sha256"],
            "source_md5": source["md5"],
        }
        if "execution_normalization" in source:
            action["execution_normalization"] = copy.deepcopy(
                source["execution_normalization"]
            )
        plan_actions.append(action)
    plan = {
        "schema": 1,
        "kind": "candle-flyspeck-cumulative-stratum-plan",
        "action_count": subject.FINAL_ACTION_COUNT,
        "actions": plan_actions,
        "ordered_action_sha256": subject.canonical_sha256(plan_actions),
        "source_graph": {
            "entry_count": len(source_bindings),
            "ordered_binding_sha256": subject.canonical_sha256(source_bindings),
            "bindings": source_bindings,
        },
        "generated_inputs": copy.deepcopy(coverage["generated_inputs"]),
    }
    plan_bytes = subject.canonical_json_bytes(plan)
    plan_record = {
        "bytes": len(plan_bytes),
        "sha256": hashlib.sha256(plan_bytes).hexdigest(),
        "md5": hashlib.md5(plan_bytes, usedforsecurity=False).hexdigest(),
    }
    expected_actions = []
    observed_actions = []
    for record in coverage["action_events"]["records"]:
        delta = [{"fixture_action": record["index"]}]
        delta_sha256 = subject.canonical_sha256(delta)
        expected_actions.append({
            "index": record["index"],
            "source_sha256": record["source_sha256"],
            "logical_source_delta": delta,
            "logical_source_delta_sha256": delta_sha256,
        })
        observed_actions.append({
            "index": record["index"],
            "source_sha256": record["source_sha256"],
            "logical_source_delta_sha256": delta_sha256,
            "outcome": record["outcome"],
        })

    logical_projection = coverage["logical_source_coverage"]
    logical = {
        "schema": 3,
        "kind": subject.RAW_SOURCE_CLOSURE_KIND,
        "policy": logical_projection["policy"],
        "order": logical_projection["order"],
        "completed_action_count": subject.FINAL_ACTION_COUNT,
        "final_target_selected": True,
        "record_count": logical_projection["record_count"],
        "ordered_record_sha256": logical_projection["ordered_record_sha256"],
        "records": copy.deepcopy(logical_projection["records"]),
        "physical_loader_cache_trace": False,
        "execution_observation": logical_projection["execution_observation"],
        "self_certifies_nested_execution": False,
        "s2_s3_evidence": False,
        "status": "expected-closure-emitted-unapproved",
    }
    expected_logical = copy.deepcopy(logical)
    del expected_logical["status"]

    physical_projection = coverage["physical_source_coverage"]
    physical_events = []
    for event in physical_projection["events"]:
        event = copy.deepcopy(event)
        if event["event"] == "request":
            event["binding_id"] = hashlib.sha256(
                event["key"].encode()
            ).hexdigest()
        physical_events.append(event)
    physical = {
        "schema": 1,
        "protocol": subject.SOURCE_TRACE_PROTOCOL,
        "nonce": nonce,
        "event_count": len(physical_events),
        "ordered_event_sha256": subject.canonical_sha256(physical_events),
        "events": physical_events,
        "request_count": physical_projection["request_count"],
        "cache_skip_count": physical_projection["cache_skip_count"],
        "observed_key_count": physical_projection["observed_key_count"],
        "ordered_observed_key_sha256":
            physical_projection["ordered_observed_key_sha256"],
        "observed_keys": copy.deepcopy(physical_projection["observed_keys"]),
        "status": "closed-loader-owned-session",
    }

    semantic_lp_records = []
    lp_records = []
    lp_bindings = []
    lp_events = []
    for projected in coverage["lp_certificate_consumption"]["records"]:
        identity = {
            field: copy.deepcopy(projected[field]) for field in (
                "index", "class", "relative", "bytes", "sha256",
            )
        }
        identity["md5"] = f"{projected['index'] + 1:032x}"
        binding_id = subject.canonical_sha256(identity)
        event = {
            "event": "consumed",
            "id": projected["index"],
            "binding_id": binding_id,
            "index": projected["index"],
        }
        semantic_lp_records.append(identity)
        lp_records.append({
            **identity,
            "event_count": 1,
            "ordered_nonce_free_event_sha256":
                subject.canonical_sha256([event]),
        })
        lp_bindings.append({
            "binding_id": binding_id,
            **identity,
            "path": f"/snapshot/generated/{identity['relative']}",
        })
        lp_events.append(event)
    semantic_lp = {
        "status": "authenticated-runtime-inputs-not-consumption-traced",
        "record_count": 39,
        "ordered_record_sha256": subject.canonical_sha256(semantic_lp_records),
        "records": semantic_lp_records,
    }
    semantic_plan = {
        "schema": 1,
        "kind": "candle-flyspeck-direct-semantic-evidence-plan",
        "policy": "authenticated-direct-source-lp-nonlinear-observation-v1",
        "boundary_id": subject.FINAL_BOUNDARY_ID,
        "completed_action_count": subject.FINAL_ACTION_COUNT,
        "logical_source": {},
        "physical_source_trace": {},
        "structural_fingerprint_requests": list(subject.FINAL_THEOREM_NAMES),
        "dependency_history_requests": list(subject.FINAL_THEOREM_NAMES),
        "authenticated_inputs": {
            "plan_sha256": plan_record["sha256"],
            "host_materialization_sha256": "a" * 64,
            "manifest_sha256": "b" * 64,
        },
        "lp_certificate_inputs": semantic_lp,
        "approval_included": False,
        "pft_used": False,
        "s2_s3_evidence": False,
    }
    lp_contract = {
        "schema": 1,
        "protocol": subject.RAW_LP_CONSUMPTION_PROTOCOL,
        "policy": subject.RAW_LP_CONSUMPTION_POLICY,
        "order": subject.CERTIFICATE_CONSUMPTION_ORDER,
        "nonce": nonce,
        "record_count": 39,
        "ordered_binding_sha256": subject.canonical_sha256(lp_bindings),
        "bindings": lp_bindings,
        "pft_used": False,
    }
    lp_observation = {
        "schema": 1,
        "kind": subject.RAW_LP_CONSUMPTION_KIND,
        "protocol": subject.RAW_LP_CONSUMPTION_PROTOCOL,
        "policy": subject.RAW_LP_CONSUMPTION_POLICY,
        "order": subject.CERTIFICATE_CONSUMPTION_ORDER,
        "nonce": nonce,
        "status": "consumption-observed-unapproved",
        "event_count": 39,
        "ordered_event_sha256": subject.canonical_sha256(lp_events),
        "events": lp_events,
        "record_count": 39,
        "ordered_record_sha256": subject.canonical_sha256(lp_records),
        "records": lp_records,
        "unmatched_event_count": 0,
        "approved_reference_present": False,
        "pft_used": False,
        "s2_s3_evidence": False,
    }
    fingerprints, dependency = fixture()
    semantic_coverage = {
        "schema": 2,
        "kind": "candle-flyspeck-direct-semantic-coverage-observation-v2",
        "policy": subject.RAW_V6_SEMANTIC_POLICY,
        "status": "observed_uncompared",
        "boundary_id": subject.FINAL_BOUNDARY_ID,
        "semantic_evidence_plan_sha256": subject.canonical_sha256(semantic_plan),
        "logical_source_observation_sha256": subject.canonical_sha256(logical),
        "physical_source_observation_sha256": subject.canonical_sha256(physical),
        "structural_fingerprint_observation_sha256":
            subject.canonical_sha256(fingerprints),
        "dependency_history_observation_sha256":
            subject.canonical_sha256(dependency),
        "lp_certificate_input_sha256": semantic_lp["ordered_record_sha256"],
        "source": "loader-observed-exact-unapproved",
        "lp": "consumption-observed-uncompared",
        "nonlinear": "observed-uncompared",
        "final_implication": "observed-uncompared",
        "lp_certificate_consumption_trace_included": True,
        "lp_certificate_consumption_contract_sha256":
            subject.canonical_sha256(lp_contract),
        "lp_certificate_consumption_observation_sha256":
            subject.canonical_sha256(lp_observation),
        "dependency_history_is_kernel_trace": False,
        "approved_reference_present": False,
        "approval_sha256": None,
        "pft_used": False,
        "s2_eligible": False,
        "s3_eligible": False,
        "s2_s3_evidence": False,
    }
    evidence_contract = {
        "schema": "candle-flyspeck-direct-runtime-evidence-v6",
        "allowed_action_outcomes": list(subject.ACTION_OUTCOMES),
        "physical_loader_cache_skip_allowed":
            "only loader-authenticated needs cache-skip events",
        "logical_source_closure_policy": subject.SOURCE_CLOSURE_POLICY,
        "logical_source_closure_order": subject.SOURCE_CLOSURE_ORDER,
        "selected_loadt_ledger_delta_included": True,
        "physical_loader_cache_trace_included": True,
        "physical_source_trace_protocol": subject.SOURCE_TRACE_PROTOCOL,
        "pre_trace_control_exclusion": "control:runtime-config",
        "s2_s3_approval_included": False,
        "dependency_history_protocol": "CANDLE_FLYSPECK_DEPENDENCY_HISTORY_V1",
        "dependency_history_policy": subject.DEPENDENCY_HISTORY_POLICY,
        "semantic_coverage_policy": subject.RAW_V6_SEMANTIC_POLICY,
        "dependency_history_is_kernel_trace": False,
        "semantic_approval_included": False,
        "pft_used": False,
        "lp_certificate_consumption_protocol":
            subject.RAW_LP_CONSUMPTION_PROTOCOL,
        "lp_certificate_consumption_policy": subject.RAW_LP_CONSUMPTION_POLICY,
        "lp_certificate_consumption_order":
            subject.CERTIFICATE_CONSUMPTION_ORDER,
        "lp_certificate_consumption_exactly_once": True,
    }
    receipt = {field: None for field in subject.RAW_V6_RECEIPT_FIELDS}
    receipt.update({
        "schema": 6,
        "kind": "candle-flyspeck-compiled-stratum-attempt",
        "claim": subject.RAW_V6_CLAIM,
        "state": "completed",
        "boundary_id": subject.FINAL_BOUNDARY_ID,
        "diagnostic_only": False,
        "attempt_nonce": nonce,
        "action_count": subject.FINAL_ACTION_COUNT,
        "fresh_process_replay_from_action_zero": True,
        "cooperative_build_run_lock_held": True,
        "concurrent_mutation_model": subject.RAW_CONCURRENT_MUTATION_MODEL,
        "process_state_checkpoint": None,
        "runtime_environment_policy": subject.RAW_RUNTIME_ENVIRONMENT_POLICY,
        "ordered_expected_action_sha256":
            subject.canonical_sha256(expected_actions),
        "expected_action_events": expected_actions,
        "evidence_contract": evidence_contract,
        "expected_logical_source_closure": expected_logical,
        "semantic_evidence_plan": semantic_plan,
        "lp_consumption_contract": lp_contract,
        "inputs": {"plan": plan_record},
        "repositories": {
            "candle": "c" * 40,
            "flyspeck": "f" * 40,
        },
        "timed_out": False,
        "exit_code": 0,
        "action_markers_validated": subject.FINAL_ACTION_COUNT,
        "action_events": observed_actions,
        "logical_source_closure": logical,
        "physical_source_trace": physical,
        "semantic_fingerprints": fingerprints,
        "dependency_history": dependency,
        "semantic_coverage": semantic_coverage,
        "lp_certificate_consumption": lp_observation,
        "s2_s3_evidence": False,
        "validation_error": None,
        "postflight_reauthenticated": True,
    })
    return receipt, plan


class DirectReleaseProtocolTests(unittest.TestCase):
    def test_protocol_does_not_mint_compiled_authenticated_descriptors(
        self,
    ) -> None:
        self.assertFalse(hasattr(
            subject, "build_authenticated_compiled_comparison_descriptor",
        ))

    def test_exact_semantic_projection_is_unapproved_and_nonce_free(self) -> None:
        projection = subject.project_authenticated_semantic_observations(*fixture())
        self.assertEqual(
            [record["name"] for record in projection["theorems"]],
            list(subject.FINAL_THEOREM_NAMES),
        )
        self.assertEqual(set(projection), {
            "schema", "kind", "serializer", "theorems", "post_state",
            "dependency_history",
        })

        def reject_nonce_key(value) -> None:
            if isinstance(value, dict):
                self.assertNotIn("nonce", value)
                for nested in value.values():
                    reject_nonce_key(nested)
            elif isinstance(value, list):
                for nested in value:
                    reject_nonce_key(nested)

        reject_nonce_key(projection)
        self.assertIs(subject.validate_semantic_projection(projection), projection)

        fingerprints, dependency = fixture()
        detached = subject.project_authenticated_semantic_observations(
            fingerprints, dependency,
        )
        fingerprints["theorems"][0]["theorem_sha256"] = "0" * 64
        dependency["records"][0]["full_digest_md5"] = "0" * 32
        self.assertNotEqual(
            detached["theorems"][0]["theorem_sha256"], "0" * 64,
        )
        self.assertNotEqual(
            detached["dependency_history"][0]["full_digest_md5"],
            "0" * 32,
        )

    def test_projection_canonical_bytes_round_trip(self) -> None:
        projection = subject.project_authenticated_semantic_observations(*fixture())
        data = subject.canonical_json_bytes(projection)
        self.assertEqual(
            subject.decode_object(data, "projection"), projection,
        )
        self.assertEqual(
            subject.validate_canonical_semantic_projection_bytes(data), projection,
        )
        with self.assertRaisesRegex(subject.ProtocolError, "not canonical"):
            subject.validate_canonical_semantic_projection_bytes(
                subject.canonical_value_bytes(projection)
            )

    def test_duplicate_and_nonfinite_json_reject(self) -> None:
        with self.assertRaisesRegex(subject.ProtocolError, "duplicate JSON key"):
            subject.decode_object(b'{"schema":1,"schema":2}', "value")
        with self.assertRaisesRegex(subject.ProtocolError, "non-finite"):
            subject.decode_object(b'{"value":NaN}', "value")
        with self.assertRaises(ValueError):
            subject.canonical_json_bytes({"value": math.nan})

    def test_theorem_reorder_and_extra_field_reject(self) -> None:
        fingerprints, dependency = fixture()
        fingerprints["theorems"][0], fingerprints["theorems"][1] = (
            fingerprints["theorems"][1], fingerprints["theorems"][0]
        )
        with self.assertRaisesRegex(subject.ProtocolError, "order/name"):
            subject.project_authenticated_semantic_observations(
                fingerprints, dependency,
            )
        fingerprints, dependency = fixture()
        fingerprints["unexpected"] = False
        with self.assertRaisesRegex(subject.ProtocolError, "fingerprint observation"):
            subject.project_authenticated_semantic_observations(
                fingerprints, dependency,
            )

    def test_boolean_count_rejects_exact_json_type_confusion(self) -> None:
        fingerprints, dependency = fixture()
        fingerprints["post_state"]["definition_count"] = True
        with self.assertRaisesRegex(subject.ProtocolError, "post-state count"):
            subject.project_authenticated_semantic_observations(
                fingerprints, dependency,
            )
        fingerprints, dependency = fixture()
        dependency["record_count"] = True
        with self.assertRaisesRegex(subject.ProtocolError, "identity or claim"):
            subject.project_authenticated_semantic_observations(
                fingerprints, dependency,
            )

    def test_pft_or_pretended_approval_rejects(self) -> None:
        fingerprints, dependency = fixture()
        dependency["pft_used"] = True
        with self.assertRaisesRegex(subject.ProtocolError, "identity or claim"):
            subject.project_authenticated_semantic_observations(
                fingerprints, dependency,
            )
        fingerprints, dependency = fixture()
        fingerprints["approved_reference_present"] = True
        with self.assertRaisesRegex(subject.ProtocolError, "unapproved observation"):
            subject.project_authenticated_semantic_observations(
                fingerprints, dependency,
            )

    def test_dependency_digest_and_order_reject(self) -> None:
        fingerprints, dependency = fixture()
        dependency["ordered_record_sha256"] = "0" * 64
        with self.assertRaisesRegex(subject.ProtocolError, "digest mismatch"):
            subject.project_authenticated_semantic_observations(
                fingerprints, dependency,
            )
        fingerprints, dependency = fixture()
        dependency["records"][2]["index"] = 1
        dependency["ordered_record_sha256"] = subject.canonical_sha256(
            dependency["records"]
        )
        with self.assertRaisesRegex(subject.ProtocolError, "order/name"):
            subject.project_authenticated_semantic_observations(
                fingerprints, dependency,
            )

    def test_projection_cannot_embed_claim_or_approval_bits(self) -> None:
        projection = subject.project_authenticated_semantic_observations(*fixture())
        for field in (
            "pft_used", "direct_s2_execution_approved",
            "direct_s3_coverage_approved", "v1_3_s3_release_approved",
        ):
            mutated = copy.deepcopy(projection)
            mutated[field] = True
            with self.assertRaisesRegex(subject.ProtocolError, "malformed"):
                subject.validate_semantic_projection(mutated)

    def test_exact_coverage_projection_and_canonical_bytes(self) -> None:
        projection = coverage_fixture()
        self.assertIs(subject.validate_coverage_projection(projection), projection)
        data = subject.canonical_json_bytes(projection)
        self.assertEqual(
            subject.validate_canonical_coverage_projection_bytes(data), projection,
        )
        with self.assertRaisesRegex(subject.ProtocolError, "not canonical"):
            subject.validate_canonical_coverage_projection_bytes(
                subject.canonical_value_bytes(projection)
            )

    def test_schema5_presence_can_never_derive_coverage(self) -> None:
        with self.assertRaisesRegex(subject.ProtocolError, "presence but not consumption"):
            subject.coverage_projection_from_schema5({
                "schema": 5,
                "semantic_coverage": {
                    "lp_certificate_consumption_trace_included": False,
                },
            })

    def test_authenticated_schema6_projects_one_nonce_free_coverage_value(self) -> None:
        receipt, plan = schema6_fixture()
        projection = subject.coverage_projection_from_schema6(receipt, plan)
        self.assertIs(subject.validate_coverage_projection(projection), projection)
        self.assertEqual(projection["completed_action_count"], 297)
        self.assertEqual(
            projection["lp_certificate_consumption"]["record_count"], 39,
        )
        self.assertTrue(all(
            record["event_count"] == 1
            for record in projection["lp_certificate_consumption"]["records"]
        ))

        def reject_nonce_and_binding_ids(value) -> None:
            if isinstance(value, dict):
                self.assertNotIn("nonce", value)
                self.assertNotIn("binding_id", value)
                for nested in value.values():
                    reject_nonce_and_binding_ids(nested)
            elif isinstance(value, list):
                for nested in value:
                    reject_nonce_and_binding_ids(nested)

        reject_nonce_and_binding_ids(projection)

    def test_schema6_projects_disjoint_cross_runtime_coverage_v2(self) -> None:
        receipt, plan = schema6_fixture()
        projection = subject.cross_runtime_coverage_projection_from_schema6(
            receipt, plan,
        )
        self.assertIs(
            subject.validate_cross_runtime_coverage_projection(projection),
            projection,
        )
        self.assertEqual(projection["actions"]["record_count"], 297)
        self.assertEqual(
            projection["original_source_inventory"]["record_count"], 400,
        )
        self.assertEqual(
            projection["original_source_inventory"]
            ["normalization_binding_count"],
            18,
        )
        self.assertEqual(
            projection["lp_certificate_consumption"]["record_count"], 39,
        )
        self.assertEqual(
            projection["actions"]["records"][126]["target"],
            "../jHOLLight/caml/ssreflect.hl",
        )
        self.assertEqual(
            projection["actions"]["records"][183]["target"],
            "../formal_lp/hypermap/verify_all.hl",
        )
        self.assertEqual(
            projection["actions"]["records"][154]["target"],
            "../formal_graph/archive/archive_all.ml",
        )
        action_keys = {
            record["selected_source"]
            for record in projection["actions"]["records"]
        }
        logical_keys = {
            record["key"] for record in
            projection["selected_logical_source_closure"]["records"]
        }
        self.assertTrue(action_keys <= logical_keys)
        self.assertEqual(
            projection["selected_logical_source_closure"]["records"][0][
                "key"
            ],
            subject.LOGICAL_FINAL_TARGET_KEY,
        )
        projection_bytes = subject.canonical_json_bytes(projection)
        self.assertEqual(
            subject.validate_canonical_cross_runtime_coverage_projection_bytes(
                projection_bytes
            ),
            projection,
        )
        with self.assertRaisesRegex(subject.ProtocolError, "not canonical"):
            subject.validate_canonical_cross_runtime_coverage_projection_bytes(
                subject.canonical_value_bytes(projection)
            )
        for forbidden in (
            b'"nonce"', b'"binding_id"', b'"events"', b'"outcome"',
            b'"physical_source_coverage"', b'"cache_before"', b'control:',
            b'"ordered_nonce_free_event_sha256"',
        ):
            self.assertNotIn(forbidden, projection_bytes)

    def test_cross_runtime_coverage_v2_rejects_hostile_mutations(self) -> None:
        receipt, plan = schema6_fixture()
        projection = subject.cross_runtime_coverage_projection_from_schema6(
            receipt, plan,
        )

        def omit_action(item):
            actions = item["actions"]
            actions["records"].pop()
            actions["record_count"] = len(actions["records"])
            actions["ordered_record_sha256"] = subject.canonical_sha256(
                actions["records"]
            )

        def reorder_actions(item):
            actions = item["actions"]
            actions["records"][0], actions["records"][1] = (
                actions["records"][1], actions["records"][0]
            )
            actions["ordered_record_sha256"] = subject.canonical_sha256(
                actions["records"]
            )

        def omit_source(item):
            inventory = item["original_source_inventory"]
            inventory["records"].pop()
            inventory["record_count"] = len(inventory["records"])
            inventory["ordered_record_sha256"] = subject.canonical_sha256(
                inventory["records"]
            )

        def inject_pft_source(item):
            inventory = item["original_source_inventory"]
            record = inventory["records"][-1]
            record["key"] = "flyspeck:fixture/pft-results.hl"
            record["path"] = "fixture/pft-results.hl"
            inventory["ordered_record_sha256"] = subject.canonical_sha256(
                inventory["records"]
            )

        def copy_candle_control(item):
            closure = item["selected_logical_source_closure"]
            closure["records"][0]["key"] = "control:runtime-setup"
            closure["ordered_record_sha256"] = subject.canonical_sha256(
                closure["records"]
            )

        def omit_action_source_from_closure(item):
            closure = item["selected_logical_source_closure"]
            omitted = item["actions"]["records"][0]["selected_source"]
            closure["records"] = [
                record for record in closure["records"]
                if record["key"] != omitted
            ]
            for index, record in enumerate(closure["records"]):
                record["index"] = index
            closure["record_count"] = len(closure["records"])
            closure["ordered_record_sha256"] = subject.canonical_sha256(
                closure["records"]
            )

        def duplicate_closure_source(item):
            closure = item["selected_logical_source_closure"]
            closure["records"].insert(1, copy.deepcopy(closure["records"][0]))
            for index, record in enumerate(closure["records"]):
                record["index"] = index
            closure["record_count"] = len(closure["records"])
            closure["ordered_record_sha256"] = subject.canonical_sha256(
                closure["records"]
            )

        def reorder_closure_sources(item):
            closure = item["selected_logical_source_closure"]
            closure["records"][0], closure["records"][1] = (
                closure["records"][1], closure["records"][0]
            )
            for index, record in enumerate(closure["records"]):
                record["index"] = index
            closure["ordered_record_sha256"] = subject.canonical_sha256(
                closure["records"]
            )

        def omit_lp(item):
            lp = item["lp_certificate_consumption"]
            lp["records"].pop()
            lp["record_count"] = len(lp["records"])
            lp["ordered_record_sha256"] = subject.canonical_sha256(
                lp["records"]
            )

        def reorder_lp(item):
            lp = item["lp_certificate_consumption"]
            lp["records"][0], lp["records"][1] = (
                lp["records"][1], lp["records"][0]
            )
            lp["ordered_record_sha256"] = subject.canonical_sha256(
                lp["records"]
            )

        def relabel_normalization(item):
            inventory = item["original_source_inventory"]
            normalized = next(
                record for record in inventory["records"]
                if record["candle_plan_execution_selection"]["mode"] ==
                "candle-normalization-bound"
            )
            normalized["candle_plan_execution_selection"]["id"] = "RELABELLED"
            inventory["ordered_record_sha256"] = subject.canonical_sha256(
                inventory["records"]
            )

        cases = (
            ("missing action", omit_action),
            ("reordered action", reorder_actions),
            ("missing source", omit_source),
            ("PFT source", inject_pft_source),
            ("copied Candle control", copy_candle_control),
            ("action source omitted from closure", omit_action_source_from_closure),
            ("duplicate closure source", duplicate_closure_source),
            ("reordered closure source", reorder_closure_sources),
            ("missing LP", omit_lp),
            ("reordered LP", reorder_lp),
            ("duplicate LP success", lambda item: item[
                "lp_certificate_consumption"
            ]["records"][0].update(successful_deserialization_count=2)),
            ("normalization relabel", relabel_normalization),
            ("hidden raw order", lambda item: item[
                "lp_certificate_consumption"
            ].update(raw_order_retained_by_candidate=False)),
            ("missing source completion", lambda item: item[
                "mathematical_coverage"
            ].update(source_closure_observed=False)),
            ("missing LP completion", lambda item: item[
                "mathematical_coverage"
            ].update(lp_completed_observed=False)),
            ("missing nonlinear completion", lambda item: item[
                "mathematical_coverage"
            ].update(nonlinear_completed_observed=False)),
            ("missing final premises", lambda item: item[
                "mathematical_coverage"
            ].update(final_premises_completed_observed=False)),
            ("missing final implication", lambda item: item[
                "mathematical_coverage"
            ].update(final_implication_completed_observed=False)),
            ("pretended reference approval", lambda item: item[
                "mathematical_coverage"
            ].update(approved_reference_present=True)),
            ("PFT bit", lambda item: item.update(pft_used=True)),
        )
        for label, mutate in cases:
            forged = copy.deepcopy(projection)
            mutate(forged)
            with self.subTest(label=label), self.assertRaises(
                subject.ProtocolError,
            ):
                subject.validate_cross_runtime_coverage_projection(forged)

    def test_cross_runtime_action_target_aliases_are_exact(self) -> None:
        receipt, plan = schema6_fixture()
        projection = subject.cross_runtime_coverage_projection_from_schema6(
            receipt, plan,
        )
        for label, target in (
            ("escape", "../../etc/passwd"),
            ("embedded parent", "fixture/../action-126.hl"),
            ("wrong alias", "../formal_lp/caml/ssreflect.hl"),
            ("absolute", "/jHOLLight/caml/ssreflect.hl"),
        ):
            forged = copy.deepcopy(projection)
            forged["actions"]["records"][126]["target"] = target
            forged["actions"]["ordered_record_sha256"] = (
                subject.canonical_sha256(forged["actions"]["records"])
            )
            with self.subTest(label=label), self.assertRaises(
                subject.ProtocolError,
            ):
                subject.validate_cross_runtime_coverage_projection(forged)

    def test_cross_runtime_coverage_v2_rejects_numeric_type_confusion(self) -> None:
        receipt, plan = schema6_fixture()
        projection = subject.cross_runtime_coverage_projection_from_schema6(
            receipt, plan,
        )
        normalized_source_index = next(
            index for index, record in enumerate(
                projection["original_source_inventory"]["records"]
            ) if record["candle_plan_execution_selection"]["mode"] ==
            "candle-normalization-bound"
        )
        cases = (
            ("top schema bool", lambda item: item.update(schema=True)),
            ("completed float", lambda item: item.update(
                completed_action_count=297.0,
            )),
            ("action count bool", lambda item: item["actions"].update(
                record_count=True,
            )),
            ("action index bool", lambda item: item["actions"]["records"][0]
             .update(index=True)),
            ("action bytes bool", lambda item: item["actions"]["records"][0]
             .update(original_bytes=True)),
            ("inventory schema bool", lambda item: item[
                "original_source_inventory"
            ].update(schema=True)),
            ("inventory count float", lambda item: item[
                "original_source_inventory"
            ].update(record_count=400.0)),
            ("normalization count bool", lambda item: item[
                "original_source_inventory"
            ].update(normalization_binding_count=True)),
            ("source index float", lambda item: item[
                "original_source_inventory"
            ]["records"][0].update(index=0.0)),
            ("source bytes bool", lambda item: item[
                "original_source_inventory"
            ]["records"][0].update(original_bytes=True)),
            ("normalized bytes bool", lambda item: item[
                "original_source_inventory"
            ]["records"][normalized_source_index][
                "candle_plan_execution_selection"
            ].update(normalized_bytes=True)),
            ("operation count float", lambda item: item[
                "original_source_inventory"
            ]["records"][normalized_source_index][
                "candle_plan_execution_selection"
            ].update(operation_count=1.0)),
            ("logical schema bool", lambda item: item[
                "selected_logical_source_closure"
            ].update(schema=True)),
            ("logical count bool", lambda item: item[
                "selected_logical_source_closure"
            ].update(record_count=True)),
            ("logical index bool", lambda item: item[
                "selected_logical_source_closure"
            ]["records"][0].update(index=True)),
            ("logical bytes float", lambda item: item[
                "selected_logical_source_closure"
            ]["records"][0].update(original_bytes=1.0)),
            ("LP schema bool", lambda item: item[
                "lp_certificate_consumption"
            ].update(schema=True)),
            ("LP count float", lambda item: item[
                "lp_certificate_consumption"
            ].update(record_count=39.0)),
            ("LP index bool", lambda item: item[
                "lp_certificate_consumption"
            ]["records"][0].update(index=True)),
            ("LP bytes bool", lambda item: item[
                "lp_certificate_consumption"
            ]["records"][0].update(bytes=True)),
            ("LP success bool", lambda item: item[
                "lp_certificate_consumption"
            ]["records"][0].update(successful_deserialization_count=True)),
        )
        for label, mutate in cases:
            forged = copy.deepcopy(projection)
            mutate(forged)
            with self.subTest(label=label), self.assertRaises(
                subject.ProtocolError,
            ):
                subject.validate_cross_runtime_coverage_projection(forged)

    def test_cross_runtime_projection_rejects_raw_normalization_relabel(self) -> None:
        receipt, plan = schema6_fixture()
        logical = receipt["logical_source_closure"]
        normalized = next(
            record for record in logical["records"]
            if record["key"] == "flyspeck:b.hl"
        )
        normalized["execution_normalization"]["id"] = "RELABELLED"
        logical["ordered_record_sha256"] = subject.canonical_sha256(
            logical["records"]
        )
        expected_logical = copy.deepcopy(logical)
        del expected_logical["status"]
        receipt["expected_logical_source_closure"] = expected_logical
        receipt["semantic_coverage"][
            "logical_source_observation_sha256"
        ] = subject.canonical_sha256(logical)
        with self.assertRaisesRegex(
            subject.ProtocolError,
            "normalization differs from plan",
        ):
            subject.cross_runtime_coverage_projection_from_schema6(
                receipt, plan,
            )

    def test_schema6_projection_rejects_plan_splice_and_overclaim(self) -> None:
        receipt, plan = schema6_fixture()
        spliced = copy.deepcopy(plan)
        spliced["generated_inputs"]["bindings"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(subject.ProtocolError, "plan differs"):
            subject.coverage_projection_from_schema6(receipt, spliced)
        for label, mutate in (
            ("diagnostic", lambda item: item.update(diagnostic_only=True)),
            ("receipt approval", lambda item: item.update(s2_s3_evidence=True)),
            ("contract approval", lambda item: item[
                "evidence_contract"
            ].update(semantic_approval_included=True)),
            ("contract PFT", lambda item: item[
                "evidence_contract"
            ].update(pft_used=True)),
            ("coverage PFT", lambda item: item[
                "semantic_coverage"
            ].update(pft_used=True)),
        ):
            forged = copy.deepcopy(receipt)
            mutate(forged)
            with self.subTest(label=label), self.assertRaises(
                subject.ProtocolError,
            ):
                subject.coverage_projection_from_schema6(forged, plan)

    def test_schema6_projection_rejects_detached_observation_sections(self) -> None:
        receipt, plan = schema6_fixture()
        original = subject.coverage_projection_from_schema6(receipt, plan)
        changed_outcome = copy.deepcopy(receipt)
        changed_outcome["action_events"][0]["outcome"] = "skip-ledger"
        self.assertNotEqual(
            subject.coverage_projection_from_schema6(changed_outcome, plan),
            original,
        )
        cases = (
            lambda item: item["logical_source_closure"]["records"][0].update(
                source_sha256="0" * 64,
            ),
            lambda item: item["physical_source_trace"]["events"][0].update(
                cache_before="prior-cache",
            ),
            lambda item: item["lp_certificate_consumption"]["records"][0].update(
                event_count=0,
            ),
        )
        for index, mutate in enumerate(cases):
            forged = copy.deepcopy(receipt)
            mutate(forged)
            with self.subTest(index=index), self.assertRaises(
                subject.ProtocolError,
            ):
                subject.coverage_projection_from_schema6(forged, plan)

    def test_authenticated_schema6_capture_binds_sources_and_authority(self) -> None:
        receipt, plan = schema6_fixture()
        authority = {
            "policy": subject.AUTHENTICATED_CAPTURE_POLICY,
            "consumer_project_commit": "1" * 40,
            "candle_commit": "c" * 40,
            "cakeml_commit": "2" * 40,
            "hol4_commit": "3" * 40,
            "flyspeck_commit": "f" * 40,
        }
        capture = subject.build_authenticated_schema6_capture(
            receipt, plan, authority,
        )
        self.assertIs(
            subject.validate_authenticated_schema6_capture(
                capture, receipt=receipt, authenticated_plan=plan,
                expected_authority=authority,
            ), capture,
        )
        self.assertFalse(capture["approval_included"])
        self.assertFalse(capture["promotion"])
        self.assertFalse(capture["direct_s2_execution_approved"])
        self.assertFalse(capture["direct_s3_coverage_approved"])
        self.assertFalse(capture["v1_3_s3_release_approved"])
        self.assertFalse(capture["pft_used"])
        self.assertFalse(capture["s2_s3_evidence"])
        self.assertEqual(
            capture["kind"], subject.COMPILED_DIRECT_CANDIDATE_KIND,
        )

        for label, mutate in (
            ("receipt digest", lambda item: item["receipt"].update(
                sha256="0" * 64,
            )),
            ("semantic projection", lambda item: item[
                "semantic_projection"
            ]["theorems"][0].update(theorem_sha256="0" * 64)),
            ("approval", lambda item: item.update(approval_included=True)),
            ("direct S2", lambda item: item.update(
                direct_s2_execution_approved=True,
            )),
            ("direct S3", lambda item: item.update(
                direct_s3_coverage_approved=True,
            )),
            ("release S3", lambda item: item.update(
                v1_3_s3_release_approved=True,
            )),
            ("PFT", lambda item: item.update(pft_used=True)),
            *((field, lambda item, field=field: item["authority"].update({
                field: "0" * 40,
            })) for field in (
                "consumer_project_commit", "candle_commit", "cakeml_commit",
                "hol4_commit", "flyspeck_commit",
            )),
        ):
            forged = copy.deepcopy(capture)
            mutate(forged)
            with self.subTest(label=label), self.assertRaises(
                subject.ProtocolError,
            ):
                subject.validate_authenticated_schema6_capture(
                    forged, receipt=receipt, authenticated_plan=plan,
                    expected_authority=authority,
                )

    def test_capture_rejects_a_spliced_source_pair(self) -> None:
        receipt, plan = schema6_fixture()
        capture = subject.build_authenticated_schema6_capture(receipt, plan, {
            "policy": subject.AUTHENTICATED_CAPTURE_POLICY,
            "consumer_project_commit": "1" * 40,
            "candle_commit": "c" * 40,
            "cakeml_commit": "2" * 40,
            "hol4_commit": "3" * 40,
            "flyspeck_commit": "f" * 40,
        })
        spliced_plan = copy.deepcopy(plan)
        spliced_plan["action_count"] = 296
        with self.assertRaises(subject.ProtocolError):
            subject.validate_authenticated_schema6_capture(
                capture, receipt=receipt, authenticated_plan=spliced_plan,
                expected_authority=capture["authority"],
            )

    def test_schema6_projection_rejects_nonfresh_or_checkpointed_execution(
        self,
    ) -> None:
        receipt, plan = schema6_fixture()
        capture_authority = {
            "policy": subject.AUTHENTICATED_CAPTURE_POLICY,
            "consumer_project_commit": "1" * 40,
            "candle_commit": "c" * 40,
            "cakeml_commit": "2" * 40,
            "hol4_commit": "3" * 40,
            "flyspeck_commit": "f" * 40,
        }
        for field, value in (
            ("fresh_process_replay_from_action_zero", False),
            ("cooperative_build_run_lock_held", False),
            ("concurrent_mutation_model", "forged"),
            ("process_state_checkpoint", {"forged": "checkpoint"}),
            ("runtime_environment_policy", "forged"),
        ):
            forged = copy.deepcopy(receipt)
            forged[field] = value
            with self.subTest(field=field), self.assertRaises(
                subject.ProtocolError,
            ):
                subject.build_authenticated_schema6_capture(
                    forged, plan, capture_authority,
                )

    def test_unapproved_three_way_comparison_fixture_is_exact(self) -> None:
        semantic = subject.project_authenticated_semantic_observations(*fixture())
        coverage = coverage_fixture()
        content = lambda byte, length: {
            "bytes": length,
            "sha256": byte * 64,
            "md5": byte * 32,
        }
        plan_record = content("1", 101)
        compiled_record = content("2", 102)
        reference_records = [content("3", 103), content("4", 104)]
        source = lambda path, byte: {
            "path": path, "bytes": 10,
            "sha256": byte * 64, "md5": byte * 32,
        }
        authority = {
            "policy": subject.COMPARISON_AUTHORITY_POLICY,
            "reviewer_project_commit": "5" * 40,
            "reviewer_sources": [source("scripts/reviewer.py", "5")],
            "reviewer_entrypoint": source("scripts/reviewer.py", "5"),
            "compiled_producer_project_commit": "6" * 40,
            "compiled_runtime_commit": "b" * 40,
            "compiled_consumer_sources": [
                source("scripts/compiled-consumer.py", "6"),
            ],
            "compiled_producer_entrypoint": source(
                "scripts/compiled-consumer.py", "6",
            ),
            "reference_producer_project_commit": "7" * 40,
            "reference_runtime_commit": "c" * 40,
            "reference_validator_sources": [
                source("scripts/reference-validator.py", "7"),
            ],
            "reference_producer_entrypoint": source(
                "scripts/reference-validator.py", "7",
            ),
        }
        comparison = {
            "schema": 1,
            "kind": subject.INDEPENDENT_COMPARISON_KIND,
            "policy": subject.INDEPENDENT_COMPARISON_POLICY,
            "boundary_id": subject.FINAL_BOUNDARY_ID,
            "action_count": subject.FINAL_ACTION_COUNT,
            "authenticated_plan": plan_record,
            "compiled_candidate": {
                "candidate": compiled_record,
                "attempt_nonce": "8" * 32,
            },
            "reference_candidates": [{
                "ordinal": 1, "candidate": reference_records[0],
                "session_nonce": "9" * 64,
            }, {
                "ordinal": 2, "candidate": reference_records[1],
                "session_nonce": "a" * 64,
            }],
            "semantic_projection": semantic,
            "coverage_projection": coverage,
            "authority": authority,
            "comparison_status": "three-way-exact-match-unapproved",
            "promotion_allowed": False,
            "approval_included": False,
            "direct_s2_execution_approved": False,
            "direct_s3_coverage_approved": False,
            "v1_3_s3_release_approved": False,
            "pft_used": False,
            "s2_s3_evidence": False,
        }

        def candidate_authority(role, index):
            compiled = role == subject.COMPILED_COMPARISON_ROLE
            authority_byte = "6" if compiled else "7"
            runtime_byte = "b" if compiled else "c"
            entrypoint = source(
                ("scripts/compiled-consumer.py" if compiled else
                 "scripts/reference-validator.py"),
                authority_byte,
            )
            return {
                "policy": subject.COMPARISON_CANDIDATE_AUTHORITY_POLICY,
                "authenticator": (
                    subject.COMPILED_COMPARISON_AUTHENTICATOR if compiled else
                    subject.REFERENCE_COMPARISON_AUTHENTICATOR
                ),
                "project_commit": authority_byte * 40,
                "runtime_commit": runtime_byte * 40,
                "entrypoint": entrypoint,
                "sources": [copy.deepcopy(entrypoint)],
            }

        descriptors = []
        for index, candidate in enumerate(
            [compiled_record, *reference_records]
        ):
            compiled = index == 0
            role = (
                subject.COMPILED_COMPARISON_ROLE
                if compiled else subject.REFERENCE_COMPARISON_ROLE
            )
            descriptors.append({
                "schema": 1,
                "kind": subject.AUTHENTICATED_COMPARISON_DESCRIPTOR_KIND,
                "role": role,
                "ordinal": index,
                "candidate": copy.deepcopy(candidate),
                "authenticated_nonce": {
                    "kind": (
                        subject.COMPILED_COMPARISON_NONCE_KIND if compiled else
                        subject.REFERENCE_COMPARISON_NONCE_KIND
                    ),
                    "value": (comparison["compiled_candidate"]["attempt_nonce"]
                              if compiled else comparison["reference_candidates"]
                              [index - 1]["session_nonce"]),
                },
                "authenticated_plan": copy.deepcopy(plan_record),
                "semantic_projection": copy.deepcopy(semantic),
                "coverage_projection": copy.deepcopy(coverage),
                "candidate_authority": candidate_authority(role, index),
                "pft_used": False,
            })
        arguments = {
            "authenticated_candidate_descriptors": descriptors,
            "expected_authority": authority,
        }
        self.assertIs(
            subject.validate_unapproved_direct_comparison_fixture(
                comparison, **arguments,
            ), comparison,
        )
        self.assertEqual(
            subject.validate_canonical_unapproved_direct_comparison_fixture_bytes(
                subject.canonical_json_bytes(comparison), **arguments,
            ), comparison,
        )
        with self.assertRaisesRegex(subject.ProtocolError, "not canonical"):
            subject.validate_canonical_unapproved_direct_comparison_fixture_bytes(
                subject.canonical_value_bytes(comparison), **arguments,
            )

        def change_coverage(_item, candidate_arguments):
            action_events = candidate_arguments[
                "authenticated_candidate_descriptors"
            ][2]["coverage_projection"]["action_events"]
            action_events["records"][0]["source_sha256"] = "0" * 64
            action_events["ordered_record_sha256"] = subject.canonical_sha256(
                action_events["records"]
            )

        def inject_pft_source(item, candidate_arguments):
            item["authority"]["reference_validator_sources"][0]["path"] = (
                "scripts/pft-results.py"
            )
            candidate_arguments["expected_authority"][
                "reference_validator_sources"
            ][0]["path"] = "scripts/pft-results.py"

        def remove_authority_independence(item, candidate_arguments):
            compiled_entrypoint = copy.deepcopy(
                item["authority"]["compiled_producer_entrypoint"]
            )
            item["authority"]["reviewer_entrypoint"] = compiled_entrypoint
            item["authority"]["reviewer_sources"] = [
                copy.deepcopy(compiled_entrypoint)
            ]
            candidate_arguments["expected_authority"] = copy.deepcopy(
                item["authority"]
            )

        def hide_identical_entrypoint_content(item, candidate_arguments):
            reviewer = item["authority"]["reviewer_entrypoint"]
            compiled = item["authority"]["compiled_producer_entrypoint"]
            for field in ("bytes", "sha256", "md5"):
                reviewer[field] = compiled[field]
                item["authority"]["reviewer_sources"][0][field] = (
                    compiled[field]
                )
            candidate_arguments["expected_authority"] = copy.deepcopy(
                item["authority"]
            )

        def use_coercible_expected_bytes(
            item, candidate_arguments, replacement,
        ):
            item["authority"]["reviewer_sources"][0]["bytes"] = 1
            item["authority"]["reviewer_entrypoint"]["bytes"] = 1
            candidate_arguments["expected_authority"] = copy.deepcopy(
                item["authority"]
            )
            candidate_arguments["expected_authority"][
                "reviewer_sources"
            ][0]["bytes"] = replacement
            candidate_arguments["expected_authority"][
                "reviewer_entrypoint"
            ]["bytes"] = replacement

        cases = (
            ("claim", lambda item, args: item.update(
                direct_s3_coverage_approved=True,
            )),
            ("bool ordinal", lambda item, args: item[
                "reference_candidates"
            ][0].update(ordinal=True)),
            ("duplicate nonce", lambda item, args: item[
                "reference_candidates"
            ][1].update(session_nonce="9" * 64)),
            ("duplicate candidate", lambda item, args: item[
                "reference_candidates"
            ][1].update(candidate=copy.deepcopy(reference_records[0]))),
            ("candidate descriptor splice", lambda item, args: args[
                "authenticated_candidate_descriptors"
            ][0].update(candidate=copy.deepcopy(reference_records[0]))),
            ("candidate plan splice", lambda item, args: args[
                "authenticated_candidate_descriptors"
            ][1].update(authenticated_plan=content("e", 105))),
            ("candidate nonce splice", lambda item, args: args[
                "authenticated_candidate_descriptors"
            ][2]["authenticated_nonce"].update(value="b" * 64)),
            ("candidate PFT bit", lambda item, args: args[
                "authenticated_candidate_descriptors"
            ][1].update(pft_used=True)),
            ("reviewer descendant", lambda item, args: item[
                "authority"
            ].update(reviewer_project_commit="b" * 40)),
            ("PFT source", inject_pft_source),
            ("dependent reviewer", remove_authority_independence),
            ("path-hidden identical reviewer", hide_identical_entrypoint_content),
            ("boolean expected bytes", lambda item, args:
             use_coercible_expected_bytes(item, args, True)),
            ("float expected bytes", lambda item, args:
             use_coercible_expected_bytes(item, args, 1.0)),
            ("boolean plan bytes", lambda item, args: item[
                "authenticated_plan"
            ].update(bytes=True)),
            ("boolean candidate bytes", lambda item, args: item[
                "compiled_candidate"
            ]["candidate"].update(bytes=True)),
            ("float reference bytes", lambda item, args: item[
                "reference_candidates"
            ][0]["candidate"].update(bytes=103.0)),
            ("float descriptor bytes", lambda item, args: args[
                "authenticated_candidate_descriptors"
            ][1]["candidate"].update(bytes=103.0)),
            ("compiled authority drift", lambda item, args: args[
                "authenticated_candidate_descriptors"
            ][0]["candidate_authority"].update(runtime_commit="d" * 40)),
            ("reference authority drift", lambda item, args: args[
                "authenticated_candidate_descriptors"
            ][2]["candidate_authority"].update(runtime_commit="d" * 40)),
            ("semantic mismatch", lambda item, args: args[
                "authenticated_candidate_descriptors"
            ][2]["semantic_projection"]["theorems"][0].update(
                theorem_sha256="0" * 64,
            )),
            ("coverage mismatch", change_coverage),
        )
        for label, mutate in cases:
            forged = copy.deepcopy(comparison)
            forged_arguments = copy.deepcopy(arguments)
            mutate(forged, forged_arguments)
            with self.subTest(label=label), self.assertRaises(
                subject.ProtocolError,
            ):
                subject.validate_unapproved_direct_comparison_fixture(
                    forged, **forged_arguments,
                )

    def test_coverage_requires_exact_final_boundary_count_and_no_pft(self) -> None:
        for field, value in (
            ("boundary_id", "06-text_formalization-through-290"),
            ("completed_action_count", 296),
            ("completed_action_count", True),
            ("pft_used", True),
        ):
            projection = coverage_fixture()
            projection[field] = value
            with self.assertRaisesRegex(subject.ProtocolError, "identity or claim"):
                subject.validate_coverage_projection(projection)

    def test_action_coverage_omission_reorder_and_outcome_reject(self) -> None:
        projection = coverage_fixture()
        projection["action_events"]["records"].pop()
        with self.assertRaisesRegex(subject.ProtocolError, "exactly 297"):
            subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        projection["action_events"]["records"][0]["index"] = 1
        projection["action_events"]["ordered_record_sha256"] = (
            subject.canonical_sha256(projection["action_events"]["records"])
        )
        with self.assertRaisesRegex(subject.ProtocolError, "action coverage record"):
            subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        projection["action_events"]["records"][10]["outcome"] = (
            "skip-loader-cache"
        )
        projection["action_events"]["ordered_record_sha256"] = (
            subject.canonical_sha256(projection["action_events"]["records"])
        )
        with self.assertRaisesRegex(subject.ProtocolError, "action coverage record"):
            subject.validate_coverage_projection(projection)

    def test_logical_coverage_reorder_and_normalization_reject(self) -> None:
        projection = coverage_fixture()
        records = projection["logical_source_coverage"]["records"]
        records[0], records[1] = records[1], records[0]
        for index, record in enumerate(records):
            record["index"] = index
        projection["logical_source_coverage"]["ordered_record_sha256"] = (
            subject.canonical_sha256(records)
        )
        with self.assertRaisesRegex(subject.ProtocolError, "not canonical"):
            subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        normalization = projection["logical_source_coverage"]["records"][4][
            "execution_normalization"
        ]
        normalization["normalized_sha256"] = "not-a-hash"
        projection["logical_source_coverage"]["ordered_record_sha256"] = (
            subject.canonical_sha256(
                projection["logical_source_coverage"]["records"]
            )
        )
        with self.assertRaisesRegex(subject.ProtocolError, "normalized SHA-256"):
            subject.validate_coverage_projection(projection)
        for unsafe_id in (
            "PFT-instrumented", "normalization-pft-results-v1",
            "normalization_pft_trace_v1", "normalization\ncontrol-v1",
        ):
            projection = coverage_fixture()
            normalization = projection["logical_source_coverage"]["records"][4][
                "execution_normalization"
            ]
            normalization["id"] = unsafe_id
            projection["logical_source_coverage"]["ordered_record_sha256"] = (
                subject.canonical_sha256(
                    projection["logical_source_coverage"]["records"]
                )
            )
            with self.subTest(unsafe_id=unsafe_id), self.assertRaises(
                subject.ProtocolError,
            ):
                subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        records = projection["logical_source_coverage"]["records"]
        records[4]["key"] = "flyspeck:c.hl"
        projection["logical_source_coverage"]["ordered_record_sha256"] = (
            subject.canonical_sha256(records)
        )
        with self.assertRaisesRegex(subject.ProtocolError, "logical and physical"):
            subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        projection["logical_source_coverage"]["kind"] = (
            subject.RAW_SOURCE_CLOSURE_KIND
        )
        with self.assertRaisesRegex(subject.ProtocolError, "malformed"):
            subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        logical = projection["logical_source_coverage"]
        logical["records"][4]["key"] = "pft:trace"
        logical["ordered_record_sha256"] = subject.canonical_sha256(
            logical["records"]
        )
        physical = projection["physical_source_coverage"]
        physical["events"][7]["key"] = "pft:trace"
        physical["ordered_event_sha256"] = subject.canonical_sha256(
            physical["events"]
        )
        physical["observed_keys"] = sorted(
            "pft:trace" if key == "flyspeck:b.hl" else key
            for key in physical["observed_keys"]
        )
        physical["ordered_observed_key_sha256"] = subject.canonical_sha256(
            physical["observed_keys"]
        )
        with self.assertRaisesRegex(subject.ProtocolError, "PFT namespace"):
            subject.validate_coverage_projection(projection)
        for unsafe in ("cert\x00.dat", "cert\n.dat", "cert\t.dat"):
            projection = coverage_fixture()
            bindings = projection["generated_inputs"]["bindings"]
            original = bindings[0]["path"]
            bindings[0]["path"] = unsafe
            projection["generated_inputs"]["ordered_binding_sha256"] = (
                subject.canonical_sha256(bindings)
            )
            records = projection["lp_certificate_consumption"]["records"]
            for record in records:
                if record["relative"] == original:
                    record["relative"] = unsafe
                    break
            projection["lp_certificate_consumption"][
                "ordered_record_sha256"
            ] = subject.canonical_sha256(records)
            with self.assertRaisesRegex(subject.ProtocolError, "malformed"):
                subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        logical = projection["logical_source_coverage"]
        logical["records"][0]["key"] = "control:fingerprint-serializer"
        logical["ordered_record_sha256"] = subject.canonical_sha256(
            logical["records"]
        )
        physical = projection["physical_source_coverage"]
        physical["events"][3]["key"] = "control:fingerprint-serializer"
        physical["ordered_event_sha256"] = subject.canonical_sha256(
            physical["events"]
        )
        physical["observed_keys"].remove("candle:candle/build/insulate.ml")
        physical["observed_key_count"] -= 1
        physical["ordered_observed_key_sha256"] = subject.canonical_sha256(
            physical["observed_keys"]
        )
        with self.assertRaisesRegex(subject.ProtocolError, "namespace|reserved"):
            subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        logical = projection["logical_source_coverage"]
        logical["records"][4]["classification"] = "derivation-only-input"
        logical["ordered_record_sha256"] = subject.canonical_sha256(
            logical["records"]
        )
        with self.assertRaisesRegex(subject.ProtocolError, "classification closure"):
            subject.validate_coverage_projection(projection)

    def test_physical_coverage_parent_cache_outcome_and_terminal_reject(self) -> None:
        for event_index, field, value, message in (
            (7, "parent", None, "parent mismatch"),
            (7, "cache_before", "prior-cache", "cache state mismatch"),
            (8, "outcome", "cache-skip", "outcome mismatch"),
            (18, "request_count", 8, "terminal mismatch"),
        ):
            projection = coverage_fixture()
            events = projection["physical_source_coverage"]["events"]
            events[event_index][field] = value
            projection["physical_source_coverage"]["ordered_event_sha256"] = (
                subject.canonical_sha256(events)
            )
            with self.assertRaisesRegex(subject.ProtocolError, message):
                subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        projection["physical_source_coverage"]["nonce"] = "0" * 32
        with self.assertRaisesRegex(subject.ProtocolError, "malformed"):
            subject.validate_coverage_projection(projection)

    def test_generated_input_omission_duplicate_and_type_reject(self) -> None:
        projection = coverage_fixture()
        projection["generated_inputs"]["bindings"].pop()
        with self.assertRaisesRegex(subject.ProtocolError, "exactly 43"):
            subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        bindings = projection["generated_inputs"]["bindings"]
        bindings[1]["path"] = bindings[0]["path"]
        projection["generated_inputs"]["ordered_binding_sha256"] = (
            subject.canonical_sha256(bindings)
        )
        with self.assertRaisesRegex(subject.ProtocolError, "duplicate"):
            subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        projection["generated_inputs"]["bindings"][0]["bytes"] = True
        with self.assertRaisesRegex(subject.ProtocolError, "generated-input record"):
            subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        bindings = projection["generated_inputs"]["bindings"]
        for record in bindings[-4:]:
            record["class"] = "lp-archive"
        projection["generated_inputs"]["ordered_binding_sha256"] = (
            subject.canonical_sha256(bindings)
        )
        with self.assertRaisesRegex(subject.ProtocolError, "class closure"):
            subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        bindings = projection["generated_inputs"]["bindings"]
        bindings[0]["path"] = "pft/trace/cert-00.dat"
        projection["generated_inputs"]["ordered_binding_sha256"] = (
            subject.canonical_sha256(bindings)
        )
        records = projection["lp_certificate_consumption"]["records"]
        records[0]["relative"] = bindings[0]["path"]
        projection["lp_certificate_consumption"]["ordered_record_sha256"] = (
            subject.canonical_sha256(records)
        )
        with self.assertRaisesRegex(subject.ProtocolError, "PFT namespace"):
            subject.validate_coverage_projection(projection)

    def test_certificate_consumption_positive_exact_and_pft_free(self) -> None:
        projection = coverage_fixture()
        projection["lp_certificate_consumption"]["records"][0]["event_count"] = 0
        projection["lp_certificate_consumption"]["ordered_record_sha256"] = (
            subject.canonical_sha256(
                projection["lp_certificate_consumption"]["records"]
            )
        )
        with self.assertRaisesRegex(subject.ProtocolError, "consumption record"):
            subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        projection["lp_certificate_consumption"]["records"][0]["event_count"] = 2
        projection["lp_certificate_consumption"]["ordered_record_sha256"] = (
            subject.canonical_sha256(
                projection["lp_certificate_consumption"]["records"]
            )
        )
        with self.assertRaisesRegex(subject.ProtocolError, "consumption record"):
            subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        projection["lp_certificate_consumption"]["unmatched_event_count"] = 1
        with self.assertRaisesRegex(subject.ProtocolError, "consumption coverage"):
            subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        projection["lp_certificate_consumption"]["pft_used"] = True
        with self.assertRaisesRegex(subject.ProtocolError, "consumption coverage"):
            subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        projection["lp_certificate_consumption"]["records"][0]["sha256"] = "0" * 64
        projection["lp_certificate_consumption"]["ordered_record_sha256"] = (
            subject.canonical_sha256(
                projection["lp_certificate_consumption"]["records"]
            )
        )
        with self.assertRaisesRegex(subject.ProtocolError, "differs from generated"):
            subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        records = projection["lp_certificate_consumption"]["records"]
        records.reverse()
        for index, record in enumerate(records):
            record["index"] = index
        projection["lp_certificate_consumption"]["ordered_record_sha256"] = (
            subject.canonical_sha256(records)
        )
        with self.assertRaisesRegex(subject.ProtocolError, "runtime order"):
            subject.validate_coverage_projection(projection)
        projection = coverage_fixture()
        records = projection["lp_certificate_consumption"]["records"]
        records[1]["ordered_nonce_free_event_sha256"] = records[0][
            "ordered_nonce_free_event_sha256"
        ]
        projection["lp_certificate_consumption"]["ordered_record_sha256"] = (
            subject.canonical_sha256(records)
        )
        with self.assertRaisesRegex(subject.ProtocolError, "event digest"):
            subject.validate_coverage_projection(projection)


if __name__ == "__main__":
    unittest.main()
