#!/usr/bin/env python3
"""Generic fail-closed audit for a finalized and fresh-restarted checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, type=pathlib.Path)
    parser.add_argument("--receipt-kind", required=True)
    parser.add_argument("--driver-sha256", required=True)
    parser.add_argument("--marker", required=True)
    parser.add_argument("--required-log", action="append", default=[])
    parser.add_argument("--probe", required=True, type=pathlib.Path)
    parser.add_argument("--probe-marker", required=True)
    args = parser.parse_args()

    required = (
        args.base / "CHECKPOINT-READY",
        args.base / "checkpoint.receipt",
        args.base / "runtime.log",
        args.probe / "PROBE-PASSED",
        args.probe / "restart-probe.receipt",
        args.probe / "runtime.log",
    )
    for path in required:
        if not path.is_file():
            return fail(f"missing:{path}")
    if (args.base / "CHECKPOINT-FAILED").exists() or (
        args.probe / "PROBE-FAILED"
    ).exists():
        return fail("failure_marker")

    base_receipt = receipt(args.base / "checkpoint.receipt")
    checkpoint_text = base_receipt.get("checkpoint", "")
    checkpoint = pathlib.Path(checkpoint_text)
    if not checkpoint.is_file():
        return fail("missing_checkpoint")
    actual_sha = sha256(checkpoint)
    if (
        base_receipt.get("receipt_kind") != args.receipt_kind
        or base_receipt.get("release_evidence") != "false"
        or base_receipt.get("driver_mode") != "direct"
        or base_receipt.get("driver_sha256") != args.driver_sha256
        or base_receipt.get("expected_marker") != args.marker
        or base_receipt.get("checkpoint_sha256") != actual_sha
        or base_receipt.get("checkpoint_size_bytes") != str(checkpoint.stat().st_size)
    ):
        return fail("base_receipt")

    base_log = (args.base / "runtime.log").read_text(
        encoding="utf-8", errors="replace"
    )
    teardown = "Message: read invalid message, _magicBits mismatch."
    if (
        len(re.findall(r"(?m)^CANDLE_RESTORE_INPUT_ACK nonce=[0-9a-f]{64}$", base_log))
        != 1
        or base_log.count(args.marker) != 1
        or base_log.count(teardown) != 1
        or base_log.index(teardown) < base_log.index(args.marker)
        or any(base_log.count(fragment) != 1 for fragment in args.required_log)
    ):
        return fail("base_log_contract")

    probe_receipt = receipt(args.probe / "restart-probe.receipt")
    probe_log = (args.probe / "runtime.log").read_text(
        encoding="utf-8", errors="replace"
    )
    ack = probe_receipt.get("fresh_ack", "")
    if (
        probe_receipt.get("receipt_kind")
        != "development-fast-nl-checkpoint-restart-probe-v1"
        or probe_receipt.get("release_evidence") != "false"
        or probe_receipt.get("base_checkpoint") != checkpoint_text
        or probe_receipt.get("base_checkpoint_sha256") != actual_sha
        or not ack
        or probe_receipt.get("expected_marker") != args.probe_marker
        or probe_log.count(ack) != 1
        or probe_log.count(args.probe_marker) != 1
        or "ERROR:" in probe_log
    ):
        return fail("restart_probe_contract")

    elapsed = probe_receipt.get("elapsed_seconds", "")
    if not elapsed.isdigit() or not 0 < int(elapsed) <= 600:
        return fail("restart_elapsed")

    print("status=0")
    print("checkpoint_count=1")
    print("fresh_restart_count=1")
    print(f"required_completion_count={len(args.required_log)}")
    print(f"checkpoint_sha256={actual_sha}")
    print(f"restart_elapsed_seconds={elapsed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
