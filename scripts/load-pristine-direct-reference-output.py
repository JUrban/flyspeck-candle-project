#!/usr/bin/python3
"""Trusted fixed-path loader for the pristine direct-reference byte parser.

The caller supplies the project root as a trust input.  This loader reads the
fixed protocol and parser sources without following symlinks, checks both byte
records against the raw plan before execution, and compiles those exact bytes
directly.  It never imports a timestamp- or hash-based bytecode cache.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
from types import ModuleType
from typing import Any


PROTOCOL_PATH = "scripts/pristine_direct_reference_protocol.py"
OUTPUT_PARSER_PATH = "scripts/parse-pristine-direct-reference-output.py"
HEX64 = re.compile(r"[0-9a-f]{64}")


class LoaderError(ValueError):
    """A fixed source or its claimed plan authority is not exact."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise LoaderError(message)


def _content_record(path: str, data: bytes) -> dict[str, object]:
    return {
        "path": path,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _trusted_root(value: object) -> Path:
    require(type(value) is str or isinstance(value, Path),
            "project root is not an exact path")
    path = Path(value)
    require(path.is_absolute(), "project root is not absolute")
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise LoaderError(f"cannot resolve project root: {error}") from error
    require(path == resolved and resolved.is_dir(),
            "project root is not an exact ordinary directory")
    return resolved


def _read_fixed_source(root: Path, relative: str) -> bytes:
    logical = PurePosixPath(relative)
    require(not logical.is_absolute() and logical.parts and
            all(part not in {"", ".", ".."} for part in logical.parts),
            f"unsafe fixed source path: {relative}")
    path = root.joinpath(*logical.parts)
    try:
        require(path.resolve(strict=True) == path,
                f"fixed source is redirected: {relative}")
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
    except (OSError, LoaderError) as error:
        if isinstance(error, LoaderError):
            raise
        raise LoaderError(f"cannot open fixed source {relative}: {error}") from error
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode),
                f"fixed source is not an ordinary file: {relative}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    except OSError as error:
        raise LoaderError(f"cannot read fixed source {relative}: {error}") from error
    finally:
        os.close(descriptor)
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
            f"fixed source changed while reading: {relative}")
    data = b"".join(chunks)
    require(len(data) == before.st_size and data,
            f"fixed source byte count changed: {relative}")
    return data


def _claimed_record(plan: object, name: str) -> dict[str, Any]:
    require(isinstance(plan, dict), "raw plan is not an object")
    try:
        project = plan["authority"]["repositories"]["project"]
        producer = plan["authority"]["producer"]
        record = producer[name]
    except (KeyError, TypeError) as error:
        raise LoaderError(f"raw plan lacks {name} source authority") from error
    require(isinstance(project, dict) and set(project) == {
                "path", "git_head", "git_status",
            }, "raw plan project authority is malformed")
    require(isinstance(record, dict) and set(record) == {
                "path", "bytes", "sha256",
            } and isinstance(record.get("path"), str) and
            type(record.get("bytes")) is int and record["bytes"] > 0 and
            isinstance(record.get("sha256"), str) and
            HEX64.fullmatch(record["sha256"]) is not None,
            f"raw plan {name} source authority is malformed")
    return record


def _compile_exact_module(
    name: str, path: Path, data: bytes, injected: dict[str, object] | None = None,
) -> ModuleType:
    try:
        code = compile(data, str(path), "exec", dont_inherit=True, optimize=0)
    except (SyntaxError, ValueError, TypeError) as error:
        raise LoaderError(f"cannot compile exact source {path.name}: {error}") from error
    module = ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    module.__loader__ = None
    if injected is not None:
        module.__dict__.update(injected)
    try:
        exec(code, module.__dict__)
    except Exception as error:
        raise LoaderError(f"cannot execute exact source {path.name}: {error}") from error
    return module


def load_trusted_output_parser(project_root: object, plan: object) -> ModuleType:
    """Load exact fixed sources after binding both to ``plan`` authority."""

    root = _trusted_root(project_root)
    protocol_bytes = _read_fixed_source(root, PROTOCOL_PATH)
    parser_bytes = _read_fixed_source(root, OUTPUT_PARSER_PATH)
    protocol_record = _content_record(PROTOCOL_PATH, protocol_bytes)
    parser_record = _content_record(OUTPUT_PARSER_PATH, parser_bytes)
    claimed_protocol = _claimed_record(plan, "protocol")
    claimed_parser = _claimed_record(plan, "output_parser")
    project = plan["authority"]["repositories"]["project"]
    require(project["path"] == str(root),
            "raw plan project root differs from trusted project root")
    require(claimed_protocol == protocol_record,
            "fixed protocol source differs from plan authority")
    require(claimed_parser == parser_record,
            "fixed output parser source differs from plan authority")

    protocol_path = root.joinpath(*PurePosixPath(PROTOCOL_PATH).parts)
    protocol = _compile_exact_module(
        "_trusted_pristine_direct_reference_protocol", protocol_path,
        protocol_bytes,
    )
    try:
        protocol.validate_raw_plan(plan)
    except Exception as error:
        if isinstance(error, protocol.ProtocolError):
            raise LoaderError(f"raw plan fails exact protocol: {error}") from error
        raise

    parser_path = root.joinpath(*PurePosixPath(OUTPUT_PARSER_PATH).parts)
    parser = _compile_exact_module(
        "_trusted_pristine_direct_reference_output", parser_path, parser_bytes,
        {
            "_TRUSTED_ACTIVATION": True,
            "_TRUSTED_PROJECT_ROOT_INPUT": str(root),
            "_TRUSTED_SOURCE_BYTES_INPUT": parser_bytes,
            "_TRUSTED_PROTOCOL_BYTES_INPUT": protocol_bytes,
            "_TRUSTED_PROTOCOL_MODULE_INPUT": protocol,
        },
    )
    try:
        parser._require_compatible_protocol(protocol)
    except parser.OutputProtocolError as error:
        raise LoaderError(f"parser/protocol compatibility failure: {error}") from error
    return parser
