#!/usr/bin/python3
"""Trusted fixed-path loader for the pristine direct-reference byte parser.

The caller supplies the project root as a trust input.  This loader reads the
three fixed protocol/parser sources through one pinned directory traversal,
checks their byte records against the raw plan before execution, and compiles
those exact bytes directly.  It never imports a timestamp- or hash-based
bytecode cache.

This source and its private module inputs are not an in-process security
boundary.  A production collector must invoke this loader as the exclusive
entrypoint of a fresh isolated Python process and authenticate the loader,
checkout root, Python executable, and Python module closure externally.
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
DIRECT_PROTOCOL_PATH = "scripts/direct_release_protocol.py"
FIXED_SOURCES = {
    "protocol": PROTOCOL_PATH,
    "output_parser": OUTPUT_PARSER_PATH,
    "direct_release_protocol": DIRECT_PROTOCOL_PATH,
}
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


def _descriptor_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev, value.st_ino, value.st_mode, value.st_size,
        value.st_mtime_ns, value.st_ctime_ns,
    )


def _open_flags(*, directory: bool) -> int:
    require(hasattr(os, "O_NOFOLLOW"),
            "platform lacks no-follow descriptor traversal")
    if directory:
        require(hasattr(os, "O_DIRECTORY"),
                "platform lacks directory-only descriptor traversal")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
    if directory:
        flags |= os.O_DIRECTORY
    return flags


class _PinnedSourceTraversal:
    """Hold one no-follow root/scripts/files traversal until compilation ends."""

    def __init__(self, root: Path):
        self.root = root
        self._descriptors: list[int] = []
        self._snapshots: list[tuple[str, int, tuple[int, ...]]] = []
        self.source_bytes: dict[str, bytes] = {}
        try:
            self.root_descriptor = os.open(
                str(root), _open_flags(directory=True),
            )
            self._hold("project root", self.root_descriptor, directory=True)
            named_root = os.stat(str(root), follow_symlinks=False)
            require(
                _descriptor_identity(named_root) ==
                self._snapshots[-1][2],
                "trusted project root changed while it was opened",
            )
            self.scripts_descriptor = os.open(
                "scripts", _open_flags(directory=True),
                dir_fd=self.root_descriptor,
            )
            self._hold(
                "scripts directory", self.scripts_descriptor, directory=True,
            )
            for authority_name, relative in FIXED_SOURCES.items():
                logical = PurePosixPath(relative)
                require(
                    not logical.is_absolute() and len(logical.parts) == 2 and
                    logical.parts[0] == "scripts" and
                    all(part not in {"", ".", ".."} for part in logical.parts),
                    f"unsafe fixed source path: {relative}",
                )
                descriptor = os.open(
                    logical.parts[1], _open_flags(directory=False),
                    dir_fd=self.scripts_descriptor,
                )
                self._hold(relative, descriptor, directory=False)
                self.source_bytes[authority_name] = self._read(
                    relative, descriptor,
                )
            self.verify_unchanged()
        except (OSError, LoaderError) as error:
            self.close()
            if isinstance(error, LoaderError):
                raise
            raise LoaderError(
                f"cannot pin fixed pristine-reference sources: {error}"
            ) from error

    def _hold(self, label: str, descriptor: int, *, directory: bool) -> None:
        self._descriptors.append(descriptor)
        try:
            current = os.fstat(descriptor)
        except OSError as error:
            raise LoaderError(f"cannot inspect {label}: {error}") from error
        require(
            stat.S_ISDIR(current.st_mode) if directory
            else stat.S_ISREG(current.st_mode),
            f"pinned {label} is not an ordinary " +
            ("directory" if directory else "file"),
        )
        self._snapshots.append(
            (label, descriptor, _descriptor_identity(current)),
        )

    def _read(self, label: str, descriptor: int) -> bytes:
        chunks: list[bytes] = []
        try:
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            current = os.fstat(descriptor)
        except OSError as error:
            raise LoaderError(f"cannot read fixed source {label}: {error}") from error
        data = b"".join(chunks)
        expected = next(
            snapshot for name, held, snapshot in self._snapshots
            if name == label and held == descriptor
        )
        require(_descriptor_identity(current) == expected,
                f"fixed source changed while reading: {label}")
        require(len(data) == current.st_size and data,
                f"fixed source byte count changed: {label}")
        return data

    def verify_unchanged(self) -> None:
        for label, descriptor, expected in self._snapshots:
            try:
                current = os.fstat(descriptor)
            except OSError as error:
                raise LoaderError(
                    f"cannot recheck pinned {label}: {error}"
                ) from error
            require(_descriptor_identity(current) == expected,
                    f"pinned {label} changed during trusted activation")

    def close(self) -> None:
        while self._descriptors:
            descriptor = self._descriptors.pop()
            try:
                os.close(descriptor)
            except OSError:
                pass


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
    """Load three exact sources after binding each to ``plan`` authority."""

    root = _trusted_root(project_root)
    pinned = _PinnedSourceTraversal(root)
    try:
        source_records = {
            name: _content_record(FIXED_SOURCES[name], data)
            for name, data in pinned.source_bytes.items()
        }
        claimed_records = {
            name: _claimed_record(plan, name) for name in FIXED_SOURCES
        }
        project = plan["authority"]["repositories"]["project"]
        require(project["path"] == str(root),
                "raw plan project root differs from trusted project root")
        for name, record in source_records.items():
            require(claimed_records[name] == record,
                    f"fixed {name.replace('_', ' ')} source differs from plan "
                    "authority")

        direct_bytes = pinned.source_bytes["direct_release_protocol"]
        direct_path = root.joinpath(*PurePosixPath(DIRECT_PROTOCOL_PATH).parts)
        direct = _compile_exact_module(
            "_trusted_direct_release_protocol", direct_path, direct_bytes,
        )
        protocol_bytes = pinned.source_bytes["protocol"]
        protocol_path = root.joinpath(*PurePosixPath(PROTOCOL_PATH).parts)
        protocol = _compile_exact_module(
            "_trusted_pristine_direct_reference_protocol", protocol_path,
            protocol_bytes,
            {"_TRUSTED_DIRECT_PROTOCOL_MODULE_INPUT": direct},
        )
        try:
            protocol.validate_raw_plan(plan)
            protocol._direct_protocol()
        except Exception as error:
            if isinstance(error, protocol.ProtocolError):
                raise LoaderError(
                    f"raw plan or direct protocol fails exact protocol: {error}"
                ) from error
            raise

        parser_bytes = pinned.source_bytes["output_parser"]
        parser_path = root.joinpath(*PurePosixPath(OUTPUT_PARSER_PATH).parts)
        parser = _compile_exact_module(
            "_trusted_pristine_direct_reference_output", parser_path,
            parser_bytes,
            {
                "_TRUSTED_ACTIVATION": True,
                "_TRUSTED_PROJECT_ROOT_INPUT": str(root),
                "_TRUSTED_SOURCE_BYTES_INPUT": parser_bytes,
                "_TRUSTED_PROTOCOL_BYTES_INPUT": protocol_bytes,
                "_TRUSTED_DIRECT_PROTOCOL_BYTES_INPUT": direct_bytes,
                "_TRUSTED_PROTOCOL_MODULE_INPUT": protocol,
            },
        )
        try:
            parser._require_compatible_protocol(protocol)
        except parser.OutputProtocolError as error:
            raise LoaderError(
                f"parser/protocol compatibility failure: {error}"
            ) from error
        pinned.verify_unchanged()
        return parser
    finally:
        try:
            pinned.verify_unchanged()
        finally:
            pinned.close()
