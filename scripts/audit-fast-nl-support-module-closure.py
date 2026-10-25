#!/usr/bin/env python3
"""Fail-closed audit of the planned fast-NL support load order.

The ordinary source-closure audit follows literal ``needs``/``loadt``/
``loads``/``#use`` requests.  Some fast-NL files were originally developed
after an action-296 checkpoint and therefore also depend on modules already
present in that ambient state.  The v664 replay showed that checking only the
literal closure is insufficient: ``cv_compute_analytic_dim_jet_matan.ml``
opened two matan support modules that the action-49 state did not contain.

This audit validates an explicit, deliberately small replacement for that
ambient state.  It loads Flyspeck's verifier and matan evaluator umbrellas,
then the two Candle matan bridge files, before the four existing support
entries.  Their declared literal dependency graphs determine the exact load
order.  Every source node must be authenticated, every hash must match, and
every source-level module reference must be available before its consumer is
evaluated.  The audit never guesses a provider from an unrelated test file.

The authenticated v664 base and action-49 logs are the authority for the
starting state.  This is DEVELOPMENT / NON-RELEASE preflight evidence, not
theorem evidence.
"""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import re
import sys


PROJECT = pathlib.Path("/project")
PROJECT_REPO = PROJECT / "flyspeck-candle-project"
LITERAL_AUDIT_PATH = PROJECT_REPO / "scripts/audit-fast-nl-support-source-closure.py"
RUN = PROJECT / "flyspeck-candle-runs/v664-fast-nl-complete-support-closure-dev-001"
BASE_LOG = RUN / "base.log"
ACTION_LOG = RUN / "postaction49/runtime.log"

# These four entries replace the ambient action-296 assumptions documented by
# the matan and verifier support sources.  Entry order is part of the contract.
PREREQUISITE_ENTRY_REQUESTS = (
    "verifier/m_verifier_main.hl",
    "trig/matan_eval.hl",
    "candle/cv_compute_exact_interval_matan_series.ml",
    "candle/cv_compute_exact_interval_matan_series_program.ml",
)

# Modules supplied by the compiled runtime or OCaml basis rather than by a
# source file loaded through HOL Light's authenticated loader.  Keep this list
# narrow: adding an item requires a runtime probe or direct source evidence.
RUNTIME_MODULES = {
    "Big_int",
    "Kernel",
    "Printf",
}


def load_literal_audit():
    spec = importlib.util.spec_from_file_location(
        "fast_nl_literal_closure", LITERAL_AUDIT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {LITERAL_AUDIT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LITERAL = load_literal_audit()

MODULE_PROVIDER_RE = re.compile(
    r"(?m)^module\s+(?!type\b)([A-Z][A-Za-z0-9_']*)\b"
)
OPEN_RE = re.compile(r"(?m)^\s*open\s+([A-Z][A-Za-z0-9_']*)\b")
QUALIFIED_RE = re.compile(r"\b([A-Z][A-Za-z0-9_']*)\s*\.")
LOADING_RE = re.compile(r"^- Loading (.+)$")


def mask_strings_and_quotations(text: str) -> str:
    """Mask OCaml strings and HOL quotations while preserving newlines."""

    out: list[str] = []
    in_string = False
    in_hol_quote = False
    escaped = False
    for char in text:
        if in_string:
            out.append(char if char == "\n" else " ")
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if in_hol_quote:
            out.append(char if char == "\n" else " ")
            if char == "`":
                in_hol_quote = False
            continue
        if char == '"':
            in_string = True
            out.append(" ")
        elif char == "`":
            in_hol_quote = True
            out.append(" ")
        else:
            out.append(char)
    return "".join(out)


def source_facts(
    path: pathlib.Path,
) -> tuple[set[str], set[str], list[str], list[tuple[int, str]]]:
    # The authenticated Flyspeck corpus contains a few historical non-UTF-8
    # comment bytes.  Candle accepted those exact bytes; replacement is used
    # only for this lexical module scan and never for hashing or execution.
    text = path.read_text(encoding="utf-8", errors="replace")
    uncommented = LITERAL.strip_comments(text)
    masked = mask_strings_and_quotations(uncommented)
    providers = set(MODULE_PROVIDER_RE.findall(masked))
    references = set(OPEN_RE.findall(masked)) | set(QUALIFIED_RE.findall(masked))
    literal_loads = LITERAL.LOAD_RE.findall(uncommented)
    dynamic_loads = []
    for line_number, line in enumerate(uncommented.splitlines(), start=1):
        if re.search(r"\b(?:needs|loadt|loads)\b", line) and not LITERAL.LOAD_RE.search(line):
            dynamic_loads.append((line_number, line.strip()))
    return providers, references - providers, literal_loads, dynamic_loads


def resolve_logged_path(text: str) -> pathlib.Path | None:
    candidate = pathlib.Path(text)
    if candidate.is_absolute() and candidate.is_file():
        return candidate.resolve()
    return LITERAL.resolve(text)


def loaded_paths() -> tuple[set[pathlib.Path], list[str]]:
    paths: set[pathlib.Path] = set()
    unresolved: list[str] = []
    for log in (BASE_LOG, ACTION_LOG):
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            match = LOADING_RE.match(line)
            if not match:
                continue
            path = resolve_logged_path(match.group(1))
            if path is None:
                unresolved.append(f"{log}:{match.group(1)}")
            else:
                paths.add(path)
    return paths, unresolved


def md5(path: pathlib.Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    for required in (LITERAL_AUDIT_PATH, BASE_LOG, ACTION_LOG):
        if not required.is_file():
            print(f"missing_input={required}", file=sys.stderr)
            return 2

    starting_paths, unresolved_loaded = loaded_paths()
    facts: dict[
        pathlib.Path, tuple[set[str], set[str], list[str], list[tuple[int, str]]]
    ] = {}
    parse_errors: list[tuple[pathlib.Path, str]] = []

    def get_facts(path: pathlib.Path):
        if path not in facts:
            try:
                facts[path] = source_facts(path)
            except (OSError, UnicodeDecodeError, ValueError) as error:
                parse_errors.append((path, str(error)))
                facts[path] = set(), set(), [], []
        return facts[path]

    starting_modules = set(RUNTIME_MODULES)
    for path in starting_paths:
        providers, _, _, _ = get_facts(path)
        starting_modules.update(providers)

    entry_requests = PREREQUISITE_ENTRY_REQUESTS + LITERAL.ENTRY_REQUESTS
    entry_paths: list[pathlib.Path] = []
    unresolved_requests: list[tuple[pathlib.Path | None, str]] = []
    literal_edges: list[tuple[pathlib.Path, pathlib.Path]] = []
    execution_order: list[pathlib.Path] = []
    visiting: set[pathlib.Path] = set()
    visited: set[pathlib.Path] = set(starting_paths)

    def visit_request(request: str, parent: pathlib.Path | None) -> None:
        path = LITERAL.resolve(request)
        if path is None:
            unresolved_requests.append((parent, request))
            return
        if parent is None:
            entry_paths.append(path)
        else:
            literal_edges.append((parent, path))
        if path in visited:
            return
        if path in visiting:
            # HOL Light's physical load cache breaks recursive needs cycles.
            return
        visiting.add(path)
        _, _, requests, _ = get_facts(path)
        for child in requests:
            visit_request(child, path)
        visiting.remove(path)
        visited.add(path)
        execution_order.append(path)

    for request in entry_requests:
        visit_request(request, None)

    available_modules = set(starting_modules)
    missing_modules: list[tuple[pathlib.Path, str]] = []
    dynamic_loads: list[tuple[pathlib.Path, int, str]] = []
    for path in execution_order:
        providers, references, _, dynamic = get_facts(path)
        for module in sorted(references - available_modules - providers):
            missing_modules.append((path, module))
        dynamic_loads.extend((path, line, text) for line, text in dynamic)
        available_modules.update(providers)

    identities, _ = LITERAL.parse_authority()
    required_paths = set(execution_order)
    missing_identities = sorted(
        (path for path in required_paths if path not in identities), key=str
    )
    stale_identities: list[tuple[pathlib.Path, str, str]] = []
    for path in sorted(required_paths, key=str):
        expected = identities.get(path)
        if expected is not None:
            actual = md5(path)
            if expected != actual:
                stale_identities.append((path, expected, actual))

    status = int(
        bool(
            parse_errors
            or unresolved_loaded
            or unresolved_requests
            or dynamic_loads
            or missing_modules
            or missing_identities
            or stale_identities
        )
    )
    print(f"status={status}")
    print(f"prerequisite_entry_count={len(PREREQUISITE_ENTRY_REQUESTS)}")
    print(f"support_entry_count={len(LITERAL.ENTRY_REQUESTS)}")
    print(f"starting_loaded_path_count={len(starting_paths)}")
    print(f"starting_module_count={len(starting_modules)}")
    print(f"planned_load_path_count={len(required_paths)}")
    print(f"literal_edge_count={len(literal_edges)}")
    print(f"missing_module_count={len(missing_modules)}")
    print(f"missing_identity_count={len(missing_identities)}")
    print(f"stale_identity_count={len(stale_identities)}")
    print(f"dynamic_request_count={len(dynamic_loads)}")
    print(f"unresolved_loaded_path_count={len(unresolved_loaded)}")
    print(f"unresolved_request_count={len(unresolved_requests)}")
    print(f"parse_error_count={len(parse_errors)}")

    for index, path in enumerate(entry_paths):
        print(f"entry_path={index}\t{path}")
    for path in missing_identities:
        print(f"missing_identity={path}\tmd5={md5(path)}")
    for path, module in missing_modules:
        print(f"missing_module={path}\t{module}")
    for path, line_number, line in dynamic_loads:
        print(f"dynamic_request={path}:{line_number}\t{line}")
    for item in unresolved_loaded:
        print(f"unresolved_loaded_path={item}")
    for parent, request in unresolved_requests:
        print(f"unresolved_request={parent or '<entry>'}\t{request}")
    for path, expected, actual in stale_identities:
        print(f"stale_identity={path}\texpected={expected}\tactual={actual}")
    for path, error in parse_errors:
        print(f"parse_error={path}\t{error}")

    return status


if __name__ == "__main__":
    raise SystemExit(main())
