#!/usr/bin/env python3
"""Cheap audit of the 56+29 normalization partition around actions 0--49."""

from __future__ import annotations

import hashlib
import pathlib
import re
import sys


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
WRAPPER = PROJECT / "tools/fast_nl_v668_action49_overlay_partition.ml"
BASE_DATA = pathlib.Path(
    "/project/flyspeck-candle-runs/v355-postsetup-checkpoint-dev-001/overlay-data-v355.ml"
)
VERIFIER_DATA = PROJECT / "tools/fast_nl_v665_verifier_data.ml"
ACTION_DRIVER = pathlib.Path(
    "/project/flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001/action0-through49.ml"
)
SUCCESS_LOG = pathlib.Path(
    "/project/flyspeck-candle-runs/v664-fast-nl-complete-support-closure-dev-001/postaction49/runtime.log"
)
FAILED_LOG = pathlib.Path(
    "/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/postaction49/runtime.log"
)
VERIFIER_ROOT = "/project/worktrees/flyspeck-cv-nonlinear-closure-v11-manifest-d6/"
EXPECTED_ACTION_SHA256 = (
    "0174c32fd75dd9db8027c9dddfef46cd6a98afd58c4f48345203800158ab03ce"
)
NORMALIZATION_RE = re.compile(
    r'^\s*\("([^"]+)","([^"]+)","([0-9a-f]{32})"\);$',
    flags=re.MULTILINE,
)
LOAD_RE = re.compile(r'^- Loading (.+)$', flags=re.MULTILINE)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def main() -> int:
    for path in (WRAPPER, BASE_DATA, VERIFIER_DATA, ACTION_DRIVER, SUCCESS_LOG, FAILED_LOG):
        if not path.is_file():
            return fail(f"missing:{path}")
    if sha256(ACTION_DRIVER) != EXPECTED_ACTION_SHA256:
        return fail("action_driver_hash")

    base_rows = NORMALIZATION_RE.findall(BASE_DATA.read_text(encoding="utf-8"))
    verifier_text = VERIFIER_DATA.read_text(encoding="utf-8")
    verifier_text = verifier_text.split(
        "let candle_fast_nl_v665_verifier_normalized_sources", 1
    )[1]
    verifier_rows = NORMALIZATION_RE.findall(verifier_text)
    base_originals = {row[0] for row in base_rows}
    verifier_originals = {row[0] for row in verifier_rows}
    if (
        len(base_rows) != 56
        or len(base_originals) != 56
        or len(verifier_rows) != 29
        or len(verifier_originals) != 29
        or base_originals & verifier_originals
    ):
        return fail("normalization_partition")

    wrapper_text = WRAPPER.read_text(encoding="utf-8")
    required_wrapper_fragments = (
        "List.length candle_flyspeck_v668_verifier_mappings <> 29",
        "List.length candle_flyspeck_v668_direct_mappings <> 56",
        f'#use "{ACTION_DRIVER}";;',
        "List.length candle_flyspeck_v668_complete_mappings <> 85",
        "CANDLE_FLYSPECK_V668_ACTION49_CHECKPOINT_READY actions=50 passed=50 normalizations=85",
    )
    if any(wrapper_text.count(fragment) != 1 for fragment in required_wrapper_fragments):
        return fail("wrapper_contract")

    success_text = SUCCESS_LOG.read_text(encoding="utf-8", errors="replace")
    if (
        success_text.count(
            "CANDLE_FLYSPECK_V656_ACTION49_CHECKPOINT_READY actions=50 passed=50"
        )
        != 1
        or re.search(
            r"ERROR:|EXCEPTION:|Parsing failed|Fatal error|Out of memory",
            success_text,
        )
        or any(path.startswith(VERIFIER_ROOT) for path in LOAD_RE.findall(success_text))
    ):
        return fail("historical_action_evidence")

    failed_text = FAILED_LOG.read_text(encoding="utf-8", errors="replace")
    expected_failure = 'EXCEPTION: Failure "v356 tactic overlay prior cardinality mismatch"'
    failure_lines = re.findall(
        r"^(?:ERROR:|EXCEPTION:|Parsing failed|Fatal error|Out of memory).*$",
        failed_text,
        flags=re.MULTILINE,
    )
    if failure_lines != [expected_failure]:
        return fail("failed_evidence_class")

    late_overlay_root = BASE_DATA.parent
    cardinality_files = []
    for name in ("late-overlay-v356.ml", "late-overlay-v357.ml", "late-overlay-v358.ml"):
        path = late_overlay_root / name
        text = path.read_text(encoding="utf-8")
        if text.count("List.length mappings <> 56") != 1:
            return fail(f"late_overlay_contract:{name}")
        cardinality_files.append(path)

    print("status=0")
    print("base_normalization_count=56")
    print("verifier_normalization_count=29")
    print("combined_normalization_count=85")
    print("normalization_overlap_count=0")
    print("historical_action_verifier_load_count=0")
    print("historical_action_status=50/50")
    print("late_overlay_cardinality_file_count=3")
    print(f"action_driver_sha256={sha256(ACTION_DRIVER)}")
    print(f"wrapper_sha256={sha256(WRAPPER)}")
    print(f"failed_log_sha256={sha256(FAILED_LOG)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
