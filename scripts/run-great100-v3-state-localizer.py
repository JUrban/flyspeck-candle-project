#!/usr/bin/env python3
"""Run exact, explicitly nonpromotable candidate-V3 Great-100 closure.

The controller authenticates each retained V2 reference transcript against the
existing independent approval, transforms its structural wire through the
separately tested V2-to-V3 canonicalizer, and compares Candle's candidate-V3
theorem and complete post-state records with collision-resistant SHA-256 plus
exact byte lengths.  Transformed data does not inherit V2 approval, so this
tool can close diagnostic G100-S only; it can never emit S1 evidence.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import canonicalize_fingerprint_v2_to_v3 as canonical


SCRIPT_DIR = Path(__file__).resolve().parent
COMPATIBILITY_LOCALIZER = SCRIPT_DIR / "run-great100-compatibility-localizer.py"
V3_HELPER_RELATIVE = Path("candle/fingerprint_v3.ml")
V3_STREAM_HELPER_RELATIVE = Path("candle/fingerprint_v3_state_stream.ml")
V2_HELPER_RELATIVE = Path("candle/fingerprint.ml")
STREAM_BEGIN = b"CANDLE_STATE_FINGERPRINT_V3_STREAM_BEGIN"
STREAM_COMPONENT_BEGIN = b"CANDLE_STATE_FINGERPRINT_V3_STREAM_COMPONENT_BEGIN"
STREAM_CHUNK = b"CANDLE_STATE_FINGERPRINT_V3_STREAM_CHUNK"
STREAM_COMPONENT_END = b"CANDLE_STATE_FINGERPRINT_V3_STREAM_COMPONENT_END"
STREAM_END = b"CANDLE_STATE_FINGERPRINT_V3_STREAM_END"
STREAM_COMPONENTS = (
    "type_constants", "term_constants", "definitions", "global_axioms")
ALPHA_ONLY_TARGETS = frozenset({
    "100/birthday",
    "100/derangements",
    "100/fourier",
    "100/pascal",
})


@dataclass(frozen=True)
class V3Reference:
    name: str
    theorem_names: tuple[str, ...]
    approved_v2: dict
    identity: dict
    transcript: dict
    success: dict


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _identity(value: bytes) -> dict:
    return {"sha256": hashlib.sha256(value).hexdigest(), "bytes": len(value)}


def _capture_identity(capture: canonical.Capture) -> dict:
    canonical.validate_capture_structure(capture)
    theorem_records = []
    for record in capture.theorems:
        try:
            name = record.name.decode("ascii")
        except UnicodeDecodeError as error:
            raise canonical.WireError("non-ASCII theorem name") from error
        theorem_records.append({
            "name": name,
            "theorem": _identity(record.theorem),
            "hypotheses": _identity(record.hypotheses),
            "conclusion": _identity(record.conclusion),
            "global_axioms": _identity(record.global_axioms),
            "hypothesis_count": record.hypothesis_count,
            "global_axiom_count": record.global_axiom_count,
        })
    state = capture.state
    return {
        "theorems": theorem_records,
        "post_state": {
            "kernel_state": _identity(state.kernel_state),
            "type_constants": _identity(state.type_constants),
            "term_constants": _identity(state.term_constants),
            "definitions": _identity(state.definitions),
            "global_axioms": _identity(state.global_axioms),
            "type_constant_count": state.type_constant_count,
            "term_constant_count": state.term_constant_count,
            "definition_count": state.definition_count,
            "global_axiom_count": state.global_axiom_count,
        },
    }


def _derive_v3_references(compatibility, candle_root, tests, canonical_indices):
    authenticated = compatibility._derive_references(
        candle_root, tests, canonical_indices)
    references = {}
    for test in tests:
        key = tuple(test.fingerprint_theorems)
        reference = authenticated[key]
        capture = canonical.read_v2_capture(
            Path(reference.transcript["path"]), test.fingerprint_theorems)
        transformed = canonical.canonicalize_capture(capture)
        identity = _capture_identity(transformed)
        if [record["name"] for record in identity["theorems"]] != \
                list(test.fingerprint_theorems):
            raise ValueError(f"V3 theorem inventory changed for {test.name}")
        if any(
                record["hypothesis_count"] != 0 or
                record["global_axiom_count"] != 3
                for record in identity["theorems"]):
            raise ValueError(f"V3 theorem closure changed for {test.name}")
        if identity["post_state"]["global_axiom_count"] != 3:
            raise ValueError(f"V3 state axiom count changed for {test.name}")
        references[key] = V3Reference(
            name=test.name,
            theorem_names=key,
            approved_v2=reference.approved,
            identity=identity,
            transcript=reference.transcript,
            success=reference.success,
        )
    if len(references) != len(tests):
        raise ValueError("Great-100 theorem tuples are not unique")
    return references


def _request_source_factory(regression, stream_source):
    def request(theorem_names, suite_nonce=None, process_nonce=None):
        if suite_nonce is not None or process_nonce is not None:
            raise ValueError("V3 state localizer cannot emit suite evidence")
        lines = [stream_source]
        for name in theorem_names:
            if regression.OCAML_VALUE_PATH_RE.fullmatch(name) is None:
                raise ValueError(f"unsafe theorem value path: {name!r}")
            lines.append(f'candle_s1_emit_fingerprint "{name}" {name};;')
        lines.append("candle_s1_emit_state_fingerprint_v3_stream ();;")
        return "\n".join(lines) + "\n"
    return request


def _nonnegative(field: bytes, label: str) -> int:
    if canonical.DECIMAL_RE.fullmatch(field) is None:
        raise canonical.WireError(f"noncanonical decimal in {label}")
    return int(field)


class _StateStreamReader:
    def __init__(self):
        self.started = False
        self.ended = False
        self.lengths = None
        self.counts = None
        self.component_index = 0
        self.active = None
        self.component_identities = {}
        self.kernel_digest = hashlib.sha256()
        self.kernel_bytes = 0

    def begin(self, fields):
        if self.started or len(fields) != 10:
            raise canonical.WireError("malformed or duplicate V3 stream begin")
        values = [
            _nonnegative(field, f"V3 stream begin field {index}")
            for index, field in enumerate(fields[1:], 1)
        ]
        kernel_length, *rest = values
        self.lengths = dict(zip(STREAM_COMPONENTS, rest[:4]))
        self.counts = dict(zip((
            "type_constant_count", "term_constant_count",
            "definition_count", "global_axiom_count"), rest[4:]))
        header = (
            canonical.encode_field(b"kernel-state") +
            canonical.encode_field(b"4"))
        self.kernel_digest.update(header)
        self.kernel_bytes = len(header)
        self.kernel_length = kernel_length
        self.started = True

    def component_begin(self, fields):
        if (not self.started or self.ended or self.active is not None or
                len(fields) != 3 or
                self.component_index >= len(STREAM_COMPONENTS)):
            raise canonical.WireError("malformed V3 component begin")
        try:
            name = fields[1].decode("ascii")
        except UnicodeDecodeError as error:
            raise canonical.WireError("non-ASCII V3 component name") from error
        expected_name = STREAM_COMPONENTS[self.component_index]
        if name != expected_name:
            raise canonical.WireError(
                f"out-of-order V3 component: {name!r}, expected {expected_name!r}")
        length = _nonnegative(fields[2], f"{name} length")
        if length != self.lengths[name]:
            raise canonical.WireError(f"V3 {name} begin length mismatch")
        prefix = str(length).encode("ascii") + b":"
        self.kernel_digest.update(prefix)
        self.kernel_bytes += len(prefix)
        self.active = {
            "name": name,
            "length": length,
            "received": 0,
            "chunks": 0,
            "digest": hashlib.sha256(),
        }

    def chunk(self, fields):
        if self.active is None or len(fields) != 4:
            raise canonical.WireError("V3 chunk outside a component")
        try:
            name = fields[1].decode("ascii")
        except UnicodeDecodeError as error:
            raise canonical.WireError("non-ASCII V3 chunk component") from error
        if name != self.active["name"]:
            raise canonical.WireError("V3 chunk component mismatch")
        sequence = _nonnegative(fields[2], f"{name} chunk sequence")
        if sequence != self.active["chunks"]:
            raise canonical.WireError(f"V3 {name} chunk sequence mismatch")
        if (canonical.LOWER_HEX_RE.fullmatch(fields[3]) is None or
                not fields[3]):
            raise canonical.WireError(f"malformed or empty V3 {name} chunk")
        raw = bytes.fromhex(fields[3].decode("ascii"))
        self.active["received"] += len(raw)
        if self.active["received"] > self.active["length"]:
            raise canonical.WireError(f"V3 {name} exceeds declared length")
        self.active["chunks"] += 1
        self.active["digest"].update(raw)
        self.kernel_digest.update(raw)
        self.kernel_bytes += len(raw)

    def component_end(self, fields):
        if self.active is None or len(fields) != 4:
            raise canonical.WireError("V3 component end without begin")
        try:
            name = fields[1].decode("ascii")
        except UnicodeDecodeError as error:
            raise canonical.WireError("non-ASCII V3 component end") from error
        length = _nonnegative(fields[2], f"{name} end length")
        chunks = _nonnegative(fields[3], f"{name} end chunk count")
        if (name != self.active["name"] or length != self.active["length"] or
                length != self.active["received"] or
                chunks != self.active["chunks"]):
            raise canonical.WireError(f"V3 {name} component end mismatch")
        self.component_identities[name] = {
            "sha256": self.active["digest"].hexdigest(),
            "bytes": length,
        }
        self.active = None
        self.component_index += 1

    def end(self, fields):
        if (len(fields) != 1 or not self.started or self.ended or
                self.active is not None or
                self.component_index != len(STREAM_COMPONENTS)):
            raise canonical.WireError("malformed V3 stream end")
        self.ended = True

    def finish(self):
        if not self.started or not self.ended:
            raise canonical.WireError("incomplete V3 state stream")
        if self.kernel_bytes != self.kernel_length:
            raise canonical.WireError("V3 reconstructed kernel length mismatch")
        return {
            "kernel_state": {
                "sha256": self.kernel_digest.hexdigest(),
                "bytes": self.kernel_bytes,
            },
            **self.component_identities,
            **self.counts,
        }


def _read_v3_identity(log_path: Path, theorem_names) -> dict:
    expected = [name.encode("ascii") for name in theorem_names]
    theorems = []
    stream = _StateStreamReader()
    with Path(log_path).open("rb") as source:
        for number, line in enumerate(source, 1):
            stripped = line.rstrip(b"\r\n")
            if stripped.startswith(canonical.V3_THEOREM_MARKER + b"\t"):
                theorems.append(canonical.theorem_record_from_fields(
                    stripped.split(b"\t"), f"line {number}"))
            elif stripped.startswith(STREAM_BEGIN + b"\t"):
                stream.begin(stripped.split(b"\t"))
            elif stripped.startswith(STREAM_COMPONENT_BEGIN + b"\t"):
                stream.component_begin(stripped.split(b"\t"))
            elif stripped.startswith(STREAM_CHUNK + b"\t"):
                stream.chunk(stripped.split(b"\t"))
            elif stripped.startswith(STREAM_COMPONENT_END + b"\t"):
                stream.component_end(stripped.split(b"\t"))
            elif stripped == STREAM_END:
                stream.end([stripped])
            elif stripped.startswith(canonical.V3_STATE_MARKER + b"\t"):
                raise canonical.WireError(
                    "unexpected aggregate V3 state record in stream mode")
    observed = [record.name for record in theorems]
    if observed != expected:
        raise canonical.WireError(
            f"V3 theorem request mismatch: expected={expected!r}, "
            f"observed={observed!r}")
    theorem_identities = []
    for index, record in enumerate(theorems):
        theorem = canonical.parse_node(record.theorem, f"theorem record {index}")
        if (theorem.tag != b"theorem" or len(theorem.fields) != 2 or
                theorem.fields != (record.hypotheses, record.conclusion)):
            raise canonical.WireError(
                f"theorem record {index} disagrees with redundant fields")
        hypotheses = canonical.parse_node(
            record.hypotheses, f"theorem record {index} hypotheses")
        if (hypotheses.tag != b"list" or
                len(hypotheses.fields) != record.hypothesis_count):
            raise canonical.WireError(
                f"theorem record {index} hypothesis count mismatch")
        theorem_identities.append({
            "name": record.name.decode("ascii"),
            "theorem": _identity(record.theorem),
            "hypotheses": _identity(record.hypotheses),
            "conclusion": _identity(record.conclusion),
            "global_axioms": _identity(record.global_axioms),
            "hypothesis_count": record.hypothesis_count,
            "global_axiom_count": record.global_axiom_count,
        })
    state_identity = stream.finish()
    for index, record in enumerate(theorem_identities):
        if (record["global_axioms"] != state_identity["global_axioms"] or
                record["global_axiom_count"] !=
                state_identity["global_axiom_count"]):
            raise canonical.WireError(
                f"theorem record {index} global axioms disagree with state")
    return {"theorems": theorem_identities, "post_state": state_identity}


def _identity_mismatches(observed: dict, expected: dict) -> list[str]:
    mismatches = []
    observed_theorems = observed["theorems"]
    expected_theorems = expected["theorems"]
    if len(observed_theorems) != len(expected_theorems):
        mismatches.append("theorem inventory")
    for left, right in zip(observed_theorems, expected_theorems):
        name = right["name"]
        for key in right:
            if left.get(key) != right[key]:
                mismatches.append(f"{name}.{key}")
    for key, value in expected["post_state"].items():
        if observed["post_state"].get(key) != value:
            mismatches.append(f"post_state.{key}")
    return mismatches


def _reader_factory(references, failure_type, serializer_record):
    def read(log_path, theorem_names, mapping_status,
             expected_identities=None):
        if mapping_status != "audited":
            raise failure_type("V3 state localizer requires audited mapping")
        key = tuple(theorem_names)
        reference = references.get(key)
        if reference is None:
            raise failure_type("no transformed V3 reference for theorem tuple")
        if expected_identities != reference.approved_v2:
            raise failure_type("runtime target lost its approved V2 identity")
        try:
            observed = _read_v3_identity(Path(log_path), theorem_names)
        except (OSError, UnicodeError, canonical.WireError) as error:
            raise failure_type(str(error)) from error
        mismatches = _identity_mismatches(observed, reference.identity)
        if mismatches:
            raise failure_type(
                "candidate-V3 exact identity mismatch: " +
                ", ".join(mismatches))
        return {
            "status": "exact_theorem_and_state_matched",
            "comparison": "canonical-v3-structural-wire-sha256-and-length-v1",
            "promotion_eligible": False,
            "s1_evidence": False,
            "serializer": serializer_record,
            **observed,
            "reference": {
                "derivation": (
                    "authenticated approved V2 transcript transformed by "
                    "the diagnostic V2-to-V3 canonicalizer"),
                "identity": reference.identity,
                "v2_transcript": reference.transcript,
                "v2_success": reference.success,
            },
        }
    return read


def _v3_normalizations(compatibility):
    selected = []
    removed = []
    for specification in compatibility.TOP100_NORMALIZATIONS:
        targets = set(specification.targets)
        if targets and targets.issubset(ALPHA_ONLY_TARGETS):
            removed.append(specification)
        else:
            selected.append(specification)
    if {target for spec in removed for target in spec.targets} != \
            set(ALPHA_ONLY_TARGETS):
        raise RuntimeError("unexpected V2 generated-name normalization set")
    return tuple(selected), tuple(removed)


def _result_record(compatibility, regression, result, test):
    fingerprints = result.fingerprints
    return {
        "name": result.name,
        "files": list(test.files),
        "status": result.status.value,
        "exact_state_status": (
            fingerprints["status"]
            if result.status is regression.TestStatus.PASS and
            fingerprints is not None else "failed"),
        "timeout_kind": result.timeout_kind,
        "boot_elapsed_seconds": result.boot_elapsed,
        "hol_elapsed_seconds": result.hol_elapsed,
        "test_elapsed_seconds": result.test_elapsed,
        "fingerprint_elapsed_seconds": result.fingerprint_elapsed,
        "total_elapsed_seconds": result.total,
        "peak_process_rss_kib": result.peak_process_rss_kib,
        "peak_tree_rss_kib": result.peak_tree_rss_kib,
        "error_message": result.error_message,
        "transcript": compatibility._file_record(result.log_path),
        "v3_fingerprints": fingerprints,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run nonpromotable exact candidate-V3 Great-100 closure")
    parser.add_argument("--candle-root", required=True, type=Path)
    parser.add_argument("--json-report", required=True, type=Path)
    parser.add_argument("--log-dir", required=True, type=Path)
    parser.add_argument("--target", action="append", default=[])
    parser.add_argument("-j", "--jobs", type=int, default=7)
    parser.add_argument("--inactivity-timeout", type=float, default=1800)
    parser.add_argument("--wall-timeout", type=float, default=5400)
    parser.add_argument("--heap-mb", type=int, default=10240)
    parser.add_argument(
        "--csdp-binary", type=Path,
        default=Path("/project/deps/hol-light-external-tools-v9/usr/bin/csdp"))
    args = parser.parse_args(argv)

    if not 1 <= args.jobs <= 10:
        parser.error("--jobs must be between 1 and 10")
    if args.inactivity_timeout <= 0 or args.wall_timeout <= 0:
        parser.error("timeouts must be positive")
    if args.heap_mb <= 0:
        parser.error("--heap-mb must be positive")

    compatibility = _load_module(
        COMPATIBILITY_LOCALIZER, "_great100_v3_compatibility_support")
    candle_root = args.candle_root.resolve(strict=True)
    report, log_dir = compatibility._prepare_destinations(
        args.json_report, args.log_dir)
    regression = compatibility._load_regression(candle_root)
    head, status = regression._git_state()
    if status:
        raise SystemExit(
            "V3 state localizer requires a clean Candle Git tree: " +
            repr(status))

    available = {test.name: test for test in regression.TOP100}
    if args.target:
        unknown = [name for name in args.target if name not in available]
        if unknown:
            parser.error(f"unknown canonical target(s): {unknown}")
        if len(set(args.target)) != len(args.target):
            parser.error("duplicate --target")
        tests = [available[name] for name in args.target]
    else:
        tests = list(regression.TOP100)

    canonical_indices = {
        test.name: index for index, test in enumerate(regression.TOP100, 1)
    }
    print("NONPROMOTABLE CANDIDATE-V3 EXACT-STATE LOCALIZER — NEVER S1")
    print(f"Candle: {head}")
    print("Authenticating approved V2 transcripts and deriving V3 expectations...")
    references = _derive_v3_references(
        compatibility, candle_root, tests, canonical_indices)

    v3_helper = candle_root / V3_HELPER_RELATIVE
    v2_helper = candle_root / V2_HELPER_RELATIVE
    serializer_record = compatibility._file_record(v3_helper)
    if serializer_record["path"] != str(v3_helper.resolve()):
        raise SystemExit("V3 serializer path did not resolve exactly")
    approved_serializers = {
        test.fingerprint_expected_identities["serializer_sha256"]
        for test in tests
    }
    if len(approved_serializers) != 1:
        raise SystemExit("selected targets do not share one V2 serializer")
    approved_serializer = next(iter(approved_serializers))
    if serializer_record["sha256"] == approved_serializer:
        raise SystemExit("candidate V3 unexpectedly has approved V2 identity")

    specifications, removed_alpha = _v3_normalizations(compatibility)
    selected_target_names = {test.name for test in tests}
    normalization_setup, normalization_contract = \
        compatibility._materialize_normalizations(
            candle_root, log_dir, tests, specifications=specifications)
    normalization_contract["omitted_v2_identity_only_targets"] = sorted(
        target for spec in removed_alpha for target in spec.targets
        if target in selected_target_names)
    csdp_targets, csdp_binary, csdp_contract = \
        compatibility._prepare_csdp_bridge(
            log_dir, tests, args.csdp_binary)

    original_helper = regression.FINGERPRINT_HELPER
    original_request = regression._fingerprint_request_source
    original_reader = regression._read_fingerprint_records
    original_finish = regression.CandleREPL.finish
    original_load = regression.CandleREPL.load
    original_check_output = regression.CandleREPL._check_output
    stream_helper = candle_root / V3_STREAM_HELPER_RELATIVE
    try:
        stream_bytes, stream_record = compatibility._stable_source_bytes(
            stream_helper)
        stream_source = stream_bytes.decode("ascii")
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise SystemExit(f"cannot load stable V3 stream helper: {error}") from error
    regression.FINGERPRINT_HELPER = v3_helper
    regression._fingerprint_request_source = _request_source_factory(
        regression, stream_source)
    regression._read_fingerprint_records = _reader_factory(
        references, regression.LoadFailure, serializer_record)
    regression.CandleREPL.finish = (
        lambda repl: compatibility._finish_candle_at_eof(regression, repl))
    if normalization_setup is not None:
        csdp_handler = (
            compatibility._csdp_progress_handler(
                csdp_binary, csdp_contract["requests"], regression.LoadFailure)
            if csdp_binary is not None else None)
        regression.CandleREPL.load = \
            compatibility._load_after_normalization_setup(
                original_load, normalization_setup, csdp_targets, csdp_handler)
        normalization_mappings = {
            source["normalized"]["path"]: source["runtime_original"]
            for source in normalization_contract["sources"]
        }
        regression.CandleREPL._check_output = \
            compatibility._check_output_with_normalizations(
                original_check_output, normalization_mappings)

    requested_jobs = args.jobs
    jobs = regression.cap_jobs_for_heap(requested_jobs, args.heap_mb)
    environment = {**os.environ, "CML_HEAP_SIZE": str(args.heap_mb)}
    started_utc = datetime.now(timezone.utc).isoformat()
    try:
        results, wall = regression.run_suite(
            tests, jobs, args.inactivity_timeout,
            wall_timeout=args.wall_timeout, env=environment, log_dir=log_dir)
    finally:
        regression.FINGERPRINT_HELPER = original_helper
        regression._fingerprint_request_source = original_request
        regression._read_fingerprint_records = original_reader
        regression.CandleREPL.finish = original_finish
        regression.CandleREPL.load = original_load
        regression.CandleREPL._check_output = original_check_output

    end_head, end_status = regression._git_state()
    if (end_head, end_status) != (head, status):
        raise SystemExit("Candle Git state changed during V3 state run")
    tests_by_name = {test.name: test for test in tests}
    rows = [
        _result_record(
            compatibility, regression, result, tests_by_name[result.name])
        for result in results
    ]
    exact = sum(
        row["exact_state_status"] == "exact_theorem_and_state_matched"
        for row in rows)
    timeouts = sum(row["status"] == "TIMEOUT" for row in rows)
    failures = len(rows) - exact
    transformer_record = compatibility._file_record(
        SCRIPT_DIR / "canonicalize_fingerprint_v2_to_v3.py")
    payload = {
        "format": "candle-great100-v3-state-localizer-v1",
        "warning": (
            "DIAGNOSTIC ONLY: candidate V3 expectations are transformed from "
            "authenticated V2 evidence but have no independent V3 approval; "
            "never schema-6, schema-7, S1, or promotable evidence."),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "started_utc": started_utc,
        "promotion": {
            "eligible": False,
            "s1_evidence": False,
            "schema6_evidence": False,
            "schema7_evidence": False,
            "reason": "unapproved-candidate-v3-exact-state-localizer",
        },
        "scope": {
            "canonical_inventory_target_count": len(regression.TOP100),
            "requested_target_count": len(tests),
            "requested_targets": [test.name for test in tests],
            "complete_canonical_inventory": len(tests) == 65,
        },
        "summary": {
            "reported_target_count": len(rows),
            "exact_theorem_and_state_match_count": exact,
            "failure_count": failures,
            "timeout_count": timeouts,
            "diagnostic_g100_s_65_of_65": (
                len(tests) == 65 and len(rows) == 65 and exact == 65),
        },
        "comparison_contract": {
            "algorithm": (
                "SHA-256 plus exact byte length over candidate canonical-V3 "
                "structural theorem and complete kernel-state wire"),
            "reference_derivation": (
                "each retained V2 transcript is first checked byte-for-byte "
                "against its independently approved SHA-256 identities, then "
                "transformed structurally to candidate V3"),
            "approval_inheritance": False,
            "differential_validation": [
                "native/Candle common-base V3 records byte-identical",
                "approved V2 common base transforms to the native V3 record",
                "approved V2 arithmetic-geometric-mean transcript transforms "
                "to the fresh native V3 records",
                "fresh native and Candle V3 arithmetic-geometric-mean theorem "
                "and complete-state records byte-identical",
            ],
            "streaming_decision": (
                "implemented: the exact aggregate V3 wire is reconstructed "
                "incrementally from ordered 8192-byte component chunks, "
                "avoiding multi-megabyte aggregate strings and lines"),
            "source_normalizations": normalization_contract,
            "diagnostic_csdp_bridge": csdp_contract,
        },
        "execution": {
            "candle_root": str(candle_root),
            "candle_git_head": head,
            "candle_git_status": status,
            "jobs_requested": requested_jobs,
            "jobs_used": jobs,
            "heap_mb_per_process": args.heap_mb,
            "timeout_policy": regression._timeout_policy(
                args.inactivity_timeout, args.wall_timeout),
            "wall_seconds": wall,
            "script": compatibility._file_record(Path(__file__).resolve()),
            "transformer": transformer_record,
            "candidate_v3_serializer": serializer_record,
            "candidate_v3_state_stream": stream_record,
            "retained_v2_serializer": compatibility._file_record(v2_helper),
            "approved_v2_serializer_sha256": approved_serializer,
            "linked_record": compatibility._file_record(
                regression.LINKED_RECORD_PATH),
        },
        "reference_inputs": [
            {
                "target": reference.name,
                "v2_transcript": reference.transcript,
                "v2_success": reference.success,
                "derived_v3_identity_sha256": compatibility._canonical_sha256(
                    reference.identity),
            }
            for reference in references.values()
        ],
        "results": rows,
    }
    with report.open("x", encoding="utf-8") as output:
        json.dump(payload, output, indent=2)
        output.write("\n")
    print(f"Exact theorem plus state: {exact}/{len(tests)}")
    print(f"Machine-readable nonpromotable report: {report}")
    return 0 if failures == 0 and len(rows) == len(tests) else 1


if __name__ == "__main__":
    raise SystemExit(main())
