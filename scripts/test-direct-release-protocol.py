#!/usr/bin/python3

from __future__ import annotations

import copy
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


class DirectReleaseProtocolTests(unittest.TestCase):
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
