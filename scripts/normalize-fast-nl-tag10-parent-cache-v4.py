#!/usr/bin/env python3
"""Relocate the complete authenticated tag-10 generated cache in place.

Only absolute scratch-directory observations in textual Poly/Holmake .ui/.uo
manifests are changed.  Proof data and generated ML sources must already be
byte-identical in the scratch and parent caches; this program refuses to copy
or rebuild them.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
from datetime import datetime, timezone


WORKTREE = pathlib.Path(
    "/project/worktrees/cakeml-direct-fast-nl-integration-v1"
)
COMPUTE = WORKTREE / "candle/prover/compute"
SCRATCH = COMPUTE / "tag10_probe_scratch"
OBJECTS = COMPUTE / ".hol/objs"
SCRATCH_OBJECTS = SCRATCH / ".hol/objs"
EXPECTED_HEAD = "839017e696dea5fbbb2e03bfeff02c6679724e00"
OLD_COMPONENT = b"/tag10_probe_scratch/"
NEW_COMPONENT = b"/"
EXPECTED_THEORY_COUNT = 34
EXPECTED_MANIFEST_COUNT = 68
RECOVERY = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v686-fast-nl-tag10-cache-recovery-dev-001/CACHE-RECOVERY.receipt"
)


class RelocationFailure(Exception):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree_digest(items: list[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for name, data in sorted(items):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest()


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(WORKTREE), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise RelocationFailure(f"git_failed:{' '.join(args)}")
    return completed.stdout.strip()


def require_file(path: pathlib.Path) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise RelocationFailure(f"not_regular_file:{path}")
    return path.read_bytes()


def candidate_manifests() -> list[pathlib.Path]:
    candidates: list[pathlib.Path] = []
    for suffix in ("*.ui", "*.uo"):
        for path in OBJECTS.glob(suffix):
            if OLD_COMPONENT in require_file(path):
                candidates.append(path)
    return sorted(candidates)


def theory_name(path: pathlib.Path) -> str:
    marker = "Theory."
    if marker not in path.name:
        raise RelocationFailure(f"unexpected_manifest_name:{path.name}")
    return path.name.split(marker, 1)[0]


def verify_inputs() -> tuple[list[pathlib.Path], list[str], str]:
    if git("rev-parse", "HEAD") != EXPECTED_HEAD:
        raise RelocationFailure("integration_head_mismatch")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise RelocationFailure("integration_tracked_worktree_dirty")

    recovery_lines = set(require_file(RECOVERY).decode("utf-8").splitlines())
    for marker in (
        "status=0",
        "restored_theory_count=3",
        "restored_artifact_count=12",
        "retained_manifests_changed=false",
    ):
        if marker not in recovery_lines:
            raise RelocationFailure(f"recovery_receipt_missing:{marker}")

    manifests = candidate_manifests()
    theories = sorted({theory_name(path) for path in manifests})
    if len(manifests) != EXPECTED_MANIFEST_COUNT:
        raise RelocationFailure(f"manifest_count:{len(manifests)}")
    if len(theories) != EXPECTED_THEORY_COUNT:
        raise RelocationFailure(f"theory_count:{len(theories)}")
    if any(
        not (
            name == "compute_evalRestrictedCongruence"
            or name.startswith("compute_registeredCase10173Tag10")
        )
        for name in theories
    ):
        raise RelocationFailure("unexpected_theory_scope")

    proof_items: list[tuple[str, bytes]] = []
    for name in theories:
        parent_script = require_file(COMPUTE / f"{name}Script.sml")
        scratch_script = require_file(SCRATCH / f"{name}Script.sml")
        if parent_script != scratch_script:
            raise RelocationFailure(f"script_bytes_differ:{name}")
        proof_items.append((f"{name}Script.sml", parent_script))

        for suffix in ("sml", "sig", "dat", "cachekey"):
            filename = f"{name}Theory.{suffix}"
            parent = require_file(OBJECTS / filename)
            scratch = require_file(SCRATCH_OBJECTS / filename)
            if parent != scratch:
                raise RelocationFailure(f"generated_bytes_differ:{filename}")
            proof_items.append((filename, parent))

        for suffix in ("ui", "uo"):
            filename = f"{name}Theory.{suffix}"
            parent = require_file(OBJECTS / filename)
            scratch = require_file(SCRATCH_OBJECTS / filename)
            if parent.replace(OLD_COMPONENT, NEW_COMPONENT) != scratch.replace(
                OLD_COMPONENT, NEW_COMPONENT
            ):
                raise RelocationFailure(f"normalized_manifest_differs:{filename}")

    return manifests, theories, tree_digest(proof_items)


def apply_relocation(run_dir: pathlib.Path) -> None:
    manifests, theories, proof_digest_before = verify_inputs()
    if run_dir.exists():
        raise RelocationFailure(f"run_directory_exists:{run_dir}")
    backup = run_dir / "manifest-backup"
    backup.mkdir(parents=True)

    before_items: list[tuple[str, bytes]] = []
    after_items: list[tuple[str, bytes]] = []
    replacement_count = 0
    for path in manifests:
        original = require_file(path)
        relocated = original.replace(OLD_COMPONENT, NEW_COMPONENT)
        count = original.count(OLD_COMPONENT)
        if count == 0 or OLD_COMPONENT in relocated or original == relocated:
            raise RelocationFailure(f"manifest_not_relocated:{path.name}")
        shutil.copy2(path, backup / path.name)
        temporary = path.with_name(path.name + ".relocate-v4.tmp")
        try:
            temporary.write_bytes(relocated)
            os.chmod(temporary, path.stat().st_mode & 0o777)
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()
        before_items.append((path.name, original))
        after_items.append((path.name, relocated))
        replacement_count += count

    remaining = candidate_manifests()
    if remaining:
        raise RelocationFailure(f"scratch_references_remain:{len(remaining)}")

    # Re-run the full byte-identity checks without requiring candidates.
    proof_items_after: list[tuple[str, bytes]] = []
    for name in theories:
        proof_items_after.append(
            (f"{name}Script.sml", require_file(COMPUTE / f"{name}Script.sml"))
        )
        for suffix in ("sml", "sig", "dat", "cachekey"):
            filename = f"{name}Theory.{suffix}"
            parent = require_file(OBJECTS / filename)
            scratch = require_file(SCRATCH_OBJECTS / filename)
            if parent != scratch:
                raise RelocationFailure(f"proof_data_changed:{filename}")
            proof_items_after.append((filename, parent))
    proof_digest_after = tree_digest(proof_items_after)
    if proof_digest_after != proof_digest_before:
        raise RelocationFailure("proof_data_digest_changed")

    receipt = run_dir / "PARENT-CACHE-RELOCATION.receipt"
    receipt.write_text(
        "\n".join(
            (
                "receipt_kind=development-fast-nl-tag10-parent-cache-relocation-v2",
                "release_evidence=false",
                "status=0",
                f"candidate_head={EXPECTED_HEAD}",
                f"relocated_theory_count={len(theories)}",
                f"relocated_manifest_count={len(manifests)}",
                f"path_replacement_count={replacement_count}",
                "remaining_scratch_manifest_count=0",
                "proof_data_changed=false",
                f"proof_data_tree_sha256={proof_digest_after}",
                f"manifest_before_tree_sha256={tree_digest(before_items)}",
                f"manifest_after_tree_sha256={tree_digest(after_items)}",
                "rewritten_field=absolute_scratch_path_component_only",
                "completed_utc="
                + datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "",
            )
        ),
        encoding="utf-8",
    )
    print(receipt.read_text(encoding="utf-8"), end="")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", type=pathlib.Path)
    args = parser.parse_args()
    try:
        if args.apply is not None:
            apply_relocation(args.apply)
        else:
            manifests, theories, proof_digest = verify_inputs()
            print("status=0")
            print(f"relocation_candidate_theory_count={len(theories)}")
            print(f"relocation_candidate_manifest_count={len(manifests)}")
            print(f"proof_data_tree_sha256={proof_digest}")
            print("proof_data_matches_scratch=true")
    except (OSError, RelocationFailure, subprocess.SubprocessError) as error:
        print("status=1")
        print(f"error={error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
