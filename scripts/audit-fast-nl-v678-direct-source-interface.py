#!/usr/bin/env python3
"""Audit the bounded direct-source interface that avoids legacy NL replay."""

from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
ROOT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001"
)
BASE = ROOT / "post-compact-support-v677x"
BASE_SHA256 = "9865171f71ea99bb4277f98f441a331b142cffb9a266e8356d0dad5d3942979f"
DRIVER = PROJECT / "tools/fast_nl_v678_direct_source_interface_stage.ml"
CHAIN_AUDIT = PROJECT / "scripts/audit-fast-nl-v677-repair-checkpoint-chain.py"
SOURCE_AUDIT = PROJECT / "scripts/audit-fast-nl-support-source-closure.py"
MODULE_AUDIT = PROJECT / "scripts/audit-fast-nl-support-module-closure.py"
NORMALIZATION_AUDIT = PROJECT / "scripts/preflight-fast-nl-v663-normalization.sh"
FAILED_RUN = ROOT / "post-direct-bridge-v677y"
DIRECT_ACTION_RUN = pathlib.Path(
    "/project/flyspeck-candle-runs/v419-action296-correct-axiom-contract-dev-001"
)
DIRECT_ACTION_TIMING = pathlib.Path(
    "/project/flyspeck-candle-runs/v417-action296-static-dependencies-dev-001/failure.receipt"
)
ORIGINAL_ROOT = pathlib.Path("/project/worktrees/candle-direct-fast-nl-runtime-v1")
CANDIDATE_ROOT = pathlib.Path(
    "/project/worktrees/candle-fast-nl-direct-source-interface-v1"
)
CANDIDATE_HEAD = "5ca0e5770ce66925c3a5efd01073fb394f9105b4"
LOGICAL = "candle/cv_compute_flyspeck_direct_source_compat.ml"
ORIGINAL_SHA256 = "e69d6d5e067984e46812213e7c93f2cb7233928aed1631e25d4c9bdda6d107c4"
CANDIDATE_SHA256 = "5963ac4bf0ec070dd1f84731da9844b88ee6a325bbb2409f2058c2588d33cd89"
ORIGINAL_MD5 = "6da54e8de2098d8281bc7e4a8a4dd62a"
CANDIDATE_MD5 = "9c9f370e594809f955f3c9b6a1e1261d"
BREAK_CASE_SOURCE = pathlib.Path(
    "/project/worktrees/flyspeck-direct-action296-643bfd12/"
    "text_formalization/nonlinear/break_case_exec.hl"
)
THEOREMS = (
    ("subat_rules", "candle_direct_subat_rules"),
    ("subat_explicit", "candle_direct_subat_explicit"),
    ("bisect_left_frac", "candle_direct_bisect_left_frac"),
    ("bisect_right_frac", "candle_direct_bisect_right_frac"),
    ("ineq6m", "candle_direct_ineq6m"),
    ("ineq9m", "candle_direct_ineq9m"),
)


def digest(path: pathlib.Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    value.update(path.read_bytes())
    return value.hexdigest()


def receipt(path: pathlib.Path) -> dict[str, str]:
    return dict(
        line.split("=", 1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )


def run_audit(path: pathlib.Path, timeout: int = 180) -> bool:
    completed = subprocess.run(
        [str(path)], cwd=PROJECT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=timeout, check=False,
    )
    if completed.returncode != 0 or "status=0" not in completed.stdout.splitlines():
        print(completed.stdout, end="")
        return False
    return True


def theorem_quote(source: str, name: str) -> str | None:
    match = re.search(
        rf"(?s)\blet\s+{re.escape(name)}\s*=\s*prove_by_refinement\s*\(\s*`(.*?)`\s*,",
        source,
    )
    if match is None:
        return None
    return re.sub(r"\s+", "", match.group(1))


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def main() -> int:
    original = ORIGINAL_ROOT / LOGICAL
    candidate = CANDIDATE_ROOT / LOGICAL
    required = (
        DRIVER, original, candidate, BREAK_CASE_SOURCE, BASE / "checkpoint.receipt",
        FAILED_RUN / "CHECKPOINT-FAILED", FAILED_RUN / "runtime.log",
        DIRECT_ACTION_RUN / "runtime.log", DIRECT_ACTION_TIMING,
    )
    if any(not path.is_file() or path.is_symlink() for path in required):
        return fail("missing_or_symlink_input")
    if not (BASE / "CHECKPOINT-READY").is_file() or (BASE / "CHECKPOINT-FAILED").exists():
        return fail("base_readiness")
    observed = receipt(BASE / "checkpoint.receipt")
    if (
        observed.get("receipt_kind")
        != "development-fast-nl-v677-compact-support-checkpoint-v1"
        or observed.get("checkpoint_sha256") != BASE_SHA256
    ):
        return fail("base_receipt")
    for audit in (CHAIN_AUDIT, SOURCE_AUDIT, MODULE_AUDIT, NORMALIZATION_AUDIT):
        if not run_audit(audit):
            return fail(f"dependency_audit:{audit.name}")

    head = subprocess.check_output(
        ["git", "-C", str(CANDIDATE_ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    status = subprocess.check_output(
        ["git", "-C", str(CANDIDATE_ROOT), "status", "--porcelain"], text=True
    )
    if head != CANDIDATE_HEAD or status:
        return fail("candidate_repository")
    if (
        digest(original) != ORIGINAL_SHA256
        or digest(candidate) != CANDIDATE_SHA256
        or digest(original, "md5") != ORIGINAL_MD5
        or digest(candidate, "md5") != CANDIDATE_MD5
    ):
        return fail("interface_source_identity")

    break_case_text = BREAK_CASE_SOURCE.read_text(encoding="utf-8")
    candidate_text = candidate.read_text(encoding="utf-8")
    candidate_executable_text = candidate_text.replace(
        "[Break_case_exec.ineq_conv]", "[legacy inequality conversion]"
    )
    if "Break_case_exec." in candidate_executable_text:
        return fail("candidate_retains_break_case_dependency")
    for old_name, new_name in THEOREMS:
        if theorem_quote(break_case_text, old_name) != theorem_quote(candidate_text, new_name):
            return fail(f"theorem_statement_drift:{old_name}")

    failed_log = (FAILED_RUN / "runtime.log").read_text(
        encoding="utf-8", errors="replace"
    )
    if (
        failed_log.count("dynamic use_file_b is disabled by the static manifest:") != 1
        or "nonlinear/prep.hl" not in failed_log
        or "CANDLE_FLYSPECK_V677_DIRECT_BRIDGE_CHECKPOINT_READY" in failed_log
    ):
        return fail("v677y_failure_evidence")
    action_log = (DIRECT_ACTION_RUN / "runtime.log").read_text(
        encoding="utf-8", errors="replace"
    )
    required_action_lines = (
        "- Flyspeck source action complete: nonlinear/prep.hl",
        "- Flyspeck source action complete: nonlinear/break_case_type.hl",
        "- Flyspeck source action complete: nonlinear/break_case_log.hl",
        "- Flyspeck source action complete: nonlinear/break_case_exec.hl",
    )
    if any(action_log.count(line) != 1 for line in required_action_lines):
        return fail("direct_action296_dependency_evidence")
    action_failure = receipt(DIRECT_ACTION_TIMING)
    if float(action_failure.get("action296_source_runtime_wall_seconds", "0")) < 13000:
        return fail("direct_action296_elapsed_evidence")

    driver = DRIVER.read_text(encoding="utf-8")
    needs = re.findall(r'(?m)^needs "([^"]+)";;$', driver)
    if needs != ["candle/cv_compute_analytic_expr_case10173_fixture.ml"]:
        return fail("driver_boundary")
    for forbidden in ("general/serialization.hl", "nonlinear/break_case_exec.hl"):
        if forbidden in driver:
            return fail(f"driver_legacy_replay:{forbidden}")
    if (
        driver.count(str(original)) != 1
        or driver.count(str(candidate)) != 1
        or driver.count("DIRECT_SOURCE_INTERFACE_CHECKPOINT_READY") != 1
        or "#use " in driver
        or "#flyspeck_needs" in driver
    ):
        return fail("driver_contract")

    print("status=0")
    print("logical_support_load_count=2")
    print("copied_theorem_statement_count=6")
    print("legacy_replay_source_count=0")
    print("prior_legacy_runtime_lower_bound_seconds=13000")
    print(f"driver_sha256={digest(DRIVER)}")
    print(f"candidate_sha256={CANDIDATE_SHA256}")
    print(f"base_checkpoint_sha256={BASE_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
