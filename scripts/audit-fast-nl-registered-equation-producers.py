#!/usr/bin/env python3
"""Audit the frozen 344-equation fast-NL export against current Candle.

This is a source/export identity preflight.  It does not execute the checker
and is not release evidence.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys


DEFAULT_CANDLE = pathlib.Path(
    "/project/worktrees/candle-direct-fast-nl-runtime-v1"
)
DEFAULT_CAKEML = pathlib.Path(
    "/project/worktrees/cakeml-direct-fast-nl-integration-v1"
)
DEFAULT_EXPORT_REVISION = "da7ec84c"
DATA_RELATIVE = pathlib.Path(
    "candle/prover/compute/"
    "compute_registeredCase10173HistoricalChunk16DataScript.sml"
)


def git(repo: pathlib.Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *arguments], text=True, errors="replace"
    )


def producer_blocks(text: str, constant: str) -> list[str]:
    pattern = re.compile(
        r"\blet\s+(" + re.escape(constant) + r"_(?:def|compute))\b"
    )
    blocks: list[str] = []
    for match in pattern.finditer(text):
        end = text.find(";;", match.start())
        blocks.append(text[match.start() : end + 2 if end >= 0 else len(text)])
    return blocks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle", type=pathlib.Path, default=DEFAULT_CANDLE)
    parser.add_argument("--cakeml", type=pathlib.Path, default=DEFAULT_CAKEML)
    parser.add_argument("--export-revision", default=DEFAULT_EXPORT_REVISION)
    arguments = parser.parse_args()

    data_path = arguments.cakeml / DATA_RELATIVE
    data = data_path.read_text()
    exported_names = re.findall(r"^\s*\[?\(«([^»]+)»,\(", data, re.MULTILINE)
    if len(exported_names) != 344 or len(set(exported_names)) != 344:
        raise RuntimeError("frozen registered export is not 344 unique equations")
    selected = set(exported_names)

    producers: dict[str, list[pathlib.Path]] = {}
    binding_pattern = re.compile(r"\blet\s+([A-Za-z0-9_]+_(?:def|compute))\b")
    for source in (arguments.candle / "candle").glob("*.ml"):
        for binding in binding_pattern.findall(source.read_text(errors="replace")):
            constant = re.sub(r"_(?:def|compute)$", "", binding)
            if constant in selected:
                producers.setdefault(constant, []).append(
                    source.relative_to(arguments.candle)
                )

    missing = selected - set(producers)
    if missing:
        raise RuntimeError(
            "no current producer binding for: " + ", ".join(sorted(missing))
        )

    changed = set(
        pathlib.Path(path)
        for path in git(
            arguments.candle,
            "diff",
            "--name-only",
            f"{arguments.export_revision}..HEAD",
            "--",
            "candle",
        ).splitlines()
    )
    selected_in_changed_files: set[str] = set()
    compared_bindings = 0
    for constant, paths in producers.items():
        for relative in paths:
            if relative not in changed:
                continue
            selected_in_changed_files.add(constant)
            current = (arguments.candle / relative).read_text(errors="replace")
            try:
                old = git(
                    arguments.candle,
                    "show",
                    f"{arguments.export_revision}:{relative}",
                )
            except subprocess.CalledProcessError as error:
                raise RuntimeError(
                    f"selected producer {constant} is new after the export: {relative}"
                ) from error
            old_blocks = producer_blocks(old, constant)
            current_blocks = producer_blocks(current, constant)
            compared_bindings += 1
            if old_blocks != current_blocks:
                raise RuntimeError(
                    f"selected producer changed after export: {constant} in {relative}"
                )

    print("status=PASS")
    print("release_evidence=false")
    print(f"exported_equations={len(exported_names)}")
    print(f"current_producers={len(producers)}")
    print(f"changed_candle_files={len(changed)}")
    print(f"selected_heads_in_changed_files={len(selected_in_changed_files)}")
    print(f"compared_changed_producer_bindings={compared_bindings}")
    print(
        "selected_heads_in_unchanged_files="
        f"{len(selected) - len(selected_in_changed_files)}"
    )
    print(f"export_revision={arguments.export_revision}")
    print(f"candle_head={git(arguments.candle, 'rev-parse', 'HEAD').strip()}")
    print(f"cakeml_head={git(arguments.cakeml, 'rev-parse', 'HEAD').strip()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"status=FAIL\nreason={error}", file=sys.stderr)
        raise SystemExit(1)
