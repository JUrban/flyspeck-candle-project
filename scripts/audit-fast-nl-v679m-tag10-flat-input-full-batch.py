#!/usr/bin/env python3
"""Preflight and authenticate the bounded tag-10 numerical checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import subprocess


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
BASE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-tag10-flat-input-v679l"
)
OUTPUT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-tag10-flat-full-batch-v679m-v2"
)
FAILED = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-tag10-flat-full-batch-v679m"
)
RUNNER = PROJECT / "scripts/run-fast-nl-v679m-tag10-flat-input-full-batch.sh"
DRIVER = PROJECT / "tools/fast_nl_v679m_tag10_flat_input_full_batch.ml"
SURFACE_DRIVER = PROJECT / "tools/fast_nl_v679m_kernel_compute_surface_probe.ml"
PREDECESSOR_AUDIT = (
    PROJECT / "scripts/audit-fast-nl-v679l-import-prepared-input-flat.py"
)
SURFACE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679m-fast-nl-kernel-compute-surface-probe-dev-001"
)
BASE_SHA256 = "07c921204ebe48ad01ffce1c8484785af27b767f4df74500fff058eedfb3946d"
FAILED_LOG_SHA256 = "95ef45b338b808133516a70440b210f835a19a980fc878677d6e308ba159fb7d"
TIMED_OUT_LOG_SHA256 = "45d156e6060ba585444ca9e8a4a34615675749f13000598330133b008ef2ae63"
SURFACE_LOG_SHA256 = "1e29b9bd1d7ccddfae55545aa511988cc16960179015448210897865b67cc773"
SURFACE_MARKER = (
    "CANDLE_FLYSPECK_V679M_KERNEL_COMPUTE_SURFACE_OK "
    "DEVELOPMENT_NON_RELEASE result=1 assumptions=0"
)
MARKER = (
    "CANDLE_FLYSPECK_V679M_TAG10_FLAT_INPUT_FULL_BATCH_READY "
    "DEVELOPMENT_NON_RELEASE cells=4173 result=1 "
    "authenticated_aux_roots=16692 assumptions=0 axiom_growth=0"
)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fields(path: pathlib.Path) -> dict[str, str]:
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def preflight() -> int:
    required = (
        RUNNER,
        DRIVER,
        SURFACE_DRIVER,
        PREDECESSOR_AUDIT,
        BASE / "CHECKPOINT-READY",
        BASE / "checkpoint.receipt",
        BASE / "checkpoint.sha256",
        FAILED / "CHECKPOINT-FAILED",
        FAILED / "runtime.log",
        SURFACE / "PROBE-PASSED",
        SURFACE / "input-probe.receipt",
        SURFACE / "runtime.log",
        OUTPUT / "CHECKPOINT-FAILED",
        OUTPUT / "runtime.log",
    )
    if any(not path.is_file() or path.is_symlink() for path in required):
        return fail("missing_or_symlinked_preflight_authority")
    if not os.access(RUNNER, os.X_OK):
        return fail("runner_not_executable")
    failed_log = FAILED / "runtime.log"
    failed_text = failed_log.read_text(encoding="utf-8", errors="replace")
    if (
        sha256(failed_log) != FAILED_LOG_SHA256
        or failed_text.count(
            "ERROR: Undefined module: Candle_cv_analytic_expr_jet_prove"
        )
        != 1
        or "v679m-tag10-flat-input-full-compute-begin" in failed_text
        or "restored runtime reported an error before the requested boundary"
        not in (FAILED / "CHECKPOINT-FAILED").read_text(encoding="utf-8")
    ):
        return fail("full_batch_namespace_failure_contract")
    surface_receipt = fields(SURFACE / "input-probe.receipt")
    surface_log_path = SURFACE / "runtime.log"
    surface_log = surface_log_path.read_text(encoding="utf-8", errors="replace")
    if (
        sha256(surface_log_path) != SURFACE_LOG_SHA256
        or surface_receipt.get("base_checkpoint_sha256") != BASE_SHA256
        or surface_receipt.get("driver_sha256") != sha256(SURFACE_DRIVER)
        or surface_receipt.get("expected_marker") != SURFACE_MARKER
        or int(surface_receipt.get("elapsed_seconds", "601")) > 600
        or surface_log.count(SURFACE_MARKER) != 1
        or "|- " not in surface_log
        or any(text in surface_log for text in ("EXCEPTION:", "ERROR:", "Parsing failed"))
    ):
        return fail("kernel_compute_surface_probe_contract")
    predecessor = subprocess.run(
        [str(PREDECESSOR_AUDIT)],
        cwd=PROJECT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
        check=False,
    )
    if (
        predecessor.returncode != 0
        or predecessor.stdout.splitlines().count("status=0") != 2
        or f"checkpoint_sha256={BASE_SHA256}" not in predecessor.stdout
    ):
        return fail("prepared_input_predecessor_contract")

    timed_out_log_path = OUTPUT / "runtime.log"
    timed_out_log = timed_out_log_path.read_text(
        encoding="utf-8", errors="replace"
    )
    if (
        sha256(timed_out_log_path) != TIMED_OUT_LOG_SHA256
        or timed_out_log.count("v679m-tag10-flat-input-full-compute-begin") != 1
        or "v679m-tag10-flat-input-full-compute-end" in timed_out_log
        or MARKER in timed_out_log
        or any(
            text in timed_out_log
            for text in ("EXCEPTION:", "ERROR:", "Parsing failed")
        )
        or (OUTPUT / "CHECKPOINT-FAILED").read_text(encoding="utf-8").strip()
        != "restored runtime exited before the requested boundary"
    ):
        return fail("full_batch_timeout_evidence_contract")

    runner = RUNNER.read_text(encoding="utf-8")
    driver = DRIVER.read_text(encoding="utf-8")
    surface_driver = SURFACE_DRIVER.read_text(encoding="utf-8")
    if (
        runner.count("FAST_NL_PHASE_TIMEOUT_SECONDS=1200") != 1
        or runner.count("audit-fast-nl-v679m-tag10-flat-input-full-batch.py") != 1
        or runner.count("$audit") != 2
        or runner.count("run-fast-nl-restored-checkpoint-phase-v1.sh") != 1
        or driver.count("let theorem = Kernel.compute") != 1
        or "Candle_cv_analytic_expr_jet_prove" in driver
        or driver.count("let candle_v679m_compute equations tm") != 1
        or surface_driver.count("let theorem = Kernel.compute") != 1
        or "Candle_cv_analytic_expr_jet_prove" in surface_driver
        or "if hyp theorem <> [] then" not in driver
        or "if hyp theorem <> [] then" not in surface_driver
        or driver.count("candle_v679l_checked_call") != 2
        or driver.count(MARKER) != 1
        or driver.count("axioms ()") != 2
        or "new_axiom" in driver
    ):
        return fail("full_batch_source_contract")

    # The runtime's registered dispatcher is frozen against the pre-matan
    # private-tag-9 equation environment.  This restored state deliberately
    # carries the corrected private-tag-10 equations, so exact ceq equality
    # makes a fast hit impossible and the observed computation is generic
    # fallback.  Do not retry or increase the timeout: rebuild and positively
    # probe the registered dispatcher against the corrected identity first.
    return fail("registered_fast_dispatch_tag10_identity_mismatch")


def postflight() -> int:
    if preflight() != 0:
        return 1
    required = (
        OUTPUT / "CHECKPOINT-READY",
        OUTPUT / "checkpoint.receipt",
        OUTPUT / "checkpoint.sha256",
        OUTPUT / "runtime.log",
        OUTPUT / "runtime-log.sha256",
    )
    if any(not path.is_file() or path.is_symlink() for path in required):
        return fail("full_batch_checkpoint_missing")
    receipt = fields(OUTPUT / "checkpoint.receipt")
    if (
        receipt.get("receipt_kind")
        != "development-fast-nl-v679m-tag10-flat-full-batch-checkpoint-v1"
        or receipt.get("release_evidence") != "false"
        or receipt.get("driver_mode") != "source"
        or receipt.get("driver_sha256") != sha256(DRIVER)
        or receipt.get("expected_marker") != MARKER
    ):
        return fail("full_batch_checkpoint_receipt")
    base_checkpoint = pathlib.Path(receipt.get("base_checkpoint", ""))
    checkpoint = pathlib.Path(receipt.get("checkpoint", ""))
    if (
        not base_checkpoint.is_file()
        or base_checkpoint.is_symlink()
        or sha256(base_checkpoint) != BASE_SHA256
        or not checkpoint.is_file()
        or checkpoint.is_symlink()
        or sha256(checkpoint) != receipt.get("checkpoint_sha256")
    ):
        return fail("full_batch_checkpoint_identity")
    log_path = OUTPUT / "runtime.log"
    log = log_path.read_text(encoding="utf-8", errors="replace")
    if (
        log.count(MARKER) != 1
        or log.count("v679m-tag10-flat-input-full-compute-begin") != 1
        or log.count("v679m-tag10-flat-input-full-compute-end") != 1
        or sha256(log_path) not in (OUTPUT / "runtime-log.sha256").read_text(encoding="utf-8")
        or any(text in log for text in ("EXCEPTION:", "ERROR:", "Parsing failed", "Fatal error", "Out of memory"))
    ):
        return fail("full_batch_runtime_contract")

    print("status=0")
    print("cells=4173")
    print("result=1")
    print("assumptions=0")
    print("axiom_growth=0")
    print(f"checkpoint_sha256={sha256(checkpoint)}")
    print(f"runtime_log_sha256={sha256(log_path)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    arguments = parser.parse_args()
    return preflight() if arguments.preflight else postflight()


if __name__ == "__main__":
    raise SystemExit(main())
