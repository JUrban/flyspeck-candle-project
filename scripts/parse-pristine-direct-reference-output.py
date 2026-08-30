#!/usr/bin/python3
"""Pure byte parser for pristine direct-reference source observations.

This module consumes immutable stdout/stderr bytes and already validated v3
plan/request values.  It constructs the raw transcript and native execution
closure; it never accepts those projections as inputs.

Wire lines are UTF-8, LF terminated, and tab delimited.  Decimal fields use
``0|[1-9][0-9]*``.  The exact line forms are:

``START nonce ordinal boundary``
``NATIVE_LOAD nonce event phase action-or-dash logical basename bytes sha md5``
``ACTION_COMPLETE nonce action selected-source source-sha``
``LP_SUCCESS nonce raw-index action input-index class relative bytes sha count``
``REFERENCE_COMPLETE nonce boundary action-count lp-count loader-count``

Every symbolic name, including the native-loader observation marker, comes
from the validated request marker contract.  The prose above uses spaces only
for readability; the wire separator is one tab.

This migration slice includes a bounded pure decoder for the exact semantic-v3
wire forms.  The source-stream state machine does not consume those forms yet;
it therefore rejects semantic markers and emits an explicitly incomplete,
noncandidate source rederivation.  Its result is raw, unauthenticated,
unapproved, and ineligible for S2/S3.

Trusted activation and the injected modules below are private plumbing, not an
in-process security boundary.  A future collector must run the separately
authenticated fixed-source loader as the exclusive entrypoint of a fresh
isolated process; executing a copied module can synthesize Python globals.
"""

from __future__ import annotations

import hashlib
import json
import re
from types import ModuleType
from typing import Any


INCOMPLETE_SOURCE_REDERIVATION_KIND = (
    "candle-flyspeck-pristine-direct-incomplete-source-rederivation-"
    "diagnostic-v3"
)
FINAL_SOURCE_REDERIVATION_KIND = (
    "candle-flyspeck-pristine-direct-raw-source-rederivation-v3"
)
EXPECTED_RAW_PROTOCOL_SCHEMA = 3
EXPECTED_PLAN_KIND = "candle-flyspeck-pristine-direct-reference-raw-plan-v3"
EXPECTED_REQUEST_KIND = "candle-flyspeck-pristine-direct-reference-request-v3"
EXPECTED_TRANSCRIPT_KIND = (
    "candle-flyspeck-pristine-direct-reference-transcript-v3"
)
EXPECTED_NATIVE_CLOSURE_KIND = (
    "candle-flyspeck-pristine-direct-native-execution-closure-v3"
)
EXPECTED_MARKER_PROTOCOL = (
    "candle-flyspeck-pristine-direct-reference-markers-v3"
)
EXPECTED_OUTPUT_PARSER_PATH = (
    "scripts/parse-pristine-direct-reference-output.py"
)
EXPECTED_MARKER_CONTRACT = {
    "protocol": EXPECTED_MARKER_PROTOCOL,
    "session_start": "CANDLE_PRISTINE_DIRECT_REFERENCE_START_V3",
    "native_load": "CANDLE_PRISTINE_DIRECT_NATIVE_LOAD_V3",
    "action_complete": "CANDLE_PRISTINE_DIRECT_ACTION_COMPLETE_V3",
    "lp_success": "CANDLE_PRISTINE_DIRECT_LP_SUCCESS_V3",
    "semantic_observation": "CANDLE_PRISTINE_DIRECT_SEMANTIC_V3",
    "session_complete": "CANDLE_PRISTINE_DIRECT_REFERENCE_COMPLETE_V3",
    "nonce_in_every_marker": True,
}
SEMANTIC_GRAMMAR_STATUS = (
    "decoder-available-not-integrated-into-source-stream"
)
COVERAGE_GRAMMAR_STATUS = (
    "not-derived-requires-authenticated-inventory-and-generated-inputs"
)
CANONICAL_DECIMAL = re.compile(r"0|[1-9][0-9]*")
MAX_CANONICAL_DECIMAL_DIGITS = 19
MAX_FRAMED_DECIMAL_DIGITS = 9
MAX_FRAMED_VALUE = 536870912
MAX_FRAMED_VALUE_TOKEN = b"536870912"
EXPECTED_FINAL_THEOREM_NAMES = (
    "Linear_programming_results.linear_programming_results_th",
    "Mk_all_ineq.the_nonlinear_inequalities",
    "The_kepler_conjecture.tame_nonlinear_imp_kepler_conjecture",
    "Candle_flyspeck_l2.tame_imp_kepler_conjecture",
)
PFT_TOKEN = re.compile(r"(?<![A-Za-z0-9])pft(?![A-Za-z0-9])", re.IGNORECASE)
SUCCESS_LIKE = re.compile(
    r"(?:CANDLE_|PASS(?:[\t :]|$)|SUCCESS(?:[\t :]|$)|"
    r"SUCCEEDED(?:[\t :]|$)|COMPLETED(?:[\t :]|$))",
    re.IGNORECASE,
)
FAILURE_LIKE = re.compile(
    r"(?:FAIL(?:ED)?(?:[\t :]|$)|FATAL(?:[\t :]|$)|"
    r"ERROR(?:[\t :]|$)|EXCEPTION(?:[\t :]|$)|Parsing failed(?:[\t :]|$))",
    re.IGNORECASE,
)


class OutputProtocolError(ValueError):
    """Immutable pristine output bytes violate the exact source grammar."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise OutputProtocolError(message)


_TRUSTED_ACTIVATION = globals().get("_TRUSTED_ACTIVATION") is True
_TRUSTED_PROJECT_ROOT = globals().get("_TRUSTED_PROJECT_ROOT_INPUT")
_EXECUTING_SOURCE_BYTES = globals().get("_TRUSTED_SOURCE_BYTES_INPUT")
_EXECUTING_PROTOCOL_BYTES = globals().get("_TRUSTED_PROTOCOL_BYTES_INPUT")
_EXECUTING_DIRECT_PROTOCOL_BYTES = globals().get(
    "_TRUSTED_DIRECT_PROTOCOL_BYTES_INPUT"
)
_PROTOCOL: ModuleType | None = globals().get("_TRUSTED_PROTOCOL_MODULE_INPUT")
if _TRUSTED_ACTIVATION:
    require(isinstance(_TRUSTED_PROJECT_ROOT, str) and
            type(_EXECUTING_SOURCE_BYTES) is bytes and
            type(_EXECUTING_PROTOCOL_BYTES) is bytes and
            type(_EXECUTING_DIRECT_PROTOCOL_BYTES) is bytes and
            isinstance(_PROTOCOL, ModuleType),
            "trusted parser activation is incomplete")


def _canonical_value_bytes(value: Any, label: str) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode()
    except (TypeError, ValueError) as error:
        raise OutputProtocolError(f"malformed exact JSON {label}: {error}") from error


def _require_exact_json(value: Any, expected: Any, label: str) -> None:
    require(
        _canonical_value_bytes(value, label) ==
        _canonical_value_bytes(expected, label),
        f"exact JSON {label} mismatch",
    )


def _require_compatible_protocol(module: ModuleType) -> None:
    contract = getattr(module, "MARKER_CONTRACT", None)
    require(getattr(module, "RAW_PROTOCOL_SCHEMA", None) ==
            EXPECTED_RAW_PROTOCOL_SCHEMA and
            getattr(module, "PLAN_KIND", None) == EXPECTED_PLAN_KIND and
            getattr(module, "REQUEST_KIND", None) == EXPECTED_REQUEST_KIND and
            getattr(module, "TRANSCRIPT_KIND", None) ==
            EXPECTED_TRANSCRIPT_KIND and
            getattr(module, "NATIVE_CLOSURE_KIND", None) ==
            EXPECTED_NATIVE_CLOSURE_KIND and
            getattr(module, "MARKER_PROTOCOL", None) ==
            EXPECTED_MARKER_PROTOCOL and
            getattr(module, "OUTPUT_PARSER_PATH", None) ==
            EXPECTED_OUTPUT_PARSER_PATH and
            getattr(module, "PROTOCOL_PATH", None) ==
            "scripts/pristine_direct_reference_protocol.py" and
            getattr(module, "DIRECT_PROTOCOL_PATH", None) ==
            "scripts/direct_release_protocol.py" and
            getattr(module, "AUTHORITY_POLICY", None) ==
            "exact-clean-project-hol-light-flyspeck-runtime-tool-and-input-"
            "authority-v3" and
            getattr(module, "REFERENCE_ROLE", None) ==
            "pristine-clean-reference" and
            getattr(module, "REFERENCE_NONCE_KIND", None) ==
            "reference-session-nonce-v1" and
            getattr(module, "FINAL_ACTION_COUNT", None) == 297 and
            getattr(module, "FINAL_BOUNDARY_ID", None) ==
            "07-final_assembly-through-296" and
            getattr(module, "RETAINED_STDOUT_MAX_BYTES", None) == 536870912 and
            getattr(module, "RETAINED_STDERR_MAX_BYTES", None) == 0 and
            getattr(module, "SOURCE_REDERIVATION_KIND", None) ==
            FINAL_SOURCE_REDERIVATION_KIND and
            getattr(module, "INCOMPLETE_SOURCE_REDERIVATION_KIND", None) ==
            INCOMPLETE_SOURCE_REDERIVATION_KIND and
            getattr(module, "LP_CONSUMER_ACTION_INDEX", None) == 184 and
            getattr(module, "LP_SUCCESS_KIND", None) ==
            "candle-flyspeck-pristine-direct-lp-success-stream-v1" and
            getattr(module, "LP_ORDER", None) == "raw-success-marker-order-v1" and
            getattr(module, "LOADER_LEDGER_POLICY", None) ==
            "stock-hol-light-loaded-files-success-ledger-canonical-source-map-v1" and
            getattr(module, "LOADER_LEDGER_ORDER", None) ==
            "per-phase-new-loaded-files-delta-reversed-to-success-order-v1",
            "incompatible pristine-reference protocol sibling")
    _require_exact_json(
        contract, EXPECTED_MARKER_CONTRACT,
        "pristine-reference marker contract compatibility",
    )


def _protocol() -> ModuleType:
    require(_TRUSTED_ACTIVATION and isinstance(_PROTOCOL, ModuleType),
            "trusted fixed-path parser activation is required")
    _require_compatible_protocol(_PROTOCOL)
    return _PROTOCOL


def byte_content_record(data: bytes, label: str) -> dict[str, object]:
    require(type(data) is bytes, f"{label} is not immutable bytes")
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _executing_parser_source_record(protocol: ModuleType) -> dict[str, object]:
    return {
        "path": protocol.OUTPUT_PARSER_PATH,
        **byte_content_record(
            _EXECUTING_SOURCE_BYTES, "executing output parser source",
        ),
    }


def _executing_protocol_source_record(protocol: ModuleType) -> dict[str, object]:
    return {
        "path": protocol.PROTOCOL_PATH,
        **byte_content_record(
            _EXECUTING_PROTOCOL_BYTES, "executing pristine protocol source",
        ),
    }


def _executing_direct_protocol_source_record(
    protocol: ModuleType,
) -> dict[str, object]:
    return {
        "path": protocol.DIRECT_PROTOCOL_PATH,
        **byte_content_record(
            _EXECUTING_DIRECT_PROTOCOL_BYTES,
            "executing direct-release protocol source",
        ),
    }


def _trusted_plan_request(
    plan: object, request: object, label: str,
) -> tuple[ModuleType, dict[str, Any], dict[str, Any]]:
    """Rebind every public parser operation to its loader activation."""

    protocol = _protocol()
    try:
        validated_plan = protocol.validate_raw_plan(plan)
        validated_request = protocol.validate_raw_request(
            request, validated_plan,
        )
    except protocol.ProtocolError as error:
        raise OutputProtocolError(f"invalid {label} input: {error}") from error
    for authority_name, executing, authority_label in (
        (
            "output_parser", _executing_parser_source_record(protocol),
            "executing output parser versus plan authority",
        ),
        (
            "protocol", _executing_protocol_source_record(protocol),
            "executing pristine protocol versus plan authority",
        ),
        (
            "direct_release_protocol",
            _executing_direct_protocol_source_record(protocol),
            "executing direct-release protocol versus plan authority",
        ),
    ):
        _require_exact_json(
            validated_plan["authority"]["producer"][authority_name],
            executing,
            authority_label,
        )
    require(
        validated_plan["authority"]["repositories"]["project"]["path"] ==
        _TRUSTED_PROJECT_ROOT,
        "trusted parser project root differs from plan authority",
    )
    return protocol, validated_plan, validated_request


def _decimal(value: str, label: str) -> int:
    require(0 < len(value) <= MAX_CANONICAL_DECIMAL_DIGITS,
            f"overlong {label}")
    require(CANONICAL_DECIMAL.fullmatch(value) is not None,
            f"noncanonical {label}")
    try:
        return int(value)
    except (ValueError, OverflowError) as error:
        raise OutputProtocolError(f"cannot convert {label}") from error


def _decode_lines(data: bytes, label: str, *, allow_empty: bool) -> list[str]:
    require(type(data) is bytes, f"{label} is not immutable bytes")
    if not data:
        require(allow_empty, f"empty {label}")
        return []
    require(data.endswith(b"\n"), f"{label} lacks a terminal LF")
    require(b"\r" not in data, f"{label} contains a CR byte")
    require(b"\x00" not in data, f"{label} contains a NUL byte")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise OutputProtocolError(f"{label} is not exact UTF-8: {error}") from error
    require(all(character in "\n\t" or 32 <= ord(character) <= 126
                for character in text),
            f"{label} contains a character outside the exact ASCII wire alphabet")
    return text[:-1].split("\n")


def _serialized_hex(value: str, label: str) -> bytes:
    require(value != "" and len(value) % 2 == 0 and
            re.fullmatch(r"[0-9a-f]+", value) is not None,
            f"malformed lowercase serialized hex for {label}")
    try:
        return bytes.fromhex(value)
    except ValueError as error:
        raise OutputProtocolError(f"cannot decode serialized hex for {label}") from error


def _framed_decimal(value: bytes, label: str) -> int:
    require(0 < len(value) <= MAX_FRAMED_DECIMAL_DIGITS,
            f"overlong {label}")
    require(all(48 <= byte <= 57 for byte in value) and
            (value == b"0" or value[0] != 48), f"noncanonical {label}")
    require(len(value) < len(MAX_FRAMED_VALUE_TOKEN) or
            (len(value) == len(MAX_FRAMED_VALUE_TOKEN) and
             value <= MAX_FRAMED_VALUE_TOKEN), f"oversize {label}")
    try:
        result = int(value)
    except (ValueError, OverflowError) as error:
        raise OutputProtocolError(f"cannot convert {label}") from error
    # Defense in depth; the exact lexical comparison above is the normative
    # pre-conversion bound.
    require(result <= MAX_FRAMED_VALUE, f"oversize {label}")
    return result


def _read_frame(
    data: bytes, offset: int, label: str,
) -> tuple[bytes, int]:
    colon = data.find(b":", offset)
    require(colon >= offset, f"missing {label} frame delimiter")
    length = _framed_decimal(data[offset:colon], f"{label} frame length")
    payload_start = colon + 1
    remaining = len(data) - payload_start
    require(length <= remaining, f"{label} frame exceeds remaining bytes")
    payload_end = payload_start + length
    return _extract_bounded_payload(data, payload_start, payload_end), payload_end


def _extract_bounded_payload(data: bytes, start: int, end: int) -> bytes:
    """Slice only after the caller has proved the declared frame is present."""

    return data[start:end]


def _decode_node(data: bytes, label: str) -> tuple[bytes, list[bytes]]:
    tag, offset = _read_frame(data, 0, f"{label} tag")
    count_bytes, offset = _read_frame(data, offset, f"{label} child count")
    child_count = _framed_decimal(count_bytes, f"{label} child count")
    # An empty canonical frame is two bytes (0:).  This check is deliberately
    # before range construction or child iteration.
    require(child_count <= (len(data) - offset) // 2,
            f"{label} child count exceeds remaining framed bytes")
    children: list[bytes] = []
    for child_index in range(child_count):
        child, offset = _read_frame(data, offset, f"{label} child {child_index}")
        children.append(child)
    require(offset == len(data), f"trailing bytes in {label} node")
    return tag, children


def _encode_frame(data: bytes) -> bytes:
    return str(len(data)).encode("ascii") + b":" + data


def _encode_node(tag: bytes, children: list[bytes]) -> bytes:
    return (
        _encode_frame(tag) + _encode_frame(str(len(children)).encode("ascii")) +
        b"".join(_encode_frame(child) for child in children)
    )


def _validate_list_node(data: bytes, count: int, label: str) -> None:
    tag, children = _decode_node(data, label)
    require(tag == b"list" and len(children) == count,
            f"{label} is not the exact declared list")


def decode_semantic_v3_bytes(
    data: bytes, plan: object, request: object, transcript: object,
    native_closure: object,
) -> dict[str, Any]:
    """Decode exactly ten semantic-v3 lines into a nonce-free projection.

    This pure decoder establishes only byte grammar and internal equality.  It
    is intentionally not called by the source-stream parser in this migration
    slice.  It requires the matching raw transcript/native closure solely to
    bind the final serializer identity and cannot create a completion
    observation or raw candidate.
    """

    protocol, plan, request = _trusted_plan_request(
        plan, request, "pristine semantic",
    )
    require(type(data) is bytes and
            len(data) <= plan["retained_stdout_max_bytes"],
            "semantic marker bytes exceed the exact retained stdout cap")
    try:
        transcript = protocol.validate_raw_transcript(
            transcript, plan, request,
        )
        native_closure = protocol.validate_native_execution_closure(
            native_closure, plan, request, transcript,
        )
    except protocol.ProtocolError as error:
        raise OutputProtocolError(
            f"invalid pristine semantic closure: {error}"
        ) from error
    lines = _decode_lines(data, "pristine semantic marker stream", allow_empty=False)
    require(len(lines) == 10, "semantic marker stream is not exactly ten lines")
    marker = request["marker_contract"]["semantic_observation"]
    nonce = plan["session_nonce"]
    direct = protocol._direct_protocol()
    require(tuple(getattr(direct, "FINAL_THEOREM_NAMES", ())) ==
            EXPECTED_FINAL_THEOREM_NAMES,
            "incompatible direct theorem-name contract")

    theorem_records: list[dict[str, Any]] = []
    theorem_axioms: list[bytes] = []
    for index, line in enumerate(lines[:4]):
        require(PFT_TOKEN.search(line) is None,
                f"PFT namespace is forbidden in semantic line {index}")
        fields = _exact_fields(line, 11, "semantic THEOREM")
        require(fields[0] == marker and fields[1] == "THEOREM" and
                fields[2] == nonce and
                _decimal(fields[3], "semantic theorem index") == index,
                f"semantic theorem order/identity mismatch: {index}")
        name_bytes = _serialized_hex(fields[4], f"semantic theorem name {index}")
        try:
            name = name_bytes.decode("ascii", errors="strict")
        except UnicodeDecodeError as error:
            raise OutputProtocolError(
                f"semantic theorem name is not ASCII: {index}"
            ) from error
        require(name == EXPECTED_FINAL_THEOREM_NAMES[index],
                f"semantic theorem name mismatch: {index}")
        theorem = _serialized_hex(fields[5], f"semantic theorem {index}")
        hypotheses = _serialized_hex(fields[6], f"semantic hypotheses {index}")
        conclusion = _serialized_hex(fields[7], f"semantic conclusion {index}")
        global_axioms = _serialized_hex(
            fields[8], f"semantic global axioms {index}",
        )
        hypothesis_count = _decimal(fields[9], "semantic hypothesis count")
        global_axiom_count = _decimal(fields[10], "semantic global-axiom count")
        _validate_list_node(hypotheses, hypothesis_count,
                            f"semantic hypotheses {index}")
        _validate_list_node(global_axioms, global_axiom_count,
                            f"semantic global axioms {index}")
        require(hypothesis_count == 0 and hypotheses == b"4:list1:0",
                f"semantic theorem has noncanonical hypotheses: {index}")
        require(global_axiom_count == 3,
                f"semantic theorem global-axiom count mismatch: {index}")
        require(theorem == _encode_node(b"theorem", [hypotheses, conclusion]),
                f"semantic theorem composite mismatch: {index}")
        theorem_axioms.append(global_axioms)
        theorem_records.append({
            "name": name,
            "theorem_sha256": hashlib.sha256(theorem).hexdigest(),
            "hypotheses_sha256": hashlib.sha256(hypotheses).hexdigest(),
            "conclusion_sha256": hashlib.sha256(conclusion).hexdigest(),
            "global_axioms_sha256": hashlib.sha256(global_axioms).hexdigest(),
            "hypothesis_count": hypothesis_count,
            "global_axiom_count": global_axiom_count,
        })

    require(PFT_TOKEN.search(lines[4]) is None,
            "PFT namespace is forbidden in semantic line 4")
    fields = _exact_fields(lines[4], 12, "semantic POST_STATE")
    require(fields[0] == marker and fields[1] == "POST_STATE" and
            fields[2] == nonce, "semantic post-state identity mismatch")
    kernel_state = _serialized_hex(fields[3], "semantic kernel state")
    type_constants = _serialized_hex(fields[4], "semantic type constants")
    term_constants = _serialized_hex(fields[5], "semantic term constants")
    definitions = _serialized_hex(fields[6], "semantic definitions")
    global_axioms = _serialized_hex(fields[7], "semantic post-state global axioms")
    type_count = _decimal(fields[8], "semantic type-constant count")
    term_count = _decimal(fields[9], "semantic term-constant count")
    definition_count = _decimal(fields[10], "semantic definition count")
    global_axiom_count = _decimal(fields[11], "semantic global-axiom count")
    for component, count, label in (
        (type_constants, type_count, "semantic type constants"),
        (term_constants, term_count, "semantic term constants"),
        (definitions, definition_count, "semantic definitions"),
        (global_axioms, global_axiom_count, "semantic post-state global axioms"),
    ):
        _validate_list_node(component, count, label)
    require(global_axiom_count == 3 and
            all(item == global_axioms for item in theorem_axioms),
            "semantic theorem/post-state global axioms differ")
    require(kernel_state == _encode_node(
                b"kernel-state",
                [type_constants, term_constants, definitions, global_axioms],
            ), "semantic kernel-state composite mismatch")
    post_state = {
        "kernel_state_sha256": hashlib.sha256(kernel_state).hexdigest(),
        "type_constants_sha256": hashlib.sha256(type_constants).hexdigest(),
        "term_constants_sha256": hashlib.sha256(term_constants).hexdigest(),
        "definitions_sha256": hashlib.sha256(definitions).hexdigest(),
        "global_axioms_sha256": hashlib.sha256(global_axioms).hexdigest(),
        "type_constant_count": type_count,
        "term_constant_count": term_count,
        "definition_count": definition_count,
        "global_axiom_count": global_axiom_count,
    }

    dependency_records: list[dict[str, Any]] = []
    for index, line in enumerate(lines[5:9]):
        line_index = index + 5
        require(PFT_TOKEN.search(line) is None,
                f"PFT namespace is forbidden in semantic line {line_index}")
        fields = _exact_fields(line, 6, "semantic DEPENDENCY")
        require(fields[0] == marker and fields[1] == "DEPENDENCY" and
                fields[2] == nonce and
                _decimal(fields[3], "semantic dependency index") == index,
                f"semantic dependency order/identity mismatch: {index}")
        name_bytes = _serialized_hex(fields[4], f"semantic dependency name {index}")
        try:
            name = name_bytes.decode("ascii", errors="strict")
        except UnicodeDecodeError as error:
            raise OutputProtocolError(
                f"semantic dependency name is not ASCII: {index}"
            ) from error
        require(name == EXPECTED_FINAL_THEOREM_NAMES[index],
                f"semantic dependency name mismatch: {index}")
        require(re.fullmatch(r"[0-9a-f]{32}", fields[5]) is not None,
                f"malformed semantic dependency digest: {index}")
        dependency_records.append({
            "index": index,
            "name": name,
            "full_digest_md5": fields[5],
        })

    require(PFT_TOKEN.search(lines[9]) is None,
            "PFT namespace is forbidden in semantic line 9")
    fields = _exact_fields(lines[9], 6, "semantic COMPLETE")
    require(fields[0] == marker and fields[1] == "COMPLETE" and
            fields[2] == nonce and fields[3] == plan["boundary_id"] and
            _decimal(fields[4], "semantic theorem count") == 4 and
            _decimal(fields[5], "semantic dependency count") == 4,
            "semantic completion identity/count mismatch")

    serializer_event = native_closure["loader_events"][-1]
    serializer_authority = plan["authority"]["inputs"]["serializer"]
    require(
        serializer_event["phase"] == "post-action" and
        serializer_event["action_index"] is None and
        serializer_event["logical_source"] == protocol.SERIALIZER_SOURCE and
        serializer_event["bytes"] == serializer_authority["bytes"] and
        serializer_event["sha256"] == serializer_authority["sha256"] and
        serializer_event["md5"] == serializer_authority["md5"],
        "semantic projection serializer is not the exact final native event",
    )
    serializer_path = serializer_event["logical_source"].partition(":")[2]
    require(serializer_path == serializer_authority["path"],
            "semantic projection serializer path differs from final native event")
    projection = {
        "schema": 1,
        "kind": direct.SEMANTIC_PROJECTION_KIND,
        "serializer": {
            "path": serializer_path,
            "sha256": serializer_event["sha256"],
        },
        "theorems": theorem_records,
        "post_state": post_state,
        "dependency_history": dependency_records,
    }
    try:
        return direct.validate_semantic_projection(projection)
    except direct.ProtocolError as error:
        raise OutputProtocolError(
            f"derived semantic projection is invalid: {error}"
        ) from error


def _exact_fields(line: str, count: int, label: str) -> list[str]:
    fields = line.split("\t")
    require(len(fields) == count and all(field != "" for field in fields),
            f"malformed {label} marker")
    return fields


def _action_completion(
    protocol: ModuleType, plan: dict[str, Any], events: list[dict[str, Any]],
    action_index: int, ledger_start: int,
) -> dict[str, object]:
    action = plan["actions"]["records"][action_index]
    delta = events[ledger_start:]
    selected_prior = [
        event["index"] for event in events[:ledger_start]
        if event["logical_source"] == action["selected_source"]
    ]
    selected_delta = [
        event["index"] for event in delta
        if event["logical_source"] == action["selected_source"]
    ]
    require(not (selected_prior and selected_delta),
            f"action {action_index} selected source appears twice")
    if selected_delta:
        require(len(selected_delta) == 1,
                f"action {action_index} selected source is ambiguous")
        outcome = "loaded"
        selected_index = selected_delta[0]
    else:
        require(len(selected_prior) == 1,
                f"action {action_index} lacks an observed selected source")
        outcome = "already-loaded"
        selected_index = selected_prior[0]
    return {
        "index": action_index,
        "session_nonce": plan["session_nonce"],
        "selected_source": action["selected_source"],
        "source_sha256": action["original_sha256"],
        "completion_status": "completed-observed-unapproved",
        "ledger_start_index": ledger_start,
        "ledger_end_index": len(events),
        "ordered_ledger_delta_sha256": protocol.canonical_sha256(delta),
        "loader_outcome": outcome,
        "selected_ledger_index": selected_index,
    }


def _parse_source_lines(
    stdout: bytes, plan: dict[str, Any], request: dict[str, Any],
) -> tuple[dict[str, object], dict[str, object], list[dict[str, Any]]]:
    protocol = _protocol()
    lines = _decode_lines(stdout, "pristine reference stdout", allow_empty=False)
    markers = request["marker_contract"]
    allowed = {
        markers["session_start"], markers["action_complete"],
        markers["lp_success"], markers["session_complete"],
        markers["native_load"],
    }
    nonce = plan["session_nonce"]
    started = False
    completed = False
    next_action = 0
    ledger_start: int | None = None
    action_phase_started = False
    events: list[dict[str, Any]] = []
    completions: list[dict[str, object]] = []
    lp_records: list[dict[str, object]] = []
    lp_input_indices: set[int] = set()

    for line_index, line in enumerate(lines):
        require(PFT_TOKEN.search(line) is None,
                f"PFT namespace is forbidden in stdout line {line_index}")
        marker_name = line.split("\t", 1)[0]
        if marker_name not in allowed:
            stripped = line.lstrip()
            require(SUCCESS_LIKE.match(stripped) is None,
                    f"unknown or unsupported success-like stdout line {line_index}")
            require(FAILURE_LIKE.match(stripped) is None,
                    f"failure-like stdout line {line_index}")
            require(not completed,
                    "ordinary stdout follows the terminal completion marker")
            continue

        require(not completed, "protocol marker follows terminal completion")
        if marker_name == markers["session_start"]:
            fields = _exact_fields(line, 4, "session-start")
            require(not started and not events and not completions and not lp_records,
                    "duplicate or reordered session-start marker")
            require(fields[1] == nonce and
                    _decimal(fields[2], "reference ordinal") ==
                    plan["reference_ordinal"] and
                    fields[3] == plan["boundary_id"],
                    "session-start marker differs from request")
            started = True
            continue

        require(started, "observation marker precedes session start")
        if marker_name == markers["native_load"]:
            fields = _exact_fields(line, 10, "native-load")
            require(fields[1] == nonce, "mixed nonce in native-load marker")
            event_index = _decimal(fields[2], "native-load event index")
            require(event_index == len(events),
                    "missing, duplicate, or reordered native-load event")
            phase = fields[3]
            require(phase in {"bootstrap", "action", "post-action"},
                    "unknown native-load phase")
            if phase == "bootstrap":
                require(not action_phase_started and next_action == 0 and
                        fields[4] == "-",
                        "reordered bootstrap native-load event")
                action_index: int | None = None
            elif phase == "action":
                require(next_action < protocol.FINAL_ACTION_COUNT,
                        "action native-load event follows all actions")
                action_index = _decimal(fields[4], "native-load action index")
                require(action_index == next_action,
                        "native-load event belongs to another action")
                if not action_phase_started:
                    ledger_start = len(events)
                action_phase_started = True
            else:
                require(next_action == protocol.FINAL_ACTION_COUNT and
                        fields[4] == "-",
                        "post-action native-load event precedes action completion")
                action_index = None
            event = {
                "index": event_index,
                "session_nonce": nonce,
                "phase": phase,
                "action_index": action_index,
                "logical_source": fields[5],
                "basename": fields[6],
                "bytes": _decimal(fields[7], "native-load byte count"),
                "sha256": fields[8],
                "md5": fields[9],
            }
            # The strict protocol validator checks logical-key safety, basename,
            # digest syntax, positive size, uniqueness, and phase/action typing.
            events.append(event)
            continue

        if marker_name == markers["action_complete"]:
            fields = _exact_fields(line, 5, "action-complete")
            require(fields[1] == nonce, "mixed nonce in action-complete marker")
            action_index = _decimal(fields[2], "completed action index")
            require(action_index == next_action and
                    action_index < protocol.FINAL_ACTION_COUNT,
                    "missing, duplicate, or reordered action completion")
            action = plan["actions"]["records"][action_index]
            require(fields[3] == action["selected_source"] and
                    fields[4] == action["original_sha256"],
                    f"action {action_index} completion differs from plan")
            if ledger_start is None:
                ledger_start = len(events)
            completion = _action_completion(
                protocol, plan, events, action_index, ledger_start,
            )
            completions.append(completion)
            next_action += 1
            ledger_start = len(events)
            action_phase_started = True
            continue

        if marker_name == markers["lp_success"]:
            fields = _exact_fields(line, 10, "LP-success")
            require(fields[1] == nonce, "mixed nonce in LP-success marker")
            record_index = _decimal(fields[2], "LP-success raw index")
            action_index = _decimal(fields[3], "LP-success action index")
            input_index = _decimal(fields[4], "LP-success input index")
            require(record_index == len(lp_records),
                    "missing, duplicate, or reordered LP-success event")
            require(next_action == protocol.LP_CONSUMER_ACTION_INDEX and
                    action_index == protocol.LP_CONSUMER_ACTION_INDEX,
                    "LP success is outside the consuming action")
            require(input_index not in lp_input_indices and
                    input_index < len(plan["lp_certificate_inputs"]["records"]),
                    "duplicate or out-of-range LP-success input")
            expected = plan["lp_certificate_inputs"]["records"][input_index]
            require(fields[5] == expected["class"] and
                    fields[6] == expected["relative"] and
                    _decimal(fields[7], "LP-success byte count") ==
                    expected["bytes"] and fields[8] == expected["sha256"] and
                    _decimal(fields[9], "LP successful-deserialization count") == 1,
                    "LP-success marker differs from authenticated input")
            lp_input_indices.add(input_index)
            lp_records.append({
                "index": record_index,
                "session_nonce": nonce,
                "action_index": action_index,
                "input_index": input_index,
                "class": expected["class"],
                "relative": expected["relative"],
                "bytes": expected["bytes"],
                "sha256": expected["sha256"],
                "successful_deserialization_count": 1,
            })
            continue

        fields = _exact_fields(line, 6, "session-complete")
        require(fields[1] == nonce and fields[2] == plan["boundary_id"],
                "session-complete marker differs from request")
        require(_decimal(fields[3], "completed action count") ==
                protocol.FINAL_ACTION_COUNT and
                _decimal(fields[4], "LP-success count") == 39 and
                _decimal(fields[5], "native-load count") == len(events),
                "session-complete marker has forged counts")
        require(next_action == protocol.FINAL_ACTION_COUNT and
                len(lp_records) == 39 and line_index == len(lines) - 1,
                "premature or nonterminal session-complete marker")
        completed = True

    require(started and completed, "missing pristine session boundary marker")
    require(len(completions) == protocol.FINAL_ACTION_COUNT,
            "incomplete pristine action completion stream")
    require(lp_input_indices == set(range(39)),
            "incomplete pristine LP-success stream")
    initial_count = completions[0]["ledger_start_index"]
    final_count = completions[-1]["ledger_end_index"]
    action_completions = {
        "record_count": len(completions),
        "ordered_record_sha256": protocol.canonical_sha256(completions),
        "initial_ledger_count": initial_count,
        "final_ledger_count": final_count,
        "records": completions,
    }
    lp_successes = {
        "schema": 1,
        "kind": protocol.LP_SUCCESS_KIND,
        "order": protocol.LP_ORDER,
        "record_count": len(lp_records),
        "ordered_record_sha256": protocol.canonical_sha256(lp_records),
        "records": lp_records,
    }
    return action_completions, lp_successes, events


def rederive_raw_source_observations(
    stdout: bytes, stderr: bytes, process_result: object,
    plan: object, request: object,
) -> dict[str, object]:
    """Rederive raw transcript/native closure solely from retained bytes.

    ``process_result`` is a separately retained process fact, with exact shape
    ``{"exit_code": 0, "timed_out": False}``.  It is not inferred from a
    success-looking line.
    """

    protocol, plan, request = _trusted_plan_request(
        plan, request, "pristine",
    )
    require(type(stdout) is bytes and
            len(stdout) <= plan["retained_stdout_max_bytes"],
            "pristine reference stdout exceeds the exact retained-byte cap")
    require(type(stderr) is bytes and
            len(stderr) <= plan["retained_stderr_max_bytes"],
            "pristine reference stderr exceeds the exact retained-byte cap")
    require(isinstance(process_result, dict) and set(process_result) == {
                "exit_code", "timed_out",
            } and type(process_result.get("exit_code")) is int and
            process_result["exit_code"] == 0 and
            process_result.get("timed_out") is False,
            "process result is not an exact successful exit")
    stdout_record = byte_content_record(stdout, "pristine reference stdout")
    stderr_record = byte_content_record(stderr, "pristine reference stderr")
    require(stderr == b"", "successful pristine reference stderr is not empty")
    action_completions, lp_successes, events = _parse_source_lines(
        stdout, plan, request,
    )
    transcript = {
        "schema": protocol.RAW_PROTOCOL_SCHEMA,
        "kind": protocol.TRANSCRIPT_KIND,
        "role": plan["role"],
        "reference_ordinal": plan["reference_ordinal"],
        "nonce_kind": plan["nonce_kind"],
        "session_nonce": plan["session_nonce"],
        "boundary_id": plan["boundary_id"],
        "plan": protocol.content_record(plan),
        "request": protocol.content_record(request),
        "marker_protocol": protocol.MARKER_PROTOCOL,
        "stdout": stdout_record,
        "stderr": stderr_record,
        "exit_code": 0,
        "timed_out": False,
        "session_started": True,
        "session_completed": True,
        "action_completions": action_completions,
        "lp_successes": lp_successes,
        "status": "process-complete-unapproved",
        "approval_included": False,
        "pft_used": False,
        "s2_s3_evidence": False,
    }
    try:
        protocol.validate_raw_transcript(transcript, plan, request)
    except protocol.ProtocolError as error:
        raise OutputProtocolError(
            f"rederived pristine transcript is invalid: {error}"
        ) from error
    final = action_completions["final_ledger_count"]
    closure = {
        "schema": protocol.RAW_PROTOCOL_SCHEMA,
        "kind": protocol.NATIVE_CLOSURE_KIND,
        "role": plan["role"],
        "reference_ordinal": plan["reference_ordinal"],
        "nonce_kind": plan["nonce_kind"],
        "session_nonce": plan["session_nonce"],
        "boundary_id": plan["boundary_id"],
        "plan": protocol.content_record(plan),
        "request": protocol.content_record(request),
        "transcript": protocol.content_record(transcript),
        "loader_policy": protocol.LOADER_LEDGER_POLICY,
        "loader_order": protocol.LOADER_LEDGER_ORDER,
        "loader_parentage_observed": False,
        "loader_cache_outcomes_observed": False,
        # Both observation classes are emitted into and content-bound by the
        # same immutable stdout marker stream in this v3 migration parser.
        "loader_ledger_artifact": stdout_record,
        "loader_event_count": len(events),
        "ordered_loader_event_sha256": protocol.canonical_sha256(events),
        "loader_events": events,
        "pre_action_event_count": action_completions["initial_ledger_count"],
        "post_action_event_count": len(events) - final,
        "action_bindings": action_completions,
        "lp_success_artifact": stdout_record,
        "lp_successes": lp_successes,
        "raw_lp_order_retained": True,
        "unsupported_identity_count": 0,
        "status": "native-observation-complete-unapproved",
        "approval_included": False,
        "pft_used": False,
        "s2_s3_evidence": False,
    }
    try:
        protocol.validate_native_execution_closure(
            closure, plan, request, transcript,
        )
    except protocol.ProtocolError as error:
        raise OutputProtocolError(
            f"rederived pristine native closure is invalid: {error}"
        ) from error
    return {
        "schema": protocol.RAW_PROTOCOL_SCHEMA,
        "kind": INCOMPLETE_SOURCE_REDERIVATION_KIND,
        "role": plan["role"],
        "reference_ordinal": plan["reference_ordinal"],
        "nonce_kind": plan["nonce_kind"],
        "session_nonce": plan["session_nonce"],
        "boundary_id": plan["boundary_id"],
        "plan": protocol.content_record(plan),
        "request": protocol.content_record(request),
        "stdout": stdout_record,
        "stderr": stderr_record,
        "process_result": {"exit_code": 0, "timed_out": False},
        "transcript": transcript,
        "native_execution_closure": closure,
        "semantic_projection": None,
        "semantic_completion_observation": None,
        "cross_runtime_coverage": None,
        "semantic_status": SEMANTIC_GRAMMAR_STATUS,
        "coverage_status": COVERAGE_GRAMMAR_STATUS,
        "authentication_status": "not-authenticated",
        "candidate_included": False,
        "approval_included": False,
        "promotion_allowed": False,
        "pft_used": False,
        "s2_eligible": False,
        "s3_eligible": False,
        "s2_s3_evidence": False,
    }
