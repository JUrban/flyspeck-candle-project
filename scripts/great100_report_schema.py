"""Canonical versioned JSON shape for Great100 schema-4 run reports.

The qualified producer is an immutable, already-audited artifact, so it cannot
import a module added by its successor finalizer project.  Instead, the
finalizer applies this authority to the authenticated ``candle/regression.py``
bytes before accepting a report.  Tests use the same authority to construct
their producer fixture.  A schema change therefore requires a new versioned
authority rather than another handwritten producer/finalizer key copy.
"""

from __future__ import annotations

import ast
from types import MappingProxyType


REPORT_SCHEMA_VERSION = 4

_SHAPES = {
    "report": {
        "schema", "generated_utc", "suite_started_utc", "suite",
        "test_count", "jobs", "timeout_policy", "wall_seconds",
        "sum_test_seconds", "counts", "candle_root", "candle_git_head",
        "candle_git_status", "candle_executable", "log_directory",
        "fingerprint_contract", "s1_evidence", "run_evidence",
        "execution_contract", "source_closure", "independent_approval",
        "linked_record", "results", "promotion",
    },
    "result": {
        "name", "files", "status", "timeout_kind", "boot_elapsed_seconds",
        "hol_elapsed_seconds", "test_elapsed_seconds",
        "fingerprint_elapsed_seconds", "total_elapsed_seconds",
        "peak_process_rss_kib", "peak_tree_rss_kib", "error_message",
        "log_path", "process_evidence", "fingerprints",
    },
    "process_evidence": {
        "suite_nonce", "process_nonce", "pid", "started_utc",
        "completed_utc", "exit_code", "markers", "linked_record_sha256",
        "transcript", "pre_runtime_state", "post_runtime_state",
        "resource_sampling",
    },
    "run_evidence": {
        "suite_nonce", "marker_contract", "linked_record_sha256",
        "source_closure_sha256", "independent_approval_sha256",
    },
    "fingerprints": {
        "status", "mapping_status", "expected_identities_present",
        "serializer", "theorems", "post_state", "approval_sha256",
    },
    "theorem": {
        "name", "theorem_sha256", "hypotheses_sha256",
        "conclusion_sha256", "global_axioms_sha256", "hypothesis_count",
        "global_axiom_count",
    },
    "post_state": {
        "kernel_state_sha256", "type_constants_sha256",
        "type_constant_count", "term_constants_sha256",
        "term_constant_count", "definitions_sha256", "definition_count",
        "global_axioms_sha256", "global_axiom_count",
    },
    "runtime_state": {
        "candle_git_head", "candle_git_status", "linked_record_sha256",
        "candle_executable", "execution_contract_sha256",
        "source_closure_sha256",
    },
    "resource_sampling": {
        "interval_seconds", "sample_count", "root_observed",
        "sampler_completed", "peak_process_rss_kib", "peak_tree_rss_kib",
    },
    "markers": {"suite_line", "start_line", "linked_line", "complete_line"},
    "s1_evidence": {
        "requested_target_count", "reported_target_count",
        "expected_identity_target_count", "manual_review_mapping_target_count",
        "matched_target_count", "observed_uncompared_target_count",
        "missing_or_failed_fingerprint_target_count", "suite_closed",
    },
    "timeout_policy": {
        "inactivity_timeout_seconds", "inactivity_resets_on",
        "inactivity_scope", "total_wall_timeout_seconds",
        "total_wall_scope", "progress_extends_total_wall_deadline",
    },
    "promotion": {
        "eligible", "s1_evidence", "required_linked_schema", "reason",
    },
}

REPORT_SCHEMA_SHAPES = MappingProxyType({
    name: frozenset(keys) for name, keys in _SHAPES.items()
})

PROMOTABLE_TOP100_PROMOTION = MappingProxyType({
    "eligible": True,
    "s1_evidence": True,
    "required_linked_schema": 6,
    "reason": "promotable-schema-6-full-suite",
})


def shape(name: str) -> frozenset[str]:
    """Return one closed schema-4 object-key set."""
    return REPORT_SCHEMA_SHAPES[name]


def _constant_bindings(tree: ast.Module) -> dict[str, object]:
    bindings: dict[str, object] = {}
    for statement in tree.body:
        if (isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)):
            try:
                bindings[statement.targets[0].id] = ast.literal_eval(
                    statement.value)
            except (ValueError, TypeError):
                pass
    return bindings


def _closed_dict(node: ast.AST, bindings: dict[str, object]) -> dict[str, object]:
    if not isinstance(node, ast.Dict) or any(key is None for key in node.keys):
        raise ValueError("producer schema declaration is not a closed dict")
    result: dict[str, object] = {}
    for key_node, value_node in zip(node.keys, node.values):
        if not isinstance(key_node, ast.Constant) or not isinstance(
                key_node.value, str):
            raise ValueError("producer schema declaration has a dynamic key")
        if isinstance(value_node, ast.Name) and value_node.id in bindings:
            value = bindings[value_node.id]
        else:
            try:
                value = ast.literal_eval(value_node)
            except (ValueError, TypeError):
                value = None
        result[key_node.value] = value
    return result


def validate_producer_source(source: bytes) -> None:
    """Verify the immutable producer declares this exact schema-4 envelope.

    This is deliberately a static check: importing the producer would execute
    environment-sensitive runner setup, while rewriting it would invalidate
    the qualified source closure.  The finalizer calls this on the already
    captured and authenticated producer bytes.
    """
    try:
        tree = ast.parse(source.decode("utf-8"), filename="candle/regression.py")
    except (UnicodeDecodeError, SyntaxError) as error:
        raise ValueError("cannot parse authenticated Great100 producer") from error
    bindings = _constant_bindings(tree)
    reporter = next((node for node in tree.body
                     if isinstance(node, ast.ClassDef)
                     and node.name == "Reporter"), None)
    if reporter is None:
        raise ValueError("producer lacks Reporter")
    writer = next((node for node in reporter.body
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and node.name == "write_json"), None)
    if writer is None:
        raise ValueError("producer lacks Reporter.write_json")

    payloads = [node.value for node in ast.walk(writer)
                if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name)
                        and target.id == "payload" for target in node.targets)]
    if len(payloads) != 1:
        raise ValueError("producer must declare one report payload")
    initial = _closed_dict(payloads[0], bindings)
    emitted_keys = set(initial)
    if initial.get("schema") != REPORT_SCHEMA_VERSION:
        raise ValueError("producer report schema version drift")

    for call in (node for node in ast.walk(writer) if isinstance(node, ast.Call)):
        if not (isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == "payload"
                and call.func.attr == "update"):
            continue
        if len(call.args) != 1 or call.keywords:
            raise ValueError("producer report payload has a dynamic update")
        emitted_keys.update(_closed_dict(call.args[0], bindings))
    if emitted_keys != shape("report"):
        raise ValueError("producer report-envelope keys drift from schema-4 authority")

    promotion_function = next((node for node in tree.body
                               if isinstance(node, ast.FunctionDef)
                               and node.name == "_promotion_record"), None)
    if promotion_function is None:
        raise ValueError("producer lacks _promotion_record")
    promotion_records = [
        _closed_dict(node.value, bindings)
        for node in ast.walk(promotion_function)
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
    ]
    if not promotion_records:
        raise ValueError("producer has no closed promotion record")
    if any(set(record) != shape("promotion") for record in promotion_records):
        raise ValueError("producer promotion keys drift from schema-4 authority")
    if dict(PROMOTABLE_TOP100_PROMOTION) not in promotion_records:
        raise ValueError("producer lacks the canonical promotable classification")
