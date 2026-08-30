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


def _no_pft_namespace(value: str, label: str) -> str:
    require(PFT_NAMESPACE.search(value) is None,
            f"PFT namespace is forbidden in {label}")
    return value


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
            } and isinstance(normalization.get("id"), str) and
            bool(normalization["id"])
        ), f"malformed direct logical-source normalization: {index}")
        if isinstance(normalization, dict):
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
                record["event_count"] >= 1,
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


def coverage_projection_from_schema5(_schema5: object) -> dict[str, Any]:
    """Fail closed until a disjoint Candle certificate-consumption schema exists."""
    raise ProtocolError(
        "schema 5 authenticates LP-certificate presence but not consumption; "
        "direct coverage projection requires the future disjoint consumption schema"
    )


def validate_canonical_coverage_projection_bytes(data: bytes) -> dict[str, Any]:
    projection = decode_object(data, "coverage projection")
    validate_coverage_projection(projection)
    require(data == canonical_json_bytes(projection),
            "coverage projection is not canonical JSON")
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
    arguments = parser.parse_args()
    try:
        data = arguments.projection.read_bytes()
        if arguments.command == "validate-semantic":
            validate_canonical_semantic_projection_bytes(data)
            print("direct semantic equality projection PASS: not an approval")
        else:
            validate_canonical_coverage_projection_bytes(data)
            print("direct coverage projection PASS: unapproved fixture protocol")
    except (OSError, ProtocolError) as error:
        print(f"direct release protocol rejected: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
