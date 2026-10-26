#!/usr/bin/env python3
"""Authenticate the v678 loader ledger and partition its remaining NL support.

This is a cheap admission discriminator, not theorem evidence.  In particular,
it compares sources by the same logical identity used by Candle's authenticated
loader: basename plus MD5.  Absolute paths are observations of a particular
worktree or snapshot and are deliberately not used to decide whether a source
has already been loaded.
"""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import re
import subprocess
import sys


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
SOURCE_AUDIT = PROJECT / "scripts/audit-fast-nl-support-source-closure.py"
MODULE_AUDIT = PROJECT / "scripts/audit-fast-nl-support-module-closure.py"
PROBE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679-fast-nl-loaded-source-ledger-probe-dev-001"
)
RECEIPT = PROBE / "loaded-source-ledger.receipt"
LOG = PROBE / "runtime.log"
LOG_SHA256 = PROBE / "runtime-log.sha256"
DRIVER = PROJECT / "tools/fast_nl_v679_loaded_source_ledger_probe.ml"

EXPECTED_BASE_SHA256 = (
    "980d06be6fb7b418a018fddfd3cdd0bece5bd5f1ba83695264cc532dd742fce1"
)
EXPECTED_DRIVER_SHA256 = (
    "645585219886d3a8f595a9fbb17f040d1e72f0bfdea1043102f966e94e0fcefd"
)
EXPECTED_LOADED_COUNT = 301
EXPECTED_ENTRY_REMAINING = (56, 1, 28, 48)

# Each root is cumulative.  The increments make the intended bounded loading
# order explicit and stop a later source edit from silently growing a stage.
PARTITION_ROOTS = (
    "candle/cv_compute_analytic_expr_case10173_historical_registered_combine.ml",
    "candle/benchmark_cv_compute_analytic_expr_case10173_historical_registered_input.ml",
    "candle/benchmark_cv_compute_registered_hol4_export.ml",
    "candle/benchmark_cv_compute_analytic_expr_case10173_historical_registered_topology_capture.ml",
    "candle/cv_compute_analytic_expr_case10173_historical_registered_topology_prove.ml",
    "candle/cv_compute_analytic_expr_case10173_historical_registered_domain_prove.ml",
    "candle/cv_compute_analytic_expr_case10173_historical_authenticated_ledger_sound.ml",
    "candle/cv_compute_analytic_expr_case10173_historical_registered_original_prove.ml",
)
EXPECTED_PARTITION_INCREMENTS = (20, 24, 1, 4, 2, 3, 2, 1)

# The first twenty-file group is itself admitted in three small stages.  The
# first stage is the immediate next candidate and must remain exactly five
# sources after the v678 logical ledger is subtracted.
FIRST_GROUP_ROOTS = (
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_checked_sound.ml",
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_production_contract_sound.ml",
    "candle/cv_compute_analytic_expr_case10173_historical_registered_combine.ml",
)
EXPECTED_FIRST_GROUP_INCREMENTS = (5, 6, 9)

BEGIN = "CANDLE_FLYSPECK_V679_LOADED_SOURCE_LEDGER_BEGIN count=301"
END = "CANDLE_FLYSPECK_V679_LOADED_SOURCE_LEDGER_END"
ITEM_RE = re.compile(
    r"CANDLE_FLYSPECK_V679_LOADED_SOURCE identity=([^:\s]+):([0-9a-f]{32})"
)


def digest(path: pathlib.Path, algorithm: str = "sha256") -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def parse_receipt(path: pathlib.Path) -> dict[str, str]:
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


def load_source_audit():
    spec = importlib.util.spec_from_file_location("fast_nl_source_audit", SOURCE_AUDIT)
    if spec is None or spec.loader is None:
        raise RuntimeError("source audit import")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def closure(
    audit,
    request: str,
    loads_cache: dict[pathlib.Path, list[str]],
    identity_cache: dict[pathlib.Path, tuple[str, str]],
) -> set[tuple[str, str]]:
    pending = [request]
    seen_paths: set[pathlib.Path] = set()
    identities: set[tuple[str, str]] = set()
    while pending:
        item = pending.pop()
        path = audit.resolve(item)
        if path is None:
            raise RuntimeError(f"unresolved:{item}")
        if path in seen_paths:
            continue
        seen_paths.add(path)
        if path not in loads_cache:
            _, loads_cache[path] = audit.source_and_literal_loads(path)
        requests = loads_cache[path]
        pending.extend(requests)
        if path not in identity_cache:
            identity_cache[path] = (path.name, audit.md5(path))
        identities.add(identity_cache[path])
    return identities


def checked_audit(path: pathlib.Path, expected: tuple[str, ...]) -> bool:
    completed = subprocess.run(
        [str(path)],
        cwd=PROJECT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
        check=False,
    )
    lines = set(completed.stdout.splitlines())
    return completed.returncode == 0 and all(item in lines for item in expected)


def main() -> int:
    required = (SOURCE_AUDIT, MODULE_AUDIT, RECEIPT, LOG, LOG_SHA256, DRIVER)
    if any(not path.is_file() or path.is_symlink() for path in required):
        return fail("missing_or_symlinked_authority")
    if digest(DRIVER) != EXPECTED_DRIVER_SHA256:
        return fail("probe_driver_identity")

    receipt = parse_receipt(RECEIPT)
    expected_receipt = {
        "receipt_kind": "development-fast-nl-loaded-source-ledger-probe-v1",
        "release_evidence": "false",
        "status": "0",
        "base_checkpoint_sha256": EXPECTED_BASE_SHA256,
        "driver_sha256": EXPECTED_DRIVER_SHA256,
        "loaded_source_count": str(EXPECTED_LOADED_COUNT),
    }
    if any(receipt.get(key) != value for key, value in expected_receipt.items()):
        return fail("probe_receipt_contract")
    if not receipt.get("fresh_ack", "").startswith("CANDLE_RESTORE_INPUT_ACK nonce="):
        return fail("probe_fresh_ack_receipt")

    log = LOG.read_text(encoding="utf-8", errors="replace")
    recorded_log_sha = LOG_SHA256.read_text(encoding="utf-8").split()[0]
    if recorded_log_sha != digest(LOG):
        return fail("probe_log_identity")
    if log.count(BEGIN) != 1 or log.count(END) != 1:
        return fail("probe_ledger_markers")
    if log.count(receipt["fresh_ack"]) != 1:
        return fail("probe_fresh_ack_log")
    forbidden = ("ERROR:", "EXCEPTION:", "Parsing failed", "Fatal error", "Out of memory")
    if any(item in log for item in forbidden):
        return fail("probe_runtime_error")

    loaded = set(ITEM_RE.findall(log))
    if len(loaded) != EXPECTED_LOADED_COUNT:
        return fail("probe_loaded_identity_count")
    if len(ITEM_RE.findall(log)) != len(loaded):
        return fail("probe_duplicate_loaded_identity")
    by_name: dict[str, set[str]] = {}
    for name, identity in loaded:
        by_name.setdefault(name, set()).add(identity)
    if any(len(identities) != 1 for identities in by_name.values()):
        return fail("probe_basename_identity_conflict")

    if not checked_audit(
        SOURCE_AUDIT,
        (
            "status=0",
            "entry_count=4",
            "missing_identity_count=0",
            "unresolved_request_count=0",
            "dynamic_request_count=0",
            "stale_authority_count=0",
        ),
    ):
        return fail("source_closure_audit")
    if not checked_audit(
        MODULE_AUDIT,
        (
            "status=0",
            "support_entry_count=4",
            "planned_load_path_count=297",
            "missing_module_count=0",
            "identity_conflict_count=0",
        ),
    ):
        return fail("module_closure_audit")

    audit = load_source_audit()
    loads_cache: dict[pathlib.Path, list[str]] = {}
    identity_cache: dict[pathlib.Path, tuple[str, str]] = {}
    try:
        entry_remaining = tuple(
            len(closure(audit, entry, loads_cache, identity_cache) - loaded)
            for entry in audit.ENTRY_REQUESTS
        )
        all_remaining = set().union(
            *(
                closure(audit, entry, loads_cache, identity_cache) - loaded
                for entry in audit.ENTRY_REQUESTS
            )
        )
        if entry_remaining != EXPECTED_ENTRY_REMAINING or len(all_remaining) != 57:
            return fail("entry_remaining_partition")

        covered: set[tuple[str, str]] = set()
        increments: list[int] = []
        for root in PARTITION_ROOTS:
            remaining = closure(audit, root, loads_cache, identity_cache) - loaded
            increments.append(len(remaining - covered))
            covered.update(remaining)
        if tuple(increments) != EXPECTED_PARTITION_INCREMENTS:
            return fail("cumulative_remaining_partition")
        if covered != all_remaining:
            return fail("cumulative_remaining_coverage")

        first_covered: set[tuple[str, str]] = set()
        first_increments: list[int] = []
        for root in FIRST_GROUP_ROOTS:
            remaining = closure(audit, root, loads_cache, identity_cache) - loaded
            first_increments.append(len(remaining - first_covered))
            first_covered.update(remaining)
        if tuple(first_increments) != EXPECTED_FIRST_GROUP_INCREMENTS:
            return fail("first_group_partition")
        if len(first_covered) != EXPECTED_PARTITION_INCREMENTS[0]:
            return fail("first_group_coverage")
    except (OSError, UnicodeDecodeError, ValueError, RuntimeError) as error:
        return fail(f"closure_error:{error}")

    print("status=0")
    print(f"authenticated_loaded_identity_count={len(loaded)}")
    print("logical_identity_key=basename+md5")
    print("absolute_path_identity_required=false")
    print("entry_remaining_counts=" + ",".join(map(str, entry_remaining)))
    print(f"remaining_union_count={len(all_remaining)}")
    print("partition_increment_counts=" + ",".join(map(str, increments)))
    print("first_group_increment_counts=" + ",".join(map(str, first_increments)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
