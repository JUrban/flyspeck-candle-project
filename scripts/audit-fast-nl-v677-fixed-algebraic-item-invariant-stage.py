#!/usr/bin/env python3
"""Audit the focused fixed-algebraic item-invariant repair stage."""

from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
DRIVER = PROJECT / "tools/fast_nl_v677_fixed_algebraic_item_invariant_stage.ml"
REPAIR_AUDIT = PROJECT / "scripts/audit-fast-nl-v677-matan-repair.py"
BASE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-compile-sound-v677k"
)
BASE_SHA256 = "b934ae796417798dcf95952363f625431525af012e11413454fa7ca63a7d4583"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    for path in (DRIVER, REPAIR_AUDIT, BASE / "checkpoint.receipt"):
        if not path.is_file() or path.is_symlink():
            return fail(f"missing_or_symlink:{path}")
    if not (BASE / "CHECKPOINT-READY").is_file() or (BASE / "CHECKPOINT-FAILED").exists():
        return fail("base_readiness")
    prior = receipt(BASE / "checkpoint.receipt")
    if (
        prior.get("receipt_kind")
        != "development-fast-nl-v677-compile-sound-checkpoint-v1"
        or prior.get("checkpoint_sha256") != BASE_SHA256
    ):
        return fail("base_receipt")
    completed = subprocess.run(
        [str(REPAIR_AUDIT)], cwd=PROJECT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120, check=False
    )
    if completed.returncode != 0 or "status=0" not in completed.stdout.splitlines():
        print(completed.stdout, end="")
        return fail("repair_audit")
    text = DRIVER.read_text(encoding="utf-8")
    expected = (
        "candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_item_invariant.ml",
    )
    if tuple(re.findall(r'(?m)^needs "([^"]+)";;$', text)) != expected:
        return fail("driver_boundary")
    if "#use " in text or text.count(
        "CANDLE_FLYSPECK_V677_FIXED_ALGEBRAIC_ITEM_INVARIANT_CHECKPOINT_READY"
    ) != 1:
        return fail("driver_contract")
    print("status=0")
    print("planned_top_level_load_count=1")
    print(f"driver_sha256={sha256(DRIVER)}")
    print(f"base_checkpoint_sha256={BASE_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
