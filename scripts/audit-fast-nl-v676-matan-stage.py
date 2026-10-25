#!/usr/bin/env python3
"""Audit the two-file exact-interval matan checkpoint stage."""

from __future__ import annotations

import hashlib
import pathlib
import re


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
DRIVER = PROJECT / "tools/fast_nl_v676_matan_stage.ml"
CANONICAL = PROJECT / "tools/fast_nl_v665_support.ml"
PREDECESSOR = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/post-foundation-v675"
)
ENTRIES = (
    (
        "candle/cv_compute_exact_interval_matan_series.ml",
        "7461529a70e5f006cf0ecc8c45ba4297",
    ),
    (
        "candle/cv_compute_exact_interval_matan_series_program.ml",
        "8baa6fa6c5cb749377f07339d36f3705",
    ),
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        != "development-fast-nl-v675-foundation-checkpoint-v1"
        or predecessor.get("checkpoint_sha256")
        != "ced224dfab13d0f5fb2185a3d290883f1f4b460ff8ccb21cd9d374736cf46fe6"
    ):
        return fail("predecessor_receipt")

    canonical_entries = re.findall(
        r'(?m)^needs "([^"]+)";;$', CANONICAL.read_text(encoding="utf-8")
    )
    foundation_tail = "candle/cv_compute_exact_rational_inv.ml"
    index = canonical_entries.index(foundation_tail)
    expected = tuple(path for path, _ in ENTRIES)
    if tuple(canonical_entries[index + 1 : index + 3]) != expected:
        return fail("canonical_partition")

    driver = DRIVER.read_text(encoding="utf-8")
    if tuple(re.findall(r'(?m)^needs "([^"]+)";;$', driver)) != expected:
        return fail("driver_partition")
    for logical, digest in ENTRIES:
        if driver.count(f'("{pathlib.Path(logical).name}",') != 1 or digest not in driver:
            return fail(f"driver_identity:{logical}")
    if (
        "historical_dihedral_first_order_sound" in driver
        or "fixed_outer_variable_compact_stack_sound" in driver
        or "registered_original_prove" in driver
    ):
        return fail("driver_scope")

    predecessor_log = (PREDECESSOR / "runtime.log").read_text(
        encoding="utf-8", errors="replace"
    )
    for name in (
        "cv_compute_polynomial_expr_dim_jet_semantics",
        "cv_compute_exact_interval_square_core",
        "cv_compute_exact_rational_inv",
    ):
        if predecessor_log.count(f"- Finished loading candle/{name}.ml") != 1:
            return fail(f"predecessor_completion:{name}")

    print("status=0")
    print(f"planned_top_level_load_count={len(ENTRIES)}")
    print("deferred_support_count=10")
    print(f"driver_sha256={sha256(DRIVER)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
