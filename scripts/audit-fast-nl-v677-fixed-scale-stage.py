#!/usr/bin/env python3
"""Audit the two-file fixed-scale analytic checkpoint stage."""

from __future__ import annotations

import hashlib
import pathlib
import re


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
DRIVER = PROJECT / "tools/fast_nl_v677_fixed_scale_stage.ml"
CANONICAL = PROJECT / "tools/fast_nl_v665_support.ml"
SOURCE_ROOT = pathlib.Path("/project/worktrees/candle-direct-fast-nl-runtime-v1")
PREDECESSOR = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/post-matan-v676"
)
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
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def main() -> int:
    for path in (
        DRIVER,
        CANONICAL,
        PREDECESSOR / "CHECKPOINT-READY",
        PREDECESSOR / "checkpoint.receipt",
        PREDECESSOR / "runtime.log",
    ):
        if not path.is_file():
            return fail(f"missing:{path}")
    if (PREDECESSOR / "CHECKPOINT-FAILED").exists():
        return fail("predecessor_failure_marker")

    predecessor = receipt(PREDECESSOR / "checkpoint.receipt")
    if (
        predecessor.get("receipt_kind")
        != "development-fast-nl-v676-matan-checkpoint-v1"
        or predecessor.get("checkpoint_sha256")
        != "014ac019edcb782bb4cc9aca77553bd541ea184aea0f64c29b6c6d6e865f5b0d"
    ):
        return fail("predecessor_receipt")

    canonical_entries = re.findall(
        r'(?m)^needs "([^"]+)";;$', CANONICAL.read_text(encoding="utf-8")
    )
    matan_tail = "candle/cv_compute_exact_interval_matan_series_program.ml"
    index = canonical_entries.index(matan_tail)
    expected = tuple(path for path, _, _ in ENTRIES)
    if tuple(canonical_entries[index + 1 : index + 3]) != expected:
        return fail("canonical_partition")

    driver = DRIVER.read_text(encoding="utf-8")
    if tuple(re.findall(r'(?m)^needs "([^"]+)";;$', driver)) != expected:
        return fail("driver_partition")
    for logical, expected_md5, expected_sha256 in ENTRIES:
        source = SOURCE_ROOT / logical
        if not source.is_file():
            return fail(f"source_missing:{logical}")
        if md5(source) != expected_md5 or sha256(source) != expected_sha256:
            return fail(f"source_identity:{logical}")
        if driver.count(f'("{pathlib.Path(logical).name}",') != 1:
            return fail(f"driver_identity_count:{logical}")
        if expected_md5 not in driver:
            return fail(f"driver_identity:{logical}")
    if (
        "fixed_outer_variable_compact_stack_sound" in driver
        or "taylor_model_tree_compact_correct" in driver
        or "registered_original_prove" in driver
    ):
        return fail("driver_scope")

    predecessor_log = (PREDECESSOR / "runtime.log").read_text(
        encoding="utf-8", errors="replace"
    )
    for name in (
        "cv_compute_exact_interval_matan_series",
        "cv_compute_exact_interval_matan_series_program",
    ):
        if predecessor_log.count(f"- Finished loading candle/{name}.ml") != 1:
            return fail(f"predecessor_completion:{name}")

    print("status=0")
    print(f"planned_top_level_load_count={len(ENTRIES)}")
    print("deferred_support_count=8")
    print(f"driver_sha256={sha256(DRIVER)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
