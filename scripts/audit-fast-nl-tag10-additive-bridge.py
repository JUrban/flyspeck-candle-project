#!/usr/bin/env python3
"""Authenticate the bounded additive tag-10 CakeML proof boundary."""

from __future__ import annotations

import hashlib
import pathlib
import subprocess


WORKTREE = pathlib.Path(
    "/project/worktrees/cakeml-direct-fast-nl-tag10-additive-v1"
)
SCRATCH = pathlib.Path(
    "/project/worktrees/cakeml-direct-fast-nl-integration-v1/"
    "candle/prover/compute/tag10_probe_scratch"
)
BASE_HEAD = "b3fb54e9f822fd462b929843e816d1fa1dd46cfd"
HEAD = "a4c3d40dc90b8dd68ee5d4632f2d178d1e422c2a"
PREFIX = "candle/prover/compute/"
FILES = {
    PREFIX + "compute_registeredCase10173HistoricalChunk16Tag10DataScript.sml":
        "5bc1e8af5f6a9bf038c96077a86d1e7eea00c9ae4c66322c7e7457975b8bd203",
    PREFIX + "compute_registeredCase10173Tag10DataIdentityScript.sml":
        "9db003dac59bea87e86632d042e45b97bb04e983edf2654fcf0bbbf7a80f3510",
    PREFIX + "compute_registeredCase10173Tag10DispatchProbeScript.sml":
        "67525ea9f27c9666e9bd550c429ec5a2e76dc0261f0ef3aafe456798bfe64305",
    PREFIX + "compute_registeredCase10173Tag10HistStepEvalScript.sml":
        "cc1b06f44aaf7e5c7eed520c4f59eda85a5b9b08262ce0cc19858d9318c738e9",
}
LOGS = {
    "tag10-probe-build.log": (
        "registered_case10173_tag10_fast_eval_hit",
        "registered_case10173_old_fast_eval_rejects_tag10_ceqs",
    ),
    "tag10-data-identity-build.log": (
        "registered_case10173_old_and_tag10_input_equal",
        "registered_case10173_old_and_tag10_expected_result_equal",
        "registered_case10173_old_and_tag10_equations_differ",
    ),
    "tag10-hist-step-eval-build.log": (
        "registered_case10173_tag10_hist_step_special_eval_from_item",
        "registered_case10173_tag10_hist_step_ordinary_eval_from_step",
    ),
}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def main() -> int:
    head = subprocess.check_output(
        ["git", "-C", str(WORKTREE), "rev-parse", "HEAD"], text=True
    ).strip()
    status = subprocess.check_output(
        ["git", "-C", str(WORKTREE), "status", "--porcelain"], text=True
    )
    changed = set(
        subprocess.check_output(
            ["git", "-C", str(WORKTREE), "diff", "--name-only", BASE_HEAD, HEAD],
            text=True,
        ).splitlines()
    )
    if head != HEAD or status or changed != set(FILES):
        return fail("additive_repository_contract")

    for logical, expected in FILES.items():
        path = WORKTREE / logical
        if not path.is_file() or path.is_symlink() or sha256(path) != expected:
            return fail(f"additive_source_identity:{logical}")
        text = path.read_text(encoding="utf-8")
        if "new_axiom" in text or "cheat" in text.lower() or "admit" in text.lower():
            return fail(f"untrusted_proof_escape:{logical}")

    original = (
        WORKTREE / PREFIX / "compute_registeredCase10173HistoricalChunk16DataScript.sml"
    )
    base_original = subprocess.check_output(
        ["git", "-C", str(WORKTREE), "show", f"{BASE_HEAD}:{PREFIX}compute_registeredCase10173HistoricalChunk16DataScript.sml"]
    )
    if original.read_bytes() != base_original:
        return fail("original_registration_data_changed")

    identity = (WORKTREE / list(FILES)[1]).read_text(encoding="utf-8")
    if (
        identity.count("old_and_tag10_input_equal") != 1
        or identity.count("old_and_tag10_expected_result_equal") != 1
        or identity.count("old_and_tag10_equations_differ") != 1
    ):
        return fail("identity_partition_contract")

    for name, markers in LOGS.items():
        path = SCRATCH / name
        if not path.is_file() or path.is_symlink():
            return fail(f"missing_build_log:{name}")
        text = path.read_text(encoding="utf-8", errors="replace")
        if "status=1" in text or "FAILED" in text or "Error:" in text:
            return fail(f"failed_build_log:{name}")
        for marker in markers:
            if text.count(marker) < 1:
                return fail(f"missing_theorem_marker:{name}:{marker}")

    scratch_step = SCRATCH / "compute_registeredCase10173Tag10HistStepEvalScript.sml"
    if sha256(scratch_step) != FILES[PREFIX + scratch_step.name]:
        return fail("validated_step_source_identity")

    print("status=0")
    print(f"candidate_head={HEAD}")
    print("changed_source_count=4")
    print("original_registration_data_changed=false")
    print("tag10_input_identity=equal")
    print("tag10_expected_result_identity=equal")
    print("tag10_equation_identity=distinct")
    print("focused_theory_builds=3")
    print("declared_axiom_growth=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
