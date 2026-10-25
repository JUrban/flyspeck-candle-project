#!/usr/bin/env python3
"""Fail-closed audit of the planned fast-NL support load order.

The ordinary source-closure audit follows literal ``needs``/``loadt``/
``loads``/``flyspeck_needs``/``#use`` requests.  Some fast-NL files were
originally developed after an action-296 checkpoint and therefore also depend
on modules already present in that ambient state.  The v664 replay showed that
checking only the literal closure is insufficient:
``cv_compute_analytic_dim_jet_matan.ml`` opened two matan support modules that
the action-49 state did not contain.

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
import json
import pathlib
import re
import subprocess
import sys


PROJECT = pathlib.Path("/project")
PROJECT_REPO = PROJECT / "flyspeck-candle-project"
LITERAL_AUDIT_PATH = PROJECT_REPO / "scripts/audit-fast-nl-support-source-closure.py"
RUN = PROJECT / "flyspeck-candle-runs/v664-fast-nl-complete-support-closure-dev-001"
BASE_LOG = RUN / "base.log"
ACTION_LOG = RUN / "postaction49/runtime.log"
NORMALIZATION_OVERLAY = (
    PROJECT
    / "flyspeck-candle-runs/v355-postsetup-checkpoint-dev-001"
    / "overlay-data-v355.ml"
)
VERIFIER_FLYSPECK_ROOT = (
    PROJECT / "worktrees/flyspeck-cv-nonlinear-closure-v11-manifest-d6"
)
VERIFIER_FORMAL_ROOT = VERIFIER_FLYSPECK_ROOT / "formal_ineqs"
VERIFIER_CLOSURE = (
    PROJECT
    / "worktrees/candle-direct-fast-nl-runtime-v1"
    / "candle/flyspeck_nonlinear_verifier_closure.json"
)
VERIFIER_OVERLAY_ROOT = (
    PROJECT
    / "flyspeck-candle-runs/cv-first-leaf-predecessor-checkpoint-v37"
    / "overlay"
)
V665_RENDERER = PROJECT_REPO / "scripts/render-fast-nl-v665-inputs.py"
V665_DATA = PROJECT_REPO / "tools/fast_nl_v665_verifier_data.ml"
V665_COMPAT = PROJECT_REPO / "tools/fast_nl_v665_verifier_runtime_compat.ml"
V665_SUPPORT = PROJECT_REPO / "tools/fast_nl_v665_support.ml"
V664_BASE_STRICTBUILD = (
    PROJECT
    / "worktrees/flyspeck-strictbuild-checkpoint-base-9ae969df"
    / "text_formalization/build/strictbuild.hl"
)

# These four entries replace the ambient action-296 assumptions documented by
# the matan and verifier support sources.  Entry order is part of the contract.
PREREQUISITE_ENTRY_REQUESTS = (
    # Runtime-only names used throughout the canonical verifier closure.
    str(V665_COMPAT),
    # This must execute before arith_num.hl selects its numeral base.
    "arith_options.hl",
    # One declared umbrella for the legacy verifier, including matan_eval.
    "verifier/m_verifier_main.hl",
    # Foundational Candle modules that the matan bridge historically inherited
    # from the action-296 analytic checkpoint.
    "candle/cv_compute_polynomial_expr_dim_jet_semantics.ml",
    "candle/cv_compute_exact_interval_square_core.ml",
    "candle/cv_compute_exact_rational_inv.ml",
    "candle/cv_compute_exact_interval_matan_series.ml",
    "candle/cv_compute_exact_interval_matan_series_program.ml",
    # Other source files in the support closure with documented ambient
    # prerequisites rather than literal loads.
    "candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml",
    "candle/cv_compute_analytic_expr_fixed_scale_historical_root_four_x0_sound.ml",
    "candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_variable_compact_stack_sound.ml",
    "candle/cv_compute_analytic_expr_taylor_model_tree_compact_correct.ml",
    # Authenticate the original logical Flyspeck nodes; the configured
    # normalization overlay selects their current compatibility sources.
    "/project/flyspeck-candle-runs/v352-full-boundary-materialization-heap16-dev-005/snapshot/flyspeck/text_formalization/general/serialization.hl",
    "/project/flyspeck-candle-runs/v352-full-boundary-materialization-heap16-dev-005/snapshot/flyspeck/text_formalization/nonlinear/break_case_exec.hl",
)

# Modules supplied by the compiled runtime or OCaml basis rather than by a
# source file loaded through HOL Light's authenticated loader.  Keep this list
# narrow: adding an item requires a runtime probe or direct source evidence.
RUNTIME_MODULES = {
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
    r"(?m)^\s*module\s+(?!type\b)([A-Z][A-Za-z0-9_']*)\b"
)
OPEN_RE = re.compile(r"(?m)^\s*open\s+([A-Z][A-Za-z0-9_']*)\b")
QUALIFIED_RE = re.compile(r"\b([A-Z][A-Za-z0-9_']*)\s*\.")
LOADING_RE = re.compile(r"^- Loading (.+)$")
NORMALIZATION_RE = re.compile(
    r'^\s*\("([^"]+)","([^"]+)","([0-9a-f]{32})"\);\s*$'
)


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
        if LITERAL.LOAD_CALL_RE.search(line) and not LITERAL.LOAD_RE.search(line):
            dynamic_loads.append((line_number, line.strip()))
    return providers, references - providers, literal_loads, dynamic_loads


def parse_normalization() -> tuple[
    dict[pathlib.Path, pathlib.Path], list[tuple[pathlib.Path, pathlib.Path, str, str]]
]:
    """Return canonical-to-executed sources and any target hash mismatches."""

    mapping: dict[pathlib.Path, pathlib.Path] = {}
    mismatches: list[tuple[pathlib.Path, pathlib.Path, str, str]] = []
    for line in NORMALIZATION_OVERLAY.read_text(encoding="utf-8").splitlines():
        match = NORMALIZATION_RE.match(line)
        if not match:
            continue
        canonical = pathlib.Path(match.group(1)).resolve()
        target = pathlib.Path(match.group(2)).resolve()
        expected = match.group(3)
        # These are the three exact transformations performed by
        # tools/fast_nl_v664_setup.ml after loading overlay-data-v355.ml.
        # Assert the old values before applying them so setup drift fails
        # closed instead of being silently accepted by the static audit.
        if target == (
            PROJECT
            / "worktrees/flyspeck-strictbuild-bootstrap-v1"
            / "text_formalization/build/strictbuild.hl"
        ).resolve():
            if expected != "88364c468334ed91b661cc2ecc8a484a":
                mismatches.append((canonical, target, "88364c468334ed91b661cc2ecc8a484a", expected))
            target = V664_BASE_STRICTBUILD.resolve()
        elif target == (
            PROJECT
            / "worktrees/flyspeck-direct-action296-643bfd12"
            / "text_formalization/general/serialization.hl"
        ).resolve():
            if expected != "f8460ac2a26b291b113ffa2ad2ffaace":
                mismatches.append((canonical, target, "f8460ac2a26b291b113ffa2ad2ffaace", expected))
            expected = "e0766072204d441da563dd688cfe1a7b"
        elif target == (
            PROJECT
            / "worktrees/flyspeck-direct-action296-643bfd12"
            / "text_formalization/nonlinear/mk_all_ineq.hl"
        ).resolve():
            if expected != "3076e3e4143397c5764911906732abb7":
                mismatches.append((canonical, target, "3076e3e4143397c5764911906732abb7", expected))
            expected = "e335cb02c223ba4a0f748a62e7b48d87"
        mapping[canonical] = target
        actual = md5(target) if target.is_file() else "MISSING"
        if actual != expected:
            mismatches.append((canonical, target, expected, actual))
    return mapping, mismatches


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_verifier_closure() -> tuple[
    dict[pathlib.Path, str],
    dict[pathlib.Path, pathlib.Path],
    list[str],
]:
    """Authenticate the canonical verifier closure and its materialized overlay."""

    payload = json.loads(VERIFIER_CLOSURE.read_text(encoding="utf-8"))
    errors: list[str] = []
    if (
        payload.get("schema") != 1
        or payload.get("root")
        != "flyspeck:formal_ineqs/verifier/m_verifier_main.hl"
        or payload.get("counts", {}).get("selected_source_nodes") != 90
        or payload.get("counts", {}).get("normalized_sources") != 29
    ):
        errors.append("verifier_closure_contract")
    expected_head = payload.get("repositories", {}).get("flyspeck", {}).get("commit")
    try:
        actual_head = subprocess.check_output(
            ["git", "-C", str(VERIFIER_FLYSPECK_ROOT), "rev-parse", "HEAD"],
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        actual_head = f"ERROR:{error}"
    if actual_head != expected_head:
        errors.append(f"verifier_flyspeck_head:{actual_head}")

    roots = {
        "candle": LITERAL.CANDLE_CURRENT,
        "flyspeck": VERIFIER_FLYSPECK_ROOT,
    }
    identities: dict[pathlib.Path, str] = {}
    normalized: dict[pathlib.Path, pathlib.Path] = {}
    nodes = payload.get("source_nodes", {})
    if not isinstance(nodes, dict) or len(nodes) != 90:
        errors.append("verifier_source_nodes")
        nodes = {}
    for source_key, node in nodes.items():
        repository = node.get("repository")
        logical = node.get("logical_relative_path")
        if repository not in roots or not isinstance(logical, str):
            errors.append(f"verifier_node_shape:{source_key}")
            continue
        path = (roots[repository] / logical).resolve()
        if not path.is_file():
            errors.append(f"verifier_source_missing:{path}")
            continue
        actual_md5 = md5(path)
        actual_sha256 = sha256(path)
        if actual_md5 != node.get("md5") or actual_sha256 != node.get("sha256"):
            errors.append(f"verifier_source_hash:{path}")
            continue
        identities[path] = actual_md5
        normalization = node.get("normalization")
        if normalization is None:
            continue
        overlay = (VERIFIER_OVERLAY_ROOT / repository / logical).resolve()
        if not overlay.is_file():
            errors.append(f"verifier_overlay_missing:{overlay}")
            continue
        if (
            overlay.stat().st_size != normalization.get("normalized_bytes")
            or md5(overlay) != normalization.get("normalized_md5")
            or sha256(overlay) != normalization.get("normalized_sha256")
        ):
            errors.append(f"verifier_overlay_hash:{overlay}")
            continue
        normalized[path] = overlay
    if len(identities) != 90:
        errors.append(f"verifier_identity_count:{len(identities)}")
    if len(normalized) != 29:
        errors.append(f"verifier_normalization_count:{len(normalized)}")
    return identities, normalized, errors


def authenticate_v665_generated_inputs() -> list[str]:
    """Require the committed ML fragments to equal their canonical render."""

    try:
        completed = subprocess.run(
            [str(V665_RENDERER), "check"],
            cwd=PROJECT_REPO,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return [f"v665_generated_input_check:{error}"]
    if completed.returncode != 0:
        summary = " | ".join(completed.stdout.splitlines()[-4:])
        return [f"v665_generated_input_check:{summary}"]
    return []


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


def resolve_planned(request: str) -> pathlib.Path | None:
    """Resolve through the exact planned verifier-first support load path."""

    candidate = pathlib.Path(request)
    if candidate.is_absolute():
        return candidate.resolve(strict=False) if candidate.is_file() else None
    for root in (VERIFIER_FORMAL_ROOT,) + LITERAL.SEARCH_ROOTS:
        candidate = root / request
        if candidate.is_file():
            return candidate.resolve()
    return None


def main() -> int:
    for required in (
        LITERAL_AUDIT_PATH,
        BASE_LOG,
        ACTION_LOG,
        NORMALIZATION_OVERLAY,
        VERIFIER_CLOSURE,
        V665_RENDERER,
        V665_DATA,
        V665_COMPAT,
        V665_SUPPORT,
    ):
        if not required.is_file():
            print(f"missing_input={required}", file=sys.stderr)
            return 2

    starting_paths, unresolved_loaded = loaded_paths()
    normalized_sources, normalization_mismatches = parse_normalization()
    verifier_identities, verifier_normalized, verifier_errors = (
        parse_verifier_closure()
    )
    verifier_errors.extend(authenticate_v665_generated_inputs())
    normalization_conflicts = sorted(
        set(normalized_sources) & set(verifier_normalized), key=str
    )
    normalized_sources.update(verifier_normalized)
    facts: dict[
        pathlib.Path, tuple[set[str], set[str], list[str], list[tuple[int, str]]]
    ] = {}
    parse_errors: list[tuple[pathlib.Path, str]] = []

    def get_facts(path: pathlib.Path):
        if path not in facts:
            try:
                # The authenticated loader authorizes the canonical logical
                # source node, but evaluates the configured normalization
                # target.  Module and child-load facts must therefore come
                # from the exact bytes that will execute.
                facts[path] = source_facts(normalized_sources.get(path, path))
            except (OSError, UnicodeDecodeError, ValueError) as error:
                parse_errors.append((path, str(error)))
                facts[path] = set(), set(), [], []
        return facts[path]

    starting_modules = set(RUNTIME_MODULES)
    for path in starting_paths:
        providers, _, _, _ = get_facts(path)
        starting_modules.update(providers)

    _, _, support_requests, support_dynamic = source_facts(V665_SUPPORT)
    if tuple(support_requests) != PREREQUISITE_ENTRY_REQUESTS + LITERAL.ENTRY_REQUESTS:
        verifier_errors.append("v665_support_entry_order")
    if support_dynamic:
        verifier_errors.append("v665_support_dynamic_request")
    entry_requests = tuple(support_requests)
    entry_paths: list[pathlib.Path] = []
    unresolved_requests: list[tuple[pathlib.Path | None, str]] = []
    literal_edges: list[tuple[pathlib.Path, pathlib.Path]] = []
    execution_order: list[pathlib.Path] = []
    visiting: set[pathlib.Path] = set()
    visited: set[pathlib.Path] = set(starting_paths)

    def visit_request(request: str, parent: pathlib.Path | None) -> None:
        path = resolve_planned(request)
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
    identity_conflicts = sorted(
        path
        for path, expected in verifier_identities.items()
        if path in identities and identities[path] != expected
    )
    identities.update(verifier_identities)
    for path in (
        LITERAL.CANDLE_CURRENT / "candle/cv_compute_exact_interval_matan_series.ml",
        LITERAL.CANDLE_CURRENT
        / "candle/cv_compute_exact_interval_matan_series_program.ml",
        V665_COMPAT,
    ):
        identities[path.resolve()] = md5(path)
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
            or normalization_mismatches
            or verifier_errors
            or normalization_conflicts
            or identity_conflicts
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
    print(f"normalization_mismatch_count={len(normalization_mismatches)}")
    print(f"verifier_closure_error_count={len(verifier_errors)}")
    print(f"normalization_conflict_count={len(normalization_conflicts)}")
    print(f"identity_conflict_count={len(identity_conflicts)}")

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
    for canonical, target, expected, actual in normalization_mismatches:
        print(
            "normalization_mismatch="
            f"{canonical}\ttarget={target}\texpected={expected}\tactual={actual}"
        )
    for error in verifier_errors:
        print(f"verifier_closure_error={error}")
    for path in normalization_conflicts:
        print(f"normalization_conflict={path}")
    for path in identity_conflicts:
        print(f"identity_conflict={path}")

    return status


if __name__ == "__main__":
    raise SystemExit(main())
