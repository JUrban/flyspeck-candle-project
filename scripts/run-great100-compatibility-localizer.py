#!/usr/bin/env python3
"""Run a compact, explicitly nonpromotable Great-100 compatibility census.

This tool exists for one narrow transition case: Candle can execute a
wire-equivalent structural serializer, but that serializer does not have the
identity pinned by the independently approved S1 reference artifact.  It must
not be used to produce, replace, or amend S1 evidence.

The localizer derives MD5-plus-length comparison values from the retained
sweep-2 reference transcripts after checking their SHA-256 identities against
the approved Top100 manifest.  Candle then hashes the same structural strings
inside the verified runtime, avoiding multi-megabyte hexadecimal output.  MD5
is used only to localize functional mismatches; every report is explicitly
ineligible for promotion and S1.
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
import re
import sys
import time


FINGERPRINT_MARKER = b"CANDLE_FINGERPRINT_V2"
STATE_MARKER = b"CANDLE_STATE_FINGERPRINT_V2"
COMPACT_FINGERPRINT_MARKER = b"CANDLE_COMPATIBILITY_FINGERPRINT_MD5_V1"
COMPACT_STATE_MARKER = b"CANDLE_COMPATIBILITY_STATE_MD5_V1"
REFERENCE_RELATIVE = Path(
    "candle/evidence/"
    "s1-reference-v9-csdp-two-sweep-652a18a-95bb84f/sweep-2"
)
LOWER_HEX_RE = re.compile(rb"(?:[0-9a-f]{2})*")
MD5_RE = re.compile(rb"[0-9a-f]{32}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class ReferenceTarget:
    name: str
    theorem_names: tuple[str, ...]
    approved: dict
    compact_theorems: tuple[dict, ...]
    compact_state: dict
    transcript: dict
    success: dict


@dataclass(frozen=True)
class SourceNormalization:
    """Exact, diagnostic-only source rewrite for one or more targets."""

    targets: tuple[str, ...]
    source: str
    expected_sha256: str
    replacements: tuple[tuple[bytes, bytes], ...]
    rationale: str


TOP100_NORMALIZATIONS = (
    SourceNormalization(
        targets=("100/birthday",),
        source="100/birthday.ml",
        expected_sha256=(
            "f2298f7d1b411d0b6341eedc6bcff6348e2537cec39bb00b7c61414c0602c591"
        ),
        replacements=((
            b'''  CONV_TAC NUM_REDUCE_CONV);;''',
            b'''  CONV_TAC NUM_REDUCE_CONV);;

(* Preserve the reference run's names for the two invented type variables. *)
let BIRTHDAY_THM_EXPLICIT =
  INST_TYPE
    [(mk_vartype "?143993",mk_vartype "?154493");
     (mk_vartype "?143989",mk_vartype "?154489")]
    BIRTHDAY_THM_EXPLICIT;;''',
        ),),
        rationale=(
            "alpha-rename two deterministic invented type variables to the "
            "names recorded by the approved reference theorem"
        ),
    ),
    SourceNormalization(
        targets=("100/derangements",),
        source="100/derangements.ml",
        expected_sha256=(
            "37c460acbc2863cdcd154bc3d4620080b3da23116c353d4bb77d89d99534a322"
        ),
        replacements=((
            b'''  ASM_SIMP_TAC[HAS_SIZE; DERANGEMENTS_EXP]);;''',
            b'''  ASM_SIMP_TAC[HAS_SIZE; DERANGEMENTS_EXP]);;

(* Preserve the reference run's name for the invented type variable. *)
let THE_DERANGEMENTS_FORMULA =
  INST_TYPE
    [(mk_vartype "?211488",mk_vartype "?221988")]
    THE_DERANGEMENTS_FORMULA;;''',
        ),),
        rationale=(
            "alpha-rename one deterministic invented type variable to the "
            "name recorded by the approved reference theorem"
        ),
    ),
    SourceNormalization(
        targets=("100/ramsey",),
        source="100/ramsey.ml",
        expected_sha256=(
            "c27a2197fd0faa1a8197523ec8b7e8182a122959c3ce3b76f0f0f70326ced94f"
        ),
        replacements=(
            (
                b'''let rec mk_primed_var(name,ty) =\n'''
                b'''  if can get_const_type name then mk_primed_var(name^"'",ty)\n'''
                b'''  else mk_var(name,ty);;''',
                b'''let rec mk_primed_var(name,ty) =\n'''
                b'''  if can get_const_type name then\n'''
                b'''    let next_name = name ^ "'" in\n'''
                b'''    mk_primed_var(next_name,ty)\n'''
                b'''  else mk_var(name,ty);;''',
            ),
            (
                b'''  let check st l = (if l = [] then failwith st else l) in\n'''
                b'''  let IMP_RES_THEN ttac impth =''',
                b'''  let check_thm st l : thm list =\n'''
                b'''    (if l = [] then failwith st else l) in\n'''
                b'''  let check_tac st l : tactic list =\n'''
                b'''    (if l = [] then failwith st else l) in\n'''
                b'''  let IMP_RES_THEN ttac impth =''',
            ),
            (b'''        let res = check "IMP_RES_THEN: no resolvents " l in''',
             b'''        let res = check_thm "IMP_RES_THEN: no resolvents " l in'''),
            (b'''        let tacs = check "IMP_RES_THEN: no tactics" (mapfilter ttac res) in''',
             b'''        let tacs = check_tac "IMP_RES_THEN: no tactics" (mapfilter ttac res) in'''),
            (b'''      let imps = check "RES_THEN: no implication" ths in''',
             b'''      let imps = check_thm "RES_THEN: no implication" ths in'''),
            (b'''      let res = check "RES_THEN: no resolvents " l in''',
             b'''      let res = check_thm "RES_THEN: no resolvents " l in'''),
            (b'''      let tacs = check "RES_THEN: no tactics" (mapfilter ttac res) in''',
             b'''      let tacs = check_tac "RES_THEN: no tactics" (mapfilter ttac res) in'''),
        ),
        rationale=(
            "separate an infix expression from a tuple argument and split one "
            "locally polymorphic helper into its theorem and tactic instances"
        ),
    ),
    SourceNormalization(
        targets=("100/heron",),
        source="100/heron.ml",
        expected_sha256=(
            "de7cd4bd92e9d6fa19076ae2195d58fe6c68901307a15da05c366bc0b2b40763"
        ),
        replacements=((
            b'''    let stms = setify(find_terms is_sqrt w) in''',
            b'''    let stms = setify Term.(<) (find_terms is_sqrt w) in''',
        ),),
        rationale=(
            "supply the explicit term comparator required by the CakeML "
            "finite-set helper"
        ),
    ),
)


def _canonical_sha256(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")).hexdigest()


def _file_record(path, display=None):
    path = Path(path)
    before = path.stat(follow_symlinks=False)
    if path.is_symlink() or not path.is_file() or before.st_nlink != 1:
        raise ValueError(f"not an ordinary single-link file: {path}")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
            size += len(block)
    after = path.stat(follow_symlinks=False)
    if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
         before.st_ctime_ns) !=
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
             after.st_ctime_ns) or size != before.st_size):
        raise ValueError(f"file changed while hashing: {path}")
    return {
        "path": str(display if display is not None else path.resolve()),
        "bytes": size,
        "sha256": digest.hexdigest(),
    }


def _decode_hex(field, label):
    if LOWER_HEX_RE.fullmatch(field) is None:
        raise ValueError(f"malformed lowercase hex field: {label}")
    return bytes.fromhex(field.decode("ascii"))


def _compact_identity(serialized):
    return {
        "md5": hashlib.md5(serialized, usedforsecurity=False).hexdigest(),
        "bytes": len(serialized),
    }


def _sha256_identity(serialized):
    return hashlib.sha256(serialized).hexdigest()


def _reference_theorem(raw_fields):
    name_bytes = _decode_hex(raw_fields[1], "reference theorem name")
    try:
        name = name_bytes.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError("non-ASCII reference theorem name") from error
    serialized = [
        _decode_hex(field, label)
        for field, label in zip(raw_fields[2:6], (
            "reference theorem", "reference hypotheses",
            "reference conclusion", "reference global axioms"))
    ]
    try:
        hypothesis_count, axiom_count = map(int, raw_fields[6:8])
    except ValueError as error:
        raise ValueError("non-numeric reference theorem count") from error
    approved = {
        "name": name,
        "theorem_sha256": _sha256_identity(serialized[0]),
        "hypotheses_sha256": _sha256_identity(serialized[1]),
        "conclusion_sha256": _sha256_identity(serialized[2]),
        "global_axioms_sha256": _sha256_identity(serialized[3]),
        "hypothesis_count": hypothesis_count,
        "global_axiom_count": axiom_count,
    }
    compact = {
        "name": name,
        "theorem": _compact_identity(serialized[0]),
        "hypotheses": _compact_identity(serialized[1]),
        "conclusion": _compact_identity(serialized[2]),
        "global_axioms": _compact_identity(serialized[3]),
        "hypothesis_count": hypothesis_count,
        "global_axiom_count": axiom_count,
    }
    return approved, compact


def _reference_state(raw_fields):
    serialized = [
        _decode_hex(field, label)
        for field, label in zip(raw_fields[1:6], (
            "reference kernel state", "reference type constants",
            "reference term constants", "reference definitions",
            "reference state axioms"))
    ]
    try:
        counts = [int(field) for field in raw_fields[6:10]]
    except ValueError as error:
        raise ValueError("non-numeric reference state count") from error
    approved = {
        "kernel_state_sha256": _sha256_identity(serialized[0]),
        "type_constants_sha256": _sha256_identity(serialized[1]),
        "term_constants_sha256": _sha256_identity(serialized[2]),
        "definitions_sha256": _sha256_identity(serialized[3]),
        "global_axioms_sha256": _sha256_identity(serialized[4]),
        "type_constant_count": counts[0],
        "term_constant_count": counts[1],
        "definition_count": counts[2],
        "global_axiom_count": counts[3],
    }
    compact = {
        "kernel_state": _compact_identity(serialized[0]),
        "type_constants": _compact_identity(serialized[1]),
        "term_constants": _compact_identity(serialized[2]),
        "definitions": _compact_identity(serialized[3]),
        "global_axioms": _compact_identity(serialized[4]),
        "type_constant_count": counts[0],
        "term_constant_count": counts[1],
        "definition_count": counts[2],
        "global_axiom_count": counts[3],
    }
    return approved, compact


def _derive_reference_transcript(path, theorem_names, approved):
    """Validate one retained raw transcript and derive compact identities."""
    path = Path(path)
    digest = hashlib.sha256()
    size = 0
    theorem_records = {}
    state_records = []
    with path.open("rb") as transcript:
        for line in transcript:
            digest.update(line)
            size += len(line)
            stripped = line.rstrip(b"\r\n")
            if stripped.startswith(FINGERPRINT_MARKER + b"\t"):
                fields = stripped.split(b"\t")
                if len(fields) != 8:
                    raise ValueError(
                        f"malformed reference theorem record in {path}")
                full, compact = _reference_theorem(fields)
                if full["name"] in theorem_records:
                    raise ValueError(
                        f"duplicate reference theorem {full['name']} in {path}")
                theorem_records[full["name"]] = (full, compact)
            elif stripped.startswith(STATE_MARKER + b"\t"):
                fields = stripped.split(b"\t")
                if len(fields) != 10:
                    raise ValueError(f"malformed reference state record in {path}")
                state_records.append(_reference_state(fields))

    expected_names = list(theorem_names)
    if list(theorem_records) != expected_names:
        raise ValueError(
            f"reference theorem inventory mismatch in {path}: "
            f"expected={expected_names}, observed={list(theorem_records)}")
    if len(state_records) != 1:
        raise ValueError(
            f"expected one reference state record in {path}; "
            f"observed {len(state_records)}")
    full_theorems = [theorem_records[name][0] for name in expected_names]
    full_state, compact_state = state_records[0]
    if full_theorems != approved["theorems"]:
        raise ValueError(
            f"retained reference theorem SHA-256 does not match approval: {path}")
    if full_state != approved["post_state"]:
        raise ValueError(
            f"retained reference state SHA-256 does not match approval: {path}")
    return (
        tuple(theorem_records[name][1] for name in expected_names),
        compact_state,
        {"path": str(path.resolve()), "bytes": size,
         "sha256": digest.hexdigest()},
    )


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _derive_references(candle_root, tests, canonical_indices):
    sweep_root = candle_root / REFERENCE_RELATIVE
    references = {}
    for test in tests:
        index = canonical_indices[test.name]
        target_dir = sweep_root / f"target-{index:03d}"
        success_paths = sorted(target_dir.glob("attempt-*/success.json"))
        if len(success_paths) != 1:
            raise ValueError(
                f"expected one successful sweep-2 attempt for {test.name}; "
                f"found {len(success_paths)}")
        success_path = success_paths[0]
        success = _load_json(success_path)
        if (success.get("schema") != 1 or success.get("sweep") != 2 or
                success.get("target_index") != index or
                success.get("target") != test.name or
                success.get("promotion_allowed") is not False):
            raise ValueError(f"malformed reference success record: {success_path}")
        transcript_pin = success.get("artifacts", {}).get("transcript", {})
        relative = transcript_pin.get("path")
        if not isinstance(relative, str):
            raise ValueError(f"missing transcript pin: {success_path}")
        transcript_path = (
            candle_root / REFERENCE_RELATIVE.parent / relative).resolve()
        try:
            transcript_path.relative_to(
                (candle_root / REFERENCE_RELATIVE.parent).resolve())
        except ValueError as error:
            raise ValueError(
                f"reference transcript escapes evidence root: {relative}") from error
        compact_theorems, compact_state, transcript = (
            _derive_reference_transcript(
                transcript_path, test.fingerprint_theorems,
                test.fingerprint_expected_identities))
        if ({key: transcript[key] for key in ("bytes", "sha256")} !=
                {key: transcript_pin.get(key) for key in ("bytes", "sha256")}):
            raise ValueError(
                f"reference transcript does not match success pin: {transcript_path}")
        references[tuple(test.fingerprint_theorems)] = ReferenceTarget(
            name=test.name,
            theorem_names=tuple(test.fingerprint_theorems),
            approved=test.fingerprint_expected_identities,
            compact_theorems=compact_theorems,
            compact_state=compact_state,
            transcript=transcript,
            success=_file_record(success_path),
        )
    if len(references) != len(tests):
        raise ValueError("Great-100 theorem-name tuples are not unique")
    return references


def _compact_request_source(regression, theorem_names, suite_nonce=None,
                            process_nonce=None):
    if suite_nonce is not None or process_nonce is not None:
        raise ValueError("compatibility localizer cannot emit suite evidence")
    for name in theorem_names:
        if regression.OCAML_VALUE_PATH_RE.fullmatch(name) is None:
            raise ValueError(f"unsafe theorem value path: {name!r}")
    lines = [r'''
let candle_compatibility_md5 value =
  Digest.to_hex (Digest.string value);;

let candle_compatibility_emit_fingerprint name theorem =
  let theorem_identity,hypothesis_identity,conclusion_identity =
    candle_s1_theorem_parts theorem
  and axiom_identity = candle_s1_global_axioms () in
  print_endline
    ("CANDLE_COMPATIBILITY_FINGERPRINT_MD5_V1\t" ^
     candle_s1_hex name ^ "\t" ^
     candle_compatibility_md5 theorem_identity ^ "\t" ^
     candle_compatibility_md5 hypothesis_identity ^ "\t" ^
     candle_compatibility_md5 conclusion_identity ^ "\t" ^
     candle_compatibility_md5 axiom_identity ^ "\t" ^
     string_of_int (String.length theorem_identity) ^ "\t" ^
     string_of_int (String.length hypothesis_identity) ^ "\t" ^
     string_of_int (String.length conclusion_identity) ^ "\t" ^
     string_of_int (String.length axiom_identity) ^ "\t" ^
     string_of_int (List.length (hyp theorem)) ^ "\t" ^
     string_of_int (List.length (axioms())));;

let candle_compatibility_emit_state () =
  let state,type_constants,term_constants,primitive_definitions,global_axioms =
    candle_s1_kernel_state_parts () in
  print_endline
    ("CANDLE_COMPATIBILITY_STATE_MD5_V1\t" ^
     candle_compatibility_md5 state ^ "\t" ^
     candle_compatibility_md5 type_constants ^ "\t" ^
     candle_compatibility_md5 term_constants ^ "\t" ^
     candle_compatibility_md5 primitive_definitions ^ "\t" ^
     candle_compatibility_md5 global_axioms ^ "\t" ^
     string_of_int (String.length state) ^ "\t" ^
     string_of_int (String.length type_constants) ^ "\t" ^
     string_of_int (String.length term_constants) ^ "\t" ^
     string_of_int (String.length primitive_definitions) ^ "\t" ^
     string_of_int (String.length global_axioms) ^ "\t" ^
     string_of_int (List.length (types())) ^ "\t" ^
     string_of_int (List.length (constants())) ^ "\t" ^
     string_of_int (List.length (definitions())) ^ "\t" ^
     string_of_int (List.length (axioms())));;
'''.strip()]
    lines.extend(
        f'candle_compatibility_emit_fingerprint "{name}" {name};;'
        for name in theorem_names)
    lines.append("candle_compatibility_emit_state ();;")
    return "\n".join(lines) + "\n"


def _parse_md5(field, label):
    if MD5_RE.fullmatch(field) is None:
        raise ValueError(f"malformed compact MD5: {label}")
    return field.decode("ascii")


def _parse_nonnegative(field, label):
    try:
        value = int(field)
    except ValueError as error:
        raise ValueError(f"non-numeric compact field: {label}") from error
    if value < 0:
        raise ValueError(f"negative compact field: {label}")
    return value


def _observed_theorem(fields):
    if len(fields) != 12:
        raise ValueError(
            f"compact theorem record has {len(fields)} fields; expected 12")
    name_bytes = _decode_hex(fields[1], "compact theorem name")
    try:
        name = name_bytes.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError("non-ASCII compact theorem name") from error
    labels = ("theorem", "hypotheses", "conclusion", "global_axioms")
    digests = [
        _parse_md5(field, label)
        for field, label in zip(fields[2:6], labels)
    ]
    lengths = [
        _parse_nonnegative(field, f"{label} length")
        for field, label in zip(fields[6:10], labels)
    ]
    return {
        "name": name,
        **{label: {"md5": digest, "bytes": length}
           for label, digest, length in zip(labels, digests, lengths)},
        "hypothesis_count": _parse_nonnegative(
            fields[10], "hypothesis count"),
        "global_axiom_count": _parse_nonnegative(
            fields[11], "global axiom count"),
    }


def _observed_state(fields):
    if len(fields) != 15:
        raise ValueError(
            f"compact state record has {len(fields)} fields; expected 15")
    labels = ("kernel_state", "type_constants", "term_constants",
              "definitions", "global_axioms")
    digests = [
        _parse_md5(field, label)
        for field, label in zip(fields[1:6], labels)
    ]
    lengths = [
        _parse_nonnegative(field, f"{label} length")
        for field, label in zip(fields[6:11], labels)
    ]
    counts = [
        _parse_nonnegative(field, label)
        for field, label in zip(fields[11:15], (
            "type constant count", "term constant count",
            "definition count", "global axiom count"))
    ]
    return {
        **{label: {"md5": digest, "bytes": length}
           for label, digest, length in zip(labels, digests, lengths)},
        "type_constant_count": counts[0],
        "term_constant_count": counts[1],
        "definition_count": counts[2],
        "global_axiom_count": counts[3],
    }


def _parse_compact_log(log_path, theorem_names, reference, failure_type):
    theorem_records = {}
    states = []
    with Path(log_path).open("rb") as log:
        for line in log:
            stripped = line.rstrip(b"\r\n")
            try:
                if stripped.startswith(COMPACT_FINGERPRINT_MARKER + b"\t"):
                    record = _observed_theorem(stripped.split(b"\t"))
                    if record["name"] in theorem_records:
                        raise ValueError(
                            f"duplicate compact theorem: {record['name']}")
                    theorem_records[record["name"]] = record
                elif stripped.startswith(COMPACT_STATE_MARKER + b"\t"):
                    states.append(_observed_state(stripped.split(b"\t")))
            except ValueError as error:
                raise failure_type(str(error)) from error

    expected_names = list(theorem_names)
    if list(theorem_records) != expected_names:
        raise failure_type(
            "compact theorem request mismatch: "
            f"expected={expected_names}, observed={list(theorem_records)}")
    if len(states) != 1:
        raise failure_type(
            f"expected one compact state record; observed {len(states)}")
    observed_theorems = tuple(theorem_records[name] for name in expected_names)
    theorem_matches = [
        observed == expected
        for observed, expected in zip(
            observed_theorems, reference.compact_theorems)
    ]
    if not all(theorem_matches):
        mismatches = [
            name for name, matched in zip(expected_names, theorem_matches)
            if not matched
        ]
        raise failure_type(
            "compact theorem identity mismatch against retained approved "
            f"transcript: {mismatches}")
    observed_state = states[0]
    state_components = {
        key: observed_state[key] == reference.compact_state[key]
        for key in observed_state
    }
    return {
        "status": "theorems_matched",
        "comparison": "structural-wire-md5-plus-byte-length-v1",
        "promotion_eligible": False,
        "s1_evidence": False,
        "theorems": list(observed_theorems),
        "post_state": {
            "status": (
                "matched" if all(state_components.values()) else "mismatched"),
            "component_matches": state_components,
            "observed": observed_state,
            "reference": reference.compact_state,
        },
        "reference_transcript": reference.transcript,
    }


def _make_compact_reader(references, failure_type):
    def read(log_path, theorem_names, mapping_status,
             expected_identities=None):
        if mapping_status != "audited":
            raise failure_type("compatibility localizer requires audited mapping")
        key = tuple(theorem_names)
        reference = references.get(key)
        if reference is None:
            raise failure_type("no retained compact reference for theorem tuple")
        if expected_identities != reference.approved:
            raise failure_type("runtime target does not retain approved identities")
        return _parse_compact_log(
            log_path, theorem_names, reference, failure_type)
    return read


def _finish_candle_at_eof(regression, repl, shutdown_timeout=300.0):
    """End a completed diagnostic session through ordinary stdin EOF.

    Candle intentionally does not provide OCaml's process-global [exit]
    binding.  The shared regression runner currently assumes it does.  EOF is
    the native REPL termination path and is already used by Candle's compiled
    performance gate; keep the workaround local to this nonpromotable tool.
    """
    timeout, wall_limited = regression._effective_expect_timeout(
        min(repl.inactivity_timeout, shutdown_timeout), repl.wall_deadline)
    repl.process.sendeof()
    index = repl.process.expect(
        [regression.pexpect.EOF, regression.pexpect.TIMEOUT], timeout=timeout)
    if index == 1:
        if wall_limited:
            raise regression.WallTimeout(
                "total wall deadline expired while closing Candle stdin")
        raise regression.InactivityTimeout(
            "Candle did not exit after ordinary stdin EOF")
    repl.process.close()
    if repl.process.exitstatus != 0 or repl.process.signalstatus is not None:
        raise regression.LoadFailure(
            "Candle EOF termination was not an ordinary zero exit")
    return repl.process.exitstatus


def _load_regression(candle_root):
    path = candle_root / "candle/regression.py"
    name = "_candle_great100_compatibility_regression"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Candle regression runner: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    if Path(module.CANDLE_ROOT).resolve() != candle_root:
        raise RuntimeError("loaded Candle regression runner has wrong root")
    return module


def _prepare_destinations(report, log_dir):
    report = Path(report)
    log_dir = Path(log_dir)
    if not report.is_absolute() or not log_dir.is_absolute():
        raise ValueError("report and log directory must be absolute")
    if report.exists() or report.is_symlink():
        raise ValueError(f"report already exists: {report}")
    if (report.parent.is_symlink() or not report.parent.is_dir() or
            report.parent.resolve() != report.parent):
        raise ValueError("report parent must be an ordinary canonical directory")
    if log_dir.exists() or log_dir.is_symlink():
        if (log_dir.is_symlink() or not log_dir.is_dir() or
                log_dir.resolve() != log_dir or any(log_dir.iterdir())):
            raise ValueError("log destination must be an empty canonical directory")
    else:
        if (log_dir.parent.is_symlink() or not log_dir.parent.is_dir() or
                log_dir.parent.resolve() != log_dir.parent):
            raise ValueError("log parent must be an ordinary canonical directory")
        log_dir.mkdir(mode=0o700)
    return report, log_dir


def _ocaml_string(value):
    """Quote the restricted path strings emitted into a Candle setup file."""
    if any(character in value for character in ('"', "\\", "\n", "\r")):
        raise ValueError(f"path cannot be represented safely in setup: {value!r}")
    return f'"{value}"'


def _stable_source_bytes(path):
    before = _file_record(path)
    source = Path(path).read_bytes()
    after = _file_record(path)
    if before != after or len(source) != before["bytes"]:
        raise ValueError(f"source changed while reading: {path}")
    return source, before


def _materialize_normalizations(candle_root, log_dir, tests,
                                specifications=TOP100_NORMALIZATIONS):
    """Create exact derived inputs and the one-shot runtime overlay setup."""
    selected_targets = {test.name for test in tests}
    selected = [
        specification for specification in specifications
        if selected_targets.intersection(specification.targets)
    ]
    if not selected:
        return None, {"active": False, "sources": []}

    prepared = []
    for specification in selected:
        relative = Path(specification.source)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(
                f"normalization source is not a safe relative path: {relative}")
        original = (candle_root / relative).resolve(strict=True)
        if original.parent == candle_root or candle_root not in original.parents:
            raise ValueError(f"normalization source escapes Candle root: {relative}")
        source, original_record = _stable_source_bytes(original)
        if original_record["sha256"] != specification.expected_sha256:
            raise ValueError(
                f"normalization source identity mismatch: {relative}")
        normalized = source
        for old, new in specification.replacements:
            count = normalized.count(old)
            if count != 1:
                raise ValueError(
                    f"normalization replacement count for {relative}: {count}")
            normalized = normalized.replace(old, new, 1)
        if normalized == source:
            raise ValueError(f"normalization made no change: {relative}")
        prepared.append((specification, relative, original, source,
                         original_record, normalized))

    overlay_root = log_dir / "normalizations"
    overlay_root.mkdir(mode=0o700)
    runtime_mappings = []
    records = []
    for (specification, relative, original, source, original_record,
         normalized) in prepared:
        output = overlay_root / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as destination:
            destination.write(normalized)
        output_record = _file_record(output)
        original_md5 = hashlib.md5(
            source, usedforsecurity=False).hexdigest()
        normalized_md5 = hashlib.md5(
            normalized, usedforsecurity=False).hexdigest()
        # Great100 runs keep the boot loader's default manifest-root search
        # path.  Candle's Filename.concat normalizes that root away, so the
        # exact loader key is the manifest-relative source.  The authenticated
        # absolute path remains in the report.
        runtime_original = relative.as_posix()
        runtime_mappings.append(
            (runtime_original, str(output.resolve()),
             original_md5, normalized_md5))
        records.append({
            "targets": list(specification.targets),
            "source": specification.source,
            "rationale": specification.rationale,
            "replacement_count": len(specification.replacements),
            "original": original_record,
            "normalized": output_record,
            "runtime_md5": {
                "original": original_md5,
                "normalized": normalized_md5,
            },
            "runtime_original": runtime_original,
        })

    setup_lines = [
        "let candle_great100_check_normalization label path expected =",
        "  if Digest.to_hex (Digest.file path) = expected then ()",
        "  else failwith (\"Great 100 normalization digest mismatch: \" ^ label);;",
    ]
    mapping_names = []
    for index, (original, normalized, original_md5,
                normalized_md5) in enumerate(runtime_mappings, 1):
        original_name = f"candle_great100_original_{index}"
        normalized_name = f"candle_great100_normalized_{index}"
        mapping_names.append(f"({original_name},{normalized_name})")
        setup_lines.extend([
            f"let {original_name} = {_ocaml_string(original)};;",
            f"let {normalized_name} = {_ocaml_string(normalized)};;",
            ("candle_great100_check_normalization \"original\" "
             f"{original_name} \"{original_md5}\";;"),
            ("candle_great100_check_normalization \"normalized\" "
             f"{normalized_name} \"{normalized_md5}\";;"),
        ])
    setup_lines.extend([
        "Cakeml.configureNormalizationOverlay",
        "  [" + ";".join(mapping_names) + "];;",
    ])
    setup_path = overlay_root / "setup.ml"
    with setup_path.open("x", encoding="ascii", newline="\n") as setup:
        setup.write("\n".join(setup_lines) + "\n")
    return setup_path, {
        "active": True,
        "contract": (
            "exact original SHA-256 plus single-occurrence rewrites; runtime "
            "rechecks original and normalized MD5 before one-shot overlay"
        ),
        "promotion_eligible": False,
        "setup": _file_record(setup_path),
        "sources": records,
    }


def _load_after_normalization_setup(original_load, setup_path):
    """Wrap CandleREPL.load so setup runs once, after hol.ml and before target."""
    setup_path = str(Path(setup_path).resolve())

    def load(repl, file):
        if file != "hol.ml" and not getattr(
                repl, "_great100_normalization_configured", False):
            repl._great100_normalization_configured = True
            original_load(repl, setup_path)
        return original_load(repl, file)

    return load


def _result_record(regression, result, test):
    fingerprints = result.fingerprints
    return {
        "name": result.name,
        "files": list(test.files),
        "status": result.status.value,
        "compatibility_status": (
            fingerprints["status"] if result.status is regression.TestStatus.PASS
            and fingerprints is not None else "failed"),
        "timeout_kind": result.timeout_kind,
        "boot_elapsed_seconds": result.boot_elapsed,
        "hol_elapsed_seconds": result.hol_elapsed,
        "test_elapsed_seconds": result.test_elapsed,
        "fingerprint_elapsed_seconds": result.fingerprint_elapsed,
        "total_elapsed_seconds": result.total,
        "peak_process_rss_kib": result.peak_process_rss_kib,
        "peak_tree_rss_kib": result.peak_tree_rss_kib,
        "error_message": result.error_message,
        "transcript": _file_record(result.log_path),
        "compact_fingerprints": fingerprints,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the nonpromotable compact Great-100 localizer")
    parser.add_argument("--candle-root", required=True, type=Path)
    parser.add_argument("--json-report", required=True, type=Path)
    parser.add_argument("--log-dir", required=True, type=Path)
    parser.add_argument("--target", action="append", default=[],
                        help="run only this canonical target (repeatable)")
    parser.add_argument("-j", "--jobs", type=int, default=8)
    parser.add_argument("--inactivity-timeout", type=float, default=3600)
    parser.add_argument("--wall-timeout", type=float, default=21600)
    parser.add_argument("--heap-mb", type=int, default=6000)
    args = parser.parse_args(argv)

    if not 1 <= args.jobs <= 10:
        parser.error("--jobs must be between 1 and 10")
    if args.inactivity_timeout <= 0 or args.wall_timeout <= 0:
        parser.error("timeouts must be positive")
    if args.heap_mb <= 0:
        parser.error("--heap-mb must be positive")
    candle_root = args.candle_root.resolve(strict=True)
    report, log_dir = _prepare_destinations(args.json_report, args.log_dir)
    regression = _load_regression(candle_root)
    head, status = regression._git_state()
    if status:
        raise SystemExit(
            "compatibility localizer requires a clean Candle Git tree: " +
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

    approved_serializers = {
        test.fingerprint_expected_identities["serializer_sha256"]
        for test in tests
    }
    if len(approved_serializers) != 1:
        raise SystemExit("selected targets do not share one approved serializer")
    approved_serializer = next(iter(approved_serializers))
    current_serializer = _file_record(regression.FINGERPRINT_HELPER)
    if current_serializer["sha256"] == approved_serializer:
        raise SystemExit(
            "current serializer is approved; use Candle's official Great-100 "
            "controller instead of the compatibility localizer")

    print("NONPROMOTABLE COMPATIBILITY LOCALIZER — NEVER S1 EVIDENCE")
    print(f"Candle: {head}")
    print(f"Approved serializer: {approved_serializer}")
    print(f"Observed serializer: {current_serializer['sha256']}")
    print("Deriving compact comparison values from retained approved transcripts...")
    canonical_indices = {
        test.name: index for index, test in enumerate(regression.TOP100, 1)
    }
    references = _derive_references(candle_root, tests, canonical_indices)
    normalization_setup, normalization_contract = _materialize_normalizations(
        candle_root, log_dir, tests)

    original_request = regression._fingerprint_request_source
    original_reader = regression._read_fingerprint_records
    original_finish = regression.CandleREPL.finish
    original_load = regression.CandleREPL.load
    regression._fingerprint_request_source = (
        lambda names, suite_nonce=None, process_nonce=None:
        _compact_request_source(
            regression, names, suite_nonce, process_nonce))
    regression._read_fingerprint_records = _make_compact_reader(
        references, regression.LoadFailure)
    regression.CandleREPL.finish = (
        lambda repl: _finish_candle_at_eof(regression, repl))
    if normalization_setup is not None:
        regression.CandleREPL.load = _load_after_normalization_setup(
            original_load, normalization_setup)

    requested_jobs = args.jobs
    jobs = regression.cap_jobs_for_heap(requested_jobs, args.heap_mb)
    environment = {**os.environ, "CML_HEAP_SIZE": str(args.heap_mb)}
    started_utc = datetime.now(timezone.utc).isoformat()
    try:
        results, wall = regression.run_suite(
            tests, jobs, args.inactivity_timeout,
            wall_timeout=args.wall_timeout, env=environment, log_dir=log_dir)
    finally:
        regression._fingerprint_request_source = original_request
        regression._read_fingerprint_records = original_reader
        regression.CandleREPL.finish = original_finish
        regression.CandleREPL.load = original_load

    end_head, end_status = regression._git_state()
    if (end_head, end_status) != (head, status):
        raise SystemExit("Candle Git state changed during compatibility run")
    tests_by_name = {test.name: test for test in tests}
    rows = [
        _result_record(regression, result, tests_by_name[result.name])
        for result in results
    ]
    compatible = sum(
        row["compatibility_status"] == "theorems_matched" for row in rows)
    state_matched = sum(
        row["compact_fingerprints"] is not None and
        row["compact_fingerprints"]["post_state"]["status"] == "matched"
        for row in rows)
    timeouts = sum(row["status"] == "TIMEOUT" for row in rows)
    failures = len(rows) - compatible
    script = _file_record(Path(__file__).resolve())
    approval = _file_record(regression.APPROVAL_PATH)
    linked = _file_record(regression.LINKED_RECORD_PATH)
    payload = {
        "format": "candle-great100-compatibility-localizer-v1",
        "warning": (
            "DIAGNOSTIC ONLY: MD5-plus-length comparison under an unapproved "
            "serializer and optional exact source normalizations; never "
            "schema-7, S1, or promotable evidence."),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "started_utc": started_utc,
        "promotion": {
            "eligible": False,
            "s1_evidence": False,
            "schema7_evidence": False,
            "reason": "unapproved-serializer-compact-functional-localizer",
        },
        "scope": {
            "canonical_inventory_target_count": len(regression.TOP100),
            "requested_target_count": len(tests),
            "requested_targets": [test.name for test in tests],
            "complete_canonical_inventory": len(tests) == 65,
        },
        "summary": {
            "reported_target_count": len(rows),
            "theorem_compatibility_match_count": compatible,
            "post_state_match_count": state_matched,
            "failure_count": failures,
            "timeout_count": timeouts,
            "functional_compatibility_65_of_65": (
                len(tests) == 65 and len(rows) == 65 and compatible == 65),
        },
        "comparison_contract": {
            "algorithm": "MD5 plus exact byte length over structural-v2 wire",
            "collision_resistance_claimed": False,
            "reference_derivation": (
                "retained sweep-2 raw wires rechecked against independently "
                "approved SHA-256 identities before MD5 derivation"),
            "theorem_mismatch_result": "FAIL",
            "post_state_mismatch_result": (
                "reported separately; does not mask theorem compatibility"),
            "process_termination": (
                "ordinary zero exit after REPL stdin EOF; Candle does not "
                "provide the OCaml exit binding assumed by regression.py"),
            "source_normalizations": normalization_contract,
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
            "script": script,
            "candle_executable": _file_record(
                candle_root / "candle/build/cake"),
            "linked_record": linked,
            "observed_serializer": current_serializer,
            "approved_serializer_sha256": approved_serializer,
            "independent_approval": approval,
        },
        "reference_inputs": [
            {
                "target": reference.name,
                "transcript": reference.transcript,
                "success": reference.success,
                "compact_identity_sha256": _canonical_sha256({
                    "theorems": reference.compact_theorems,
                    "post_state": reference.compact_state,
                }),
            }
            for reference in references.values()
        ],
        "results": rows,
    }
    with report.open("x", encoding="utf-8") as output:
        json.dump(payload, output, indent=2)
        output.write("\n")
    print(f"Compatibility: {compatible}/{len(tests)}")
    print(f"Post-state exact matches: {state_matched}/{len(tests)}")
    print(f"Machine-readable nonpromotable report: {report}")
    return 0 if failures == 0 and len(rows) == len(tests) else 1


if __name__ == "__main__":
    raise SystemExit(main())
