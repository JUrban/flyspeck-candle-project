#!/usr/bin/env python3
"""Fail closed while the v677t historical-sound SPECL defect is unresolved."""

from __future__ import annotations

import pathlib


RUN = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-historical-sound-v677t"
)


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def main() -> int:
    log_path = RUN / "runtime.log"
    failed_path = RUN / "CHECKPOINT-FAILED"
    if not log_path.is_file() or not failed_path.is_file():
        return fail("missing_v677t_failure_evidence")
    log = log_path.read_text(encoding="utf-8", errors="replace")
    if log.count('EXCEPTION: Failure "SPECL"') != 1:
        return fail("v677t_specl_exception_count")
    if "CANDLE_FLYSPECK_V677_HISTORICAL_SOUND_CHECKPOINT_READY" in log:
        return fail("v677t_unexpected_success_marker")
    print("status=1")
    print("failed_run_exception_count=1")
    print("unresolved_historical_sound_specl_count=1")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
