#!/usr/bin/env python3
"""Authenticate the focused v677 historical-sound SPECL diagnostic."""

from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
DRIVER = PROJECT / "tools/fast_nl_v677_historical_sound_specl_diagnostic.ml"
REPAIR_AUDIT = PROJECT / "scripts/audit-fast-nl-v677-matan-repair.py"
CHAIN_AUDIT = PROJECT / "scripts/audit-fast-nl-v677-repair-checkpoint-chain.py"
BASE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-fixed-outer-nonlinear-compile-sound-v677s"
)
BASE_SHA256 = "25e7179af6617c2983746666903ed36a2d4d70072a71b36e8be314da44c87e14"


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


def run_audit(path: pathlib.Path) -> bool:
    completed = subprocess.run(
        [str(path)], cwd=PROJECT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120,
        check=False,
    )
    if completed.returncode != 0 or "status=0" not in completed.stdout.splitlines():
        print(completed.stdout, end="")
        return False
    return True


def main() -> int:
    for path in (DRIVER, REPAIR_AUDIT, CHAIN_AUDIT, BASE / "checkpoint.receipt"):
        if not path.is_file() or path.is_symlink():
            return fail(f"missing_or_symlink:{path}")
    if (BASE / "CHECKPOINT-FAILED").exists():
        return fail("base_failure_marker")
    prior = receipt(BASE / "checkpoint.receipt")
    if (
        prior.get("receipt_kind")
        != "development-fast-nl-v677-fixed-outer-nonlinear-compile-sound-checkpoint-v1"
        or prior.get("checkpoint_sha256") != BASE_SHA256
    ):
        return fail("base_receipt")
    if not run_audit(REPAIR_AUDIT) or not run_audit(CHAIN_AUDIT):
        return fail("repair_or_chain_audit")

    text = DRIVER.read_text(encoding="utf-8")
    expected = (
        "candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml",
    )
    if tuple(re.findall(r'(?m)^needs "([^"]+)";;$', text)) != expected:
        return fail("driver_boundary")
    required = (
        "let candle_v677_original_SPECL = SPECL;;",
        "CANDLE_V677_SPECL_FAILURE call=",
        "CANDLE_V677_SPECL_THEOREM ",
        "string_of_term (concl theorem)",
        "v677 historical SPECL diagnostic unexpectedly completed",
    )
    if any(text.count(item) != 1 for item in required):
        return fail("diagnostic_contract")

    print("status=0")
    print("planned_top_level_load_count=1")
    print("diagnostic_specl_wrapper_count=1")
    print(f"driver_sha256={sha256(DRIVER)}")
    print(f"base_checkpoint_sha256={BASE_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
