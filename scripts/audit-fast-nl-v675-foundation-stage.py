#!/usr/bin/env python3
"""Audit the first three post-verifier support entries."""

from __future__ import annotations

import hashlib
import pathlib
import re


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
DRIVER = PROJECT / "tools/fast_nl_v675_foundation_stage.ml"
CANONICAL = PROJECT / "tools/fast_nl_v665_support.ml"
PREDECESSOR = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/post-m-verifier-v674"
)
ENTRIES = (
    (
        "candle/cv_compute_polynomial_expr_dim_jet_semantics.ml",
        "2cedcfc47a7658a443847039ea1f25eb",
    ),
    (
        "candle/cv_compute_exact_interval_square_core.ml",
        "0a342a6887dc5ff35eaae2d3447eba12",
    ),
    (
        "candle/cv_compute_exact_rational_inv.ml",
        "d2a4afdcb26c9eb12fefc2c6a935602d",
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
        != "development-fast-nl-v674-m-verifier-checkpoint-v1"
        or predecessor.get("checkpoint_sha256")
        != "9ea755cc3ac581eae1c4f2a7306c6fcfc94d7b0b04a3c20c5e4abfb31e7e3f1e"
    ):
        return fail("predecessor_receipt")

    canonical = CANONICAL.read_text(encoding="utf-8")
    canonical_entries = re.findall(r'(?m)^needs "([^"]+)";;$', canonical)
    verifier_index = canonical_entries.index("verifier/m_verifier_main.hl")
    expected = tuple(path for path, _ in ENTRIES)
    if tuple(canonical_entries[verifier_index + 1 : verifier_index + 4]) != expected:
        return fail("canonical_partition")

    driver = DRIVER.read_text(encoding="utf-8")
    driver_entries = tuple(re.findall(r'(?m)^needs "([^"]+)";;$', driver))
    if driver_entries != expected:
        return fail("driver_partition")
    for logical, digest in ENTRIES:
        if driver.count(f'("{pathlib.Path(logical).name}",') != 1 or digest not in driver:
            return fail(f"driver_identity:{logical}")
    if (
        "cv_compute_exact_interval_matan_series" in driver
        or "historical_dihedral_first_order_sound" in driver
        or "registered_original_prove" in driver
    ):
        return fail("driver_scope")

    predecessor_log = (PREDECESSOR / "runtime.log").read_text(
        encoding="utf-8", errors="replace"
    )
    if (
        predecessor_log.count("- Finished loading verifier/m_verifier_main.hl") != 1
        or predecessor_log.count("CANDLE_FLYSPECK_V674_M_VERIFIER_CHECKPOINT_READY")
        != 1
    ):
        return fail("predecessor_log")

    print("status=0")
    print(f"planned_top_level_load_count={len(ENTRIES)}")
    print("deferred_support_count=12")
    print(f"driver_sha256={sha256(DRIVER)}")
    print(f"canonical_support_sha256={sha256(CANONICAL)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
