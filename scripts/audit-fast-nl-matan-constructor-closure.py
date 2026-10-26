#!/usr/bin/env python3
"""Detect stale analytic datatype consumers in the exact fast-NL closure."""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import re
import sys


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
MODULE_AUDIT_PATH = PROJECT / "scripts/audit-fast-nl-support-module-closure.py"
FAILURE_LOG = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-fixed-scale-v677/runtime.log"
)
EXPECTED_FAILURE_LOG_SHA256 = (
    "a88f44347a830c7ed6dfe76b052082106d50b75e08516fffe82d6cc408c83006"
)

EXPR_OLD_CONSTRUCTORS = {
    "Candle_analytic_poly",
    "Candle_analytic_neg",
    "Candle_analytic_add",
    "Candle_analytic_mul",
    "Candle_analytic_square",
    "Candle_analytic_inv",
    "Candle_analytic_sqrt",
    "Candle_analytic_atn",
    "Candle_analytic_pi_half",
}
INSTRUCTION_OLD_CONSTRUCTORS = {
    "Candle_analytic_program_neg",
    "Candle_analytic_program_add",
    "Candle_analytic_program_mul",
    "Candle_analytic_program_square",
    "Candle_analytic_program_inv",
    "Candle_analytic_program_sqrt",
    "Candle_analytic_program_atn",
    "Candle_analytic_program_pi_half",
}
EXPR_RE = re.compile(r"\bCandle_analytic_[a-z][A-Za-z0-9_]*\b")
INSTRUCTION_RE = re.compile(r"\bCandle_analytic_program_[a-z][A-Za-z0-9_]*\b")
MATAN_IDENTIFIER_RE = re.compile(r"\b[A-Za-z0-9_]*matan[A-Za-z0-9_]*\b", re.I)


def explicit_induction_branch_missing(
    text: str, induction_name: str, constructor_name: str
) -> bool:
    """Identify enumerated induction proofs with no matan case.

    A proof that applies one tactic uniformly to every induction goal does not
    need to name constructors.  A THENL proof enumerates its branches and must
    contain either the constructor or a matan-specific semantic theorem in the
    proof segment.  Complete constructor-family definitions are audited
    separately below.
    """

    start = 0
    while True:
        index = text.find(induction_name, start)
        if index < 0:
            return False
        end = text.find(";;", index)
        segment = text[index:] if end < 0 else text[index:end]
        if (
            "THENL" in segment
            and constructor_name not in segment
            and MATAN_IDENTIFIER_RE.search(segment) is None
        ):
            return True
        start = index + len(induction_name)


def load_module_audit():
    spec = importlib.util.spec_from_file_location(
        "fast_nl_module_closure", MODULE_AUDIT_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {MODULE_AUDIT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


MODULE = load_module_audit()


def planned_paths() -> tuple[set[pathlib.Path], list[str]]:
    """Reconstruct the same authenticated literal closure as the module audit."""

    starting, unresolved_loaded = MODULE.loaded_paths()
    normalized, normalization_mismatches = MODULE.parse_normalization()
    normalized[MODULE.DIRECT_SOURCE_INTERFACE_ORIGINAL] = (
        MODULE.DIRECT_SOURCE_INTERFACE_CANDIDATE
    )
    _, verifier_normalized, verifier_errors = MODULE.parse_verifier_closure()
    normalized.update(verifier_normalized)
    _, _, requests, dynamic = MODULE.source_facts(MODULE.V665_SUPPORT)
    errors = list(unresolved_loaded) + list(verifier_errors)
    errors.extend(f"normalization:{item}" for item in normalization_mismatches)
    errors.extend(f"support_dynamic:{item}" for item in dynamic)
    if tuple(requests) != (
        MODULE.PREREQUISITE_ENTRY_REQUESTS
        + MODULE.SUPERSEDED_LEGACY_REPLAY_REQUESTS
        + MODULE.LITERAL.ENTRY_REQUESTS
    ):
        errors.append("support_entry_order")
    requests = list(MODULE.PREREQUISITE_ENTRY_REQUESTS + MODULE.LITERAL.ENTRY_REQUESTS)

    visited = set(starting)
    visiting: set[pathlib.Path] = set()
    execution: set[pathlib.Path] = set()

    def visit(request: str) -> None:
        path = MODULE.resolve_planned(request)
        if path is None:
            errors.append(f"unresolved:{request}")
            return
        if path in visited or path in visiting:
            return
        visiting.add(path)
        executed = normalized.get(path, path)
        _, _, children, child_dynamic = MODULE.source_facts(executed)
        errors.extend(f"dynamic:{path}:{item}" for item in child_dynamic)
        for child in children:
            visit(child)
        visiting.remove(path)
        visited.add(path)
        execution.add(path)

    for request in requests:
        visit(request)
    return execution, errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Detect stale pre-matan datatype consumers in the exact fast-NL "
            "load closure.  By default the authenticated source tree is "
            "checked.  --candidate-candle-root is a development-only view of "
            "the same logical files and is never used by the central gate."
        )
    )
    parser.add_argument(
        "--candidate-candle-root",
        type=pathlib.Path,
        help="development Candle repository root whose relative files are checked",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not FAILURE_LOG.is_file() or MODULE.sha256(FAILURE_LOG) != EXPECTED_FAILURE_LOG_SHA256:
        print("status=1")
        print("error=failure_log_identity")
        return 1
    failure_text = FAILURE_LOG.read_text(encoding="utf-8", errors="replace")
    if (
        failure_text.count('EXCEPTION: Failure "TAC_PROOF: Unsolved goals"') != 1
        or failure_text.count(
            "- Finished loading candle/cv_compute_analytic_expr_program.ml"
        )
        != 1
        or "- Loading /project/worktrees/candle-direct-fast-nl-runtime-v1/"
        "candle/cv_compute_analytic_expr_certificate_patch.ml"
        not in failure_text
    ):
        print("status=1")
        print("error=failure_signature")
        return 1

    closure, errors = planned_paths()
    stale: dict[pathlib.Path, set[str]] = {}
    candle_root = MODULE.LITERAL.CANDLE_CURRENT.resolve()
    candidate_root = (
        args.candidate_candle_root.resolve()
        if args.candidate_candle_root is not None
        else None
    )
    if candidate_root is not None and not (candidate_root / "candle").is_dir():
        errors.append(f"candidate_candle_root:{candidate_root}")
    for path in sorted(closure, key=str):
        try:
            relative = path.relative_to(candle_root)
        except ValueError:
            continue
        checked_path = candidate_root / relative if candidate_root is not None else path
        if not checked_path.is_file():
            errors.append(f"candidate_missing:{checked_path}")
            continue
        text = checked_path.read_text(encoding="utf-8", errors="replace")
        uncommented = MODULE.LITERAL.strip_comments(text)
        reasons: set[str] = set()
        if explicit_induction_branch_missing(
            uncommented,
            "candle_analytic_expr_INDUCT",
            "Candle_analytic_matan",
        ):
            reasons.add("expr_induction_missing_matan")
        if explicit_induction_branch_missing(
            uncommented,
            "candle_analytic_instruction_INDUCT",
            "Candle_analytic_program_matan",
        ):
            reasons.add("instruction_induction_missing_matan")
        expr_constructors = set(EXPR_RE.findall(uncommented))
        if (
            EXPR_OLD_CONSTRUCTORS <= expr_constructors
            and "Candle_analytic_matan" not in expr_constructors
        ):
            reasons.add("complete_old_expr_family_missing_matan")
        instruction_constructors = set(INSTRUCTION_RE.findall(uncommented))
        if (
            INSTRUCTION_OLD_CONSTRUCTORS <= instruction_constructors
            and "Candle_analytic_program_matan" not in instruction_constructors
        ):
            reasons.add("complete_old_instruction_family_missing_matan")
        if (
            "Cexp_num 8" in uncommented
            and ("program_step" in uncommented or "instruction" in uncommented)
            and "Cexp_num 9" not in uncommented
        ):
            reasons.add("numeric_instruction_dispatch_missing_matan")
        if reasons:
            stale[checked_path] = reasons

    status = int(bool(errors or stale))
    print(f"status={status}")
    print(f"scan_mode={'candidate' if candidate_root is not None else 'authenticated'}")
    if candidate_root is not None:
        print(f"candidate_candle_root={candidate_root}")
    print(f"planned_load_path_count={len(closure)}")
    print(f"closure_error_count={len(errors)}")
    print(f"stale_constructor_consumer_count={len(stale)}")
    print(
        "observed_failure_source="
        "/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/"
        "cv_compute_analytic_expr_certificate_patch.ml"
    )
    for error in errors:
        print(f"closure_error={error}")
    for path, reasons in stale.items():
        print(f"stale_constructor_consumer={path}\treasons={','.join(sorted(reasons))}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
