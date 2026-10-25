#!/usr/bin/env python3
"""Audit the bounded v677 matan-repair semantic proof-load inputs."""

from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
DRIVER = PROJECT / "tools/fast_nl_v677_matan_repair_probe.ml"
OVERLAY = PROJECT / "tools/fast_nl_v677_matan_repair_overlay.ml"
REPAIR_AUDIT = PROJECT / "scripts/audit-fast-nl-v677-matan-repair.py"
BASE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/post-matan-v676"
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def main() -> int:
    for path in (DRIVER, OVERLAY, REPAIR_AUDIT, BASE / "checkpoint.receipt"):
        if not path.is_file():
            return fail(f"missing:{path}")
    if not (BASE / "CHECKPOINT-READY").is_file() or (BASE / "CHECKPOINT-FAILED").exists():
        return fail("base_readiness")
    completed = subprocess.run(
        [str(REPAIR_AUDIT)], cwd=PROJECT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120, check=False
    )
    if completed.returncode != 0 or "status=0" not in completed.stdout.splitlines():
        print(completed.stdout, end="")
        return fail("repair_audit")
    driver = DRIVER.read_text(encoding="utf-8")
    if driver.count(f'#use "{OVERLAY}";;') != 1:
        return fail("overlay_use")
    expected_needs = (
        "candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml",
        "candle/cv_compute_analytic_expr_fixed_scale_historical_root_four_x0_sound.ml",
    )
    if tuple(re.findall(r'(?m)^needs "([^"]+)";;$', driver)) != expected_needs:
        return fail("driver_load_boundary")
    if driver.count("v677 repaired source was already loaded in predecessor") != 1:
        return fail("predecessor_noninterference_check")
    if driver.count("CANDLE_FLYSPECK_V677_MATAN_REPAIR_PROOF_LOAD_READY") != 1:
        return fail("ready_marker")
    print("status=0")
    print("planned_top_level_load_count=2")
    print("repair_source_count=19")
    print(f"driver_sha256={sha256(DRIVER)}")
    print(f"overlay_sha256={sha256(OVERLAY)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
