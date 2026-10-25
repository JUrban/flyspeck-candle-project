#!/usr/bin/env python3
"""Audit the bounded stable prerequisite checkpoint before first-jet repair."""

from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
DRIVER = PROJECT / "tools/fast_nl_v677_pre_first_jet_checkpoint.ml"
OVERLAY = PROJECT / "tools/fast_nl_v677_matan_repair_overlay.ml"
REPAIR_AUDIT = PROJECT / "scripts/audit-fast-nl-v677-matan-repair.py"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def main() -> int:
    for path in (DRIVER, OVERLAY, REPAIR_AUDIT):
        if not path.is_file():
            return fail(f"missing:{path}")
    completed = subprocess.run(
        [str(REPAIR_AUDIT)], cwd=PROJECT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120, check=False
    )
    if completed.returncode != 0 or "status=0" not in completed.stdout.splitlines():
        print(completed.stdout, end="")
        return fail("repair_audit")
    text = DRIVER.read_text(encoding="utf-8")
    if text.count(f'#use "{OVERLAY}";;') != 1:
        return fail("overlay_use")
    expected = (
        "candle/cv_compute_analytic_expr_certificate_patch_compute.ml",
        "candle/cv_compute_analytic_expr_jet_check.ml",
    )
    if tuple(re.findall(r'(?m)^needs "([^"]+)";;$', text)) != expected:
        return fail("driver_boundary")
    if text.count("cv_compute_analytic_expr_first_jet_program_compute.ml") != 2:
        return fail("deferred_first_jet_check")
    print("status=0")
    print("planned_top_level_load_count=2")
    print("deferred_first_jet_count=1")
    print(f"driver_sha256={sha256(DRIVER)}")
    print(f"overlay_sha256={sha256(OVERLAY)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
