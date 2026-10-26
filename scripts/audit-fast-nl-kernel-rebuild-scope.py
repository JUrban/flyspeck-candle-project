#!/usr/bin/env python3
"""Fail closed on a case-specific rebuild of the Candle/compiler ancestry."""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
import pathlib
import subprocess


WORKTREE = pathlib.Path(
    "/project/worktrees/cakeml-direct-fast-nl-integration-v1"
)
ROOT = "candle/prover/candle_kernelProgTheory"
HEAD = "839017e696dea5fbbb2e03bfeff02c6679724e00"
EXPECTED_DESCENDANTS = (
    "candle/prover/candle_basis_evaluateTheory",
    "candle/prover/candle_kernel_funsTheory",
    "candle/prover/candle_kernel_permsTheory",
    "candle/prover/candle_kernel_valsTheory",
    "candle/prover/candle_prover_evaluateTheory",
    "candle/prover/candle_prover_invTheory",
    "candle/prover/candle_prover_semanticsTheory",
    "compiler/bootstrap/compilation/x64/64/proofs/replProofTheory",
    "compiler/bootstrap/compilation/x64/64/proofs/x64BootstrapProofTheory",
    "compiler/bootstrap/compilation/x64/64/x64BootstrapTheory",
    "compiler/bootstrap/translation/arm8ProgTheory",
    "compiler/bootstrap/translation/basis_defProgTheory",
    "compiler/bootstrap/translation/caml_lexProgTheory",
    "compiler/bootstrap/translation/caml_parserProgTheory",
    "compiler/bootstrap/translation/compiler64ProgTheory",
    "compiler/bootstrap/translation/decProgTheory",
    "compiler/bootstrap/translation/decodeProgTheory",
    "compiler/bootstrap/translation/explorerProgTheory",
    "compiler/bootstrap/translation/from_pancake64ProgTheory",
    "compiler/bootstrap/translation/inferProgTheory",
    "compiler/bootstrap/translation/lexerProgTheory",
    "compiler/bootstrap/translation/mipsProgTheory",
    "compiler/bootstrap/translation/pancake_lexProgTheory",
    "compiler/bootstrap/translation/pancake_parseProgTheory",
    "compiler/bootstrap/translation/parserProgTheory",
    "compiler/bootstrap/translation/printingProgTheory",
    "compiler/bootstrap/translation/reg_allocProgTheory",
    "compiler/bootstrap/translation/riscvProgTheory",
    "compiler/bootstrap/translation/sexp_parserProgTheory",
    "compiler/bootstrap/translation/to_bviProgTheory",
    "compiler/bootstrap/translation/to_bvlProgTheory",
    "compiler/bootstrap/translation/to_closProgTheory",
    "compiler/bootstrap/translation/to_dataProgTheory",
    "compiler/bootstrap/translation/to_flatProgTheory",
    "compiler/bootstrap/translation/to_target64ProgTheory",
    "compiler/bootstrap/translation/to_word64ProgTheory",
    "compiler/bootstrap/translation/x64ProgTheory",
    "compiler/repl/repl_check_and_tweakTheory",
    "compiler/repl/repl_decs_allowedTheory",
    "compiler/repl/repl_initTheory",
    "compiler/repl/repl_init_envProgTheory",
    "compiler/repl/repl_init_typesTheory",
    "compiler/repl/repl_moduleProgTheory",
    "compiler/repl/repl_typesTheory",
)


def fail(message: str, descendants: set[str] | None = None) -> int:
    print("status=1")
    print(f"error={message}")
    if descendants is not None:
        print(f"downstream_theory_count={len(descendants)}")
        print(f"affected_theory_count={len(descendants) + 1}")
    return 1


def logical_objects() -> dict[str, pathlib.Path]:
    objects: dict[str, pathlib.Path] = {}
    for path in WORKTREE.rglob(".hol/objs/*Theory.uo"):
        if "tag10_probe_scratch" in path.parts:
            continue
        relative = path.relative_to(WORKTREE)
        parts = list(relative.parts)
        object_index = parts.index(".hol")
        logical = "/".join(parts[:object_index] + [path.stem])
        if logical in objects:
            raise RuntimeError(f"duplicate logical object: {logical}")
        objects[logical] = path
    return objects


def reverse_descendants(objects: dict[str, pathlib.Path]) -> set[str]:
    reverse: dict[str, set[str]] = defaultdict(set)
    prefix = "$(CAKEMLDIR)/"
    for logical, path in objects.items():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith(prefix):
                continue
            dependency = line[len(prefix) :]
            if dependency in objects and dependency != logical:
                reverse[dependency].add(logical)
    result: set[str] = set()
    queue: deque[str] = deque([ROOT])
    while queue:
        current = queue.popleft()
        for successor in sorted(reverse[current]):
            if successor not in result:
                result.add(successor)
                queue.append(successor)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission-controller", type=pathlib.Path)
    args = parser.parse_args()

    if subprocess.check_output(
        ["git", "-C", str(WORKTREE), "rev-parse", "HEAD"], text=True
    ).strip() != HEAD:
        return fail("integration_head")
    if subprocess.check_output(
        [
            "git", "-C", str(WORKTREE), "status", "--porcelain",
            "--untracked-files=no",
        ],
        text=True,
    ).strip():
        return fail("tracked_worktree_dirty")

    try:
        objects = logical_objects()
        descendants = reverse_descendants(objects)
    except (OSError, RuntimeError) as error:
        return fail(f"manifest_graph:{error}")
    if tuple(sorted(descendants)) != EXPECTED_DESCENDANTS:
        return fail("reverse_dependency_cone_changed", descendants)

    kernel = (WORKTREE / "candle/prover/candle_kernelProgScript.sml").read_text(
        encoding="utf-8"
    )
    compiler = (
        WORKTREE / "compiler/bootstrap/translation/compiler64ProgScript.sml"
    ).read_text(encoding="utf-8")
    embedded = "registered_case10173_genuine_packed_certificate_payload" in kernel
    compiler_patch = (
        "registered_case10173_genuine_packed_certificate_v_thm" in compiler
    )
    if not embedded or not compiler_patch:
        return fail("expected_case_specific_embedding_changed", descendants)

    print(f"candidate_head={HEAD}")
    print(f"manifest_object_count={len(objects)}")
    print(f"downstream_theory_count={len(descendants)}")
    print(f"affected_theory_count={len(descendants) + 1}")
    print("certificate_interface=case_specific_embedded_literal")
    print("compiler64_literal_patch=true")
    print("estimated_rebuild_scope=kernel_repl_compiler_bootstrap")

    if args.admission_controller is not None:
        controller = args.admission_controller.resolve()
        if not controller.is_file() or controller.is_symlink():
            return fail("admission_controller_identity", descendants)
        # This snapshot is evidence for the architecture review, not authority
        # to spend a day rebuilding a one-case runtime.  A future reusable
        # interface needs a new audit tied to its new source identity.
        return fail("case_specific_runtime_rebuild_forbidden", descendants)

    print("status=0")
    print("case_specific_runtime_rebuild_admitted=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
