#!/usr/bin/python3
"""Strict pure protocol for raw pristine direct-reference evidence.

This module validates retained JSON values and their content bindings.  It does
not inspect a filesystem, run HOL Light, authenticate a process, mint a
comparison descriptor, approve S2/S3, or authorize release.  A future producer
must rederive these values from immutable request and transcript bytes before
calling this protocol.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
from types import ModuleType
from typing import Any, Callable


FINAL_BOUNDARY_ID = "07-final_assembly-through-296"
FINAL_ACTION_COUNT = 297
REFERENCE_ROLE = "pristine-clean-reference"
REFERENCE_ORDINALS = (1, 2)
REFERENCE_NONCE_KIND = "reference-session-nonce-v1"
PLAN_KIND = "candle-flyspeck-pristine-direct-reference-raw-plan-v1"
REQUEST_KIND = "candle-flyspeck-pristine-direct-reference-request-v1"
TRANSCRIPT_KIND = "candle-flyspeck-pristine-direct-reference-transcript-v1"
NATIVE_CLOSURE_KIND = (
    "candle-flyspeck-pristine-direct-native-execution-closure-v1"
)
RAW_CANDIDATE_KIND = (
    "candle-flyspeck-pristine-direct-reference-raw-candidate-v1"
)
AUTHORITY_POLICY = (
    "exact-clean-project-hol-light-flyspeck-runtime-tool-and-input-authority-v1"
)
ACTION_POLICY = "authenticated-original-build-sequence-full-v1"
EXECUTION_SELECTION_SEMANTICS = (
    "bind-candle-plan-selection-without-pristine-overlay-execution-claim-v1"
)
LP_INPUT_KIND = "candle-flyspeck-pristine-direct-lp-input-inventory-v1"
LP_SUCCESS_KIND = "candle-flyspeck-pristine-direct-lp-success-stream-v1"
LP_ORDER = "raw-success-marker-order-v1"
LOADER_LEDGER_POLICY = (
    "stock-hol-light-loaded-files-success-ledger-canonical-source-map-v1"
)
LOADER_LEDGER_ORDER = (
    "per-phase-new-loaded-files-delta-reversed-to-success-order-v1"
)
MARKER_PROTOCOL = "candle-flyspeck-pristine-direct-reference-markers-v1"
ENVIRONMENT_POLICY = (
    "fresh-sanitized-single-thread-reference-process-serialization-key-absent-v1"
)
SERIALIZATION_ENVIRONMENT_KEY = "FLYSPECK_SERIALIZATION"
LP_WRAPPER_AFTER_ACTION_INDEX = 177
LP_VERIFY_ACTION_INDEX = 183
LP_CONSUMER_ACTION_INDEX = 184
LP_CERTIFICATE_SOURCE = "flyspeck:formal_lp/hypermap/main/lp_certificate.hl"
LP_VERIFY_SOURCE = "flyspeck:formal_lp/hypermap/verify_all.hl"
LP_CONSUMER_SOURCE = (
    "flyspeck:text_formalization/tame/linear_programming_results.hl"
)
FINAL_TARGET_SOURCE = "candle:candle/flyspeck_l2_target.ml"
SERIALIZER_SOURCE = "candle:candle/fingerprint.ml"
STRICTBUILD_SOURCE = "flyspeck:text_formalization/build/strictbuild.hl"
HOL_LIGHT_SOURCE = "candle:hol.ml"
ACTION_STRATA = (
    "base", "arithmetic", "analysis", "geometry", "lp_support",
    "nonlinear_support", "text_formalization", "final_assembly",
)
CANDLE_ONLY_REFERENCE_EXCLUSIONS = (
    "candle:candle/flyspeck_full_build.ml",
    "candle:candle/build/insulate.ml",
    "candle:candle/flyspeck_source_digests.ml",
    "candle:candle/flyspeck_source_integrity.ml",
)
ENTRYPOINT_SEQUENCE = (
    {
        "index": 0,
        "operation": "start-pristine-hol-light",
        "source": HOL_LIGHT_SOURCE,
    },
    {
        "index": 1,
        "operation": "install-native-loader-ledger-observer",
        "source": "request-local-instrumentation",
    },
    {
        "index": 2,
        "operation": "load-original-strictbuild",
        "source": STRICTBUILD_SOURCE,
    },
    {
        "index": 3,
        "operation": "execute-original-build-sequence",
        "function": "Build.build_sequence_full",
        "loader": "flyspeck_needs",
        "first_action_index": 0,
        "last_action_index": LP_WRAPPER_AFTER_ACTION_INDEX,
    },
    {
        "index": 4,
        "operation": "install-lp-success-wrapper",
        "wrapped_function": "Lp_certificate.read_lp_certificates",
        "after_action_index": LP_WRAPPER_AFTER_ACTION_INDEX,
        "before_action_index": LP_WRAPPER_AFTER_ACTION_INDEX + 1,
        "emit_only_after_success": True,
    },
    {
        "index": 5,
        "operation": "continue-original-build-sequence",
        "function": "Build.build_sequence_full",
        "loader": "flyspeck_needs",
        "first_action_index": LP_WRAPPER_AFTER_ACTION_INDEX + 1,
        "last_action_index": FINAL_ACTION_COUNT - 1,
    },
    {
        "index": 6,
        "operation": "load-final-target",
        "source": FINAL_TARGET_SOURCE,
    },
    {
        "index": 7,
        "operation": "emit-semantic-and-dependency-observations",
        "source": SERIALIZER_SOURCE,
    },
    {
        "index": 8,
        "operation": "emit-native-closure-and-complete",
    },
)
MARKER_CONTRACT = {
    "protocol": MARKER_PROTOCOL,
    "session_start": "CANDLE_PRISTINE_DIRECT_REFERENCE_START_V1",
    "action_complete": "CANDLE_PRISTINE_DIRECT_ACTION_COMPLETE_V1",
    "lp_success": "CANDLE_PRISTINE_DIRECT_LP_SUCCESS_V1",
    "semantic_observation": "CANDLE_PRISTINE_DIRECT_SEMANTIC_V1",
    "session_complete": "CANDLE_PRISTINE_DIRECT_REFERENCE_COMPLETE_V1",
    "nonce_in_every_marker": True,
}

HEX64 = re.compile(r"[0-9a-f]{64}")
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX32 = re.compile(r"[0-9a-f]{32}")
PFT_NAMESPACE = re.compile(r"(?:^|[/:._-])pft(?:$|[/:._-])", re.IGNORECASE)


class ProtocolError(ValueError):
    """A raw pristine-reference protocol value is malformed or overclaims."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProtocolError(message)


def is_int(value: object) -> bool:
    return type(value) is int


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


def content_record(value: Any) -> dict[str, object]:
    encoded = canonical_json_bytes(value)
    return {"bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest()}


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
        value = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProtocolError(f"cannot decode {label}: {error}") from error
    require(isinstance(value, dict), f"{label} is not a JSON object")
    return value


def validate_canonical_bytes(
    data: bytes, label: str, validator: Callable[[object], dict[str, Any]],
) -> dict[str, Any]:
    value = decode_object(data, label)
    require(data == canonical_json_bytes(value), f"{label} is not canonical JSON")
    return validator(value)


def _hex(value: object, pattern: re.Pattern[str], label: str) -> str:
    require(isinstance(value, str) and pattern.fullmatch(value) is not None,
            f"malformed {label}")
    return value


def _printable(value: object, label: str) -> str:
    require(isinstance(value, str) and value and
            all(32 <= ord(character) < 127 for character in value),
            f"malformed {label}")
    require(PFT_NAMESPACE.search(value) is None,
            f"PFT namespace is forbidden in {label}")
    return value


def _safe_relative(value: object, label: str) -> str:
    text = _printable(value, label)
    require("\\" not in text, f"malformed {label}")
    path = PurePosixPath(text)
    require(not path.is_absolute() and path.as_posix() == text and
            all(part not in {"", ".", ".."} for part in path.parts),
            f"unsafe {label}")
    return text


def _safe_absolute(value: object, label: str) -> str:
    text = _printable(value, label)
    require("\\" not in text, f"malformed {label}")
    path = PurePosixPath(text)
    require(text != "/" and path.is_absolute() and path.as_posix() == text and
            all(part not in {"", ".", ".."} for part in path.parts[1:]),
            f"unsafe {label}")
    return text


def _logical_key(value: object, label: str) -> str:
    text = _printable(value, label)
    repository, separator, relative = text.partition(":")
    require(separator == ":" and repository in {"candle", "flyspeck"},
            f"malformed {label} namespace")
    _safe_relative(relative, label)
    require(text not in CANDLE_ONLY_REFERENCE_EXCLUSIONS,
            f"Candle-only control or setup harness is forbidden in {label}")
    return text


def _content_record(
    value: object, label: str, *, allow_empty: bool = False,
) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {"bytes", "sha256"} and
            is_int(value.get("bytes")) and
            (value["bytes"] >= 0 if allow_empty else value["bytes"] > 0),
            f"malformed {label} content record")
    _hex(value.get("sha256"), HEX64, f"{label} SHA-256")
    return value


def _named_content_record(value: object, label: str) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {
                "path", "bytes", "sha256",
            }, f"malformed {label}")
    _safe_relative(value.get("path"), f"{label} path")
    _content_record(
        {"bytes": value.get("bytes"), "sha256": value.get("sha256")}, label,
    )
    return value


def _repository_record(value: object, label: str) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {
                "path", "git_head", "git_status",
            } and value.get("git_status") == "", f"malformed {label}")
    _safe_absolute(value.get("path"), f"{label} path")
    _hex(value.get("git_head"), HEX40, f"{label} Git head")
    return value


def _executable_record(value: object, label: str) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {
                "argument_path", "resolved_path", "bytes", "sha256", "mode",
            } and value.get("mode") == "100755", f"malformed {label}")
    _safe_absolute(value.get("argument_path"), f"{label} argument path")
    _safe_absolute(value.get("resolved_path"), f"{label} resolved path")
    _content_record(
        {"bytes": value.get("bytes"), "sha256": value.get("sha256")}, label,
    )
    return value


def _identity_fields(value: object, label: str) -> tuple[str, int, str, str]:
    require(isinstance(value, dict), f"malformed {label}")
    key = _logical_key(value.get("selected_source"), f"{label} source")
    require(is_int(value.get("original_bytes")) and value["original_bytes"] > 0,
            f"malformed {label} byte count")
    sha256 = _hex(value.get("original_sha256"), HEX64, f"{label} SHA-256")
    md5 = _hex(value.get("original_md5"), HEX32, f"{label} MD5")
    return key, value["original_bytes"], sha256, md5


def _execution_selection(value: object, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"malformed {label}")
    if value.get("mode") == "original-source":
        require(set(value) == {"mode"}, f"malformed {label}")
        return value
    require(set(value) == {
                "mode", "id", "kind", "normalized_bytes",
                "normalized_sha256", "normalized_md5", "operation_count",
            } and value.get("mode") == "candle-normalization-bound" and
            value.get("kind") == "exact_bytes_replace_sequence" and
            is_int(value.get("normalized_bytes")) and
            value["normalized_bytes"] > 0 and
            is_int(value.get("operation_count")) and
            value["operation_count"] > 0, f"malformed {label}")
    _printable(value.get("id"), f"{label} ID")
    _hex(value.get("normalized_sha256"), HEX64, f"{label} normalized SHA-256")
    _hex(value.get("normalized_md5"), HEX32, f"{label} normalized MD5")
    return value


def _action_target(value: object, selected_source: str, label: str) -> str:
    text = _printable(value, label)
    require("\\" not in text, f"malformed {label}")
    path = PurePosixPath(text)
    parts = path.parts
    require(not path.is_absolute() and path.as_posix() == text and parts and
            all(part not in {"", "."} for part in parts) and
            sum(part == ".." for part in parts) <= 1 and
            (".." not in parts or parts[0] == ".."), f"unsafe {label}")
    resolved = ["text_formalization"]
    for part in parts:
        if part == "..":
            require(len(resolved) == 1, f"unsafe {label}")
            resolved.pop()
        else:
            resolved.append(part)
    require(resolved and selected_source == f"flyspeck:{'/'.join(resolved)}",
            f"{label} does not resolve to selected source")
    return text


def _validate_role_nonce(value: dict[str, Any], label: str) -> None:
    require(value.get("role") == REFERENCE_ROLE and
            is_int(value.get("reference_ordinal")) and
            value["reference_ordinal"] in REFERENCE_ORDINALS and
            value.get("nonce_kind") == REFERENCE_NONCE_KIND,
            f"malformed {label} role/ordinal/nonce kind")
    _hex(value.get("session_nonce"), HEX64, f"{label} session nonce")


def _validate_authority(value: object) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {
                "policy", "producer", "repositories", "runtime", "inputs",
            } and value.get("policy") == AUTHORITY_POLICY,
            "malformed pristine reference authority")
    producer = value.get("producer")
    require(isinstance(producer, dict) and set(producer) == {
                "entrypoint", "protocol",
            }, "malformed pristine reference producer authority")
    _named_content_record(producer.get("entrypoint"), "producer entrypoint")
    protocol = _named_content_record(producer.get("protocol"), "producer protocol")
    require(protocol["path"] == "scripts/pristine_direct_reference_protocol.py",
            "pristine reference protocol path mismatch")

    repositories = value.get("repositories")
    require(isinstance(repositories, dict) and set(repositories) == {
                "project", "hol_light", "flyspeck",
            }, "malformed pristine reference repository authority")
    for name, record in repositories.items():
        _repository_record(record, f"{name} repository")

    runtime = value.get("runtime")
    require(isinstance(runtime, dict) and set(runtime) == {
                "ocaml_hol", "gp", "csdp", "runtime_elf_closure",
            }, "malformed pristine reference runtime authority")
    for name in ("ocaml_hol", "gp", "csdp"):
        _executable_record(runtime[name], f"{name} executable")
    _content_record(runtime.get("runtime_elf_closure"), "runtime ELF closure")

    inputs = value.get("inputs")
    require(isinstance(inputs, dict) and set(inputs) == {
                "action_plan", "source_inventory", "generated_inputs",
                "serializer", "final_target",
            }, "malformed pristine reference input authority")
    for name, record in inputs.items():
        _named_content_record(record, f"{name} input")
    require(inputs["serializer"]["path"] == "candle/fingerprint.ml" and
            inputs["final_target"]["path"] ==
            "candle/flyspeck_l2_target.ml",
            "pristine reference serializer/final-target authority mismatch")
    return value


def _validate_actions(value: object) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {
                "policy", "execution_selection_semantics", "record_count",
                "ordered_record_sha256", "records",
            } and value.get("policy") == ACTION_POLICY and
            value.get("execution_selection_semantics") ==
            EXECUTION_SELECTION_SEMANTICS and
            is_int(value.get("record_count")) and
            value["record_count"] == FINAL_ACTION_COUNT,
            "malformed pristine reference action plan")
    records = value.get("records")
    require(isinstance(records, list) and len(records) == FINAL_ACTION_COUNT,
            "pristine reference action plan is not exactly 297 records")
    fields = {
        "index", "selected_source", "target", "stratum", "original_bytes",
        "original_sha256", "original_md5", "candle_plan_execution_selection",
    }
    for index, record in enumerate(records):
        require(isinstance(record, dict) and set(record) == fields and
                is_int(record.get("index")) and record["index"] == index and
                record.get("stratum") in ACTION_STRATA,
                f"malformed pristine reference action: {index}")
        selected_source, _, _, _ = _identity_fields(
            record, f"pristine reference action: {index}",
        )
        _action_target(record.get("target"), selected_source,
                       f"pristine reference action target: {index}")
        _execution_selection(
            record.get("candle_plan_execution_selection"),
            f"pristine reference action selection: {index}",
        )
    require(value.get("ordered_record_sha256") == canonical_sha256(records),
            "pristine reference action plan digest mismatch")
    required = {
        LP_WRAPPER_AFTER_ACTION_INDEX: LP_CERTIFICATE_SOURCE,
        LP_VERIFY_ACTION_INDEX: LP_VERIFY_SOURCE,
        LP_CONSUMER_ACTION_INDEX: LP_CONSUMER_SOURCE,
    }
    for index, source in required.items():
        require(records[index]["selected_source"] == source,
                f"pristine reference LP action identity mismatch: {index}")
    return value


def _validate_lp_inputs(value: object) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == {
                "schema", "kind", "order", "record_count",
                "ordered_record_sha256", "records",
            } and is_int(value.get("schema")) and value["schema"] == 1 and
            value.get("kind") == LP_INPUT_KIND and
            value.get("order") == "canonical-relative-path-lexicographic-v1" and
            is_int(value.get("record_count")) and value["record_count"] == 39,
            "malformed pristine reference LP input inventory")
    records = value.get("records")
    require(isinstance(records, list) and len(records) == 39,
            "pristine reference LP input inventory is not exactly 39 records")
    previous: str | None = None
    prepared = 0
    identities: set[tuple[str, str, int, str]] = set()
    for index, record in enumerate(records):
        require(isinstance(record, dict) and set(record) == {
                    "index", "class", "relative", "bytes", "sha256",
                } and is_int(record.get("index")) and record["index"] == index and
                record.get("class") in {
                    "lp-certificate", "lp-certificate-prepared",
                } and is_int(record.get("bytes")) and record["bytes"] > 0,
                f"malformed pristine reference LP input: {index}")
        relative = _safe_relative(
            record.get("relative"), f"pristine reference LP input path: {index}",
        )
        require(previous is None or previous < relative,
                f"pristine reference LP input order mismatch: {index}")
        previous = relative
        sha256 = _hex(record.get("sha256"), HEX64,
                      f"pristine reference LP input SHA-256: {index}")
        identity = (record["class"], relative, record["bytes"], sha256)
        require(identity not in identities,
                f"duplicate pristine reference LP input: {index}")
        identities.add(identity)
        prepared += record["class"] == "lp-certificate-prepared"
    require(prepared == 1 and
            value.get("ordered_record_sha256") == canonical_sha256(records),
            "pristine reference LP input identity/digest mismatch")
    return value


def validate_raw_plan(value: object) -> dict[str, Any]:
    fields = {
        "schema", "kind", "role", "reference_ordinal", "nonce_kind",
        "session_nonce", "boundary_id", "fresh_process_replay_from_action_zero",
        "process_state_checkpoint", "serialization_environment",
        "environment_policy", "thread_count", "authority", "actions",
        "lp_certificate_inputs", "approval_included", "pft_used",
        "s2_s3_evidence",
    }
    require(isinstance(value, dict) and set(value) == fields and
            is_int(value.get("schema")) and value["schema"] == 1 and
            value.get("kind") == PLAN_KIND and
            value.get("boundary_id") == FINAL_BOUNDARY_ID and
            value.get("fresh_process_replay_from_action_zero") is True and
            value.get("process_state_checkpoint") is None and
            value.get("environment_policy") == ENVIRONMENT_POLICY and
            is_int(value.get("thread_count")) and value["thread_count"] == 1 and
            value.get("approval_included") is False and
            value.get("pft_used") is False and
            value.get("s2_s3_evidence") is False,
            "malformed or overclaiming pristine reference raw plan")
    _validate_role_nonce(value, "pristine reference raw plan")
    serialization = value.get("serialization_environment")
    require(isinstance(serialization, dict) and set(serialization) == {
                "key", "present",
            } and serialization.get("key") == SERIALIZATION_ENVIRONMENT_KEY and
            serialization.get("present") is False,
            "FLYSPECK_SERIALIZATION must be absent from pristine reference plan")
    _validate_authority(value.get("authority"))
    _validate_actions(value.get("actions"))
    _validate_lp_inputs(value.get("lp_certificate_inputs"))
    return value


def _same_run(value: dict[str, Any], plan: dict[str, Any], label: str) -> None:
    require(value.get("role") == plan["role"] and
            value.get("reference_ordinal") == plan["reference_ordinal"] and
            value.get("nonce_kind") == plan["nonce_kind"] and
            value.get("session_nonce") == plan["session_nonce"] and
            value.get("boundary_id") == plan["boundary_id"],
            f"{label} run identity differs from plan")


def validate_raw_request(value: object, plan: object) -> dict[str, Any]:
    plan = validate_raw_plan(plan)
    fields = {
        "schema", "kind", "role", "reference_ordinal", "nonce_kind",
        "session_nonce", "boundary_id", "plan", "request_source",
        "entrypoint_sequence", "marker_contract", "action_count",
        "serialization_environment", "fresh_process_replay_from_action_zero",
        "process_state_checkpoint", "approval_included", "pft_used",
        "s2_s3_evidence",
    }
    require(isinstance(value, dict) and set(value) == fields and
            is_int(value.get("schema")) and value["schema"] == 1 and
            value.get("kind") == REQUEST_KIND and
            is_int(value.get("action_count")) and
            value["action_count"] == FINAL_ACTION_COUNT and
            value.get("entrypoint_sequence") == list(ENTRYPOINT_SEQUENCE) and
            value.get("marker_contract") == MARKER_CONTRACT and
            value.get("serialization_environment") ==
            plan["serialization_environment"] and
            value.get("fresh_process_replay_from_action_zero") is True and
            value.get("process_state_checkpoint") is None and
            value.get("approval_included") is False and
            value.get("pft_used") is False and
            value.get("s2_s3_evidence") is False,
            "malformed or overclaiming pristine reference request")
    _validate_role_nonce(value, "pristine reference request")
    _same_run(value, plan, "pristine reference request")
    require(value.get("plan") == content_record(plan),
            "pristine reference request plan content mismatch")
    _named_content_record(value.get("request_source"), "reference request source")
    return value


def _validate_action_completions(
    value: object, plan: dict[str, Any],
) -> dict[str, Any]:
    fields = {
        "record_count", "ordered_record_sha256", "initial_ledger_count",
        "final_ledger_count", "records",
    }
    require(isinstance(value, dict) and set(value) == fields and
            is_int(value.get("record_count")) and
            value["record_count"] == FINAL_ACTION_COUNT and
            is_int(value.get("initial_ledger_count")) and
            value["initial_ledger_count"] >= 0 and
            is_int(value.get("final_ledger_count")) and
            value["final_ledger_count"] >= value["initial_ledger_count"],
            "malformed pristine reference action completions")
    records = value.get("records")
    require(isinstance(records, list) and len(records) == FINAL_ACTION_COUNT,
            "pristine reference transcript is not exactly 297 actions")
    expected_start = value["initial_ledger_count"]
    fields = {
        "index", "session_nonce", "selected_source", "source_sha256",
        "completion_status", "ledger_start_index", "ledger_end_index",
        "ordered_ledger_delta_sha256", "loader_outcome",
        "selected_ledger_index",
    }
    plan_actions = plan["actions"]["records"]
    for index, (record, action) in enumerate(zip(records, plan_actions, strict=True)):
        require(isinstance(record, dict) and set(record) == fields and
                is_int(record.get("index")) and record["index"] == index and
                record.get("session_nonce") == plan["session_nonce"] and
                record.get("selected_source") == action["selected_source"] and
                record.get("source_sha256") == action["original_sha256"] and
                record.get("completion_status") == "completed-observed-unapproved" and
                is_int(record.get("ledger_start_index")) and
                record["ledger_start_index"] == expected_start and
                is_int(record.get("ledger_end_index")) and
                record["ledger_end_index"] >= record["ledger_start_index"] and
                record.get("loader_outcome") in {"loaded", "already-loaded"} and
                is_int(record.get("selected_ledger_index")) and
                record["selected_ledger_index"] >= 0,
                f"malformed pristine reference action completion: {index}")
        _hex(record.get("ordered_ledger_delta_sha256"), HEX64,
             f"action completion loader delta SHA-256: {index}")
        expected_start = record["ledger_end_index"]
    require(expected_start == value["final_ledger_count"] and
            value.get("ordered_record_sha256") == canonical_sha256(records),
            "pristine reference action completion count/digest mismatch")
    return value


def _validate_lp_successes(
    value: object, plan: dict[str, Any],
) -> dict[str, Any]:
    fields = {
        "schema", "kind", "order", "record_count", "ordered_record_sha256",
        "records",
    }
    require(isinstance(value, dict) and set(value) == fields and
            is_int(value.get("schema")) and value["schema"] == 1 and
            value.get("kind") == LP_SUCCESS_KIND and value.get("order") == LP_ORDER and
            is_int(value.get("record_count")) and value["record_count"] == 39,
            "malformed pristine reference LP success stream")
    records = value.get("records")
    require(isinstance(records, list) and len(records) == 39,
            "pristine reference transcript is not exactly 39 LP successes")
    inputs = plan["lp_certificate_inputs"]["records"]
    input_indices: set[int] = set()
    for index, record in enumerate(records):
        require(isinstance(record, dict) and set(record) == {
                    "index", "session_nonce", "action_index", "input_index",
                    "class", "relative", "bytes", "sha256",
                    "successful_deserialization_count",
                } and is_int(record.get("index")) and record["index"] == index and
                record.get("session_nonce") == plan["session_nonce"] and
                is_int(record.get("action_index")) and
                record["action_index"] == LP_CONSUMER_ACTION_INDEX and
                is_int(record.get("input_index")) and
                0 <= record["input_index"] < 39 and
                is_int(record.get("successful_deserialization_count")) and
                record["successful_deserialization_count"] == 1,
                f"malformed pristine reference LP success: {index}")
        input_index = record["input_index"]
        require(input_index not in input_indices,
                f"duplicate pristine reference LP success: {index}")
        input_indices.add(input_index)
        expected = inputs[input_index]
        require(all(record[field] == expected[field] for field in (
                    "class", "relative", "bytes", "sha256",
                )), f"pristine reference LP success differs from input: {index}")
    require(input_indices == set(range(39)) and
            value.get("ordered_record_sha256") == canonical_sha256(records),
            "pristine reference LP success identity/digest mismatch")
    return value


def validate_raw_transcript(
    value: object, plan: object, request: object,
) -> dict[str, Any]:
    plan = validate_raw_plan(plan)
    request = validate_raw_request(request, plan)
    fields = {
        "schema", "kind", "role", "reference_ordinal", "nonce_kind",
        "session_nonce", "boundary_id", "plan", "request", "marker_protocol",
        "stdout", "stderr", "exit_code", "timed_out", "session_started",
        "session_completed", "action_completions", "lp_successes", "status",
        "approval_included", "pft_used", "s2_s3_evidence",
    }
    require(isinstance(value, dict) and set(value) == fields and
            is_int(value.get("schema")) and value["schema"] == 1 and
            value.get("kind") == TRANSCRIPT_KIND and
            value.get("marker_protocol") == MARKER_PROTOCOL and
            is_int(value.get("exit_code")) and value["exit_code"] == 0 and
            value.get("timed_out") is False and
            value.get("session_started") is True and
            value.get("session_completed") is True and
            value.get("status") == "process-complete-unapproved" and
            value.get("approval_included") is False and
            value.get("pft_used") is False and
            value.get("s2_s3_evidence") is False,
            "malformed or overclaiming pristine reference transcript")
    _validate_role_nonce(value, "pristine reference transcript")
    _same_run(value, plan, "pristine reference transcript")
    require(value.get("plan") == content_record(plan) and
            value.get("request") == content_record(request),
            "pristine reference transcript input content mismatch")
    _content_record(value.get("stdout"), "reference stdout", allow_empty=True)
    _content_record(value.get("stderr"), "reference stderr", allow_empty=True)
    _validate_action_completions(value.get("action_completions"), plan)
    _validate_lp_successes(value.get("lp_successes"), plan)
    return value


def _validate_loader_events(
    value: object, session_nonce: str,
) -> list[dict[str, Any]]:
    require(isinstance(value, list) and value,
            "pristine native loader ledger is empty")
    identities: set[tuple[str, str]] = set()
    fields = {
        "index", "session_nonce", "phase", "action_index", "logical_source",
        "basename", "bytes", "sha256", "md5",
    }
    for index, record in enumerate(value):
        require(isinstance(record, dict) and set(record) == fields and
                is_int(record.get("index")) and record["index"] == index and
                record.get("session_nonce") == session_nonce and
                record.get("phase") in {"bootstrap", "action", "post-action"} and
                is_int(record.get("bytes")) and record["bytes"] > 0,
                f"malformed pristine native loader event: {index}")
        key = _logical_key(record.get("logical_source"),
                           f"native loader event source: {index}")
        relative = key.partition(":")[2]
        require(record.get("basename") == PurePosixPath(relative).name,
                f"native loader event basename mismatch: {index}")
        sha256 = _hex(record.get("sha256"), HEX64,
                      f"native loader event SHA-256: {index}")
        md5 = _hex(record.get("md5"), HEX32,
                   f"native loader event MD5: {index}")
        identity = (key, md5)
        require(identity not in identities,
                f"duplicate pristine native loader identity: {index}")
        identities.add(identity)
        action_index = record.get("action_index")
        if record["phase"] == "action":
            require(is_int(action_index) and 0 <= action_index < FINAL_ACTION_COUNT,
                    f"native loader action index mismatch: {index}")
        else:
            require(action_index is None,
                    f"non-action loader event has action index: {index}")
    return value


def validate_native_execution_closure(
    value: object, plan: object, request: object, transcript: object,
) -> dict[str, Any]:
    plan = validate_raw_plan(plan)
    request = validate_raw_request(request, plan)
    transcript = validate_raw_transcript(transcript, plan, request)
    fields = {
        "schema", "kind", "role", "reference_ordinal", "nonce_kind",
        "session_nonce", "boundary_id", "plan", "request", "transcript",
        "loader_policy", "loader_order", "loader_parentage_observed",
        "loader_cache_outcomes_observed", "loader_ledger_artifact",
        "loader_event_count", "ordered_loader_event_sha256", "loader_events",
        "pre_action_event_count", "post_action_event_count", "action_bindings",
        "lp_success_artifact", "lp_successes", "raw_lp_order_retained",
        "unsupported_identity_count", "status", "approval_included", "pft_used",
        "s2_s3_evidence",
    }
    require(isinstance(value, dict) and set(value) == fields and
            is_int(value.get("schema")) and value["schema"] == 1 and
            value.get("kind") == NATIVE_CLOSURE_KIND and
            value.get("loader_policy") == LOADER_LEDGER_POLICY and
            value.get("loader_order") == LOADER_LEDGER_ORDER and
            value.get("loader_parentage_observed") is False and
            value.get("loader_cache_outcomes_observed") is False and
            value.get("raw_lp_order_retained") is True and
            is_int(value.get("unsupported_identity_count")) and
            value["unsupported_identity_count"] == 0 and
            value.get("status") == "native-observation-complete-unapproved" and
            value.get("approval_included") is False and
            value.get("pft_used") is False and
            value.get("s2_s3_evidence") is False,
            "malformed or overclaiming pristine native execution closure")
    _validate_role_nonce(value, "pristine native execution closure")
    _same_run(value, plan, "pristine native execution closure")
    require(value.get("plan") == content_record(plan) and
            value.get("request") == content_record(request) and
            value.get("transcript") == content_record(transcript),
            "pristine native execution closure input content mismatch")
    _content_record(value.get("loader_ledger_artifact"),
                    "native loader-ledger artifact")
    _content_record(value.get("lp_success_artifact"), "native LP-success artifact")

    events = _validate_loader_events(
        value.get("loader_events"), plan["session_nonce"],
    )
    require(is_int(value.get("loader_event_count")) and
            value["loader_event_count"] == len(events) and
            value.get("ordered_loader_event_sha256") == canonical_sha256(events),
            "pristine native loader event count/digest mismatch")
    action_bindings = value.get("action_bindings")
    require(action_bindings == transcript["action_completions"],
            "native action bindings differ from transcript")
    initial = action_bindings["initial_ledger_count"]
    final = action_bindings["final_ledger_count"]
    require(is_int(value.get("pre_action_event_count")) and
            value["pre_action_event_count"] == initial and
            is_int(value.get("post_action_event_count")) and
            value["post_action_event_count"] == len(events) - final and
            0 <= initial <= final <= len(events),
            "native loader phase cardinality mismatch")
    require(all(event["phase"] == "bootstrap" and event["action_index"] is None
                for event in events[:initial]) and
            all(event["phase"] == "post-action" and
                event["action_index"] is None for event in events[final:]),
            "native loader bootstrap/post-action phase mismatch")

    plan_actions = plan["actions"]["records"]
    for index, (binding, action) in enumerate(zip(
        action_bindings["records"], plan_actions, strict=True,
    )):
        start = binding["ledger_start_index"]
        end = binding["ledger_end_index"]
        require(end <= final and
                all(event["phase"] == "action" and
                    event["action_index"] == index for event in events[start:end]) and
                binding["ordered_ledger_delta_sha256"] ==
                canonical_sha256(events[start:end]),
                f"native loader delta differs from action binding: {index}")
        selected_index = binding["selected_ledger_index"]
        if binding["loader_outcome"] == "loaded":
            require(start <= selected_index < end,
                    f"loaded action lacks selected ledger event: {index}")
        else:
            require(selected_index < start,
                    f"already-loaded action lacks prior ledger event: {index}")
        selected = events[selected_index]
        require(selected["logical_source"] == action["selected_source"] and
                selected["bytes"] == action["original_bytes"] and
                selected["sha256"] == action["original_sha256"] and
                selected["md5"] == action["original_md5"],
                f"native selected loader identity differs from action: {index}")

    post_keys = [event["logical_source"] for event in events[final:]]
    require(post_keys.count(FINAL_TARGET_SOURCE) == 1 and
            post_keys.count(SERIALIZER_SOURCE) == 1,
            "native closure lacks exact final-target/serializer observations")
    inputs = plan["authority"]["inputs"]
    by_key = {event["logical_source"]: event for event in events[final:]}
    for key, input_name in (
        (FINAL_TARGET_SOURCE, "final_target"),
        (SERIALIZER_SOURCE, "serializer"),
    ):
        event = by_key[key]
        claimed = inputs[input_name]
        require(event["bytes"] == claimed["bytes"] and
                event["sha256"] == claimed["sha256"],
                f"native {input_name} differs from authority")

    lp_successes = _validate_lp_successes(value.get("lp_successes"), plan)
    require(lp_successes == transcript["lp_successes"],
            "native LP successes differ from transcript")
    return value


_DIRECT_PROTOCOL: ModuleType | None = None


def _direct_protocol() -> ModuleType:
    global _DIRECT_PROTOCOL
    if _DIRECT_PROTOCOL is None:
        path = Path(__file__).with_name("direct_release_protocol.py")
        spec = importlib.util.spec_from_file_location(
            "_pristine_reference_exact_direct_release_protocol", path,
        )
        require(spec is not None and spec.loader is not None,
                "cannot load exact direct-release protocol sibling")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        require(module.FINAL_BOUNDARY_ID == FINAL_BOUNDARY_ID and
                module.FINAL_ACTION_COUNT == FINAL_ACTION_COUNT and
                module.REFERENCE_COMPARISON_ROLE == REFERENCE_ROLE and
                module.REFERENCE_COMPARISON_NONCE_KIND == REFERENCE_NONCE_KIND and
                tuple(module.CROSS_RUNTIME_EXCLUDED_LOGICAL_KEYS) ==
                CANDLE_ONLY_REFERENCE_EXCLUSIONS,
                "incompatible direct-release protocol sibling")
        _DIRECT_PROTOCOL = module
    return _DIRECT_PROTOCOL


def _validate_common_projections(
    semantic_projection: object, coverage_projection: object,
) -> None:
    direct = _direct_protocol()
    try:
        direct.validate_semantic_projection(semantic_projection)
        direct.validate_cross_runtime_coverage_projection(coverage_projection)
    except direct.ProtocolError as error:
        raise ProtocolError(f"invalid common direct projection: {error}") from error


def _bind_plan_to_common_projections(
    plan: dict[str, Any], semantic_projection: dict[str, Any],
    coverage_projection: dict[str, Any],
) -> None:
    plan_actions = plan["actions"]["records"]
    coverage_actions = coverage_projection["actions"]["records"]
    require(len(plan_actions) == len(coverage_actions) and all(
                all(plan_action[field] == coverage_action[field] for field in (
                    "index", "selected_source", "target", "stratum",
                    "original_bytes", "original_sha256", "original_md5",
                    "candle_plan_execution_selection",
                )) and coverage_action["completion_status"] ==
                "completed-observed-unapproved"
                for plan_action, coverage_action in
                zip(plan_actions, coverage_actions, strict=True)
            ), "pristine raw plan actions differ from common coverage")
    plan_lp = plan["lp_certificate_inputs"]["records"]
    coverage_lp = coverage_projection["lp_certificate_consumption"]["records"]
    require(len(plan_lp) == len(coverage_lp) and all(
                all(plan_record[field] == coverage_record[field] for field in (
                    "index", "class", "relative", "bytes", "sha256",
                )) and coverage_record["successful_deserialization_count"] == 1
                for plan_record, coverage_record in
                zip(plan_lp, coverage_lp, strict=True)
            ), "pristine raw plan LP inputs differ from common coverage")
    authority_inputs = plan["authority"]["inputs"]
    for name, value in (
        ("action_plan", plan["actions"]),
        ("source_inventory", coverage_projection["original_source_inventory"]),
        ("generated_inputs", coverage_projection["generated_inputs"]),
    ):
        record = authority_inputs[name]
        require({"bytes": record["bytes"], "sha256": record["sha256"]} ==
                content_record(value),
                f"pristine {name} authority differs from common coverage")
    require(authority_inputs["serializer"]["sha256"] ==
            semantic_projection["serializer"]["sha256"],
            "pristine serializer authority differs from semantic projection")
    final = next(
        (record for record in
         coverage_projection["original_source_inventory"]["records"]
         if record["key"] == FINAL_TARGET_SOURCE),
        None,
    )
    require(final is not None and
            authority_inputs["final_target"]["bytes"] ==
            final["original_bytes"] and
            authority_inputs["final_target"]["sha256"] ==
            final["original_sha256"],
            "pristine final-target authority differs from common coverage")


def validate_raw_candidate(
    value: object, plan: object, request: object, transcript: object,
    native_closure: object, semantic_projection: object,
    coverage_projection: object,
) -> dict[str, Any]:
    plan = validate_raw_plan(plan)
    request = validate_raw_request(request, plan)
    transcript = validate_raw_transcript(transcript, plan, request)
    native_closure = validate_native_execution_closure(
        native_closure, plan, request, transcript,
    )
    _validate_common_projections(semantic_projection, coverage_projection)
    _bind_plan_to_common_projections(
        plan, semantic_projection, coverage_projection,
    )
    fields = {
        "schema", "kind", "role", "reference_ordinal", "nonce_kind",
        "session_nonce", "boundary_id", "status", "authentication_status",
        "authority_sha256", "artifacts", "action_count", "loader_event_count",
        "lp_success_count", "exit_code", "timed_out", "validation_error",
        "fresh_process_replay_from_action_zero", "process_state_checkpoint",
        "serialization_environment", "approved_reference_present",
        "promotion_allowed", "pft_used", "s2_eligible", "s3_eligible",
        "s2_s3_evidence",
    }
    require(isinstance(value, dict) and set(value) == fields and
            is_int(value.get("schema")) and value["schema"] == 1 and
            value.get("kind") == RAW_CANDIDATE_KIND and
            value.get("status") == "complete-unapproved" and
            value.get("authentication_status") == "not-authenticated" and
            value.get("authority_sha256") == canonical_sha256(plan["authority"]) and
            is_int(value.get("action_count")) and
            value["action_count"] == FINAL_ACTION_COUNT and
            is_int(value.get("loader_event_count")) and
            value["loader_event_count"] == native_closure["loader_event_count"] and
            is_int(value.get("lp_success_count")) and
            value["lp_success_count"] == 39 and
            is_int(value.get("exit_code")) and value["exit_code"] == 0 and
            value.get("timed_out") is False and
            value.get("validation_error") is None and
            value.get("fresh_process_replay_from_action_zero") is True and
            value.get("process_state_checkpoint") is None and
            value.get("serialization_environment") ==
            plan["serialization_environment"] and
            value.get("approved_reference_present") is False and
            value.get("promotion_allowed") is False and
            value.get("pft_used") is False and
            value.get("s2_eligible") is False and
            value.get("s3_eligible") is False and
            value.get("s2_s3_evidence") is False,
            "malformed or overclaiming pristine raw candidate")
    _validate_role_nonce(value, "pristine raw candidate")
    _same_run(value, plan, "pristine raw candidate")
    artifacts = value.get("artifacts")
    expected = {
        "plan": content_record(plan),
        "request": content_record(request),
        "transcript": content_record(transcript),
        "native_execution_closure": content_record(native_closure),
        "semantic_projection": content_record(semantic_projection),
        "cross_runtime_coverage": content_record(coverage_projection),
    }
    require(isinstance(artifacts, dict) and set(artifacts) == set(expected),
            "malformed pristine raw candidate artifact closure")
    for name, record in artifacts.items():
        _content_record(record, f"raw candidate {name}")
    require(artifacts == expected,
            "pristine raw candidate artifact content mismatch")
    return value


BUNDLE_FIELDS = {
    "plan", "request", "transcript", "native_execution_closure",
    "semantic_projection", "cross_runtime_coverage", "candidate",
}


def validate_reference_bundle(value: object) -> dict[str, Any]:
    require(isinstance(value, dict) and set(value) == BUNDLE_FIELDS,
            "malformed pristine raw reference bundle")
    validate_raw_candidate(
        value["candidate"], value["plan"], value["request"],
        value["transcript"], value["native_execution_closure"],
        value["semantic_projection"], value["cross_runtime_coverage"],
    )
    return value


def validate_distinct_reference_pair(
    first: object, second: object,
) -> tuple[dict[str, Any], dict[str, Any]]:
    first = validate_reference_bundle(first)
    second = validate_reference_bundle(second)
    first_plan = first["plan"]
    second_plan = second["plan"]
    require((first_plan["reference_ordinal"], second_plan["reference_ordinal"]) ==
            REFERENCE_ORDINALS,
            "pristine reference pair ordinals must be exactly 1 then 2")
    require(first_plan["session_nonce"] != second_plan["session_nonce"],
            "pristine reference pair reused a session nonce")
    require(first_plan["authority"] == second_plan["authority"] and
            first_plan["actions"] == second_plan["actions"] and
            first_plan["lp_certificate_inputs"] ==
            second_plan["lp_certificate_inputs"],
            "pristine reference pair does not share exact authority/plan inputs")
    for artifact in ("request", "transcript", "native_execution_closure"):
        require(first["candidate"]["artifacts"][artifact] !=
                second["candidate"]["artifacts"][artifact],
                f"pristine reference pair reused {artifact} content")
    require(content_record(first["candidate"]) != content_record(second["candidate"]),
            "pristine reference pair reused candidate content")
    return first, second


def validate_canonical_raw_plan_bytes(data: bytes) -> dict[str, Any]:
    return validate_canonical_bytes(data, "pristine raw plan", validate_raw_plan)


def validate_canonical_raw_request_bytes(
    data: bytes, plan: object,
) -> dict[str, Any]:
    return validate_canonical_bytes(
        data, "pristine raw request", lambda value: validate_raw_request(value, plan),
    )


def validate_canonical_raw_transcript_bytes(
    data: bytes, plan: object, request: object,
) -> dict[str, Any]:
    return validate_canonical_bytes(
        data, "pristine raw transcript",
        lambda value: validate_raw_transcript(value, plan, request),
    )


def validate_canonical_native_closure_bytes(
    data: bytes, plan: object, request: object, transcript: object,
) -> dict[str, Any]:
    return validate_canonical_bytes(
        data, "pristine native closure",
        lambda value: validate_native_execution_closure(
            value, plan, request, transcript,
        ),
    )


def validate_canonical_raw_candidate_bytes(
    data: bytes, plan: object, request: object, transcript: object,
    native_closure: object, semantic_projection: object,
    coverage_projection: object,
) -> dict[str, Any]:
    return validate_canonical_bytes(
        data, "pristine raw candidate",
        lambda value: validate_raw_candidate(
            value, plan, request, transcript, native_closure,
            semantic_projection, coverage_projection,
        ),
    )
