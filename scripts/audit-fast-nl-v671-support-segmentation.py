#!/usr/bin/env python3
"""Audit measured support cost and mandatory reusable Taylor boundaries."""

from __future__ import annotations

import hashlib
import pathlib
import re


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
TIMEOUT_LOG = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v670-fast-nl-runtime-surface-support-probe-dev-001/runtime.log"
)
FAILED_MARKER = TIMEOUT_LOG.parent / "CHECKPOINT-FAILED"
STAGE1 = PROJECT / "tools/fast_nl_v671_taylor_interval_stage.ml"
STAGE2 = PROJECT / "tools/fast_nl_v672_multivariate_taylor_stage.ml"
CURRENT_PREDECESSOR = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "postaction49-v669/checkpoint.receipt"
)
HISTORICAL_INPUTS = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "cv-flyspeck-taylor-analytic-base-checkpoint-v2-16g-dev-001/"
    "input-files.sha256"
)
HISTORICAL_SEAL = HISTORICAL_INPUTS.parent / "checkpoint-seal.receipt"


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
        TIMEOUT_LOG,
        FAILED_MARKER,
        STAGE1,
        STAGE2,
        CURRENT_PREDECESSOR,
        HISTORICAL_INPUTS,
        HISTORICAL_SEAL,
    ):
        if not path.is_file():
            return fail(f"missing:{path}")

    log = TIMEOUT_LOG.read_text(encoding="utf-8", errors="replace")
    error_count = len(
        re.findall(
            r"ERROR:|EXCEPTION:|Parsing failed|Program exited|Fatal error|Out of memory",
            log,
        )
    )
    if (
        error_count != 0
        or len(re.findall(r"^- Loading ", log, flags=re.MULTILINE)) != 43
        or len(re.findall(r"^- Finished loading ", log, flags=re.MULTILINE)) != 40
        or log.count("CANDLE_FLYSPECK_V670_RUNTIME_SYMBOL_SURFACE_OK identifiers=9")
        != 1
        or log.count("- Finished loading taylor/theory/taylor_interval-compiled.hl")
        != 1
        or log.count(
            "- Loading /project/worktrees/flyspeck-cv-nonlinear-closure-v11-manifest-d6/"
            "formal_ineqs/taylor/theory/multivariate_taylor-compiled.hl"
        )
        != 1
        or "- Finished loading taylor/theory/multivariate_taylor-compiled.hl" in log
        or FAILED_MARKER.read_text(encoding="utf-8").strip()
        != "restored runtime exited before the requested boundary"
    ):
        return fail("timeout_evidence")

    stage1 = STAGE1.read_text(encoding="utf-8")
    stage2 = STAGE2.read_text(encoding="utf-8")
    stage1_required = (
        'needs "arith_options.hl";;',
        "Arith_options.base := 200;;",
        'needs "taylor/theory/taylor_interval-compiled.hl";;',
        "CANDLE_FLYSPECK_V671_TAYLOR_INTERVAL_CHECKPOINT_READY",
    )
    stage2_required = (
        'needs "taylor/theory/multivariate_taylor-compiled.hl";;',
        "CANDLE_FLYSPECK_V672_MULTIVARIATE_TAYLOR_CHECKPOINT_READY",
    )
    if (
        any(stage1.count(fragment) != 1 for fragment in stage1_required)
        or "multivariate_taylor-compiled.hl" in stage1
        or "m_verifier" in stage1
        or any(stage2.count(fragment) != 1 for fragment in stage2_required)
        or "m_verifier" in stage2
    ):
        return fail("stage_contract")

    current = receipt(CURRENT_PREDECESSOR)
    historical = receipt(HISTORICAL_SEAL)
    historical_inputs = HISTORICAL_INPUTS.read_text(encoding="utf-8")
    current_checkpoint = current.get("checkpoint")
    if (
        not current_checkpoint
        or current_checkpoint in historical_inputs
        or historical.get("receipt_kind") != "cv-setup-checkpoint"
        or historical.get("release_evidence") != "false"
    ):
        return fail("historical_checkpoint_lineage")

    print("status=0")
    print("timed_support_load_count=43")
    print("timed_support_finish_count=40")
    print("timed_support_error_count=0")
    print("completed_expensive_stage_count=1")
    print("open_expensive_stage_count=1")
    print("required_checkpoint_stage_count=2")
    print("historical_checkpoint_reusable_count=0")
    print(f"timeout_log_sha256={sha256(TIMEOUT_LOG)}")
    print(f"stage1_sha256={sha256(STAGE1)}")
    print(f"stage2_sha256={sha256(STAGE2)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
