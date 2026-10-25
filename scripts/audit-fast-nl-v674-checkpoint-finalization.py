#!/usr/bin/env python3
"""Validate the v674 m_verifier checkpoint and fresh restart."""

from __future__ import annotations

import hashlib
import pathlib
import re


BASE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-m-verifier-v674"
)
PROBE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v674-fast-nl-m-verifier-restart-probe-dev-001"
)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
        BASE / "CHECKPOINT-READY",
        BASE / "checkpoint.receipt",
        BASE / "runtime.log",
        PROBE / "PROBE-PASSED",
        PROBE / "restart-probe.receipt",
        PROBE / "runtime.log",
    )
    for path in required:
        if not path.is_file():
            return fail(f"missing:{path}")
    if (BASE / "CHECKPOINT-FAILED").exists() or (PROBE / "PROBE-FAILED").exists():
        return fail("failure_marker")

    base_receipt = receipt(BASE / "checkpoint.receipt")
    checkpoint_text = base_receipt.get("checkpoint", "")
    checkpoint = pathlib.Path(checkpoint_text)
    if not checkpoint.is_file():
        return fail("missing_checkpoint")
    actual_sha = sha256(checkpoint)
    if (
        base_receipt.get("receipt_kind")
        != "development-fast-nl-v674-m-verifier-checkpoint-v1"
        or base_receipt.get("release_evidence") != "false"
        or base_receipt.get("driver_mode") != "direct"
        or base_receipt.get("driver_sha256")
        != "5f3558aae7b427c9fbef6a7bf48a70153189527fe2d52a3747f9fdc2d01d58b8"
        or base_receipt.get("expected_marker")
        != "CANDLE_FLYSPECK_V674_M_VERIFIER_CHECKPOINT_READY"
        or base_receipt.get("checkpoint_sha256") != actual_sha
        or base_receipt.get("checkpoint_size_bytes") != str(checkpoint.stat().st_size)
    ):
        return fail("base_receipt")

    base_log = (BASE / "runtime.log").read_text(encoding="utf-8", errors="replace")
    marker = "CANDLE_FLYSPECK_V674_M_VERIFIER_CHECKPOINT_READY"
    teardown = "Message: read invalid message, _magicBits mismatch."
    if (
        len(re.findall(r"(?m)^CANDLE_RESTORE_INPUT_ACK nonce=[0-9a-f]{64}$", base_log))
        != 1
        or base_log.count("val List.flatten = <fun>") != 1
        or base_log.count("- Finished loading verifier/m_verifier_main.hl") != 1
        or base_log.count(marker) != 1
        or base_log.count(teardown) != 1
        or base_log.index(teardown) < base_log.index(marker)
    ):
        return fail("base_log_contract")

    probe_receipt = receipt(PROBE / "restart-probe.receipt")
    probe_log = (PROBE / "runtime.log").read_text(encoding="utf-8", errors="replace")
    ack = probe_receipt.get("fresh_ack", "")
    probe_marker = probe_receipt.get("expected_marker", "")
    if (
        probe_receipt.get("receipt_kind")
        != "development-fast-nl-checkpoint-restart-probe-v1"
        or probe_receipt.get("release_evidence") != "false"
        or probe_receipt.get("base_checkpoint") != checkpoint_text
        or probe_receipt.get("base_checkpoint_sha256") != actual_sha
        or not ack
        or probe_marker != "CANDLE_FLYSPECK_V674_M_VERIFIER_RESTART_PROBE_OK"
        or probe_log.count(ack) != 1
        or probe_log.count(probe_marker) != 1
        or "ERROR:" in probe_log
    ):
        return fail("restart_probe_contract")

    elapsed = probe_receipt.get("elapsed_seconds", "")
    if not elapsed.isdigit() or not 0 < int(elapsed) <= 600:
        return fail("restart_elapsed")

    print("status=0")
    print("checkpoint_count=1")
    print("fresh_restart_count=1")
    print("list_flatten_export_count=1")
    print("m_verifier_completion_count=1")
    print(f"checkpoint_sha256={actual_sha}")
    print(f"restart_elapsed_seconds={elapsed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
