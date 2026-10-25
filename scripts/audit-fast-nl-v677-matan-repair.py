#!/usr/bin/env python3
"""Authenticate the exact 19-file fast-NL matan compatibility overlay."""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
MANIFEST = PROJECT / "docs/fast-nl-v677-matan-repair-manifest.json"
OVERLAY = PROJECT / "tools/fast_nl_v677_matan_repair_overlay.ml"
IDENTITIES = pathlib.Path(
    "/project/flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001/"
    "extra-source-identities.ml"
)
CONSTRUCTOR_AUDIT = PROJECT / "scripts/audit-fast-nl-matan-constructor-closure.py"


def digest(path: pathlib.Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def git(path: pathlib.Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), *arguments], text=True
    ).strip()


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def main() -> int:
    for path in (MANIFEST, OVERLAY, IDENTITIES, CONSTRUCTOR_AUDIT):
        if not path.is_file():
            return fail(f"missing:{path}")
    try:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return fail(f"manifest_parse:{error}")
    if payload.get("schema_version") != 1:
        return fail("manifest_schema")
    original = payload.get("original", {})
    candidate = payload.get("candidate", {})
    files = payload.get("files")
    if not isinstance(files, list) or len(files) != 19:
        return fail("manifest_file_count")
    roots = []
    try:
        for role, item in (("original", original), ("candidate", candidate)):
            root = pathlib.Path(item["root"]).resolve()
            expected_head = item["commit"]
            if git(root, "rev-parse", "HEAD") != expected_head:
                return fail(f"{role}_head")
            if git(root, "status", "--porcelain"):
                return fail(f"{role}_dirty")
            roots.append(root)
    except (KeyError, OSError, subprocess.CalledProcessError) as error:
        return fail(f"repository:{error}")
    original_root, candidate_root = roots

    paths = [entry.get("path") for entry in files if isinstance(entry, dict)]
    if len(paths) != 19 or len(set(paths)) != 19 or paths != sorted(paths):
        return fail("manifest_paths")
    changed = git(
        candidate_root,
        "diff",
        "--name-only",
        original["commit"],
        candidate["commit"],
    ).splitlines()
    if changed != paths:
        return fail("candidate_changed_file_set")

    identity_text = IDENTITIES.read_text(encoding="utf-8")
    for entry in files:
        logical = entry["path"]
        old_path = original_root / logical
        new_path = candidate_root / logical
        for path in (old_path, new_path):
            if not path.is_file() or path.is_symlink():
                return fail(f"source_node:{path}")
        expected = {
            "original_md5": digest(old_path, "md5"),
            "original_sha256": digest(old_path, "sha256"),
            "candidate_md5": digest(new_path, "md5"),
            "candidate_sha256": digest(new_path, "sha256"),
        }
        for key, actual in expected.items():
            if entry.get(key) != actual:
                return fail(f"{key}:{logical}")
        identity = (
            f'("{old_path}",("{old_path.name}",'
            f'"{entry["original_md5"]}"));'
        )
        if identity_text.count(identity) != 1:
            return fail(f"source_identity:{logical}")

    # LR-032: in a HOL quotation, an unparenthesized ``let ... in`` RHS can
    # absorb the following implication and make a certificate tuple serve as
    # a Boolean.  Require the repaired helper's premise to close explicitly.
    patch_text = (candidate_root / paths[0]).read_text(encoding="utf-8")
    delimited_premise = re.compile(
        r"!a intervals\.\s*"
        r"\(candle_analytic_program_patch_sqrt intervals\s*"
        r"\(candle_analytic_compile a\)\s*=\s*"
        r"let patched =\s*"
        r"candle_analytic_patch_sqrt_certificates intervals a in\s*"
        r"\(FST patched,candle_analytic_compile \(SND patched\)\)\)\s*"
        r"==>",
        re.S,
    )
    if len(delimited_premise.findall(patch_text)) != 1:
        return fail("matan_step_premise_delimitation")
    compute_patch_text = (candidate_root / paths[1]).read_text(encoding="utf-8")
    if "PRINT_GOAL_TAC" in compute_patch_text:
        return fail("matan_representation_debug_tactic")
    representation_branch = re.compile(
        r"REWRITE_TAC\s*\[candle_cv_analytic_program_matan_patch_sqrt;\s*"
        r"candle_analytic_instruction_patch_sqrt_def; FST; SND\]",
        re.S,
    )
    if len(representation_branch.findall(compute_patch_text)) != 1:
        return fail("matan_representation_logical_normalization")
    first_jet_text = (candidate_root / paths[4]).read_text(encoding="utf-8")
    matan_series_bindings = (
        "candle_cv_q_interval_matan_series_correct",
        "candle_cv_q_interval_dmatan_series_correct",
        "candle_cv_q_interval_matan_series_domain_correct",
    )
    if (
        any(binding not in first_jet_text for binding in matan_series_bindings)
        or first_jet_text.count(
            "open Candle_cv_exact_interval_matan_series_program;;"
        )
        != 1
    ):
        return fail("first_jet_matan_series_module_binding")
    candidate_texts = {
        logical: (candidate_root / logical).read_text(encoding="utf-8")
        for logical in paths
    }
    compile_sound_text = candidate_texts[paths[5]]
    premise_free_discharge = re.compile(
        r"REWRITE_TAC\s*"
        r"\[candle_q_dim_taylor_model_result_default_analytic_invariant\]",
        re.S,
    )
    if (
        len(premise_free_discharge.findall(compile_sound_text)) != 1
    ):
        return fail("matan_default_invariant_discharge")
    # LR-035/LR-037: all three default-invariant theorems are universally
    # quantified propositions without implication premises.  MATCH_MP_TAC
    # therefore raises Bad theorem.  Scan the complete authenticated repair
    # closure so copied downstream instances cannot be found one stage at a
    # time during expensive proof loads.
    premise_free_invariants = (
        "candle_q_dim_taylor_model_result_default_analytic_invariant",
        "candle_fsa_item_matan_default_analytic_invariant",
        "candle_fsa_logical_item_matan_default_analytic_invariant",
    )
    all_candidate_text = "\n".join(candidate_texts.values())
    for theorem in premise_free_invariants:
        if re.search(rf"MATCH_MP_TAC\s*{theorem}\b", all_candidate_text):
            return fail(f"premise_free_match_mp:{theorem}")
    direct_accepts = re.findall(
        r"MATCH_ACCEPT_TAC\s*"
        r"(?:candle_q_dim_taylor_model_result_default_analytic_invariant|"
        r"candle_fsa_item_matan_default_analytic_invariant|"
        r"candle_fsa_logical_item_matan_default_analytic_invariant)\b",
        all_candidate_text,
    )
    normalized_item_accepts = re.findall(
        r"MATCH_ACCEPT_TAC\s*\(REWRITE_RULE\s*"
        r"\[LET_DEF;\s*LET_END_DEF\]\s*"
        r"candle_fsa_item_matan_default_analytic_invariant\)",
        all_candidate_text,
    )
    if len(direct_accepts) != 4 or len(normalized_item_accepts) != 1:
        return fail("premise_free_direct_accept_count")
    # LR-038: classify every MATCH_MP_TAC introduced by the repair, not only
    # the theorem family that has failed already.  The twelve remaining sites
    # are four constructor branches, each with an equivalence implication, an
    # induction hypothesis, and an append-single theorem with real premises.
    repair_diff = subprocess.check_output(
        [
            "git", "-C", str(candidate_root), "diff", "--unified=0",
            original["commit"], candidate["commit"], "--", *paths,
        ],
        text=True,
    )
    added_text = "\n".join(
        line[1:]
        for line in repair_diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    introduced_match_mp = len(re.findall(r"\bMATCH_MP_TAC\b", added_text))
    introduced_match_mp_shapes = {
        "erase_equivalence": len(re.findall(
            r"MATCH_MP_TAC\s+\(fst\s+\(EQ_IMP_RULE", added_text
        )),
        "induction_hypothesis": len(re.findall(
            r'USE_THEN\s+"ih"\s+MATCH_MP_TAC', added_text
        )),
        "append_single": len(re.findall(
            r"MATCH_MP_TAC\s+(?:"
            r"candle_q_dim_taylor_model_program_run_append_single|"
            r"candle_fsa_logical_program_run_with_future_append_single|"
            r"candle_fsn_logical_program_run_append_single|"
            r"candle_fso_logical_program_run_append_single)",
            added_text,
        )),
    }
    if introduced_match_mp != 12 or any(
        count != 4 for count in introduced_match_mp_shapes.values()
    ):
        return fail("introduced_match_mp_shape_partition")
    # LR-039: the new tag-9 cases leave ifc (numc 0) terms only after
    # NUM_REDUCE_CONV.  The final representation cleanup must therefore
    # include cexp_if_def, rather than relying on the earlier rewrite pass.
    algebraic_program_sound = candidate_texts[
        "candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_program_sound.ml"
    ]
    step_cleanup = re.compile(
        r"let candle_cv_fsa_logical_program_step_correct = prove.*?"
        r"LET_DEF; LET_END_DEF; cexp_if_def\]\);;",
        re.S,
    )
    if len(step_cleanup.findall(algebraic_program_sound)) != 1:
        return fail("algebraic_program_step_if_cleanup")

    overlay = OVERLAY.read_text(encoding="utf-8")
    overlay_pairs = re.findall(
        r'\("(/project/worktrees/candle-direct-fast-nl-runtime-v1/(candle/[^\"]+\.ml))",\s*'
        r'"(/project/worktrees/candle-fast-nl-matan-closure-v1/candle/[^\"]+\.ml)"\)',
        overlay,
    )
    overlay_paths = [logical for _, logical, _ in overlay_pairs]
    if overlay_paths != paths:
        return fail("overlay_path_set")
    for old_text, logical, new_text in overlay_pairs:
        if pathlib.Path(old_text) != original_root / logical:
            return fail(f"overlay_original:{logical}")
        if pathlib.Path(new_text) != candidate_root / logical:
            return fail(f"overlay_candidate:{logical}")
    required_overlay_fragments = (
        'List.length candle_flyspeck_v677_existing_mappings <> 95',
        'List.length candle_flyspeck_v677_matan_repair_mappings <> 19',
        'existing = original',
        'Some\n    (candle_flyspeck_v677_matan_repair_mappings @',
        'mappings) <> 114',
        'CANDLE_FLYSPECK_V677_MATAN_REPAIR_OVERLAY_READY mappings=19 total=114',
    )
    for fragment in required_overlay_fragments:
        if fragment not in overlay:
            return fail(f"overlay_contract:{fragment}")

    completed = subprocess.run(
        [str(CONSTRUCTOR_AUDIT), "--candidate-candle-root", str(candidate_root)],
        cwd=PROJECT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
        check=False,
    )
    if completed.returncode != 0 or "status=0" not in completed.stdout.splitlines():
        print(completed.stdout, end="")
        return fail("candidate_constructor_closure")

    print("status=0")
    print(f"repair_source_count={len(files)}")
    print(f"original_head={original['commit']}")
    print(f"candidate_head={candidate['commit']}")
    print("matan_step_premise_delimitation_count=1")
    print("matan_representation_logical_normalization_count=1")
    print("first_jet_matan_series_module_binding_count=1")
    print("matan_default_invariant_discharge_count=1")
    print("premise_free_match_mp_count=0")
    print(
        "premise_free_direct_accept_count="
        f"{len(direct_accepts) + len(normalized_item_accepts)}"
    )
    print(f"normalized_item_accept_count={len(normalized_item_accepts)}")
    print(f"introduced_match_mp_count={introduced_match_mp}")
    print("introduced_match_mp_shape_counts=4,4,4")
    print("algebraic_program_step_if_cleanup_count=1")
    print(f"manifest_sha256={digest(MANIFEST, 'sha256')}")
    print(f"overlay_sha256={digest(OVERLAY, 'sha256')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
