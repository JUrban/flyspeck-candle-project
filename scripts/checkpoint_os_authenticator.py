#!/usr/bin/python3
"""Live, fail-closed OS-observation companion for direct checkpoint attempts.

This module is intentionally not a release finalizer.  It observes files and
processes through kernel interfaces while they are live, and emits only an
unapproved controller-asserted candidate.  The available observations do not
close the kernel/runtime trust boundary.  This module never authenticates the
candidate and never sets runtime qualification, S2/S3 approval, or promotion.

Stable file identity/content remains revalidatable after process exit.
Process liveness, parent-owned exit/reap, READY ordering, no-replace rename,
and restart-time rehash are historical facts and are accepted only when this
object observed them live.  Retrospective controller JSON is not a substitute.
"""

from __future__ import annotations

import copy
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import signal
import stat
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable


class AuthenticationError(ValueError):
    """An OS observation did not satisfy the predeclared contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuthenticationError(message)


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ) + "\n").encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def direct_ordered_manifest_sha256(value: object) -> str:
    data = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def protocol_content_record(value: object) -> dict[str, Any]:
    """Match the direct protocol's indented canonical content records."""
    data = (json.dumps(
        value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False,
    ) + "\n").encode("utf-8")
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "md5": hashlib.md5(data, usedforsecurity=False).hexdigest(),
    }


HEX32 = re.compile(r"[0-9a-f]{32}")
HEX64 = re.compile(r"[0-9a-f]{64}")
UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
PFT_NAMESPACE = re.compile(r"(?:^|[/:._-])pft(?:$|[/:._-])", re.IGNORECASE)

DMTCP_VERSION = "4.1.0"
DMTCP_AUTHORITY_KIND = "candle-flyspeck-dmtcp-authority-v1"
DMTCP_ENVIRONMENT_POLICY = (
    "clean-runtime-plus-exact-dmtcp-and-injected-library-environment-v1"
)
DMTCP_ALLOWED_ENVIRONMENT_NAMES = (
    "CML_HEAP_SIZE", "CML_STACK_SIZE", "DMTCP_CHECKPOINT_DIR",
    "DMTCP_COORD_PORT", "DMTCP_GZIP", "DMTCP_QUIET", "LC_ALL",
    "LD_PRELOAD", "PATH",
)
DMTCP_FORBIDDEN_ENVIRONMENT_NAMES = (
    "BASH_ENV", "ENV", "GLIBC_TUNABLES", "LD_AUDIT", "LD_LIBRARY_PATH",
)
EXCEPTIONAL_MEMORY_CEILING_BYTES = 120 * 1024**3
EXCEPTIONAL_MEMORY_CEILING_KIB = 120 * 1024**2
CHECKPOINT_IMAGE_CEILING_BYTES = 120 * 1024**3
CHECKPOINT_DISK_CEILING_BYTES = 240 * 1024**3
DMTCP_ROLES = ("command", "coordinator", "launch", "restart")
DMTCP_ROLE_PATHS = {
    role: f"/usr/local/bin/dmtcp_{role}" for role in DMTCP_ROLES
}
PHASES = ("pilot", "origin", "checkpoint", "clean-1", "clean-2", "resume")
CONTROLLER_ASSERTION_SCOPE = (
    "controller-asserted-unapproved-without-anchored-os-revalidation-v1"
)
EVIDENCE_KIND = "candle-flyspeck-checkpoint-os-observation-candidate-v1"
CHALLENGE_KIND = "candle-flyspeck-checkpoint-controller-challenges-v1"
CHALLENGE_POLICY = "externally-predeclared-distinct-nonces-and-tokens-v1"
UNCLOSED_TRUST_BOUNDARIES = (
    "continuous-tracefork-vfork-clone-exec-exit-or-cgroup-subreaper-membership",
    "kernel-bound-ack-channel",
    "complete-process-tree-and-time-ordering",
    "mount-and-proc-namespace-plus-fstatfs-anchor",
    "coordinator-port-time-ownership-and-reuseport-exclusion",
    "elf-pt-interp-rpath-runpath-ld-cache-and-mapped-plugin-inode-closure",
    "writable-files-and-inherited-or-open-fd-races",
    "pgid-sampling-of-exited-setsid-and-transient-work-plus-complete-retained-files",
    "resumed-controller-exec-gate-continuity",
    "independently-predeclared-coordinator-and-restart-argv",
    "immutable-held-fd-or-bind-mount-restart-without-pathname-toctou",
    "restart-working-directory-binding-for-relative-direct-protocol-paths",
)

_OBSERVATION_SEAL = object()


def _hex(value: object, pattern: re.Pattern[str], label: str) -> str:
    require(isinstance(value, str) and pattern.fullmatch(value) is not None,
            f"malformed {label}")
    return value


def _safe_relative(value: object, label: str) -> str:
    require(isinstance(value, str) and value and "\\" not in value and
            not value.startswith("/") and all(
                ord(character) >= 32 and character != "\x7f"
                for character in value
            ), f"malformed {label}")
    path = PurePosixPath(value)
    require(path.as_posix() == value and all(
        part not in {"", ".", ".."} for part in path.parts
    ), f"unsafe {label}")
    require(PFT_NAMESPACE.search(value) is None,
            f"PFT namespace is forbidden in {label}")
    return value


def _absolute_to_relative(value: object, label: str) -> str:
    require(isinstance(value, str) and value.startswith("/") and
            "\\" not in value and all(
                ord(character) >= 32 and character != "\x7f"
                for character in value
            ), f"malformed {label}")
    path = PurePosixPath(value)
    require(path.as_posix() == value and all(
        part not in {"", ".", ".."} for part in path.parts[1:]
    ), f"unsafe {label}")
    require(PFT_NAMESPACE.search(value) is None,
            f"PFT namespace is forbidden in {label}")
    return "/".join(path.parts[1:])


def validate_controller_challenges(value: object) -> dict[str, Any]:
    fields = {
        "schema", "kind", "policy", "challenge_id",
        "diagnostic_pilot_nonce", "origin_attempt_nonce", "checkpoint_token",
        "resume_nonce", "resume_token", "clean_attempt_nonces",
        "authenticated_plan", "diagnostic_pilot", "dmtcp_authority",
        "resource_limits", "runtime_environment", "checkpoint_environment",
        "pft_used",
    }
    require(isinstance(value, dict) and set(value) == fields and
            type(value.get("schema")) is int and value["schema"] == 1 and
            value.get("kind") == CHALLENGE_KIND and
            value.get("policy") == CHALLENGE_POLICY and
            value.get("pft_used") is False,
            "malformed external checkpoint challenges")
    _hex(value.get("challenge_id"), HEX64, "challenge ID")
    nonces = [
        _hex(value.get(name), HEX32, name) for name in (
            "diagnostic_pilot_nonce", "origin_attempt_nonce", "resume_nonce",
        )
    ]
    clean = value.get("clean_attempt_nonces")
    require(isinstance(clean, list) and len(clean) == 2,
            "checkpoint challenges need two clean nonces")
    nonces.extend(_hex(item, HEX32, "clean attempt nonce") for item in clean)
    tokens = [
        _hex(value.get(name), HEX64, name)
        for name in ("checkpoint_token", "resume_token")
    ]
    require(len(set(nonces)) == 5 and
            len(set(tokens + [value["challenge_id"]])) == 3,
            "checkpoint challenges reuse a nonce or token")
    for name in (
        "authenticated_plan", "diagnostic_pilot", "dmtcp_authority",
        "resource_limits", "runtime_environment", "checkpoint_environment",
    ):
        record = value.get(name)
        require(isinstance(record, dict) and set(record) == {
            "bytes", "sha256", "md5",
        } and type(record.get("bytes")) is int and record["bytes"] > 0,
                f"malformed challenged {name} record")
        _hex(record.get("sha256"), HEX64, f"challenged {name} SHA-256")
        _hex(record.get("md5"), HEX32, f"challenged {name} MD5")
    return value


def phase_challenge(challenges: dict[str, Any], phase: str) -> tuple[str, str]:
    require(phase in PHASES, "unknown checkpoint OS phase")
    if phase == "pilot":
        return "diagnostic_pilot_nonce", challenges["diagnostic_pilot_nonce"]
    if phase == "origin":
        return "origin_attempt_nonce", challenges["origin_attempt_nonce"]
    if phase == "checkpoint":
        return "checkpoint_token", challenges["checkpoint_token"]
    if phase == "clean-1":
        return "clean_attempt_nonce", challenges["clean_attempt_nonces"][0]
    if phase == "clean-2":
        return "clean_attempt_nonce", challenges["clean_attempt_nonces"][1]
    return "resume_nonce", challenges["resume_nonce"]


def _stat_identity(item: os.stat_result) -> tuple[int, ...]:
    return (
        item.st_mode, item.st_uid, item.st_gid, item.st_nlink,
        item.st_dev, item.st_ino, item.st_size,
        item.st_mtime_ns, item.st_ctime_ns,
    )


class AnchoredFilesystem:
    """An O_NOFOLLOW directory anchor with fd-only content reads."""

    def __init__(self, root: str | os.PathLike[str]):
        self.root_path = os.fspath(root)
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            self.root_fd = os.open(self.root_path, flags)
        except OSError as error:
            raise AuthenticationError(f"cannot anchor directory: {root}") from error
        root_stat = os.fstat(self.root_fd)
        require(stat.S_ISDIR(root_stat.st_mode), "anchor is not a directory")

    def close(self) -> None:
        if self.root_fd >= 0:
            os.close(self.root_fd)
            self.root_fd = -1

    def __enter__(self) -> "AnchoredFilesystem":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _open_parent(self, relative: str) -> tuple[int, str]:
        relative = _safe_relative(relative, "anchored path")
        parts = PurePosixPath(relative).parts
        current = os.dup(self.root_fd)
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            for part in parts[:-1]:
                try:
                    next_fd = os.open(part, flags, dir_fd=current)
                except OSError as error:
                    raise AuthenticationError(
                        "cannot traverse anchored path without following links"
                    ) from error
                before = os.fstat(next_fd)
                require(stat.S_ISDIR(before.st_mode),
                        "anchored path component is not a directory")
                os.close(current)
                current = next_fd
            return current, parts[-1]
        except Exception:
            os.close(current)
            raise

    def open_directory(self, relative: str) -> int:
        parent, name = self._open_parent(relative)
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            try:
                result = os.open(name, flags, dir_fd=parent)
            except OSError as error:
                raise AuthenticationError(
                    "cannot open anchored directory without following links"
                ) from error
        finally:
            os.close(parent)
        require(stat.S_ISDIR(os.fstat(result).st_mode),
                "anchored directory is not a directory")
        return result

    def authenticate_file(
        self, relative: str, expected: dict[str, Any], *, immutable: bool,
        after_read_hook: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        """Hash one regular file from its fd and reject identity races."""
        relative = _safe_relative(relative, "authenticated file path")
        required = {"bytes", "sha256", "md5", "mode", "uid", "gid"}
        require(isinstance(expected, dict) and set(expected) == required and
                type(expected.get("bytes")) is int and expected["bytes"] >= 0 and
                type(expected.get("uid")) is int and expected["uid"] >= 0 and
                type(expected.get("gid")) is int and expected["gid"] >= 0 and
                isinstance(expected.get("mode"), str) and
                re.fullmatch(r"0[0-7]{3}", expected["mode"]) is not None,
                "malformed expected file authority")
        _hex(expected.get("sha256"), HEX64, "expected file SHA-256")
        _hex(expected.get("md5"), HEX32, "expected file MD5")
        parent, name = self._open_parent(relative)
        flags = os.O_RDONLY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(name, flags, dir_fd=parent)
            try:
                before = os.fstat(fd)
                require(stat.S_ISREG(before.st_mode),
                        "authenticated path is not a regular file")
                sha256 = hashlib.sha256()
                md5 = hashlib.md5(usedforsecurity=False)
                size = 0
                while True:
                    chunk = os.read(fd, 1024 * 1024)
                    if not chunk:
                        break
                    sha256.update(chunk)
                    md5.update(chunk)
                    size += len(chunk)
                if after_read_hook is not None:
                    after_read_hook()
                after = os.fstat(fd)
                path_after = os.stat(name, dir_fd=parent, follow_symlinks=False)
                require(_stat_identity(before) == _stat_identity(after) and
                        before.st_dev == path_after.st_dev and
                        before.st_ino == path_after.st_ino,
                        "authenticated file changed or was replaced while read")
            finally:
                os.close(fd)
        except OSError as error:
            raise AuthenticationError(
                f"cannot authenticate file without following links: {relative}"
            ) from error
        finally:
            os.close(parent)
        observed = {
            "path": relative,
            "bytes": size,
            "sha256": sha256.hexdigest(),
            "md5": md5.hexdigest(),
            "mode": f"0{stat.S_IMODE(before.st_mode):03o}",
            "uid": before.st_uid,
            "gid": before.st_gid,
            "nlink": before.st_nlink,
            "device": before.st_dev,
            "inode": before.st_ino,
            "mtime_ns": before.st_mtime_ns,
            "ctime_ns": before.st_ctime_ns,
        }
        for field in required:
            require(observed[field] == expected[field],
                    f"authenticated file differs from expected {field}: {relative}")
        require(not immutable or (
            observed["mode"] == "0444" and observed["nlink"] == 1
        ), f"authenticated raw file is not immutable and unaliased: {relative}")
        return observed

    def exact_tree(self, directory: str) -> list[str]:
        """List only regular files under one nofollow directory tree."""
        top_fd = self.open_directory(directory)
        result: list[str] = []

        def walk(fd: int, prefix: str) -> None:
            for name in sorted(os.listdir(fd)):
                require(name not in {".", ".."} and "/" not in name,
                        "malformed directory entry")
                item = os.stat(name, dir_fd=fd, follow_symlinks=False)
                path = f"{prefix}/{name}" if prefix else name
                if stat.S_ISDIR(item.st_mode):
                    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
                    if hasattr(os, "O_NOFOLLOW"):
                        flags |= os.O_NOFOLLOW
                    child = os.open(name, flags, dir_fd=fd)
                    try:
                        walk(child, path)
                    finally:
                        os.close(child)
                else:
                    require(stat.S_ISREG(item.st_mode),
                            "checkpoint tree contains a link or special file")
                    result.append(path)

        try:
            walk(top_fd, "")
        finally:
            os.close(top_fd)
        return result


def file_expectation(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Diagnostic helper for predeclaring a local file in tests/setup."""
    path = os.fspath(path)
    item = os.stat(path, follow_symlinks=False)
    require(stat.S_ISREG(item.st_mode), "authority snapshot path is not regular")
    sha256 = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    with open(path, "rb", buffering=0) as stream:
        while chunk := stream.read(1024 * 1024):
            sha256.update(chunk)
            md5.update(chunk)
    return {
        "bytes": item.st_size,
        "sha256": sha256.hexdigest(),
        "md5": md5.hexdigest(),
        "mode": f"0{stat.S_IMODE(item.st_mode):03o}",
        "uid": item.st_uid,
        "gid": item.st_gid,
    }


@dataclass(frozen=True)
class _Observation:
    kind: str
    evidence: dict[str, Any]
    nonfixture: bool
    _seal: object


def _make_observation(kind: str, evidence: dict[str, Any], nonfixture: bool) -> _Observation:
    return _Observation(kind, copy.deepcopy(evidence), nonfixture, _OBSERVATION_SEAL)


def _require_observation(value: object, kind: str, *, nonfixture: bool = True) -> _Observation:
    require(isinstance(value, _Observation) and value._seal is _OBSERVATION_SEAL and
            value.kind == kind and (not nonfixture or value.nonfixture),
            f"missing sealed nonfixture {kind} observation")
    return value


def _readelf_needed_from_fd(
    fd: int, runner: Callable[[int], str] | None,
) -> list[str]:
    if runner is not None:
        output = runner(fd)
    else:
        try:
            completed = subprocess.run(
                ["/usr/bin/readelf", "-d", f"/proc/self/fd/{fd}"],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, check=True, timeout=10,
                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
                pass_fds=(fd,),
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise AuthenticationError("cannot inspect authenticated ELF") from error
        output = completed.stdout
    needed = re.findall(r"Shared library: \[([^\]]+)\]", output)
    require(len(needed) == len(set(needed)), "ELF repeats a needed library")
    return needed


def _authenticate_elf_file(
    filesystem: AnchoredFilesystem, absolute_path: str,
    expected: dict[str, Any], readelf_runner: Callable[[int], str] | None,
) -> tuple[dict[str, Any], list[str]]:
    relative = _absolute_to_relative(absolute_path, "ELF authority path")
    evidence = filesystem.authenticate_file(relative, expected, immutable=False)
    evidence["path"] = absolute_path
    parent, name = filesystem._open_parent(relative)
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(name, flags, dir_fd=parent)
        before = os.fstat(fd)
        require(before.st_dev == evidence["device"] and
                before.st_ino == evidence["inode"],
                "ELF was replaced between content and dependency inspection")
        needed = _readelf_needed_from_fd(fd, readelf_runner)
        after = os.fstat(fd)
        require(_stat_identity(before) == _stat_identity(after),
                "ELF changed during dependency inspection")
    finally:
        if "fd" in locals():
            os.close(fd)
        os.close(parent)
    return evidence, needed


def authenticate_dmtcp_authority(
    expected: object, *, filesystem_root: str = "/",
    version_runner: Callable[[str], str] | None = None,
    readelf_runner: Callable[[int], str] | None = None,
) -> _Observation:
    """Authenticate exact DMTCP binaries, plugins, and their ELF closure."""
    fields = {"version", "executables", "injected_libraries", "elf_closure"}
    require(isinstance(expected, dict) and set(expected) == fields and
            expected.get("version") == DMTCP_VERSION,
            "malformed expected DMTCP OS authority")
    executables = expected.get("executables")
    require(isinstance(executables, list) and
            [item.get("role") if isinstance(item, dict) else None
             for item in executables] == list(DMTCP_ROLES),
            "DMTCP authority does not have the exact role order")
    libraries = expected.get("injected_libraries")
    closure = expected.get("elf_closure")
    require(isinstance(libraries, list) and libraries and
            isinstance(closure, list), "DMTCP library authority is incomplete")
    expected_library_paths = [
        item.get("path") if isinstance(item, dict) else None for item in libraries
    ]
    require(expected_library_paths == sorted(expected_library_paths) and
            len(set(expected_library_paths)) == len(expected_library_paths) and
            all(isinstance(path, str) and
                path.startswith("/usr/local/lib/dmtcp/") and path.endswith(".so")
                for path in expected_library_paths),
            "DMTCP injected-library set is not exact and canonical")
    closure_sonames = [
        item.get("soname") if isinstance(item, dict) else None for item in closure
    ]
    require(closure_sonames == sorted(closure_sonames) and
            len(set(closure_sonames)) == len(closure_sonames),
            "DMTCP ELF closure is not canonical")
    closure_by_soname = {
        item["soname"]: item for item in closure if isinstance(item, dict)
    }
    observations: list[dict[str, Any]] = []
    needed_by_path: dict[str, list[str]] = {}
    versions: dict[str, str] = {}
    identities: set[tuple[int, int]] = set()
    with AnchoredFilesystem(filesystem_root) as filesystem:
        for item in executables:
            require(isinstance(item, dict) and set(item) == {
                "role", "path", "authority",
            } and item["path"] == DMTCP_ROLE_PATHS[item["role"]],
                    "DMTCP executable path is not the trusted /usr/local role")
            observed, needed = _authenticate_elf_file(
                filesystem, item["path"], item["authority"], readelf_runner,
            )
            identity = (observed["device"], observed["inode"])
            require(identity not in identities, "DMTCP executable aliases another role")
            identities.add(identity)
            needed_by_path[item["path"]] = needed
            observations.append({"role": item["role"], **observed})
            if version_runner is None:
                versions[item["role"]] = _run_authenticated_dmtcp_version(
                    filesystem, item["path"], observed, item["role"],
                )
        for item in libraries:
            require(isinstance(item, dict) and set(item) == {
                "path", "authority",
            }, "malformed DMTCP injected-library authority")
            observed, needed = _authenticate_elf_file(
                filesystem, item["path"], item["authority"], readelf_runner,
            )
            identity = (observed["device"], observed["inode"])
            require(identity not in identities, "DMTCP library aliases another file")
            identities.add(identity)
            needed_by_path[item["path"]] = needed
            observations.append({"injected": True, **observed})
        for soname, item in closure_by_soname.items():
            require(set(item) == {"soname", "path", "authority"} and
                    isinstance(soname, str) and soname and "/" not in soname and
                    PFT_NAMESPACE.search(soname) is None and
                    isinstance(item["path"], str) and item["path"].startswith("/"),
                    "malformed DMTCP ELF-closure entry")
            observed, needed = _authenticate_elf_file(
                filesystem, item["path"], item["authority"], readelf_runner,
            )
            identity = (observed["device"], observed["inode"])
            require(identity not in identities, "DMTCP closure contains an alias")
            identities.add(identity)
            needed_by_path[item["path"]] = needed
            observations.append({"soname": soname, **observed})
    allowed_sonames = set(closure_by_soname)
    injected_sonames = {PurePosixPath(path).name for path in expected_library_paths}
    required_sonames = {
        soname for needed in needed_by_path.values() for soname in needed
    }
    require(required_sonames <= allowed_sonames | injected_sonames,
            "DMTCP ELF closure omits a needed library")
    reachable = set(required_sonames) & allowed_sonames
    pending = list(reachable)
    while pending:
        soname = pending.pop()
        for dependency in needed_by_path[closure_by_soname[soname]["path"]]:
            if dependency in allowed_sonames and dependency not in reachable:
                reachable.add(dependency)
                pending.append(dependency)
    require(reachable == allowed_sonames,
            "DMTCP ELF closure contains unreachable surplus libraries")
    if version_runner is not None:
        versions = {
            role: version_runner(DMTCP_ROLE_PATHS[role]) for role in DMTCP_ROLES
        }
    require(all(_parse_dmtcp_version(output) == DMTCP_VERSION
                for output in versions.values()),
            "DMTCP executable version differs from 4.1.0")
    return _make_observation("dmtcp-authority", {
        "version": DMTCP_VERSION,
        "executables": observations[:len(DMTCP_ROLES)],
        "injected_libraries": observations[
            len(DMTCP_ROLES):len(DMTCP_ROLES) + len(libraries)
        ],
        "elf_closure": observations[len(DMTCP_ROLES) + len(libraries):],
        "needed_by_path": needed_by_path,
        "version_output_sha256": {
            role: hashlib.sha256(versions[role].encode()).hexdigest()
            for role in DMTCP_ROLES
        },
    }, filesystem_root == "/" and version_runner is None and
       readelf_runner is None)


def _run_dmtcp_version(path: str) -> str:
    try:
        result = subprocess.run(
            [path, "--version"], stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, check=False, timeout=10,
            env={"PATH": "/usr/local/bin:/usr/bin:/bin", "LC_ALL": "C"},
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise AuthenticationError(f"cannot execute DMTCP version probe: {path}") from error
    expected_status = 1 if path == DMTCP_ROLE_PATHS["command"] else 0
    require(result.returncode == expected_status,
            f"DMTCP version probe has unexpected status: {path}")
    return result.stdout


def _run_authenticated_dmtcp_version(
    filesystem: AnchoredFilesystem, path: str, authority: dict[str, Any], role: str,
) -> str:
    relative = _absolute_to_relative(path, "DMTCP version path")
    parent, name = filesystem._open_parent(relative)
    flags = os.O_RDONLY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(name, flags, dir_fd=parent)
        item = os.fstat(fd)
        require(item.st_dev == authority["device"] and
                item.st_ino == authority["inode"],
                "DMTCP executable changed before fd-based version probe")
        try:
            result = subprocess.run(
                [f"/proc/self/fd/{fd}", "--version"],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, check=False, timeout=10,
                env={"PATH": "/usr/local/bin:/usr/bin:/bin", "LC_ALL": "C"},
                pass_fds=(fd,),
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise AuthenticationError(
                f"cannot execute authenticated DMTCP role: {role}"
            ) from error
        expected_status = 1 if role == "command" else 0
        require(result.returncode == expected_status and
                _stat_identity(item) == _stat_identity(os.fstat(fd)),
                f"authenticated DMTCP version probe failed: {role}")
        return result.stdout
    finally:
        if "fd" in locals():
            os.close(fd)
        os.close(parent)


def _parse_dmtcp_version(output: str) -> str:
    match = re.search(r"\(DMTCP\) ([0-9]+\.[0-9]+\.[0-9]+)", output)
    require(match is not None, "malformed DMTCP version output")
    return match.group(1)


def bind_dmtcp_controller_authority(
    *, os_authority: _Observation, kernel: _Observation,
    direct_authority: dict[str, Any], elf_closure_document: dict[str, Any],
    challenges: dict[str, Any],
) -> _Observation:
    """Bind live OS observations to the externally challenged direct authority."""
    observed = _require_observation(os_authority, "dmtcp-authority", nonfixture=False)
    kernel_observation = _require_observation(kernel, "kernel", nonfixture=False)
    challenges = validate_controller_challenges(copy.deepcopy(challenges))
    fields = {
        "schema", "kind", "version", "executables", "injected_libraries",
        "elf_closure", "kernel_trust", "environment_policy",
        "allowed_environment_names", "forbidden_environment_names", "pft_used",
    }
    require(isinstance(direct_authority, dict) and set(direct_authority) == fields and
            direct_authority.get("schema") == 1 and
            direct_authority.get("kind") == DMTCP_AUTHORITY_KIND and
            direct_authority.get("version") == DMTCP_VERSION and
            direct_authority.get("environment_policy") ==
            DMTCP_ENVIRONMENT_POLICY and
            direct_authority.get("allowed_environment_names") ==
            list(DMTCP_ALLOWED_ENVIRONMENT_NAMES) and
            direct_authority.get("forbidden_environment_names") ==
            list(DMTCP_FORBIDDEN_ENVIRONMENT_NAMES) and
            direct_authority.get("pft_used") is False and
            challenges["dmtcp_authority"] ==
            protocol_content_record(direct_authority),
            "direct DMTCP authority is not the externally challenged value")
    direct_executables = direct_authority.get("executables")
    direct_libraries = direct_authority.get("injected_libraries")
    require(isinstance(direct_executables, list) and
            isinstance(direct_libraries, list),
            "direct DMTCP file authority is malformed")

    def direct_file(item: object, *, role: bool) -> dict[str, Any]:
        expected_fields = ({"role", "path", "bytes", "sha256", "md5"}
                           if role else {"path", "bytes", "sha256", "md5"})
        require(isinstance(item, dict) and set(item) == expected_fields,
                "malformed challenged DMTCP file")
        return item

    observed_executables = observed.evidence["executables"]
    require(len(direct_executables) == len(observed_executables),
            "challenged DMTCP executable set differs from OS observation")
    for direct, live in zip(direct_executables, observed_executables, strict=True):
        direct = direct_file(direct, role=True)
        require(direct["role"] == live["role"] and
                direct["path"] == live["path"] and all(
                    direct[field] == live[field]
                    for field in ("bytes", "sha256", "md5")
                ), "challenged DMTCP executable differs from live fd")
    observed_libraries = observed.evidence["injected_libraries"]
    require(len(direct_libraries) == len(observed_libraries),
            "challenged injected-library set differs from OS observation")
    for direct, live in zip(direct_libraries, observed_libraries, strict=True):
        direct = direct_file(direct, role=False)
        require(direct["path"] == live["path"] and all(
                    direct[field] == live[field]
                    for field in ("bytes", "sha256", "md5")
                ), "challenged injected library differs from live fd")
    require(direct_authority["elf_closure"] ==
            protocol_content_record(elf_closure_document) and
            isinstance(elf_closure_document, dict) and
            set(elf_closure_document) == {"schema", "kind", "files"} and
            elf_closure_document.get("schema") == 1 and
            elf_closure_document.get("kind") ==
            "candle-flyspeck-dmtcp-elf-closure-v1",
            "raw ELF closure is not the challenged document")
    closure_files = elf_closure_document.get("files")
    require(isinstance(closure_files, list) and
            len(closure_files) == len(observed.evidence["elf_closure"]),
            "raw ELF closure differs from live closure")
    for raw, live in zip(
        closure_files, observed.evidence["elf_closure"], strict=True,
    ):
        require(isinstance(raw, dict) and set(raw) == {
                    "soname", "path", "bytes", "sha256", "md5",
                } and raw["soname"] == live["soname"] and
                raw["path"] == live["path"] and all(
                    raw[field] == live[field]
                    for field in ("bytes", "sha256", "md5")
                ), "raw ELF closure file differs from live fd")
    kernel_trust = direct_authority.get("kernel_trust")
    require(isinstance(kernel_trust, dict) and set(kernel_trust) == {
                "policy", "release", "machine", "vdso_sha256",
            } and kernel_trust.get("policy") ==
            "same-boot-pinned-kernel-vdso-v1" and
            kernel_trust.get("release") == kernel_observation.evidence["release"] and
            kernel_trust.get("machine") == kernel_observation.evidence["machine"],
            "challenged kernel authority differs from live kernel")
    _hex(kernel_trust.get("vdso_sha256"), HEX64, "challenged vDSO SHA-256")
    return _make_observation("bound-dmtcp-authority", {
        "direct_authority_sha256": challenges["dmtcp_authority"]["sha256"],
        "version": DMTCP_VERSION,
        "executables": copy.deepcopy(observed_executables),
        "injected_libraries": copy.deepcopy(observed_libraries),
        "elf_closure": copy.deepcopy(observed.evidence["elf_closure"]),
        "elf_closure_document_sha256":
            direct_authority["elf_closure"]["sha256"],
        "kernel": copy.deepcopy(kernel_observation.evidence),
        "vdso_sha256": kernel_trust["vdso_sha256"],
    }, observed.nonfixture and kernel_observation.nonfixture)


def authenticate_challenged_environments(
    *, challenges: dict[str, Any], runtime_environment: dict[str, str],
    checkpoint_environment: dict[str, str], dmtcp_authority: _Observation,
) -> _Observation:
    """Authenticate exact clean/checkpoint env maps against external records."""
    challenges = validate_controller_challenges(copy.deepcopy(challenges))
    dmtcp = _require_observation(
        dmtcp_authority, "bound-dmtcp-authority", nonfixture=False,
    )
    require(isinstance(runtime_environment, dict) and runtime_environment and
            isinstance(checkpoint_environment, dict) and
            all(isinstance(name, str) and name and isinstance(value, str)
                for mapping in (runtime_environment, checkpoint_environment)
                for name, value in mapping.items()) and
            not (set(runtime_environment) & set(checkpoint_environment)) and
            challenges["runtime_environment"] ==
            protocol_content_record(runtime_environment) and
            challenges["checkpoint_environment"] ==
            protocol_content_record(checkpoint_environment),
            "runtime/checkpoint environment is not externally challenged")
    require(set(runtime_environment) >= {"LC_ALL", "PATH"} and
            set(runtime_environment) <= {
                "LC_ALL", "PATH", "CML_HEAP_SIZE", "CML_STACK_SIZE",
            } and runtime_environment.get("LC_ALL") == "C" and
            runtime_environment.get("PATH") == "/usr/bin:/bin" and
            all(re.fullmatch(r"[1-9][0-9]*", runtime_environment[name])
                is not None for name in ("CML_HEAP_SIZE", "CML_STACK_SIZE")
                if name in runtime_environment),
            "clean runtime environment violates the fixed policy")
    require(set(checkpoint_environment) == {
                "DMTCP_CHECKPOINT_DIR", "DMTCP_COORD_PORT", "DMTCP_GZIP",
                "DMTCP_QUIET", "LD_PRELOAD",
            } and re.fullmatch(r"[1-9][0-9]*",
                               checkpoint_environment["DMTCP_COORD_PORT"]) is not None and
            1 <= int(checkpoint_environment["DMTCP_COORD_PORT"]) <= 65535 and
            checkpoint_environment["DMTCP_GZIP"] in {"0", "1"} and
            checkpoint_environment["DMTCP_QUIET"] in {"0", "1", "2"},
            "checkpoint environment violates the fixed policy")
    _safe_relative(
        checkpoint_environment["DMTCP_CHECKPOINT_DIR"],
        "DMTCP checkpoint directory",
    )
    injected = ":".join(
        item["path"] for item in dmtcp.evidence["injected_libraries"]
    )
    require(checkpoint_environment.get("LD_PRELOAD") == injected,
            "checkpoint LD_PRELOAD differs from live injected libraries")
    combined = {**runtime_environment, **checkpoint_environment}
    return _make_observation("challenged-environments", {
        "runtime": copy.deepcopy(runtime_environment),
        "checkpoint": copy.deepcopy(checkpoint_environment),
        "combined": combined,
    }, dmtcp.nonfixture)


def authenticate_resource_limits(
    *, challenges: dict[str, Any], limits: dict[str, int],
) -> _Observation:
    """Bind sampling and storage ceilings to the external challenge."""
    challenges = validate_controller_challenges(copy.deepcopy(challenges))
    fields = {
        "max_address_space_bytes", "max_aggregate_rss_kib",
        "max_checkpoint_image_bytes", "max_retained_disk_bytes",
        "sampling_interval_milliseconds",
    }
    require(isinstance(limits, dict) and set(limits) == fields and
            all(type(limits[field]) is int and limits[field] > 0
                for field in fields) and
            challenges["resource_limits"] == protocol_content_record(limits) and
            limits["max_address_space_bytes"] <=
            EXCEPTIONAL_MEMORY_CEILING_BYTES and
            limits["max_aggregate_rss_kib"] <=
            EXCEPTIONAL_MEMORY_CEILING_KIB and
            limits["max_checkpoint_image_bytes"] <=
            CHECKPOINT_IMAGE_CEILING_BYTES and
            limits["max_retained_disk_bytes"] <=
            CHECKPOINT_DISK_CEILING_BYTES and
            limits["max_checkpoint_image_bytes"] <=
            limits["max_retained_disk_bytes"] and
            10 <= limits["sampling_interval_milliseconds"] <= 60_000,
            "resource limits are not the externally challenged fixed envelope")
    return _make_observation("resource-limits", copy.deepcopy(limits), True)


def authenticate_kernel(
    expected: object, *, proc_root: str = "/proc",
    uname: os.uname_result | None = None,
) -> _Observation:
    fields = {"release", "machine", "boot_id"}
    require(isinstance(expected, dict) and set(expected) == fields,
            "malformed expected kernel authority")
    _hex(expected.get("boot_id"), UUID, "kernel boot ID")
    observed_uname = uname or os.uname()
    boot_path = Path(proc_root) / "sys/kernel/random/boot_id"
    try:
        boot_id = boot_path.read_text(encoding="ascii").strip()
    except OSError as error:
        raise AuthenticationError("cannot read kernel boot ID") from error
    observed = {
        "release": observed_uname.release,
        "machine": observed_uname.machine,
        "boot_id": boot_id,
    }
    require(observed == expected, "kernel release, machine, or boot ID drifted")
    return _make_observation("kernel", observed, proc_root == "/proc" and uname is None)


def _read_all_fd(fd: int, limit: int = 64 * 1024 * 1024) -> bytes:
    result = bytearray()
    while True:
        chunk = os.read(fd, min(1024 * 1024, limit - len(result) + 1))
        if not chunk:
            return bytes(result)
        result.extend(chunk)
        require(len(result) <= limit, "kernel file exceeds bounded read limit")


def _read_proc_at(pid_fd: int, name: str) -> bytes:
    require("/" not in name and name not in {"", ".", ".."},
            "unsafe proc entry name")
    try:
        fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC, dir_fd=pid_fd)
        try:
            return _read_all_fd(fd)
        finally:
            os.close(fd)
    except OSError as error:
        raise AuthenticationError(f"cannot read live proc entry: {name}") from error


def _parse_proc_stat(data: bytes) -> dict[str, int | str]:
    try:
        text = data.decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise AuthenticationError("non-ASCII proc stat") from error
    left = text.find("(")
    right = text.rfind(")")
    require(left > 0 and right > left and right + 2 < len(text),
            "malformed proc stat")
    pid = int(text[:left].strip())
    rest = text[right + 2:].split()
    require(len(rest) >= 20, "truncated proc stat")
    return {
        "pid": pid,
        "state": rest[0],
        "parent_pid": int(rest[1]),
        "process_group_id": int(rest[2]),
        "start_ticks": int(rest[19]),
        "user_ticks": int(rest[11]),
        "system_ticks": int(rest[12]),
        "address_space_bytes": int(rest[20]),
        "resident_pages": int(rest[21]),
    }


def _parse_nul_vector(data: bytes, label: str) -> list[str]:
    require(not data or data.endswith(b"\0"), f"unterminated proc {label}")
    raw = data[:-1].split(b"\0") if data else []
    result: list[str] = []
    for item in raw:
        try:
            value = item.decode("utf-8")
        except UnicodeDecodeError as error:
            raise AuthenticationError(f"non-UTF-8 proc {label}") from error
        require(value and all(ord(character) >= 32 for character in value),
                f"malformed proc {label}")
        result.append(value)
    return result


def _parse_environ(data: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in _parse_nul_vector(data, "environment"):
        require("=" in item, "proc environment entry lacks equals")
        name, value = item.split("=", 1)
        require(name and name not in result, "duplicate proc environment name")
        result[name] = value
    return result


def _read_vdso(
    pid_fd: int, maps: bytes, *, fixture: bool,
) -> tuple[int, int, bytes]:
    try:
        lines = maps.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise AuthenticationError("non-ASCII proc maps") from error
    matches = [line for line in lines if line.endswith(" [vdso]")]
    require(len(matches) == 1, "process does not have one exact vDSO mapping")
    address = matches[0].split(None, 1)[0]
    start_text, end_text = address.split("-", 1)
    start, end = int(start_text, 16), int(end_text, 16)
    require(0 < start < end and end - start <= 16 * 1024 * 1024,
            "malformed or oversized vDSO mapping")
    name = "vdso" if fixture else "mem"
    try:
        fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC, dir_fd=pid_fd)
        try:
            data = os.pread(fd, end - start, 0 if fixture else start)
        finally:
            os.close(fd)
    except OSError as error:
        raise AuthenticationError("cannot read process vDSO bytes") from error
    require(len(data) == end - start, "process vDSO read is incomplete")
    return start, end, data


@dataclass
class LiveProcessPin:
    evidence: dict[str, Any]
    pidfd: int | None
    proc_root: str
    nonfixture: bool
    _seal: object = _OBSERVATION_SEAL
    completed: bool = False
    gated_by_authenticator: bool = False
    trace_attached: bool = False
    gate_evidence: dict[str, Any] | None = None

    def close(self) -> None:
        if self.trace_attached:
            try:
                _ptrace(17, self.evidence["pid"], 0)
            except AuthenticationError:
                pass
            self.trace_attached = False
        if self.pidfd is not None and self.pidfd >= 0:
            os.close(self.pidfd)
            self.pidfd = None


def pin_live_process(
    expected: object, *, proc_root: str = "/proc",
) -> LiveProcessPin:
    """Pin a live process identity, argv/env/exe, kernel tuple, and vDSO."""
    fields = {
        "pid", "process_group_id", "start_ticks", "executable", "argv",
        "environment", "vdso_sha256", "kernel",
    }
    require(isinstance(expected, dict) and set(expected) == fields and
            all(type(expected.get(field)) is int and expected[field] > 0
                for field in ("pid", "process_group_id", "start_ticks")) and
            isinstance(expected.get("executable"), str) and
            expected["executable"].startswith("/") and
            isinstance(expected.get("argv"), list) and expected["argv"] and
            all(isinstance(item, str) and item and
                all(ord(character) >= 32 and character != "\x7f"
                    for character in item) and
                PFT_NAMESPACE.search(item) is None
                for item in expected["argv"]) and
            isinstance(expected.get("environment"), dict) and
            all(isinstance(name, str) and isinstance(value, str)
                for name, value in expected["environment"].items()),
            "malformed expected live process")
    _absolute_to_relative(expected["executable"], "live process executable")
    _hex(expected.get("vdso_sha256"), HEX64, "expected process vDSO SHA-256")
    kernel = expected.get("kernel")
    require(isinstance(kernel, dict) and set(kernel) == {
        "release", "machine", "boot_id",
    }, "malformed process kernel expectation")
    pid = expected["pid"]
    proc_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        proc_flags |= os.O_NOFOLLOW
    real_pidfd: int | None = None
    try:
        root_fd = os.open(proc_root, proc_flags)
        try:
            pid_fd = os.open(str(pid), proc_flags, dir_fd=root_fd)
        finally:
            os.close(root_fd)
    except OSError as error:
        raise AuthenticationError("expected process is not live") from error
    fixture = proc_root != "/proc"
    if not fixture:
        require(hasattr(os, "pidfd_open"), "kernel lacks pidfd_open")
        try:
            real_pidfd = os.pidfd_open(pid, 0)
        except OSError as error:
            os.close(pid_fd)
            raise AuthenticationError("cannot acquire live process pidfd") from error
    try:
        before = _parse_proc_stat(_read_proc_at(pid_fd, "stat"))
        require(before["state"] not in {"Z", "X", "x"},
                "expected process is not live")
        argv = _parse_nul_vector(_read_proc_at(pid_fd, "cmdline"), "argv")
        environment = _parse_environ(_read_proc_at(pid_fd, "environ"))
        maps = _read_proc_at(pid_fd, "maps")
        start, end, vdso = _read_vdso(pid_fd, maps, fixture=fixture)
        try:
            executable = os.readlink("exe", dir_fd=pid_fd)
            executable_stat = os.stat(
                "exe", dir_fd=pid_fd, follow_symlinks=not fixture,
            )
        except OSError as error:
            raise AuthenticationError("cannot read pinned process executable") from error
        after = _parse_proc_stat(_read_proc_at(pid_fd, "stat"))
        require(all(before[field] == after[field] for field in (
                    "pid", "parent_pid", "process_group_id", "start_ticks",
                )) and before["pid"] == pid and
                before["process_group_id"] == expected["process_group_id"] and
                before["start_ticks"] == expected["start_ticks"] and
                executable == expected["executable"] and
                argv == expected["argv"] and environment == expected["environment"] and
                hashlib.sha256(vdso).hexdigest() == expected["vdso_sha256"],
                "live process identity, executable, argv, env, or vDSO drifted")
        kernel_observation = authenticate_kernel(
            kernel, proc_root=proc_root,
            uname=None if not fixture else os.uname(),
        )
    except Exception:
        os.close(pid_fd)
        if real_pidfd is not None:
            os.close(real_pidfd)
        raise
    os.close(pid_fd)
    evidence = {
        **before,
        "executable": executable,
        "executable_device": executable_stat.st_dev,
        "executable_inode": executable_stat.st_ino,
        "argv": argv,
        "environment": environment,
        "vdso_start": start,
        "vdso_end": end,
        "vdso_sha256": hashlib.sha256(vdso).hexdigest(),
        "kernel": kernel_observation.evidence,
    }
    return LiveProcessPin(evidence, real_pidfd, proc_root, not fixture)


def _ptrace(request: int, pid: int, data: int) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    libc.ptrace.argtypes = [
        ctypes.c_uint, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
    ]
    libc.ptrace.restype = ctypes.c_long
    result = libc.ptrace(request, pid, None, ctypes.c_void_p(data))
    if result != 0:
        error_number = ctypes.get_errno()
        raise AuthenticationError(
            f"ptrace launch gate failed: request {request}, errno {error_number}"
        )


def _live_expected_from_proc(
    pid: int, kernel: _Observation,
) -> dict[str, Any]:
    kernel_observation = _require_observation(kernel, "kernel", nonfixture=False)
    process = Path("/proc") / str(pid)
    stat_value = _parse_proc_stat(process.joinpath("stat").read_bytes())
    pid_directory_fd = os.open(
        process, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    try:
        _, _, vdso = _read_vdso(
            pid_directory_fd, process.joinpath("maps").read_bytes(), fixture=False,
        )
    finally:
        os.close(pid_directory_fd)
    return {
        "pid": pid,
        "process_group_id": stat_value["process_group_id"],
        "start_ticks": stat_value["start_ticks"],
        "executable": os.readlink(process / "exe"),
        "argv": _parse_nul_vector(process.joinpath("cmdline").read_bytes(), "argv"),
        "environment": _parse_environ(
            process.joinpath("environ").read_bytes(),
        ),
        "vdso_sha256": hashlib.sha256(vdso).hexdigest(),
        "kernel": copy.deepcopy(kernel_observation.evidence),
    }


def spawn_exec_gated_process(
    *, executable: str, argv: list[str], environment: dict[str, str],
    kernel: _Observation, new_process_group: bool,
) -> LiveProcessPin:
    """Fork and stop at PTRACE_EVENT_EXEC before any target instruction runs."""
    kernel_observation = _require_observation(kernel, "kernel")
    require(isinstance(executable, str) and executable.startswith("/") and
            isinstance(argv, list) and argv and argv[0] == executable and
            all(isinstance(item, str) and item and
                all(ord(character) >= 32 and character != "\x7f"
                    for character in item) and
                PFT_NAMESPACE.search(item) is None for item in argv) and
            isinstance(environment, dict) and all(
                isinstance(name, str) and name and isinstance(value, str)
                for name, value in environment.items()
            ) and type(new_process_group) is bool,
            "malformed gated process launch")
    _absolute_to_relative(executable, "gated process executable")
    pid = os.fork()
    if pid == 0:
        try:
            if new_process_group:
                os.setpgid(0, 0)
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.ptrace(0, 0, None, None) != 0:  # PTRACE_TRACEME
                os._exit(126)
            os.kill(os.getpid(), signal.SIGSTOP)
            os.execve(executable, argv, environment)
        except BaseException:
            os._exit(127)
    try:
        stopped_pid, status = os.waitpid(pid, os.WUNTRACED)
        require(stopped_pid == pid and os.WIFSTOPPED(status) and
                os.WSTOPSIG(status) == signal.SIGSTOP,
                "gated child did not stop before exec")
        # PTRACE_O_TRACEEXEC | PTRACE_O_EXITKILL
        _ptrace(0x4200, pid, 0x10 | 0x00100000)
        _ptrace(7, pid, 0)  # PTRACE_CONT
        stopped_pid, status = os.waitpid(pid, os.WUNTRACED)
        require(stopped_pid == pid and os.WIFSTOPPED(status) and
                os.WSTOPSIG(status) == signal.SIGTRAP and status >> 16 == 4,
                "gated child did not stop at the exec boundary")
        expected = _live_expected_from_proc(pid, kernel_observation)
        require(expected["executable"] == executable and
                expected["argv"] == argv and
                expected["environment"] == environment and
                (not new_process_group or
                 expected["process_group_id"] == pid),
                "exec-gated child differs from exact launch inputs")
        pin = pin_live_process(expected)
        pin.gated_by_authenticator = True
        pin.trace_attached = True
        pin.gate_evidence = {
            "policy": "parent-ptrace-exec-stop-before-first-target-instruction-v1",
            "pid": pid,
            "process_group_id": expected["process_group_id"],
            "start_ticks": expected["start_ticks"],
            "exec_stop_signal": int(signal.SIGTRAP),
            "ptrace_event": "PTRACE_EVENT_EXEC",
            "released": False,
        }
        return pin
    except Exception:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
        raise


def release_exec_gated_process(pin: LiveProcessPin) -> None:
    require(isinstance(pin, LiveProcessPin) and pin._seal is _OBSERVATION_SEAL and
            pin.nonfixture and pin.gated_by_authenticator and pin.trace_attached and
            pin.gate_evidence is not None and
            pin.gate_evidence.get("released") is False,
            "process does not have an unreleased authenticator exec gate")
    _ptrace(17, pin.evidence["pid"], 0)  # PTRACE_DETACH resumes the tracee.
    pin.trace_attached = False
    pin.gate_evidence["released"] = True
    pin.gate_evidence["release_monotonic_ns"] = time.monotonic_ns()


def complete_parent_owned_process(
    pin: LiveProcessPin, *, allowed_exit_codes: Iterable[int] = (),
    allowed_signals: Iterable[int] = (),
    fixture_completion: object | None = None,
) -> _Observation:
    """Observe exit through pidfd, reap as parent, and prove /proc removal."""
    require(isinstance(pin, LiveProcessPin) and pin._seal is _OBSERVATION_SEAL and
            not pin.completed, "invalid or reused live process pin")
    exit_codes = set(allowed_exit_codes)
    signals = set(allowed_signals)
    require(all(isinstance(item, int) and not isinstance(item, bool) and item >= 0
                for item in exit_codes) and
            all(isinstance(item, int) and not isinstance(item, bool) and item > 0
                for item in signals),
            "malformed allowed process termination")
    pid = pin.evidence["pid"]
    if pin.nonfixture:
        require(pin.pidfd is not None and hasattr(os, "P_PIDFD"),
                "parent-owned lifecycle requires pidfd wait support")
        try:
            observed = os.waitid(
                os.P_PIDFD, pin.pidfd, os.WEXITED | os.WNOWAIT,
            )
        except (ChildProcessError, OSError) as error:
            raise AuthenticationError(
                "authenticator is not the exiting process parent"
            ) from error
        require(observed is not None, "process has not exited")
        if observed.si_code == os.CLD_EXITED:
            termination = {"kind": "exit", "value": observed.si_status}
            require(observed.si_status in exit_codes,
                    "process exit code was not predeclared")
        else:
            termination = {"kind": "signal", "value": observed.si_status}
            require(observed.si_status in signals,
                    "process termination signal was not predeclared")
        os.waitid(os.P_PIDFD, pin.pidfd, os.WEXITED)
        require(not (Path(pin.proc_root) / str(pid)).exists(),
                "reaped process still exists in procfs")
    else:
        require(isinstance(fixture_completion, dict) and
                set(fixture_completion) == {"kind", "value", "proc_absent"} and
                fixture_completion.get("proc_absent") is True,
                "fixture lifecycle completion is incomplete")
        require(not (Path(pin.proc_root) / str(pid)).exists(),
                "fixture process was claimed absent but remains in proc fixture")
        termination = {
            "kind": fixture_completion["kind"],
            "value": fixture_completion["value"],
        }
        require((termination["kind"] == "exit" and
                 termination["value"] in exit_codes) or
                (termination["kind"] == "signal" and
                 termination["value"] in signals),
                "fixture termination was not predeclared")
    pin.completed = True
    pin.close()
    return _make_observation("completed-process", {
        "process": copy.deepcopy(pin.evidence),
        "termination": termination,
        "reaped": True,
        "proc_absent_after_reap": True,
    }, pin.nonfixture)


def _listening_socket_inodes(proc_root: str, port: int) -> set[str]:
    require(type(port) is int and 1 <= port <= 65535,
            "malformed coordinator port")
    result: set[str] = set()
    for name in ("tcp", "tcp6"):
        path = Path(proc_root) / "net" / name
        try:
            lines = path.read_text(encoding="ascii").splitlines()[1:]
        except OSError as error:
            raise AuthenticationError("cannot read kernel TCP socket table") from error
        for line in lines:
            fields = line.split()
            require(len(fields) >= 10, "malformed kernel TCP socket row")
            local = fields[1]
            state = fields[3]
            inode = fields[9]
            try:
                observed_port = int(local.rsplit(":", 1)[1], 16)
            except (ValueError, IndexError) as error:
                raise AuthenticationError("malformed kernel TCP address") from error
            if state == "0A" and observed_port == port:
                result.add(inode)
    require(result, "coordinator port is not listening")
    return result


def authenticate_coordinator_port(pin: LiveProcessPin, port: int) -> _Observation:
    require(isinstance(pin, LiveProcessPin) and pin._seal is _OBSERVATION_SEAL and
            not pin.completed, "coordinator process is not live")
    inodes = _listening_socket_inodes(pin.proc_root, port)
    fd_path = Path(pin.proc_root) / str(pin.evidence["pid"]) / "fd"
    try:
        links = [os.readlink(item) for item in fd_path.iterdir()]
    except OSError as error:
        raise AuthenticationError("cannot inspect coordinator file descriptors") from error
    owned = {
        match.group(1) for value in links
        if (match := re.fullmatch(r"socket:\[([0-9]+)\]", value)) is not None
    }
    selected = sorted(inodes & owned)
    require(len(selected) == 1,
            "coordinator does not own exactly one selected listening socket")
    return _make_observation("coordinator-port", {
        "process_identity": {
            field: pin.evidence[field]
            for field in ("pid", "process_group_id", "start_ticks")
        },
        "port": port,
        "socket_inode": selected[0],
    }, pin.nonfixture)


def _decode_exact_json(data: bytes, label: str) -> dict[str, Any]:
    try:
        text = data.decode("utf-8")
        value = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuthenticationError(f"malformed {label} JSON") from error
    require(isinstance(value, dict) and data == canonical_json_bytes(value),
            f"{label} is not canonical JSON")
    return value


def authenticate_phase_files(
    *, filesystem: AnchoredFilesystem, phase: str,
    challenges: dict[str, Any], completed_controller: _Observation,
    event_path: str, event_authority: dict[str, Any],
    log_path: str, log_authority: dict[str, Any],
    sampling_interval_milliseconds: int,
) -> _Observation:
    """Inspect retrospective phase files without qualifying them as live evidence.

    This helper is useful for diagnostics only.  Only ``LivePhaseObserver`` can
    produce a nonfixture phase token, because it timestamps receipts and reads
    resource counters while the controller is alive.
    """
    challenges = validate_controller_challenges(copy.deepcopy(challenges))
    completed = _require_observation(
        completed_controller, "completed-process", nonfixture=False,
    )
    require(phase in PHASES and type(sampling_interval_milliseconds) is int and
            sampling_interval_milliseconds > 0,
            "malformed phase sampling policy")
    event = filesystem.authenticate_file(
        event_path, event_authority, immutable=True,
    )
    log = filesystem.authenticate_file(log_path, log_authority, immutable=True)
    event_parent, event_name = filesystem._open_parent(event_path)
    try:
        fd = os.open(event_name, os.O_RDONLY | os.O_CLOEXEC, dir_fd=event_parent)
        try:
            event_value = _decode_exact_json(_read_all_fd(fd), "phase event")
        finally:
            os.close(fd)
    finally:
        os.close(event_parent)
    fields = {
        "schema", "kind", "phase", "challenge_id", "challenge_name",
        "challenge_value", "controller_identity", "begin_monotonic_ns",
        "end_monotonic_ns", "sampling_interval_milliseconds", "samples",
        "events", "pft_used",
    }
    challenge_name, challenge_value = phase_challenge(challenges, phase)
    process = completed.evidence["process"]
    identity = {
        name: process[name] for name in (
            "pid", "process_group_id", "start_ticks",
        )
    }
    require(set(event_value) == fields and event_value.get("schema") == 1 and
            event_value.get("kind") ==
            "candle-flyspeck-raw-os-phase-events-v1" and
            event_value.get("phase") == phase and
            event_value.get("challenge_id") == challenges["challenge_id"] and
            event_value.get("challenge_name") == challenge_name and
            event_value.get("challenge_value") == challenge_value and
            event_value.get("controller_identity") == identity and
            event_value.get("sampling_interval_milliseconds") ==
            sampling_interval_milliseconds and event_value.get("pft_used") is False,
            "phase event file is challenge- or process-spliced")
    begin = event_value.get("begin_monotonic_ns")
    end = event_value.get("end_monotonic_ns")
    samples = event_value.get("samples")
    require(type(begin) is int and type(end) is int and 0 < begin < end and
            isinstance(samples, list) and len(samples) >= 2,
            "phase cadence coverage is incomplete")
    sample_fields = {
        "monotonic_ns", "cpu_ns", "aggregate_rss_kib",
        "address_space_bytes", "retained_disk_bytes",
    }
    previous: int | None = None
    for index, sample in enumerate(samples):
        require(isinstance(sample, dict) and set(sample) == sample_fields and
                all(type(sample.get(name)) is int and sample[name] >= 0
                    for name in sample_fields),
                f"malformed cadence sample: {index}")
        current = sample["monotonic_ns"]
        require(previous is None or (
            previous < current and
            current - previous <= sampling_interval_milliseconds * 1_000_000
        ), f"cadence sample gap exceeds policy: {index}")
        previous = current
    require(samples[0]["monotonic_ns"] == begin and
            samples[-1]["monotonic_ns"] == end,
            "cadence samples do not cover phase begin and end")
    events = event_value.get("events")
    require(isinstance(events, list), "phase events are not a list")
    event_fields = {"sequence", "kind", "monotonic_ns", "action_index"}
    ready_positions: list[int] = []
    for index, item in enumerate(events):
        require(isinstance(item, dict) and set(item) == event_fields and
                type(item.get("sequence")) is int and item["sequence"] == index and
                isinstance(item.get("kind"), str) and item["kind"] and
                type(item.get("monotonic_ns")) is int and
                begin <= item["monotonic_ns"] <= end and
                (item.get("action_index") is None or
                 type(item["action_index"]) is int),
                f"malformed ordered phase event: {index}")
        if item["kind"] == "READY":
            ready_positions.append(index)
    if phase == "origin":
        require(len(ready_positions) == 1 and not any(
            item["kind"] == "action" for item in events[ready_positions[0] + 1:]
        ), "origin phase executed an action after READY")
    log_parent, log_name = filesystem._open_parent(log_path)
    try:
        fd = os.open(log_name, os.O_RDONLY | os.O_CLOEXEC, dir_fd=log_parent)
        try:
            log_bytes = _read_all_fd(fd)
        finally:
            os.close(fd)
    finally:
        os.close(log_parent)
    for binding in (
        challenges["challenge_id"], challenge_value, str(identity["pid"]),
        str(identity["process_group_id"]), str(identity["start_ticks"]),
    ):
        require(binding.encode() in log_bytes,
                "phase log omits a challenge or controller identity binding")
    return _make_observation("phase", {
        "phase": phase,
        "challenge_name": challenge_name,
        "challenge_value": challenge_value,
        "controller": copy.deepcopy(completed.evidence),
        "event_file": event,
        "log_file": log,
        "begin_monotonic_ns": begin,
        "end_monotonic_ns": end,
        "sample_count": len(samples),
        "maximum_sampling_gap_ns": max(
            right["monotonic_ns"] - left["monotonic_ns"]
            for left, right in zip(samples, samples[1:])
        ),
        "ordered_sample_sha256": canonical_sha256(samples),
        "ordered_event_sha256": canonical_sha256(events),
        "post_ready_action_receipt_count": 0,
        "retrospective_only": True,
    }, False)


def _process_group_sample(
    proc_root: str, process_group_id: int, controller_pid: int,
    controller_start_ticks: int, retained_fds: tuple[int, ...], monotonic_ns: int,
) -> dict[str, int]:
    """Read aggregate CPU/RSS/address-space and pinned retained-file bytes."""
    ticks_per_second = os.sysconf("SC_CLK_TCK")
    page_size = os.sysconf("SC_PAGE_SIZE")
    require(ticks_per_second > 0 and page_size > 0,
            "invalid kernel clock/page configuration")
    cpu_ticks = 0
    rss_pages = 0
    address_space = 0
    members = 0
    controller_seen = False
    try:
        entries = list(Path(proc_root).iterdir())
    except OSError as error:
        raise AuthenticationError("cannot scan live process group") from error
    for entry in entries:
        if not entry.name.isdecimal():
            continue
        try:
            first = _parse_proc_stat((entry / "stat").read_bytes())
            if first["process_group_id"] != process_group_id or first["state"] in {
                "Z", "X", "x",
            }:
                continue
            second = _parse_proc_stat((entry / "stat").read_bytes())
        except (OSError, AuthenticationError):
            continue
        require(all(first[field] == second[field] for field in (
                    "pid", "process_group_id", "start_ticks",
                )), "process changed identity during resource sample")
        members += 1
        cpu_ticks += int(second["user_ticks"]) + int(second["system_ticks"])
        rss_pages += max(0, int(second["resident_pages"]))
        address_space += max(0, int(second["address_space_bytes"]))
        if (second["pid"] == controller_pid and
                second["process_group_id"] == process_group_id and
                second["start_ticks"] == controller_start_ticks):
            controller_seen = True
    require(controller_seen and members > 0,
            "controller vanished from its sampled process group")
    retained_bytes = 0
    for fd in retained_fds:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode),
                "retained-disk sample contains a non-regular fd")
        retained_bytes += before.st_size
        after = os.fstat(fd)
        require(_stat_identity(before) == _stat_identity(after),
                "retained file changed during resource sample")
    return {
        "monotonic_ns": monotonic_ns,
        "cpu_ns": cpu_ticks * 1_000_000_000 // ticks_per_second,
        "aggregate_rss_kib": rss_pages * page_size // 1024,
        "address_space_bytes": address_space,
        "retained_disk_bytes": retained_bytes,
        "process_group_members": members,
    }


def _write_content_addressed_json(
    filesystem: AnchoredFilesystem, directory: str, prefix: str, value: object,
) -> dict[str, Any]:
    """Publish one canonical immutable raw record with O_EXCL and fd rehash."""
    require(re.fullmatch(r"[a-z0-9-]+", prefix) is not None,
            "unsafe content-addressed prefix")
    data = canonical_json_bytes(value)
    digest = hashlib.sha256(data).hexdigest()
    name = f"{prefix}-{digest}.json"
    directory = _safe_relative(directory, "raw evidence directory")
    directory_fd = filesystem.open_directory(directory)
    directory_stat = os.fstat(directory_fd)
    require(directory_stat.st_uid == os.getuid() and
            stat.S_IMODE(directory_stat.st_mode) & 0o022 == 0,
            "raw evidence directory is not privately controlled")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd: int | None = None
    try:
        fd = os.open(name, flags, 0o400, dir_fd=directory_fd)
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            require(written > 0, "short raw-evidence write")
            view = view[written:]
        os.fsync(fd)
        os.fchmod(fd, 0o444)
        os.fsync(fd)
        observed = os.fstat(fd)
        require(stat.S_ISREG(observed.st_mode) and observed.st_nlink == 1,
                "raw evidence publication is aliased")
        os.fsync(directory_fd)
    except OSError as error:
        if error.errno == errno.EEXIST:
            raise AuthenticationError(
                "content-addressed raw evidence already exists; no-replace refused"
            ) from error
        raise AuthenticationError("cannot publish raw evidence") from error
    finally:
        if fd is not None:
            os.close(fd)
        os.close(directory_fd)
    relative = f"{directory}/{name}"
    authority = {
        "bytes": len(data),
        "sha256": digest,
        "md5": hashlib.md5(data, usedforsecurity=False).hexdigest(),
        "mode": "0444",
        "uid": os.getuid(),
        "gid": os.getgid(),
    }
    return filesystem.authenticate_file(relative, authority, immutable=True)


class LivePhaseObserver:
    """Parent-side observer for one controller process and its raw receipts."""

    def __init__(
        self, *, pin: LiveProcessPin, phase: str,
        challenges: dict[str, Any], resource_limits: _Observation,
        retained_fds: Iterable[int] = (), fixture_monotonic_ns: int | None = None,
    ) -> None:
        require(isinstance(pin, LiveProcessPin) and pin._seal is _OBSERVATION_SEAL and
                not pin.completed, "phase controller is not pinned live")
        self.challenges = validate_controller_challenges(copy.deepcopy(challenges))
        self.resource_limits = _require_observation(
            resource_limits, "resource-limits", nonfixture=False,
        )
        require(phase in PHASES, "malformed live phase policy")
        require(fixture_monotonic_ns is None or not pin.nonfixture,
                "nonfixture timestamps must come from CLOCK_MONOTONIC")
        self.pin = pin
        self.phase = phase
        self.interval_ms = self.resource_limits.evidence[
            "sampling_interval_milliseconds"
        ]
        self.retained_fds = tuple(retained_fds)
        self.challenge_name, self.challenge_value = phase_challenge(
            self.challenges, phase,
        )
        self.identity = {
            field: pin.evidence[field]
            for field in ("pid", "process_group_id", "start_ticks")
        }
        self.samples: list[dict[str, int]] = []
        self.receipts: list[dict[str, Any]] = []
        self.raw_receipt_hashes: set[str] = set()
        self.event_nonces: set[str] = set()
        self.ended = False
        self.gate_was_held_at_begin = (
            pin.gated_by_authenticator and pin.trace_attached and
            pin.gate_evidence is not None and
            pin.gate_evidence.get("released") is False
        )
        self.sample(monotonic_ns=fixture_monotonic_ns)

    def release_controller(self) -> None:
        """Release the exec stop only after the first OS sample is recorded."""
        require(self.gate_was_held_at_begin and len(self.samples) == 1,
                "phase did not begin behind the authenticator exec gate")
        release_exec_gated_process(self.pin)

    def _now(self, supplied: int | None) -> int:
        require(supplied is None or not self.pin.nonfixture,
                "nonfixture timestamps cannot be caller supplied")
        value = time.monotonic_ns() if supplied is None else supplied
        require(type(value) is int and value > 0, "invalid monotonic timestamp")
        return value

    def sample(self, *, monotonic_ns: int | None = None) -> dict[str, int]:
        require(not self.ended and not self.pin.completed,
                "cannot sample a completed phase")
        now = self._now(monotonic_ns)
        require(not self.samples or self.samples[-1]["monotonic_ns"] < now,
                "phase samples are not strictly monotonic")
        if self.samples:
            require(now - self.samples[-1]["monotonic_ns"] <=
                    self.interval_ms * 1_000_000,
                    "live sampling cadence exceeded policy")
        observed = _process_group_sample(
            self.pin.proc_root, self.identity["process_group_id"],
            self.identity["pid"], self.identity["start_ticks"],
            self.retained_fds, now,
        )
        require(observed["aggregate_rss_kib"] <=
                self.resource_limits.evidence["max_aggregate_rss_kib"] and
                observed["address_space_bytes"] <=
                self.resource_limits.evidence["max_address_space_bytes"] and
                observed["retained_disk_bytes"] <=
                self.resource_limits.evidence["max_retained_disk_bytes"],
                "live phase exceeded challenged resource limits")
        self.samples.append(observed)
        return copy.deepcopy(observed)

    def receive_event(
        self, raw_receipt: bytes, *, monotonic_ns: int | None = None,
    ) -> str:
        """Receive one canonical child receipt and return a parent handshake ACK."""
        require(not self.ended and not self.pin.completed,
                "cannot receive an event from a completed phase")
        receipt = _decode_exact_json(raw_receipt, "live phase receipt")
        fields = {
            "schema", "kind", "phase", "challenge_id", "challenge_name",
            "challenge_value", "controller_identity", "event", "event_nonce",
            "action_index", "pft_used",
        }
        require(set(receipt) == fields and receipt.get("schema") == 1 and
                receipt.get("kind") == "candle-flyspeck-live-phase-receipt-v1" and
                receipt.get("phase") == self.phase and
                receipt.get("challenge_id") == self.challenges["challenge_id"] and
                receipt.get("challenge_name") == self.challenge_name and
                receipt.get("challenge_value") == self.challenge_value and
                receipt.get("controller_identity") == self.identity and
                isinstance(receipt.get("event"), str) and receipt["event"] and
                receipt.get("pft_used") is False,
                "live receipt is challenge- or process-spliced")
        _hex(receipt.get("event_nonce"), HEX32, "live event nonce")
        require(receipt["event_nonce"] not in self.event_nonces,
                "live event nonce was reused")
        if receipt["event"] == "action":
            require(type(receipt.get("action_index")) is int and
                    receipt["action_index"] >= 0,
                    "action receipt lacks an action index")
        else:
            require(receipt.get("action_index") is None,
                    "non-action receipt has an action index")
        digest = hashlib.sha256(raw_receipt).hexdigest()
        require(digest not in self.raw_receipt_hashes,
                "live raw receipt was replayed")
        now = self._now(monotonic_ns)
        require(now >= self.samples[0]["monotonic_ns"] and
                (not self.receipts or
                 self.receipts[-1]["received_monotonic_ns"] < now),
                "live event receipt order is not monotonic")
        self.raw_receipt_hashes.add(digest)
        self.event_nonces.add(receipt["event_nonce"])
        self.receipts.append({
            "sequence": len(self.receipts),
            "received_monotonic_ns": now,
            "raw_bytes": len(raw_receipt),
            "raw_sha256": digest,
            "receipt": receipt,
        })
        return f"ACK/{receipt['event']}/{digest}"

    def end(self, *, monotonic_ns: int | None = None) -> None:
        require(not self.ended, "phase observer already ended")
        self.sample(monotonic_ns=monotonic_ns)
        required_event = {
            "pilot": "PILOT_DONE",
            "origin": "READY",
            "checkpoint": "CHECKPOINT_IMAGE_READY",
            "clean-1": "ATTEMPT_DONE",
            "clean-2": "ATTEMPT_DONE",
            "resume": "RESUMED",
        }[self.phase]
        positions = [
            index for index, item in enumerate(self.receipts)
            if item["receipt"]["event"] == required_event
        ]
        require(len(positions) == 1,
                f"phase lacks one exact {required_event} handshake")
        if self.phase == "origin":
            require(not any(
                item["receipt"]["event"] == "action"
                for item in self.receipts[positions[0] + 1:]
            ), "origin controller executed an action after READY")
        self.ended = True

    def finish(
        self, completed_controller: _Observation, *,
        filesystem: AnchoredFilesystem, output_directory: str,
    ) -> _Observation:
        """Seal parent-observed raw data after the exact controller is reaped."""
        require(self.ended, "phase lifecycle has not reached its end boundary")
        completed = _require_observation(
            completed_controller, "completed-process", nonfixture=False,
        )
        process = completed.evidence["process"]
        require({field: process[field] for field in self.identity} == self.identity,
                "completed controller differs from live phase controller")
        cadence = {
            "schema": 1,
            "kind": "candle-flyspeck-parent-os-cadence-v1",
            "phase": self.phase,
            "challenge_id": self.challenges["challenge_id"],
            "challenge_name": self.challenge_name,
            "challenge_value": self.challenge_value,
            "controller_identity": self.identity,
            "sampling_interval_milliseconds": self.interval_ms,
            "samples": self.samples,
            "pft_used": False,
        }
        events = {
            "schema": 1,
            "kind": "candle-flyspeck-parent-event-receipts-v1",
            "phase": self.phase,
            "challenge_id": self.challenges["challenge_id"],
            "challenge_name": self.challenge_name,
            "challenge_value": self.challenge_value,
            "controller_identity": self.identity,
            "receipts": self.receipts,
            "pft_used": False,
        }
        cadence_file = _write_content_addressed_json(
            filesystem, output_directory, f"{self.phase}-cadence", cadence,
        )
        events_file = _write_content_addressed_json(
            filesystem, output_directory, f"{self.phase}-events", events,
        )
        maximum_gap = max(
            right["monotonic_ns"] - left["monotonic_ns"]
            for left, right in zip(self.samples, self.samples[1:])
        )
        return _make_observation("phase", {
            "phase": self.phase,
            "challenge_id": self.challenges["challenge_id"],
            "challenge_name": self.challenge_name,
            "challenge_value": self.challenge_value,
            "controller": copy.deepcopy(completed.evidence),
            "begin_monotonic_ns": self.samples[0]["monotonic_ns"],
            "end_monotonic_ns": self.samples[-1]["monotonic_ns"],
            "sample_count": len(self.samples),
            "resource_limits": copy.deepcopy(self.resource_limits.evidence),
            "maximum_sampling_gap_ns": maximum_gap,
            "ordered_sample_sha256": canonical_sha256(self.samples),
            "ordered_event_sha256": canonical_sha256(self.receipts),
            "event_nonces": sorted(self.event_nonces),
            "cadence_file": cadence_file,
            "event_file": events_file,
            "filesystem_root": filesystem.root_path,
            "post_ready_action_receipt_count": 0,
            "receipt_observation_scope":
                "controller-supplied-bytes-received-and-timestamped-by-parent",
            "exec_gate": copy.deepcopy(self.pin.gate_evidence),
        }, self.pin.nonfixture and completed.nonfixture and
           filesystem.root_path == "/" and self.resource_limits.nonfixture and
           self.gate_was_held_at_begin and self.pin.gate_evidence is not None and
           self.pin.gate_evidence.get("released") is True)


def _hash_open_fd(fd: int) -> dict[str, Any]:
    before = os.fstat(fd)
    require(stat.S_ISREG(before.st_mode), "held image fd is not regular")
    os.lseek(fd, 0, os.SEEK_SET)
    sha256 = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    size = 0
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            break
        sha256.update(chunk)
        md5.update(chunk)
        size += len(chunk)
    after = os.fstat(fd)
    require(_stat_identity(before) == _stat_identity(after),
            "held image changed while rehashed")
    return {
        "bytes": size,
        "sha256": sha256.hexdigest(),
        "md5": md5.hexdigest(),
        "mode": f"0{stat.S_IMODE(before.st_mode):03o}",
        "uid": before.st_uid,
        "gid": before.st_gid,
        "nlink": before.st_nlink,
        "device": before.st_dev,
        "inode": before.st_ino,
        "mtime_ns": before.st_mtime_ns,
        "ctime_ns": before.st_ctime_ns,
    }


@dataclass
class PublicationPin:
    evidence: dict[str, Any]
    directory_fd: int
    image_fds: tuple[int, ...]
    filesystem_root: str
    nonfixture: bool
    _seal: object = _OBSERVATION_SEAL

    def close(self) -> None:
        for fd in self.image_fds:
            try:
                os.close(fd)
            except OSError:
                pass
        self.image_fds = ()
        if self.directory_fd >= 0:
            os.close(self.directory_fd)
            self.directory_fd = -1


def publish_checkpoint_no_replace(
    *, filesystem: AnchoredFilesystem, staging_directory: str,
    publication_parent: str, images: list[dict[str, Any]],
    challenges: dict[str, Any], resource_limits: _Observation,
) -> PublicationPin:
    """Atomically publish the exact ordered image set and retain all fds."""
    challenges = validate_controller_challenges(copy.deepcopy(challenges))
    limits = _require_observation(resource_limits, "resource-limits", nonfixture=False)
    staging_directory = _safe_relative(staging_directory, "staging directory")
    publication_parent = _safe_relative(
        publication_parent, "checkpoint publication parent",
    )
    require(PurePosixPath(staging_directory).parts[0] == "staging" and
            publication_parent == "checkpoints",
            "checkpoint paths differ from the direct protocol layout")
    require(isinstance(images, list) and images,
            "checkpoint publication has no selected images")
    ordered_paths: list[str] = []
    for item in images:
        require(isinstance(item, dict) and set(item) == {"path", "authority"},
                "malformed selected checkpoint image")
        path = _safe_relative(item["path"], "checkpoint image path")
        require(PurePosixPath(path).parent == PurePosixPath(".") and
                path.endswith(".dmtcp") and path not in ordered_paths and
                isinstance(item["authority"], dict) and
                type(item["authority"].get("bytes")) is int,
                "checkpoint image names are duplicated or not DMTCP images")
        ordered_paths.append(path)
    total_image_bytes = sum(item["authority"].get("bytes", -1) for item in images)
    require(0 <= total_image_bytes <=
            limits.evidence["max_checkpoint_image_bytes"] and
            total_image_bytes <= limits.evidence["max_retained_disk_bytes"],
            "checkpoint images exceed challenged storage limits")
    actual = filesystem.exact_tree(staging_directory)
    require(actual == sorted(ordered_paths),
            "staging tree differs from exact selected checkpoint images")
    stage_fd = filesystem.open_directory(staging_directory)
    stage_stat = os.fstat(stage_fd)
    require(stage_stat.st_uid == os.getuid() and stage_stat.st_gid == os.getgid() and
            stat.S_IMODE(stage_stat.st_mode) & 0o022 == 0,
            "staging image directory is not privately owned")
    held: list[int] = []
    observations: list[dict[str, Any]] = []
    try:
        for item in images:
            relative = f"{staging_directory}/{item['path']}"
            observed = filesystem.authenticate_file(
                relative, item["authority"], immutable=True,
            )
            parent_fd, name = filesystem._open_parent(relative)
            flags = os.O_RDONLY | os.O_CLOEXEC
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                image_fd = os.open(name, flags, dir_fd=parent_fd)
            finally:
                os.close(parent_fd)
            held_stat = os.fstat(image_fd)
            require(held_stat.st_dev == observed["device"] and
                    held_stat.st_ino == observed["inode"] and
                    held_stat.st_nlink == 1,
                    "checkpoint image changed before fd retention")
            held.append(image_fd)
            observations.append(observed)
        direct_files = [{
                "path": item["path"],
                "bytes": item["authority"]["bytes"],
                "sha256": item["authority"]["sha256"],
                "md5": item["authority"]["md5"],
            } for item in images]
        ordered_manifest_sha256 = direct_ordered_manifest_sha256(direct_files)
        source_parent, source_name = filesystem._open_parent(staging_directory)
        destination_parent_fd = filesystem.open_directory(publication_parent)
        publication_parent_stat = os.fstat(destination_parent_fd)
        require(publication_parent_stat.st_dev == stage_stat.st_dev,
                "staging and checkpoints directories are on different devices")
        libc = ctypes.CDLL(None, use_errno=True)
        syscall_numbers = {"x86_64": 316, "aarch64": 276, "i686": 353}
        syscall_number = syscall_numbers.get(platform.machine())
        require(syscall_number is not None,
                "unknown renameat2 syscall number for this machine")
        libc.syscall.argtypes = [
            ctypes.c_long, ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
            ctypes.c_char_p, ctypes.c_uint,
        ]
        libc.syscall.restype = ctypes.c_long
        try:
            result = libc.syscall(
                syscall_number, source_parent, os.fsencode(source_name),
                destination_parent_fd, os.fsencode(ordered_manifest_sha256), 1,
            )
            if result != 0:
                error_number = ctypes.get_errno()
                if error_number == errno.EEXIST:
                    raise AuthenticationError(
                        "checkpoint publication destination exists; no-replace refused"
                    )
                raise AuthenticationError(
                    f"checkpoint no-replace rename failed: errno {error_number}"
                )
            os.fchmod(stage_fd, 0o555)
            os.fsync(stage_fd)
            os.fsync(destination_parent_fd)
        finally:
            os.close(source_parent)
            os.close(destination_parent_fd)
        published_directory = f"{publication_parent}/{ordered_manifest_sha256}"
        require(filesystem.exact_tree(published_directory) ==
                sorted(ordered_paths),
                "published checkpoint tree changed during rename")
        published_fd = filesystem.open_directory(published_directory)
        published_stat = os.fstat(published_fd)
        require(stage_stat.st_dev == published_stat.st_dev and
                stage_stat.st_ino == published_stat.st_ino and
                stat.S_IMODE(published_stat.st_mode) == 0o555,
                "published checkpoint directory is not the staged inode")
        for item, before, held_fd in zip(images, observations, held, strict=True):
            after = filesystem.authenticate_file(
                f"{published_directory}/{item['path']}", item["authority"],
                immutable=True,
            )
            held_stat = os.fstat(held_fd)
            require(after["device"] == before["device"] == held_stat.st_dev and
                    after["inode"] == before["inode"] == held_stat.st_ino and
                    held_stat.st_nlink == 1,
                    "published image identity differs from retained image fd")
    except Exception:
        os.close(stage_fd)
        for fd in held:
            os.close(fd)
        raise
    os.close(stage_fd)
    absolute_prefix = "/" + published_directory if filesystem.root_path == "/" else (
        str(Path(filesystem.root_path) / published_directory)
    )
    return PublicationPin({
        "challenge_id": challenges["challenge_id"],
        "checkpoint_token": challenges["checkpoint_token"],
        "resource_limits": copy.deepcopy(limits.evidence),
        "ordered_manifest_sha256": ordered_manifest_sha256,
        "published_directory": absolute_prefix,
        "published_relative_directory": published_directory,
        "ordered_images": [{
            "path": item["path"],
            "authority": copy.deepcopy(item["authority"]),
            "identity": {
                "device": observed["device"], "inode": observed["inode"],
            },
        } for item, observed in zip(images, observations, strict=True)],
        "direct_protocol_image_files": copy.deepcopy(direct_files),
        "ordered_restart_image_argv": [
            f"{published_directory}/{path}" for path in ordered_paths
        ],
        "direct_protocol_atomic_publication": {
            "staging_path": staging_directory,
            "published_path": published_directory,
            "staging_device": stage_stat.st_dev,
            "published_parent_device": publication_parent_stat.st_dev,
            "rename_noreplace": True,
            "parent_fsync": True,
            "image_files_read_only": True,
            "image_directory_read_only": True,
            "authentication_scope": CONTROLLER_ASSERTION_SCOPE,
            "anchored_nofollow_rehash": False,
        },
        "anchored_nofollow_observed": True,
        "rename_noreplace_observed": True,
        "held_directory_and_image_fds": True,
    }, published_fd, tuple(held), filesystem.root_path,
       filesystem.root_path == "/" and limits.nonfixture)


def rehash_checkpoint_for_restart(
    publication: PublicationPin, *, filesystem: AnchoredFilesystem,
) -> _Observation:
    """Revalidate held and named image identities immediately around restart."""
    require(isinstance(publication, PublicationPin) and
            publication._seal is _OBSERVATION_SEAL and publication.directory_fd >= 0 and
            len(publication.image_fds) ==
            len(publication.evidence["ordered_images"]),
            "missing live checkpoint publication pin")
    require(filesystem.root_path == publication.filesystem_root,
            "restart rehash uses a different filesystem anchor")
    directory = publication.evidence["published_relative_directory"]
    named_fd = filesystem.open_directory(directory)
    try:
        held_directory = os.fstat(publication.directory_fd)
        named_directory = os.fstat(named_fd)
        require(held_directory.st_dev == named_directory.st_dev and
                held_directory.st_ino == named_directory.st_ino and
                stat.S_IMODE(held_directory.st_mode) == 0o555,
                "published checkpoint directory was renamed or replaced")
    finally:
        os.close(named_fd)
    ordered = publication.evidence["ordered_images"]
    require(filesystem.exact_tree(directory) ==
            sorted(item["path"] for item in ordered),
            "restart checkpoint tree has omitted or extra images")
    observations: list[dict[str, Any]] = []
    for item, held_fd in zip(ordered, publication.image_fds, strict=True):
        held = _hash_open_fd(held_fd)
        authority = item["authority"]
        for field in ("bytes", "sha256", "md5", "mode", "uid", "gid"):
            require(held[field] == authority[field],
                    "held restart image content or authority changed")
        require(held["nlink"] == 1 and
                held["device"] == item["identity"]["device"] and
                held["inode"] == item["identity"]["inode"],
                "held restart image was linked or replaced")
        named = filesystem.authenticate_file(
            f"{directory}/{item['path']}", authority, immutable=True,
        )
        require(named["device"] == held["device"] and
                named["inode"] == held["inode"],
                "restart image name does not select the held publication inode")
        observations.append(named)
    return _make_observation("restart-images", {
        "ordered_manifest_sha256": publication.evidence["ordered_manifest_sha256"],
        "ordered_restart_image_argv": copy.deepcopy(
            publication.evidence["ordered_restart_image_argv"],
        ),
        "restart_rehash_monotonic_ns": time.monotonic_ns(),
        "images": observations,
    }, publication.nonfixture and filesystem.root_path == "/")


def authenticate_killed_process_tree(
    *, expected_identities: list[dict[str, int]],
    completed_processes: list[_Observation],
) -> _Observation:
    """Prove a predeclared, single-PGID process tree was killed and reaped."""
    identity_fields = {"pid", "process_group_id", "start_ticks"}
    require(isinstance(expected_identities, list) and expected_identities and
            all(isinstance(item, dict) and set(item) == identity_fields and
                all(type(item[field]) is int and item[field] > 0
                    for field in identity_fields)
                for item in expected_identities),
            "malformed predeclared process-tree identities")
    identities = [tuple(item[field] for field in (
        "pid", "process_group_id", "start_ticks",
    )) for item in expected_identities]
    require(len(set(identities)) == len(identities) and
            len({item["pid"] for item in expected_identities}) ==
            len(expected_identities) and
            len({item["process_group_id"] for item in expected_identities}) == 1,
            "process tree identities alias or span process groups")
    require(len(completed_processes) == len(expected_identities),
            "completed process tree has omitted or extra members")
    by_identity: dict[tuple[int, int, int], _Observation] = {}
    for candidate in completed_processes:
        completed = _require_observation(candidate, "completed-process", nonfixture=False)
        process = completed.evidence["process"]
        identity = tuple(process[field] for field in (
            "pid", "process_group_id", "start_ticks",
        ))
        require(identity not in by_identity and
                completed.evidence["termination"]["kind"] == "signal" and
                completed.evidence["termination"]["value"] in {
                    int(signal.SIGTERM), int(signal.SIGKILL),
                } and completed.evidence["reaped"] is True and
                completed.evidence["proc_absent_after_reap"] is True,
                "process tree member was not killed and reaped")
        by_identity[identity] = completed
    require(set(by_identity) == set(identities),
            "completed process tree identities differ from predeclaration")
    root_pid = expected_identities[0]["pid"]
    member_pids = {item["pid"] for item in expected_identities}
    for identity in identities[1:]:
        process = by_identity[identity].evidence["process"]
        parent = process["parent_pid"]
        seen: set[int] = set()
        while parent != root_pid:
            require(parent in member_pids and parent not in seen,
                    "predeclared process members do not form one owned tree")
            seen.add(parent)
            parent_identity = next(
                item for item in identities if item[0] == parent
            )
            parent = by_identity[parent_identity].evidence["process"]["parent_pid"]
    return _make_observation("killed-process-tree", {
        "root_identity": copy.deepcopy(expected_identities[0]),
        "ordered_identities": copy.deepcopy(expected_identities),
        "members": [copy.deepcopy(by_identity[item].evidence) for item in identities],
        "single_owned_process_group": True,
        "all_members_killed_reaped_and_proc_absent": True,
    }, all(by_identity[item].nonfixture for item in identities))


def authenticate_coordinator_lifecycle(
    *, pin: LiveProcessPin, port_observation: _Observation,
    completed_process: _Observation, environments: _Observation,
    expected_argv: list[str],
) -> _Observation:
    """Bind the exact DMTCP coordinator process, socket, and termination."""
    port = _require_observation(port_observation, "coordinator-port", nonfixture=False)
    completed = _require_observation(completed_process, "completed-process", nonfixture=False)
    environment_observation = _require_observation(
        environments, "challenged-environments", nonfixture=False,
    )
    process = completed.evidence["process"]
    identity = {field: process[field] for field in (
        "pid", "process_group_id", "start_ticks",
    )}
    require(pin.completed and process == pin.evidence and
            port.evidence["process_identity"] == identity and
            process["executable"] == DMTCP_ROLE_PATHS["coordinator"] and
            isinstance(expected_argv, list) and process["argv"] == expected_argv and
            process["environment"] == environment_observation.evidence["combined"] and
            completed.evidence["termination"] in (
                {"kind": "exit", "value": 0},
                {"kind": "signal", "value": int(signal.SIGTERM)},
            ), "coordinator executable/argv/env/port/termination is not exact")
    return _make_observation("coordinator-lifecycle", {
        "process": copy.deepcopy(process),
        "exec_gate": copy.deepcopy(pin.gate_evidence),
        "port": port.evidence["port"],
        "socket_inode": port.evidence["socket_inode"],
        "termination": copy.deepcopy(completed.evidence["termination"]),
        "reaped": True,
    }, pin.nonfixture and pin.gated_by_authenticator and
       pin.gate_evidence is not None and pin.gate_evidence.get("released") is True and
       port.nonfixture and completed.nonfixture and
       environment_observation.nonfixture)


class RestartObserver:
    """Hold and rehash the exact positional image set across a restart."""

    def __init__(
        self, *, launcher_pin: LiveProcessPin, publication: PublicationPin,
        filesystem: AnchoredFilesystem, coordinator_port: _Observation,
        challenges: dict[str, Any], environments: _Observation,
    ) -> None:
        require(isinstance(launcher_pin, LiveProcessPin) and
                launcher_pin._seal is _OBSERVATION_SEAL and not launcher_pin.completed,
                "restart launcher is not live")
        self.challenges = validate_controller_challenges(copy.deepcopy(challenges))
        self.port = _require_observation(
            coordinator_port, "coordinator-port", nonfixture=False,
        )
        self.environments = _require_observation(
            environments, "challenged-environments", nonfixture=False,
        )
        self.publication = publication
        self.filesystem = filesystem
        self.launcher_pin = launcher_pin
        self.gate_was_held_at_begin = (
            launcher_pin.gated_by_authenticator and launcher_pin.trace_attached and
            launcher_pin.gate_evidence is not None and
            launcher_pin.gate_evidence.get("released") is False
        )
        self.before = rehash_checkpoint_for_restart(
            publication, filesystem=filesystem,
        )
        expected_argv = [
            DMTCP_ROLE_PATHS["restart"], "--join-coordinator", "--coord-port",
            str(self.port.evidence["port"]),
            *publication.evidence["ordered_restart_image_argv"],
        ]
        require(launcher_pin.evidence["executable"] ==
                DMTCP_ROLE_PATHS["restart"] and
                launcher_pin.evidence["argv"] == expected_argv and
                launcher_pin.evidence["environment"] ==
                self.environments.evidence["combined"] and
                publication.evidence["challenge_id"] ==
                self.challenges["challenge_id"] and
                publication.evidence["checkpoint_token"] ==
                self.challenges["checkpoint_token"],
                "restart executable, ordered positional images, or env is spliced")

    def release_launcher(self) -> None:
        require(self.gate_was_held_at_begin,
                "restart launcher did not begin behind an exec gate")
        release_exec_gated_process(self.launcher_pin)

    def finish(
        self, *, completed_launcher: _Observation, resumed_phase: _Observation,
    ) -> _Observation:
        launcher = _require_observation(
            completed_launcher, "completed-process", nonfixture=False,
        )
        resume = _require_observation(resumed_phase, "phase", nonfixture=False)
        require(self.launcher_pin.completed and
                launcher.evidence["process"] == self.launcher_pin.evidence and
                resume.evidence["phase"] == "resume" and
                resume.evidence.get("receipt_observation_scope") ==
                "controller-supplied-bytes-received-and-timestamped-by-parent" and
                resume.evidence["challenge_name"] == "resume_nonce" and
                resume.evidence["challenge_value"] ==
                self.challenges["resume_nonce"],
                "restart completion or RESUMED handshake is not authentic")
        after = rehash_checkpoint_for_restart(
            self.publication, filesystem=self.filesystem,
        )
        require(self.before.evidence["images"] == after.evidence["images"] and
                self.before.evidence["ordered_restart_image_argv"] ==
                after.evidence["ordered_restart_image_argv"],
                "checkpoint images changed across restart lifecycle")
        return _make_observation("restart-lifecycle", {
            "launcher": copy.deepcopy(launcher.evidence),
            "exec_gate": copy.deepcopy(self.launcher_pin.gate_evidence),
            "restarted_controller": copy.deepcopy(
                resume.evidence["controller"]["process"],
            ),
            "resumed_receipt_count": 1,
            "ordered_manifest_sha256": self.publication.evidence["ordered_manifest_sha256"],
            "coordinator_port": self.port.evidence["port"],
            "ordered_restart_image_argv": copy.deepcopy(
                self.before.evidence["ordered_restart_image_argv"],
            ),
            "pre_restart_images": copy.deepcopy(self.before.evidence["images"]),
            "post_restart_images": copy.deepcopy(after.evidence["images"]),
        }, self.launcher_pin.nonfixture and launcher.nonfixture and
           resume.nonfixture and self.before.nonfixture and after.nonfixture and
           self.environments.nonfixture and self.gate_was_held_at_begin and
           self.launcher_pin.gate_evidence is not None and
           self.launcher_pin.gate_evidence.get("released") is True)


def assemble_unapproved_candidate(
    *, challenges: dict[str, Any], dmtcp_authority: _Observation,
    environments: _Observation, resource_limits: _Observation, kernel: _Observation,
    phases: list[_Observation], coordinator: _Observation,
    origin_process_tree: _Observation, publication: PublicationPin,
    restart: _Observation,
) -> dict[str, Any]:
    """Emit only an unapproved candidate after bounded local observations."""
    challenges = validate_controller_challenges(copy.deepcopy(challenges))
    dmtcp = _require_observation(dmtcp_authority, "bound-dmtcp-authority")
    environment_observation = _require_observation(environments, "challenged-environments")
    limits = _require_observation(resource_limits, "resource-limits")
    kernel_observation = _require_observation(kernel, "kernel")
    coordinator_observation = _require_observation(coordinator, "coordinator-lifecycle")
    tree = _require_observation(origin_process_tree, "killed-process-tree")
    restart_observation = _require_observation(restart, "restart-lifecycle")
    require(isinstance(publication, PublicationPin) and
            publication._seal is _OBSERVATION_SEAL and publication.nonfixture and
            publication.directory_fd >= 0,
            "missing live nonfixture publication pin")
    require(isinstance(phases, list) and len(phases) == len(PHASES),
            "lifecycle evidence omits a required phase")
    phase_tokens = [
        _require_observation(item, "phase") for item in phases
    ]
    require([item.evidence["phase"] for item in phase_tokens] == list(PHASES),
            "lifecycle phases are absent, duplicated, or reordered")
    with AnchoredFilesystem("/") as final_filesystem:
        for item in phase_tokens:
            require(item.evidence.get("filesystem_root") == "/",
                    "phase raw files do not use the nonfixture root anchor")
            for name in ("cadence_file", "event_file"):
                prior = item.evidence.get(name)
                require(isinstance(prior, dict),
                        "phase omits an immutable raw evidence file")
                authority = {
                    field: prior[field] for field in (
                        "bytes", "sha256", "md5", "mode", "uid", "gid",
                    )
                }
                current = final_filesystem.authenticate_file(
                    prior["path"], authority, immutable=True,
                )
                require(current == prior,
                        "phase raw evidence changed before final assembly")
    with AnchoredFilesystem(publication.filesystem_root) as final_filesystem:
        final_images = rehash_checkpoint_for_restart(
            publication, filesystem=final_filesystem,
        )
    require(final_images.evidence["images"] ==
            restart_observation.evidence["post_restart_images"],
            "published images changed after restart completion")
    prior_end = 0
    all_event_nonces: set[str] = set()
    for item in phase_tokens:
        phase = item.evidence["phase"]
        challenge_name, challenge_value = phase_challenge(challenges, phase)
        expected_environment = environment_observation.evidence[
            "runtime" if phase in {"pilot", "clean-1", "clean-2"}
            else "combined"
        ]
        process = item.evidence["controller"]["process"]
        begin = item.evidence.get("begin_monotonic_ns")
        end = item.evidence.get("end_monotonic_ns")
        event_nonces = item.evidence.get("event_nonces")
        require(item.evidence.get("challenge_id") == challenges["challenge_id"] and
                item.evidence.get("challenge_name") == challenge_name and
                item.evidence.get("challenge_value") == challenge_value and
                process.get("environment") == expected_environment and
                item.evidence.get("resource_limits") == limits.evidence and
                item.evidence.get("receipt_observation_scope") ==
                "controller-supplied-bytes-received-and-timestamped-by-parent" and
                item.evidence.get("post_ready_action_receipt_count") == 0 and
                isinstance(item.evidence.get("exec_gate"), dict) and
                item.evidence["exec_gate"].get("released") is True and
                process.get("vdso_sha256") == dmtcp.evidence["vdso_sha256"] and
                process.get("kernel") == kernel_observation.evidence and
                type(begin) is int and type(end) is int and
                prior_end < begin < end and isinstance(event_nonces, list) and
                event_nonces and len(event_nonces) == len(set(event_nonces)) and
                all(isinstance(nonce, str) and HEX32.fullmatch(nonce)
                    for nonce in event_nonces) and
                all_event_nonces.isdisjoint(event_nonces),
                "phase challenge, environment, kernel, or vDSO is spliced")
        prior_end = end
        all_event_nonces.update(event_nonces)
    identities = {
        item.evidence["phase"]: tuple(
            item.evidence["controller"]["process"][field]
            for field in ("pid", "process_group_id", "start_ticks")
        ) for item in phase_tokens
    }
    critical = [identities[name] for name in (
        "origin", "clean-1", "clean-2", "resume",
    )]
    coordinator_identity = tuple(
        coordinator_observation.evidence["process"][field]
        for field in ("pid", "process_group_id", "start_ticks")
    )
    require(len(set(critical)) == 4 and coordinator_identity not in set(critical),
            "origin, clean attempts, resume, or coordinator reuse an identity")
    resume_process = restart_observation.evidence["restarted_controller"]
    dmtcp_roles = {
        item["role"]: item for item in dmtcp.evidence["executables"]
    }
    coordinator_process = coordinator_observation.evidence["process"]
    restart_launcher = restart_observation.evidence["launcher"]["process"]
    require(tuple(resume_process[field] for field in (
                "pid", "process_group_id", "start_ticks",
            )) == identities["resume"] and
            tree.evidence["root_identity"] == {
                field: phase_tokens[1].evidence["controller"]["process"][field]
                for field in ("pid", "process_group_id", "start_ticks")
            } and
            restart_observation.evidence["ordered_manifest_sha256"] ==
            publication.evidence["ordered_manifest_sha256"] and
            publication.evidence.get("resource_limits") == limits.evidence and
            restart_observation.evidence.get("coordinator_port") ==
            coordinator_observation.evidence.get("port") and
            dmtcp.evidence.get("kernel") == kernel_observation.evidence and
            coordinator_observation.evidence["process"].get("environment") ==
            environment_observation.evidence["combined"] and
            coordinator_observation.evidence["process"].get("vdso_sha256") ==
            dmtcp.evidence["vdso_sha256"] and
            coordinator_observation.evidence["process"].get("kernel") ==
            kernel_observation.evidence and
            coordinator_process.get("executable") ==
            DMTCP_ROLE_PATHS["coordinator"] and
            coordinator_process.get("executable_device") ==
            dmtcp_roles["coordinator"]["device"] and
            coordinator_process.get("executable_inode") ==
            dmtcp_roles["coordinator"]["inode"] and
            coordinator_observation.evidence.get("exec_gate", {}).get("released") is True and
            restart_observation.evidence.get("exec_gate", {}).get("released") is True and
            restart_launcher.get("executable") == DMTCP_ROLE_PATHS["restart"] and
            restart_launcher.get("executable_device") ==
            dmtcp_roles["restart"]["device"] and
            restart_launcher.get("executable_inode") ==
            dmtcp_roles["restart"]["inode"] and
            restart_launcher.get("environment") ==
            environment_observation.evidence["combined"] and
            restart_launcher.get("vdso_sha256") ==
            dmtcp.evidence["vdso_sha256"] and
            restart_launcher.get("kernel") ==
            kernel_observation.evidence,
            "restart, origin tree, phase, or publication evidence is spliced")
    evidence = {
        "schema": 1,
        "kind": EVIDENCE_KIND,
        "status": "controller-asserted-unapproved",
        "authentication_scope": CONTROLLER_ASSERTION_SCOPE,
        "challenge_id": challenges["challenge_id"],
        "controller_challenges_sha256": canonical_sha256(challenges),
        "dmtcp_authority": copy.deepcopy(dmtcp.evidence),
        "environments": copy.deepcopy(environment_observation.evidence),
        "resource_limits": copy.deepcopy(limits.evidence),
        "kernel": copy.deepcopy(kernel_observation.evidence),
        "phases": [copy.deepcopy(item.evidence) for item in phase_tokens],
        "coordinator": copy.deepcopy(coordinator_observation.evidence),
        "origin_process_tree": copy.deepcopy(tree.evidence),
        "checkpoint_publication": copy.deepcopy(publication.evidence),
        "restart": copy.deepcopy(restart_observation.evidence),
        "unclosed_trust_boundaries": list(UNCLOSED_TRUST_BOUNDARIES),
        "lifecycle_complete": False,
        "os_evidence_authenticated": False,
        "runtime_qualified": False,
        "checkpoint_protocol_qualified": False,
        "s2_approved": False,
        "s3_approved": False,
        "release_promoted": False,
        "pft_used": False,
    }
    evidence["candidate_payload_sha256"] = canonical_sha256(evidence)
    return validate_unapproved_candidate(evidence)


def validate_unapproved_candidate(value: object) -> dict[str, Any]:
    """Validate the exact canonical fail-closed candidate contract."""
    fields = {
        "schema", "kind", "status", "authentication_scope", "challenge_id",
        "controller_challenges_sha256", "dmtcp_authority", "environments",
        "resource_limits", "kernel", "phases", "coordinator",
        "origin_process_tree", "checkpoint_publication", "restart",
        "unclosed_trust_boundaries", "lifecycle_complete",
        "os_evidence_authenticated", "runtime_qualified",
        "checkpoint_protocol_qualified", "s2_approved", "s3_approved",
        "release_promoted", "pft_used", "candidate_payload_sha256",
    }
    require(isinstance(value, dict) and set(value) == fields and
            type(value.get("schema")) is int and value["schema"] == 1 and
            value.get("kind") == EVIDENCE_KIND and
            value.get("status") == "controller-asserted-unapproved" and
            value.get("authentication_scope") == CONTROLLER_ASSERTION_SCOPE and
            value.get("unclosed_trust_boundaries") ==
            list(UNCLOSED_TRUST_BOUNDARIES) and
            all(value.get(field) is False for field in (
                "lifecycle_complete", "os_evidence_authenticated",
                "runtime_qualified", "checkpoint_protocol_qualified",
                "s2_approved", "s3_approved", "release_promoted", "pft_used",
            )), "checkpoint OS candidate overclaims trust or approval")
    _hex(value.get("challenge_id"), HEX64, "candidate challenge ID")
    _hex(value.get("controller_challenges_sha256"), HEX64,
         "candidate challenges SHA-256")
    dmtcp = value.get("dmtcp_authority")
    require(isinstance(dmtcp, dict), "candidate DMTCP observation is malformed")
    for group in ("executables", "injected_libraries", "elf_closure"):
        items = dmtcp.get(group)
        require(isinstance(items, list), f"candidate {group} is malformed")
        for item in items:
            require(isinstance(item, dict), f"candidate {group} item is malformed")
            _absolute_to_relative(item.get("path"), f"candidate {group} path")
    publication = value.get("checkpoint_publication")
    require(isinstance(publication, dict), "candidate publication is malformed")
    published_absolute = _absolute_to_relative(
        publication.get("published_directory"),
        "candidate held publication path",
    )
    published_relative = _safe_relative(
        publication.get("published_relative_directory"),
        "candidate relative publication path",
    )
    absolute_parts = PurePosixPath(published_absolute).parts
    relative_parts = PurePosixPath(published_relative).parts
    require(absolute_parts[-len(relative_parts):] == relative_parts,
            "candidate absolute publication path omits the direct layout")
    atomic = publication.get("direct_protocol_atomic_publication")
    require(isinstance(atomic, dict), "candidate direct publication is malformed")
    for name in ("staging_path", "published_path"):
        _safe_relative(atomic.get(name), f"candidate direct {name}")
    direct_files = publication.get("direct_protocol_image_files")
    require(isinstance(direct_files, list), "candidate direct image files malformed")
    for item in direct_files:
        require(isinstance(item, dict) and set(item) == {
                    "path", "bytes", "sha256", "md5",
                } and type(item.get("bytes")) is int and item["bytes"] >= 0,
                "candidate direct image item malformed")
        _safe_relative(item.get("path"), "candidate direct image path")
        _hex(item.get("sha256"), HEX64, "candidate direct image SHA-256")
        _hex(item.get("md5"), HEX32, "candidate direct image MD5")
    ordered_images = publication.get("ordered_images")
    require(isinstance(ordered_images, list) and
            len(ordered_images) == len(direct_files),
            "candidate ordered checkpoint images are malformed")
    for direct, held in zip(direct_files, ordered_images, strict=True):
        require(isinstance(held, dict) and set(held) == {
                    "path", "authority", "identity",
                } and held.get("path") == direct["path"] and
                isinstance(held.get("authority"), dict) and all(
                    held["authority"].get(field) == direct[field]
                    for field in ("bytes", "sha256", "md5")
                ), "candidate held and direct checkpoint images differ")
        _safe_relative(held["path"], "candidate held image path")
    manifest_sha256 = direct_ordered_manifest_sha256(direct_files)
    require(publication.get("ordered_manifest_sha256") == manifest_sha256 and
            published_relative == f"checkpoints/{manifest_sha256}" and
            atomic.get("published_path") == published_relative and
            PurePosixPath(atomic.get("staging_path", "")).parts[:1] ==
            ("staging",),
            "candidate checkpoint manifest or direct layout differs")
    for phase in value.get("phases", []):
        require(isinstance(phase, dict), "candidate phase is malformed")
        for name in ("cadence_file", "event_file"):
            item = phase.get(name)
            require(isinstance(item, dict), "candidate phase file is malformed")
            _safe_relative(item.get("path"), "candidate phase file path")
        process = phase.get("controller", {}).get("process", {})
        _absolute_to_relative(
            process.get("executable"), "candidate phase executable",
        )
    restart = value.get("restart")
    require(isinstance(restart, dict), "candidate restart is malformed")
    argv = restart.get("ordered_restart_image_argv")
    require(isinstance(argv, list) and argv,
            "candidate restart image argv is malformed")
    for item in argv:
        _safe_relative(item, "candidate restart image argv")
    require(argv == [
                f"{published_relative}/{item['path']}" for item in direct_files
            ], "candidate restart image argv differs from direct image order")
    launcher = restart.get("launcher", {}).get("process", {})
    _absolute_to_relative(
        launcher.get("executable"), "candidate restart executable",
    )
    coordinator = value.get("coordinator", {}).get("process", {})
    _absolute_to_relative(
        coordinator.get("executable"), "candidate coordinator executable",
    )
    digest = _hex(value.get("candidate_payload_sha256"), HEX64,
                  "candidate payload SHA-256")
    payload = copy.deepcopy(value)
    del payload["candidate_payload_sha256"]
    require(digest == canonical_sha256(payload),
            "checkpoint OS candidate payload digest differs")
    return value


def decode_unapproved_candidate(data: bytes) -> dict[str, Any]:
    return validate_unapproved_candidate(
        _decode_exact_json(data, "checkpoint OS observation candidate")
    )
