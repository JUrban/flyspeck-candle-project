#!/usr/bin/env python3
"""Fail closed while the historical private tag collides with matan tag 9."""

from __future__ import annotations

import hashlib
import pathlib


FAILED = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-historical-production-contract-v679b"
)
CURRENT_GENERIC = pathlib.Path(
    "/project/worktrees/candle-fast-nl-matan-closure-v1/candle/"
    "cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear_program_sound.ml"
)
HISTORICAL_COMPUTE = pathlib.Path(
    "/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/"
    "cv_compute_analytic_expr_case10173_historical_dihedral_program_compute.ml"
)
HISTORICAL_LOGICAL = pathlib.Path(
    "/project/worktrees/candle-direct-fast-nl-runtime-v1/candle/"
    "cv_compute_analytic_expr_case10173_historical_dihedral_program_logical_sound.ml"
)
PRIOR = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "cv-case10173-historical-program-logical-sound-v021-dev-001"
)
CURRENT_GENERIC_SHA256 = (
    "d3c3b19b5e6349d74624591d0d7345ff71857c4d32f85d91117f0abf667aac51"
)
PRIOR_GENERIC_SHA256 = (
    "abf9f3c055c3e7e6ab5c0d0eb406d625b1540812b6aa0b20eb771749284172a2"
)
HISTORICAL_LOGICAL_SHA256 = (
    "2d35de3cd32e18c070ec917e3f66681c844941dacb1879f076baecf47c5e9253"
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def main() -> int:
    required = (
        FAILED / "CHECKPOINT-FAILED",
        FAILED / "runtime.log",
        CURRENT_GENERIC,
        HISTORICAL_COMPUTE,
        HISTORICAL_LOGICAL,
        PRIOR / "fragments.sha256",
        PRIOR / "candle.log",
    )
    if any(not path.is_file() or path.is_symlink() for path in required):
        return fail("tag9_evidence_missing")
    if (
        sha256(CURRENT_GENERIC) != CURRENT_GENERIC_SHA256
        or sha256(HISTORICAL_LOGICAL) != HISTORICAL_LOGICAL_SHA256
    ):
        return fail("tag9_source_identity_drift")

    generic = CURRENT_GENERIC.read_text(encoding="utf-8")
    compute = HISTORICAL_COMPUTE.read_text(encoding="utf-8")
    logical = HISTORICAL_LOGICAL.read_text(encoding="utf-8")
    if (
        "candle_q_analytic_instruction_tag center_instruction = 9" not in generic
        or "Cexp_eq center_instruction (Cexp_num 9)" not in compute
        or "Cexp_pair (Cexp_num 9)" not in logical
    ):
        return fail("tag9_collision_signature_drift")

    failed_log = (FAILED / "runtime.log").read_text(
        encoding="utf-8", errors="replace"
    )
    if (
        failed_log.count("CANDLE_RESTORE_INPUT_ACK nonce=") != 1
        or failed_log.count("EXCEPTION: Failure \"TAC_PROOF: Unsolved goals\"") != 1
        or failed_log.count(
            "- Finished loading candle/"
            "cv_compute_analytic_expr_case10173_historical_dihedral_item_sound.ml"
        ) != 1
        or "HISTORICAL_PRODUCTION_CONTRACT_CHECKPOINT_READY" in failed_log
    ):
        return fail("tag9_failed_run_signature")

    prior_fragments = (PRIOR / "fragments.sha256").read_text(encoding="utf-8")
    prior_log = (PRIOR / "candle.log").read_text(
        encoding="utf-8", errors="replace"
    )
    if (
        prior_fragments.count(PRIOR_GENERIC_SHA256) != 1
        or prior_fragments.count(HISTORICAL_LOGICAL_SHA256) != 1
        or prior_log.count("CANDLE_CV_CASE10173_HISTORICAL_PROGRAM_LOGICAL_SOUND_OK")
        != 1
    ):
        return fail("tag9_prior_proof_signature")

    print("status=1")
    print("error=historical_private_tag9_collides_with_matan_tag9")
    print("failed_stage_source_count=1")
    print("prior_exact_logical_proof_count=1")
    print("prior_generic_tag9_branch_count=0")
    print("current_generic_tag9_branch_count=1")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
