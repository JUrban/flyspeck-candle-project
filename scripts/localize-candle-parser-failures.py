#!/usr/bin/python3
"""Localize non-promotable Candle corpus parser failures.

This is a development aid, not a parser gate or evidence consumer.  It reads a
quotation-aware all-inventory plan and a retained development sweep, isolates
the first independently failing module item for each parser-error input, and
optionally performs line-granularity delta reduction while requiring that
OCaml 4.14.1 still parses the candidate and Candle still returns its canonical
parser-error protocol.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


EXACT_ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
RUN_ARGUMENT = "--candle-parser-diagnostic-v1"
RESULT_PREFIX = b"CANDLE_CAMLPARSER_DIAGNOSTIC_V1\t"
PARSER_ERROR_EXIT = 65
OUTPUT_ROOT_MODE = 0o555
OUTPUT_FILE_MODE = 0o444
PRIVATE_MODE = 0o700


class LocalizationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise LocalizationError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def read_json(path: Path, label: str) -> tuple[dict, bytes]:
    data = path.read_bytes()
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LocalizationError(f"cannot decode {label}: {path}: {error}") from error
    require(isinstance(value, dict), f"{label} is not an object")
    return value, data


@dataclass(frozen=True)
class Event:
    kind: str
    value: str
    start: int
    end: int
    depth: int


def _skip_comment(source: bytes, index: int) -> int:
    start = index
    index += 2
    depth = 1
    while index < len(source):
        if source[index:index + 2] == b"(*":
            depth += 1
            index += 2
        elif source[index:index + 2] == b"*)":
            depth -= 1
            index += 2
            if depth == 0:
                return index
        else:
            index += 1
    raise LocalizationError(f"unterminated comment at byte {start}")


def _skip_escaped(source: bytes, index: int, delimiter: int, label: str) -> int:
    start = index - 1
    while index < len(source):
        byte = source[index]
        index += 1
        if byte == 0x5C:
            if index < len(source):
                index += 1
        elif byte == delimiter:
            return index
    raise LocalizationError(f"unterminated {label} at byte {start}")


def _is_name_byte(byte: int) -> bool:
    return (
        0x41 <= byte <= 0x5A or 0x61 <= byte <= 0x7A
        or 0x30 <= byte <= 0x39 or byte in (0x5F, 0x27)
    )


def _skip_char_or_type_variable(source: bytes, index: int) -> int:
    index += 1
    if index >= len(source):
        return index
    byte = source[index]
    if byte == 0x5C:
        return _skip_escaped(source, index + 1, 0x27, "character literal")
    if byte in (0x20, 0x09, 0x0A, 0x0D):
        return index
    index += 1
    if index < len(source) and source[index] == 0x27:
        return index + 1
    while index < len(source) and _is_name_byte(source[index]):
        index += 1
    return index


def lexical_events(source: bytes) -> list[Event]:
    """Return loader-relevant words and ``;;`` with lexical nesting depth."""
    events: list[Event] = []
    stack: list[str] = []
    index = 0
    while index < len(source):
        if source[index:index + 2] == b"(*":
            index = _skip_comment(source, index)
            continue
        byte = source[index]
        if byte == 0x22:
            index = _skip_escaped(source, index + 1, 0x22, "string")
            continue
        if byte == 0x27:
            index = _skip_char_or_type_variable(source, index)
            continue
        if byte == 0x3B and source[index:index + 2] == b";;":
            events.append(Event("semis", ";;", index, index + 2, len(stack)))
            index += 2
            continue
        if (
            0x41 <= byte <= 0x5A or 0x61 <= byte <= 0x7A or byte == 0x5F
        ):
            end = index + 1
            while end < len(source) and _is_name_byte(source[end]):
                end += 1
            word = source[index:end].decode("ascii")
            events.append(Event("word", word, index, end, len(stack)))
            if word in {"struct", "sig", "begin"}:
                stack.append(word)
            elif word == "end" and stack:
                stack.pop()
            index = end
            continue
        index += 1
    return events


def first_outer_struct(source: bytes) -> tuple[int, int, int] | None:
    """Return body start/end and body depth for the first outer structure."""
    stack: list[Event] = []
    for event in lexical_events(source):
        if event.kind != "word":
            continue
        if event.value in {"struct", "sig", "begin"}:
            stack.append(event)
        elif event.value == "end" and stack:
            opened = stack.pop()
            if opened.value == "struct" and not stack:
                return opened.end, event.start, opened.depth + 1
    return None


def candidate_chunks(source: bytes) -> list[tuple[int, int, bytes]]:
    """Split an outer structure body, or a source, at same-level ``;;``."""
    region = first_outer_struct(source)
    if region is None:
        start, end, depth = 0, len(source), 0
    else:
        start, end, depth = region
    cuts = [
        event.end for event in lexical_events(source)
        if event.kind == "semis" and event.depth == depth
        and start <= event.start < end
    ]
    points = [start, *cuts, end]
    return [
        (left, right, source[left:right])
        for left, right in zip(points, points[1:])
        if source[left:right].strip()
    ]


@dataclass(frozen=True)
class ParserObservation:
    outcome: str
    exit_code: int | None
    stdout: bytes
    stderr: bytes
    elapsed_seconds: float


class ParserInvoker:
    def __init__(self, runtime: Path, timeout: int):
        self.runtime = runtime
        self.timeout = timeout
        self.calls = 0

    def __call__(self, source: bytes, nonce_value: int) -> ParserObservation:
        nonce = f"{nonce_value:064x}"[-64:]
        started = time.monotonic()
        try:
            process = subprocess.run(
                [str(self.runtime), RUN_ARGUMENT, nonce],
                input=source,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout,
                env=EXACT_ENVIRONMENT,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            self.calls += 1
            return ParserObservation(
                "timeout", None, error.stdout or b"", error.stderr or b"",
                time.monotonic() - started,
            )
        self.calls += 1
        expected = RESULT_PREFIX + nonce.encode() + b"\tOK\n"
        if process.returncode == 0 and process.stdout == expected and not process.stderr:
            outcome = "parse-ok"
        elif process.returncode == PARSER_ERROR_EXIT:
            outcome = "parse-error"
        else:
            outcome = "protocol-or-runtime-error"
        return ParserObservation(
            outcome, process.returncode, process.stdout, process.stderr,
            time.monotonic() - started,
        )


def ocaml_parses(ocamlc: Path, source: bytes) -> bool:
    with tempfile.TemporaryDirectory(prefix="candle-parser-localize-") as directory:
        path = Path(directory) / "candidate.ml"
        path.write_bytes(source)
        process = subprocess.run(
            [str(ocamlc), "-stop-after", "parsing", "-impl", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=EXACT_ENVIRONMENT,
            check=False,
        )
        return process.returncode == 0


def ddmin_lines(source: bytes, interesting: Callable[[bytes], bool]) -> bytes:
    lines = source.splitlines(keepends=True)
    if len(lines) < 2:
        return source
    granularity = 2
    while len(lines) >= 2:
        chunk_size = (len(lines) + granularity - 1) // granularity
        reduced = False
        for start in range(0, len(lines), chunk_size):
            candidate_lines = lines[:start] + lines[start + chunk_size:]
            if not candidate_lines:
                continue
            candidate = b"".join(candidate_lines)
            if interesting(candidate):
                lines = candidate_lines
                granularity = max(2, granularity - 1)
                reduced = True
                break
        if reduced:
            continue
        if granularity >= len(lines):
            break
        granularity = min(len(lines), granularity * 2)
    return b"".join(lines)


def line_number(source: bytes, offset: int) -> int:
    return source.count(b"\n", 0, offset) + 1


def preview(source: bytes) -> str:
    return re.sub(rb"\s+", b" ", source).strip()[:320].decode("utf-8", "replace")


def file_record(data: bytes, path: str) -> dict:
    return {"path": path, "bytes": len(data), "sha256": sha256(data)}


def validate_development_binding(
    result: dict, plan_data: bytes, runtime_data: bytes,
) -> None:
    """Accept the historical receipt and the reproducible runner receipt."""
    common = (
        result.get("kind")
        == "nonpromotable-development-parser-all-inventory"
        and result.get("promotion_allowed") is False
    )
    if result.get("schema") == 1:
        require(
            common
            and result.get("plan_sha256") == sha256(plan_data)
            and result.get("runtime_sha256") == sha256(runtime_data),
            "historical development result does not bind plan and runtime",
        )
        return
    if result.get("schema") == 2:
        plan = result.get("plan")
        runtime = result.get("runtime")
        require(
            common
            and result.get("profile") == "all-inventory"
            and result.get("s1_evidence") is False
            and result.get("s2_evidence") is False
            and result.get("s3_evidence") is False
            and result.get("ordinary_linked_provenance_consumed") is False
            and isinstance(plan, dict)
            and plan.get("bytes") == len(plan_data)
            and plan.get("sha256") == sha256(plan_data)
            and isinstance(runtime, dict)
            and runtime.get("bytes") == len(runtime_data)
            and runtime.get("sha256") == sha256(runtime_data)
            and runtime.get("ordinary_linked_provenance_consumed") is False,
            "development result does not bind plan and runtime",
        )
        return
    raise LocalizationError("unsupported development parser result schema")


def localize(
    plan_root: Path,
    development_result_root: Path,
    runtime: Path,
    ocamlc: Path,
    output_root: Path,
    timeout: int,
    minimize: bool,
) -> dict:
    require(not output_root.exists(), f"output root already exists: {output_root}")
    plan, plan_data = read_json(plan_root / "plan.json", "parser plan")
    result, result_data = read_json(
        development_result_root / "DEVELOPMENT-NONPROMOTABLE.json",
        "development parser result",
    )
    inputs = plan.get("inputs")
    attempts = result.get("attempts")
    require(
        plan.get("schema") == 3
        and plan.get("kind")
        == "candle-flyspeck-caml-parser-all-inventory-diagnostic-plan"
        and isinstance(inputs, list) and len(inputs) == 400,
        "localizer requires quotation-aware all-inventory plan schema 3",
    )
    runtime_data = runtime.read_bytes()
    require(
        runtime.is_file() and os.access(runtime, os.X_OK),
        "development runtime is not an executable file",
    )
    validate_development_binding(result, plan_data, runtime_data)
    require(
        isinstance(attempts, list) and len(attempts) == len(inputs),
        "development result attempt count differs from plan",
    )
    for index, (entry, attempt) in enumerate(zip(inputs, attempts)):
        require(
            isinstance(attempt, dict)
            and attempt.get("index") == index
            and attempt.get("source_key") == entry.get("source_key")
            and attempt.get("prepared_sha256")
            == entry.get("prepared_input", {}).get("sha256"),
            f"development result attempt does not bind plan input: {index}",
        )
    require(
        subprocess.run(
            [str(ocamlc), "-version"], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=EXACT_ENVIRONMENT, check=False,
        ).stdout.strip() == b"4.14.1",
        "localizer requires OCaml compiler 4.14.1",
    )

    invoker = ParserInvoker(runtime, timeout)
    records = []
    output_files: dict[str, bytes] = {}
    parse_error_indices = [
        attempt["index"] for attempt in attempts
        if attempt.get("outcome") == "parse-error"
    ]
    for index in parse_error_indices:
        entry = inputs[index]
        relative = entry["prepared_input"]["path"]
        source = (plan_root / relative).read_bytes()
        require(sha256(source) == entry["prepared_input"]["sha256"],
                f"prepared input drift: {index}")
        chunks = candidate_chunks(source)
        selected = None
        observation = None
        selected_chunk_index = None
        for chunk_index, (start, end, candidate) in enumerate(chunks):
            current = invoker(candidate, index * 100000 + chunk_index)
            if current.outcome != "parse-ok":
                selected = (start, end, candidate)
                observation = current
                selected_chunk_index = chunk_index
                break
        if selected is None:
            records.append({
                "index": index,
                "source_key": entry["source_key"],
                "status": "no-individually-failing-chunk",
                "chunk_count": len(chunks),
            })
            continue

        start, end, candidate = selected
        initial_observation = observation
        ocaml_initial = ocaml_parses(ocamlc, candidate)
        minimized = candidate
        if minimize and ocaml_initial and observation.outcome == "parse-error":
            reduction_counter = 0

            def interesting(value: bytes) -> bool:
                nonlocal reduction_counter
                reduction_counter += 1
                if not ocaml_parses(ocamlc, value):
                    return False
                return invoker(
                    value, index * 100000000 + reduction_counter,
                ).outcome == "parse-error"

            minimized = ddmin_lines(candidate, interesting)
        final_observation = invoker(minimized, index * 1000000000 + 999999)
        candidate_path = f"candidates/{index:03d}.ml"
        stdout_path = f"candidates/{index:03d}.stdout"
        stderr_path = f"candidates/{index:03d}.stderr"
        output_files[candidate_path] = minimized
        output_files[stdout_path] = final_observation.stdout
        output_files[stderr_path] = final_observation.stderr
        records.append({
            "index": index,
            "source_key": entry["source_key"],
            "status": "localized-candidate",
            "claim": "first independently non-passing lexical chunk; candidate only",
            "chunk_index": selected_chunk_index,
            "chunk_count": len(chunks),
            "original_start_byte": start,
            "original_end_byte": end,
            "original_start_line": line_number(source, start),
            "original_candidate": file_record(candidate, "unpublished-original-candidate"),
            "ocaml_4_14_1_initial_parse": ocaml_initial,
            "minimized": minimize and minimized != candidate,
            "candidate": file_record(minimized, candidate_path),
            "preview": preview(minimized),
            "initial_candle_outcome": initial_observation.outcome,
            "final_candle": {
                "outcome": final_observation.outcome,
                "exit_code": final_observation.exit_code,
                "elapsed_seconds": round(final_observation.elapsed_seconds, 6),
                "stdout": file_record(final_observation.stdout, stdout_path),
                "stderr": file_record(final_observation.stderr, stderr_path),
            },
        })
        print(
            f"{index:03d} {entry['source_key']} "
            f"{records[-1]['status']} {len(candidate)}->{len(minimized)} bytes",
            flush=True,
        )

    summary = {
        "schema": 1,
        "kind": "nonpromotable-candle-parser-failure-localization",
        "promotion_allowed": False,
        "s1_evidence": False,
        "s2_evidence": False,
        "s3_evidence": False,
        "limitations": [
            "lexical chunk isolation may change syntactic context",
            "line reduction proves only OCaml parsing and Candle parser divergence",
            "no inference, evaluation, semantics, reachability, or release claim",
        ],
        "plan": file_record(plan_data, str(plan_root / "plan.json")),
        "development_result": file_record(
            result_data,
            str(development_result_root / "DEVELOPMENT-NONPROMOTABLE.json"),
        ),
        "runtime": file_record(runtime_data, str(runtime)),
        "ocamlc": str(ocamlc),
        "ocaml_version": "4.14.1",
        "timeout_seconds": timeout,
        "line_minimization_enabled": minimize,
        "parse_error_input_count": len(parse_error_indices),
        "localized_candidate_count": sum(
            record["status"] == "localized-candidate" for record in records
        ),
        "no_individual_failure_count": sum(
            record["status"] == "no-individually-failing-chunk" for record in records
        ),
        "parser_invocation_count": invoker.calls,
        "records": records,
    }
    output_files["localization.json"] = canonical_bytes(summary)
    output_root.mkdir(mode=PRIVATE_MODE)
    for relative, data in output_files.items():
        path = output_root / relative
        path.parent.mkdir(mode=PRIVATE_MODE, parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(OUTPUT_FILE_MODE)
    for directory, names, _files in os.walk(output_root, topdown=False):
        for name in names:
            (Path(directory) / name).chmod(OUTPUT_ROOT_MODE)
    output_root.chmod(OUTPUT_ROOT_MODE)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-root", type=Path, required=True)
    parser.add_argument("--development-result-root", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--ocamlc", type=Path, default=Path("/usr/bin/ocamlc"))
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--no-minimize", action="store_true")
    arguments = parser.parse_args()
    summary = localize(
        arguments.plan_root.resolve(strict=True),
        arguments.development_result_root.resolve(strict=True),
        arguments.runtime.resolve(strict=True),
        arguments.ocamlc.resolve(strict=True),
        arguments.output_root,
        arguments.timeout_seconds,
        not arguments.no_minimize,
    )
    print(json.dumps({
        "localized_candidate_count": summary["localized_candidate_count"],
        "no_individual_failure_count": summary["no_individual_failure_count"],
        "parser_invocation_count": summary["parser_invocation_count"],
    }, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (LocalizationError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f"parser failure localization rejected: {error}") from error
