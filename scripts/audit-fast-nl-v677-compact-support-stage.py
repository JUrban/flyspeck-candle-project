#!/usr/bin/env python3
"""Audit the bounded compact tree/stack continuation from v677w."""

from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
DRIVER = PROJECT / "tools/fast_nl_v677_compact_support_stage.ml"
CONTRACT = PROJECT / "scripts/audit-fast-nl-v677-compact-support-contract.py"
CHAIN_AUDIT = PROJECT / "scripts/audit-fast-nl-v677-repair-checkpoint-chain.py"
BASE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-historical-sound-v677w"
)
BASE_SHA256 = "0bd11b95aa83a1bf95d5df035f3a4639362c2f0ba076390ff80d3ffc22368bca"
SOURCE_ROOT = pathlib.Path("/project/worktrees/candle-direct-fast-nl-runtime-v1")
ENTRIES = (
    (
        "candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_variable_compact_stack_sound.ml",
        "4f77e1cbc03a58f0ae9819b3f08aaa8a",
        "ab84e3f6cd280ca441836bfca5baf1ab9ad51d7b60da373710ec2272a670ee39",
    ),
    (
        "candle/cv_compute_analytic_expr_taylor_model_tree_compact_correct.ml",
        "d5ca10ca9408acb7f9ea82460b8b7005",
        "efb231191051fb5c571911f38f2801bd596b33bba01b21b0cd9900ed2930ae55",
    ),
)


def digest(path: pathlib.Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    hasher.update(path.read_bytes())
    return hasher.hexdigest()


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
    for path in (DRIVER, CONTRACT, CHAIN_AUDIT, BASE / "checkpoint.receipt"):
        if not path.is_file() or path.is_symlink():
            return fail(f"missing_or_symlink:{path}")
    if not (BASE / "CHECKPOINT-READY").is_file() or (BASE / "CHECKPOINT-FAILED").exists():
        return fail("base_readiness")
    prior = receipt(BASE / "checkpoint.receipt")
    if (
        prior.get("receipt_kind")
        != "development-fast-nl-v677-historical-sound-checkpoint-v1"
        or prior.get("checkpoint_sha256") != BASE_SHA256
    ):
        return fail("base_receipt")
    checkpoint = pathlib.Path(prior.get("checkpoint", ""))
    if not checkpoint.is_file() or prior.get("checkpoint_size_bytes") != str(checkpoint.stat().st_size):
        return fail("base_checkpoint")
    if not run_audit(CHAIN_AUDIT) or not run_audit(CONTRACT):
        return fail("chain_or_compact_contract")

    text = DRIVER.read_text(encoding="utf-8")
    expected = tuple(logical for logical, _, _ in ENTRIES)
    if tuple(re.findall(r'(?m)^needs "([^"]+)";;$', text)) != expected:
        return fail("driver_boundary")
    if "#use " in text or text.count("COMPACT_SUPPORT_CHECKPOINT_READY") != 1:
        return fail("driver_contract")
    for index, (logical, expected_md5, expected_sha256) in enumerate(ENTRIES):
        source = SOURCE_ROOT / logical
        expected_driver_count = 2 if index == 0 else 1
        if (
            not source.is_file()
            or source.is_symlink()
            or digest(source, "md5") != expected_md5
            or digest(source, "sha256") != expected_sha256
            or text.count(expected_md5) != expected_driver_count
        ):
            return fail(f"source_identity:{logical}")

    print("status=0")
    print("planned_top_level_load_count=2")
    print("planned_new_source_count=8")
    print(f"driver_sha256={digest(DRIVER, 'sha256')}")
    print(f"base_checkpoint_sha256={BASE_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
