#!/usr/bin/python3
"""Read-only fail-closed gate for the final-head canonical CakeML bootstrap."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import re
import stat
import subprocess
import sys


GIT_ENVIRONMENT = {
    "PATH": "/usr/bin:/bin",
    "LC_ALL": "C",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_NO_REPLACE_OBJECTS": "1",
}
GIT_OPTIONS = (
    "-c", "core.fsmonitor=false",
    "-c", "core.untrackedCache=false",
    "-c", "core.preloadIndex=false",
)
REPLAY_STAGES = (
    ("cakeml-heap", "misc", "cakeml-heap",
     "00-cakeml-heap.time", "00-cakeml-heap.log"),
    ("cake_compile_heap", "cv_translator", "cake_compile_heap",
     "01-cake-compile-heap.time", "01-cake-compile-heap.log"),
    ("compiler64ProgTheory.uo", "compiler/bootstrap/translation",
     "compiler64ProgTheory.uo", "02-compiler64Prog.time",
     "02-compiler64Prog.log"),
    ("x64BootstrapTheory.uo", "compiler/bootstrap/compilation/x64/64",
     "x64BootstrapTheory.uo", "03-x64Bootstrap.time",
     "03-x64Bootstrap.log"),
    ("x64BootstrapProofTheory.uo",
     "compiler/bootstrap/compilation/x64/64/proofs",
     "x64BootstrapProofTheory.uo", "04-x64BootstrapProof.time",
     "04-x64BootstrapProof.log"),
)
TIME_RECEIPTS = tuple(stage[3] for stage in REPLAY_STAGES)
TIME_TARGETS = tuple(stage[2] for stage in REPLAY_STAGES)
TIME_FIELDS = (
    "Command being timed",
    "User time (seconds)",
    "System time (seconds)",
    "Percent of CPU this job got",
    "Elapsed (wall clock) time (h:mm:ss or m:ss)",
    "Average shared text size (kbytes)",
    "Average unshared data size (kbytes)",
    "Average stack size (kbytes)",
    "Average total size (kbytes)",
    "Maximum resident set size (kbytes)",
    "Average resident set size (kbytes)",
    "Major (requiring I/O) page faults",
    "Minor (reclaiming a frame) page faults",
    "Voluntary context switches",
    "Involuntary context switches",
    "Swaps",
    "File system inputs",
    "File system outputs",
    "Socket messages sent",
    "Socket messages received",
    "Signals delivered",
    "Page size (bytes)",
    "Exit status",
)
CAKEML_POSTCONDITIONS = (
    "misc/cakeml-heap",
    "cv_translator/cake_compile_heap",
    "compiler/bootstrap/translation/.hol/objs/compiler64ProgTheory.uo",
    "compiler/bootstrap/compilation/x64/64/.hol/objs/x64BootstrapTheory.uo",
    "compiler/bootstrap/compilation/x64/64/cake.S",
    "compiler/bootstrap/compilation/x64/64/config_enc_str.txt",
    (
        "compiler/bootstrap/compilation/x64/64/proofs/.hol/objs/"
        "x64BootstrapProofTheory.uo"
    ),
)
REPLAY_CONTROLLER_RELATIVE = "scripts/run-canonical-bootstrap-replay.sh"
REPLAY_GATE_RELATIVE = "scripts/check-canonical-bootstrap-gate.py"
PRISTINE_PREFLIGHT_RELATIVE = "pristine-preflight.json"
TERMINAL_MANIFEST_RELATIVE = "terminal-manifest.json"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
PREFLIGHT_KIND = "canonical-cakeml-cold-pristine-preflight-v2"
MANIFEST_KIND = "canonical-cakeml-cold-terminal-manifest-v2"
SMALL_FILE_MAX_BYTES = 1024 * 1024
PROC_STAT_MAX_BYTES = 4096
PROC_CMDLINE_MAX_BYTES = 64 * 1024
CONTROLLER_SOURCE_FD = 9
UINT64_MAX = (1 << 64) - 1


class GateError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateError(message)


def ordinary_exact_directory(path: Path, label: str) -> Path:
    require(path.is_absolute(), f"{label} must be absolute")
    resolved = path.resolve(strict=True)
    require(resolved == path, f"{label} contains a symlink or alias: {path}")
    metadata = path.lstat()
    require(stat.S_ISDIR(metadata.st_mode), f"{label} is not an ordinary directory")
    return path


def stable_file_bytes(
    path: Path,
    label: str,
    *,
    nonempty: bool = True,
    max_bytes: int = SMALL_FILE_MAX_BYTES,
) -> bytes:
    require(type(max_bytes) is int and max_bytes > 0,
            f"invalid {label} byte cap")
    try:
        descriptor = os.open(
            path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW |
            getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as error:
        raise GateError(f"could not open ordinary {label}: {path}") from error
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode), f"{label} is not an ordinary file")
        require(before.st_size <= max_bytes,
                f"{label} exceeds size cap: {path}")
        chunks = []
        total = 0
        while block := os.read(
            descriptor, min(1024 * 1024, max_bytes + 1 - total),
        ):
            chunks.append(block)
            total += len(block)
            require(total <= max_bytes, f"{label} exceeds size cap: {path}")
        after = os.fstat(descriptor)
        named = path.stat(follow_symlinks=False)
    finally:
        os.close(descriptor)
    value = b"".join(chunks)
    require((before.st_dev, before.st_ino, before.st_mode, before.st_nlink,
             before.st_size,
             before.st_mtime_ns, before.st_ctime_ns) ==
            (after.st_dev, after.st_ino, after.st_mode, after.st_nlink,
             after.st_size,
             after.st_mtime_ns, after.st_ctime_ns) and
            (named.st_dev, named.st_ino, named.st_mode, named.st_nlink) ==
            (after.st_dev, after.st_ino, after.st_mode, after.st_nlink) and
            len(value) == before.st_size,
            f"{label} changed while reading: {path}")
    require(not nonempty or value, f"empty {label}: {path}")
    return value


def stable_file_record(
    path: Path,
    label: str,
    *,
    relative: str,
    nonempty: bool = True,
) -> dict[str, object]:
    try:
        descriptor = os.open(
            path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW |
            getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as error:
        raise GateError(f"could not open ordinary {label}: {path}") from error
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode), f"{label} is not an ordinary file")
        digest = hashlib.sha256()
        total = 0
        while block := os.read(descriptor, 1024 * 1024):
            digest.update(block)
            total += len(block)
        after = os.fstat(descriptor)
        named = path.stat(follow_symlinks=False)
    finally:
        os.close(descriptor)
    projection = lambda value: (
        value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
        value.st_size, value.st_mtime_ns, value.st_ctime_ns,
    )
    require(projection(before) == projection(after) == projection(named) and
            total == before.st_size,
            f"{label} changed while hashing: {path}")
    require(not nonempty or total > 0, f"empty {label}: {path}")
    return {"relative": relative, "bytes": total, "sha256": digest.hexdigest()}


def exact_relative_file_record(
    root: Path,
    relative: str,
    label: str,
    *,
    nonempty: bool = True,
) -> dict[str, object]:
    require(relative and not relative.startswith("/") and
            all(component not in {"", ".", ".."}
                for component in relative.split("/")),
            f"unsafe {label} relative path")
    current = root
    components = relative.split("/")
    for component in components[:-1]:
        current = current / component
        metadata = current.lstat()
        require(stat.S_ISDIR(metadata.st_mode),
                f"{label} ancestor is not an ordinary directory: {current}")
    return stable_file_record(
        root / relative, label, relative=relative, nonempty=nonempty,
    )


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def no_duplicate_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_canonical_json(path: Path, label: str) -> tuple[dict[str, object], bytes]:
    value = stable_file_bytes(path, label, max_bytes=SMALL_FILE_MAX_BYTES)
    try:
        parsed = json.loads(value.decode("utf-8"), object_pairs_hook=no_duplicate_object)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise GateError(f"malformed {label}: {path}") from error
    require(isinstance(parsed, dict), f"{label} is not a JSON object")
    require(canonical_json_bytes(parsed) == value, f"{label} is not canonical JSON")
    return parsed, value


def write_exclusive(path: Path, value: bytes) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
        getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW,
        0o600,
    )
    try:
        offset = 0
        while offset < len(value):
            count = os.write(descriptor, value[offset:])
            require(count > 0, f"short write publishing {path}")
            offset += count
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def git_bytes(root: Path, *arguments: str) -> bytes:
    process = subprocess.run(
        ["/usr/bin/git", *GIT_OPTIONS, "-C", str(root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=GIT_ENVIRONMENT,
    )
    require(
        process.returncode == 0,
        f"Git check failed for {root}: {process.stderr.decode(errors='replace').strip()}",
    )
    return process.stdout


def git_output(root: Path, *arguments: str) -> str:
    return git_bytes(root, *arguments).decode("utf-8", errors="strict")


def split_nul(value: bytes) -> list[bytes]:
    if not value:
        return []
    require(value.endswith(b"\0"), "Git NUL record stream is unterminated")
    return value[:-1].split(b"\0")


def git_blob_oid(value: bytes, object_format: str) -> str:
    require(object_format in {"sha1", "sha256"},
            f"unsupported Git object format: {object_format}")
    digest = hashlib.new(object_format)
    digest.update(f"blob {len(value)}\0".encode("ascii"))
    digest.update(value)
    return digest.hexdigest()


def stable_blob_oid(path: bytes, mode: str, object_format: str) -> str:
    display = os.fsdecode(path)
    before = os.lstat(path)
    stable_fields = lambda value: (
        value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
        value.st_size, value.st_mtime_ns, value.st_ctime_ns,
    )
    if mode in {"100644", "100755"}:
        require(stat.S_ISREG(before.st_mode),
                f"tracked path is not an ordinary file: {display}")
        observed_mode = "100755" if before.st_mode & stat.S_IXUSR else "100644"
        require(observed_mode == mode,
                f"tracked file Git mode mismatch: {display}")
        try:
            descriptor = os.open(
                path, os.O_RDONLY | os.O_NOFOLLOW |
                getattr(os, "O_CLOEXEC", 0),
            )
        except OSError as error:
            raise GateError(f"could not open tracked file: {display}") from error
        try:
            opened = os.fstat(descriptor)
            require(stable_fields(opened) == stable_fields(before),
                    f"tracked file changed before reading: {display}")
            digest = hashlib.new(object_format)
            digest.update(f"blob {opened.st_size}\0".encode("ascii"))
            total = 0
            while value := os.read(descriptor, 1024 * 1024):
                digest.update(value)
                total += len(value)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        named = os.lstat(path)
        require(total == opened.st_size and
                stable_fields(opened) == stable_fields(after) ==
                stable_fields(named),
                f"tracked file changed while reading: {display}")
        return digest.hexdigest()
    if mode == "120000":
        require(stat.S_ISLNK(before.st_mode),
                f"tracked path is not a symbolic link: {display}")
        value = os.readlink(path)
        require(isinstance(value, bytes), "byte-path readlink returned text")
        after = os.lstat(path)
        require(stable_fields(before) == stable_fields(after),
                f"tracked symbolic link changed while reading: {display}")
        return git_blob_oid(value, object_format)
    raise GateError(f"unsupported tracked Git mode {mode}: {display}")


def parse_tree_records(value: bytes) -> tuple[list[tuple[str, str, str, bytes]],
                                               dict[bytes, tuple[str, str]]]:
    records = []
    leaves = {}
    for record in split_nul(value):
        try:
            metadata, path = record.split(b"\t", 1)
            mode_bytes, object_type_bytes, oid_bytes = metadata.split(b" ", 2)
            mode = mode_bytes.decode("ascii")
            object_type = object_type_bytes.decode("ascii")
            oid = oid_bytes.decode("ascii")
        except (ValueError, UnicodeError) as error:
            raise GateError("malformed Git tree record") from error
        components = path.split(b"/")
        require(path and not path.startswith(b"/") and
                all(component not in {b"", b".", b".."}
                    for component in components),
                "unsafe tracked Git path")
        records.append((mode, object_type, oid, path))
        if object_type != "tree":
            require(path not in leaves, "duplicate tracked Git path")
            leaves[path] = (mode, oid)
    return records, leaves


def parse_index_records(value: bytes) -> dict[bytes, tuple[str, str]]:
    result = {}
    for record in split_nul(value):
        try:
            metadata, path = record.split(b"\t", 1)
            mode_bytes, oid_bytes, stage_bytes = metadata.split(b" ", 2)
            mode = mode_bytes.decode("ascii")
            oid = oid_bytes.decode("ascii")
            stage = stage_bytes.decode("ascii")
        except (ValueError, UnicodeError) as error:
            raise GateError("malformed Git index record") from error
        require(stage == "0", f"non-stage-zero Git index entry: {os.fsdecode(path)}")
        require(path not in result, "duplicate Git index path")
        result[path] = (mode, oid)
    return result


def require_plain_index_tags(root: Path, leaves: dict[bytes, tuple[str, str]]) -> None:
    expected_paths = set(leaves)
    for option, label in (("-t", "skip-worktree"),
                          ("-v", "assume-unchanged"),
                          ("-f", "fsmonitor-valid")):
        observed_paths = set()
        for record in split_nul(git_bytes(root, "ls-files", option, "-z")):
            require(len(record) >= 3 and record[1:2] == b" ",
                    f"malformed Git {label} index tag")
            tag = record[:1]
            path = record[2:]
            require(tag == b"H",
                    f"special Git {label} index state: {os.fsdecode(path)}")
            observed_paths.add(path)
        require(observed_paths == expected_paths,
                f"Git {label} index path set differs from pinned tree")
    require(git_bytes(root, "ls-files", "--resolve-undo", "-z") == b"",
            "Git resolve-undo index state is present")


def validate_exact_git_tree(
    root: Path,
    expected_head: str,
    label: str,
    *,
    require_no_ignored: bool = False,
) -> dict[str, object]:
    require(git_output(root, "rev-parse", "--show-toplevel").strip() == str(root),
            f"{label} is not the exact Git worktree root")
    observed = git_output(root, "rev-parse", "HEAD").strip()
    require(observed == expected_head, f"{label} head mismatch: {observed}")
    require(git_output(root, "replace", "-l") == "",
            f"{label} Git replacement refs are present")
    graft_value = git_output(root, "rev-parse", "--git-path", "info/grafts").strip()
    graft_path = Path(graft_value)
    if not graft_path.is_absolute():
        graft_path = root / graft_path
    if os.path.lexists(graft_path):
        graft_metadata = graft_path.lstat()
        require(stat.S_ISREG(graft_metadata.st_mode) and
                graft_metadata.st_size == 0,
                f"{label} Git grafts are present")

    tree_oid = git_output(root, "rev-parse", f"{expected_head}^{{tree}}").strip()
    tree_bytes = git_bytes(
        root, "ls-tree", "-r", "-t", "-z", "--full-tree", expected_head,
    )
    records, leaves = parse_tree_records(tree_bytes)
    index = parse_index_records(git_bytes(root, "ls-files", "--stage", "-z"))
    require(index == leaves, f"{label} index differs from pinned commit tree")
    require_plain_index_tags(root, leaves)
    require(git_bytes(root, "ls-files", "--others", "--exclude-standard", "-z") == b"",
            f"{label} has nonignored untracked paths")

    object_format = git_output(root, "rev-parse", "--show-object-format").strip()
    root_bytes = os.fsencode(root)
    for mode, object_type, oid, relative in records:
        path = root_bytes + b"/" + relative
        display = os.fsdecode(path)
        if object_type == "tree":
            metadata = os.lstat(path)
            require(mode == "040000" and stat.S_ISDIR(metadata.st_mode),
                    f"tracked directory type mismatch: {display}")
            continue
        require(object_type == "blob",
                f"unsupported tracked object type {object_type}: {display}")
        require(stable_blob_oid(path, mode, object_format) == oid,
                f"tracked object content differs from pinned commit: {display}")

    ignored = git_bytes(
        root, "ls-files", "--others", "--ignored", "--exclude-standard", "-z",
    )
    ignored_records = split_nul(ignored)
    if require_no_ignored:
        require(not ignored_records, f"{label} contains ignored build products")
    return {
        "head": expected_head,
        "tree": tree_oid,
        "tracked_path_count": len(records),
        "tracked_tree_sha256": hashlib.sha256(tree_bytes).hexdigest(),
        "ignored_untracked_count": len(ignored_records),
        "ignored_untracked_sha256": hashlib.sha256(ignored).hexdigest(),
    }


def validate_git(root: Path, expected_head: str, label: str) -> None:
    validate_exact_git_tree(root, expected_head, label)


def validate_self_authority(project_root: Path, expected_head: str) -> str:
    project_root = ordinary_exact_directory(project_root, "project gate root")
    validate_git(project_root, expected_head, "project gate authority")
    source = Path(__file__).resolve(strict=True)
    require(source.is_relative_to(project_root),
            "project gate source is outside authenticated project root")
    relative = source.relative_to(project_root).as_posix()
    live = stable_file_bytes(source, "project gate source")
    committed = git_output(project_root, "show", f"{expected_head}:{relative}").encode()
    require(live == committed, "project gate source differs from committed blob")
    return expected_head


def source_authority_record(
    project_root: Path,
    project_head: str,
    relative: str,
    label: str,
) -> dict[str, object]:
    source = project_root / relative
    live = stable_file_bytes(source, label)
    committed = git_bytes(project_root, "show", f"{project_head}:{relative}")
    require(live == committed, f"{label} differs from committed authority")
    return {
        "relative": relative,
        "bytes": len(live),
        "sha256": hashlib.sha256(live).hexdigest(),
    }


def read_positive_decimal(path: Path, label: str, maximum: int) -> int:
    try:
        raw = stable_file_bytes(path, label, max_bytes=32)
        require(re.fullmatch(rb"[1-9][0-9]*\n", raw) is not None,
                f"malformed {label}: {path}")
        value = int(raw[:-1])
    except (OSError, UnicodeError, ValueError) as error:
        raise GateError(f"malformed {label}: {path}") from error
    require(1 < value <= maximum, f"malformed {label}: {value}")
    return value


def read_positive_pid(path: Path) -> int:
    return read_positive_decimal(path, "replay controller PID", (1 << 31) - 1)


def bounded_proc_file_bytes(path: Path, label: str, max_bytes: int) -> bytes:
    require(type(max_bytes) is int and max_bytes > 0,
            f"invalid {label} byte cap")
    try:
        descriptor = os.open(
            path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW |
            getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as error:
        raise GateError(f"could not open {label}: {path}") from error
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode), f"{label} is not a regular proc file")
        chunks = []
        total = 0
        while block := os.read(
            descriptor, min(4096, max_bytes + 1 - total),
        ):
            chunks.append(block)
            total += len(block)
            require(total <= max_bytes, f"{label} exceeds size cap: {path}")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    require((before.st_dev, before.st_ino, before.st_mode) ==
            (after.st_dev, after.st_ino, after.st_mode),
            f"{label} changed while reading: {path}")
    value = b"".join(chunks)
    require(value, f"empty {label}: {path}")
    return value


def parse_proc_stat_identity(value: bytes) -> dict[str, int]:
    require(len(value) <= PROC_STAT_MAX_BYTES,
            "controller proc stat exceeds size cap")
    try:
        text = value.decode("ascii")
        require(text.endswith("\n") and text.count("\n") == 1,
                "controller proc stat is not one complete line")
        opening = text.index(" (")
        closing = text.rindex(") ")
        require(opening > 0 and closing > opening + 2,
                "controller proc stat command field is malformed")
        pid_text = text[:opening]
        fields = text[closing + 2:-1].split()
        require(len(fields) >= 20,
                "controller proc stat has too few fields")
        require(re.fullmatch(r"[1-9][0-9]*", pid_text) is not None and
                re.fullmatch(r"[1-9][0-9]*", fields[2]) is not None and
                re.fullmatch(r"[1-9][0-9]*", fields[19]) is not None,
                "controller proc stat identity fields are malformed")
        pid = int(pid_text)
        process_group = int(fields[2])
        start_ticks = int(fields[19])
    except (UnicodeError, ValueError) as error:
        raise GateError("malformed controller proc stat") from error
    require(1 < pid <= (1 << 31) - 1 and
            1 < process_group <= (1 << 31) - 1 and
            0 < start_ticks <= UINT64_MAX,
            "controller proc stat identity is outside its domain")
    return {"pid": pid, "pgid": process_group, "start_ticks": start_ticks}


def read_live_process_identity(proc_root: Path, pid: int) -> dict[str, int]:
    require(type(pid) is int and 1 < pid <= (1 << 31) - 1,
            "controller PID is outside its domain")
    value = bounded_proc_file_bytes(
        proc_root / str(pid) / "stat", "controller proc stat", PROC_STAT_MAX_BYTES,
    )
    identity = parse_proc_stat_identity(value)
    require(identity["pid"] == pid, "controller proc stat PID mismatch")
    return identity


def validate_controller_identity_record(value: object) -> dict[str, int]:
    require(type(value) is dict and set(value) == {"pid", "pgid", "start_ticks"},
            "controller identity has unexpected fields")
    assert isinstance(value, dict)
    require(type(value["pid"]) is int and 1 < value["pid"] <= (1 << 31) - 1,
            "controller identity PID is outside its domain")
    require(type(value["pgid"]) is int and 1 < value["pgid"] <= (1 << 31) - 1,
            "controller identity process group is outside its domain")
    require(type(value["start_ticks"]) is int and
            0 < value["start_ticks"] <= UINT64_MAX,
            "controller identity start ticks are outside their domain")
    return {
        "pid": value["pid"],
        "pgid": value["pgid"],
        "start_ticks": value["start_ticks"],
    }


def authenticate_controller_parent(
    proc_root: Path,
    controller_pid: int,
    controller_pgid: int,
    controller_script: Path,
    expected_arguments: tuple[str, ...],
) -> dict[str, int]:
    # This is a same-host process-origin check, not a cryptographic defense
    # against same-UID ptrace/process-memory tampering.  The post-exit gate
    # separately requires the terminal digest retained by its trusted caller.
    require(os.getppid() == controller_pid,
            "internal publication caller is not the recorded controller")
    before = read_live_process_identity(proc_root, controller_pid)
    require(before["pgid"] == controller_pgid,
            "live controller process group mismatch")
    expected_command = (
        "/bin/bash", "-p", str(controller_script), *expected_arguments,
    )
    observed_command = bounded_proc_file_bytes(
        proc_root / str(controller_pid) / "cmdline",
        "controller proc cmdline", PROC_CMDLINE_MAX_BYTES,
    )
    expected_command_bytes = b"\0".join(
        os.fsencode(argument) for argument in expected_command
    ) + b"\0"
    require(observed_command == expected_command_bytes,
            "live controller command line differs from canonical invocation")

    expected_executable = Path("/bin/bash").resolve(strict=True).stat()
    observed_executable = (proc_root / str(controller_pid) / "exe").stat()
    require(stat.S_ISREG(expected_executable.st_mode) and
            (observed_executable.st_dev, observed_executable.st_ino) ==
            (expected_executable.st_dev, expected_executable.st_ino),
            "live controller executable differs from /bin/bash")

    expected_source = controller_script.stat(follow_symlinks=False)
    inherited_source = os.fstat(CONTROLLER_SOURCE_FD)
    parent_source = (
        proc_root / str(controller_pid) / "fd" / str(CONTROLLER_SOURCE_FD)
    ).stat()
    source_projection = lambda value: (
        value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
    )
    require(stat.S_ISREG(expected_source.st_mode) and
            source_projection(expected_source) ==
            source_projection(inherited_source) ==
            source_projection(parent_source),
            "controller source descriptor differs from committed script")
    require((fcntl.fcntl(CONTROLLER_SOURCE_FD, fcntl.F_GETFL) & os.O_ACCMODE) ==
            os.O_RDONLY,
            "controller source descriptor is not read-only")
    after = read_live_process_identity(proc_root, controller_pid)
    require(after == before, "controller identity changed during authentication")
    return before


def read_replay_controller_identity(replay: Path) -> dict[str, int]:
    return validate_controller_identity_record({
        "pid": read_positive_pid(replay / "controller_pid"),
        "pgid": read_positive_decimal(
            replay / "controller_pgid", "replay controller process group",
            (1 << 31) - 1,
        ),
        "start_ticks": read_positive_decimal(
            replay / "controller_start_ticks", "replay controller start ticks",
            UINT64_MAX,
        ),
    })


def live_holmake_pids(proc_root: Path) -> list[int]:
    result = []
    for child in proc_root.iterdir():
        if not child.name.isdigit():
            continue
        try:
            command_name = (child / "comm").read_text(encoding="ascii").strip()
        except (FileNotFoundError, ProcessLookupError):
            continue
        except (PermissionError, UnicodeError, OSError) as error:
            raise GateError(f"could not inspect process name: {child}") from error
        if command_name == "Holmake":
            result.append(int(child.name))
            continue
        try:
            executable = os.readlink(child / "exe")
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError as error:
            raise GateError(f"could not inspect process executable: {child}") from error
        except OSError as error:
            if error.errno in {errno.ENOENT, errno.ESRCH}:
                continue
            raise GateError(f"could not inspect process executable: {child}") from error
        if Path(executable).name == "Holmake":
            result.append(int(child.name))
    return sorted(result)


def process_group_members(proc_root: Path, process_group: int) -> list[int]:
    result = []
    for child in proc_root.iterdir():
        if not child.name.isdigit():
            continue
        try:
            value = (child / "stat").read_text(encoding="ascii")
            fields = value[value.rindex(") ") + 2:].split()
            observed_group = int(fields[2])
        except (FileNotFoundError, ProcessLookupError):
            continue
        except (PermissionError, OSError, UnicodeError, ValueError, IndexError) as error:
            raise GateError(f"could not inspect process group: {child}") from error
        if observed_group == process_group:
            result.append(int(child.name))
    return sorted(result)


def validate_time_receipt(path: Path, hol4: Path, target: str) -> None:
    try:
        lines = stable_file_bytes(
            path, "cold replay time receipt",
        ).decode("utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise GateError(f"could not read cold replay time receipt: {path}") from error
    require(len(lines) == len(TIME_FIELDS) and
            all(line.startswith("\t") for line in lines),
            f"cold replay time receipt field count mismatch: {path}")
    values = []
    for line, expected_field in zip(lines, TIME_FIELDS, strict=True):
        prefix = f"\t{expected_field}: "
        require(line.startswith(prefix),
                f"cold replay time receipt field mismatch: {path}")
        values.append(line[len(prefix):])
    expected_command = f'"{hol4}/bin/Holmake -j1 --mt=1 {target}"'
    require(values[0] == expected_command,
            f"cold replay time command mismatch: {path}")
    require(all(re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value)
                for value in values[1:3]),
            f"cold replay time CPU fields are malformed: {path}")
    require(re.fullmatch(r"[0-9]+%", values[3]) is not None,
            f"cold replay time percent field is malformed: {path}")
    require(re.fullmatch(r"(?:[0-9]+:)?[0-9]+:[0-9]+(?:\.[0-9]+)?", values[4])
            is not None,
            f"cold replay elapsed field is malformed: {path}")
    require(all(re.fullmatch(r"[0-9]+", value) for value in values[5:22]),
            f"cold replay time integer fields are malformed: {path}")
    require(values[22] == "0",
            f"cold replay command did not record exit zero: {path}")


def validate_inherited_limits() -> dict[str, str]:
    observed = {}
    for label, limit in (
        ("cpu", resource.RLIMIT_CPU),
        ("file_size", resource.RLIMIT_FSIZE),
        ("address_space", resource.RLIMIT_AS),
    ):
        soft, _hard = resource.getrlimit(limit)
        require(soft == resource.RLIM_INFINITY,
                f"inherited {label} soft limit is not unlimited: {soft}")
        observed[label] = "unlimited"
    return observed


def validate_replay_controller_authority(
    replay: Path,
    project_root: Path,
    project_head: str,
    cakeml_root: Path,
    cakeml_head: str,
    hol4_root: Path,
    hol4_head: str,
) -> dict[str, object]:
    controller_identity = read_replay_controller_identity(replay)
    sidecars = {
        "controller_project_root": f"{project_root}\n".encode(),
        "controller_project_head": f"{project_head}\n".encode(),
        "controller_script_relative": f"{REPLAY_CONTROLLER_RELATIVE}\n".encode(),
        "gate_script_relative": f"{REPLAY_GATE_RELATIVE}\n".encode(),
        "cakeml_root": f"{cakeml_root}\n".encode(),
        "cakeml_head": f"{cakeml_head}\n".encode(),
        "hol4_root": f"{hol4_root}\n".encode(),
        "hol4_head": f"{hol4_head}\n".encode(),
        "cakeml_ignored_products_preflight": b"none\n",
        "build_parallelism": b"-j1 --mt=1\n",
        "address_space_limit_kib": b"117964800\n",
    }
    for relative, expected in sidecars.items():
        require(stable_file_bytes(
                    replay / relative, f"cold replay {relative}",
                ) == expected,
                f"cold replay {relative} mismatch")
    controller = source_authority_record(
        project_root, project_head, REPLAY_CONTROLLER_RELATIVE,
        "cold replay controller source",
    )
    gate = source_authority_record(
        project_root, project_head, REPLAY_GATE_RELATIVE,
        "cold replay gate source",
    )
    require(stable_file_bytes(
                replay / "controller_script_sha256",
                "cold replay controller source digest",
            ) == f"{controller['sha256']}\n".encode(),
            "cold replay controller source digest mismatch")
    require(stable_file_bytes(
                replay / "gate_script_sha256",
                "cold replay gate source digest",
            ) == f"{gate['sha256']}\n".encode(),
            "cold replay gate source digest mismatch")
    return {
        "controller": controller,
        "gate": gate,
        "controller_identity": controller_identity,
    }


def tracked_summary_only(value: dict[str, object]) -> dict[str, object]:
    return {
        key: value[key]
        for key in ("head", "tree", "tracked_path_count", "tracked_tree_sha256")
    }


def build_pristine_preflight(
    project_root: Path,
    project_head: str,
    cakeml_root: Path,
    cakeml_head: str,
    hol4_root: Path,
    hol4_head: str,
    controller_identity: object,
    *,
    require_pristine: bool,
) -> dict[str, object]:
    identity = validate_controller_identity_record(controller_identity)
    project = validate_exact_git_tree(
        project_root, project_head, "replay controller project",
    )
    cakeml = validate_exact_git_tree(
        cakeml_root, cakeml_head, "CakeML",
        require_no_ignored=require_pristine,
    )
    hol4 = validate_exact_git_tree(hol4_root, hol4_head, "HOL4")
    authority = {
        "controller": source_authority_record(
            project_root, project_head, REPLAY_CONTROLLER_RELATIVE,
            "cold replay controller source",
        ),
        "gate": source_authority_record(
            project_root, project_head, REPLAY_GATE_RELATIVE,
            "cold replay gate source",
        ),
    }
    ignored_count = cakeml["ignored_untracked_count"] if require_pristine else 0
    ignored_digest = cakeml["ignored_untracked_sha256"] if require_pristine else EMPTY_SHA256
    require(ignored_count == 0 and ignored_digest == EMPTY_SHA256,
            "historical CakeML ignored-product preflight is not empty")
    return {
        "schema": 2,
        "kind": PREFLIGHT_KIND,
        "project_root": str(project_root),
        "project_head": project_head,
        "project_tracked_tree": tracked_summary_only(project),
        "cakeml_root": str(cakeml_root),
        "cakeml_head": cakeml_head,
        "cakeml_tracked_tree": tracked_summary_only(cakeml),
        "cakeml_ignored_untracked_count": ignored_count,
        "cakeml_ignored_untracked_sha256": ignored_digest,
        "hol4_root": str(hol4_root),
        "hol4_head": hol4_head,
        "hol4_tracked_tree": tracked_summary_only(hol4),
        "sources": authority,
        "controller_identity": identity,
        "complete": True,
    }


def build_terminal_manifest(
    replay: Path,
    project_root: Path,
    project_head: str,
    cakeml_root: Path,
    cakeml_head: str,
    hol4_root: Path,
    hol4_head: str,
) -> dict[str, object]:
    controller_identity = read_replay_controller_identity(replay)
    preflight, _preflight_bytes = load_canonical_json(
        replay / PRISTINE_PREFLIGHT_RELATIVE, "cold replay pristine preflight",
    )
    expected_preflight = build_pristine_preflight(
        project_root, project_head, cakeml_root, cakeml_head, hol4_root, hol4_head,
        controller_identity, require_pristine=False,
    )
    require(preflight == expected_preflight,
            "cold replay pristine preflight authority mismatch")
    final_project = validate_exact_git_tree(
        project_root, project_head, "replay controller project",
    )
    final_cakeml = validate_exact_git_tree(cakeml_root, cakeml_head, "CakeML")
    final_hol4 = validate_exact_git_tree(hol4_root, hol4_head, "HOL4")
    authority = {
        "controller": source_authority_record(
            project_root, project_head, REPLAY_CONTROLLER_RELATIVE,
            "cold replay controller source",
        ),
        "gate": source_authority_record(
            project_root, project_head, REPLAY_GATE_RELATIVE,
            "cold replay gate source",
        ),
    }
    stages = []
    for index, (name, directory, target, receipt, log) in enumerate(REPLAY_STAGES):
        stages.append({
            "index": index,
            "name": name,
            "working_directory": str(cakeml_root / directory),
            "target": target,
            "time_receipt": exact_relative_file_record(
                replay, receipt, "cold replay time receipt",
            ),
            "log": exact_relative_file_record(
                replay, log, "cold replay log", nonempty=False,
            ),
        })
    products = [
        {
            "index": index,
            **exact_relative_file_record(
                cakeml_root, relative, "cold replay product",
            ),
        }
        for index, relative in enumerate(CAKEML_POSTCONDITIONS)
    ]
    started = stable_file_bytes(
        replay / "started_utc", "cold replay start timestamp",
    ).decode("ascii").strip()
    finished = stable_file_bytes(
        replay / "finished_utc", "cold replay completion timestamp",
    ).decode("ascii").strip()
    return {
        "schema": 2,
        "kind": MANIFEST_KIND,
        "replay_root": str(replay),
        "project_root": str(project_root),
        "project_head": project_head,
        "cakeml_root": str(cakeml_root),
        "cakeml_head": cakeml_head,
        "hol4_root": str(hol4_root),
        "hol4_head": hol4_head,
        "controller_identity": controller_identity,
        "started_utc": started,
        "finished_utc": finished,
        "build_parallelism": "-j1 --mt=1",
        "address_space_limit_kib": 117964800,
        "sources": authority,
        "pristine_preflight": exact_relative_file_record(
            replay, PRISTINE_PREFLIGHT_RELATIVE,
            "cold replay pristine preflight",
        ),
        "final_tracked_trees": {
            "project": tracked_summary_only(final_project),
            "cakeml": tracked_summary_only(final_cakeml),
            "hol4": tracked_summary_only(final_hol4),
        },
        "stages": stages,
        "products": products,
        "complete": True,
    }


def memory_available_kib(proc_root: Path) -> int:
    try:
        fields = {
            line.split(":", 1)[0]: line.split()[1]
            for line in (proc_root / "meminfo").read_text(encoding="ascii").splitlines()
            if ":" in line and len(line.split()) >= 2
        }
        return int(fields["MemAvailable"])
    except (OSError, UnicodeError, KeyError, ValueError) as error:
        raise GateError("could not read MemAvailable") from error


def utc_timestamp(value: bytes, label: str) -> datetime:
    try:
        text = value.decode("ascii")
        require(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T"
                             r"[0-9]{2}:[0-9]{2}:[0-9]{2}Z\n", text) is not None,
                f"malformed {label}")
        return datetime.strptime(text.strip(), "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc,
        )
    except (UnicodeError, ValueError) as error:
        raise GateError(f"malformed {label}") from error


def validate_gate(arguments: argparse.Namespace) -> dict[str, object]:
    replay = ordinary_exact_directory(arguments.replay_root, "replay root")
    candle = ordinary_exact_directory(arguments.candle_root, "Candle root")
    cakeml = ordinary_exact_directory(arguments.cakeml_root, "CakeML root")
    hol4 = ordinary_exact_directory(arguments.hol4_root, "HOL4 root")
    proc_root = ordinary_exact_directory(arguments.proc_root, "proc root")
    project_root = ordinary_exact_directory(
        arguments.project_root, "project gate root",
    )

    validate_git(candle, arguments.candle_head, "Candle")
    validate_git(cakeml, arguments.cakeml_head, "CakeML")
    validate_git(hol4, arguments.hol4_head, "HOL4")
    replay_authority = validate_replay_controller_authority(
        replay, project_root, arguments.project_head,
        cakeml, arguments.cakeml_head, hol4, arguments.hol4_head,
    )
    controller_identity = replay_authority["controller_identity"]
    require(controller_identity == {
                "pid": arguments.replay_controller_pid,
                "pgid": arguments.replay_process_group,
                "start_ticks": arguments.replay_controller_start_ticks,
            },
            "cold replay controller identity differs from pinned launch identity")

    require(stable_file_bytes(
                replay / "stage", "cold replay stage",
            ) == b"complete\n",
            "cold replay has not completed its base heap and four stages")
    started = utc_timestamp(
        stable_file_bytes(replay / "started_utc", "cold replay start timestamp"),
        "cold replay start timestamp",
    )
    finished = utc_timestamp(
        stable_file_bytes(replay / "finished_utc", "cold replay completion timestamp"),
        "cold replay completion timestamp",
    )
    require(started <= finished <= datetime.now(timezone.utc),
            "cold replay timestamp ordering is invalid")
    controller_pid = controller_identity["pid"]
    controller_pgid = controller_identity["pgid"]
    require(not (proc_root / str(controller_pid)).exists(),
            f"cold replay controller is still live: {controller_pid}")
    group_members = process_group_members(proc_root, arguments.replay_process_group)
    require(not group_members,
            f"cold replay process group is still live: {group_members}")
    for relative, target in zip(TIME_RECEIPTS, TIME_TARGETS, strict=True):
        path = replay / relative
        validate_time_receipt(path, hol4, target)
    for relative in CAKEML_POSTCONDITIONS:
        exact_relative_file_record(cakeml, relative, "cold replay postcondition")
    manifest, manifest_bytes = load_canonical_json(
        replay / TERMINAL_MANIFEST_RELATIVE, "cold replay terminal manifest",
    )
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
    require(manifest_digest == arguments.terminal_manifest_sha256,
            "cold replay terminal manifest differs from pinned publication digest")
    expected_manifest = build_terminal_manifest(
        replay, project_root, arguments.project_head,
        cakeml, arguments.cakeml_head, hol4, arguments.hol4_head,
    )
    require(manifest == expected_manifest,
            "cold replay terminal manifest does not match current authorities")

    holmake = live_holmake_pids(proc_root)
    require(not holmake, f"Holmake is still live: {holmake}")
    available_kib = memory_available_kib(proc_root)
    required_kib = arguments.minimum_mem_available_gib * 1024 * 1024
    require(available_kib >= required_kib,
            f"insufficient MemAvailable: {available_kib} KiB < {required_kib} KiB")
    require(not os.path.lexists(arguments.attempt_root),
            f"canonical attempt root already exists: {arguments.attempt_root}")
    ordinary_exact_directory(arguments.attempt_root.parent, "attempt parent")
    inherited_limits = validate_inherited_limits()

    return {
        "gate": "canonical-cakeml-bootstrap-ready",
        "candle_head": arguments.candle_head,
        "cakeml_head": arguments.cakeml_head,
        "hol4_head": arguments.hol4_head,
        "replay_controller_pid": controller_pid,
        "replay_process_group": arguments.replay_process_group,
        "replay_controller_start_ticks": controller_identity["start_ticks"],
        "mem_available_kib": available_kib,
        "minimum_mem_available_kib": required_kib,
        "attempt_root": str(arguments.attempt_root),
        "live_holmake_pids": holmake,
        "live_replay_process_group_members": group_members,
        "inherited_soft_limits": inherited_limits,
        "replay_controller_sha256": replay_authority["controller"]["sha256"],
        "replay_gate_sha256": replay_authority["gate"]["sha256"],
        "terminal_manifest_sha256": manifest_digest,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--project-head", required=True)
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--replay-controller-pid", type=int, required=True)
    parser.add_argument("--replay-process-group", type=int, required=True)
    parser.add_argument("--replay-controller-start-ticks", type=int, required=True)
    parser.add_argument("--terminal-manifest-sha256", required=True)
    parser.add_argument("--candle-root", type=Path, required=True)
    parser.add_argument("--candle-head", required=True)
    parser.add_argument("--cakeml-root", type=Path, required=True)
    parser.add_argument("--cakeml-head", required=True)
    parser.add_argument("--hol4-root", type=Path, required=True)
    parser.add_argument("--hol4-head", required=True)
    parser.add_argument("--attempt-root", type=Path, required=True)
    parser.add_argument("--minimum-mem-available-gib", type=int, default=120)
    parser.add_argument("--proc-root", type=Path, default=Path("/proc"),
                        help=argparse.SUPPRESS)
    arguments = parser.parse_args()
    require(arguments.minimum_mem_available_gib > 0,
            "minimum memory threshold must be positive")
    require(arguments.replay_controller_pid > 1 and
            arguments.replay_process_group > 1 and
            0 < arguments.replay_controller_start_ticks <= UINT64_MAX,
            "replay launch identity must use positive non-system IDs")
    require(re.fullmatch(r"[0-9a-f]{64}", arguments.terminal_manifest_sha256)
            is not None,
            "terminal manifest digest must be canonical SHA-256")
    project_head = validate_self_authority(
        arguments.project_root, arguments.project_head,
    )
    result = validate_gate(arguments)
    result["project_gate_head"] = project_head
    print(json.dumps(result, sort_keys=True))


def internal_exact_git_main(arguments: list[str]) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--require-no-ignored", action="store_true")
    parsed = parser.parse_args(arguments)
    root = ordinary_exact_directory(parsed.root, parsed.label)
    result = validate_exact_git_tree(
        root, parsed.head, parsed.label,
        require_no_ignored=parsed.require_no_ignored,
    )
    sys.stdout.buffer.write(canonical_json_bytes(result))


def internal_preflight_main(arguments: list[str]) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--project-head", required=True)
    parser.add_argument("--cakeml-root", type=Path, required=True)
    parser.add_argument("--cakeml-head", required=True)
    parser.add_argument("--hol4-root", type=Path, required=True)
    parser.add_argument("--hol4-head", required=True)
    parser.add_argument("--controller-pid", type=int, required=True)
    parser.add_argument("--controller-pgid", type=int, required=True)
    parser.add_argument("--proc-root", type=Path, default=Path("/proc"),
                        help=argparse.SUPPRESS)
    parsed = parser.parse_args(arguments)
    replay = ordinary_exact_directory(parsed.replay_root, "replay root")
    project = ordinary_exact_directory(parsed.project_root, "controller project root")
    cakeml = ordinary_exact_directory(parsed.cakeml_root, "CakeML root")
    hol4 = ordinary_exact_directory(parsed.hol4_root, "HOL4 root")
    proc_root = ordinary_exact_directory(parsed.proc_root, "proc root")
    identity = authenticate_controller_parent(
        proc_root, parsed.controller_pid, parsed.controller_pgid,
        project / REPLAY_CONTROLLER_RELATIVE,
        (
            str(replay), str(cakeml), parsed.cakeml_head,
            str(hol4), parsed.hol4_head,
        ),
    )
    require(read_positive_pid(replay / "controller_pid") == identity["pid"] and
            read_positive_decimal(
                replay / "controller_pgid", "replay controller process group",
                (1 << 31) - 1,
            ) == identity["pgid"],
            "live controller identity differs from replay sidecars")
    write_exclusive(
        replay / "controller_start_ticks",
        f"{identity['start_ticks']}\n".encode("ascii"),
    )
    preflight = build_pristine_preflight(
        project, parsed.project_head, cakeml, parsed.cakeml_head,
        hol4, parsed.hol4_head, identity, require_pristine=True,
    )
    value = canonical_json_bytes(preflight)
    write_exclusive(replay / PRISTINE_PREFLIGHT_RELATIVE, value)
    print(hashlib.sha256(value).hexdigest())


def internal_manifest_main(arguments: list[str]) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--project-head", required=True)
    parser.add_argument("--cakeml-root", type=Path, required=True)
    parser.add_argument("--cakeml-head", required=True)
    parser.add_argument("--hol4-root", type=Path, required=True)
    parser.add_argument("--hol4-head", required=True)
    parser.add_argument("--controller-pid", type=int, required=True)
    parser.add_argument("--controller-pgid", type=int, required=True)
    parser.add_argument("--proc-root", type=Path, default=Path("/proc"),
                        help=argparse.SUPPRESS)
    parsed = parser.parse_args(arguments)
    replay = ordinary_exact_directory(parsed.replay_root, "replay root")
    project = ordinary_exact_directory(parsed.project_root, "controller project root")
    cakeml = ordinary_exact_directory(parsed.cakeml_root, "CakeML root")
    hol4 = ordinary_exact_directory(parsed.hol4_root, "HOL4 root")
    proc_root = ordinary_exact_directory(parsed.proc_root, "proc root")
    live_identity = authenticate_controller_parent(
        proc_root, parsed.controller_pid, parsed.controller_pgid,
        project / REPLAY_CONTROLLER_RELATIVE,
        (
            str(replay), str(cakeml), parsed.cakeml_head,
            str(hol4), parsed.hol4_head,
        ),
    )
    require(live_identity == read_replay_controller_identity(replay),
            "terminal publisher differs from authenticated controller identity")
    manifest = build_terminal_manifest(
        replay, project, parsed.project_head, cakeml, parsed.cakeml_head,
        hol4, parsed.hol4_head,
    )
    value = canonical_json_bytes(manifest)
    write_exclusive(replay / TERMINAL_MANIFEST_RELATIVE, value)
    print(hashlib.sha256(value).hexdigest())


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--internal-exact-git":
            internal_exact_git_main(sys.argv[2:])
        elif len(sys.argv) > 1 and sys.argv[1] == "--internal-write-preflight":
            internal_preflight_main(sys.argv[2:])
        elif len(sys.argv) > 1 and sys.argv[1] == "--internal-publish-manifest":
            internal_manifest_main(sys.argv[2:])
        else:
            main()
    except (GateError, OSError, UnicodeError) as error:
        raise SystemExit(f"canonical bootstrap gate rejected: {error}") from error
