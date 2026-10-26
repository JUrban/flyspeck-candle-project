#!/usr/bin/env python3
"""Preflight and authenticate the bounded complete tag-10 candidate run."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import subprocess


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
CANDIDATE = pathlib.Path("/project/worktrees/candle-fast-nl-historical-tag10-v1")
BASE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-direct-source-interface-v678"
)
PRIOR = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679c-fast-nl-tag10-logical-fragment-probe-v2-dev-001"
)
INPUT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679d-fast-nl-tag10-full-input-v2-dev-001"
)
OUTPUT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679d-fast-nl-tag10-full-candidate-v2-dev-001"
)
REGISTERED_INPUT_PROBE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679e-fast-nl-registered-input-probe-dev-001"
)
RUNNER = PROJECT / "scripts/run-fast-nl-v679d-tag10-full-candidate.sh"
GLUE = (
    PROJECT / "tools/fast_nl_v679d_tag10_full_preamble.ml",
    PROJECT / "tools/fast_nl_v679d_tag10_full_batch.ml",
    PROJECT / "tools/fast_nl_v679d_tag10_full_postcheck.ml",
)
BASE_SHA256 = "980d06be6fb7b418a018fddfd3cdd0bece5bd5f1ba83695264cc532dd742fce1"
CANDIDATE_HEAD = "85276ec10e3fd2f6df6114350aa773da9b327a4e"
SOURCES = {
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_compute.ml": "5bbf53ebc14fa98bad9f65b3984f4819d519c75e5490e51af0a1a26b5444e676",
    "candle/cv_compute_analytic_expr_fixed_scale_historical_root_certificate_sound.ml": "1fb77c8796652bba92b0da73386f981ea7ff4a367eb865c2760b4783ebec124c",
    "candle/cv_compute_analytic_expr_fixed_scale_historical_root_certificate_compute.ml": "e31a76bb5c4fcfa73840025b6f5afbb54a18f7e190759440c988630b0ea3c2b3",
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_checked_compute.ml": "0a8d536bba53cf602de2beefcc3b1c97643e0870b76ac2a813532069d3dbfcb9",
    "candle/benchmark_cv_compute_analytic_expr_case10173_historical_registered_input.ml": "797e9e603d5ae2116cfc94ecba25fd415cda25762a33f31b6acac330348b32fa",
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_checked_sound.ml": "376b445901de8bcc32ec896039c3b90a4137c0f3cbdb6df1ad1c50136c6fbd1c",
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_item_sound.ml": "536d2ea98fb836390ba6ef46fc745cd7ed97a6d6c4fad9218352f145f3bd1154",
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_logical_sound.ml": "21e5973145500e77250c746ca36b494dc1a3c2a3405d359d0f7035227cc731df",
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_sound.ml": "83de4cd2c5d0b6041e921b59f0e608968f25f7fbe921f6d6c410bf27631e558a",
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_item_invariant.ml": "11601da1e3b5fb25e545197ccd6b9a34a3c3a5b7641c027a1e626e7dae32fd73",
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_analytic_sound.ml": "4a21c93a975fa14e04e9b02148d650a5961ca1e16c4e045838ddcb276b0cd334",
    "candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_reference_sound.ml": "05cc09ef264cecaa88707992c7dd7f525485029a6e6e985dfb2ef345d652cf97",
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_production_contract_sound.ml": "1f9abe8a86a70bf8bbd593c4ec59fc215936270d30f6d0a321e9949cb80ea0bc",
}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def parse_receipt(path: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def preflight() -> int:
    required = (
        RUNNER,
        *GLUE,
        BASE / "CHECKPOINT-READY",
        BASE / "checkpoint.sha256",
        PRIOR / "PROBE-PASSED",
        PRIOR / "input-probe.receipt",
        PRIOR / "runtime.log",
        REGISTERED_INPUT_PROBE / "PROBE-PASSED",
        REGISTERED_INPUT_PROBE / "input-probe.receipt",
        REGISTERED_INPUT_PROBE / "runtime.log",
    )
    if any(not path.is_file() or path.is_symlink() for path in required):
        return fail("missing_or_symlinked_preflight_authority")
    if BASE_SHA256 not in (BASE / "checkpoint.sha256").read_text(encoding="utf-8"):
        return fail("predecessor_checkpoint_identity")

    head = subprocess.check_output(
        ["git", "-C", str(CANDIDATE), "rev-parse", "HEAD"], text=True
    ).strip()
    status = subprocess.check_output(
        ["git", "-C", str(CANDIDATE), "status", "--porcelain"], text=True
    )
    if head != CANDIDATE_HEAD or status:
        return fail("candidate_repository_contract")
    for logical, expected in SOURCES.items():
        source = CANDIDATE / logical
        if not source.is_file() or source.is_symlink() or sha256(source) != expected:
            return fail(f"candidate_source_identity:{logical}")

    prior_log = (PRIOR / "runtime.log").read_text(
        encoding="utf-8", errors="replace"
    )
    if (
        prior_log.count("CANDLE_FLYSPECK_V679C_TAG10_FRAGMENT_LOGICAL_PROOF_OK")
        != 1
        or "EXCEPTION:" in prior_log
        or "ERROR:" in prior_log
    ):
        return fail("prior_logical_proof_contract")
    input_probe_log = (REGISTERED_INPUT_PROBE / "runtime.log").read_text(
        encoding="utf-8", errors="replace"
    )
    if (
        input_probe_log.count("CANDLE_FLYSPECK_V679E_REGISTERED_INPUT_OK") != 1
        or "EXCEPTION:" in input_probe_log
        or "ERROR:" in input_probe_log
    ):
        return fail("registered_input_probe_contract")

    runner = RUNNER.read_text(encoding="utf-8")
    if (
        runner.count("FAST_NL_INPUT_PROBE_TIMEOUT_SECONDS=1200") != 1
        or runner.count("audit-fast-nl-v679d-tag10-full-candidate.py") != 2
        or runner.count("historical_dihedral_program_compute.ml") != 1
        or runner.count("historical_dihedral_program_logical_sound.ml") != 1
        or runner.count("historical_dihedral_program_analytic_sound.ml") != 1
        or runner.count("historical_dihedral_program_sound.ml") != 1
        or 'for parse_source in "$preamble" "$postcheck"' not in runner
    ):
        return fail("bounded_runner_contract")

    preamble, batch, postcheck = (
        path.read_text(encoding="utf-8") for path in GLUE
    )
    if (
        preamble.count("axioms ()") != 1
        or batch.count("cells=4173") != 1
        or batch.count("candle_q_dim_analytic_jet_compute") != 1
        or postcheck.count("axioms ()") != 1
        or "TAG10_FULL_CANDIDATE_OK" not in postcheck
        or any("new_axiom" in text for text in (preamble, batch, postcheck))
    ):
        return fail("full_candidate_driver_contract")

    print("status=0")
    print("planned_fragment_count=16")
    print("candidate_source_count=13")
    print("full_batch_cells=4173")
    print("timeout_seconds=1200")
    print(f"candidate_head={CANDIDATE_HEAD}")
    print(f"predecessor_checkpoint_sha256={BASE_SHA256}")
    return 0


def postflight() -> int:
    if preflight() != 0:
        return 1
    required = (
        INPUT / "driver.ml",
        INPUT / "driver.sha256",
        INPUT / "fragments.sha256",
        OUTPUT / "PROBE-PASSED",
        OUTPUT / "input-probe.receipt",
        OUTPUT / "runtime.log",
        OUTPUT / "runtime-log.sha256",
    )
    if any(not path.is_file() or path.is_symlink() for path in required):
        return fail("complete_candidate_evidence_missing")
    receipt = parse_receipt(OUTPUT / "input-probe.receipt")
    if (
        receipt.get("base_checkpoint_sha256") != BASE_SHA256
        or receipt.get("driver_sha256") != sha256(INPUT / "driver.ml")
        or receipt.get("expected_marker")
        != "CANDLE_FLYSPECK_V679D_TAG10_FULL_CANDIDATE_OK"
        or int(receipt.get("elapsed_seconds", "1201")) > 1200
    ):
        return fail("complete_candidate_receipt")
    if sha256(OUTPUT / "runtime.log") not in (
        OUTPUT / "runtime-log.sha256"
    ).read_text(encoding="utf-8"):
        return fail("complete_candidate_log_identity")

    manifest = (INPUT / "fragments.sha256").read_text(encoding="utf-8")
    for expected in SOURCES.values():
        if manifest.count(expected) != 1:
            return fail("complete_candidate_fragment_identity")
    log = (OUTPUT / "runtime.log").read_text(encoding="utf-8", errors="replace")
    required_markers = (
        "CANDLE_REGISTERED_INPUT_CONSTRUCTION_END cells=4173 numerical_compute=0",
        "CANDLE_FLYSPECK_V679D_TAG10_FULL_BATCH_OK DEVELOPMENT_NON_RELEASE cells=4173 result=1 authenticated_aux_roots=16692 assumptions=0",
        "CANDLE_FLYSPECK_V679D_TAG10_FULL_CANDIDATE_OK DEVELOPMENT_NON_RELEASE cells=4173 assumptions=0 axiom_growth=0",
    )
    if any(log.count(marker) != 1 for marker in required_markers):
        return fail("complete_candidate_marker_contract")
    if any(
        forbidden in log
        for forbidden in (
            "EXCEPTION:",
            "ERROR:",
            "Parsing failed",
            "Fatal error",
            "Out of memory",
        )
    ):
        return fail("complete_candidate_runtime_error")

    print("status=0")
    print("full_batch_cells=4173")
    print("downstream_theorem_partition=7")
    print("assumptions=0")
    print("axiom_growth=0")
    print(f"elapsed_seconds={receipt['elapsed_seconds']}")
    print(f"runtime_log_sha256={sha256(OUTPUT / 'runtime.log')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    return preflight() if args.preflight else postflight()


if __name__ == "__main__":
    raise SystemExit(main())
