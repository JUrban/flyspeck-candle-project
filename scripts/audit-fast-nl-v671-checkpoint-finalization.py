#!/usr/bin/env python3
"""Validate the v671 checkpoint and its independent fresh-restart probe."""

from __future__ import annotations

import hashlib
import datetime
import pathlib
import re


BASE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "posttaylor-interval-v671"
)
PROBE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v671-fast-nl-taylor-interval-restart-probe-dev-002"
)
SHORT_PROBE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v671-fast-nl-taylor-interval-restart-probe-dev-001"
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
        PROBE / "runtime.log",
        SHORT_PROBE / "PROBE-FAILED",
        SHORT_PROBE / "runtime.log",
    )
    for path in required:
        if not path.is_file():
            return fail(f"missing:{path}")
    if (BASE / "CHECKPOINT-FAILED").exists():
        return fail("failure_marker")
    if (
        (SHORT_PROBE / "PROBE-FAILED").read_text(encoding="utf-8").strip()
        != "restart probe runtime exited before fresh markers"
        or (SHORT_PROBE / "runtime.log").stat().st_size != 0
    ):
        return fail("short_probe_evidence")

    base_receipt = receipt(BASE / "checkpoint.receipt")
    checkpoint_text = base_receipt.get("checkpoint", "")
    checkpoint = pathlib.Path(checkpoint_text)
    if not checkpoint.is_file():
        return fail("missing_checkpoint")
    actual_sha = sha256(checkpoint)
    if (
        base_receipt.get("receipt_kind")
        != "development-fast-nl-v671-taylor-interval-checkpoint-v1"
        or base_receipt.get("release_evidence") != "false"
        or base_receipt.get("driver_mode") != "direct"
        or base_receipt.get("expected_marker")
        != "CANDLE_FLYSPECK_V671_TAYLOR_INTERVAL_CHECKPOINT_READY"
        or base_receipt.get("checkpoint_sha256") != actual_sha
        or base_receipt.get("checkpoint_size_bytes") != str(checkpoint.stat().st_size)
    ):
        return fail("base_receipt")

    base_log = (BASE / "runtime.log").read_text(encoding="utf-8", errors="replace")
    ack_lines = re.findall(r"(?m)^CANDLE_RESTORE_INPUT_ACK nonce=[0-9a-f]{64}$", base_log)
    marker = "CANDLE_FLYSPECK_V671_TAYLOR_INTERVAL_CHECKPOINT_READY"
    teardown = "Message: read invalid message, _magicBits mismatch."
    if (
        len(ack_lines) != 1
        or base_log.count(marker) != 1
        or base_log.count("- Finished loading taylor/theory/taylor_interval-compiled.hl")
        != 1
        or base_log.count(teardown) != 1
        or base_log.index(teardown) < base_log.index(marker)
    ):
        return fail("base_log_contract")

    probe_log = (PROBE / "runtime.log").read_text(encoding="utf-8", errors="replace")
    probe_nonce = hashlib.sha256(f"{actual_sha}\n{PROBE}\n".encode()).hexdigest()
    expected_ack = f"CANDLE_RESTORE_INPUT_ACK nonce={probe_nonce}"
    expected_marker = "CANDLE_FLYSPECK_V671_RESTART_PROBE_OK"
    if (
        probe_log.count(expected_ack) != 1
        or probe_log.count(expected_marker) != 1
        or re.search(
            r"ERROR:|EXCEPTION:|Parsing failed|Program exited|Fatal error|Out of memory",
            probe_log,
        )
    ):
        return fail("restart_probe_contract")

    coordinator_logs = list((PROBE / "dmtcp-tmp").glob("**/dmtcp_coordinator.*.log"))
    if len(coordinator_logs) != 1:
        return fail("restart_coordinator_log_count")
    coordinator_log = coordinator_logs[0].read_text(encoding="utf-8", errors="replace")
    started_match = re.search(r"\[([0-9T:.+-]+), [0-9]+, [0-9]+, INFO\]", coordinator_log)
    if not started_match:
        return fail("restart_start_time")
    started = datetime.datetime.fromisoformat(started_match.group(1)).timestamp()
    restart_elapsed = round((PROBE / "runtime.log").stat().st_mtime - started)
    if not 180 < restart_elapsed < 600:
        return fail("restart_elapsed_range")

    print("status=0")
    print("checkpoint_count=1")
    print("fresh_restart_count=1")
    print("short_probe_timeout_count=1")
    print("post_marker_teardown_diagnostic_count=1")
    print(f"checkpoint_sha256={actual_sha}")
    print(f"restart_elapsed_seconds={restart_elapsed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
