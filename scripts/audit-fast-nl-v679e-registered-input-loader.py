#!/usr/bin/env python3
"""Authenticate the failed registered-input load and its bounded replacement."""

from __future__ import annotations

import argparse
import hashlib
import pathlib


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
FAILED = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679d-fast-nl-tag10-full-candidate-dev-001"
)
INPUT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679e-fast-nl-registered-input-probe-input-v2-dev-001"
)
OUTPUT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679e-fast-nl-registered-input-probe-v2-dev-001"
)
TYPED_FAILED = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679e-fast-nl-registered-input-probe-dev-001"
)
PREAMBLE = PROJECT / "tools/fast_nl_v679d_tag10_full_preamble.ml"
POSTCHECK = PROJECT / "tools/fast_nl_v679e_registered_input_postcheck.ml"
RUNNER = PROJECT / "scripts/run-fast-nl-v679e-registered-input-probe.sh"
MANIFEST_ROOT = pathlib.Path(
    "/project/worktrees/flyspeck-cv-nonlinear-closure-v11-manifest-d6"
)
BOOTSTRAP_ROOT = pathlib.Path(
    "/project/worktrees/flyspeck-strictbuild-bootstrap-v1"
)
NORMALIZED_ROOT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "cv-first-leaf-predecessor-checkpoint-v37/overlay/flyspeck"
)
RAW_CERTIFICATE_SHA256 = (
    "6a511a0dff27cbfa8c40236837863d580a89790f3ef23cc57553bcce0fa81b69"
)
NORMALIZED_CERTIFICATE_SHA256 = (
    "de0d645e005651e8190e44b71380f35d4986ee167802b34bfa4a403d4dd962db"
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def preflight() -> int:
    raw_manifest = MANIFEST_ROOT / "formal_ineqs/verifier/certificate.hl"
    raw_bootstrap = BOOTSTRAP_ROOT / "formal_ineqs/verifier/certificate.hl"
    normalized = NORMALIZED_ROOT / "formal_ineqs/verifier/certificate.hl"
    required = (
        FAILED / "PROBE-FAILED",
        FAILED / "runtime.log",
        TYPED_FAILED / "PROBE-FAILED",
        TYPED_FAILED / "runtime.log",
        PREAMBLE,
        POSTCHECK,
        RUNNER,
        raw_manifest,
        raw_bootstrap,
        normalized,
    )
    if any(not path.is_file() or path.is_symlink() for path in required):
        return fail("registered_input_loader_authority")
    if (
        sha256(raw_manifest) != RAW_CERTIFICATE_SHA256
        or sha256(raw_bootstrap) != RAW_CERTIFICATE_SHA256
        or sha256(normalized) != NORMALIZED_CERTIFICATE_SHA256
    ):
        return fail("certificate_normalization_identity")

    log = (FAILED / "runtime.log").read_text(encoding="utf-8", errors="replace")
    if (
        log.count("Undefined variable: sprintf at line 109") != 1
        or str(raw_bootstrap) not in log
        or "CANDLE_REGISTERED_INPUT_CONSTRUCTION_END" in log
        or "CANDLE_FLYSPECK_V679D_TAG10_FULL_BATCH_OK" in log
    ):
        return fail("failed_registered_input_signature")
    typed_failed_log = (TYPED_FAILED / "runtime.log").read_text(
        encoding="utf-8", errors="replace"
    )
    if (
        typed_failed_log.count("Type mismatch between string and bool at line 3")
        != 1
        or typed_failed_log.count(str(MANIFEST_ROOT)) < 3
        or "verifier/certificate.hl ->" in typed_failed_log
        or "CANDLE_REGISTERED_INPUT_CONSTRUCTION_BEGIN" in typed_failed_log
    ):
        return fail("typed_preamble_failure_signature")

    preamble = PREAMBLE.read_text(encoding="utf-8")
    if (
        preamble.count(str(MANIFEST_ROOT)) != 1
        or "formal_ineqs/verifier/certificate.hl" not in preamble
        or "formal_ineqs/misc/report.hl" not in preamble
        or "verifier source-root precedence" not in preamble
        or preamble.count(
            '(candle_v679d_verifier_source_root ^\n'
        ) != 2
    ):
        return fail("verifier_source_root_precedence_contract")
    runner = RUNNER.read_text(encoding="utf-8")
    if (
        runner.count("FAST_NL_INPUT_PROBE_TIMEOUT_SECONDS=600") != 1
        or runner.count("historical_registered_input.ml") != 1
        or runner.count("audit-fast-nl-v679e-registered-input-loader.py") != 2
    ):
        return fail("registered_input_probe_runner_contract")
    postcheck = POSTCHECK.read_text(encoding="utf-8")
    if (
        postcheck.count("4173") != 3
        or "numerical_compute=0" not in postcheck
        or "new_axiom" in postcheck
    ):
        return fail("registered_input_postcheck_contract")

    print("status=0")
    print("failed_stage=registered_input_dependency_load")
    print("failed_numerical_compute_started=false")
    print("preamble_precedence_failure_count=1")
    print("replacement_timeout_seconds=600")
    print("replacement_preferred_source_root=verifier_manifest")
    return 0


def postflight() -> int:
    if preflight() != 0:
        return 1
    required = (
        INPUT / "driver.ml",
        INPUT / "fragments.sha256",
        OUTPUT / "PROBE-PASSED",
        OUTPUT / "input-probe.receipt",
        OUTPUT / "runtime.log",
        OUTPUT / "runtime-log.sha256",
    )
    if any(not path.is_file() or path.is_symlink() for path in required):
        return fail("registered_input_probe_evidence_missing")
    log = (OUTPUT / "runtime.log").read_text(encoding="utf-8", errors="replace")
    marker = (
        "CANDLE_FLYSPECK_V679E_REGISTERED_INPUT_OK DEVELOPMENT_NON_RELEASE "
        "cells=4173 numerical_compute=0 assumptions=0 axiom_growth=0"
    )
    if (
        log.count(marker) != 1
        or log.count("CANDLE_REGISTERED_INPUT_CONSTRUCTION_END cells=4173 numerical_compute=0")
        != 1
        or any(text in log for text in ("EXCEPTION:", "ERROR:", "Parsing failed"))
    ):
        return fail("registered_input_probe_runtime_contract")
    if sha256(OUTPUT / "runtime.log") not in (
        OUTPUT / "runtime-log.sha256"
    ).read_text(encoding="utf-8"):
        return fail("registered_input_probe_log_identity")

    print("status=0")
    print("registered_input_cells=4173")
    print("numerical_compute=0")
    print("assumptions=0")
    print("axiom_growth=0")
    print(f"runtime_log_sha256={sha256(OUTPUT / 'runtime.log')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    return preflight() if args.preflight else postflight()


if __name__ == "__main__":
    raise SystemExit(main())
