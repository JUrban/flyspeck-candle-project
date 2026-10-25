#!/usr/bin/env python3
"""Authenticate the isolated algebraic program-sound residual diagnostic."""

from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
DRIVER = PROJECT / "tools/fast_nl_v677_algebraic_program_sound_diagnostic.ml"
BASE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-fixed-algebraic-item-invariant-v677m"
)
BASE_SHA256 = "6c48608d0bc73c18d7eb02ba66f0dd6cc63ab4841c1ec7dfaae240a1bfcf316f"
DIAGNOSTIC_ROOT = pathlib.Path("/project/worktrees/candle-fast-nl-matan-diagnostic-v1")
DIAGNOSTIC_HEAD = "5f78000e331d1e5777fb5b2b3662febb133b6916"
DIAGNOSTIC_SOURCE = DIAGNOSTIC_ROOT / (
    "candle/"
    "cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_program_sound.ml"
)
DIAGNOSTIC_SHA256 = "131a453f6058370cb53098a6ce7c284bd668d0e3566aeaa3211f39a806f936b1"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(DIAGNOSTIC_ROOT), *arguments], text=True
    ).strip()


def receipt(path: pathlib.Path) -> dict[str, str]:
    return dict(
        line.split("=", 1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def main() -> int:
    for path in (DRIVER, DIAGNOSTIC_SOURCE, BASE / "checkpoint.receipt"):
        if not path.is_file() or path.is_symlink():
            return fail(f"missing_or_symlink:{path}")
    if git("rev-parse", "HEAD") != DIAGNOSTIC_HEAD or git("status", "--porcelain"):
        return fail("diagnostic_worktree")
    if sha256(DIAGNOSTIC_SOURCE) != DIAGNOSTIC_SHA256:
        return fail("diagnostic_source_sha256")
    prior = receipt(BASE / "checkpoint.receipt")
    if (
        prior.get("receipt_kind")
        != "development-fast-nl-v677-fixed-algebraic-item-invariant-checkpoint-v1"
        or prior.get("checkpoint_sha256") != BASE_SHA256
    ):
        return fail("base_receipt")
    text = DRIVER.read_text(encoding="utf-8")
    expected = (
        "candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_program_sound.ml",
    )
    if tuple(re.findall(r'(?m)^needs "([^"]+)";;$', text)) != expected:
        return fail("driver_boundary")
    if text.count("candle_v677_program_sound_diagnostic") != 3:
        return fail("diagnostic_overlay_contract")
    if "Alist.lookup" in text or text.count("candle_v677_overlay_lookup") != 4:
        return fail("diagnostic_lookup_surface")
    print("status=0")
    print("planned_top_level_load_count=1")
    print(f"driver_sha256={sha256(DRIVER)}")
    print(f"diagnostic_source_sha256={DIAGNOSTIC_SHA256}")
    print(f"base_checkpoint_sha256={BASE_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
