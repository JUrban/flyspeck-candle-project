#!/usr/bin/env python3
"""Describe a fail-closed namespace for a development-only HOL theory cache.

This program does not invoke Holmake and does not create a cache.  It emits a
canonical preflight receipt whose namespace digest can be used as the sole
directory name passed to Holmake's ``--cache-dir`` option by a later benchmark
controller.  Native HOL cache keys do not bind the producing HOL executable,
heap, kernel, or host toolchain, so those identities are bound here instead.

Invoke this file as ``/usr/bin/python3 -I -S <file> ...``.  It rejects a
non-isolated interpreter before authenticating any experiment inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat
import subprocess
import sys
from typing import Any


GIT = Path("/usr/bin/git")
LDD = Path("/usr/bin/ldd")
POLY = Path("/usr/bin/poly")
CP = Path("/bin/cp")
SH = Path("/bin/sh")
BASH = Path("/bin/bash")
LD_CACHE = Path("/etc/ld.so.cache")
CONTROLLED_ENVIRONMENT = {
    "PATH": "/usr/bin:/bin",
    "LC_ALL": "C",
    "LANG": "C",
}
EXPECTED_ISOLATED_SYS_PATH = [
    "/usr/lib/python312.zip",
    "/usr/lib/python3.12",
    "/usr/lib/python3.12/lib-dynload",
]
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
TARGET_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+/-]*")
ADDRESS_RE = re.compile(r"0x[0-9a-fA-F]+")
LDD_NAMED_RE = re.compile(
    r"([A-Za-z0-9_.+-]+) => (/[^ ()]+) \((0x[0-9a-fA-F]+)\)"
)
LDD_DIRECT_RE = re.compile(r"(/[^ ()]+) \((0x[0-9a-fA-F]+)\)")
LDD_VDSO_RE = re.compile(
    r"linux-vdso[.]so[.][0-9]+ \((0x[0-9a-fA-F]+)\)"
)
SCHEMA = "candle-hol4-native-cache-preflight-v1"
NAMESPACE_SCHEMA = "candle-hol4-native-cache-namespace-v1"
POLICY = "development-only-cache-disabled-release-v1"
V1_TARGET_DIRECTORY = "compiler/bootstrap/translation"
V1_TARGET = "compiler64ProgTheory.uo"
PROGRAM = Path(__file__).resolve(strict=True)
PYTHON = Path(sys.executable).resolve(strict=True)


class PreflightFailure(RuntimeError):
    """The requested cache namespace could not be authenticated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PreflightFailure(message)


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def compact_sha256(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _stable_stat(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev, metadata.st_ino, metadata.st_mode, metadata.st_nlink,
        metadata.st_uid, metadata.st_gid, metadata.st_size,
        metadata.st_mtime_ns, metadata.st_ctime_ns,
    )


def stable_file_record(
    path: Path, label: str, *, include_git_blob: bool = False,
) -> dict[str, Any]:
    digest = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise PreflightFailure(f"cannot open {label}: {path}: {error}") from error
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode), f"{label} is not a regular file: {path}")
        git_blob = hashlib.sha1(usedforsecurity=False)
        if include_git_blob:
            git_blob.update(f"blob {before.st_size}\0".encode("ascii"))
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
            if include_git_blob:
                git_blob.update(block)
        after = os.fstat(descriptor)
        require(_stable_stat(before) == _stable_stat(after),
                f"{label} changed while it was hashed: {path}")
        record = {
            "bytes": after.st_size,
            "mode": stat.S_IMODE(after.st_mode),
            "sha256": digest.hexdigest(),
        }
        if include_git_blob:
            record["git_blob_sha1"] = git_blob.hexdigest()
        return record
    finally:
        os.close(descriptor)


def canonical_directory(path: Path, label: str) -> Path:
    path = Path(os.path.abspath(path))
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise PreflightFailure(f"missing {label}: {path}") from error
    require(stat.S_ISDIR(metadata.st_mode) and not path.is_symlink(),
            f"{label} is not an ordinary directory: {path}")
    require(path.resolve(strict=True) == path,
            f"{label} is not a canonical path: {path}")
    return path


def resolved_file(path: Path, label: str, *, executable: bool = False) -> Path:
    argument = Path(os.path.abspath(path))
    try:
        resolved = argument.resolve(strict=True)
        metadata = resolved.stat()
    except FileNotFoundError as error:
        raise PreflightFailure(f"missing {label}: {argument}") from error
    require(stat.S_ISREG(metadata.st_mode),
            f"{label} does not resolve to an ordinary file: {argument}")
    require(not executable or os.access(resolved, os.X_OK),
            f"{label} is not executable: {resolved}")
    return resolved


def file_identity(path: Path, label: str, *, executable: bool = False) -> dict[str, Any]:
    resolved = resolved_file(path, label, executable=executable)
    return stable_file_record(resolved, label)


def local_file_route(path: Path, label: str, *, executable: bool = False) -> dict[str, str]:
    argument = Path(os.path.abspath(path))
    resolved = resolved_file(argument, label, executable=executable)
    return {"argument": str(argument), "resolved": str(resolved)}


def run(arguments: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        arguments,
        cwd=None if cwd is None else str(cwd),
        env=CONTROLLED_ENVIRONMENT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    require(completed.returncode == 0,
            f"command failed ({completed.returncode}): {' '.join(arguments)}: "
            f"{completed.stderr.strip()}")
    return completed


def ignored_artifact_inventory(
    root: Path, label: str, *, require_empty: bool,
) -> dict[str, Any]:
    result = run([
        str(GIT), "-C", str(root), "ls-files", "--others", "--ignored",
        "--exclude-standard", "-z",
    ])
    require(result.stderr == "", f"git ignored-file scan wrote stderr: {label}")
    paths = result.stdout.split("\0")
    require(paths[-1:] == [""], f"unterminated ignored-file scan: {label}")
    paths = paths[:-1]
    require(paths == sorted(paths), f"unsorted ignored-file scan: {label}")
    if require_empty:
        require(not paths, f"{label} contains {len(paths)} ignored artifacts")
    records = []
    total_bytes = 0
    for value in paths:
        pure = PurePosixPath(value)
        require(value and not pure.is_absolute() and ".." not in pure.parts,
                f"unsafe ignored path in {label}: {value!r}")
        path = root.joinpath(*pure.parts)
        try:
            before = path.lstat()
        except OSError as error:
            raise PreflightFailure(
                f"cannot inspect ignored artifact in {label}: {value}: {error}"
            ) from error
        if stat.S_ISREG(before.st_mode):
            identity = stable_file_record(path, f"{label} ignored artifact {value}")
            record = {"path": value, "kind": "regular", **identity}
            total_bytes += identity["bytes"]
        elif stat.S_ISLNK(before.st_mode):
            target = os.readlink(path)
            after = path.lstat()
            require(_stable_stat(before) == _stable_stat(after),
                    f"ignored symlink changed while inspected: {label}:{value}")
            record = {
                "path": value,
                "kind": "symlink",
                "mode": stat.S_IMODE(after.st_mode),
                "target": target,
            }
        else:
            raise PreflightFailure(
                f"unsupported ignored artifact type in {label}: {value}"
            )
        records.append(record)
    return {
        "count": len(records),
        "total_regular_bytes": total_bytes,
        "ordered_inventory_sha256": compact_sha256(records),
        "policy": "must-be-empty-v1" if require_empty else "content-bound-v1",
    }


def tracked_worktree_shape(root: Path, label: str) -> dict[str, Any]:
    tree_result = run([
        str(GIT), "-C", str(root), "ls-tree", "-r", "-z", "HEAD",
    ])
    require(tree_result.stderr == "", f"git tree scan wrote stderr: {label}")
    tree_items = tree_result.stdout.split("\0")
    require(tree_items[-1:] == [""], f"unterminated Git tree scan: {label}")
    expected: dict[str, tuple[str, str]] = {}
    for item in tree_items[:-1]:
        try:
            header, value = item.split("\t", 1)
            mode, object_kind, object_id = header.split(" ")
        except ValueError as error:
            raise PreflightFailure(f"malformed Git tree entry in {label}") from error
        require(object_kind == "blob" and mode in {"100644", "100755", "120000"},
                f"unsupported Git tree entry in {label}: {item!r}")
        require(value not in expected, f"duplicate Git tree path in {label}: {value}")
        require(re.fullmatch(r"[0-9a-f]{40}", object_id) is not None,
                f"malformed Git object ID in {label}: {value}")
        expected[value] = (mode, object_id)

    index_result = run([
        str(GIT), "-C", str(root), "ls-files", "--stage", "-v", "-z",
    ])
    require(index_result.stderr == "", f"git index scan wrote stderr: {label}")
    index_items = index_result.stdout.split("\0")
    require(index_items[-1:] == [""], f"unterminated Git index scan: {label}")
    index_paths: set[str] = set()
    for item in index_items[:-1]:
        try:
            tagged_header, value = item.split("\t", 1)
            tag, mode, object_id, stage = tagged_header.split(" ")
        except ValueError as error:
            raise PreflightFailure(f"malformed Git index entry in {label}") from error
        require(tag == "H", f"non-default Git index flag in {label}: {value}:{tag}")
        require(stage == "0", f"nonzero Git index stage in {label}: {value}:{stage}")
        require(value in expected and expected[value] == (mode, object_id),
                f"Git index/HEAD mismatch in {label}: {value}")
        require(value not in index_paths, f"duplicate Git index path in {label}: {value}")
        index_paths.add(value)
    require(index_paths == set(expected), f"Git index/HEAD path mismatch in {label}")

    tracked = set(expected)
    allowed_directories: set[str] = set()
    for value in tracked:
        pure = PurePosixPath(value)
        require(value and not pure.is_absolute() and ".." not in pure.parts,
                f"unsafe tracked path in {label}: {value!r}")
        parent = pure.parent
        while parent != PurePosixPath("."):
            allowed_directories.add(parent.as_posix())
            parent = parent.parent

    observed_files: set[str] = set()
    observed_directories: set[str] = set()
    actual_records: list[dict[str, Any]] = []

    def walk(directory: Path, relative: PurePosixPath) -> None:
        before_names = sorted(entry.name for entry in os.scandir(directory))
        for name in before_names:
            if relative == PurePosixPath(".") and name == ".git":
                continue
            path = directory / name
            item_relative = relative / name
            value = item_relative.as_posix()
            metadata = path.lstat()
            if stat.S_ISDIR(metadata.st_mode):
                require(value in allowed_directories,
                        f"extra directory in {label}: {value}")
                observed_directories.add(value)
                walk(path, item_relative)
            elif stat.S_ISREG(metadata.st_mode):
                require(value in tracked, f"extra filesystem entry in {label}: {value}")
                mode, object_id = expected[value]
                require(mode in {"100644", "100755"},
                        f"tracked file type mismatch in {label}: {value}")
                identity = stable_file_record(
                    path, f"{label} tracked file {value}", include_git_blob=True,
                )
                require(identity["git_blob_sha1"] == object_id,
                        f"tracked file content mismatch in {label}: {value}")
                executable = bool(identity["mode"] & 0o111)
                require(executable == (mode == "100755"),
                        f"tracked executable mode mismatch in {label}: {value}")
                actual_records.append({
                    "path": value,
                    "git_mode": mode,
                    "bytes": identity["bytes"],
                    "sha256": identity["sha256"],
                })
                observed_files.add(value)
            elif stat.S_ISLNK(metadata.st_mode):
                require(value in tracked, f"extra filesystem entry in {label}: {value}")
                mode, object_id = expected[value]
                require(mode == "120000", f"tracked symlink type mismatch: {label}:{value}")
                target = os.fsencode(os.readlink(path))
                after = path.lstat()
                require(_stable_stat(metadata) == _stable_stat(after),
                        f"tracked symlink changed in {label}: {value}")
                git_blob = hashlib.sha1(usedforsecurity=False)
                git_blob.update(f"blob {len(target)}\0".encode("ascii"))
                git_blob.update(target)
                require(git_blob.hexdigest() == object_id,
                        f"tracked symlink content mismatch in {label}: {value}")
                actual_records.append({
                    "path": value,
                    "git_mode": mode,
                    "bytes": len(target),
                    "sha256": hashlib.sha256(target).hexdigest(),
                })
                observed_files.add(value)
            else:
                raise PreflightFailure(f"special filesystem entry in {label}: {value}")
        after_names = sorted(entry.name for entry in os.scandir(directory))
        require(before_names == after_names,
                f"{label} directory changed while its shape was checked: {directory}")

    walk(root, PurePosixPath("."))
    require(observed_files == tracked, f"tracked filesystem shape mismatch: {label}")
    require(observed_directories == allowed_directories,
            f"tracked directory shape mismatch: {label}")
    actual_records.sort(key=lambda record: record["path"])
    return {
        "tracked_file_count": len(tracked),
        "tracked_directory_count": len(allowed_directories),
        "ordered_tracked_content_sha256": compact_sha256(actual_records),
        "policy": "exact-tracked-files-and-ancestor-directories-only-v1",
    }


def toolchain_tree_inventory(root: Path, containment: Path, label: str) -> dict[str, Any]:
    root = canonical_directory(root, label)
    containment = canonical_directory(containment, f"{label} containment root")
    require(root.is_relative_to(containment), f"{label} is outside its containment root")
    records: list[dict[str, Any]] = []
    total_bytes = 0

    def walk(directory: Path, relative: PurePosixPath) -> None:
        nonlocal total_bytes
        try:
            before_names = sorted(entry.name for entry in os.scandir(directory))
        except OSError as error:
            raise PreflightFailure(f"cannot list {label}: {directory}: {error}") from error
        for name in before_names:
            path = directory / name
            item_relative = relative / name
            value = item_relative.as_posix()
            try:
                metadata = path.lstat()
            except OSError as error:
                raise PreflightFailure(
                    f"cannot inspect {label} entry {value}: {error}"
                ) from error
            if stat.S_ISDIR(metadata.st_mode):
                records.append({
                    "path": value,
                    "kind": "directory",
                    "mode": stat.S_IMODE(metadata.st_mode),
                })
                walk(path, item_relative)
            elif stat.S_ISREG(metadata.st_mode):
                identity = stable_file_record(path, f"{label} entry {value}")
                records.append({"path": value, "kind": "regular", **identity})
                total_bytes += identity["bytes"]
            elif stat.S_ISLNK(metadata.st_mode):
                resolved = path.resolve(strict=True)
                require(resolved.is_relative_to(containment),
                        f"{label} symlink escapes containment: {value}")
                normalized_target = (
                    "<containment-root>/" +
                    resolved.relative_to(containment).as_posix()
                )
                identity = file_identity(path, f"{label} symlink target {value}")
                after = path.lstat()
                require(_stable_stat(metadata) == _stable_stat(after),
                        f"{label} symlink changed while inspected: {value}")
                records.append({
                    "path": value,
                    "kind": "symlink-to-regular",
                    "mode": stat.S_IMODE(after.st_mode),
                    "target_policy": "resolved-within-containment-root-v1",
                    "normalized_target": normalized_target,
                    "target_identity": identity,
                })
                total_bytes += identity["bytes"]
            else:
                raise PreflightFailure(f"unsupported {label} entry type: {value}")
        after_names = sorted(entry.name for entry in os.scandir(directory))
        require(before_names == after_names,
                f"{label} directory changed while inspected: {directory}")

    walk(root, PurePosixPath("."))
    return {
        "entry_count": len(records),
        "total_regular_and_target_bytes": total_bytes,
        "ordered_inventory_sha256": compact_sha256(records),
        "policy": "exact-recursive-content-and-symlink-target-binding-v1",
    }


def authenticate_git_root(
    root: Path, expected: str, label: str, *, require_no_ignored: bool,
) -> dict[str, Any]:
    require(COMMIT_RE.fullmatch(expected) is not None,
            f"malformed expected {label} commit: {expected!r}")
    top_level = run([
        str(GIT), "-C", str(root), "rev-parse", "--show-toplevel",
    ]).stdout.strip()
    require(Path(top_level).resolve(strict=True) == root and top_level == str(root),
            f"{label} root is not the exact Git top level: {root}")
    actual = run([str(GIT), "-C", str(root), "rev-parse", "HEAD"]).stdout.strip()
    require(actual == expected,
            f"{label} commit mismatch: expected {expected}, found {actual}")
    status_result = run([
        str(GIT), "-C", str(root), "status", "--porcelain=v1",
        "--untracked-files=all",
    ])
    require(status_result.stdout == "", f"{label} worktree is not clean")
    if require_no_ignored:
        ignored = ignored_artifact_inventory(root, label, require_empty=True)
        shape = tracked_worktree_shape(root, label)
    else:
        ignored = {
            "policy": "explicit-toolchain-closure-only-v1",
            "global_ignored_scan_enforced": False,
        }
        shape = {"policy": "not-enforced; consumers require isolated access-v1"}
    return {
        "commit": actual,
        "ignored_artifacts": ignored,
        "worktree_shape": shape,
        "worktree_policy": "tracked-and-untracked-clean-git-toplevel-v1",
    }


def parse_ldd(stdout: str) -> list[tuple[str, Path]]:
    """Return the named, resolved file closure from controlled GNU ldd output."""
    entries: list[tuple[str, Path]] = []
    seen: set[tuple[str, str]] = set()
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if LDD_VDSO_RE.fullmatch(line):
            continue
        require("=> not found" not in line, f"unresolved ldd dependency: {line}")
        named = LDD_NAMED_RE.fullmatch(line)
        direct = LDD_DIRECT_RE.fullmatch(line)
        if named is not None:
            name, path_text = named.group(1), named.group(2)
        elif direct is not None:
            path_text = direct.group(1)
            name = Path(path_text).name
        else:
            raise PreflightFailure(f"unrecognized ldd output: {line}")
        route = (name, str(Path(path_text)))
        require(route not in seen, f"duplicate ldd route: {line}")
        seen.add(route)
        entries.append((name, Path(path_text)))
    require(entries, "ldd returned no file-backed dependencies")
    return entries


def dynamic_closure(
    binary: Path, label: str, *, allow_no_dependencies: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    completed = run([str(LDD), str(binary)])
    require(completed.stderr == "", f"ldd wrote to stderr for {label}")
    if allow_no_dependencies and completed.stdout == "statically linked\n":
        parsed: list[tuple[str, Path]] = []
    else:
        parsed = parse_ldd(completed.stdout)
    identity_entries = []
    local_entries = []
    for index, (name, path) in enumerate(parsed):
        item_label = f"{label} dynamic dependency {index} ({name})"
        identity_entries.append({
            "name": name,
            "file": file_identity(path, item_label),
        })
        local_entries.append({
            "name": name,
            **local_file_route(path, item_label),
        })
    normalized_output = ADDRESS_RE.sub("<address>", completed.stdout)
    return (
        {
            "dependencies": identity_entries,
            "normalized_stdout_sha256": hashlib.sha256(
                normalized_output.encode("utf-8")
            ).hexdigest(),
        },
        {"dependencies": local_entries},
    )


def require_isolated_runtime() -> None:
    require(sys.flags.isolated == 1, "Python isolated mode (-I) is required")
    require(sys.flags.no_site == 1, "Python no-site mode (-S) is required")
    require(sys.flags.ignore_environment == 1,
            "Python environment isolation is required")
    require(sys.flags.safe_path, "Python safe-path mode is required")
    require(Path(sys.executable).resolve(strict=True) == PYTHON,
            "unexpected Python executable")
    require(sys.path == EXPECTED_ISOLATED_SYS_PATH,
            f"unexpected isolated Python search path: {sys.path!r}")


def python_module_inventory() -> dict[str, Any]:
    stdlib_root = canonical_directory(Path("/usr/lib"), "Python stdlib root")
    records = []
    extension_closures = []
    for name, module in sorted(sys.modules.items()):
        path_value = getattr(module, "__file__", None)
        if path_value is None or name == "__main__":
            continue
        path = Path(path_value).resolve(strict=True)
        require(path.is_relative_to(stdlib_root),
                f"Python module is outside the system stdlib: {name}:{path}")
        relative = path.relative_to(stdlib_root).as_posix()
        records.append({
            "module": name,
            "path": relative,
            "file": file_identity(path, f"Python module {name}"),
        })
        if path.suffix == ".so":
            closure, _local = dynamic_closure(
                path, f"Python extension {name}", allow_no_dependencies=True,
            )
            extension_closures.append({"module": name, "closure": closure})
    require(records, "no file-backed Python modules were authenticated")
    return {
        "file_backed_module_count": len(records),
        "ordered_module_inventory_sha256": compact_sha256(records),
        "extension_dynamic_closures": extension_closures,
        "flags": {
            "ignore_environment": sys.flags.ignore_environment,
            "isolated": sys.flags.isolated,
            "no_site": sys.flags.no_site,
            "safe_path": sys.flags.safe_path,
        },
        "sys_path": list(sys.path),
    }


def validate_target(value: str) -> str:
    require(TARGET_RE.fullmatch(value) is not None,
            f"malformed Holmake target: {value!r}")
    pure = PurePosixPath(value)
    require(not pure.is_absolute() and ".." not in pure.parts,
            f"unsafe Holmake target: {value!r}")
    return value


def validate_target_directory(root: Path, value: str) -> str:
    require(value != "", "empty target directory")
    pure = PurePosixPath(value)
    require(not pure.is_absolute() and ".." not in pure.parts,
            f"unsafe target directory: {value!r}")
    candidate = root.joinpath(*pure.parts)
    canonical_directory(candidate, "CakeML target directory")
    return pure.as_posix()


def validate_arguments(arguments: argparse.Namespace) -> None:
    require(type(arguments.jobs) is int and arguments.jobs in (1, 2),
            "jobs must be exactly integer 1 or 2")
    require(type(arguments.mt) is int and arguments.mt == 1,
            "mt must be exactly integer 1")
    require(
        type(arguments.cache_mode) is str
        and arguments.cache_mode in ("cache-dir-mtime", "use-cache-cachekey"),
        "unsupported cache mode",
    )
    require(type(arguments.target) is str, "target is not a string")
    require(type(arguments.target_directory) is str,
            "target directory is not a string")
    require(arguments.target == V1_TARGET,
            f"v1 preflight only supports target {V1_TARGET}")
    require(arguments.target_directory == V1_TARGET_DIRECTORY,
            f"v1 preflight only supports directory {V1_TARGET_DIRECTORY}")


def _snapshot(arguments: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    require_isolated_runtime()
    validate_arguments(arguments)
    project_root = canonical_directory(arguments.project_root, "project root")
    hol4_root = canonical_directory(arguments.hol4_root, "HOL4 root")
    cakeml_root = canonical_directory(arguments.cakeml_root, "CakeML root")
    project = authenticate_git_root(
        project_root, arguments.expected_project_head, "project",
        require_no_ignored=False,
    )
    require(
        PROGRAM == project_root / "scripts/describe-hol-cache-namespace.py",
        "preflight program is not the authenticated project copy",
    )
    cakeml = authenticate_git_root(
        cakeml_root, arguments.expected_cakeml_head, "CakeML",
        require_no_ignored=True,
    )
    hol4 = authenticate_git_root(
        hol4_root, arguments.expected_hol4_head, "HOL4",
        require_no_ignored=False,
    )

    holmake_path = hol4_root / "bin/Holmake"
    hol_path = hol4_root / "bin/hol"
    fixed_files = {
        "Holmake": file_identity(holmake_path, "Holmake", executable=True),
        "hol": file_identity(hol_path, "hol", executable=True),
        "hol.state": file_identity(hol4_root / "bin/hol.state", "hol.state"),
        "kernelidstr": file_identity(hol4_root / ".kernelidstr", "kernel ID"),
    }
    sigobj_inventory = toolchain_tree_inventory(
        hol4_root / "sigobj", hol4_root, "HOL4 sigobj",
    )
    holmake_closure, holmake_local = dynamic_closure(holmake_path, "Holmake")
    hol_closure, hol_local = dynamic_closure(hol_path, "hol")
    cp_closure, cp_local = dynamic_closure(CP, "cache copy command")
    sh_closure, sh_local = dynamic_closure(SH, "command shell")
    poly_closure, poly_local = dynamic_closure(POLY, "Poly/ML")
    bash_closure, bash_local = dynamic_closure(BASH, "Bash")
    git_closure, git_local = dynamic_closure(GIT, "git")
    python_closure, python_local = dynamic_closure(PYTHON, "Python")
    poly_version = run([str(POLY), "--version"])
    require(poly_version.stderr == "", "Poly/ML --version wrote to stderr")
    require(poly_version.stdout.endswith("\n") and poly_version.stdout.strip(),
            "malformed Poly/ML version output")

    uname = os.uname()
    namespace = {
        "schema": NAMESPACE_SCHEMA,
        "policy": POLICY,
        "build": {
            "cache_mode": arguments.cache_mode,
            "jobs": arguments.jobs,
            "mt": arguments.mt,
            "target": validate_target(arguments.target),
            "target_directory": validate_target_directory(
                cakeml_root, arguments.target_directory,
            ),
        },
        "cakeml": cakeml,
        "project": project,
        "environment": {
            **CONTROLLED_ENVIRONMENT,
            "CAKEMLDIR": "<exact-clean-cakeml-root>",
            "HOLDIR": "<exact-clean-hol4-root>",
        },
        "hol4": {
            **hol4,
            "files": fixed_files,
            "sigobj_inventory": sigobj_inventory,
        },
        "host": {
            "byteorder": sys.byteorder,
            "machine": platform.machine(),
            "release": platform.release(),
            "system": platform.system(),
            "uname_version": uname.version,
        },
        "toolchain": {
            "cache_copy": file_identity(CP, "cache copy command", executable=True),
            "cache_copy_dynamic_closure": cp_closure,
            "command_shell": file_identity(SH, "command shell", executable=True),
            "command_shell_dynamic_closure": sh_closure,
            "ldd_interpreter_bash": file_identity(BASH, "Bash", executable=True),
            "ldd_interpreter_bash_dynamic_closure": bash_closure,
            "git": file_identity(GIT, "git", executable=True),
            "git_dynamic_closure": git_closure,
            "ld_cache": file_identity(LD_CACHE, "dynamic loader cache"),
            "ldd": file_identity(LDD, "ldd", executable=True),
            "poly": {
                "dynamic_closure": poly_closure,
                "executable": file_identity(POLY, "Poly/ML", executable=True),
                "version_stdout": poly_version.stdout,
                "version_stdout_sha256": hashlib.sha256(
                    poly_version.stdout.encode("utf-8")
                ).hexdigest(),
            },
            "preflight_program": file_identity(PROGRAM, "preflight program"),
            "python": {
                "dynamic_closure": python_closure,
                "executable": file_identity(PYTHON, "Python", executable=True),
                "module_inventory": python_module_inventory(),
                "version": platform.python_version(),
            },
            "Holmake_dynamic_closure": holmake_closure,
            "hol_dynamic_closure": hol_closure,
        },
    }
    local_paths = {
        "cakeml_root": str(cakeml_root),
        "hol4_root": str(hol4_root),
        "hol4_sigobj": str(hol4_root / "sigobj"),
        "project_root": str(project_root),
        "files": {
            "Holmake": local_file_route(holmake_path, "Holmake", executable=True),
            "cache_copy": local_file_route(CP, "cache copy command", executable=True),
            "command_shell": local_file_route(SH, "command shell", executable=True),
            "hol": local_file_route(hol_path, "hol", executable=True),
            "hol.state": local_file_route(hol4_root / "bin/hol.state", "hol.state"),
            "kernelidstr": local_file_route(hol4_root / ".kernelidstr", "kernel ID"),
            "git": local_file_route(GIT, "git", executable=True),
            "ldd_interpreter_bash": local_file_route(BASH, "Bash", executable=True),
            "ld_cache": local_file_route(LD_CACHE, "dynamic loader cache"),
            "ldd": local_file_route(LDD, "ldd", executable=True),
            "poly": local_file_route(POLY, "Poly/ML", executable=True),
            "preflight_program": local_file_route(PROGRAM, "preflight program"),
            "python": local_file_route(PYTHON, "Python", executable=True),
        },
        "Holmake_dynamic_closure": holmake_local,
        "cache_copy_dynamic_closure": cp_local,
        "command_shell_dynamic_closure": sh_local,
        "hol_dynamic_closure": hol_local,
        "poly_dynamic_closure": poly_local,
        "ldd_interpreter_bash_dynamic_closure": bash_local,
        "git_dynamic_closure": git_local,
        "python_dynamic_closure": python_local,
    }
    return namespace, local_paths


def build_receipt(arguments: argparse.Namespace) -> dict[str, Any]:
    first_namespace, first_local_paths = _snapshot(arguments)
    namespace, local_paths = _snapshot(arguments)
    require(first_namespace == namespace,
            "namespace inputs changed between preflight snapshots")
    require(first_local_paths == local_paths,
            "local routes changed between preflight snapshots")
    namespace_digest = compact_sha256(namespace)
    return {
        "schema": SCHEMA,
        "kind": "candle-hol4-native-cache-preflight",
        "namespace": namespace,
        "namespace_digest_encoding": "sorted-compact-ascii-json-sha256-v1",
        "namespace_sha256": namespace_digest,
        "recommended_cache_directory_name": namespace_digest,
        "local_paths": local_paths,
        "limitations": [
            "preflight only: no Holmake invocation and no cache creation",
            "development acceleration only: never release evidence",
            "does not harden native manifest names, URLs, content, or commits",
            "native cache hits still require HOL parent-hash validation",
            "a benchmark controller must revalidate this receipt before and after Holmake",
            "target-specific external-command completeness still requires baseline tracing",
        ],
    }


def parse_arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--expected-project-head", required=True)
    parser.add_argument("--hol4-root", required=True, type=Path)
    parser.add_argument("--expected-hol4-head", required=True)
    parser.add_argument("--cakeml-root", required=True, type=Path)
    parser.add_argument("--expected-cakeml-head", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--target-directory", required=True)
    parser.add_argument("--jobs", required=True, type=int, choices=(1, 2))
    parser.add_argument("--mt", required=True, type=int, choices=(1,))
    parser.add_argument(
        "--cache-mode", required=True,
        choices=("cache-dir-mtime", "use-cache-cachekey"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        receipt = build_receipt(parse_arguments(sys.argv[1:] if argv is None else argv))
    except (PreflightFailure, OSError, subprocess.SubprocessError) as error:
        print(f"cache namespace preflight failed: {error}", file=sys.stderr)
        return 1
    sys.stdout.buffer.write(canonical_json(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
