#!/usr/bin/env python3
"""Read-only audit of every object reachable by candle_kernelProgScript."""

from __future__ import annotations

import collections
import hashlib
import pathlib
import re
import subprocess


CAKEML = pathlib.Path(
    "/project/worktrees/cakeml-direct-fast-nl-integration-v1"
)
HOLDIR = pathlib.Path("/project/worktrees/HOL-cakeml-dopen-v13")
PROVER = CAKEML / "candle/prover"
SOURCE = PROVER / "candle_kernelProgScript.sml"
DEPFILE = PROVER / ".hol/make-deps/candle_kernelProgScript.sml.d"
HOLDEP = HOLDIR / "bin/holdeptool.exe"
RECOVERY = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v686-fast-nl-tag10-cache-recovery-dev-001/CACHE-RECOVERY.receipt"
)
PARENT_COMPUTE = CAKEML / "candle/prover/compute"
SCRATCH_COMPUTE = PARENT_COMPUTE / "tag10_probe_scratch"
EXPECTED_HEAD = "839017e696dea5fbbb2e03bfeff02c6679724e00"
# These names are provided by the fixed HOL state used by Holmake and are
# deliberately absent from the generated dependency file.
PRELOADED_MODULES = {"CompilerSpecific", "locationTheory"}


class AuditFailure(Exception):
    pass


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def actual_file(logical: pathlib.Path) -> pathlib.Path | None:
    if logical.is_file():
        return logical
    object_path = logical.parent / ".hol/objs" / logical.name
    if object_path.is_file():
        return object_path
    if HOLDIR in logical.parents:
        installed = HOLDIR / "sigobj" / logical.name
        if installed.is_file():
            return installed
    return None


def actual_object(logical_base: pathlib.Path, suffix: str) -> pathlib.Path | None:
    return actual_file(logical_base.with_suffix(suffix))


def expand(line: str) -> pathlib.Path:
    expanded = line.replace("$(CAKEMLDIR)", str(CAKEML)).replace(
        "$(HOLDIR)", str(HOLDIR)
    )
    match = re.search(r"\$\([^)]+\)", expanded)
    if match:
        raise AuditFailure(f"unknown_path_variable:{match.group(0)}")
    path = pathlib.Path(expanded)
    if not path.is_absolute():
        raise AuditFailure(f"nonabsolute_manifest_path:{line}")
    if SCRATCH_COMPUTE in path.parents:
        raise AuditFailure(f"scratch_manifest_reference:{line}")
    return path


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(CAKEML), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise AuditFailure(f"git_failed:{' '.join(args)}")
    return completed.stdout.strip()


def direct_modules() -> list[str]:
    completed = subprocess.run(
        [str(HOLDEP), SOURCE.name],
        cwd=PROVER,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise AuditFailure("holdep_failed")
    modules = [
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip() and line.strip() not in PRELOADED_MODULES
    ]
    if len(modules) != len(set(modules)) or len(modules) < 100:
        raise AuditFailure(f"direct_module_inventory:{len(modules)}")
    return modules


def dependency_hints() -> dict[str, list[pathlib.Path]]:
    text = DEPFILE.read_text(encoding="utf-8")
    tokens = text.replace("\\\n", " ").split()
    hints: dict[str, list[pathlib.Path]] = collections.defaultdict(list)
    for token in tokens:
        if not token.endswith(".uo") or not token.startswith("/"):
            continue
        path = pathlib.Path(token)
        hints[path.stem].append(path.with_suffix(""))
    return hints


def choose_direct(module: str, hints: dict[str, list[pathlib.Path]]) -> pathlib.Path:
    candidates = list(hints.get(module, ()))
    if not candidates:
        raise AuditFailure(f"direct_module_without_hint:{module}")

    # The dependency file was generated while one source commit was still
    # being added.  If the same logical theory now has a parent object, the
    # current Holmake scan selects that parent before the scratch directory.
    normalized: list[pathlib.Path] = []
    for logical in candidates:
        if SCRATCH_COMPUTE in logical.parents:
            parent = PARENT_COMPUTE / logical.name
            if actual_object(parent, ".uo") and actual_object(parent, ".ui"):
                logical = parent
        if logical not in normalized:
            normalized.append(logical)

    existing = [
        logical
        for logical in normalized
        if actual_object(logical, ".uo") and actual_object(logical, ".ui")
    ]
    if not existing:
        raise AuditFailure(f"direct_module_object_missing:{module}")
    parent_existing = [
        item for item in existing
        if PARENT_COMPUTE == item.parent
    ]
    return parent_existing[0] if parent_existing else existing[0]


def audit_manifest(
    manifest: pathlib.Path,
    queue: collections.deque[pathlib.Path],
    generated: set[pathlib.Path],
) -> tuple[int, int]:
    try:
        text = manifest.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise AuditFailure(f"manifest_not_text:{manifest}:{error}") from error
    dependency_count = 0
    generated_count = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        logical = expand(line)
        if logical.suffix in (".sml", ".sig"):
            artifact = actual_file(logical)
            if artifact is None:
                raise AuditFailure(f"generated_source_missing:{logical}")
            if (
                logical.name.endswith("Theory.sml")
                and logical.stem != "Theory"
            ):
                base = logical.with_suffix("")
                for suffix in (".sig", ".dat"):
                    required = actual_object(base, suffix)
                    if required is None:
                        raise AuditFailure(
                            f"generated_theory_artifact_missing:{base}{suffix}"
                        )
                    generated.add(required)
                generated.add(artifact)
                generated_count += 1
            continue

        dependency = actual_object(logical, ".uo")
        interface = actual_object(logical, ".ui")
        if dependency is None:
            raise AuditFailure(f"transitive_object_missing:{logical}.uo")
        if interface is None:
            raise AuditFailure(f"transitive_interface_missing:{logical}.ui")
        queue.append(dependency)
        dependency_count += 1
    return dependency_count, generated_count


def main() -> int:
    try:
        if git("rev-parse", "HEAD") != EXPECTED_HEAD:
            raise AuditFailure("integration_head_mismatch")
        if git("status", "--porcelain", "--untracked-files=no"):
            raise AuditFailure("integration_tracked_worktree_dirty")
        recovery = RECOVERY.read_text(encoding="utf-8")
        for marker in (
            "status=0",
            "restored_theory_count=3",
            "restored_artifact_count=12",
            "retained_manifests_changed=false",
        ):
            if marker not in recovery.splitlines():
                raise AuditFailure(f"recovery_receipt:{marker}")

        modules = direct_modules()
        hints = dependency_hints()
        roots = [choose_direct(module, hints) for module in modules]

        queue: collections.deque[pathlib.Path] = collections.deque()
        for logical in roots:
            object_path = actual_object(logical, ".uo")
            assert object_path is not None
            queue.append(object_path)

        manifests: set[pathlib.Path] = set()
        generated: set[pathlib.Path] = set()
        edge_count = 0
        generated_reference_count = 0
        while queue:
            manifest = queue.popleft().resolve()
            if manifest in manifests:
                continue
            manifests.add(manifest)
            edges, generated_refs = audit_manifest(manifest, queue, generated)
            edge_count += edges
            generated_reference_count += generated_refs

        if len(manifests) < len(modules) or len(generated) < 100:
            raise AuditFailure(
                f"closure_too_small:{len(manifests)}:{len(generated)}"
            )
        manifest_digest = hashlib.sha256()
        for path in sorted(manifests):
            manifest_digest.update(str(path).encode("utf-8"))
            manifest_digest.update(b"\0")
            manifest_digest.update(hashlib.sha256(path.read_bytes()).digest())
    except (AuditFailure, OSError, subprocess.SubprocessError) as error:
        return fail(str(error))

    print("status=0")
    print(f"candidate_head={EXPECTED_HEAD}")
    print(f"direct_module_count={len(modules)}")
    print(f"preloaded_module_count={len(PRELOADED_MODULES)}")
    print(f"resolved_direct_object_count={len(roots)}")
    print(f"transitive_manifest_count={len(manifests)}")
    print(f"transitive_edge_count={edge_count}")
    print(f"generated_artifact_count={len(generated)}")
    print(f"generated_reference_count={generated_reference_count}")
    print("missing_object_count=0")
    print("missing_interface_count=0")
    print("missing_generated_theory_artifact_count=0")
    print("scratch_manifest_reference_count=0")
    print(f"manifest_tree_sha256={manifest_digest.hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
