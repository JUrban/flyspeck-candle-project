#!/usr/bin/env python3
"""Cheap fail-closed audit of the staged v677 matan-repair proof loads."""

from __future__ import annotations

import hashlib
import pathlib
import subprocess


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
ROOT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001"
)
REPAIR_AUDIT = PROJECT / "scripts/audit-fast-nl-v677-matan-repair.py"
HISTORICAL_AUDIT = PROJECT / "scripts/audit-fast-nl-v677-historical-sound-contract.py"
STAGES = (
    {
        "directory": ROOT / "post-pre-first-jet-v677g",
        "kind": "development-fast-nl-v677-pre-first-jet-checkpoint-v1",
        "sha256": "f0b6e5f0786acd9827d9042810c36078227849f954fa544eb5b82c11914f5cb3",
        "marker": "CANDLE_FLYSPECK_V677_PRE_FIRST_JET_CHECKPOINT_READY",
        "driver": PROJECT / "tools/fast_nl_v677_pre_first_jet_checkpoint.ml",
        "required": (
            "- Finished loading candle/cv_compute_analytic_expr_certificate_patch_compute.ml",
            "- Finished loading candle/cv_compute_analytic_expr_jet_check.ml",
        ),
        "forbidden": (
            "- Finished loading candle/cv_compute_analytic_expr_first_jet_program_compute.ml",
        ),
    },
    {
        "directory": ROOT / "post-first-jet-v677h",
        "kind": "development-fast-nl-v677-first-jet-checkpoint-v1",
        "sha256": "8bff103b1bdf6e585e7a1c67f26dd8de9c936193fecba4fe221410a32d45271e",
        "marker": "CANDLE_FLYSPECK_V677_FIRST_JET_CHECKPOINT_READY",
        "driver": PROJECT / "tools/fast_nl_v677_first_jet_stage.ml",
        "required": (
            "- Finished loading candle/cv_compute_analytic_expr_first_jet_program_compute.ml",
        ),
        "forbidden": (),
    },
    {
        "directory": ROOT / "post-pre-compile-sound-v677j",
        "kind": "development-fast-nl-v677-pre-compile-sound-checkpoint-v1",
        "sha256": "5893af20180915a40e62a2e318ff9faa64c80bf1fc617d13b27e224efbcca5ca",
        "marker": "CANDLE_FLYSPECK_V677_PRE_COMPILE_SOUND_CHECKPOINT_READY",
        "driver": PROJECT / "tools/fast_nl_v677_pre_compile_sound_checkpoint.ml",
        "required": (
            "- Finished loading candle/cv_compute_analytic_expr_fixed_scale_invariant.ml",
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_nonlinear_sound.ml",
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_certified_compute.ml",
        ),
        "forbidden": (
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_compile_sound.ml",
        ),
    },
    {
        "directory": ROOT / "post-compile-sound-v677k",
        "kind": "development-fast-nl-v677-compile-sound-checkpoint-v1",
        "sha256": "b934ae796417798dcf95952363f625431525af012e11413454fa7ca63a7d4583",
        "marker": "CANDLE_FLYSPECK_V677_COMPILE_SOUND_CHECKPOINT_READY",
        "driver": PROJECT / "tools/fast_nl_v677_compile_sound_stage.ml",
        "required": (
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_compile_sound.ml",
        ),
        "forbidden": (),
    },
    {
        "directory": ROOT / "post-fixed-algebraic-item-invariant-v677m",
        "kind": "development-fast-nl-v677-fixed-algebraic-item-invariant-checkpoint-v1",
        "sha256": "6c48608d0bc73c18d7eb02ba66f0dd6cc63ab4841c1ec7dfaae240a1bfcf316f",
        "marker": "CANDLE_FLYSPECK_V677_FIXED_ALGEBRAIC_ITEM_INVARIANT_CHECKPOINT_READY",
        "driver": PROJECT / "tools/fast_nl_v677_fixed_algebraic_item_invariant_stage.ml",
        "required": (
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_compute.ml",
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_sound.ml",
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_item_sound.ml",
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_invariant.ml",
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_item_invariant.ml",
        ),
        "forbidden": (
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_compile_sound.ml",
        ),
    },
    {
        "directory": ROOT / "post-fixed-algebraic-compile-sound-v677r",
        "kind": "development-fast-nl-v677-fixed-algebraic-compile-sound-checkpoint-v1",
        "sha256": "4a1209eae1e86f8dbb303318dce66ce43794b277395293d17077cffb09efbcfa",
        "marker": "CANDLE_FLYSPECK_V677_FIXED_ALGEBRAIC_COMPILE_SOUND_CHECKPOINT_READY",
        "driver": PROJECT / "tools/fast_nl_v677_fixed_algebraic_compile_sound_stage.ml",
        "required": (
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_program_sound.ml",
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_compile_sound.ml",
        ),
        "forbidden": (
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_compile_sound.ml",
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear_compile_sound.ml",
        ),
    },
    {
        "directory": ROOT / "post-fixed-outer-nonlinear-compile-sound-v677s",
        "kind": "development-fast-nl-v677-fixed-outer-nonlinear-compile-sound-checkpoint-v1",
        "sha256": "25e7179af6617c2983746666903ed36a2d4d70072a71b36e8be314da44c87e14",
        "marker": "CANDLE_FLYSPECK_V677_FIXED_OUTER_NONLINEAR_COMPILE_SOUND_CHECKPOINT_READY",
        "driver": PROJECT / "tools/fast_nl_v677_fixed_outer_nonlinear_compile_sound_stage.ml",
        "required": (
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_program_sound.ml",
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_compile_sound.ml",
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear_program_sound.ml",
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear_compile_sound.ml",
        ),
        "forbidden": (
            "- Finished loading candle/cv_compute_analytic_expr_certificate_variant_prepare.ml",
            "- Finished loading candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml",
        ),
    },
    {
        "directory": ROOT / "post-historical-sound-v677w",
        "kind": "development-fast-nl-v677-historical-sound-checkpoint-v1",
        "sha256": "0bd11b95aa83a1bf95d5df035f3a4639362c2f0ba076390ff80d3ffc22368bca",
        "marker": "CANDLE_FLYSPECK_V677_HISTORICAL_SOUND_CHECKPOINT_READY",
        "driver": PROJECT / "tools/fast_nl_v677_historical_sound_stage.ml",
        "required": (
            "- Finished loading candle/cv_compute_analytic_expr_fixed_scale_historical_root_four_x0_sound.ml",
            "- Finished loading candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml",
        ),
        "forbidden": (
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_variable_compact_stack_sound.ml",
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_tree_compact_correct.ml",
        ),
    },
    {
        "directory": ROOT / "post-compact-support-v677x",
        "kind": "development-fast-nl-v677-compact-support-checkpoint-v1",
        "sha256": "9865171f71ea99bb4277f98f441a331b142cffb9a266e8356d0dad5d3942979f",
        "marker": "CANDLE_FLYSPECK_V677_COMPACT_SUPPORT_CHECKPOINT_READY",
        "driver": PROJECT / "tools/fast_nl_v677_compact_support_stage.ml",
        "required": (
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_tree_compact_compute.ml",
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_tree_compact_correct.ml",
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_tree_compact_sound.ml",
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_variable_tree_sound.ml",
            "- Finished loading candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_variable_compact_stack_sound.ml",
        ),
        "forbidden": (
            "- Finished loading candle/cv_compute_analytic_expr_case10173_historical_registered_original_prove.ml",
            "- Finished loading candle/benchmark_cv_compute_analytic_expr_case10173_historical_registered_input.ml",
        ),
    },
    {
        "directory": ROOT / "post-direct-source-interface-v678",
        "kind": "development-fast-nl-v678-direct-source-interface-checkpoint-v1",
        "sha256": "980d06be6fb7b418a018fddfd3cdd0bece5bd5f1ba83695264cc532dd742fce1",
        "marker": "CANDLE_FLYSPECK_V678_DIRECT_SOURCE_INTERFACE_CHECKPOINT_READY",
        "driver": PROJECT / "tools/fast_nl_v678_direct_source_interface_stage.ml",
        "required": (
            "- Finished loading candle/cv_compute_flyspeck_direct_source_compat.ml",
            "- Finished loading candle/cv_compute_analytic_expr_case10173_fixture.ml",
        ),
        "forbidden": (
            "- Finished loading text_formalization/general/serialization.hl",
            "- Flyspeck source action complete: nonlinear/break_case_exec.hl",
        ),
    },
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def main() -> int:
    completed = subprocess.run(
        [str(REPAIR_AUDIT)], cwd=PROJECT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120, check=False
    )
    if completed.returncode != 0 or "status=0" not in completed.stdout.splitlines():
        print(completed.stdout, end="")
        return fail("repair_audit")
    historical = subprocess.run(
        [str(HISTORICAL_AUDIT)], cwd=PROJECT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30, check=False
    )
    if historical.returncode != 0 or "status=0" not in historical.stdout.splitlines():
        print(historical.stdout, end="")
        return fail("historical_sound_audit")

    previous_checkpoint: pathlib.Path | None = None
    for index, stage in enumerate(STAGES):
        directory = stage["directory"]
        driver = stage["driver"]
        required_paths = (
            directory / "CHECKPOINT-READY",
            directory / "checkpoint.receipt",
            directory / "checkpoint.sha256",
            directory / "runtime.log",
            driver,
        )
        for path in required_paths:
            if not path.is_file():
                return fail(f"stage_{index}_missing:{path}")
        if (directory / "CHECKPOINT-FAILED").exists():
            return fail(f"stage_{index}_failed")
        observed = receipt(directory / "checkpoint.receipt")
        checkpoint = pathlib.Path(observed.get("checkpoint", ""))
        if not checkpoint.is_file():
            return fail(f"stage_{index}_checkpoint")
        expected_base = (
            pathlib.Path(
                "/project/flyspeck-candle-runs/"
                "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
                "post-matan-v676/checkpoint/"
                "ckpt_cake_d26a4556-40000-1c9aea345e2928.dmtcp"
            )
            if previous_checkpoint is None
            else previous_checkpoint
        )
        expected = {
            "receipt_kind": stage["kind"],
            "release_evidence": "false",
            "driver": str(driver),
            "driver_mode": "direct",
            "driver_sha256": sha256(driver),
            "expected_marker": stage["marker"],
            "checkpoint_sha256": stage["sha256"],
            "checkpoint_size_bytes": str(checkpoint.stat().st_size),
            "base_checkpoint": str(expected_base),
        }
        for key, value in expected.items():
            if observed.get(key) != value:
                return fail(f"stage_{index}_receipt_{key}")
        checksum = (directory / "checkpoint.sha256").read_text(
            encoding="utf-8"
        ).strip()
        if checksum != f"{stage['sha256']}  {checkpoint}":
            return fail(f"stage_{index}_checksum_receipt")
        log = (directory / "runtime.log").read_text(
            encoding="utf-8", errors="replace"
        )
        if (
            log.count(stage["marker"]) != 1
            or log.count("CANDLE_RESTORE_INPUT_ACK nonce=") != 1
            or "ERROR:" in log
            or "EXCEPTION:" in log
            or any(log.count(item) != 1 for item in stage["required"])
            or any(item in log for item in stage["forbidden"])
        ):
            return fail(f"stage_{index}_runtime_log")
        previous_checkpoint = checkpoint

    print("status=0")
    print(f"repair_checkpoint_count={len(STAGES)}")
    print(f"fresh_input_ack_count={len(STAGES)}")
    print("runtime_error_count=0")
    print(f"terminal_checkpoint_sha256={STAGES[-1]['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
