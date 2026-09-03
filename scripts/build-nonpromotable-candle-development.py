#!/usr/bin/env python3
"""Link a checked, explicitly non-promotable Candle development runtime.

This helper is for fast frontend iteration after an in-place CakeML proof
build.  It deliberately does not consume or manufacture ordinary canonical
bootstrap/link provenance, and its receipt cannot be used as S1/S2/S3 or
release evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
CAPABILITY_ARGUMENT = "--candle-parser-diagnostic-capability-v1"
CAPABILITY_LINE = (
    b"CANDLE_CAMLPARSER_DIAGNOSTIC_CAPABILITY_V1\t"
    b"caml_parser$run\tstdin-exact-bytes\tparser-only\t"
    b"no-inference\tno-evaluation\n"
)
CANDLE_SMOKE_INPUT = b"let candle_development_smoke = 1;;\n"
CANDLE_SMOKE_SUFFIX = b"# val candle_development_smoke = 1: int\n# "
SOURCE_PATH = Path(__file__).resolve()


class ContractError(ValueError):
    """A requested development link did not satisfy its contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def file_record(path: Path, displayed_path: str | None = None) -> dict[str, Any]:
    before = path.stat()
    require(stat.S_ISREG(before.st_mode), f"not an ordinary file: {path}")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while block := stream.read(4 * 1024 * 1024):
            digest.update(block)
            size += len(block)
    after = path.stat()
    require(
        (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        and size == before.st_size,
        f"file changed while hashing: {path}",
    )
    result: dict[str, Any] = {"bytes": size, "sha256": digest.hexdigest()}
    if displayed_path is not None:
        result["path"] = displayed_path
    return result


def git_identity(root: Path, expected: str, label: str) -> dict[str, Any]:
    require(root.is_absolute() and root.is_dir(), f"invalid {label} root: {root}")
    require(HEX40_RE.fullmatch(expected) is not None, f"invalid expected {label} commit")
    head = subprocess.run(
        ["/usr/bin/git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
    ).stdout.decode().strip()
    require(head == expected, f"{label} HEAD mismatch: expected {expected}, found {head}")
    status = subprocess.run(
        ["/usr/bin/git", "-C", str(root), "status", "--porcelain=v1"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"},
    ).stdout
    require(status == b"", f"{label} tracked worktree is dirty")
    return {"commit": head, "root": str(root), "tracked_worktree_clean": True}


def copy_checked(source: Path, destination: Path) -> dict[str, Any]:
    source_record = file_record(source, str(source))
    with source.open("rb") as input_stream, destination.open("xb") as output_stream:
        shutil.copyfileobj(input_stream, output_stream, 4 * 1024 * 1024)
        output_stream.flush()
        os.fsync(output_stream.fileno())
    copied_record = file_record(destination, destination.name)
    require(
        (source_record["bytes"], source_record["sha256"])
        == (copied_record["bytes"], copied_record["sha256"]),
        f"copied bytes differ: {source} -> {destination}",
    )
    return {"source": source_record, "captured": copied_record}


def run_captured(
    command: list[str], root: Path, stem: str, *, stdin: Path | None = None,
) -> dict[str, Any]:
    stdout_path = root / f"{stem}.stdout"
    stderr_path = root / f"{stem}.stderr"
    started = time.monotonic()
    input_stream = stdin.open("rb") if stdin is not None else subprocess.DEVNULL
    try:
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            completed = subprocess.run(
                command, cwd=root, env={
                    "LC_ALL": "C",
                    "PATH": "/usr/bin:/bin",
                    "TMPDIR": str(root / ".candle-native-tmp"),
                }, stdin=input_stream, stdout=stdout, stderr=stderr, check=False,
                close_fds=True,
            )
    finally:
        if stdin is not None:
            input_stream.close()
    return {
        "command": command,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "exit_code": completed.returncode,
        "stdout": file_record(stdout_path, stdout_path.name),
        "stderr": file_record(stderr_path, stderr_path.name),
    }


def run(arguments: argparse.Namespace) -> dict[str, Any]:
    require(arguments.output_root.is_absolute(), "output root must be absolute")
    require(arguments.output_root.parent.is_dir(), "output parent does not exist")
    require(not arguments.output_root.exists(), "output root already exists")
    cakeml = git_identity(
        arguments.cakeml_root, arguments.cakeml_commit, "CakeML",
    )
    candle = git_identity(
        arguments.candle_root, arguments.candle_commit, "Candle",
    )
    hol4 = git_identity(
        arguments.hol4_root, arguments.hol4_commit, "HOL4",
    )
    sources = {
        "cake.S.orig": arguments.cakeml_root
        / "compiler/bootstrap/compilation/x64/64/cake.S",
        "config_enc_str.txt": arguments.cakeml_root
        / "compiler/bootstrap/compilation/x64/64/config_enc_str.txt",
        "candle_boot.ml": arguments.cakeml_root / "candle/prover/candle_boot.ml",
        "basis_ffi.c": arguments.cakeml_root / "basis/basis_ffi.c",
        "Makefile": arguments.cakeml_root
        / "compiler/bootstrap/compilation/x64/Makefile",
        "cake.S.patch": arguments.candle_root / "candle/cake.S.patch",
        "insulate.py": arguments.candle_root / "candle/insulate.py",
    }
    staging = Path(tempfile.mkdtemp(
        prefix=f".{arguments.output_root.name}.pending-",
        dir=arguments.output_root.parent,
    ))
    (staging / ".candle-native-tmp").mkdir(mode=0o700)
    captured = {
        name: copy_checked(source, staging / name)
        for name, source in sources.items()
    }
    shutil.copyfile(staging / "cake.S.orig", staging / "cake.S")
    require(
        file_record(staging / "cake.S")["sha256"]
        == captured["cake.S.orig"]["captured"]["sha256"],
        "assembly work copy differs before patching",
    )

    patch_result = run_captured(
        ["/usr/bin/patch", "--batch", "--forward", "cake.S"],
        staging, "patch", stdin=staging / "cake.S.patch",
    )
    require(patch_result["exit_code"] == 0, "Candle assembly patch failed")
    require(
        file_record(staging / "cake.S")["sha256"]
        != captured["cake.S.orig"]["captured"]["sha256"],
        "Candle assembly patch did not change cake.S",
    )

    build_command = [
        "/usr/bin/time", "-v", "-o", "build.time",
        "/usr/bin/make", "--no-builtin-rules", "--no-builtin-variables",
        "-B", "-j1", "-f", "Makefile", "OS=Linux", "CC=/usr/bin/cc",
        "CFLAGS=-O2", "LOADLIBES=", "EVALFLAG=-DEVAL", "LDFLAGS=",
        "LDLIBS=-lm", "cake",
    ]
    build_result = run_captured(build_command, staging, "build")
    require(build_result["exit_code"] == 0, "native Candle development link failed")
    require((staging / "cake").is_file(), "native link did not produce cake")
    (staging / "cake").chmod(0o755)

    types_result = run_captured(
        ["./cake", "--types"], staging, "types",
    )
    require(types_result["exit_code"] == 0, "cake --types failed")
    require(types_result["stdout"]["bytes"] == 0, "cake --types wrote unexpected stdout")
    require(types_result["stderr"]["bytes"] > 0, "cake --types emitted no type inventory")
    (staging / "types.stderr").rename(staging / "types.txt")
    types_result["stderr"] = file_record(staging / "types.txt", "types.txt")

    insulate_result = run_captured(
        ["/usr/bin/python3", "insulate.py", "types.txt", "insulate.ml"],
        staging, "insulate",
    )
    require(insulate_result["exit_code"] == 0, "insulation generation failed")
    require((staging / "insulate.ml").is_file(), "insulation output is missing")

    capability_result = run_captured(
        ["./cake", CAPABILITY_ARGUMENT], staging, "capability",
    )
    require(capability_result["exit_code"] == 0, "parser capability command failed")
    require(
        (staging / "capability.stdout").read_bytes() == CAPABILITY_LINE
        and capability_result["stderr"]["bytes"] == 0,
        "linked runtime failed the exact parser-only capability handshake",
    )

    (staging / "candle-smoke.stdin").write_bytes(CANDLE_SMOKE_INPUT)
    candle_smoke_result = run_captured(
        ["/usr/bin/timeout", "30s", "./cake", "--candle"],
        staging, "candle-smoke", stdin=staging / "candle-smoke.stdin",
    )
    require(
        candle_smoke_result["exit_code"] == 0,
        "linked runtime failed the Candle boot smoke command",
    )
    require(
        candle_smoke_result["stderr"]["bytes"] == 0
        and (staging / "candle-smoke.stdout").read_bytes().endswith(
            CANDLE_SMOKE_SUFFIX
        ),
        "linked runtime did not select and evaluate the Candle boot",
    )

    material_names = [
        "cake.S.orig", "cake.S", "cake", "config_enc_str.txt",
        "candle_boot.ml", "basis_ffi.c", "Makefile", "cake.S.patch",
        "insulate.py", "types.txt", "insulate.ml", "patch.stdout",
        "patch.stderr", "build.stdout", "build.stderr", "build.time",
        "types.stdout", "insulate.stdout", "insulate.stderr",
        "capability.stdout", "capability.stderr",
        "candle-smoke.stdin", "candle-smoke.stdout", "candle-smoke.stderr",
    ]
    products = {
        name: file_record(staging / name, name)
        for name in material_names
    }
    checksums = "".join(
        f"{products[name]['sha256']}  {name}\n" for name in sorted(products)
    ).encode()
    (staging / "DEVELOPMENT-SHA256SUMS").write_bytes(checksums)
    receipt = {
        "schema": 1,
        "kind": "nonpromotable-candle-development-link",
        "claim": (
            "development-only native link; not canonical bootstrap, ordinary "
            "linked provenance, S1, S2, S3, a theorem, or release evidence"
        ),
        "promotion_allowed": False,
        "s1_evidence": False,
        "s2_evidence": False,
        "s3_evidence": False,
        "ordinary_linked_provenance_produced": False,
        "repositories": {
            "cakeml": cakeml,
            "candle": candle,
            "hol4": hol4,
        },
        "controller": file_record(SOURCE_PATH, str(SOURCE_PATH)),
        "captured_sources": captured,
        "patch": patch_result,
        "build": build_result,
        "types": types_result,
        "insulation": insulate_result,
        "capability": capability_result,
        "candle_smoke": candle_smoke_result,
        "products": products,
    }
    (staging / "DEVELOPMENT-NONPROMOTABLE.json").write_bytes(json_bytes(receipt))

    for path in staging.iterdir():
        if path.is_file():
            path.chmod(0o555 if path.name == "cake" else 0o444)
    (staging / ".candle-native-tmp").rmdir()
    staging.chmod(0o555)
    staging.rename(arguments.output_root)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cakeml-root", type=Path, required=True)
    parser.add_argument("--cakeml-commit", required=True)
    parser.add_argument("--candle-root", type=Path, required=True)
    parser.add_argument("--candle-commit", required=True)
    parser.add_argument("--hol4-root", type=Path, required=True)
    parser.add_argument("--hol4-commit", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    receipt = run(parser.parse_args())
    print(
        f"{receipt['kind']}: development-only link passed; "
        f"cake sha256={receipt['products']['cake']['sha256']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f"development Candle link rejected: {error}") from error
