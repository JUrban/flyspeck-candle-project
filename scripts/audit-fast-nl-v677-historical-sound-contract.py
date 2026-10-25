#!/usr/bin/env python3
"""Check the diagnosed v677t historical-sound SPECL compatibility repair."""

from __future__ import annotations

import pathlib
import hashlib
import subprocess


RUN = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-historical-sound-v677t"
)
TYPE_DIAGNOSTIC = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "historical-sound-specl-types-diagnostic-v677v/runtime.log"
)
ORIGINAL_ROOT = pathlib.Path("/project/worktrees/candle-direct-fast-nl-runtime-v1")
CANDIDATE_ROOT = pathlib.Path("/project/worktrees/candle-fast-nl-historical-sound-v1")
LOGICAL = pathlib.Path(
    "candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_sound.ml"
)
ORIGINAL_HEAD = "0f9690d3683efca78a60d4607596815245e37578"
CANDIDATE_HEAD = "522e7123471bda68ec3417d728507a5cda829897"
ORIGINAL_SHA256 = "6806691c08ce8367fb7593ab1d5184482b2bd0826999e0fdf72a181bdb3c6e7e"
CANDIDATE_SHA256 = "8c1dccc2662255efce8e27dc7e6fe33d679a617f3e236b9deebfe4f0d72fc1ec"


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root: pathlib.Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *arguments], text=True
    ).strip()


def main() -> int:
    log_path = RUN / "runtime.log"
    failed_path = RUN / "CHECKPOINT-FAILED"
    original = ORIGINAL_ROOT / LOGICAL
    candidate = CANDIDATE_ROOT / LOGICAL
    required = (log_path, failed_path, TYPE_DIAGNOSTIC, original, candidate)
    if any(not path.is_file() for path in required):
        return fail("missing_v677t_failure_evidence")
    log = log_path.read_text(encoding="utf-8", errors="replace")
    if log.count('EXCEPTION: Failure "SPECL"') != 1:
        return fail("v677t_specl_exception_count")
    if "CANDLE_FLYSPECK_V677_HISTORICAL_SOUND_CHECKPOINT_READY" in log:
        return fail("v677t_unexpected_success_marker")
    diagnostic = TYPE_DIAGNOSTIC.read_text(encoding="utf-8", errors="replace")
    evidence = (
        "CANDLE_V677_SPECL_FAILURE call=98 term_count=6",
        "CANDLE_V677_SPECL_TERM index=5 type=real term=x",
        "CANDLE_V677_SPECL_ARGUMENTS",
        "CANDLE_V677_SPECL_TERM index=5 type=cval term=x * y",
    )
    if any(diagnostic.count(item) != 1 for item in evidence):
        return fail("type_diagnostic_evidence")
    try:
        if (
            git(ORIGINAL_ROOT, "rev-parse", "HEAD") != ORIGINAL_HEAD
            or git(ORIGINAL_ROOT, "status", "--porcelain")
            or git(CANDIDATE_ROOT, "rev-parse", "HEAD") != CANDIDATE_HEAD
            or git(CANDIDATE_ROOT, "status", "--porcelain")
            or git(CANDIDATE_ROOT, "diff", "--name-only", "172d6a14064575a1dabca7e8e16fd9088070f415", "HEAD")
            != str(LOGICAL)
        ):
            return fail("source_repository")
    except (OSError, subprocess.CalledProcessError) as error:
        return fail(f"source_repository:{error}")
    if sha256(original) != ORIGINAL_SHA256 or sha256(candidate) != CANDIDATE_SHA256:
        return fail("source_identity")
    source = candidate.read_text(encoding="utf-8")
    corrected = '`third:(num#num)#(num#num)`; `x * y:real`; `z:real`]'
    stale = '`third:(num#num)#(num#num)`; `x * y`; `z:real`]'
    if source.count(corrected) != 1 or stale in source:
        return fail("specialization_type_annotation")
    print("status=0")
    print("failed_run_exception_count=1")
    print("diagnosed_type_mismatch_count=1")
    print("specialization_type_annotation_count=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
