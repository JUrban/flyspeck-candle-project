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
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from types import MappingProxyType


REPORT_SCHEMA_VERSION = 4

DERIVATION_SCHEMA = 1
DERIVATION_KIND = "candle-great100-qualified-report-shapes-v1"
DISCRIMINANT_FIELDS = frozenset({
    "schema", "suite", "status", "timeout_kind", "mapping_status",
    "marker_contract", "eligible", "s1_evidence", "linked_schema",
    "required_linked_schema",
    "reason", "expected_identities_present", "load_pass_is_fingerprint_match",
    "expected_mismatch_result", "expected_identity_source", "serializer",
    "suite_closed", "root_observed", "sampler_completed",
    "progress_extends_total_wall_deadline", "inactivity_resets_on",
    "inactivity_scope", "total_wall_scope",
})

# These names are the finalizer API.  Their key sets are derived from the
# listed qualified-report paths; no key is repeated here by hand.
NAMED_SHAPE_PATHS = MappingProxyType({
    "report": ("/",),
    "result": ("/results/[]",),
    "process_evidence": ("/results/[]/process_evidence",),
    "run_evidence": ("/run_evidence",),
    "fingerprints": ("/results/[]/fingerprints",),
    "theorem": ("/results/[]/fingerprints/theorems/[]",),
    "post_state": ("/results/[]/fingerprints/post_state",),
    "runtime_state": (
        "/results/[]/process_evidence/pre_runtime_state",
        "/results/[]/process_evidence/post_runtime_state",
    ),
    "resource_sampling": ("/results/[]/process_evidence/resource_sampling",),
    "markers": ("/results/[]/process_evidence/markers",),
    "s1_evidence": ("/s1_evidence",),
    "timeout_policy": ("/timeout_policy",),
    "promotion": ("/promotion",),
    "file_record": (
        "/execution_contract/candle.sh",
        "/execution_contract/candle~1cakeml_artifact_provenance.py",
        "/execution_contract/candle~1fingerprint.ml",
        "/execution_contract/candle~1fingerprint_v3_state_stream.ml",
        "/execution_contract/candle~1reference_protocol.py",
        "/execution_contract/candle~1regression.py",
        "/execution_contract/candle~1runtime_fingerprint_protocol.py",
        "/execution_contract/candle~1top100_manifest.json",
    ),
    "file_reference": (
        "/candle_executable",
        "/independent_approval",
        "/linked_record",
        "/results/[]/process_evidence/transcript",
        "/results/[]/process_evidence/pre_runtime_state/candle_executable",
        "/results/[]/process_evidence/post_runtime_state/candle_executable",
        "/source_closure/files/[]",
    ),
})


def _json_kind(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    raise TypeError(f"value is not JSON: {type(value).__name__}")


def _pointer_key(key: str) -> str:
    return key.replace("~", "~0").replace("/", "~1")


def _child_path(path: str, key: str) -> str:
    encoded = _pointer_key(key)
    return f"/{encoded}" if path == "/" else f"{path}/{encoded}"


def derive_authority(report_sources: list[tuple[str, bytes]]) -> dict[str, object]:
    """Mechanically derive every object/array shape and discriminant."""
    if len(report_sources) != 2:
        raise ValueError("schema-4 authority requires exactly two qualified reports")
    objects: dict[str, Counter[tuple[str, ...]]] = defaultdict(Counter)
    arrays: dict[str, Counter[int]] = defaultdict(Counter)
    array_items: dict[str, Counter[str]] = defaultdict(Counter)
    scalars: dict[str, Counter[str]] = defaultdict(Counter)
    discriminants: dict[str, Counter[tuple[str, str]]] = defaultdict(Counter)
    identities = []

    def walk(value: object, path: str, field: str | None = None) -> None:
        kind = _json_kind(value)
        if isinstance(value, dict):
            if not all(isinstance(key, str) for key in value):
                raise ValueError(f"non-string object key at {path}")
            objects[path][tuple(sorted(value))] += 1
            for key, child in value.items():
                walk(child, _child_path(path, key), key)
        elif isinstance(value, list):
            arrays[path][len(value)] += 1
            for child in value:
                array_items[path][_json_kind(child)] += 1
                walk(child, f"{path}/[]")
        else:
            scalars[path][kind] += 1
            if field in DISCRIMINANT_FIELDS:
                encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
                discriminants[path][(kind, encoded)] += 1

    for label, source in report_sources:
        try:
            report = json.loads(source)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"malformed qualified report: {label}") from error
        if not isinstance(report, dict):
            raise ValueError(f"qualified report is not an object: {label}")
        identities.append({
            "label": label,
            "bytes": len(source),
            "sha256": hashlib.sha256(source).hexdigest(),
        })
        walk(report, "/")

    object_rows = {
        path: {
            "occurrences": sum(variants.values()),
            "key_variants": [list(keys) for keys in sorted(variants)],
        }
        for path, variants in sorted(objects.items())
    }
    array_rows = {
        path: {
            "occurrences": sum(lengths.values()),
            "length_variants": sorted(lengths),
            "item_kinds": sorted(array_items[path]),
        }
        for path, lengths in sorted(arrays.items())
    }
    scalar_rows = {
        path: {
            "occurrences": sum(kinds.values()),
            "kind_variants": sorted(kinds),
        }
        for path, kinds in sorted(scalars.items())
    }
    discriminant_rows = {
        path: {
            "occurrences": sum(values.values()),
            "variants": [
                {"kind": kind, "value": json.loads(encoded)}
                for kind, encoded in sorted(values)
            ],
        }
        for path, values in sorted(discriminants.items())
    }
    for name, paths in NAMED_SHAPE_PATHS.items():
        variants = {
            tuple(keys)
            for path in paths
            for keys in object_rows.get(path, {}).get("key_variants", [])
        }
        if len(variants) != 1 or any(path not in object_rows for path in paths):
            raise ValueError(f"named shape is absent or variant: {name}")
    schema_variants = discriminant_rows.get("/schema", {}).get("variants")
    if schema_variants != [{"kind": "integer", "value": REPORT_SCHEMA_VERSION}]:
        raise ValueError("qualified reports do not have exact integer schema 4")
    return {
        "schema": DERIVATION_SCHEMA,
        "kind": DERIVATION_KIND,
        "report_schema": REPORT_SCHEMA_VERSION,
        "derived_from": identities,
        "named_shape_paths": {
            name: list(paths) for name, paths in NAMED_SHAPE_PATHS.items()
        },
        "objects": object_rows,
        "arrays": array_rows,
        "scalars": scalar_rows,
        "discriminants": discriminant_rows,
    }

AUTHORITY_DEFINITION_NAME = "great100_report_schema_v4.json"
_AUTHORITY_PATH = Path(__file__).resolve().with_name(AUTHORITY_DEFINITION_NAME)
if (not _AUTHORITY_PATH.exists()
        and __name__ == "_great100_report_schema_derivation"):
    # The generator can bootstrap a deliberately absent derived definition.
    AUTHORITY = None
else:
    try:
        AUTHORITY = json.loads(_AUTHORITY_PATH.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("cannot load Great100 report schema definition") from error
if AUTHORITY is not None and not (isinstance(AUTHORITY, dict)
        and type(AUTHORITY.get("schema")) is int
        and AUTHORITY["schema"] == DERIVATION_SCHEMA
        and AUTHORITY.get("kind") == DERIVATION_KIND
        and type(AUTHORITY.get("report_schema")) is int
        and AUTHORITY["report_schema"] == REPORT_SCHEMA_VERSION
        and AUTHORITY.get("named_shape_paths") == {
            name: list(paths) for name, paths in NAMED_SHAPE_PATHS.items()
        }
        and isinstance(AUTHORITY.get("objects"), dict)
        and isinstance(AUTHORITY.get("arrays"), dict)
        and isinstance(AUTHORITY.get("scalars"), dict)
        and isinstance(AUTHORITY.get("discriminants"), dict)):
    raise RuntimeError("malformed Great100 report schema definition")


def shape(name: str) -> frozenset[str]:
    """Return one mechanically derived closed schema-4 object-key set."""
    if AUTHORITY is None:
        raise RuntimeError("Great100 report schema definition is not loaded")
    variants = {
        tuple(keys)
        for path in AUTHORITY["named_shape_paths"][name]
        for keys in AUTHORITY["objects"][path]["key_variants"]
    }
    if len(variants) != 1:
        raise RuntimeError(f"Great100 named schema shape is variant: {name}")
    return frozenset(next(iter(variants)))


REPORT_SCHEMA_SHAPES = MappingProxyType(
    {name: shape(name) for name in NAMED_SHAPE_PATHS}
    if AUTHORITY is not None else {}
)


def _single_discriminant(path: str) -> object:
    variants = AUTHORITY["discriminants"][path]["variants"]
    if len(variants) != 1:
        raise RuntimeError(f"Great100 discriminant is variant: {path}")
    return variants[0]["value"]


PROMOTABLE_TOP100_PROMOTION = MappingProxyType(
    {
        key: _single_discriminant(f"/promotion/{_pointer_key(key)}")
        for key in shape("promotion")
    } if AUTHORITY is not None else {}
)


def validate_report_shape(report: object) -> None:
    """Apply every derived object/array shape and exact discriminant."""
    def walk(value: object, path: str) -> None:
        kind = _json_kind(value)
        if isinstance(value, dict):
            row = AUTHORITY["objects"].get(path)
            keys = sorted(value)
            if row is None or keys not in row["key_variants"]:
                raise ValueError(f"Great100 object shape mismatch at {path}")
            for key, child in value.items():
                walk(child, _child_path(path, key))
            return
        if isinstance(value, list):
            row = AUTHORITY["arrays"].get(path)
            if row is None or len(value) not in row["length_variants"]:
                raise ValueError(f"Great100 array shape mismatch at {path}")
            for child in value:
                if _json_kind(child) not in row["item_kinds"]:
                    raise ValueError(f"Great100 array item mismatch at {path}")
                walk(child, f"{path}/[]")
            return
        scalar_row = AUTHORITY["scalars"].get(path)
        if scalar_row is None or kind not in scalar_row["kind_variants"]:
            raise ValueError(f"Great100 scalar kind mismatch at {path}")
        discriminant_row = AUTHORITY["discriminants"].get(path)
        if discriminant_row is not None and not any(
                variant["kind"] == kind and variant["value"] == value
                for variant in discriminant_row["variants"]):
            raise ValueError(f"Great100 discriminant mismatch at {path}")

    walk(report, "/")


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
