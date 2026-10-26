#!/usr/bin/env python3
"""Authenticate the v679e preparation failure and require a bounded repair."""

from __future__ import annotations

import hashlib
import pathlib


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
FAILED = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679e-fast-nl-registered-input-probe-v2-dev-001"
)
REPLACEMENT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679f-fast-nl-registered-input-preparation-probe-dev-001"
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
