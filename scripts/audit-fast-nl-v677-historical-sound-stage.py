#!/usr/bin/env python3
"""Audit the bounded historical-soundness continuation from v677s."""

from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
DRIVER = PROJECT / "tools/fast_nl_v677_historical_sound_stage.ml"
REPAIR_AUDIT = PROJECT / "scripts/audit-fast-nl-v677-matan-repair.py"
CHAIN_AUDIT = PROJECT / "scripts/audit-fast-nl-v677-repair-checkpoint-chain.py"
BASE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-fixed-outer-nonlinear-compile-sound-v677s"
)
BASE_SHA256 = "25e7179af6617c2983746666903ed36a2d4d70072a71b36e8be314da44c87e14"
SOURCE_ROOT = pathlib.Path("/project/worktrees/candle-direct-fast-nl-runtime-v1")
ENTRIES = (
    (
        "candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml",
        "393018a4878384295220afb6fb307ba1",
        "688bbb2305ba69d7d267ce7742d932ffd86d3528e13096d2332cd19d927d065a",
    ),
    (
        "candle/cv_compute_analytic_expr_fixed_scale_historical_root_four_x0_sound.ml",
        "2d043a6136c50c80fcf332000a157558",
        "a2eb3ec97cf75df325433ef6b3ce16fb6a6d6a5e91c4da1250838d84e8ae7e18",
    ),
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def md5(path: pathlib.Path) -> str:
    return hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()


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
    for path in (
        DRIVER,
        REPAIR_AUDIT,
        CHAIN_AUDIT,
        BASE / "CHECKPOINT-READY",
        BASE / "checkpoint.receipt",
        BASE / "runtime.log",
    ):
        if not path.is_file():
            return fail(f"missing:{path}")
    if (BASE / "CHECKPOINT-FAILED").exists():
        return fail("base_failure_marker")

    prior = receipt(BASE / "checkpoint.receipt")
    if (
        prior.get("receipt_kind")
        != "development-fast-nl-v677-fixed-outer-nonlinear-compile-sound-checkpoint-v1"
        or prior.get("checkpoint_sha256") != BASE_SHA256
    ):
        return fail("base_receipt")
    checkpoint = pathlib.Path(prior.get("checkpoint", ""))
    if (
        not checkpoint.is_file()
        or prior.get("checkpoint_size_bytes") != str(checkpoint.stat().st_size)
    ):
        return fail("base_checkpoint")

    if not run_audit(REPAIR_AUDIT):
        return fail("repair_audit")
    if not run_audit(CHAIN_AUDIT):
        return fail("checkpoint_chain_audit")

    driver = DRIVER.read_text(encoding="utf-8")
    expected = tuple(logical for logical, _, _ in ENTRIES)
    if tuple(re.findall(r'(?m)^needs "([^"]+)";;$', driver)) != expected:
        return fail("driver_boundary")
    if "#use " in driver or driver.count("HISTORICAL_SOUND_CHECKPOINT_READY") != 1:
        return fail("driver_contract")
    for logical, expected_md5, expected_sha256 in ENTRIES:
        source = SOURCE_ROOT / logical
        if not source.is_file():
            return fail(f"source_missing:{logical}")
        if md5(source) != expected_md5 or sha256(source) != expected_sha256:
            return fail(f"source_identity:{logical}")
        if expected_md5 not in driver:
            return fail(f"driver_identity:{logical}")

    print("status=0")
    print("planned_top_level_load_count=2")
    print(f"driver_sha256={sha256(DRIVER)}")
    print(f"base_checkpoint_sha256={BASE_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
