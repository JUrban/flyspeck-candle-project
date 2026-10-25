#!/usr/bin/env python3
"""Audit the observed List.flatten gap and the exact-runtime correction."""

from __future__ import annotations

import hashlib
import pathlib
import re


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
FAILED = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-m-verifier-v673"
)
PROBE_DRIVER = PROJECT / "tools/fast_nl_v674_list_flatten_probe.ml"
STAGE_DRIVER = PROJECT / "tools/fast_nl_v674_m_verifier_stage.ml"
CANDLE_OCAML = pathlib.Path(
    "/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/ocaml.ml"
)
PROBE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v674-fast-nl-list-flatten-probe-dev-001"
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
    required = (
        FAILED / "runtime.log",
        FAILED / "CHECKPOINT-FAILED",
        PROBE_DRIVER,
        STAGE_DRIVER,
        CANDLE_OCAML,
        PROBE / "PROBE-PASSED",
        PROBE / "input-probe.receipt",
        PROBE / "runtime.log",
    )
    for path in required:
        if not path.is_file():
            return fail(f"missing:{path}")

    failed_log = (FAILED / "runtime.log").read_text(encoding="utf-8", errors="replace")
    first_error = re.search(r"ERROR:.*", failed_log)
    if (
        not first_error
        or first_error.group(0) != "ERROR: Undefined variable: List.flatten at line 623"
        or failed_log.count("ERROR: Undefined variable: List.flatten") != 1
        or (FAILED / "CHECKPOINT-FAILED").read_text(encoding="utf-8").strip()
        != "restored runtime reported an error before the requested boundary"
    ):
        return fail("failure_evidence")

    intended = CANDLE_OCAML.read_text(encoding="utf-8")
    if intended.count("let flatten xss = concat xss") != 1:
        return fail("intended_runtime_semantics")

    module_patch = (
        "module List = struct\n"
        "  include List\n"
        "  let flatten xss = Cake.List.concat xss\n"
        "end;;"
    )
    semantic_probe = "List.flatten [[1;2];[];[3;4]] = [1;2;3;4]"
    for path in (PROBE_DRIVER, STAGE_DRIVER):
        text = path.read_text(encoding="utf-8")
        if text.count(module_patch) != 1 or text.count(semantic_probe) != 1:
            return fail(f"driver_contract:{path}")

    probe_receipt = receipt(PROBE / "input-probe.receipt")
    probe_log = (PROBE / "runtime.log").read_text(encoding="utf-8", errors="replace")
    ack = probe_receipt.get("fresh_ack", "")
    marker = probe_receipt.get("expected_marker", "")
    if (
        probe_receipt.get("receipt_kind")
        != "development-fast-nl-restored-input-probe-v1"
        or probe_receipt.get("release_evidence") != "false"
        or probe_receipt.get("driver_sha256") != sha256(PROBE_DRIVER)
        or not ack
        or marker != "CANDLE_FLYSPECK_V674_LIST_FLATTEN_PROBE_OK"
        or probe_log.count(ack) != 1
        or probe_log.count(marker) != 1
        or "ERROR:" in probe_log
    ):
        return fail("probe_evidence")

    print("status=0")
    print("failed_list_flatten_count=1")
    print("intended_runtime_definition_count=1")
    print("fresh_semantic_probe_count=1")
    print(f"failed_log_sha256={sha256(FAILED / 'runtime.log')}")
    print(f"probe_driver_sha256={sha256(PROBE_DRIVER)}")
    print(f"stage_driver_sha256={sha256(STAGE_DRIVER)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
