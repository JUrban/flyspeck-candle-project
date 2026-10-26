#!/usr/bin/env python3
"""Audit the exact five-source v679a historical checked-sound stage."""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import re
import subprocess
import sys


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
SOURCE_ROOT = pathlib.Path("/project/worktrees/candle-direct-fast-nl-runtime-v1")
BASE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-direct-source-interface-v678"
)
LOADER_PROBE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679-fast-nl-loaded-source-ledger-probe-dev-001"
)
DRIVER = PROJECT / "tools/fast_nl_v679_historical_checked_sound_stage.ml"
SOURCE_AUDIT = PROJECT / "scripts/audit-fast-nl-support-source-closure.py"
PARTITION_AUDIT = (
    PROJECT / "scripts/audit-fast-nl-v679-remaining-support-partition.py"
)
TARGET = (
    "candle/"
    "cv_compute_analytic_expr_case10173_historical_dihedral_checked_sound.ml"
)
BASE_SHA256 = (
    "980d06be6fb7b418a018fddfd3cdd0bece5bd5f1ba83695264cc532dd742fce1"
)
MARKER = "CANDLE_FLYSPECK_V679A_HISTORICAL_CHECKED_SOUND_CHECKPOINT_READY"
ENTRIES = (
    (
        "candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_compute.ml",
        "2e8599bb01a8f4f6bc5831529ce5ed16",
        "13cfce9922ab65b95cd7c7bd0f02a1055dcdda5b12b3568363a0f6b06451c2cd",
    ),
    (
        "candle/cv_compute_analytic_expr_fixed_scale_historical_root_certificate_sound.ml",
        "7d22d16ee9e6f3ab5e168ad8558e3bc2",
        "1fb77c8796652bba92b0da73386f981ea7ff4a367eb865c2760b4783ebec124c",
    ),
    (
        "candle/cv_compute_analytic_expr_fixed_scale_historical_root_certificate_compute.ml",
        "2bd8e34a1d1f84e3b25488224fcf275d",
        "e31a76bb5c4fcfa73840025b6f5afbb54a18f7e190759440c988630b0ea3c2b3",
    ),
    (
        "candle/cv_compute_analytic_expr_case10173_historical_dihedral_checked_compute.ml",
        "f036de23d1b2264130e28727b1eb0766",
        "0a8d536bba53cf602de2beefcc3b1c97643e0870b76ac2a813532069d3dbfcb9",
    ),
    (
        "candle/cv_compute_analytic_expr_case10173_historical_dihedral_checked_sound.ml",
        "c8fa029635719e79a1c8f8ca0cf19678",
        "376b445901de8bcc32ec896039c3b90a4137c0f3cbdb6df1ad1c50136c6fbd1c",
    ),
)
THEOREMS = (
    "candle_cv_case10173_hist_program_run_compute",
    "candle_fs_hist_root_certificate_sound",
    "candle_cv_fs_hist_root_certificate_correct",
    "candle_cv_case10173_hist_checked_raw_jobs_accept",
    "candle_cv_case10173_hist_production_guard_correct",
    "candle_case10173_hist_root_record_semantics",
)
ITEM_RE = re.compile(
    r"CANDLE_FLYSPECK_V679_LOADED_SOURCE identity=([^:\s]+):([0-9a-f]{32})"
)


def digest(path: pathlib.Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


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


def load_source_audit():
    spec = importlib.util.spec_from_file_location("fast_nl_source_audit", SOURCE_AUDIT)
    if spec is None or spec.loader is None:
        raise RuntimeError("source audit import")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def target_closure(audit) -> set[tuple[str, str]]:
    pending = [TARGET]
    seen: set[pathlib.Path] = set()
    identities: set[tuple[str, str]] = set()
    while pending:
        request = pending.pop()
        path = audit.resolve(request)
        if path is None:
            raise RuntimeError(f"unresolved:{request}")
        if path in seen:
            continue
        seen.add(path)
        _, dependencies = audit.source_and_literal_loads(path)
        pending.extend(dependencies)
        identities.add((path.name, audit.md5(path)))
    return identities


def main() -> int:
    required = (
        DRIVER,
        SOURCE_AUDIT,
        PARTITION_AUDIT,
        BASE / "CHECKPOINT-READY",
        BASE / "checkpoint.receipt",
        BASE / "runtime.log",
        LOADER_PROBE / "PROBE-PASSED",
        LOADER_PROBE / "loaded-source-ledger.receipt",
        LOADER_PROBE / "runtime.log",
    )
    if any(not path.is_file() or path.is_symlink() for path in required):
        return fail("missing_or_symlinked_authority")
    if (BASE / "CHECKPOINT-FAILED").exists() or (
        LOADER_PROBE / "PROBE-FAILED"
    ).exists():
        return fail("failed_predecessor_evidence")

    base_receipt = receipt(BASE / "checkpoint.receipt")
    if (
        base_receipt.get("receipt_kind")
        != "development-fast-nl-v678-direct-source-interface-checkpoint-v1"
        or base_receipt.get("checkpoint_sha256") != BASE_SHA256
    ):
        return fail("predecessor_receipt")
    completed = subprocess.run(
        [str(PARTITION_AUDIT)],
        cwd=PROJECT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
        check=False,
    )
    required_partition = {
        "status=0",
        "authenticated_loaded_identity_count=301",
        "remaining_union_count=57",
        "first_group_increment_counts=5,6,9",
    }
    if completed.returncode != 0 or not required_partition.issubset(
        set(completed.stdout.splitlines())
    ):
        print(completed.stdout, end="")
        return fail("remaining_partition_audit")

    expected = {(pathlib.Path(logical).name, md5) for logical, md5, _ in ENTRIES}
    loaded_log = (LOADER_PROBE / "runtime.log").read_text(
        encoding="utf-8", errors="replace"
    )
    loaded = set(ITEM_RE.findall(loaded_log))
    try:
        missing = target_closure(load_source_audit()) - loaded
    except (OSError, UnicodeDecodeError, ValueError, RuntimeError) as error:
        return fail(f"target_closure:{error}")
    if missing != expected:
        return fail("five_source_partition")
    if any(name in {loaded_name for loaded_name, _ in loaded} for name, _ in expected):
        return fail("predecessor_basename_collision")

    for logical, expected_md5, expected_sha256 in ENTRIES:
        source = SOURCE_ROOT / logical
        if (
            not source.is_file()
            or source.is_symlink()
            or digest(source, "md5") != expected_md5
            or digest(source) != expected_sha256
        ):
            return fail(f"source_identity:{logical}")

    driver = DRIVER.read_text(encoding="utf-8")
    if re.findall(r'(?m)^needs "([^"]+)";;$', driver) != [TARGET]:
        return fail("driver_load_boundary")
    for logical, expected_md5, _ in ENTRIES:
        identity_pattern = re.compile(
            rf'\("{re.escape(pathlib.Path(logical).name)}",\s*'
            rf'"{expected_md5}"\)'
        )
        if len(identity_pattern.findall(driver)) != 1:
            return fail(f"driver_identity:{logical}")
    if any(driver.count(theorem) != 1 for theorem in THEOREMS):
        return fail("driver_theorem_contract")
    if (
        driver.count(MARKER) != 1
        or "#use " in driver
        or "flyspeck_needs" in driver
        or "new_axiom" in driver
        or driver.count("axioms ()") != 2
    ):
        return fail("driver_safety_contract")

    print("status=0")
    print("predecessor_loaded_identity_count=301")
    print("planned_source_count=5")
    print("representative_closed_theorem_count=6")
    print("declared_axiom_growth=0")
    print(f"driver_sha256={digest(DRIVER)}")
    print(f"base_checkpoint_sha256={BASE_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
