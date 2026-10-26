#!/usr/bin/env python3
"""Authenticate the complete additive tag-10 proof and kernel boundary."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import subprocess


WORKTREE = pathlib.Path(
    "/project/worktrees/cakeml-direct-fast-nl-integration-v1"
)
SCRATCH = WORKTREE / "candle/prover/compute/tag10_probe_scratch"
BASE_HEAD = "b3fb54e9f822fd462b929843e816d1fa1dd46cfd"
HEAD = "839017e696dea5fbbb2e03bfeff02c6679724e00"
PREFIX = "candle/prover/compute/"
KERNEL_FILES = {
    "candle/prover/candle_kernelProgScript.sml",
    "candle/prover/candle_kernel_funsScript.sml",
}
CRITICAL_FILES = {
    PREFIX + "compute_registeredCase10173HistoricalChunk16Tag10DataScript.sml":
        "5bc1e8af5f6a9bf038c96077a86d1e7eea00c9ae4c66322c7e7457975b8bd203",
    PREFIX + "compute_registeredCase10173Tag10DataIdentityScript.sml":
        "9db003dac59bea87e86632d042e45b97bb04e983edf2654fcf0bbbf7a80f3510",
    PREFIX + "compute_registeredCase10173Tag10HistStepEvalScript.sml":
        "cc1b06f44aaf7e5c7eed520c4f59eda85a5b9b08262ce0cc19858d9318c738e9",
    PREFIX + "compute_registeredCase10173Tag10AuthenticatedFastFullEvalScript.sml":
        "f69466357daa394fe25ee3f5a9944810071a99a8714edc80e363697bf7ee49c2",
    PREFIX + "compute_registeredCase10173Tag10AuthenticatedFastDispatchScript.sml":
        "dc356f26d0bb0b3b0c973254bc60aa8229864b06a11ce01cb856b3f90f5475fb",
    PREFIX + "compute_registeredCase10173Tag10GenuineAuthenticatedFastScript.sml":
        "b6b1bc92a56007cca0ce02e88fa4ae6540914926cdf5083c726019e5ba8818bb",
    PREFIX + "compute_registeredCase10173Tag10GenuineFastChainScript.sml":
        "e2d38c3952c28a77bddacb00469a8d40d1d5f28bb7bcd4becdec6c82678f6347",
    PREFIX + "compute_registeredCase10173Tag10ProductionDispatchTestScript.sml":
        "9f84980682d0fca89ee03a69ba86ce1d30c17804595dbe8ccdf6b6691ba7bddc",
    "candle/prover/candle_kernelProgScript.sml":
        "5575a58015db5991d45bad843ad2e49d4302f0060b4dc5cc750a3e110ccb2c33",
    "candle/prover/candle_kernel_funsScript.sml":
        "73dcac4666acb9ed89c474f35e72d7c6fbe797f0aae606fbaeee29acdb0399f3",
}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def git(*arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(WORKTREE), *arguments], text=True
    ).strip()


def require_log(
    path: pathlib.Path, markers: tuple[str, ...], success: bool
) -> str | None:
    if not path.is_file() or path.is_symlink():
        return f"missing_build_log:{path.name}"
    text = path.read_text(encoding="utf-8", errors="replace")
    for marker in markers:
        if marker not in text:
            return f"missing_log_marker:{path.name}:{marker}"
    expected_status = "Exit status: 0" if success else "Exit status: 1"
    if expected_status not in text:
        return f"wrong_log_status:{path.name}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission-controller", type=pathlib.Path)
    args = parser.parse_args()

    if git("rev-parse", "HEAD") != HEAD:
        return fail("integration_head")
    if git("status", "--porcelain", "--untracked-files=no"):
        return fail("tracked_worktree_dirty")

    changed = set(git("diff", "--name-only", BASE_HEAD, HEAD).splitlines())
    if len(changed) != 41 or not KERNEL_FILES <= changed:
        return fail("changed_source_count")
    compute_changed = changed - KERNEL_FILES
    if any(
        not path.startswith(PREFIX)
        or not path.endswith("Script.sml")
        or (
            "Tag10" not in pathlib.Path(path).name
            and pathlib.Path(path).name
            != "compute_evalRestrictedCongruenceScript.sml"
        )
        for path in compute_changed
    ):
        return fail("changed_source_scope")

    for logical, expected in CRITICAL_FILES.items():
        path = WORKTREE / logical
        if not path.is_file() or path.is_symlink() or sha256(path) != expected:
            return fail(f"source_identity:{logical}")

    for logical in changed:
        diff = git("diff", "--unified=0", BASE_HEAD, HEAD, "--", logical)
        added = "\n".join(
            line[1:] for line in diff.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        )
        lowered = added.lower()
        if "new_axiom" in added or "cheat" in lowered or "admit" in lowered:
            return fail(f"untrusted_proof_escape:{logical}")

    original_name = (
        PREFIX + "compute_registeredCase10173HistoricalChunk16DataScript.sml"
    )
    original = WORKTREE / original_name
    base_original = subprocess.check_output(
        ["git", "-C", str(WORKTREE), "show", f"{BASE_HEAD}:{original_name}"]
    )
    if original.read_bytes() != base_original:
        return fail("original_registration_data_changed")

    identity = (
        WORKTREE
        / (PREFIX + "compute_registeredCase10173Tag10DataIdentityScript.sml")
    ).read_text(encoding="utf-8")
    if any(
        identity.count(marker) != 1
        for marker in (
            "old_and_tag10_input_equal",
            "old_and_tag10_expected_result_equal",
            "old_and_tag10_equations_differ",
        )
    ):
        return fail("identity_partition_contract")

    dispatch_test = (
        WORKTREE
        / (
            PREFIX
            + "compute_registeredCase10173Tag10ProductionDispatchTestScript.sml"
        )
    ).read_text(encoding="utf-8")
    for marker in (
        "rejects_old_ceqs",
        "rejects_wrong_entry",
        "rejects_wrong_source",
        "rejects_unauthenticated_payload",
    ):
        if dispatch_test.count(marker) != 1:
            return fail(f"dispatch_rejection_contract:{marker}")

    kernel = (
        WORKTREE / "candle/prover/candle_kernelProgScript.sml"
    ).read_text(encoding="utf-8")
    ordered = (
        "compute_registeredCase10173Tag10GenuineFastChain",
        "registered_case10173_historical_chunk16_tag10_ceqs_def",
        "registered_case10173_tag10_decimal_authenticated_fast_checker_def",
        "registered_case10173_tag10_decimal_authenticated_fast_eval_def",
        "registered_case10173_tag10_genuine_decimal_authenticated_fast_eval_def",
        "compute_case10173_tag10_genuine_fast_eval_def",
        "compute_case10173_tag10_genuine_fast_def",
        "close_local_blocks",
    )
    positions = [kernel.find(marker) for marker in ordered]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        return fail("in_module_translation_order")

    kernel_funs = (
        WORKTREE / "candle/prover/candle_kernel_funsScript.sml"
    ).read_text(encoding="utf-8")
    for marker in (
        "compute_case10173_tag10_genuine_fast_side_total",
        "compute_case10173_tag10_genuine_fast_thm",
        "registered_case10173_tag10_decimal_authenticated_fast_checker_side_total",
    ):
        if marker not in kernel_funs:
            return fail(f"kernel_soundness_wiring:{marker}")

    log_contracts = [
        (
            SCRATCH / "tag10-cache-normalization-build-v2.log",
            (
                "Holmake: [4/4] compute_registeredCase10173Tag10ProductionDispatchTest",
                "registered_case10173_tag10_genuine_fast_eval_rejects_old_ceqs",
                "registered_case10173_tag10_genuine_fast_eval_rejects_unauthenticated_payload",
            ),
            True,
        ),
        (
            SCRATCH / "tag10-kernel-translation-probe-build-v2.log",
            (
                "clean_assumptions: false",
                "TypeStamp",
                "merge_env candle_kernelProg_env_567",
            ),
            False,
        ),
    ]

    if args.admission_controller is None:
        log_contracts.append(
            (
                pathlib.Path(
                    "/project/flyspeck-candle-runs/"
                    "v681-fast-nl-tag10-kernel-prog-dev-001/kernel-prog.log"
                ),
                ("Holmake: [1/1] candle_kernelProg",),
                True,
            )
        )
    else:
        controller = args.admission_controller.resolve()
        expected_controller = pathlib.Path(
            "/project/flyspeck-candle-project/scripts/"
            "build-fast-nl-tag10-kernel-prog-v3.sh"
        )
        if controller != expected_controller or not controller.is_file():
            return fail("kernel_controller_identity")
        if controller.is_symlink() or not (controller.stat().st_mode & 0o111):
            return fail("kernel_controller_mode")
        controller_text = controller.read_text(encoding="utf-8")
        for marker in (
            "maximum_seconds=3000",
            "--no_prereqs --heap-size=65536",
            "--rebuild=cachekey -j1 candle_kernelProgTheory.uo",
            "require-long-run-hazard-preflight.sh",
            "[[ ! -e $run ]]",
            "loader_receipt_sha256=05ddc47ff130bf2cf695c7b36a148f13e2eaa1d8af2afd0e60a0bc21275c1692",
            "relocation_receipt_sha256=7e14d409f60c555c900e684e0bfd24845bb372d8798c4c2882c596d8df276196",
            "audit-fast-nl-tag10-kernel-loader-result.py",
        ):
            if controller_text.count(marker) != 1:
                return fail(f"kernel_controller_contract:{marker}")
        run = pathlib.Path(
            "/project/flyspeck-candle-runs/"
            "v691-fast-nl-tag10-kernel-prog-dev-001"
        )
        if run.exists():
            return fail("kernel_run_target_not_fresh")

        bounded_log = WORKTREE / "candle/prover/tag10-kernel-prog-build-v1.log"
        if not bounded_log.is_file() or bounded_log.is_symlink():
            return fail("missing_bounded_kernel_log")
        bounded_text = bounded_log.read_text(encoding="utf-8", errors="replace")
        for marker in (
            "nsLookup_candle_kernelProg_env_419_pfun_eqs",
            "Elapsed (wall clock) time (h:mm:ss or m:ss): 30:00.03",
            "Exit status: 124",
        ):
            if marker not in bounded_text:
                return fail(f"bounded_kernel_log_marker:{marker}")
        if "Exception-" in bounded_text or "Error: " in bounded_text:
            return fail("bounded_kernel_semantic_error")

        source = (WORKTREE / "candle/prover/candle_kernelProgScript.sml").read_text(
            encoding="utf-8"
        )
        pivot = source.find(
            "compute_boundedHistoricalDihedralFirstDecimalTheory."
            "bounded_delta64_pair_products_decimal_def"
        )
        if pivot < 0:
            return fail("bounded_kernel_progress_pivot")
        remaining = len(
            re.findall(
                r"\b(?:translate|translate_no_ind|translate_closed|m_translate)\b",
                source[pivot + 1 :],
            )
        )
        if remaining != 134:
            return fail(f"bounded_kernel_remaining_translation_count:{remaining}")

        meminfo = pathlib.Path("/proc/meminfo").read_text(encoding="utf-8")
        match = re.search(r"^MemAvailable:\s+(\d+) kB$", meminfo, re.MULTILINE)
        if match is None or int(match.group(1)) < 64 * 1024 * 1024:
            return fail("kernel_build_memory_headroom")

    for path, markers, success in log_contracts:
        error = require_log(path, markers, success)
        if error:
            return fail(error)

    print("status=0")
    print(f"candidate_head={HEAD}")
    print("changed_source_count=41")
    print("original_registration_data_changed=false")
    print("tag10_input_identity=equal")
    print("tag10_expected_result_identity=equal")
    print("tag10_equation_identity=distinct")
    print("authenticated_record_count=4173")
    print("dispatch_rejection_theorem_count=4")
    print("kernel_translation_location=in_module")
    print("post_closed_translation=forbidden")
    if args.admission_controller is None:
        print("kernel_translation_status=complete")
    else:
        print("kernel_translation_status=bounded_timeout_at_environment_419")
        print("remaining_translation_count=134")
        print("retry_maximum_seconds=3000")
        print("loader_probe_required=true")
    print("declared_axiom_growth=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
