#!/usr/bin/env python3
"""Reject proof-harness sources that shadow a source in the parent project."""

from __future__ import annotations

import argparse
import pathlib


DEFAULT_PROJECT_ROOT = pathlib.Path(
    "/project/worktrees/cakeml-nl-packed-refinement-v1"
)
DEFAULT_SCRATCH = (
    DEFAULT_PROJECT_ROOT
    / "candle/prover/compute/external_witness_probe_scratch"
)


def source_collisions(
    project_root: pathlib.Path, scratch: pathlib.Path
) -> tuple[list[pathlib.Path], dict[str, list[pathlib.Path]]]:
    project_root = project_root.resolve()
    scratch = scratch.resolve()
    try:
        scratch.relative_to(project_root)
    except ValueError as error:
        raise ValueError("scratch_not_below_project_root") from error

    sources = sorted(scratch.glob("*Script.sml"))
    collisions: dict[str, list[pathlib.Path]] = {}
    for source in sources:
        matches = []
        for candidate in project_root.rglob(source.name):
            if ".git" in candidate.parts or scratch in candidate.parents:
                continue
            matches.append(candidate)
        if matches:
            collisions[source.name] = sorted(matches)
    return sources, collisions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=pathlib.Path, default=DEFAULT_PROJECT_ROOT)
    parser.add_argument("--scratch", type=pathlib.Path, default=DEFAULT_SCRATCH)
    args = parser.parse_args()

    if not args.project_root.is_dir():
        print(f"project_root_missing={args.project_root}")
        print("status=1")
        return 1
    if not args.scratch.is_dir():
        print(f"scratch_missing={args.scratch}")
        print("status=1")
        return 1

    try:
        sources, collisions = source_collisions(args.project_root, args.scratch)
    except ValueError as error:
        print(f"identity_error={error}")
        print("status=1")
        return 1

    print(f"scratch_source_count={len(sources)}")
    print(f"duplicate_source_name_count={len(collisions)}")
    for name, paths in sorted(collisions.items()):
        for path in paths:
            print(f"duplicate_source={name}:{path}")
    status = 0 if sources and not collisions else 1
    print(f"status={status}")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
