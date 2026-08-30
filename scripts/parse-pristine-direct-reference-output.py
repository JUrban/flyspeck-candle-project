#!/usr/bin/python3
"""Pure byte parser for pristine direct-reference source observations.

This module consumes immutable stdout/stderr bytes and already validated v1
plan/request values.  It constructs the raw transcript and native execution
closure; it never accepts those projections as inputs.

Wire lines are UTF-8, LF terminated, and tab delimited.  Decimal fields use
``0|[1-9][0-9]*``.  The exact line forms are:

``START nonce ordinal boundary``
``NATIVE_LOAD nonce event phase action-or-dash logical basename bytes sha md5``
``ACTION_COMPLETE nonce action selected-source source-sha``
``LP_SUCCESS nonce raw-index action input-index class relative bytes sha count``
``REFERENCE_COMPLETE nonce boundary action-count lp-count loader-count``

The symbolic names come from the validated request marker contract except for
``CANDLE_PRISTINE_DIRECT_NATIVE_LOAD_V1``, which this parser defines as the
native-loader observation marker.  The prose above uses spaces only for
readability; the wire separator is one tab.

No exact pristine dependency-history/semantic marker grammar exists yet.
Accordingly this parser rejects semantic, fingerprint, and other unknown
success-like markers and emits no semantic or coverage projection.  Its result
is raw, unauthenticated, unapproved, and ineligible for S2/S3.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import re
from types import ModuleType
from typing import Any


SOURCE_REDERIVATION_KIND = (
    "candle-flyspeck-pristine-direct-raw-source-rederivation-v1"
)
NATIVE_LOAD_MARKER = "CANDLE_PRISTINE_DIRECT_NATIVE_LOAD_V1"
SEMANTIC_GRAMMAR_STATUS = (
    "not-parsed-exact-pristine-semantic-marker-grammar-absent"
)
COVERAGE_GRAMMAR_STATUS = (
    "not-derived-semantic-and-completion-grammar-absent"
)
CANONICAL_DECIMAL = re.compile(r"0|[1-9][0-9]*")
MAX_CANONICAL_DECIMAL_DIGITS = 19
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


_PROTOCOL: ModuleType | None = None


def _protocol() -> ModuleType:
    global _PROTOCOL
    if _PROTOCOL is None:
        path = Path(__file__).with_name("pristine_direct_reference_protocol.py")
        spec = importlib.util.spec_from_file_location(
            "_pristine_direct_reference_output_exact_protocol", path,
        )
        require(spec is not None and spec.loader is not None,
                "cannot load exact pristine-reference protocol sibling")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _PROTOCOL = module
    return _PROTOCOL


def byte_content_record(data: bytes, label: str) -> dict[str, object]:
    require(type(data) is bytes, f"{label} is not immutable bytes")
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


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
        NATIVE_LOAD_MARKER,
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
        if marker_name == NATIVE_LOAD_MARKER:
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

    protocol = _protocol()
    try:
        plan = protocol.validate_raw_plan(plan)
        request = protocol.validate_raw_request(request, plan)
    except protocol.ProtocolError as error:
        raise OutputProtocolError(f"invalid pristine input: {error}") from error
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
        "schema": 1,
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
        "schema": 1,
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
        # same immutable stdout marker stream in this v1 parser.
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
        "schema": 1,
        "kind": SOURCE_REDERIVATION_KIND,
        "role": plan["role"],
        "reference_ordinal": plan["reference_ordinal"],
        "nonce_kind": plan["nonce_kind"],
        "session_nonce": plan["session_nonce"],
        "boundary_id": plan["boundary_id"],
        "plan": protocol.content_record(plan),
        "request": protocol.content_record(request),
        "stdout": stdout_record,
        "stderr": stderr_record,
        "transcript": transcript,
        "native_execution_closure": closure,
        "semantic_projection": None,
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
