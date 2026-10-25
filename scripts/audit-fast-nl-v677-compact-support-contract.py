#!/usr/bin/env python3
"""Audit the exact compact tree/stack closure before its v677 proof load."""

from __future__ import annotations

import hashlib
import json
import pathlib
import re


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
LEDGER = PROJECT / "docs/long-run-hazard-ledger.json"
SOURCE_ROOT = pathlib.Path("/project/worktrees/candle-direct-fast-nl-runtime-v1")
IDENTITIES = pathlib.Path(
    "/project/flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001/"
    "extra-source-identities.ml"
)
PRIOR = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v502-direct-fixed-nonlinear-proof-support-checkpoint-dev-001"
)
TARGETS = (
    "candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_variable_compact_stack_sound.ml",
    "candle/cv_compute_analytic_expr_taylor_model_tree_compact_correct.ml",
)
EXPECTED_MISSING = (
    "candle/cv_compute_analytic_expr_taylor_model_batch.ml",
    "candle/cv_compute_analytic_expr_taylor_model_tree.ml",
    "candle/cv_compute_analytic_expr_taylor_model_tree_compact_compute.ml",
    "candle/cv_compute_analytic_expr_taylor_model_tree_compact.ml",
    "candle/cv_compute_analytic_expr_taylor_model_tree_compact_correct.ml",
    "candle/cv_compute_analytic_expr_taylor_model_tree_compact_sound.ml",
    "candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_variable_tree_sound.ml",
    "candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_variable_compact_stack_sound.ml",
)
SOURCE_SHA256 = {
    "candle/cv_compute_analytic_expr_taylor_model_batch.ml":
        "4d634b2eac50d343f2ab329cc2cb4f9862fbc68a3e15fd2f65af2989b4d28570",
    "candle/cv_compute_analytic_expr_taylor_model_tree.ml":
        "6116413a9976b8786b9f4bf85012ec0fc32d0d63b4c6adcf5f2aa3f5dc449439",
    "candle/cv_compute_analytic_expr_taylor_model_tree_compact_compute.ml":
        "dc22f25dd98d2a0042c3d1bed1ce30dc77e47437bc3e10d75d7b82e31843d752",
    "candle/cv_compute_analytic_expr_taylor_model_tree_compact.ml":
        "f0d92a024ab52eaeb02f1a760daf080a35fc2f4f9dc32bc4049a398e3bad4a6d",
    "candle/cv_compute_analytic_expr_taylor_model_tree_compact_correct.ml":
        "efb231191051fb5c571911f38f2801bd596b33bba01b21b0cd9900ed2930ae55",
    "candle/cv_compute_analytic_expr_taylor_model_tree_compact_sound.ml":
        "4ec9038694c637fd2bb99debe5c49ae210d5c23703406095d46ed6c30a2a74d4",
    "candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_variable_tree_sound.ml":
        "811e8c9d1a7a4a542d12d2ef9f4863fd432c83eee8b41fd9cb85906a5da967e2",
    "candle/cv_compute_analytic_expr_taylor_model_program_fixed_outer_variable_compact_stack_sound.ml":
        "ab84e3f6cd280ca441836bfca5baf1ab9ad51d7b60da373710ec2272a670ee39",
}


def digest(path: pathlib.Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    hasher.update(path.read_bytes())
    return hasher.hexdigest()


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def main() -> int:
    required = (LEDGER, IDENTITIES, PRIOR / "base.log", PRIOR / "fragments.sha256")
    if any(not path.is_file() for path in required):
        return fail("missing_authority")
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    receipts = ledger["scopes"]["fast-nl-first-original-theorem"]["checkpoint_receipts"]
    logs: list[str] = []
    found_base = False
    for receipt_text in receipts:
        receipt = pathlib.Path(receipt_text)
        log = receipt.parent / "runtime.log"
        if log.is_file():
            logs.append(log.read_text(encoding="utf-8", errors="replace"))
        if receipt.parent.name == "post-historical-sound-v677w":
            found_base = True
            break
    if not found_base:
        return fail("missing_v677w_lineage")
    loaded = set(re.findall(r"- Finished loading (candle/[^\s]+\.ml)", "\n".join(logs)))

    seen: set[str] = set()
    order: list[str] = []

    def walk(logical: str) -> None:
        if logical in seen:
            return
        seen.add(logical)
        source = SOURCE_ROOT / logical
        if not source.is_file():
            return
        text = source.read_text(encoding="utf-8")
        for dependency in re.findall(r'(?m)^needs "([^"]+)";;$', text):
            if dependency.startswith("candle/"):
                walk(dependency)
        order.append(logical)

    for target in TARGETS:
        walk(target)
    missing = tuple(logical for logical in order if logical not in loaded)
    if missing != EXPECTED_MISSING:
        return fail("remaining_closure_partition")

    identities = IDENTITIES.read_text(encoding="utf-8")
    combined = []
    for logical in EXPECTED_MISSING:
        source = SOURCE_ROOT / logical
        if source.is_symlink() or digest(source, "sha256") != SOURCE_SHA256[logical]:
            return fail(f"source_identity:{logical}")
        md5 = digest(source, "md5")
        identity = f'("{source}",("{source.name}","{md5}"));'
        if identities.count(identity) != 1:
            return fail(f"logical_identity:{logical}")
        combined.append(source.read_text(encoding="utf-8"))

    # LR-043 class: a bare variable-only arithmetic quotation can select a
    # cval overload in this ambient state.  All such specializations in the
    # eight-file boundary must carry an explicit type.
    bare_arithmetic = re.compile(
        r"`[A-Za-z][A-Za-z0-9_']*\s*[+*/]\s*[A-Za-z][A-Za-z0-9_']*`"
    )
    if any(bare_arithmetic.search(text) for text in combined):
        return fail("bare_arithmetic_specialization")

    prior_hashes = dict(
        line.split("  ", 1)[::-1]
        for line in (PRIOR / "fragments.sha256").read_text(encoding="utf-8").splitlines()
        if "  " in line
    )
    for logical in EXPECTED_MISSING:
        if logical.endswith("tree_compact_compute.ml"):
            continue
        if prior_hashes.get(logical) != SOURCE_SHA256[logical]:
            return fail(f"prior_fragment_identity:{logical}")
    prior_log = (PRIOR / "base.log").read_text(encoding="utf-8", errors="replace")
    markers = (
        "CANDLE_CV_COMPACT_TREE_SOUND_OK DEVELOPMENT_NON_RELEASE",
        "CANDLE_CV_FIXED_OUTER_VARIABLE_TREE_SOUND_OK DEVELOPMENT_NON_RELEASE",
        "CANDLE_CV_FIXED_OUTER_VARIABLE_COMPACT_STACK_SOUND_OK DEVELOPMENT_NON_RELEASE",
    )
    if any(prior_log.count(marker) != 1 for marker in markers):
        return fail("prior_proof_marker")

    print("status=0")
    print(f"compact_closure_count={len(order)}")
    print(f"compact_predecessor_loaded_count={len(order) - len(missing)}")
    print(f"compact_remaining_source_count={len(missing)}")
    print("bare_arithmetic_specialization_count=0")
    print("prior_exact_proof_marker_count=3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
