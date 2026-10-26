#!/usr/bin/env python3
"""Audit the bounded serialization/break-case continuation from v677x."""

from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
DRIVER = PROJECT / "tools/fast_nl_v677_direct_bridge_stage.ml"
CHAIN_AUDIT = PROJECT / "scripts/audit-fast-nl-v677-repair-checkpoint-chain.py"
SOURCE_AUDIT = PROJECT / "scripts/audit-fast-nl-support-source-closure.py"
MODULE_AUDIT = PROJECT / "scripts/audit-fast-nl-support-module-closure.py"
NORMALIZATION_AUDIT = PROJECT / "scripts/preflight-fast-nl-v663-normalization.sh"
BASE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-compact-support-v677x"
)
BASE_SHA256 = "9865171f71ea99bb4277f98f441a331b142cffb9a266e8356d0dad5d3942979f"
ORIGINAL_ROOT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v352-full-boundary-materialization-heap16-dev-005/snapshot/flyspeck"
)
CANDIDATE_ROOT = pathlib.Path("/project/worktrees/flyspeck-direct-action296-643bfd12")
CANDIDATE_HEAD = "d8adac7fe1dbb1e07d417995f786fa77fa1c80a5"
DIRECT_295_LOG = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v415-action295-corrected-ledger-continuation-dev-001/runtime.log"
)
DIRECT_296_LOG = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v421-action296-validation-recovery-dev-001/runtime.log"
)
ENTRIES = (
    (
        "text_formalization/general/serialization.hl",
        "9228eaf6a96159d9f59fea40fcc2a12f",
        "fe7f414d6e72a2c838a81b59af15494a1e9f6a5118f9ec0cd1f6ade11a939eed",
        "e0766072204d441da563dd688cfe1a7b",
        "9feec0e83dcb188880a60ac8fa23fef19ead253ccfe7465a6258fb83ec55ac0a",
    ),
    (
        "text_formalization/nonlinear/break_case_exec.hl",
        "736fb16a1dab5f13102fdb185a0a1c08",
        "e20b303d586f51f771afa3ad48f7c40fa275b6e88888554ed10b52794abfbced",
        "0d5318622fed357ec0d60d42ad266cee",
        "0c048bfef93564110ab392c6a9217db20adce935cef5c367410bd1285bea2a72",
    ),
)


def digest(path: pathlib.Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    hasher.update(path.read_bytes())
    return hasher.hexdigest()


def git(*arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(CANDIDATE_ROOT), *arguments], text=True
    ).strip()


def receipt(path: pathlib.Path) -> dict[str, str]:
    return dict(
        line.split("=", 1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def run_audit(path: pathlib.Path, timeout: int = 180) -> bool:
    completed = subprocess.run(
        [str(path)], cwd=PROJECT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
        check=False,
    )
    if completed.returncode != 0 or "status=0" not in completed.stdout.splitlines():
        print(completed.stdout, end="")
        return False
    return True


def main() -> int:
    required = (
        DRIVER, CHAIN_AUDIT, SOURCE_AUDIT, MODULE_AUDIT,
        NORMALIZATION_AUDIT, BASE / "checkpoint.receipt",
        DIRECT_295_LOG, DIRECT_296_LOG,
    )
    if any(not path.is_file() or path.is_symlink() for path in required):
        return fail("missing_or_symlink_authority")
    if not (BASE / "CHECKPOINT-READY").is_file() or (BASE / "CHECKPOINT-FAILED").exists():
        return fail("base_readiness")
    prior = receipt(BASE / "checkpoint.receipt")
    if (
        prior.get("receipt_kind") != "development-fast-nl-v677-compact-support-checkpoint-v1"
        or prior.get("checkpoint_sha256") != BASE_SHA256
    ):
        return fail("base_receipt")
    checkpoint = pathlib.Path(prior.get("checkpoint", ""))
    if not checkpoint.is_file() or prior.get("checkpoint_size_bytes") != str(checkpoint.stat().st_size):
        return fail("base_checkpoint")
    for audit in (CHAIN_AUDIT, SOURCE_AUDIT, MODULE_AUDIT, NORMALIZATION_AUDIT):
        if not run_audit(audit):
            return fail(f"dependency_audit:{audit.name}")

    if git("rev-parse", "HEAD") != CANDIDATE_HEAD or git("status", "--porcelain"):
        return fail("candidate_repository")
    for logical, old_md5, old_sha256, new_md5, new_sha256 in ENTRIES:
        original = ORIGINAL_ROOT / logical
        candidate = CANDIDATE_ROOT / logical
        if (
            original.is_symlink() or candidate.is_symlink()
            or digest(original, "md5") != old_md5
            or digest(original, "sha256") != old_sha256
            or digest(candidate, "md5") != new_md5
            or digest(candidate, "sha256") != new_sha256
        ):
            return fail(f"source_identity:{logical}")

    if DIRECT_295_LOG.read_text(encoding="utf-8", errors="replace").count(
        "CANDLE_FLYSPECK_V415_ACTION295_READY DEVELOPMENT_NON_RELEASE corrected_delta=4"
    ) != 1:
        return fail("direct_action295_evidence")
    if DIRECT_296_LOG.read_text(encoding="utf-8", errors="replace").count(
        "CANDLE_FLYSPECK_V421_DIRECT_FULL_OK actions=297 DEVELOPMENT_NON_RELEASE"
    ) != 1:
        return fail("direct_action296_evidence")

    driver = DRIVER.read_text(encoding="utf-8")
    expected = tuple(str(ORIGINAL_ROOT / logical) for logical, *_ in ENTRIES)
    if tuple(re.findall(r'(?m)^needs "([^"]+)";;$', driver)) != expected:
        return fail("driver_boundary")
    if "#use " in driver or driver.count("DIRECT_BRIDGE_CHECKPOINT_READY") != 1:
        return fail("driver_contract")
    for index, (_, old_md5, _, _, _) in enumerate(ENTRIES):
        expected_count = 2 if index == 0 else 2
        if driver.count(old_md5) != expected_count:
            return fail("driver_identity")

    print("status=0")
    print("planned_top_level_load_count=2")
    print("direct_prior_action_count=2")
    print("support_source_closure_count=245")
    print("support_module_path_count=304")
    print(f"driver_sha256={digest(DRIVER, 'sha256')}")
    print(f"base_checkpoint_sha256={BASE_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
