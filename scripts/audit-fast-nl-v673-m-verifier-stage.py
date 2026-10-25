#!/usr/bin/env python3
"""Audit the isolated m_verifier stage before its bounded run."""

from __future__ import annotations

import hashlib
import pathlib


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
DRIVER = PROJECT / "tools/fast_nl_v673_m_verifier_stage.ml"
CANONICAL = PROJECT / "tools/fast_nl_v665_support.ml"
PREDECESSOR = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "posttaylor-multivariate-v672"
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
    required = (
        DRIVER,
        CANONICAL,
        PREDECESSOR / "CHECKPOINT-READY",
        PREDECESSOR / "checkpoint.receipt",
        PREDECESSOR / "runtime.log",
    )
    for path in required:
        if not path.is_file():
            return fail(f"missing:{path}")
    if (PREDECESSOR / "CHECKPOINT-FAILED").exists():
        return fail("predecessor_failure_marker")

    predecessor = receipt(PREDECESSOR / "checkpoint.receipt")
    if (
        predecessor.get("receipt_kind")
        != "development-fast-nl-v672-multivariate-taylor-checkpoint-v1"
        or predecessor.get("checkpoint_sha256")
        != "77058d1661cc43565284db4c03d83e566affb99935112ffa7fbda643f9680d6f"
    ):
        return fail("predecessor_receipt")

    driver = DRIVER.read_text(encoding="utf-8")
    canonical = CANONICAL.read_text(encoding="utf-8")
    required_driver = (
        'needs "verifier/m_verifier_main.hl";;',
        '("taylor_interval-compiled.hl","461022ad60f0beaa660e6c8d1df59284")',
        '("multivariate_taylor-compiled.hl","802f2a19f6ad9680040e89e4ae349c78")',
        '("m_verifier_main.hl","ca4991873b0c34b2da24a7080c5f521b")',
        "CANDLE_FLYSPECK_V673_M_VERIFIER_CHECKPOINT_READY",
    )
    forbidden = (
        "cv_compute_polynomial_expr_dim_jet_semantics.ml",
        "cv_compute_exact_interval_square_core.ml",
        "cv_compute_analytic_expr_case10173_historical_registered_original_prove.ml",
        "benchmark_cv_compute_registered_hol4_export.ml",
    )
    if (
        any(driver.count(fragment) != 1 for fragment in required_driver)
        or any(fragment in driver for fragment in forbidden)
        or driver.count('needs "') != 1
    ):
        return fail("driver_scope")

    verifier_position = canonical.find('needs "verifier/m_verifier_main.hl";;')
    support_position = canonical.find(
        'needs "candle/cv_compute_polynomial_expr_dim_jet_semantics.ml";;'
    )
    if verifier_position < 0 or support_position < 0 or verifier_position >= support_position:
        return fail("canonical_order")
    deferred_support_count = canonical[verifier_position:].count("needs ") - 1
    if deferred_support_count != 15:
        return fail("deferred_support_count")

    predecessor_log = (PREDECESSOR / "runtime.log").read_text(
        encoding="utf-8", errors="replace"
    )
    if (
        predecessor_log.count(
            "- Finished loading taylor/theory/multivariate_taylor-compiled.hl"
        )
        != 1
        or predecessor_log.count(
            "CANDLE_FLYSPECK_V672_MULTIVARIATE_TAYLOR_CHECKPOINT_READY"
        )
        != 1
    ):
        return fail("predecessor_log")

    print("status=0")
    print("planned_top_level_load_count=1")
    print(f"deferred_direct_support_count={deferred_support_count}")
    print("predecessor_taylor_stage_count=2")
    print(f"driver_sha256={sha256(DRIVER)}")
    print(f"canonical_support_sha256={sha256(CANONICAL)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
