#!/usr/bin/python3
"""Strict pure projections for the direct Flyspeck release protocol.

This module does not authenticate a runtime result and never approves S2, S3,
or a release.  Its first protocol slice projects already authenticated final-
boundary observations onto the exact nonce-free semantic equality value that a
later independent approval validator may compare.
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
HEX64 = re.compile(r"[0-9a-f]{64}")
HEX32 = re.compile(r"[0-9a-f]{32}")


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
    arguments = parser.parse_args()
    try:
        data = arguments.projection.read_bytes()
        validate_canonical_semantic_projection_bytes(data)
        print("direct semantic equality projection PASS: not an approval")
    except (OSError, ProtocolError) as error:
        print(f"direct release protocol rejected: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
