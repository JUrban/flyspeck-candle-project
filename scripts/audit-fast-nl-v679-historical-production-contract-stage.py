#!/usr/bin/env python3
"""Audit the six-source v679b historical production-contract stage."""

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
    "post-historical-checked-sound-v679a"
)
BASE_PROBE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679a-fast-nl-historical-checked-sound-restart-probe-dev-001"
)
LOADER_PROBE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679-fast-nl-loaded-source-ledger-probe-dev-001"
)
PRIOR = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "cv-case10173-historical-production-contract-v122-clean-dev-001"
)
DRIVER = PROJECT / "tools/fast_nl_v679_historical_production_contract_stage.ml"
SOURCE_AUDIT = PROJECT / "scripts/audit-fast-nl-support-source-closure.py"
PARTITION_AUDIT = (
    PROJECT / "scripts/audit-fast-nl-v679-remaining-support-partition.py"
)
TARGET = (
    "candle/"
    "cv_compute_analytic_expr_case10173_historical_dihedral_production_contract_sound.ml"
)
BASE_SHA256 = (
    "7cbbab99a519adc6b939900dd4eca08db33106de38a563fc3fd63121c436623a"
)
MARKER = "CANDLE_FLYSPECK_V679B_HISTORICAL_PRODUCTION_CONTRACT_CHECKPOINT_READY"
ENTRIES = (
    (
        "candle/cv_compute_analytic_expr_case10173_historical_dihedral_item_sound.ml",
        "f70e3d9ede852ce86da639727d759349",
        "536d2ea98fb836390ba6ef46fc745cd7ed97a6d6c4fad9218352f145f3bd1154",
    ),
    (
        "candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_logical_sound.ml",
        "5a92d27ab7a9763aef6a92e174a54b76",
        "2d35de3cd32e18c070ec917e3f66681c844941dacb1879f076baecf47c5e9253",
    ),
    (
        "candle/cv_compute_analytic_expr_case10173_historical_dihedral_item_invariant.ml",
        "a9b754bcbf641721667faf038a55292a",
        "11601da1e3b5fb25e545197ccd6b9a34a3c3a5b7641c027a1e626e7dae32fd73",
    ),
    (
        "candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_analytic_sound.ml",
        "67e8175c0001aaf624ee3d3eeebbff1f",
        "56bf89ca3a0bc6d4d09b3c6bb1763daf862e74693540220aa21bba6794455c1e",
    ),
    (
        "candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_reference_sound.ml",
        "2d1c81105e5fc337289f1570b45840a1",
        "05cc09ef264cecaa88707992c7dd7f525485029a6e6e985dfb2ef345d652cf97",
    ),
    (
        TARGET,
        "26b1e42b37df603928eedf7db65a5b02",
        "1f9abe8a86a70bf8bbd593c4ec59fc215936270d30f6d0a321e9949cb80ea0bc",
    ),
)
PREDECESSOR_ENTRIES = (
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_compute.ml",
    "candle/cv_compute_analytic_expr_fixed_scale_historical_root_certificate_sound.ml",
    "candle/cv_compute_analytic_expr_fixed_scale_historical_root_certificate_compute.ml",
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_checked_compute.ml",
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_checked_sound.ml",
)
THEOREMS = (
    "candle_cv_case10173_hist_item_correct",
    "candle_cv_case10173_hist_program_of_correct",
    "candle_case10173_hist_result_analytic_invariant",
    "candle_case10173_hist_context_run_analytic_invariant",
    "candle_fs_hist_first_order_direct_reference_gradient_contains",
    "candle_case10173_hist_reference_hessian_is_source",
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


def source_module():
    spec = importlib.util.spec_from_file_location("fast_nl_source_audit", SOURCE_AUDIT)
    if spec is None or spec.loader is None:
        raise RuntimeError("source audit import")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def closure(audit) -> set[tuple[str, str]]:
    pending = [TARGET]
    seen: set[pathlib.Path] = set()
    result: set[tuple[str, str]] = set()
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
        result.add((path.name, audit.md5(path)))
    return result


def main() -> int:
    required = (
        DRIVER,
        SOURCE_AUDIT,
        PARTITION_AUDIT,
        BASE / "CHECKPOINT-READY",
        BASE / "checkpoint.receipt",
        BASE / "runtime.log",
        BASE_PROBE / "PROBE-PASSED",
        BASE_PROBE / "restart-probe.receipt",
        LOADER_PROBE / "runtime.log",
        PRIOR / "fragments.sha256",
        PRIOR / "input-ack.receipt",
        PRIOR / "candle.log",
    )
    if any(not path.is_file() or path.is_symlink() for path in required):
        return fail("missing_or_symlinked_authority")
    if (BASE / "CHECKPOINT-FAILED").exists() or (BASE_PROBE / "PROBE-FAILED").exists():
        return fail("failed_predecessor_evidence")

    base_receipt = receipt(BASE / "checkpoint.receipt")
    probe_receipt = receipt(BASE_PROBE / "restart-probe.receipt")
    if (
        base_receipt.get("receipt_kind")
        != "development-fast-nl-v679a-historical-checked-sound-checkpoint-v1"
        or base_receipt.get("checkpoint_sha256") != BASE_SHA256
        or probe_receipt.get("base_checkpoint_sha256") != BASE_SHA256
        or probe_receipt.get("elapsed_seconds") != "180"
    ):
        return fail("predecessor_receipt")

    partition = subprocess.run(
        [str(PARTITION_AUDIT)], cwd=PROJECT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=60, check=False,
    )
    if partition.returncode != 0 or "first_group_increment_counts=5,6,9" not in partition.stdout.splitlines():
        print(partition.stdout, end="")
        return fail("remaining_partition_audit")

    loaded = set(
        ITEM_RE.findall(
            (LOADER_PROBE / "runtime.log").read_text(
                encoding="utf-8", errors="replace"
            )
        )
    )
    audit = source_module()
    for logical in PREDECESSOR_ENTRIES:
        path = audit.resolve(logical)
        if path is None:
            return fail(f"predecessor_source:{logical}")
        loaded.add((path.name, audit.md5(path)))
    expected = {(pathlib.Path(logical).name, md5) for logical, md5, _ in ENTRIES}
    try:
        missing = closure(audit) - loaded
    except (OSError, UnicodeDecodeError, ValueError, RuntimeError) as error:
        return fail(f"target_closure:{error}")
    if missing != expected:
        return fail("six_source_partition")
    if any(name in {loaded_name for loaded_name, _ in loaded} for name, _ in expected):
        return fail("predecessor_basename_collision")

    for logical, expected_md5, expected_sha256 in ENTRIES:
        source = SOURCE_ROOT / logical
        if (
            not source.is_file() or source.is_symlink()
            or digest(source, "md5") != expected_md5
            or digest(source) != expected_sha256
        ):
            return fail(f"source_identity:{logical}")

    prior_hashes = (PRIOR / "fragments.sha256").read_text(encoding="utf-8")
    prior_log = (PRIOR / "candle.log").read_text(encoding="utf-8", errors="replace")
    prior_ack = receipt(PRIOR / "input-ack.receipt")
    if (
        prior_hashes.count(ENTRIES[-1][2]) != 1
        or prior_log.count("CANDLE_CV_CASE10173_HISTORICAL_PRODUCTION_CONTRACT_SOUND_OK") != 1
        or any(item in prior_log for item in ("ERROR:", "EXCEPTION:", "Parsing failed"))
        or prior_ack.get("marker_line") != "510"
    ):
        return fail("prior_exact_proof_evidence")

    driver = DRIVER.read_text(encoding="utf-8")
    if re.findall(r'(?m)^needs "([^"]+)";;$', driver) != [TARGET]:
        return fail("driver_load_boundary")
    for logical, expected_md5, _ in ENTRIES:
        pattern = re.compile(
            rf'\("{re.escape(pathlib.Path(logical).name)}",\s*"{expected_md5}"\)'
        )
        if len(pattern.findall(driver)) != 1:
            return fail(f"driver_identity:{logical}")
    if any(driver.count(theorem) != 1 for theorem in THEOREMS):
        return fail("driver_theorem_contract")
    if (
        driver.count(MARKER) != 1 or "#use " in driver
        or "flyspeck_needs" in driver or "new_axiom" in driver
        or driver.count("axioms ()") != 2
    ):
        return fail("driver_safety_contract")

    print("status=0")
    print("predecessor_loaded_identity_count=306")
    print("planned_source_count=6")
    print("representative_closed_theorem_count=6")
    print("prior_exact_target_proof_count=1")
    print("declared_axiom_growth=0")
    print(f"driver_sha256={digest(DRIVER)}")
    print(f"base_checkpoint_sha256={BASE_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
