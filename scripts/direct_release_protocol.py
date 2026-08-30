#!/usr/bin/python3
"""Strict pure projections for the direct Flyspeck release protocol.

This module does not authenticate a runtime result and never approves S2, S3,
or a release.  It defines strict nonce-free semantic and coverage values for a
later independent approval validator to compare after it has authenticated the
captured final-boundary observations from which they were projected.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


FINAL_BOUNDARY_ID = "07-final_assembly-through-296"
FINAL_ACTION_COUNT = 297
FINGERPRINT_SERIALIZER_PATH = "candle/fingerprint.ml"
FINAL_THEOREM_NAMES = (
    "Linear_programming_results.linear_programming_results_th",
    "Mk_all_ineq.the_nonlinear_inequalities",
    "The_kepler_conjecture.tame_nonlinear_imp_kepler_conjecture",
    "Candle_flyspeck_l2.tame_imp_kepler_conjecture",
)
DEPENDENCY_HISTORY_POLICY = (
    "serialization-full-digest-thm-sorted-dependency-history-v1"
)
SEMANTIC_PROJECTION_KIND = "candle-flyspeck-direct-semantic-projection-v1"
COVERAGE_PROJECTION_KIND = "candle-flyspeck-direct-coverage-projection-v1"
CROSS_RUNTIME_COVERAGE_KIND = (
    "candle-flyspeck-cross-runtime-coverage-projection-v2"
)
CROSS_RUNTIME_ACTION_POLICY = (
    "authenticated-plan-ordered-action-completion-v1"
)
CROSS_RUNTIME_SOURCE_INVENTORY_KIND = (
    "candle-flyspeck-authenticated-original-source-inventory-v1"
)
CROSS_RUNTIME_SOURCE_INVENTORY_POLICY = (
    "exact-400-plan-bindings-with-candle-selection-v1"
)
CROSS_RUNTIME_LOGICAL_CLOSURE_KIND = (
    "candle-flyspeck-cross-runtime-selected-logical-closure-v1"
)
CROSS_RUNTIME_LOGICAL_CLOSURE_POLICY = (
    "runtime-neutral-selected-source-identities-v1"
)
CROSS_RUNTIME_LP_CONSUMPTION_KIND = (
    "candle-flyspeck-cross-runtime-lp-consumption-v2"
)
CROSS_RUNTIME_LP_CONSUMPTION_POLICY = (
    "canonical-identity-exactly-once-successful-deserialization-v2"
)
CROSS_RUNTIME_LP_CONSUMPTION_ORDER = (
    "canonical-relative-path-lexicographic-v1"
)
CROSS_RUNTIME_EXECUTION_SELECTION_SEMANTICS = (
    "bind-candle-plan-selection-without-cross-runtime-execution-claim-v1"
)
AUTHENTICATED_CAPTURE_KIND = (
    "candle-flyspeck-authenticated-direct-schema6-capture-v2"
)
AUTHENTICATED_CAPTURE_POLICY = (
    "descriptor-held-schema6-revalidation-and-content-bound-projections-v2"
)
COMPILED_DIRECT_CANDIDATE_KIND = AUTHENTICATED_CAPTURE_KIND
INDEPENDENT_COMPARISON_KIND = (
    "candle-flyspeck-independent-direct-comparison-v2"
)
INDEPENDENT_COMPARISON_POLICY = (
    "one-compiled-plus-two-pristine-semantic-and-cross-coverage-v2"
)
COMPARISON_AUTHORITY_POLICY = (
    "independent-entrypoints-exact-commits-and-source-inventories-v2"
)
AUTHENTICATED_COMPARISON_DESCRIPTOR_KIND = (
    "candle-flyspeck-authenticated-comparison-candidate-v2"
)
COMPARISON_CANDIDATE_AUTHORITY_POLICY = (
    "candidate-authenticator-exact-entrypoint-and-sources-v1"
)
COMPILED_COMPARISON_ROLE = "compiled-direct-schema6"
REFERENCE_COMPARISON_ROLE = "pristine-clean-reference"
COMPILED_COMPARISON_AUTHENTICATOR = "compiled-schema6-consumer"
REFERENCE_COMPARISON_AUTHENTICATOR = "pristine-reference-validator"
COMPILED_COMPARISON_NONCE_KIND = "compiled-attempt-nonce-v1"
REFERENCE_COMPARISON_NONCE_KIND = "reference-session-nonce-v1"
PHYSICAL_COVERAGE_KIND = (
    "candle-flyspeck-direct-physical-source-coverage-v1"
)
CERTIFICATE_CONSUMPTION_KIND = (
    "candle-flyspeck-lp-certificate-consumption-projection-v1"
)
CERTIFICATE_CONSUMPTION_POLICY = (
    "runtime-validator-derived-nonce-free-certificate-consumption-v1"
)
RAW_SOURCE_CLOSURE_KIND = (
    "candle-flyspeck-selected-nested-logical-source-closure"
)
LOGICAL_COVERAGE_KIND = (
    "candle-flyspeck-direct-logical-source-coverage-v1"
)
SOURCE_CLOSURE_POLICY = "manifest-selected-nested-logical-reachability-v3"
SOURCE_CLOSURE_ORDER = "canonical-source-key-lexicographic-v1"
SOURCE_CLOSURE_OBSERVATION = (
    "outer-and-selected-loadt-ledger-observed-other-nested-expected"
)
SOURCE_TRACE_PROTOCOL = "candle-loader-owned-source-trace-v1"
SOURCE_TRACE_KINDS = (
    "#flyspeck_needs", "#flyspeck_loadt", "#use", "needs", "loads",
)
SOURCE_TRACE_NEED_KINDS = ("#flyspeck_needs", "needs")
SOURCE_TRACE_LOAD_KINDS = ("#flyspeck_loadt", "loads")
SOURCE_TRACE_TOP_LEVEL_CONTROLS = (
    "control:runtime-setup",
    "control:instrumented-prefix",
    "control:stratum-check",
    "control:postlude",
)
SOURCE_TRACE_FINAL_ADDITIONAL_KEYS = (
    *SOURCE_TRACE_TOP_LEVEL_CONTROLS,
    "control:fingerprint-serializer",
)
ACTION_OUTCOMES = ("load", "skip-ledger")
ACTION_STRATA = (
    "base", "arithmetic", "analysis", "geometry", "lp_support",
    "nonlinear_support", "text_formalization", "final_assembly",
)
LOGICAL_SOURCE_CLASSIFICATIONS = (
    "derivation-only-input", "expected-nested-source",
    "generated-executed-control", "observed-nested-source",
    "observed-outer-source",
)
LOGICAL_DERIVATION_KEY = "candle:candle/flyspeck_full_build.ml"
LOGICAL_GENERATED_CONTROL_KEYS = (
    "candle:candle/build/insulate.ml",
    "candle:candle/flyspeck_source_digests.ml",
)
LOGICAL_FINAL_TARGET_KEY = "candle:candle/flyspeck_l2_target.ml"
GENERATED_INPUT_CLASSES = (
    "lp-archive", "lp-certificate", "lp-certificate-archive",
    "lp-certificate-prepared", "nonlinear-case-log",
    "nonlinear-preparation",
)
GENERATED_INPUT_CLASS_COUNTS = {
    "lp-certificate": 38,
    "lp-certificate-prepared": 1,
    "lp-certificate-archive": 1,
    "lp-archive": 1,
    "nonlinear-preparation": 1,
    "nonlinear-case-log": 1,
}
CERTIFICATE_CONSUMPTION_ORDER = (
    "manifest-runtime-certificate-basename-lexicographic-v1"
)
RAW_V6_RECEIPT_FIELDS = frozenset({
    "schema", "kind", "claim", "state", "started_utc", "boundary_id",
    "diagnostic_only", "attempt_nonce", "action_count",
    "ordered_expected_action_sha256", "expected_action_events",
    "timeout_seconds", "resource_limits", "fresh_process_replay_from_action_zero",
    "cooperative_build_run_lock_held", "runtime_lock",
    "concurrent_mutation_model", "process_state_checkpoint", "evidence_contract",
    "expected_logical_source_closure", "expected_physical_source_trace",
    "semantic_evidence_plan", "lp_consumption_contract",
    "runtime_environment_policy", "runtime_environment", "inputs", "repositories",
    "finished_utc", "timed_out", "exit_code", "command", "child_resources",
    "log", "initial_attempt", "action_markers_validated", "action_events",
    "logical_source_closure", "physical_source_trace", "semantic_fingerprints",
    "dependency_history", "semantic_coverage", "lp_certificate_consumption",
    "s2_s3_evidence", "validation_error", "postflight_reauthenticated",
})
RAW_V6_CLAIM = (
    "compiled cumulative source-action, semantic, and exact LP-certificate "
    "consumption observation attempt; not S2/S3 without independent approval"
)
RAW_V6_SEMANTIC_POLICY = (
    "authenticated-direct-source-lp-consumption-nonlinear-observation-v2"
)
RAW_CONCURRENT_MUTATION_MODEL = (
    "cooperating build/launcher processes serialized; hostile same-user "
    "path mutation is outside this evidence model"
)
RAW_RUNTIME_ENVIRONMENT_POLICY = (
    "minimal PATH/LC_ALL=C/CML sizes; reject LD_*, GLIBC_TUNABLES, "
    "BASH_ENV, and ENV"
)
RAW_LP_CONSUMPTION_PROTOCOL = (
    "candle-flyspeck-lp-certificate-consumption-v1"
)
RAW_LP_CONSUMPTION_KIND = (
    "candle-flyspeck-lp-certificate-consumption-observation-v1"
)
RAW_LP_CONSUMPTION_POLICY = (
    "successful-deserialization-authenticated-runtime-table-v1"
)
HEX64 = re.compile(r"[0-9a-f]{64}")
HEX32 = re.compile(r"[0-9a-f]{32}")
PFT_NAMESPACE = re.compile(r"(?:^|[/:._-])pft(?:$|[/:._-])", re.IGNORECASE)


class ProtocolError(ValueError):
    """A direct-release protocol value is malformed or overclaims evidence."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProtocolError(message)


def canonical_value_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_value_bytes(value)).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ProtocolError(f"non-finite JSON number: {value}")


def decode_object(data: bytes, label: str) -> dict[str, Any]:
    try:
        text = data.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProtocolError(f"cannot decode {label}: {error}") from error
    require(isinstance(value, dict), f"{label} is not a JSON object")
    return value


def _hex(value: Any, pattern: re.Pattern[str], label: str) -> str:
    require(isinstance(value, str) and pattern.fullmatch(value) is not None,
            f"malformed {label}")
    return value


def _validate_serializer(value: object) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {"path", "sha256"},
            "malformed direct fingerprint serializer")
    require(value.get("path") == FINGERPRINT_SERIALIZER_PATH,
            "direct fingerprint serializer path mismatch")
    _hex(value.get("sha256"), HEX64, "direct fingerprint serializer SHA-256")
    return value


def _validate_theorems(value: object) -> list[dict[str, Any]]:
    require(isinstance(value, list) and len(value) == len(FINAL_THEOREM_NAMES),
            "direct semantic projection requires four theorem records")
    fields = {
        "name", "theorem_sha256", "hypotheses_sha256", "conclusion_sha256",
        "global_axioms_sha256", "hypothesis_count", "global_axiom_count",
    }
    result: list[dict[str, Any]] = []
    for index, (record, expected_name) in enumerate(zip(
        value, FINAL_THEOREM_NAMES, strict=True,
    )):
        require(isinstance(record, dict) and set(record) == fields,
                f"malformed direct theorem record: {index}")
        require(record.get("name") == expected_name,
                f"direct theorem order/name mismatch: {index}")
        require(type(record.get("hypothesis_count")) is int and
                record["hypothesis_count"] == 0,
                f"direct theorem has hypotheses: {index}")
        require(type(record.get("global_axiom_count")) is int and
                record["global_axiom_count"] == 3,
                f"direct theorem global-axiom count mismatch: {index}")
        for field in (
            "theorem_sha256", "hypotheses_sha256", "conclusion_sha256",
            "global_axioms_sha256",
        ):
            _hex(record.get(field), HEX64, f"direct theorem {field}: {index}")
        result.append(record)
    return result


def _validate_post_state(
    value: object, theorems: list[dict[str, Any]],
) -> dict[str, Any]:
    fields = {
        "kernel_state_sha256", "type_constants_sha256",
        "term_constants_sha256", "definitions_sha256",
        "global_axioms_sha256", "type_constant_count", "term_constant_count",
        "definition_count", "global_axiom_count",
    }
    require(isinstance(value, dict) and set(value) == fields,
            "malformed direct structural post-state")
    for field in (
        "type_constant_count", "term_constant_count", "definition_count",
    ):
        require(type(value.get(field)) is int and value[field] >= 0,
                f"malformed direct post-state count: {field}")
    require(type(value.get("global_axiom_count")) is int and
            value["global_axiom_count"] == 3,
            "direct post-state global-axiom count mismatch")
    for field in (
        "kernel_state_sha256", "type_constants_sha256",
        "term_constants_sha256", "definitions_sha256",
        "global_axioms_sha256",
    ):
        _hex(value.get(field), HEX64, f"direct post-state {field}")
    require(all(
        record["global_axioms_sha256"] == value["global_axioms_sha256"]
        for record in theorems
    ), "direct theorem/post-state global axioms differ")
    return value


def _validate_dependency_records(value: object) -> list[dict[str, Any]]:
    require(isinstance(value, list) and len(value) == len(FINAL_THEOREM_NAMES),
            "direct semantic projection requires four dependency records")
    result: list[dict[str, Any]] = []
    for index, (record, expected_name) in enumerate(zip(
        value, FINAL_THEOREM_NAMES, strict=True,
    )):
        require(isinstance(record, dict) and set(record) == {
                    "index", "name", "full_digest_md5",
                }, f"malformed direct dependency record: {index}")
        require(type(record.get("index")) is int and record["index"] == index and
                record.get("name") == expected_name,
                f"direct dependency order/name mismatch: {index}")
        _hex(record.get("full_digest_md5"), HEX32,
             f"direct dependency full digest: {index}")
        result.append(record)
    return result


def project_authenticated_semantic_observations(
    fingerprints: object, dependency_history: object,
) -> dict[str, Any]:
    """Project exact final-boundary observations without approving them.

    The caller must first authenticate both objects as members of the same
    content-bound final-attempt capture while holding that capture's pinned
    descriptors and lock.  This pure function validates values, not provenance.
    It is intentionally not exposed as a two-file command-line operation.
    """
    require(isinstance(fingerprints, dict) and set(fingerprints) == {
                "status", "approved_reference_present", "serializer",
                "theorems", "post_state",
            }, "malformed direct semantic-fingerprint observation")
    require(fingerprints.get("status") == "observed_uncompared" and
            fingerprints.get("approved_reference_present") is False,
            "direct semantic fingerprints are not an unapproved observation")
    serializer = _validate_serializer(fingerprints.get("serializer"))
    theorems = _validate_theorems(fingerprints.get("theorems"))
    post_state = _validate_post_state(fingerprints.get("post_state"), theorems)

    dependency_fields = {
        "schema", "kind", "policy", "status", "boundary_id", "record_count",
        "ordered_request_sha256", "ordered_record_sha256", "records",
        "approved_reference_present", "dependency_history_is_kernel_trace",
        "pft_used", "s2_s3_evidence",
    }
    require(isinstance(dependency_history, dict) and
            set(dependency_history) == dependency_fields,
            "malformed direct dependency-history observation")
    require(type(dependency_history.get("schema")) is int and
            dependency_history["schema"] == 1 and
            dependency_history.get("kind") ==
            "candle-flyspeck-dependency-history-observation" and
            dependency_history.get("policy") == DEPENDENCY_HISTORY_POLICY and
            dependency_history.get("status") == "observed_uncompared" and
            dependency_history.get("boundary_id") == FINAL_BOUNDARY_ID and
            type(dependency_history.get("record_count")) is int and
            dependency_history["record_count"] == len(FINAL_THEOREM_NAMES) and
            dependency_history.get("approved_reference_present") is False and
            dependency_history.get("dependency_history_is_kernel_trace") is False and
            dependency_history.get("pft_used") is False and
            dependency_history.get("s2_s3_evidence") is False,
            "direct dependency-history identity or claim mismatch")
    records = _validate_dependency_records(dependency_history.get("records"))
    require(dependency_history.get("ordered_request_sha256") ==
            canonical_sha256(list(FINAL_THEOREM_NAMES)) and
            dependency_history.get("ordered_record_sha256") ==
            canonical_sha256(records),
            "direct dependency-history digest mismatch")

    projection = {
        "schema": 1,
        "kind": SEMANTIC_PROJECTION_KIND,
        "serializer": copy.deepcopy(serializer),
        "theorems": copy.deepcopy(theorems),
        "post_state": copy.deepcopy(post_state),
        "dependency_history": copy.deepcopy(records),
    }
    return validate_semantic_projection(projection)


def validate_semantic_projection(value: object) -> dict[str, Any]:
    fields = {
        "schema", "kind", "serializer", "theorems", "post_state",
        "dependency_history",
    }
    require(isinstance(value, dict) and set(value) == fields,
            "malformed direct semantic projection")
    require(type(value.get("schema")) is int and value["schema"] == 1 and
            value.get("kind") == SEMANTIC_PROJECTION_KIND,
            "direct semantic projection identity mismatch")
    _validate_serializer(value.get("serializer"))
    theorems = _validate_theorems(value.get("theorems"))
    _validate_post_state(value.get("post_state"), theorems)
    _validate_dependency_records(value.get("dependency_history"))
    return value


def _safe_relative(value: object, label: str) -> str:
    require(isinstance(value, str) and value and "\\" not in value and
            all(ord(character) >= 32 and character != "\x7f"
                for character in value),
            f"malformed {label}")
    path = Path(value)
    require(not path.is_absolute() and path.as_posix() == value and
            all(part not in {"", ".", ".."} for part in path.parts),
            f"unsafe {label}")
    require(PFT_NAMESPACE.search(value) is None,
            f"PFT namespace is forbidden in {label}")
    return value


def _validate_action_target_alias(
    value: object, selected_source: object, label: str,
) -> str:
    """Resolve the exact Flyspeck build target lexical namespace.

    Action targets are relative to ``text_formalization``.  The real ledger
    contains one leading ``..`` for jHOLLight/formal_lp/formal_graph sources;
    no second or embedded parent segment is part of the authenticated v1.3
    target language.
    """
    require(isinstance(value, str) and value and "\\" not in value and
            all(ord(character) >= 32 and character != "\x7f"
                for character in value),
            f"malformed {label}")
    _no_pft_namespace(value, label)
    path = Path(value)
    parts = path.parts
    require(not path.is_absolute() and path.as_posix() == value and parts and
            all(part not in {"", "."} for part in parts) and
            sum(part == ".." for part in parts) <= 1 and
            (".." not in parts or parts[0] == ".."),
            f"unsafe {label}")
    resolved = ["text_formalization"]
    for part in parts:
        if part == "..":
            require(len(resolved) == 1, f"unsafe {label}")
            resolved.pop()
        else:
            resolved.append(part)
    require(resolved and isinstance(selected_source, str) and
            selected_source == f"flyspeck:{'/'.join(resolved)}",
            f"{label} does not resolve to selected source")
    return value


def _no_pft_namespace(value: str, label: str) -> str:
    require(PFT_NAMESPACE.search(value) is None,
            f"PFT namespace is forbidden in {label}")
    return value


def _validate_printable_label(value: object, label: str) -> str:
    require(isinstance(value, str) and value and
            all(ord(character) >= 32 and character != "\x7f"
                for character in value),
            f"malformed {label}")
    return _no_pft_namespace(value, label)


def _validate_logical_source_key(value: str, label: str) -> str:
    _no_pft_namespace(value, label)
    repository, separator, relative = value.partition(":")
    require(separator == ":" and repository in {"candle", "flyspeck"},
            f"malformed {label} namespace")
    _safe_relative(relative, label)
    return value


def _validate_action_coverage(value: object) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {
                "record_count", "ordered_record_sha256", "records",
            }, "malformed direct action coverage")
    records = value.get("records")
    require(isinstance(records, list) and len(records) == FINAL_ACTION_COUNT and
            type(value.get("record_count")) is int and
            value["record_count"] == FINAL_ACTION_COUNT,
            "direct action coverage is not exactly 297 records")
    for index, record in enumerate(records):
        require(isinstance(record, dict) and set(record) == {
                    "index", "source_sha256", "logical_source_delta_sha256",
                    "outcome",
                } and type(record.get("index")) is int and
                record["index"] == index and
                record.get("outcome") in ACTION_OUTCOMES,
                f"malformed direct action coverage record: {index}")
        _hex(record.get("source_sha256"), HEX64,
             f"direct action source SHA-256: {index}")
        _hex(record.get("logical_source_delta_sha256"), HEX64,
             f"direct action logical-source digest: {index}")
    require(value.get("ordered_record_sha256") == canonical_sha256(records),
            "direct action coverage digest mismatch")
    return value


def _validate_logical_source_coverage(value: object) -> dict[str, Any]:
    fields = {
        "schema", "kind", "policy", "order", "record_count",
        "ordered_record_sha256", "records", "execution_observation",
        "self_certifies_nested_execution",
    }
    require(isinstance(value, dict) and set(value) == fields and
            type(value.get("schema")) is int and value["schema"] == 1 and
            value.get("kind") == LOGICAL_COVERAGE_KIND and
            value.get("policy") == SOURCE_CLOSURE_POLICY and
            value.get("order") == SOURCE_CLOSURE_ORDER and
            value.get("execution_observation") == SOURCE_CLOSURE_OBSERVATION and
            value.get("self_certifies_nested_execution") is False,
            "malformed direct logical-source coverage")
    records = value.get("records")
    require(isinstance(records, list) and records and
            type(value.get("record_count")) is int and
            value["record_count"] == len(records),
            "malformed direct logical-source coverage records")
    previous_key: str | None = None
    for index, record in enumerate(records):
        require(isinstance(record, dict) and set(record) == {
                    "index", "key", "classification", "source_sha256",
                    "source_md5", "execution_normalization",
                } and type(record.get("index")) is int and
                record["index"] == index and
                isinstance(record.get("key"), str) and record["key"] and
                record.get("classification") in LOGICAL_SOURCE_CLASSIFICATIONS,
                f"malformed direct logical-source record: {index}")
        require(previous_key is None or previous_key < record["key"],
                f"direct logical-source keys are not canonical: {index}")
        _validate_logical_source_key(
            record["key"], f"direct logical-source key: {index}",
        )
        previous_key = record["key"]
        _hex(record.get("source_sha256"), HEX64,
             f"direct logical-source SHA-256: {index}")
        _hex(record.get("source_md5"), HEX32,
             f"direct logical-source MD5: {index}")
        normalization = record.get("execution_normalization")
        require(normalization is None or (
            isinstance(normalization, dict) and set(normalization) == {
                "id", "normalized_sha256", "normalized_md5",
            }
        ), f"malformed direct logical-source normalization: {index}")
        if isinstance(normalization, dict):
            _validate_printable_label(
                normalization.get("id"),
                f"direct logical-source normalization ID: {index}",
            )
            _hex(normalization.get("normalized_sha256"), HEX64,
                 f"direct logical-source normalized SHA-256: {index}")
            _hex(normalization.get("normalized_md5"), HEX32,
                 f"direct logical-source normalized MD5: {index}")
    require(value.get("ordered_record_sha256") == canonical_sha256(records),
            "direct logical-source coverage digest mismatch")
    classification_keys = {
        classification: {
            record["key"] for record in records
            if record["classification"] == classification
        }
        for classification in LOGICAL_SOURCE_CLASSIFICATIONS
    }
    require(classification_keys["derivation-only-input"] == {
                LOGICAL_DERIVATION_KEY
            } and
            classification_keys["generated-executed-control"] ==
            set(LOGICAL_GENERATED_CONTROL_KEYS) and
            any(record["key"] == LOGICAL_FINAL_TARGET_KEY and
                record["classification"] == "expected-nested-source"
                for record in records),
            "direct logical-source classification closure mismatch")
    return value


def _validate_physical_source_coverage(value: object) -> dict[str, Any]:
    fields = {
        "schema", "kind", "protocol", "event_count", "ordered_event_sha256",
        "events", "request_count", "cache_skip_count", "observed_key_count",
        "ordered_observed_key_sha256", "observed_keys", "status",
    }
    require(isinstance(value, dict) and set(value) == fields and
            type(value.get("schema")) is int and value["schema"] == 1 and
            value.get("kind") == PHYSICAL_COVERAGE_KIND and
            value.get("protocol") == SOURCE_TRACE_PROTOCOL and
            value.get("status") == "closed-loader-owned-session",
            "malformed direct physical-source coverage")
    events = value.get("events")
    require(isinstance(events, list) and events and
            type(value.get("event_count")) is int and
            value["event_count"] == len(events) and
            value.get("ordered_event_sha256") == canonical_sha256(events),
            "direct physical-source event closure mismatch")
    active: list[tuple[int, str]] = []
    cached_keys: set[str] = set()
    observed_keys: set[str] = set()
    top_level_keys: list[str] = []
    request_count = 0
    cache_skip_count = 0
    terminal_seen = False
    for event_index, event in enumerate(events):
        require(isinstance(event, dict) and not terminal_seen,
                f"malformed direct physical-source event: {event_index}")
        event_type = event.get("event")
        if event_type == "request":
            require(set(event) == {
                        "event", "id", "parent", "kind", "key", "cache_before",
                    } and type(event.get("id")) is int and
                    event["id"] == request_count and
                    (event.get("parent") is None or
                     type(event.get("parent")) is int) and
                    event.get("kind") in SOURCE_TRACE_KINDS and
                    isinstance(event.get("key"), str) and event["key"] and
                    event.get("cache_before") in {"fresh-cache", "prior-cache"},
                    f"malformed direct physical-source request: {event_index}")
            _no_pft_namespace(
                event["key"],
                f"direct physical-source key: {event_index}",
            )
            parent = active[-1][0] if active else None
            require(event["parent"] == parent,
                    f"direct physical-source parent mismatch: {event_index}")
            prior = event["key"] in cached_keys
            require(event["cache_before"] ==
                    ("prior-cache" if prior else "fresh-cache"),
                    f"direct physical-source cache state mismatch: {event_index}")
            expected_outcome = (
                "cache-skip"
                if event["kind"] in SOURCE_TRACE_NEED_KINDS and prior
                else "evaluated"
            )
            if (event["kind"] in
                    SOURCE_TRACE_NEED_KINDS + SOURCE_TRACE_LOAD_KINDS and
                    not prior):
                cached_keys.add(event["key"])
            if parent is None:
                top_level_keys.append(event["key"])
            observed_keys.add(event["key"])
            active.append((event["id"], expected_outcome))
            request_count += 1
        elif event_type == "outcome":
            require(set(event) == {"event", "id", "outcome"} and active and
                    type(event.get("id")) is int and
                    event["id"] == active[-1][0] and
                    event.get("outcome") == active[-1][1],
                    f"direct physical-source outcome mismatch: {event_index}")
            if event["outcome"] == "cache-skip":
                cache_skip_count += 1
            active.pop()
        elif event_type == "terminal":
            require(set(event) == {"event", "request_count"} and
                    event_index == len(events) - 1 and not active and
                    type(event.get("request_count")) is int and
                    event["request_count"] == request_count,
                    "direct physical-source terminal mismatch")
            terminal_seen = True
        else:
            raise ProtocolError(
                f"unknown direct physical-source event: {event_index}"
            )
    require(terminal_seen and
            top_level_keys == list(SOURCE_TRACE_TOP_LEVEL_CONTROLS),
            "direct physical-source top-level controls mismatch")
    ordered_keys = sorted(observed_keys)
    require(type(value.get("request_count")) is int and
            value["request_count"] == request_count and
            type(value.get("cache_skip_count")) is int and
            value["cache_skip_count"] == cache_skip_count and
            type(value.get("observed_key_count")) is int and
            value["observed_key_count"] == len(ordered_keys) and
            value.get("observed_keys") == ordered_keys and
            value.get("ordered_observed_key_sha256") ==
            canonical_sha256(ordered_keys),
            "direct physical-source observed closure mismatch")
    return value


def _validate_generated_inputs(value: object) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {
                "contract_sha256", "receipt_sha256", "entry_count",
                "ordered_binding_sha256", "bindings",
            }, "malformed direct generated-input coverage")
    _hex(value.get("contract_sha256"), HEX64,
         "direct generated-input contract SHA-256")
    _hex(value.get("receipt_sha256"), HEX64,
         "direct generated-input receipt SHA-256")
    bindings = value.get("bindings")
    require(isinstance(bindings, list) and len(bindings) == 43 and
            type(value.get("entry_count")) is int and value["entry_count"] == 43,
            "direct generated-input coverage is not exactly 43 records")
    paths: set[str] = set()
    class_counts = {name: 0 for name in GENERATED_INPUT_CLASSES}
    for index, record in enumerate(bindings):
        require(isinstance(record, dict) and set(record) == {
                    "class", "path", "bytes", "sha256",
                } and record.get("class") in GENERATED_INPUT_CLASSES and
                type(record.get("bytes")) is int and record["bytes"] > 0,
                f"malformed direct generated-input record: {index}")
        relative = _safe_relative(
            record.get("path"), f"direct generated-input path: {index}",
        )
        require(relative not in paths,
                f"duplicate direct generated-input path: {index}")
        paths.add(relative)
        class_counts[record["class"]] += 1
        _hex(record.get("sha256"), HEX64,
             f"direct generated-input SHA-256: {index}")
    require(value.get("ordered_binding_sha256") == canonical_sha256(bindings),
            "direct generated-input coverage digest mismatch")
    require(class_counts == GENERATED_INPUT_CLASS_COUNTS,
            "direct generated-input class closure mismatch")
    return value


def _validate_mathematical_coverage(value: object) -> dict[str, Any]:
    fields = {
        "structural_fingerprint_requests", "dependency_history_requests",
        "source", "lp", "nonlinear", "final_implication",
        "lp_certificate_consumption_trace_included",
        "dependency_history_is_kernel_trace", "approved_reference_present",
    }
    require(isinstance(value, dict) and set(value) == fields and
            value.get("structural_fingerprint_requests") ==
            list(FINAL_THEOREM_NAMES) and
            value.get("dependency_history_requests") ==
            list(FINAL_THEOREM_NAMES) and
            value.get("source") == "loader-observed-exact-unapproved" and
            value.get("lp") == "observed-uncompared" and
            value.get("nonlinear") == "observed-uncompared" and
            value.get("final_implication") == "observed-uncompared" and
            value.get("lp_certificate_consumption_trace_included") is True and
            value.get("dependency_history_is_kernel_trace") is False and
            value.get("approved_reference_present") is False,
            "malformed direct mathematical coverage")
    return value


def _validate_certificate_consumption(
    value: object, generated_inputs: dict[str, Any],
) -> dict[str, Any]:
    fields = {
        "schema", "kind", "policy", "order", "status", "record_count",
        "ordered_record_sha256", "records", "unmatched_event_count",
        "pft_used",
    }
    require(isinstance(value, dict) and set(value) == fields and
            type(value.get("schema")) is int and value["schema"] == 1 and
            value.get("kind") == CERTIFICATE_CONSUMPTION_KIND and
            value.get("policy") == CERTIFICATE_CONSUMPTION_POLICY and
            value.get("order") == CERTIFICATE_CONSUMPTION_ORDER and
            value.get("status") == "consumption-observed-unapproved" and
            type(value.get("record_count")) is int and
            value["record_count"] == 39 and
            type(value.get("unmatched_event_count")) is int and
            value["unmatched_event_count"] == 0 and
            value.get("pft_used") is False,
            "malformed direct LP-certificate consumption coverage")
    records = value.get("records")
    require(isinstance(records, list) and len(records) == 39,
            "direct LP-certificate consumption is not exactly 39 records")
    identities: set[tuple[str, str, int, str]] = set()
    basenames: list[str] = []
    event_digests: set[str] = set()
    prepared_count = 0
    for index, record in enumerate(records):
        require(isinstance(record, dict) and set(record) == {
                    "index", "class", "relative", "bytes", "sha256",
                    "event_count", "ordered_nonce_free_event_sha256",
                } and type(record.get("index")) is int and
                record["index"] == index and
                record.get("class") in {
                    "lp-certificate", "lp-certificate-prepared",
                } and type(record.get("bytes")) is int and record["bytes"] > 0 and
                type(record.get("event_count")) is int and
                record["event_count"] == 1,
                f"malformed direct LP-certificate consumption record: {index}")
        relative = _safe_relative(
            record.get("relative"),
            f"direct LP-certificate consumption path: {index}",
        )
        sha256 = _hex(record.get("sha256"), HEX64,
                      f"direct LP-certificate SHA-256: {index}")
        event_digest = _hex(
            record.get("ordered_nonce_free_event_sha256"), HEX64,
            f"direct LP-certificate event digest: {index}",
        )
        identity = (record["class"], relative, record["bytes"], sha256)
        require(identity not in identities,
                f"duplicate direct LP-certificate consumption identity: {index}")
        require(event_digest not in event_digests,
                f"duplicate direct LP-certificate event digest: {index}")
        identities.add(identity)
        event_digests.add(event_digest)
        basenames.append(Path(relative).name)
        prepared_count += record["class"] == "lp-certificate-prepared"
    require(prepared_count == 1 and len(set(basenames)) == len(basenames) and
            basenames == sorted(basenames) and
            value.get("ordered_record_sha256") == canonical_sha256(records),
            "direct LP-certificate consumption runtime order/digest mismatch")
    generated_certificate_identities = {
        (record["class"], record["path"], record["bytes"], record["sha256"])
        for record in generated_inputs["bindings"]
        if record["class"] in {"lp-certificate", "lp-certificate-prepared"}
    }
    require(identities == generated_certificate_identities,
            "direct LP-certificate consumption differs from generated inputs")
    return value


def validate_coverage_projection(value: object) -> dict[str, Any]:
    fields = {
        "schema", "kind", "boundary_id", "completed_action_count",
        "action_events", "logical_source_coverage", "physical_source_coverage",
        "generated_inputs", "mathematical_coverage",
        "lp_certificate_consumption", "pft_used",
    }
    require(isinstance(value, dict) and set(value) == fields and
            type(value.get("schema")) is int and value["schema"] == 1 and
            value.get("kind") == COVERAGE_PROJECTION_KIND and
            value.get("boundary_id") == FINAL_BOUNDARY_ID and
            type(value.get("completed_action_count")) is int and
            value["completed_action_count"] == FINAL_ACTION_COUNT and
            value.get("pft_used") is False,
            "direct coverage projection identity or claim mismatch")
    _validate_action_coverage(value.get("action_events"))
    logical = _validate_logical_source_coverage(
        value.get("logical_source_coverage")
    )
    physical = _validate_physical_source_coverage(
        value.get("physical_source_coverage")
    )
    logical_keys = {record["key"] for record in logical["records"]}
    require(logical_keys.isdisjoint(SOURCE_TRACE_FINAL_ADDITIONAL_KEYS),
            "direct logical source collides with reserved control key")
    expected_physical_keys = sorted({
        *SOURCE_TRACE_FINAL_ADDITIONAL_KEYS,
        *(record["key"] for record in logical["records"]
          if record["classification"] != "derivation-only-input"),
    })
    require(physical["observed_keys"] == expected_physical_keys,
            "direct logical and physical source coverage differ")
    generated = _validate_generated_inputs(value.get("generated_inputs"))
    _validate_mathematical_coverage(value.get("mathematical_coverage"))
    _validate_certificate_consumption(
        value.get("lp_certificate_consumption"), generated,
    )
    return value


def _validate_cross_runtime_execution_selection(
    value: object, label: str,
) -> dict[str, Any]:
    require(isinstance(value, dict), f"malformed {label}")
    if value.get("mode") == "original-source":
        require(set(value) == {"mode"}, f"malformed {label}")
        return value
    fields = {
        "mode", "id", "kind", "normalized_bytes", "normalized_sha256",
        "normalized_md5", "operation_count",
    }
    require(set(value) == fields and
            value.get("mode") == "candle-normalization-bound" and
            value.get("kind") == "exact_bytes_replace_sequence" and
            type(value.get("normalized_bytes")) is int and
            value["normalized_bytes"] > 0 and
            type(value.get("operation_count")) is int and
            value["operation_count"] > 0,
            f"malformed {label}")
    _validate_printable_label(value.get("id"), f"{label} ID")
    _hex(value.get("normalized_sha256"), HEX64,
         f"{label} normalized SHA-256")
    _hex(value.get("normalized_md5"), HEX32, f"{label} normalized MD5")
    return value


def _validate_cross_runtime_actions(value: object) -> dict[str, Any]:
    fields = {
        "policy", "selection_semantics", "record_count",
        "ordered_record_sha256", "records",
    }
    require(isinstance(value, dict) and set(value) == fields and
            value.get("policy") == CROSS_RUNTIME_ACTION_POLICY and
            value.get("selection_semantics") ==
            CROSS_RUNTIME_EXECUTION_SELECTION_SEMANTICS and
            type(value.get("record_count")) is int and
            value["record_count"] == FINAL_ACTION_COUNT,
            "malformed cross-runtime action completion")
    records = value.get("records")
    require(isinstance(records, list) and
            len(records) == FINAL_ACTION_COUNT,
            "cross-runtime action completion is not exactly 297 records")
    for index, record in enumerate(records):
        require(isinstance(record, dict) and set(record) == {
                    "index", "selected_source", "target", "stratum",
                    "original_bytes", "original_sha256", "original_md5",
                    "candle_plan_execution_selection", "completion_status",
                } and type(record.get("index")) is int and
                record["index"] == index and
                isinstance(record.get("selected_source"), str) and
                type(record.get("original_bytes")) is int and
                record["original_bytes"] > 0 and
                record.get("stratum") in ACTION_STRATA and
                record.get("completion_status") ==
                "completed-observed-unapproved",
                f"malformed cross-runtime action completion record: {index}")
        _validate_logical_source_key(
            record.get("selected_source"),
            f"cross-runtime action selected source: {index}",
        )
        _validate_action_target_alias(
            record.get("target"), record.get("selected_source"),
            f"cross-runtime action target: {index}",
        )
        _hex(record.get("original_sha256"), HEX64,
             f"cross-runtime action source SHA-256: {index}")
        _hex(record.get("original_md5"), HEX32,
             f"cross-runtime action source MD5: {index}")
        _validate_cross_runtime_execution_selection(
            record.get("candle_plan_execution_selection"),
            f"cross-runtime action execution selection: {index}",
        )
    require(value.get("ordered_record_sha256") == canonical_sha256(records),
            "cross-runtime action completion digest mismatch")
    return value


def _validate_cross_runtime_source_inventory(value: object) -> dict[str, Any]:
    fields = {
        "schema", "kind", "policy", "record_count",
        "normalization_binding_count", "ordered_record_sha256", "records",
    }
    require(isinstance(value, dict) and set(value) == fields and
            type(value.get("schema")) is int and value["schema"] == 1 and
            value.get("kind") == CROSS_RUNTIME_SOURCE_INVENTORY_KIND and
            value.get("policy") == CROSS_RUNTIME_SOURCE_INVENTORY_POLICY and
            type(value.get("record_count")) is int and
            value["record_count"] == 400 and
            type(value.get("normalization_binding_count")) is int and
            0 < value["normalization_binding_count"] < 400,
            "malformed cross-runtime original-source inventory")
    records = value.get("records")
    require(isinstance(records, list) and len(records) == 400,
            "cross-runtime source inventory is not exactly 400 records")
    previous_key: str | None = None
    normalized_count = 0
    normalization_ids: set[str] = set()
    for index, record in enumerate(records):
        require(isinstance(record, dict) and set(record) == {
                    "index", "key", "repository", "path", "original_bytes",
                    "original_sha256", "original_md5",
                    "candle_plan_execution_selection",
                } and type(record.get("index")) is int and
                record["index"] == index and
                record.get("repository") in {"candle", "flyspeck"} and
                type(record.get("original_bytes")) is int and
                record["original_bytes"] > 0,
                f"malformed cross-runtime source record: {index}")
        key = record.get("key")
        require(isinstance(key, str),
                f"malformed cross-runtime source key: {index}")
        _validate_logical_source_key(key,
                                     f"cross-runtime source key: {index}")
        require(key.startswith(f"{record['repository']}:") and
                (previous_key is None or previous_key < key),
                f"cross-runtime source inventory order/namespace mismatch: "
                f"{index}")
        path = _safe_relative(record.get("path"),
                              f"cross-runtime source path: {index}")
        require(key == f"{record['repository']}:{path}",
                f"cross-runtime source key/path mismatch: {index}")
        previous_key = key
        _hex(record.get("original_sha256"), HEX64,
             f"cross-runtime source SHA-256: {index}")
        _hex(record.get("original_md5"), HEX32,
             f"cross-runtime source MD5: {index}")
        selection = _validate_cross_runtime_execution_selection(
            record.get("candle_plan_execution_selection"),
            f"cross-runtime source execution selection: {index}",
        )
        if selection["mode"] == "candle-normalization-bound":
            require(selection["id"] not in normalization_ids,
                    f"duplicate cross-runtime normalization ID: {index}")
            normalization_ids.add(selection["id"])
            normalized_count += 1
    require(normalized_count == value["normalization_binding_count"] and
            value.get("ordered_record_sha256") == canonical_sha256(records),
            "cross-runtime source inventory digest/count mismatch")
    return value


def _validate_cross_runtime_logical_closure(
    value: object, source_inventory: dict[str, Any],
) -> dict[str, Any]:
    fields = {
        "schema", "kind", "policy", "order", "status", "record_count",
        "ordered_record_sha256", "records",
        "runtime_observation_retained_by_candidate",
    }
    require(isinstance(value, dict) and set(value) == fields and
            type(value.get("schema")) is int and value["schema"] == 1 and
            value.get("kind") == CROSS_RUNTIME_LOGICAL_CLOSURE_KIND and
            value.get("policy") == CROSS_RUNTIME_LOGICAL_CLOSURE_POLICY and
            value.get("order") == SOURCE_CLOSURE_ORDER and
            value.get("status") == "selected-closure-observed-unapproved" and
            value.get("runtime_observation_retained_by_candidate") is True,
            "malformed cross-runtime logical-source closure")
    records = value.get("records")
    require(isinstance(records, list) and records and
            type(value.get("record_count")) is int and
            value["record_count"] == len(records),
            "malformed cross-runtime logical-source closure records")
    inventory_by_key = {
        record["key"]: record for record in source_inventory["records"]
    }
    previous_key: str | None = None
    for index, record in enumerate(records):
        require(isinstance(record, dict) and set(record) == {
                    "index", "key", "original_bytes", "original_sha256",
                    "original_md5", "candle_plan_execution_selection",
                } and type(record.get("index")) is int and
                record["index"] == index and
                type(record.get("original_bytes")) is int and
                record["original_bytes"] > 0 and
                isinstance(record.get("key"), str),
                f"malformed cross-runtime logical-source record: {index}")
        key = record["key"]
        _validate_logical_source_key(
            key, f"cross-runtime logical-source key: {index}",
        )
        require(previous_key is None or previous_key < key,
                f"cross-runtime logical-source keys are not canonical: {index}")
        previous_key = key
        _hex(record.get("original_sha256"), HEX64,
             f"cross-runtime logical-source SHA-256: {index}")
        _hex(record.get("original_md5"), HEX32,
             f"cross-runtime logical-source MD5: {index}")
        _validate_cross_runtime_execution_selection(
            record.get("candle_plan_execution_selection"),
            f"cross-runtime logical-source execution selection: {index}",
        )
        source = inventory_by_key.get(key)
        require(source is not None and all(
                    _same_canonical_value(record[field], source[field])
                    for field in (
                        "original_bytes", "original_sha256", "original_md5",
                        "candle_plan_execution_selection",
                    )
                ),
                f"cross-runtime logical source differs from inventory: {index}")
    require(value.get("ordered_record_sha256") == canonical_sha256(records),
            "cross-runtime logical-source closure digest mismatch")
    return value


def _validate_cross_runtime_mathematical_coverage(
    value: object,
) -> dict[str, Any]:
    fields = {
        "status", "structural_fingerprint_requests",
        "dependency_history_requests", "source_closure_observed",
        "lp_completed_observed", "nonlinear_completed_observed",
        "final_premises_completed_observed",
        "final_implication_completed_observed", "approved_reference_present",
    }
    require(isinstance(value, dict) and set(value) == fields and
            value.get("status") == "observed-uncompared" and
            value.get("structural_fingerprint_requests") ==
            list(FINAL_THEOREM_NAMES) and
            value.get("dependency_history_requests") ==
            list(FINAL_THEOREM_NAMES) and
            value.get("source_closure_observed") is True and
            value.get("lp_completed_observed") is True and
            value.get("nonlinear_completed_observed") is True and
            value.get("final_premises_completed_observed") is True and
            value.get("final_implication_completed_observed") is True and
            value.get("approved_reference_present") is False,
            "malformed cross-runtime mathematical coverage")
    return value


def _validate_cross_runtime_lp_consumption(
    value: object, generated_inputs: dict[str, Any],
) -> dict[str, Any]:
    fields = {
        "schema", "kind", "policy", "order", "status", "record_count",
        "ordered_record_sha256", "records", "raw_order_retained_by_candidate",
        "pft_used",
    }
    require(isinstance(value, dict) and set(value) == fields and
            type(value.get("schema")) is int and value["schema"] == 2 and
            value.get("kind") == CROSS_RUNTIME_LP_CONSUMPTION_KIND and
            value.get("policy") == CROSS_RUNTIME_LP_CONSUMPTION_POLICY and
            value.get("order") == CROSS_RUNTIME_LP_CONSUMPTION_ORDER and
            value.get("status") ==
            "exactly-once-successful-deserialization-observed-unapproved" and
            type(value.get("record_count")) is int and
            value["record_count"] == 39 and
            value.get("raw_order_retained_by_candidate") is True and
            value.get("pft_used") is False,
            "malformed cross-runtime LP-certificate consumption")
    records = value.get("records")
    require(isinstance(records, list) and len(records) == 39,
            "cross-runtime LP consumption is not exactly 39 records")
    previous_relative: str | None = None
    identities: set[tuple[str, str, int, str]] = set()
    prepared_count = 0
    for index, record in enumerate(records):
        require(isinstance(record, dict) and set(record) == {
                    "index", "class", "relative", "bytes", "sha256",
                    "successful_deserialization_count",
                } and type(record.get("index")) is int and
                record["index"] == index and
                record.get("class") in {
                    "lp-certificate", "lp-certificate-prepared",
                } and type(record.get("bytes")) is int and
                record["bytes"] > 0 and
                type(record.get("successful_deserialization_count")) is int and
                record["successful_deserialization_count"] == 1,
                f"malformed cross-runtime LP consumption record: {index}")
        relative = _safe_relative(
            record.get("relative"),
            f"cross-runtime LP consumption path: {index}",
        )
        require(previous_relative is None or previous_relative < relative,
                f"cross-runtime LP consumption order mismatch: {index}")
        previous_relative = relative
        sha256 = _hex(record.get("sha256"), HEX64,
                      f"cross-runtime LP consumption SHA-256: {index}")
        identity = (record["class"], relative, record["bytes"], sha256)
        require(identity not in identities,
                f"duplicate cross-runtime LP consumption identity: {index}")
        identities.add(identity)
        prepared_count += record["class"] == "lp-certificate-prepared"
    generated_identities = {
        (record["class"], record["path"], record["bytes"], record["sha256"])
        for record in generated_inputs["bindings"]
        if record["class"] in {"lp-certificate", "lp-certificate-prepared"}
    }
    require(prepared_count == 1 and identities == generated_identities and
            value.get("ordered_record_sha256") == canonical_sha256(records),
            "cross-runtime LP consumption identity/digest mismatch")
    return value


def validate_cross_runtime_coverage_projection(
    value: object,
) -> dict[str, Any]:
    """Validate only the disjoint facts comparable across all three runtimes."""
    fields = {
        "schema", "kind", "boundary_id", "completed_action_count", "actions",
        "original_source_inventory", "selected_logical_source_closure",
        "generated_inputs", "mathematical_coverage",
        "lp_certificate_consumption", "pft_used",
    }
    require(isinstance(value, dict) and set(value) == fields and
            type(value.get("schema")) is int and value["schema"] == 2 and
            value.get("kind") == CROSS_RUNTIME_COVERAGE_KIND and
            value.get("boundary_id") == FINAL_BOUNDARY_ID and
            type(value.get("completed_action_count")) is int and
            value["completed_action_count"] == FINAL_ACTION_COUNT and
            value.get("pft_used") is False,
            "cross-runtime coverage projection identity or claim mismatch")
    actions = _validate_cross_runtime_actions(value.get("actions"))
    inventory = _validate_cross_runtime_source_inventory(
        value.get("original_source_inventory")
    )
    inventory_by_key = {
        record["key"]: record for record in inventory["records"]
    }
    for index, action in enumerate(actions["records"]):
        source = inventory_by_key.get(action["selected_source"])
        require(source is not None and all(
                    _same_canonical_value(action[action_field],
                                          source[source_field])
                    for action_field, source_field in (
                        ("original_bytes", "original_bytes"),
                        ("original_sha256", "original_sha256"),
                        ("original_md5", "original_md5"),
                        ("candle_plan_execution_selection",
                         "candle_plan_execution_selection"),
                    )
                ),
                f"cross-runtime action differs from source inventory: {index}")
    logical = _validate_cross_runtime_logical_closure(
        value.get("selected_logical_source_closure"), inventory,
    )
    action_keys = {record["selected_source"] for record in actions["records"]}
    logical_keys = {record["key"] for record in logical["records"]}
    require(action_keys <= logical_keys,
            "cross-runtime logical closure omits action sources")
    generated = _validate_generated_inputs(value.get("generated_inputs"))
    _validate_cross_runtime_mathematical_coverage(
        value.get("mathematical_coverage")
    )
    _validate_cross_runtime_lp_consumption(
        value.get("lp_certificate_consumption"), generated,
    )
    return value


def coverage_projection_from_schema6(
    receipt: object, authenticated_plan: object,
) -> dict[str, Any]:
    """Project one already-authenticated final schema-6 receipt and its plan.

    This is a pure adapter, not a raw-result authenticator.  Its caller must
    first apply Candle's schema-6 receipt/log/snapshot validator.  The exact
    plan bytes are nevertheless re-bound here so that the 43 generated inputs
    cannot be supplied from a different run.
    """
    require(isinstance(receipt, dict) and
            set(receipt) == RAW_V6_RECEIPT_FIELDS,
            "malformed authenticated direct evidence-v6 receipt")
    require(type(receipt.get("schema")) is int and receipt["schema"] == 6 and
            receipt.get("kind") ==
            "candle-flyspeck-compiled-stratum-attempt" and
            receipt.get("claim") == RAW_V6_CLAIM and
            receipt.get("state") == "completed" and
            receipt.get("boundary_id") == FINAL_BOUNDARY_ID and
            receipt.get("diagnostic_only") is False and
            type(receipt.get("action_count")) is int and
            receipt["action_count"] == FINAL_ACTION_COUNT and
            receipt.get("timed_out") is False and
            type(receipt.get("exit_code")) is int and
            receipt["exit_code"] == 0 and
            receipt.get("validation_error") is None and
            receipt.get("postflight_reauthenticated") is True and
            receipt.get("fresh_process_replay_from_action_zero") is True and
            receipt.get("cooperative_build_run_lock_held") is True and
            receipt.get("concurrent_mutation_model") ==
            RAW_CONCURRENT_MUTATION_MODEL and
            receipt.get("process_state_checkpoint") is None and
            receipt.get("runtime_environment_policy") ==
            RAW_RUNTIME_ENVIRONMENT_POLICY and
            receipt.get("s2_s3_evidence") is False,
            "direct evidence-v6 receipt is not an exact unapproved final result")
    nonce = receipt.get("attempt_nonce")
    _hex(nonce, HEX32, "direct evidence-v6 nonce")

    evidence_contract = receipt.get("evidence_contract")
    evidence_contract_fields = {
        "schema", "allowed_action_outcomes",
        "physical_loader_cache_skip_allowed", "logical_source_closure_policy",
        "logical_source_closure_order",
        "selected_loadt_ledger_delta_included",
        "physical_loader_cache_trace_included",
        "physical_source_trace_protocol", "pre_trace_control_exclusion",
        "s2_s3_approval_included", "dependency_history_protocol",
        "dependency_history_policy", "semantic_coverage_policy",
        "dependency_history_is_kernel_trace", "semantic_approval_included",
        "pft_used", "lp_certificate_consumption_protocol",
        "lp_certificate_consumption_policy",
        "lp_certificate_consumption_order",
        "lp_certificate_consumption_exactly_once",
    }
    require(isinstance(evidence_contract, dict) and
            set(evidence_contract) == evidence_contract_fields and
            evidence_contract.get("schema") ==
            "candle-flyspeck-direct-runtime-evidence-v6" and
            evidence_contract.get("allowed_action_outcomes") ==
            list(ACTION_OUTCOMES) and
            evidence_contract.get("logical_source_closure_policy") ==
            SOURCE_CLOSURE_POLICY and
            evidence_contract.get("logical_source_closure_order") ==
            SOURCE_CLOSURE_ORDER and
            evidence_contract.get("physical_source_trace_protocol") ==
            SOURCE_TRACE_PROTOCOL and
            evidence_contract.get("semantic_coverage_policy") ==
            RAW_V6_SEMANTIC_POLICY and
            evidence_contract.get("lp_certificate_consumption_protocol") ==
            RAW_LP_CONSUMPTION_PROTOCOL and
            evidence_contract.get("lp_certificate_consumption_policy") ==
            RAW_LP_CONSUMPTION_POLICY and
            evidence_contract.get("lp_certificate_consumption_order") ==
            CERTIFICATE_CONSUMPTION_ORDER and
            evidence_contract.get("lp_certificate_consumption_exactly_once")
            is True and
            evidence_contract.get("s2_s3_approval_included") is False and
            evidence_contract.get("semantic_approval_included") is False and
            evidence_contract.get("dependency_history_is_kernel_trace") is False and
            evidence_contract.get("pft_used") is False,
            "malformed direct evidence-v6 contract")

    require(isinstance(authenticated_plan, dict) and
            type(authenticated_plan.get("schema")) is int and
            authenticated_plan["schema"] == 1 and
            authenticated_plan.get("kind") ==
            "candle-flyspeck-cumulative-stratum-plan" and
            type(authenticated_plan.get("action_count")) is int and
            authenticated_plan["action_count"] == FINAL_ACTION_COUNT,
            "malformed authenticated final cumulative plan")
    plan_bytes = canonical_json_bytes(authenticated_plan)
    plan_record = {
        "bytes": len(plan_bytes),
        "sha256": hashlib.sha256(plan_bytes).hexdigest(),
        "md5": hashlib.md5(plan_bytes, usedforsecurity=False).hexdigest(),
    }
    inputs = receipt.get("inputs")
    require(isinstance(inputs, dict) and inputs.get("plan") == plan_record,
            "authenticated final plan differs from direct evidence-v6 input")

    expected_actions = receipt.get("expected_action_events")
    action_events = receipt.get("action_events")
    require(isinstance(expected_actions, list) and
            isinstance(action_events, list) and
            len(expected_actions) == len(action_events) == FINAL_ACTION_COUNT and
            type(receipt.get("action_markers_validated")) is int and
            receipt["action_markers_validated"] == FINAL_ACTION_COUNT,
            "direct evidence-v6 action closure is incomplete")
    projected_actions = []
    for index, (expected, observed) in enumerate(zip(
        expected_actions, action_events, strict=True,
    )):
        expected_fields = {
            "index", "source_sha256", "logical_source_delta",
            "logical_source_delta_sha256",
        }
        observed_fields = {
            "index", "source_sha256", "logical_source_delta_sha256", "outcome",
        }
        require(isinstance(expected, dict) and set(expected) == expected_fields and
                isinstance(observed, dict) and set(observed) == observed_fields and
                all(expected[field] == observed[field] for field in (
                    "index", "source_sha256", "logical_source_delta_sha256",
                )) and isinstance(expected.get("logical_source_delta"), list) and
                bool(expected["logical_source_delta"]) and
                expected["logical_source_delta_sha256"] ==
                canonical_sha256(expected["logical_source_delta"]),
                f"direct evidence-v6 action observation mismatch: {index}")
        projected_actions.append(copy.deepcopy(observed))
    require(receipt.get("ordered_expected_action_sha256") ==
            canonical_sha256(expected_actions),
            "direct evidence-v6 expected-action digest mismatch")

    logical = receipt.get("logical_source_closure")
    logical_fields = {
        "schema", "kind", "policy", "order", "completed_action_count",
        "final_target_selected", "record_count", "ordered_record_sha256",
        "records", "physical_loader_cache_trace", "execution_observation",
        "self_certifies_nested_execution", "s2_s3_evidence", "status",
    }
    require(isinstance(logical, dict) and set(logical) == logical_fields and
            logical.get("schema") == 3 and
            logical.get("kind") == RAW_SOURCE_CLOSURE_KIND and
            logical.get("policy") == SOURCE_CLOSURE_POLICY and
            logical.get("order") == SOURCE_CLOSURE_ORDER and
            logical.get("completed_action_count") == FINAL_ACTION_COUNT and
            logical.get("final_target_selected") is True and
            logical.get("physical_loader_cache_trace") is False and
            logical.get("execution_observation") == SOURCE_CLOSURE_OBSERVATION and
            logical.get("self_certifies_nested_execution") is False and
            logical.get("s2_s3_evidence") is False and
            logical.get("status") == "expected-closure-emitted-unapproved" and
            isinstance(logical.get("records"), list) and
            type(logical.get("record_count")) is int and
            logical["record_count"] == len(logical["records"]) and
            logical.get("ordered_record_sha256") ==
            canonical_sha256(logical["records"]),
            "malformed direct evidence-v6 logical-source observation")
    expected_logical = copy.deepcopy(logical)
    del expected_logical["status"]
    require(receipt.get("expected_logical_source_closure") == expected_logical,
            "direct evidence-v6 logical source differs from its attempt")
    projected_logical = {
        "schema": 1,
        "kind": LOGICAL_COVERAGE_KIND,
        "policy": logical["policy"],
        "order": logical["order"],
        "record_count": logical["record_count"],
        "ordered_record_sha256": logical["ordered_record_sha256"],
        "records": copy.deepcopy(logical["records"]),
        "execution_observation": logical["execution_observation"],
        "self_certifies_nested_execution": False,
    }

    physical = receipt.get("physical_source_trace")
    require(isinstance(physical, dict) and set(physical) == {
                "schema", "protocol", "nonce", "event_count",
                "ordered_event_sha256", "events", "request_count",
                "cache_skip_count", "observed_key_count",
                "ordered_observed_key_sha256", "observed_keys", "status",
            } and physical.get("schema") == 1 and
            physical.get("protocol") == SOURCE_TRACE_PROTOCOL and
            physical.get("nonce") == nonce and
            physical.get("status") == "closed-loader-owned-session" and
            isinstance(physical.get("events"), list) and
            type(physical.get("event_count")) is int and
            physical["event_count"] == len(physical["events"]) and
            physical.get("ordered_event_sha256") ==
            canonical_sha256(physical["events"]) and
            isinstance(physical.get("observed_keys"), list) and
            physical.get("ordered_observed_key_sha256") ==
            canonical_sha256(physical["observed_keys"]),
            "malformed direct evidence-v6 physical-source observation")
    projected_physical_events = []
    for index, event in enumerate(physical.get("events", [])):
        require(isinstance(event, dict),
                f"malformed direct evidence-v6 physical event: {index}")
        if event.get("event") == "request":
            require(set(event) == {
                        "event", "id", "parent", "kind", "binding_id", "key",
                        "cache_before",
                    }, f"malformed direct evidence-v6 request: {index}")
            _hex(event.get("binding_id"), HEX64,
                 f"direct evidence-v6 physical binding: {index}")
            projected_physical_events.append({
                field: copy.deepcopy(event[field]) for field in (
                    "event", "id", "parent", "kind", "key", "cache_before",
                )
            })
        else:
            projected_physical_events.append(copy.deepcopy(event))
    projected_physical = {
        "schema": 1,
        "kind": PHYSICAL_COVERAGE_KIND,
        "protocol": physical["protocol"],
        "event_count": len(projected_physical_events),
        "ordered_event_sha256": canonical_sha256(projected_physical_events),
        "events": projected_physical_events,
        "request_count": physical["request_count"],
        "cache_skip_count": physical["cache_skip_count"],
        "observed_key_count": physical["observed_key_count"],
        "ordered_observed_key_sha256": physical["ordered_observed_key_sha256"],
        "observed_keys": copy.deepcopy(physical["observed_keys"]),
        "status": physical["status"],
    }

    semantic_plan = receipt.get("semantic_evidence_plan")
    require(isinstance(semantic_plan, dict) and
            semantic_plan.get("boundary_id") == FINAL_BOUNDARY_ID and
            semantic_plan.get("completed_action_count") == FINAL_ACTION_COUNT and
            semantic_plan.get("structural_fingerprint_requests") ==
            list(FINAL_THEOREM_NAMES) and
            semantic_plan.get("dependency_history_requests") ==
            list(FINAL_THEOREM_NAMES) and
            semantic_plan.get("approval_included") is False and
            semantic_plan.get("pft_used") is False and
            semantic_plan.get("s2_s3_evidence") is False and
            isinstance(semantic_plan.get("authenticated_inputs"), dict) and
            semantic_plan["authenticated_inputs"].get("plan_sha256") ==
            plan_record["sha256"],
            "malformed direct evidence-v6 semantic plan")

    lp_contract = receipt.get("lp_consumption_contract")
    lp_observation = receipt.get("lp_certificate_consumption")
    require(isinstance(lp_contract, dict) and
            lp_contract.get("nonce") == nonce and
            lp_contract.get("protocol") == RAW_LP_CONSUMPTION_PROTOCOL and
            lp_contract.get("policy") == RAW_LP_CONSUMPTION_POLICY and
            lp_contract.get("order") == CERTIFICATE_CONSUMPTION_ORDER and
            lp_contract.get("pft_used") is False and
            isinstance(lp_observation, dict) and
            lp_observation.get("kind") == RAW_LP_CONSUMPTION_KIND and
            lp_observation.get("protocol") == RAW_LP_CONSUMPTION_PROTOCOL and
            lp_observation.get("policy") == RAW_LP_CONSUMPTION_POLICY and
            lp_observation.get("order") == CERTIFICATE_CONSUMPTION_ORDER and
            lp_observation.get("nonce") == nonce and
            lp_observation.get("status") == "consumption-observed-unapproved" and
            lp_observation.get("approved_reference_present") is False and
            lp_observation.get("pft_used") is False and
            lp_observation.get("s2_s3_evidence") is False and
            lp_observation.get("unmatched_event_count") == 0 and
            lp_observation.get("event_count") == 39 and
            lp_observation.get("record_count") == 39,
            "malformed direct evidence-v6 LP consumption observation")
    lp_records = lp_observation.get("records")
    semantic_lp = semantic_plan.get("lp_certificate_inputs")
    require(isinstance(lp_records, list) and len(lp_records) == 39 and
            isinstance(semantic_lp, dict) and
            isinstance(semantic_lp.get("records"), list) and
            len(semantic_lp["records"]) == 39 and
            semantic_lp.get("record_count") == 39 and
            semantic_lp.get("ordered_record_sha256") ==
            canonical_sha256(semantic_lp["records"]) and
            lp_observation.get("ordered_record_sha256") ==
            canonical_sha256(lp_records),
            "direct evidence-v6 lacks 39 LP consumption records")
    projected_lp_records = []
    for index, (record, planned) in enumerate(zip(
        lp_records, semantic_lp["records"], strict=True,
    )):
        identity_fields = (
            "index", "class", "relative", "bytes", "sha256", "md5",
        )
        require(isinstance(record, dict) and isinstance(planned, dict) and
                all(record.get(field) == planned.get(field)
                    for field in identity_fields) and
                type(record.get("event_count")) is int and
                record["event_count"] == 1,
                f"direct evidence-v6 LP input/observation mismatch: {index}")
        projected_lp_records.append({
            field: copy.deepcopy(record[field]) for field in (
                "index", "class", "relative", "bytes", "sha256",
                "event_count", "ordered_nonce_free_event_sha256",
            )
        })

    semantic_coverage = receipt.get("semantic_coverage")
    semantic_coverage_fields = {
        "schema", "kind", "policy", "status", "boundary_id",
        "semantic_evidence_plan_sha256", "logical_source_observation_sha256",
        "physical_source_observation_sha256",
        "structural_fingerprint_observation_sha256",
        "dependency_history_observation_sha256", "lp_certificate_input_sha256",
        "source", "lp", "nonlinear", "final_implication",
        "lp_certificate_consumption_trace_included",
        "lp_certificate_consumption_contract_sha256",
        "lp_certificate_consumption_observation_sha256",
        "dependency_history_is_kernel_trace", "approved_reference_present",
        "approval_sha256", "pft_used", "s2_eligible", "s3_eligible",
        "s2_s3_evidence",
    }
    require(isinstance(semantic_coverage, dict) and
            set(semantic_coverage) == semantic_coverage_fields and
            semantic_coverage.get("schema") == 2 and
            semantic_coverage.get("kind") ==
            "candle-flyspeck-direct-semantic-coverage-observation-v2" and
            semantic_coverage.get("policy") == RAW_V6_SEMANTIC_POLICY and
            semantic_coverage.get("status") == "observed_uncompared" and
            semantic_coverage.get("boundary_id") == FINAL_BOUNDARY_ID and
            semantic_coverage.get("source") ==
            "loader-observed-exact-unapproved" and
            semantic_coverage.get("lp") ==
            "consumption-observed-uncompared" and
            semantic_coverage.get("nonlinear") == "observed-uncompared" and
            semantic_coverage.get("final_implication") ==
            "observed-uncompared" and
            semantic_coverage.get("lp_certificate_consumption_trace_included")
            is True and
            semantic_coverage.get("dependency_history_is_kernel_trace") is False and
            semantic_coverage.get("approved_reference_present") is False and
            semantic_coverage.get("approval_sha256") is None and
            semantic_coverage.get("pft_used") is False and
            semantic_coverage.get("s2_eligible") is False and
            semantic_coverage.get("s3_eligible") is False and
            semantic_coverage.get("s2_s3_evidence") is False and
            semantic_coverage.get("semantic_evidence_plan_sha256") ==
            canonical_sha256(semantic_plan) and
            semantic_coverage.get("logical_source_observation_sha256") ==
            canonical_sha256(logical) and
            semantic_coverage.get("physical_source_observation_sha256") ==
            canonical_sha256(physical) and
            semantic_coverage.get("structural_fingerprint_observation_sha256") ==
            canonical_sha256(receipt.get("semantic_fingerprints")) and
            semantic_coverage.get("dependency_history_observation_sha256") ==
            canonical_sha256(receipt.get("dependency_history")) and
            semantic_coverage.get("lp_certificate_input_sha256") ==
            semantic_lp["ordered_record_sha256"] and
            semantic_coverage.get("lp_certificate_consumption_contract_sha256") ==
            canonical_sha256(lp_contract) and
            semantic_coverage.get("lp_certificate_consumption_observation_sha256") ==
            canonical_sha256(lp_observation),
            "direct evidence-v6 semantic coverage is not content-bound")

    generated_inputs = copy.deepcopy(authenticated_plan.get("generated_inputs"))
    projection = {
        "schema": 1,
        "kind": COVERAGE_PROJECTION_KIND,
        "boundary_id": FINAL_BOUNDARY_ID,
        "completed_action_count": FINAL_ACTION_COUNT,
        "action_events": {
            "record_count": len(projected_actions),
            "ordered_record_sha256": canonical_sha256(projected_actions),
            "records": projected_actions,
        },
        "logical_source_coverage": projected_logical,
        "physical_source_coverage": projected_physical,
        "generated_inputs": generated_inputs,
        "mathematical_coverage": {
            "structural_fingerprint_requests": list(FINAL_THEOREM_NAMES),
            "dependency_history_requests": list(FINAL_THEOREM_NAMES),
            "source": semantic_coverage["source"],
            "lp": "observed-uncompared",
            "nonlinear": semantic_coverage["nonlinear"],
            "final_implication": semantic_coverage["final_implication"],
            "lp_certificate_consumption_trace_included": True,
            "dependency_history_is_kernel_trace": False,
            "approved_reference_present": False,
        },
        "lp_certificate_consumption": {
            "schema": 1,
            "kind": CERTIFICATE_CONSUMPTION_KIND,
            "policy": CERTIFICATE_CONSUMPTION_POLICY,
            "order": CERTIFICATE_CONSUMPTION_ORDER,
            "status": "consumption-observed-unapproved",
            "record_count": len(projected_lp_records),
            "ordered_record_sha256": canonical_sha256(projected_lp_records),
            "records": projected_lp_records,
            "unmatched_event_count": 0,
            "pft_used": False,
        },
        "pft_used": False,
    }
    return validate_coverage_projection(projection)


def _cross_runtime_execution_selection_from_plan(
    normalization: object, label: str,
) -> dict[str, Any]:
    if normalization is None:
        return {"mode": "original-source"}
    fields = {
        "id", "kind", "normalized_bytes", "normalized_sha256",
        "normalized_md5", "operation_count",
    }
    require(isinstance(normalization, dict) and set(normalization) == fields,
            f"malformed {label}")
    selection = {
        "mode": "candle-normalization-bound",
        **copy.deepcopy(normalization),
    }
    return _validate_cross_runtime_execution_selection(selection, label)


def cross_runtime_coverage_projection_from_schema6(
    receipt: object, authenticated_plan: object,
) -> dict[str, Any]:
    """Derive the disjoint common coverage value from authenticated schema 6.

    Detailed loader events, cache behavior, raw LP event order, and Candle
    control records deliberately remain only in coverage-v1.  This adapter
    binds the Candle plan's normalization selection but does not claim that a
    pristine reference runtime executes the normalized overlay.
    """
    detailed = coverage_projection_from_schema6(receipt, authenticated_plan)
    require(isinstance(authenticated_plan, dict),
            "malformed authenticated cross-runtime plan")

    source_graph = authenticated_plan.get("source_graph")
    require(isinstance(source_graph, dict) and set(source_graph) == {
                "entry_count", "ordered_binding_sha256", "bindings",
            } and type(source_graph.get("entry_count")) is int and
            source_graph["entry_count"] == 400 and
            isinstance(source_graph.get("bindings"), list) and
            len(source_graph["bindings"]) == 400 and
            source_graph.get("ordered_binding_sha256") ==
            canonical_sha256(source_graph["bindings"]),
            "authenticated plan lacks exact 400-node source graph")
    inventory_records = []
    inventory_by_key: dict[str, dict[str, Any]] = {}
    previous_key: str | None = None
    normalization_count = 0
    for index, binding in enumerate(source_graph["bindings"]):
        base_fields = {"key", "repository", "path", "bytes", "sha256", "md5"}
        require(isinstance(binding, dict) and
                frozenset(binding) in {
                    frozenset(base_fields),
                    frozenset({*base_fields, "execution_normalization"}),
                } and binding.get("repository") in {"candle", "flyspeck"} and
                type(binding.get("bytes")) is int and binding["bytes"] > 0 and
                isinstance(binding.get("key"), str),
                f"malformed authenticated plan source binding: {index}")
        key = binding["key"]
        _validate_logical_source_key(
            key, f"authenticated plan source key: {index}",
        )
        path = _safe_relative(
            binding.get("path"), f"authenticated plan source path: {index}",
        )
        require(key == f"{binding['repository']}:{path}" and
                (previous_key is None or previous_key < key),
                f"authenticated plan source graph is not canonical: {index}")
        previous_key = key
        _hex(binding.get("sha256"), HEX64,
             f"authenticated plan source SHA-256: {index}")
        _hex(binding.get("md5"), HEX32,
             f"authenticated plan source MD5: {index}")
        selection = _cross_runtime_execution_selection_from_plan(
            binding.get("execution_normalization"),
            f"authenticated plan source normalization: {index}",
        )
        normalization_count += (
            selection["mode"] == "candle-normalization-bound"
        )
        projected = {
            "index": index,
            "key": key,
            "repository": binding["repository"],
            "path": path,
            "original_bytes": binding["bytes"],
            "original_sha256": binding["sha256"],
            "original_md5": binding["md5"],
            "candle_plan_execution_selection": selection,
        }
        inventory_records.append(projected)
        inventory_by_key[key] = projected

    plan_actions = authenticated_plan.get("actions")
    require(isinstance(plan_actions, list) and
            len(plan_actions) == FINAL_ACTION_COUNT and
            authenticated_plan.get("ordered_action_sha256") ==
            canonical_sha256(plan_actions),
            "authenticated plan lacks exact ordered 297-action closure")
    detailed_actions = detailed["action_events"]["records"]
    action_records = []
    for index, (action, observed) in enumerate(zip(
        plan_actions, detailed_actions, strict=True,
    )):
        base_fields = {
            "index", "selected_source", "target", "stratum", "source_bytes",
            "source_sha256", "source_md5",
        }
        require(isinstance(action, dict) and frozenset(action) in {
                    frozenset(base_fields),
                    frozenset({*base_fields, "execution_normalization"}),
                } and type(action.get("index")) is int and
                action["index"] == index and
                action.get("stratum") in ACTION_STRATA and
                type(action.get("source_bytes")) is int and
                action["source_bytes"] > 0 and
                observed.get("index") == index and
                observed.get("source_sha256") == action.get("source_sha256"),
                f"authenticated plan/action observation mismatch: {index}")
        selected_source = action.get("selected_source")
        require(isinstance(selected_source, str),
                f"malformed authenticated plan action source: {index}")
        _validate_logical_source_key(
            selected_source, f"authenticated plan action source: {index}",
        )
        _validate_action_target_alias(
            action.get("target"), selected_source,
            f"authenticated plan action target: {index}",
        )
        _hex(action.get("source_sha256"), HEX64,
             f"authenticated plan action SHA-256: {index}")
        _hex(action.get("source_md5"), HEX32,
             f"authenticated plan action MD5: {index}")
        selection = _cross_runtime_execution_selection_from_plan(
            action.get("execution_normalization"),
            f"authenticated plan action normalization: {index}",
        )
        source = inventory_by_key.get(selected_source)
        require(source is not None and
                source["original_bytes"] == action["source_bytes"] and
                source["original_sha256"] == action["source_sha256"] and
                source["original_md5"] == action["source_md5"] and
                _same_canonical_value(
                    source["candle_plan_execution_selection"], selection,
                ),
                f"authenticated plan action differs from source graph: {index}")
        action_records.append({
            "index": index,
            "selected_source": selected_source,
            "target": action["target"],
            "stratum": action["stratum"],
            "original_bytes": action["source_bytes"],
            "original_sha256": action["source_sha256"],
            "original_md5": action["source_md5"],
            "candle_plan_execution_selection": selection,
            "completion_status": "completed-observed-unapproved",
        })

    logical_sources = {
        action["selected_source"]: inventory_by_key[action["selected_source"]]
        for action in action_records
    }
    for logical in detailed["logical_source_coverage"]["records"]:
        if logical["classification"] in {
            "derivation-only-input", "generated-executed-control",
        }:
            continue
        source = inventory_by_key.get(logical["key"])
        require(source is not None and
                source["original_sha256"] == logical["source_sha256"] and
                source["original_md5"] == logical["source_md5"],
                "cross-runtime logical source differs from authenticated plan")
        logical_normalization = logical["execution_normalization"]
        selection = source["candle_plan_execution_selection"]
        if logical_normalization is None:
            require(selection["mode"] == "original-source",
                    "cross-runtime logical source omits plan normalization")
        else:
            require(selection["mode"] == "candle-normalization-bound" and
                    all(logical_normalization[field] == selection[field]
                        for field in (
                            "id", "normalized_sha256", "normalized_md5",
                        )),
                    "cross-runtime logical normalization differs from plan")
        logical_sources[source["key"]] = source
    logical_records = []
    for key in sorted(logical_sources):
        source = logical_sources[key]
        logical_records.append({
            "index": len(logical_records),
            "key": source["key"],
            "original_bytes": source["original_bytes"],
            "original_sha256": source["original_sha256"],
            "original_md5": source["original_md5"],
            "candle_plan_execution_selection": copy.deepcopy(
                source["candle_plan_execution_selection"]
            ),
        })

    canonical_lp_records = []
    detailed_lp_records = sorted(
        detailed["lp_certificate_consumption"]["records"],
        key=lambda record: record["relative"],
    )
    for index, record in enumerate(detailed_lp_records):
        canonical_lp_records.append({
            "index": index,
            "class": record["class"],
            "relative": record["relative"],
            "bytes": record["bytes"],
            "sha256": record["sha256"],
            "successful_deserialization_count": 1,
        })

    projection = {
        "schema": 2,
        "kind": CROSS_RUNTIME_COVERAGE_KIND,
        "boundary_id": FINAL_BOUNDARY_ID,
        "completed_action_count": FINAL_ACTION_COUNT,
        "actions": {
            "policy": CROSS_RUNTIME_ACTION_POLICY,
            "selection_semantics":
                CROSS_RUNTIME_EXECUTION_SELECTION_SEMANTICS,
            "record_count": len(action_records),
            "ordered_record_sha256": canonical_sha256(action_records),
            "records": action_records,
        },
        "original_source_inventory": {
            "schema": 1,
            "kind": CROSS_RUNTIME_SOURCE_INVENTORY_KIND,
            "policy": CROSS_RUNTIME_SOURCE_INVENTORY_POLICY,
            "record_count": len(inventory_records),
            "normalization_binding_count": normalization_count,
            "ordered_record_sha256": canonical_sha256(inventory_records),
            "records": inventory_records,
        },
        "selected_logical_source_closure": {
            "schema": 1,
            "kind": CROSS_RUNTIME_LOGICAL_CLOSURE_KIND,
            "policy": CROSS_RUNTIME_LOGICAL_CLOSURE_POLICY,
            "order": SOURCE_CLOSURE_ORDER,
            "status": "selected-closure-observed-unapproved",
            "record_count": len(logical_records),
            "ordered_record_sha256": canonical_sha256(logical_records),
            "records": logical_records,
            "runtime_observation_retained_by_candidate": True,
        },
        "generated_inputs": copy.deepcopy(detailed["generated_inputs"]),
        "mathematical_coverage": {
            "status": "observed-uncompared",
            "structural_fingerprint_requests": list(FINAL_THEOREM_NAMES),
            "dependency_history_requests": list(FINAL_THEOREM_NAMES),
            "source_closure_observed": True,
            "lp_completed_observed": True,
            "nonlinear_completed_observed": True,
            "final_premises_completed_observed": True,
            "final_implication_completed_observed": True,
            "approved_reference_present": False,
        },
        "lp_certificate_consumption": {
            "schema": 2,
            "kind": CROSS_RUNTIME_LP_CONSUMPTION_KIND,
            "policy": CROSS_RUNTIME_LP_CONSUMPTION_POLICY,
            "order": CROSS_RUNTIME_LP_CONSUMPTION_ORDER,
            "status":
                "exactly-once-successful-deserialization-observed-unapproved",
            "record_count": len(canonical_lp_records),
            "ordered_record_sha256": canonical_sha256(canonical_lp_records),
            "records": canonical_lp_records,
            "raw_order_retained_by_candidate": True,
            "pft_used": False,
        },
        "pft_used": False,
    }
    return validate_cross_runtime_coverage_projection(projection)


def coverage_projection_from_schema5(_schema5: object) -> dict[str, Any]:
    """Fail closed until a disjoint Candle certificate-consumption schema exists."""
    raise ProtocolError(
        "schema 5 authenticates LP-certificate presence but not consumption; "
        "direct coverage projection requires the future disjoint consumption schema"
    )


def _content_record(value: object) -> dict[str, Any]:
    data = canonical_json_bytes(value)
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "md5": hashlib.md5(data, usedforsecurity=False).hexdigest(),
    }


def _validate_capture_authority(value: object) -> dict[str, Any]:
    fields = {
        "policy", "consumer_project_commit", "candle_commit", "cakeml_commit",
        "hol4_commit", "flyspeck_commit",
    }
    require(isinstance(value, dict) and set(value) == fields and
            value.get("policy") == AUTHENTICATED_CAPTURE_POLICY,
            "malformed direct schema-6 capture authority")
    for field in fields - {"policy"}:
        _hex(value.get(field), re.compile(r"[0-9a-f]{40}"),
             f"direct capture authority {field}")
    return value


def validate_authenticated_schema6_capture(
    value: object,
    *,
    receipt: object,
    authenticated_plan: object,
    expected_authority: object,
) -> dict[str, Any]:
    fields = {
        "schema", "kind", "boundary_id", "action_count", "receipt",
        "authenticated_plan", "semantic_projection", "coverage_projection",
        "cross_runtime_coverage_projection",
        "authority", "promotion", "approval_included",
        "direct_s2_execution_approved", "direct_s3_coverage_approved",
        "v1_3_s3_release_approved", "pft_used", "s2_s3_evidence",
    }
    require(isinstance(value, dict) and set(value) == fields and
            type(value.get("schema")) is int and value["schema"] == 2 and
            value.get("kind") == AUTHENTICATED_CAPTURE_KIND and
            value.get("boundary_id") == FINAL_BOUNDARY_ID and
            type(value.get("action_count")) is int and
            value["action_count"] == FINAL_ACTION_COUNT and
            value.get("promotion") is False and
            value.get("approval_included") is False and
            value.get("direct_s2_execution_approved") is False and
            value.get("direct_s3_coverage_approved") is False and
            value.get("v1_3_s3_release_approved") is False and
            value.get("pft_used") is False and
            value.get("s2_s3_evidence") is False,
            "malformed direct authenticated schema-6 capture")
    for field in ("receipt", "authenticated_plan"):
        record = value.get(field)
        require(isinstance(record, dict) and set(record) == {
                    "bytes", "sha256", "md5",
                } and type(record.get("bytes")) is int and
                record["bytes"] > 0,
                f"malformed direct capture {field} record")
        _hex(record.get("sha256"), HEX64,
             f"direct capture {field} SHA-256")
        _hex(record.get("md5"), HEX32, f"direct capture {field} MD5")
    validate_semantic_projection(value.get("semantic_projection"))
    validate_coverage_projection(value.get("coverage_projection"))
    validate_cross_runtime_coverage_projection(
        value.get("cross_runtime_coverage_projection")
    )
    authority = _validate_capture_authority(value.get("authority"))
    expected = _validate_capture_authority(expected_authority)

    require(authority == expected,
            "direct capture authority differs from authenticated authority")
    require(value["receipt"] == _content_record(receipt) and
            value["authenticated_plan"] == _content_record(authenticated_plan),
            "direct capture source content differs from bound records")
    require(isinstance(receipt, dict) and
            receipt.get("repositories") == {
                "candle": authority["candle_commit"],
                "flyspeck": authority["flyspeck_commit"],
            }, "direct capture source repositories differ from authority")
    semantic = project_authenticated_semantic_observations(
        receipt.get("semantic_fingerprints"),
        receipt.get("dependency_history"),
    )
    coverage = coverage_projection_from_schema6(
        receipt, authenticated_plan,
    )
    cross_runtime_coverage = cross_runtime_coverage_projection_from_schema6(
        receipt, authenticated_plan,
    )
    require(value["semantic_projection"] == semantic and
            value["coverage_projection"] == coverage and
            value["cross_runtime_coverage_projection"] ==
            cross_runtime_coverage,
            "direct capture projections differ from bound source content")
    return value


def build_authenticated_schema6_capture(
    receipt: object,
    authenticated_plan: object,
    authority: object,
) -> dict[str, Any]:
    authority = copy.deepcopy(_validate_capture_authority(authority))
    capture = {
        "schema": 2,
        "kind": AUTHENTICATED_CAPTURE_KIND,
        "boundary_id": FINAL_BOUNDARY_ID,
        "action_count": FINAL_ACTION_COUNT,
        "receipt": _content_record(receipt),
        "authenticated_plan": _content_record(authenticated_plan),
        "semantic_projection": project_authenticated_semantic_observations(
            receipt.get("semantic_fingerprints")
            if isinstance(receipt, dict) else None,
            receipt.get("dependency_history")
            if isinstance(receipt, dict) else None,
        ),
        "coverage_projection": coverage_projection_from_schema6(
            receipt, authenticated_plan,
        ),
        "cross_runtime_coverage_projection":
            cross_runtime_coverage_projection_from_schema6(
                receipt, authenticated_plan,
            ),
        "authority": authority,
        "promotion": False,
        "approval_included": False,
        "direct_s2_execution_approved": False,
        "direct_s3_coverage_approved": False,
        "v1_3_s3_release_approved": False,
        "pft_used": False,
        "s2_s3_evidence": False,
    }
    return validate_authenticated_schema6_capture(
        capture, receipt=receipt, authenticated_plan=authenticated_plan,
        expected_authority=authority,
    )


def _validate_content_record(value: object, label: str) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {
                "bytes", "sha256", "md5",
            } and type(value.get("bytes")) is int and value["bytes"] > 0,
            f"malformed {label} content record")
    _hex(value.get("sha256"), HEX64, f"{label} SHA-256")
    _hex(value.get("md5"), HEX32, f"{label} MD5")
    return value


def _same_canonical_value(left: object, right: object) -> bool:
    """Compare already validated JSON values without Python bool/int aliasing."""
    return canonical_value_bytes(left) == canonical_value_bytes(right)


def _validate_source_inventory(value: object, label: str) -> list[dict[str, Any]]:
    require(isinstance(value, list) and value,
            f"malformed {label} source inventory")
    previous: str | None = None
    for index, record in enumerate(value):
        require(isinstance(record, dict) and set(record) == {
                    "path", "bytes", "sha256", "md5",
                }, f"malformed {label} source record: {index}")
        path = _safe_relative(record.get("path"), f"{label} source path: {index}")
        require(previous is None or previous < path,
                f"{label} source inventory is not canonical: {index}")
        previous = path
        _validate_content_record({
            field: record[field] for field in ("bytes", "sha256", "md5")
        }, f"{label} source: {index}")
    return value


def _validate_comparison_authority(value: object) -> dict[str, Any]:
    fields = {
        "policy", "reviewer_project_commit", "reviewer_sources",
        "reviewer_entrypoint",
        "compiled_producer_project_commit", "compiled_runtime_commit",
        "compiled_consumer_sources",
        "compiled_producer_entrypoint",
        "reference_producer_project_commit", "reference_runtime_commit",
        "reference_validator_sources",
        "reference_producer_entrypoint",
    }
    require(isinstance(value, dict) and set(value) == fields and
            value.get("policy") == COMPARISON_AUTHORITY_POLICY,
            "malformed direct comparison authority")
    for field in (
        "reviewer_project_commit", "compiled_producer_project_commit",
        "reference_producer_project_commit", "compiled_runtime_commit",
        "reference_runtime_commit",
    ):
        _hex(value.get(field), re.compile(r"[0-9a-f]{40}"),
             f"direct comparison authority {field}")
    inventories = {
        "reviewer_entrypoint": _validate_source_inventory(
            value.get("reviewer_sources"), "reviewer",
        ),
        "compiled_producer_entrypoint": _validate_source_inventory(
            value.get("compiled_consumer_sources"), "compiled consumer",
        ),
        "reference_producer_entrypoint": _validate_source_inventory(
            value.get("reference_validator_sources"), "reference validator",
        ),
    }
    entrypoints = []
    for field, inventory in inventories.items():
        entrypoint = value.get(field)
        require(isinstance(entrypoint, dict) and set(entrypoint) == {
                    "path", "bytes", "sha256", "md5",
                }, f"malformed direct comparison {field}")
        _safe_relative(entrypoint.get("path"),
                       f"direct comparison {field} path")
        _validate_content_record({
            name: entrypoint[name] for name in ("bytes", "sha256", "md5")
        }, f"direct comparison {field}")
        require(any(_same_canonical_value(entrypoint, source)
                    for source in inventory),
                f"direct comparison {field} is absent from its source inventory")
        entrypoints.append(entrypoint)
    entrypoint_contents = [{
        field: item[field] for field in ("bytes", "sha256", "md5")
    } for item in entrypoints]
    require(len({canonical_value_bytes(item)
                 for item in entrypoint_contents}) == 3,
            "direct comparison reviewer and producer entrypoints are not independent")
    return value


def _validate_candidate_authority(
    value: object, role: str,
) -> dict[str, Any]:
    fields = {
        "policy", "authenticator", "project_commit", "runtime_commit",
        "entrypoint", "sources",
    }
    expected_authenticator = (
        COMPILED_COMPARISON_AUTHENTICATOR
        if role == COMPILED_COMPARISON_ROLE
        else REFERENCE_COMPARISON_AUTHENTICATOR
    )
    require(isinstance(value, dict) and set(value) == fields and
            value.get("policy") == COMPARISON_CANDIDATE_AUTHORITY_POLICY and
            value.get("authenticator") == expected_authenticator,
            "malformed authenticated comparison candidate authority")
    for field in ("project_commit", "runtime_commit"):
        _hex(value.get(field), re.compile(r"[0-9a-f]{40}"),
             f"comparison candidate authority {field}")
    sources = _validate_source_inventory(
        value.get("sources"), "comparison candidate authenticator",
    )
    entrypoint = value.get("entrypoint")
    require(isinstance(entrypoint, dict) and set(entrypoint) == {
                "path", "bytes", "sha256", "md5",
            }, "malformed comparison candidate authority entrypoint")
    _safe_relative(entrypoint.get("path"),
                   "comparison candidate authority entrypoint path")
    _validate_content_record({
        field: entrypoint[field] for field in ("bytes", "sha256", "md5")
    }, "comparison candidate authority entrypoint")
    require(any(_same_canonical_value(entrypoint, source) for source in sources),
            "comparison candidate authority entrypoint is absent from sources")
    return value


def _validate_authenticated_comparison_descriptor(
    value: object, *, role: str, ordinal: int,
) -> dict[str, Any]:
    common_fields = {
        "schema", "kind", "role", "ordinal", "candidate",
        "authenticated_nonce", "authenticated_plan", "semantic_projection",
        "cross_runtime_coverage_projection", "candidate_authority", "pft_used",
    }
    require(role in {COMPILED_COMPARISON_ROLE, REFERENCE_COMPARISON_ROLE},
            "unknown authenticated comparison candidate role")
    role_fields = (
        {"compiled_coverage_projection"}
        if role == COMPILED_COMPARISON_ROLE
        else {"reference_execution_closure"}
    )
    fields = common_fields | role_fields
    require(isinstance(value, dict) and set(value) == fields and
            type(value.get("schema")) is int and value["schema"] == 2 and
            value.get("kind") == AUTHENTICATED_COMPARISON_DESCRIPTOR_KIND and
            value.get("role") == role and
            type(value.get("ordinal")) is int and
            value["ordinal"] == ordinal and value.get("pft_used") is False,
            "malformed authenticated comparison candidate descriptor")
    _validate_content_record(value.get("candidate"),
                             "authenticated comparison candidate")
    _validate_content_record(value.get("authenticated_plan"),
                             "authenticated comparison plan")
    nonce = value.get("authenticated_nonce")
    nonce_kind = (
        COMPILED_COMPARISON_NONCE_KIND
        if role == COMPILED_COMPARISON_ROLE
        else REFERENCE_COMPARISON_NONCE_KIND
    )
    nonce_pattern = HEX32 if role == COMPILED_COMPARISON_ROLE else HEX64
    require(isinstance(nonce, dict) and set(nonce) == {"kind", "value"} and
            nonce.get("kind") == nonce_kind,
            "malformed authenticated comparison candidate nonce")
    _hex(nonce.get("value"), nonce_pattern,
         "authenticated comparison candidate nonce")
    validate_semantic_projection(value.get("semantic_projection"))
    validate_cross_runtime_coverage_projection(
        value.get("cross_runtime_coverage_projection")
    )
    if role == COMPILED_COMPARISON_ROLE:
        validate_coverage_projection(value.get("compiled_coverage_projection"))
    else:
        _validate_content_record(
            value.get("reference_execution_closure"),
            "authenticated reference execution closure",
        )
    _validate_candidate_authority(value.get("candidate_authority"), role)
    return value


def validate_unapproved_direct_comparison_fixture(
    value: object,
    *,
    authenticated_candidate_descriptors: object,
    expected_authority: object,
) -> dict[str, Any]:
    """Validate only equality output supplied by future authenticators.

    This is deliberately not a candidate authenticator and has no CLI.  A
    production caller must first replay the compiled consumer and future
    pristine-reference validators from retained raw bundles.  Each authenticator
    must then emit one indivisible descriptor binding its candidate, nonce,
    plan, common projections, role-specific evidence, and candidate authority.
    """
    fields = {
        "schema", "kind", "policy", "boundary_id", "action_count",
        "authenticated_plan", "compiled_candidate", "reference_candidates",
        "semantic_projection", "cross_runtime_coverage_projection",
        "compiled_coverage_projection", "authority",
        "comparison_status", "promotion_allowed", "approval_included",
        "direct_s2_execution_approved", "direct_s3_coverage_approved",
        "v1_3_s3_release_approved", "pft_used", "s2_s3_evidence",
    }
    require(isinstance(value, dict) and set(value) == fields and
            type(value.get("schema")) is int and value["schema"] == 2 and
            value.get("kind") == INDEPENDENT_COMPARISON_KIND and
            value.get("policy") == INDEPENDENT_COMPARISON_POLICY and
            value.get("boundary_id") == FINAL_BOUNDARY_ID and
            type(value.get("action_count")) is int and
            value["action_count"] == FINAL_ACTION_COUNT and
            value.get("comparison_status") ==
            "three-way-semantic-and-cross-runtime-coverage-match-unapproved" and
            value.get("promotion_allowed") is False and
            value.get("approval_included") is False and
            value.get("direct_s2_execution_approved") is False and
            value.get("direct_s3_coverage_approved") is False and
            value.get("v1_3_s3_release_approved") is False and
            value.get("pft_used") is False and
            value.get("s2_s3_evidence") is False,
            "malformed unapproved direct comparison fixture")
    plan_record = _validate_content_record(
        value.get("authenticated_plan"), "direct comparison plan",
    )
    compiled = value.get("compiled_candidate")
    require(isinstance(compiled, dict) and set(compiled) == {
                "candidate", "attempt_nonce",
            }, "malformed compiled direct comparison candidate")
    compiled_record = _validate_content_record(
        compiled.get("candidate"), "compiled direct candidate",
    )
    _hex(compiled.get("attempt_nonce"), HEX32,
         "compiled direct candidate nonce")
    references = value.get("reference_candidates")
    require(isinstance(references, list) and len(references) == 2,
            "direct comparison requires exactly two reference candidates")
    reference_records = []
    reference_nonces = []
    reference_execution_closures = []
    for index, reference in enumerate(references, start=1):
        require(isinstance(reference, dict) and set(reference) == {
                    "ordinal", "candidate", "session_nonce",
                    "execution_closure",
                } and type(reference.get("ordinal")) is int and
                reference["ordinal"] == index,
                f"malformed direct reference candidate: {index}")
        reference_records.append(_validate_content_record(
            reference.get("candidate"), f"direct reference candidate: {index}",
        ))
        reference_nonces.append(_hex(
            reference.get("session_nonce"), HEX64,
            f"direct reference candidate nonce: {index}",
        ))
        reference_execution_closures.append(_validate_content_record(
            reference.get("execution_closure"),
            f"direct reference execution closure: {index}",
        ))
    candidate_digests = [
        compiled_record["sha256"],
        *(record["sha256"] for record in reference_records),
    ]
    require(len(set(candidate_digests)) == 3 and
            len(set(reference_nonces)) == 2 and
            len({record["sha256"]
                 for record in reference_execution_closures}) == 2,
            "direct comparison candidates, reference nonces, or reference "
            "closures are not distinct")
    authority = _validate_comparison_authority(value.get("authority"))
    expected = _validate_comparison_authority(expected_authority)
    semantic = value.get("semantic_projection")
    cross_runtime_coverage = value.get("cross_runtime_coverage_projection")
    compiled_coverage = value.get("compiled_coverage_projection")
    validate_semantic_projection(semantic)
    validate_cross_runtime_coverage_projection(cross_runtime_coverage)
    validate_coverage_projection(compiled_coverage)

    require(isinstance(authenticated_candidate_descriptors, (list, tuple)) and
            len(authenticated_candidate_descriptors) == 3,
            "direct comparison requires three authenticated candidate "
            "descriptors")
    compiled_descriptor = _validate_authenticated_comparison_descriptor(
        authenticated_candidate_descriptors[0],
        role=COMPILED_COMPARISON_ROLE, ordinal=0,
    )
    reference_descriptors = [
        _validate_authenticated_comparison_descriptor(
            authenticated_candidate_descriptors[index],
            role=REFERENCE_COMPARISON_ROLE, ordinal=index,
        )
        for index in (1, 2)
    ]
    descriptors = [compiled_descriptor, *reference_descriptors]
    descriptor_candidates = [item["candidate"] for item in descriptors]
    descriptor_nonces = [
        item["authenticated_nonce"]["value"] for item in descriptors
    ]
    require(len({item["sha256"] for item in descriptor_candidates}) == 3 and
            len(set(descriptor_nonces)) == 3,
            "authenticated comparison candidates or nonces are not distinct")
    require(_same_canonical_value(plan_record,
                                  compiled_descriptor["authenticated_plan"]) and
            all(_same_canonical_value(plan_record, item["authenticated_plan"])
                for item in reference_descriptors),
            "direct candidates do not bind one authenticated plan")
    require(_same_canonical_value(compiled_record,
                                  compiled_descriptor["candidate"]) and
            all(_same_canonical_value(record, descriptor["candidate"])
                for record, descriptor in zip(
                    reference_records, reference_descriptors, strict=True,
                )) and
            compiled["attempt_nonce"] == descriptor_nonces[0] and
            all(nonce == descriptor["authenticated_nonce"]["value"]
                for nonce, descriptor in zip(
                    reference_nonces, reference_descriptors, strict=True,
                )) and
            all(_same_canonical_value(closure,
                                      descriptor["reference_execution_closure"])
                for closure, descriptor in zip(
                    reference_execution_closures, reference_descriptors,
                    strict=True,
                )),
            "direct comparison differs from authenticated candidate "
            "descriptors")
    require(_same_canonical_value(authority, expected),
            "direct comparison differs from authenticated reviewer authority")
    compiled_authority = {
        "policy": COMPARISON_CANDIDATE_AUTHORITY_POLICY,
        "authenticator": COMPILED_COMPARISON_AUTHENTICATOR,
        "project_commit": authority["compiled_producer_project_commit"],
        "runtime_commit": authority["compiled_runtime_commit"],
        "entrypoint": authority["compiled_producer_entrypoint"],
        "sources": authority["compiled_consumer_sources"],
    }
    reference_authority = {
        "policy": COMPARISON_CANDIDATE_AUTHORITY_POLICY,
        "authenticator": REFERENCE_COMPARISON_AUTHENTICATOR,
        "project_commit": authority["reference_producer_project_commit"],
        "runtime_commit": authority["reference_runtime_commit"],
        "entrypoint": authority["reference_producer_entrypoint"],
        "sources": authority["reference_validator_sources"],
    }
    require(_same_canonical_value(
                compiled_descriptor["candidate_authority"],
                compiled_authority,
            ) and all(_same_canonical_value(
                item["candidate_authority"], reference_authority,
            ) for item in reference_descriptors),
            "candidate authorities differ from recorded producer authority")
    require(all(_same_canonical_value(item["semantic_projection"], semantic)
                for item in descriptors) and
            all(_same_canonical_value(
                    item["cross_runtime_coverage_projection"],
                    cross_runtime_coverage,
                ) for item in descriptors) and
            _same_canonical_value(
                compiled_descriptor["compiled_coverage_projection"],
                compiled_coverage,
            ),
            "direct candidates do not have role-correct projection equality")
    return value


def validate_canonical_unapproved_direct_comparison_fixture_bytes(
    data: bytes, **authenticated_inputs: Any,
) -> dict[str, Any]:
    """Decode the non-production comparison fixture without adding authority."""
    comparison = decode_object(data, "unapproved direct comparison fixture")
    validate_unapproved_direct_comparison_fixture(
        comparison, **authenticated_inputs,
    )
    require(data == canonical_json_bytes(comparison),
            "unapproved direct comparison fixture is not canonical JSON")
    return comparison


def validate_canonical_coverage_projection_bytes(data: bytes) -> dict[str, Any]:
    projection = decode_object(data, "coverage projection")
    validate_coverage_projection(projection)
    require(data == canonical_json_bytes(projection),
            "coverage projection is not canonical JSON")
    return projection


def validate_canonical_cross_runtime_coverage_projection_bytes(
    data: bytes,
) -> dict[str, Any]:
    projection = decode_object(data, "cross-runtime coverage projection")
    validate_cross_runtime_coverage_projection(projection)
    require(data == canonical_json_bytes(projection),
            "cross-runtime coverage projection is not canonical JSON")
    return projection


def validate_canonical_semantic_projection_bytes(data: bytes) -> dict[str, Any]:
    projection = decode_object(data, "semantic projection")
    validate_semantic_projection(projection)
    require(data == canonical_json_bytes(projection),
            "semantic projection is not canonical JSON")
    return projection


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate-semantic")
    validate.add_argument("projection", type=Path)
    validate_coverage = subparsers.add_parser("validate-coverage")
    validate_coverage.add_argument("projection", type=Path)
    validate_cross_runtime = subparsers.add_parser(
        "validate-cross-runtime-coverage"
    )
    validate_cross_runtime.add_argument("projection", type=Path)
    arguments = parser.parse_args()
    try:
        data = arguments.projection.read_bytes()
        if arguments.command == "validate-semantic":
            validate_canonical_semantic_projection_bytes(data)
            print("direct semantic equality projection PASS: not an approval")
        elif arguments.command == "validate-coverage":
            validate_canonical_coverage_projection_bytes(data)
            print("direct coverage projection PASS: unapproved fixture protocol")
        else:
            validate_canonical_cross_runtime_coverage_projection_bytes(data)
            print(
                "cross-runtime coverage projection PASS: unapproved fixture "
                "protocol"
            )
    except (OSError, ProtocolError) as error:
        print(f"direct release protocol rejected: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
