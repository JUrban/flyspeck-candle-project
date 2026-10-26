#!/usr/bin/env python3
"""Preflight the isolated tag-10 historical-sentinel proof candidate."""

from __future__ import annotations

import hashlib
import pathlib
import subprocess


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
CANDIDATE = pathlib.Path("/project/worktrees/candle-fast-nl-historical-tag10-v1")
BASE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "cv-historical-checked-stable-5aa38ffb-checkpoint-v1-dev-001"
)
RESIDUAL = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679b-fast-nl-tag9-residual-diagnostic-dev-001"
)
DRIVER = PROJECT / "tools/fast_nl_v679c_tag10_logical_probe.ml"
HEAD = "85276ec10e3fd2f6df6114350aa773da9b327a4e"
BASE_HEAD = "172d6a14064575a1dabca7e8e16fd9088070f415"
BASE_SHA256 = (
    "48a67f3189bab4c3910fcffe924be38cd64986cef9f9b57b5cb977e9d72979d9"
)
FILES = {
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_compute.ml":
        "5bbf53ebc14fa98bad9f65b3984f4819d519c75e5490e51af0a1a26b5444e676",
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_logical_sound.ml":
        "21e5973145500e77250c746ca36b494dc1a3c2a3405d359d0f7035227cc731df",
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_sound.ml":
        "83de4cd2c5d0b6041e921b59f0e608968f25f7fbe921f6d6c410bf27631e558a",
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_analytic_sound.ml":
        "4a21c93a975fa14e04e9b02148d650a5961ca1e16c4e045838ddcb276b0cd334",
}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def main() -> int:
    required = (
        DRIVER,
        BASE / "CHECKPOINT-READY",
        BASE / "checkpoint.sha256",
        BASE / "checkpoint-seal.receipt",
        RESIDUAL / "PROBE-PASSED",
        RESIDUAL / "tag9-residual.receipt",
        RESIDUAL / "runtime.log",
    )
    if any(not path.is_file() or path.is_symlink() for path in required):
        return fail("missing_or_symlinked_authority")

    head = subprocess.check_output(
        ["git", "-C", str(CANDIDATE), "rev-parse", "HEAD"], text=True
    ).strip()
    status = subprocess.check_output(
        ["git", "-C", str(CANDIDATE), "status", "--porcelain"], text=True
    )
    changed = set(
        subprocess.check_output(
            ["git", "-C", str(CANDIDATE), "diff", "--name-only", BASE_HEAD, HEAD],
            text=True,
        ).splitlines()
    )
    if head != HEAD or status or changed != set(FILES):
        return fail("candidate_repository_contract")
    for logical, expected in FILES.items():
        path = CANDIDATE / logical
        if not path.is_file() or path.is_symlink() or sha256(path) != expected:
            return fail(f"candidate_source_identity:{logical}")

    compute = (CANDIDATE / next(iter(FILES))).read_text(encoding="utf-8")
    logical = (CANDIDATE / list(FILES)[1]).read_text(encoding="utf-8")
    program_sound = (CANDIDATE / list(FILES)[2]).read_text(encoding="utf-8")
    public_program = (
        CANDIDATE / "candle/cv_compute_analytic_expr_program_compute.ml"
    ).read_text(encoding="utf-8")
    if (
        compute.count("Cexp_num 10") != 5 or "Cexp_num 9" in compute
        or logical.count("Cexp_num 10") != 1 or "Cexp_num 9" in logical
        or program_sound.count("Cexp_num 10") != 1 or "Cexp_num 9" in program_sound
        or "Candle_analytic_program_matan =\n     Cexp_num 9" not in public_program
    ):
        return fail("tag_partition_contract")

    if BASE_SHA256 not in (BASE / "checkpoint.sha256").read_text(encoding="utf-8"):
        return fail("base_checkpoint_identity")
    residual_log = (RESIDUAL / "runtime.log").read_text(
        encoding="utf-8", errors="replace"
    )
    if (
        residual_log.count("CANDLE_FLYSPECK_V679B_TAG9_RESIDUAL goal=") != 1
        or "Candle_analytic_program_matan" not in residual_log
        or residual_log.count("CANDLE_FLYSPECK_V679B_TAG9_RESIDUAL_DIAGNOSTIC_OK")
        != 1
    ):
        return fail("residual_goal_evidence")

    driver = DRIVER.read_text(encoding="utf-8")
    if (
        driver.count(str(CANDIDATE)) != 1
        or driver.count("TAG10_LOGICAL_PROOF_OK") != 1
        or driver.count("axioms ()") != 2
        or "new_axiom" in driver
    ):
        return fail("driver_contract")

    print("status=0")
    print("changed_source_count=4")
    print("historical_private_tag=10")
    print("public_matan_tag=9")
    print("residual_matan_goal_count=1")
    print("declared_axiom_growth=0")
    print(f"candidate_head={HEAD}")
    print(f"driver_sha256={sha256(DRIVER)}")
    print(f"base_checkpoint_sha256={BASE_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
