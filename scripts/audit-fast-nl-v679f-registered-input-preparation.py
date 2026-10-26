#!/usr/bin/env python3
"""Authenticate the v679e preparation failure and require a bounded repair."""

from __future__ import annotations

import hashlib
import os
import pathlib


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
FAILED = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679e-fast-nl-registered-input-probe-v2-dev-001"
)
REPLACEMENT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679g-fast-nl-registered-input-preparation-probe-dev-001"
)
FAILED_LOG_SHA256 = "1d455125df2294ae768c00d064f451dc54829107bd7f2aa92674c5067f05c6aa"
DIAGNOSTIC = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679f-fast-nl-verification-function-bind-probe-dev-001"
)
DIAGNOSTIC_LOG_SHA256 = (
    "213e8c33593e49d8b84f0d8ba2c3a0aa69329b1c7edc038518b8a1759ef7a3f4"
)
MANIFEST_ROOT = pathlib.Path(
    "/project/worktrees/flyspeck-cv-nonlinear-closure-v11-manifest-d6"
)
RUNTIME_COMPAT = PROJECT / "tools/fast_nl_v679f_direct_verifier_runtime_compat.ml"
DIAGNOSTIC_SOURCE = PROJECT / "tools/fast_nl_v679f_verification_function_bind_probe.ml"
RUNNER = PROJECT / "scripts/run-fast-nl-v679f-registered-input-preparation-probe.sh"
VERIFIER_COMPAT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v455-direct-verifier-mk-funs-overlay-dev-001/flyspeck/"
    "formal_ineqs/verifier/m_verifier_main.hl"
)
VERIFIER_COMPAT_SHA256 = (
    "19b069069caa6dd3d49cf84a3699588dd76ab77fc3b16c394cf50209dfa74706"
)
FIRST_REPAIR = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679f-fast-nl-registered-input-preparation-probe-dev-001"
)
FIRST_REPAIR_LOG_SHA256 = (
    "a3940dd1c6f001ae010d7f950fe99387496e9782b8cd3dd7ebd28ffe2bd85a97"
)
SUBTREE_PROBE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679g-fast-nl-verification-function-subtree-probe-dev-001"
)
SUBTREE_PROBE_LOG_SHA256 = (
    "00f1c7de3ff62d91b69d3ff72fa8d33af29181b81363fcf08ac921dc805de33e"
)
FAILED_EXPORT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679h-fast-nl-prepared-input-export-dev-001"
)
FAILED_EXPORT_LOG_SHA256 = (
    "bb9de7576f1e924dbc7687d4e5e074513f281a5aa39f5195594a8f5579fbe51a"
)
MONOLITH_EXPORT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679i-fast-nl-prepared-input-export-dev-001"
)
MONOLITH_EXPORT_LOG_SHA256 = (
    "403db71cb4536177e04ac779a3e9cfb663317680e0a66ced2d4208d38581f95d"
)
CHUNK_EXPORT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679j-fast-nl-prepared-input-chunks-dev-001"
)
CHUNK_EXPORT_LOG_SHA256 = (
    "e778445595cefdf7de55a71edc515f809f93b4b33526e1d9a75e2ec104252bc5"
)
FLAT_EXPORT_RUNNER = (
    PROJECT / "scripts/run-fast-nl-v679k-export-prepared-input-flat.sh"
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def authenticate_failure() -> int:
    failed_marker = FAILED / "PROBE-FAILED"
    log_path = FAILED / "runtime.log"
    if (
        not failed_marker.is_file()
        or failed_marker.is_symlink()
        or not log_path.is_file()
        or log_path.is_symlink()
    ):
        return fail("registered_input_preparation_failure_evidence")
    if sha256(log_path) != FAILED_LOG_SHA256:
        return fail("registered_input_preparation_failure_identity")
    log = log_path.read_text(encoding="utf-8", errors="replace")
    certificate = str(MANIFEST_ROOT / "formal_ineqs/verifier/certificate.hl")
    report = str(MANIFEST_ROOT / "formal_ineqs/misc/report.hl")
    required_once = (
        "CANDLE_CERT_PROFILE lane=action296-plan phase=source-bounds",
        "CANDLE_CERT_PROFILE lane=action296-plan phase=verification-functions-begin",
        "EXCEPTION: Bind",
    )
    if (
        any(log.count(marker) != 1 for marker in required_once)
        or certificate not in log
        or report not in log
        or "CANDLE_CERT_PROFILE lane=action296-plan phase=verification-functions\n"
        in log
        or "CANDLE_REGISTERED_INPUT_CONSTRUCTION_END" in log
        or "CANDLE_FLYSPECK_V679E_REGISTERED_INPUT_OK" in log
        or "CANDLE_FLYSPECK_V679D_TAG10_FULL_BATCH_OK" in log
    ):
        return fail("registered_input_preparation_failure_signature")

    diagnostic_marker = DIAGNOSTIC / "PROBE-FAILED"
    diagnostic_log_path = DIAGNOSTIC / "runtime.log"
    required_sources = (
        RUNTIME_COMPAT,
        DIAGNOSTIC_SOURCE,
        RUNNER,
        VERIFIER_COMPAT,
    )
    if (
        not diagnostic_marker.is_file()
        or diagnostic_marker.is_symlink()
        or not diagnostic_log_path.is_file()
        or diagnostic_log_path.is_symlink()
        or any(not path.is_file() or path.is_symlink() for path in required_sources)
    ):
        return fail("registered_input_dimension_failure_authority")
    if (
        sha256(diagnostic_log_path) != DIAGNOSTIC_LOG_SHA256
        or sha256(VERIFIER_COMPAT) != VERIFIER_COMPAT_SHA256
    ):
        return fail("registered_input_dimension_failure_identity")
    diagnostic_log = diagnostic_log_path.read_text(
        encoding="utf-8", errors="replace"
    )
    if (
        diagnostic_log.count("EXCEPTION: Bind") != 1
        or diagnostic_log.count("Undefined variable: string_of_bool") != 1
        or "CANDLE_V679F_BIND_PROBE boundary=verification-functions-failed"
        not in diagnostic_log
    ):
        return fail("registered_input_dimension_failure_signature")

    runtime_compat = RUNTIME_COMPAT.read_text(encoding="utf-8")
    diagnostic_source = DIAGNOSTIC_SOURCE.read_text(encoding="utf-8")
    runner = RUNNER.read_text(encoding="utf-8")
    if (
        runtime_compat.count("Kernel.dest_type (Kernel.call_type_of tm)") != 1
        or runtime_compat.count("include M_taylor") != 1
        or "string_of_bool" in diagnostic_source
        or runner.count("FAST_NL_INPUT_PROBE_TIMEOUT_SECONDS=900") != 1
        or runner.count(VERIFIER_COMPAT_SHA256) != 1
        or runner.count(str(VERIFIER_COMPAT)) != 1
    ):
        return fail("registered_input_runtime_compat_contract")

    first_repair_marker = FIRST_REPAIR / "PROBE-FAILED"
    first_repair_log_path = FIRST_REPAIR / "runtime.log"
    if (
        not first_repair_marker.is_file()
        or first_repair_marker.is_symlink()
        or not first_repair_log_path.is_file()
        or first_repair_log_path.is_symlink()
        or sha256(first_repair_log_path) != FIRST_REPAIR_LOG_SHA256
    ):
        return fail("registered_input_first_repair_failure_identity")
    first_repair_log = first_repair_log_path.read_text(
        encoding="utf-8", errors="replace"
    )
    if (
        first_repair_log.count(
            "CANDLE_V679F_DIRECT_VERIFIER_RUNTIME_COMPAT dimension=6"
        )
        != 1
        or first_repair_log.count(
            "CANDLE_CERT_PROFILE lane=action296-plan "
            "phase=verification-functions-begin"
        )
        != 1
        or first_repair_log.count('EXCEPTION: Failure "dest_const: not a constant"')
        != 1
        or "CANDLE_REGISTERED_INPUT_CONSTRUCTION_END" in first_repair_log
    ):
        return fail("registered_input_first_repair_failure_signature")

    subtree_passed = SUBTREE_PROBE / "PROBE-PASSED"
    subtree_receipt = SUBTREE_PROBE / "input-probe.receipt"
    subtree_log_path = SUBTREE_PROBE / "runtime.log"
    if (
        not subtree_passed.is_file()
        or subtree_passed.is_symlink()
        or not subtree_receipt.is_file()
        or subtree_receipt.is_symlink()
        or not subtree_log_path.is_file()
        or subtree_log_path.is_symlink()
        or sha256(subtree_log_path) != SUBTREE_PROBE_LOG_SHA256
    ):
        return fail("registered_input_subtree_probe_identity")
    subtree_log = subtree_log_path.read_text(encoding="utf-8", errors="replace")
    if (
        subtree_log.count("boundary=mk-funs-failed") != 1178
        or "boundary=mk-funs-ok" in subtree_log
        or subtree_log.count("boundary=term-shape is_abs=true dimension=6") != 1
        or subtree_log.count("boundary=verification-functions-failed") != 1
        or any(text in subtree_log for text in ("EXCEPTION:", "ERROR:", "Parsing failed"))
    ):
        return fail("registered_input_subtree_probe_contract")

    failed_export_marker = FAILED_EXPORT / "PROBE-FAILED"
    failed_export_log_path = FAILED_EXPORT / "runtime.log"
    if (
        not failed_export_marker.is_file()
        or failed_export_marker.is_symlink()
        or not failed_export_log_path.is_file()
        or failed_export_log_path.is_symlink()
        or sha256(failed_export_log_path) != FAILED_EXPORT_LOG_SHA256
    ):
        return fail("prepared_input_export_failure_identity")
    failed_export_log = failed_export_log_path.read_text(
        encoding="utf-8", errors="replace"
    )
    if (
        failed_export_log.count("Undefined variable: Stdlib.output_char") != 1
        or "CANDLE_FLYSPECK_V679H_PREPARED_INPUT_EXPORT_OK" in failed_export_log
    ):
        return fail("prepared_input_export_failure_signature")

    monolith_failed = MONOLITH_EXPORT / "PROBE-FAILED"
    monolith_log_path = MONOLITH_EXPORT / "runtime.log"
    monolith_jobs = MONOLITH_EXPORT / "encoded-jobs.term"
    monolith_roots = MONOLITH_EXPORT / "roots.term"
    if (
        not monolith_failed.is_file()
        or monolith_failed.is_symlink()
        or not monolith_log_path.is_file()
        or monolith_log_path.is_symlink()
        or sha256(monolith_log_path) != MONOLITH_EXPORT_LOG_SHA256
        or not monolith_jobs.is_file()
        or monolith_jobs.stat().st_size != 11733780
        or monolith_roots.exists()
        or "exited before fresh markers"
        not in monolith_failed.read_text(encoding="utf-8")
    ):
        return fail("prepared_input_monolith_timeout_contract")

    chunk_stopped = CHUNK_EXPORT / "PROBE-STOPPED"
    chunk_log_path = CHUNK_EXPORT / "runtime.log"
    if (
        not chunk_stopped.is_file()
        or chunk_stopped.is_symlink()
        or not chunk_log_path.is_file()
        or chunk_log_path.is_symlink()
        or sha256(chunk_log_path) != CHUNK_EXPORT_LOG_SHA256
        or len(list(CHUNK_EXPORT.glob("jobs-*.term"))) != 9
        or list(CHUNK_EXPORT.glob("roots-*.term"))
        or "roughly 50-minute" not in chunk_stopped.read_text(encoding="utf-8")
    ):
        return fail("prepared_input_chunk_parse_rate_contract")
    if (
        not FLAT_EXPORT_RUNNER.is_file()
        or FLAT_EXPORT_RUNNER.is_symlink()
        or not os.access(FLAT_EXPORT_RUNNER, os.X_OK)
    ):
        return fail("prepared_input_flat_export_runner_executable")
    return 0


def main() -> int:
    if authenticate_failure() != 0:
        return 1

    receipt = REPLACEMENT / "preparation-probe.receipt"
    log_path = REPLACEMENT / "runtime.log"
    if (
        not receipt.is_file()
        or receipt.is_symlink()
        or not log_path.is_file()
        or log_path.is_symlink()
    ):
        return fail("bounded_registered_input_preparation_repair_missing")

    receipt_fields = {}
    for line in receipt.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            receipt_fields[key] = value
    log = log_path.read_text(encoding="utf-8", errors="replace")
    marker = (
        "CANDLE_FLYSPECK_V679F_REGISTERED_INPUT_PREPARATION_OK "
        "DEVELOPMENT_NON_RELEASE cells=4173 numerical_compute=0"
    )
    if (
        receipt_fields.get("status") != "0"
        or receipt_fields.get("cells") != "4173"
        or receipt_fields.get("numerical_compute") != "0"
        or receipt_fields.get("runtime_log_sha256") != sha256(log_path)
        or log.count(marker) != 1
        or "CANDLE_REGISTERED_INPUT_CONSTRUCTION_END cells=4173 numerical_compute=0"
        not in log
        or any(text in log for text in ("EXCEPTION:", "ERROR:", "Parsing failed"))
    ):
        return fail("bounded_registered_input_preparation_repair_contract")

    print("status=0")
    print("failed_boundary=verification-functions-begin")
    print("replacement_cells=4173")
    print("replacement_numerical_compute=0")
    print(f"replacement_runtime_log_sha256={sha256(log_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
