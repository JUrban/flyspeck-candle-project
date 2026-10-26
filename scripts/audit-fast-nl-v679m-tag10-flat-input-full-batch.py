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
    "post-tag10-flat-full-batch-v679m"
)
RUNNER = PROJECT / "scripts/run-fast-nl-v679m-tag10-flat-input-full-batch.sh"
DRIVER = PROJECT / "tools/fast_nl_v679m_tag10_flat_input_full_batch.ml"
PREDECESSOR_AUDIT = (
    PROJECT / "scripts/audit-fast-nl-v679l-import-prepared-input-flat.py"
)
BASE_SHA256 = "07c921204ebe48ad01ffce1c8484785af27b767f4df74500fff058eedfb3946d"
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
        PREDECESSOR_AUDIT,
        BASE / "CHECKPOINT-READY",
        BASE / "checkpoint.receipt",
        BASE / "checkpoint.sha256",
    )
    if any(not path.is_file() or path.is_symlink() for path in required):
        return fail("missing_or_symlinked_preflight_authority")
    if not os.access(RUNNER, os.X_OK):
        return fail("runner_not_executable")
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

    runner = RUNNER.read_text(encoding="utf-8")
    driver = DRIVER.read_text(encoding="utf-8")
    if (
        runner.count("FAST_NL_PHASE_TIMEOUT_SECONDS=1200") != 1
        or runner.count("audit-fast-nl-v679m-tag10-flat-input-full-batch.py") != 1
        or runner.count("$audit") != 2
        or runner.count("run-fast-nl-restored-checkpoint-phase-v1.sh") != 1
        or driver.count("candle_q_dim_analytic_jet_compute") != 1
        or driver.count("candle_v679l_checked_call") != 2
        or driver.count(MARKER) != 1
        or driver.count("axioms ()") != 2
        or "new_axiom" in driver
    ):
        return fail("full_batch_source_contract")

    print("status=0")
    print("cells=4173")
    print("expected_result=1")
    print("numerical_compute_count=1")
    print("timeout_seconds=1200")
    print(f"predecessor_checkpoint_sha256={BASE_SHA256}")
    return 0


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
