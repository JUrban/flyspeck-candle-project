#!/usr/bin/python3
"""Read-only resource sampler for the long canonical CakeML bootstrap.

The sampler never launches or signals a workload.  It follows one required
controller process tree plus explicitly named optional process trees/groups,
records aggregate resource use, and emits alerts when the operator thresholds
are crossed.  PID start ticks bind every scope anchor so PID reuse cannot add
an unrelated workload to the sample.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
from typing import Any


GIB_KIB = 1024 * 1024
NAME_PATTERN = re.compile(r"[a-z][a-z0-9-]{0,31}")


class SampleError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SampleError(message)


@dataclass(frozen=True)
class Process:
    pid: int
    ppid: int
    process_group: int
    start_ticks: int
    cpu_ticks: int
    rss_kib: int


@dataclass(frozen=True)
class ProcessSnapshot:
    processes: dict[int, Process]
    unreadable_pids: frozenset[int]


@dataclass(frozen=True)
class Scope:
    name: str
    anchor_pid: int
    anchor_start_ticks: int
    mode: str
    process_group: int | None
    required: bool


@dataclass(frozen=True)
class ScopeTracking:
    closed: bool
    identities: frozenset[tuple[int, int]]


def canonical_json(value: Any) -> bytes:
    return (json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ) + "\n").encode("ascii")


def file_identity(path: Path) -> dict[str, Any]:
    try:
        resolved = path.resolve(strict=True)
        metadata = resolved.stat()
        require(stat.S_ISREG(metadata.st_mode),
                f"identity input is not a file: {resolved}")
        value = resolved.read_bytes()
        after = resolved.stat()
    except OSError as error:
        raise SampleError(f"could not identify file: {path}") from error
    require(
        (metadata.st_dev, metadata.st_ino, metadata.st_size,
         metadata.st_mtime_ns, metadata.st_ctime_ns) ==
        (after.st_dev, after.st_ino, after.st_size,
         after.st_mtime_ns, after.st_ctime_ns) and len(value) == metadata.st_size,
        f"identity input changed while reading: {resolved}",
    )
    return {
        "bytes": len(value),
        "path": str(resolved),
        "sha256": hashlib.sha256(value).hexdigest(),
    }


def positive_integer(value: str, label: str) -> int:
    require(re.fullmatch(r"[1-9][0-9]*", value) is not None,
            f"{label} must be a positive integer")
    return int(value)


def nonnegative_integer(value: str, label: str) -> int:
    require(re.fullmatch(r"(?:0|[1-9][0-9]*)", value) is not None,
            f"{label} must be a nonnegative integer")
    return int(value)


def parse_optional_scope(value: str) -> Scope:
    fields = value.split(":")
    require(len(fields) in {4, 5},
            "optional scope must be NAME:PID:START_TICKS:tree or "
            "NAME:PID:START_TICKS:group:PGID")
    name, pid_text, ticks_text, mode = fields[:4]
    require(NAME_PATTERN.fullmatch(name) is not None,
            f"invalid optional scope name: {name}")
    pid = positive_integer(pid_text, f"{name} PID")
    ticks = positive_integer(ticks_text, f"{name} start ticks")
    if mode == "tree":
        require(len(fields) == 4,
                f"tree scope {name} must not include a process group")
        process_group = None
    elif mode == "group":
        require(len(fields) == 5,
                f"group scope {name} requires a process group")
        process_group = positive_integer(fields[4], f"{name} process group")
    else:
        raise SampleError(f"invalid optional scope mode: {mode}")
    return Scope(name, pid, ticks, mode, process_group, False)


def parse_stat(value: str, expected_pid: int) -> tuple[int, int, int, int]:
    # /proc/PID/stat permits spaces and parentheses in comm.  The final ") "
    # precedes field 3 (state), so rpartition is the unambiguous split.
    prefix, separator, suffix = value.rstrip("\n").rpartition(") ")
    require(separator == ") " and prefix.startswith(f"{expected_pid} ("),
            f"malformed stat for PID {expected_pid}")
    fields = suffix.split()
    require(len(fields) >= 20, f"short stat for PID {expected_pid}")
    try:
        ppid = int(fields[1])
        process_group = int(fields[2])
        cpu_ticks = int(fields[11]) + int(fields[12])
        start_ticks = int(fields[19])
    except (ValueError, IndexError) as error:
        raise SampleError(f"malformed stat integers for PID {expected_pid}") from error
    require(ppid >= 0 and process_group > 0 and cpu_ticks >= 0 and start_ticks > 0,
            f"invalid stat values for PID {expected_pid}")
    return ppid, process_group, start_ticks, cpu_ticks


def read_rss_kib(value: bytes, pid: int) -> int:
    values = [line.split() for line in value.splitlines()
              if line.startswith(b"VmRSS:")]
    if not values:
        # Kernel threads legitimately have no userspace resident set.  They
        # remain in the topology so descendant and process-group selection is
        # complete, but contribute zero KiB.
        return 0
    require(len(values) == 1 and len(values[0]) == 3 and values[0][2] == b"kB",
            f"malformed VmRSS for PID {pid}")
    try:
        text = values[0][1].decode("ascii")
    except UnicodeError as error:
        raise SampleError(f"malformed VmRSS for PID {pid}") from error
    return nonnegative_integer(text, f"PID {pid} VmRSS")


def read_proc_file(directory_fd: int, name: str) -> bytes:
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        dir_fd=directory_fd,
    )
    try:
        chunks = []
        while block := os.read(descriptor, 64 * 1024):
            chunks.append(block)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def process_snapshot(proc_root: Path) -> ProcessSnapshot:
    result: dict[int, Process] = {}
    unreadable: set[int] = set()
    try:
        root_descriptor = os.open(
            proc_root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
            getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as error:
        raise SampleError(f"could not open proc root: {proc_root}") from error
    try:
        try:
            names = os.listdir(root_descriptor)
        except OSError as error:
            raise SampleError(f"could not enumerate proc root: {proc_root}") from error
        for name in names:
            if not name.isdigit() or int(name) <= 0:
                continue
            pid = int(name)
            process_descriptor = None
            try:
                process_descriptor = os.open(
                    name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
                    getattr(os, "O_CLOEXEC", 0),
                    dir_fd=root_descriptor,
                )
                before = parse_stat(
                    read_proc_file(process_descriptor, "stat").decode("latin-1"),
                    pid,
                )
                rss_kib = read_rss_kib(
                    read_proc_file(process_descriptor, "status"), pid,
                )
                after = parse_stat(
                    read_proc_file(process_descriptor, "stat").decode("latin-1"),
                    pid,
                )
                if before[2] != after[2] or after[3] < before[3]:
                    # The numeric PID was recycled while its status was read.
                    # Exclude the mixed observation; exact scope anchors will
                    # consequently be absent rather than rebound.
                    continue
            except (FileNotFoundError, ProcessLookupError):
                # Processes may exit while /proc is enumerated.
                continue
            except PermissionError:
                # Preserve the distinction between an exited PID and one that
                # exists but could not be authenticated.  Scope resolution
                # rejects an unreadable anchor or previously selected member;
                # permission churn on unrelated PIDs remains harmless.
                unreadable.add(pid)
                continue
            except OSError as error:
                if error.errno in {errno.ENOENT, errno.ESRCH}:
                    continue
                if error.errno in {errno.EACCES, errno.EPERM}:
                    unreadable.add(pid)
                    continue
                raise SampleError(f"could not inspect PID {pid}") from error
            finally:
                if process_descriptor is not None:
                    os.close(process_descriptor)
            result[pid] = Process(
                pid, after[0], after[1], after[2], after[3], rss_kib,
            )
    finally:
        os.close(root_descriptor)
    return ProcessSnapshot(result, frozenset(unreadable))


def tree_members(processes: dict[int, Process], root: int) -> set[int]:
    members = {root}
    changed = True
    while changed:
        changed = False
        for process in processes.values():
            if process.ppid in members and process.pid not in members:
                members.add(process.pid)
                changed = True
    return members & processes.keys()


def live_tracked_members(
    processes: dict[int, Process], identities: frozenset[tuple[int, int]],
) -> set[int]:
    return {
        pid for pid, start_ticks in identities
        if pid in processes and processes[pid].start_ticks == start_ticks
    }


def resolve_scope(
    scope: Scope,
    tracking: ScopeTracking,
    processes: dict[int, Process],
    unreadable_pids: frozenset[int],
    *,
    initial: bool,
) -> tuple[str, set[int], ScopeTracking]:
    if tracking.closed:
        return "closed", set(), tracking
    require(scope.anchor_pid not in unreadable_pids,
            f"scope anchor is unreadable: {scope.name}")
    tracked_pids = {pid for pid, _start_ticks in tracking.identities}
    unreadable_tracked = sorted(tracked_pids & unreadable_pids)
    require(not unreadable_tracked,
            f"tracked scope members are unreadable: {scope.name}: "
            f"{unreadable_tracked}")
    anchor = processes.get(scope.anchor_pid)
    if anchor is not None and anchor.start_ticks != scope.anchor_start_ticks:
        require(not initial, f"scope anchor identity changed: {scope.name}")
        # The numeric PID was reused after the authenticated anchor exited.
        # Treat the original anchor as absent and continue only its retained
        # identities/group; never bind the replacement.
        anchor = None
    if anchor is not None:
        if scope.mode == "tree":
            selected = tree_members(processes, scope.anchor_pid)
        else:
            require(anchor.process_group == scope.process_group,
                    f"scope anchor process group changed: {scope.name}")
            selected = {
                process.pid for process in processes.values()
                if process.process_group == scope.process_group
            }
        state = "live"
    else:
        require(not initial, f"scope anchor is absent: {scope.name}")
        selected = live_tracked_members(processes, tracking.identities)
        if scope.mode == "tree":
            # Continue following descendants of every previously observed live
            # member after the root exits.  Already reparented descendants are
            # retained by their exact (PID,start_ticks) identities.
            for root in tuple(selected):
                selected.update(tree_members(processes, root))
        # A numeric process group can be reused after its authenticated anchor
        # exits.  In either mode, draining follows only identities observed
        # while the anchor was live; unseen members of a reused group are not
        # admitted into the scope.
        state = "draining" if selected else "closed"

    identities = tracking.identities | frozenset(
        (pid, processes[pid].start_ticks) for pid in selected
    )
    next_tracking = ScopeTracking(state == "closed", identities)
    return state, selected, next_tracking


def read_mem_available_kib(proc_root: Path) -> int:
    try:
        values = [line.split() for line in
                  (proc_root / "meminfo").read_text(encoding="ascii").splitlines()
                  if line.startswith("MemAvailable:")]
    except (OSError, UnicodeError) as error:
        raise SampleError("could not read MemAvailable") from error
    require(len(values) == 1 and len(values[0]) == 3 and values[0][2] == "kB",
            "malformed MemAvailable")
    return nonnegative_integer(values[0][1], "MemAvailable")


def read_swap_pages(proc_root: Path) -> tuple[int, int]:
    try:
        fields = {
            line.split()[0]: line.split()[1]
            for line in (proc_root / "vmstat").read_text(encoding="ascii").splitlines()
            if len(line.split()) == 2
        }
        swap_in = int(fields["pswpin"])
        swap_out = int(fields["pswpout"])
    except (OSError, UnicodeError, KeyError, ValueError) as error:
        raise SampleError("could not read swap counters") from error
    require(swap_in >= 0 and swap_out >= 0, "negative swap counters")
    return swap_in, swap_out


def make_sample(
    sequence: int,
    scopes: tuple[Scope, ...],
    proc_root: Path,
    previous_swap: tuple[int, int] | None,
    previous_cpu: dict[tuple[int, int], int],
    previous_monotonic: float | None,
    alert_rss_kib: int,
    ceiling_rss_kib: int,
    minimum_mem_kib: int,
    maximum_cpu_cores: float,
    *,
    initial: bool,
    scope_tracking: dict[str, ScopeTracking] | None = None,
) -> tuple[
    dict[str, Any],
    tuple[int, int],
    dict[tuple[int, int], int],
    float,
    dict[str, ScopeTracking],
]:
    snapshot = process_snapshot(proc_root)
    processes = snapshot.processes
    scope_states: dict[str, str] = {}
    scope_members: dict[str, list[int]] = {}
    next_tracking: dict[str, ScopeTracking] = {}
    members: set[int] = set()
    scope_tracking = scope_tracking or {}
    scope_names = {scope.name for scope in scopes}
    if initial:
        require(not scope_tracking, "initial sample has prior scope tracking")
    else:
        require(set(scope_tracking) == scope_names,
                "continuation sample has incomplete scope tracking")
    for scope in scopes:
        tracking = scope_tracking.get(scope.name, ScopeTracking(False, frozenset()))
        state, selected, tracking = resolve_scope(
            scope, tracking, processes, snapshot.unreadable_pids,
            initial=initial,
        )
        scope_states[scope.name] = state
        scope_members[scope.name] = sorted(selected)
        next_tracking[scope.name] = tracking
        members.update(selected)

    current_swap = read_swap_pages(proc_root)
    if previous_swap is None:
        swap_delta = (0, 0)
    else:
        require(current_swap[0] >= previous_swap[0] and
                current_swap[1] >= previous_swap[1],
                "swap counters moved backwards")
        swap_delta = (
            current_swap[0] - previous_swap[0],
            current_swap[1] - previous_swap[1],
        )

    monotonic = time.monotonic()
    current_cpu = {
        (pid, processes[pid].start_ticks): processes[pid].cpu_ticks
        for pid in members
    }
    observed_live_cpu_cores: str | None = None
    observed_live_cpu_value: float | None = None
    if previous_monotonic is not None:
        elapsed = monotonic - previous_monotonic
        require(elapsed > 0, "nonpositive sampling interval")
        delta_ticks = 0
        for identity, ticks in current_cpu.items():
            previous = previous_cpu.get(identity)
            if previous is None:
                # A newly observed descendant was born inside the sampled
                # interval; all of its process CPU time belongs to the scope.
                delta_ticks += ticks
            else:
                require(ticks >= previous, f"CPU ticks moved backwards: {identity[0]}")
                delta_ticks += ticks - previous
        observed_live_cpu_value = (
            delta_ticks / os.sysconf("SC_CLK_TCK") / elapsed
        )
        observed_live_cpu_cores = f"{observed_live_cpu_value:.3f}"

    aggregate_rss_kib = sum(processes[pid].rss_kib for pid in members)
    mem_available_kib = read_mem_available_kib(proc_root)
    alerts = []
    if aggregate_rss_kib >= ceiling_rss_kib:
        alerts.append("aggregate-rss-ceiling")
    elif aggregate_rss_kib >= alert_rss_kib:
        alerts.append("aggregate-rss-alert")
    if mem_available_kib < minimum_mem_kib:
        alerts.append("low-mem-available")
    if swap_delta != (0, 0):
        alerts.append("paging-activity")
    if (observed_live_cpu_value is not None and
            observed_live_cpu_value > maximum_cpu_cores):
        alerts.append("cpu-core-alert")

    sample = {
        "aggregate_rss_kib": aggregate_rss_kib,
        "alerts": alerts,
        "kind": "candle-canonical-bootstrap-resource-sample",
        "mem_available_kib": mem_available_kib,
        "member_pids": sorted(members),
        "observed_live_cpu_cores": observed_live_cpu_cores,
        "schema": 1,
        "scope_members": scope_members,
        "scope_states": scope_states,
        "scope_tracked_identities": {
            name: [
                {"pid": pid, "start_ticks": start_ticks}
                for pid, start_ticks in sorted(tracking.identities)
            ]
            for name, tracking in sorted(next_tracking.items())
        },
        "sequence": sequence,
        "swap_in_delta_pages": swap_delta[0],
        "swap_out_delta_pages": swap_delta[1],
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return sample, current_swap, current_cpu, monotonic, next_tracking


class ExclusiveOutput:
    def __init__(self, path: Path) -> None:
        require(path.is_absolute(), "output path must be absolute")
        require(path.name not in {"", ".", ".."}, "invalid output basename")
        try:
            resolved_parent = path.parent.resolve(strict=True)
            parent_metadata = path.parent.lstat()
        except OSError as error:
            raise SampleError(f"could not inspect output parent: {path.parent}") from error
        require(resolved_parent == path.parent,
                "output parent contains a symlink or alias")
        require(stat.S_ISDIR(parent_metadata.st_mode),
                "output parent is not a directory")
        self.path = path
        self.parent_descriptor = -1
        try:
            self.parent_descriptor = os.open(
                path.parent,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
                getattr(os, "O_CLOEXEC", 0),
            )
            self.parent_identity = os.fstat(self.parent_descriptor)
        except OSError as error:
            if self.parent_descriptor >= 0:
                os.close(self.parent_descriptor)
                self.parent_descriptor = -1
            raise SampleError(f"could not open output parent: {path.parent}") from error
        if ((parent_metadata.st_dev, parent_metadata.st_ino) !=
                (self.parent_identity.st_dev, self.parent_identity.st_ino)):
            os.close(self.parent_descriptor)
            self.parent_descriptor = -1
            raise SampleError("output parent changed before it was opened")
        self.descriptor = -1
        self.sealed = False
        try:
            self.descriptor = os.open(
                path.name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW |
                getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=self.parent_descriptor,
            )
        except OSError as error:
            os.close(self.parent_descriptor)
            self.parent_descriptor = -1
            raise SampleError(f"could not create new output: {path}") from error
        try:
            self.output_identity = os.fstat(self.descriptor)
            require(stat.S_ISREG(self.output_identity.st_mode) and
                    self.output_identity.st_nlink == 1,
                    "new output is not a single-linked ordinary file")
            self.verify_named_identity()
            # Persist the O_EXCL directory entry before recording samples, so
            # a power loss cannot leave durable content without its pathname.
            os.fsync(self.parent_descriptor)
            self.verify_named_identity()
        except Exception:
            self.close()
            raise

    def __enter__(self) -> "ExclusiveOutput":
        return self

    def __exit__(self, _type, _value, _traceback) -> None:
        self.close()

    def write(self, value: bytes) -> None:
        require(not self.sealed and self.descriptor >= 0,
                "cannot write closed or sealed output")
        remaining = memoryview(value)
        while remaining:
            written = os.write(self.descriptor, remaining)
            require(written > 0, "short write to resource output")
            remaining = remaining[written:]

    def sync(self) -> None:
        require(not self.sealed and self.descriptor >= 0,
                "cannot sync closed or sealed output")
        os.fsync(self.descriptor)

    def verify_named_identity(self) -> None:
        descriptor_metadata = os.fstat(self.descriptor)
        try:
            named_metadata = os.stat(
                self.path.name,
                dir_fd=self.parent_descriptor,
                follow_symlinks=False,
            )
            parent_named = self.path.parent.stat(follow_symlinks=False)
        except OSError as error:
            raise SampleError("resource output disappeared before publication") from error
        parent_descriptor = os.fstat(self.parent_descriptor)
        require(
            stat.S_ISREG(descriptor_metadata.st_mode) and
            stat.S_ISREG(named_metadata.st_mode) and
            descriptor_metadata.st_nlink == named_metadata.st_nlink == 1 and
            (descriptor_metadata.st_dev, descriptor_metadata.st_ino) ==
            (named_metadata.st_dev, named_metadata.st_ino) ==
            (self.output_identity.st_dev, self.output_identity.st_ino),
            "resource output pathname no longer names the created inode",
        )
        require(
            stat.S_ISDIR(parent_descriptor.st_mode) and
            (parent_descriptor.st_dev, parent_descriptor.st_ino) ==
            (parent_named.st_dev, parent_named.st_ino) ==
            (self.parent_identity.st_dev, self.parent_identity.st_ino),
            "resource output parent identity changed",
        )

    def seal(self) -> None:
        require(not self.sealed and self.descriptor >= 0,
                "cannot reseal closed resource output")
        os.fchmod(self.descriptor, 0o444)
        os.fsync(self.descriptor)
        self.verify_named_identity()
        os.fsync(self.parent_descriptor)
        self.verify_named_identity()
        metadata = os.fstat(self.descriptor)
        require(stat.S_IMODE(metadata.st_mode) == 0o444,
                "resource output mode did not seal")
        self.sealed = True

    def close(self) -> None:
        if self.descriptor >= 0:
            os.close(self.descriptor)
            self.descriptor = -1
        if self.parent_descriptor >= 0:
            os.close(self.parent_descriptor)
            self.parent_descriptor = -1


def open_exclusive(path: Path) -> ExclusiveOutput:
    return ExclusiveOutput(path)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--controller-pid", required=True)
    result.add_argument("--controller-start-ticks", required=True)
    result.add_argument("--optional-scope", action="append", default=[])
    result.add_argument("--interval-seconds", type=int, default=30)
    result.add_argument("--alert-rss-gib", type=int, default=110)
    result.add_argument("--ceiling-rss-gib", type=int, default=120)
    result.add_argument("--minimum-mem-available-gib", type=int, default=32)
    result.add_argument("--maximum-cpu-cores", type=float, default=10.0)
    result.add_argument("--proc-root", type=Path, default=Path("/proc"),
                        help=argparse.SUPPRESS)
    result.add_argument("--once", action="store_true", help=argparse.SUPPRESS)
    result.add_argument("--quiet", action="store_true", help=argparse.SUPPRESS)
    return result


def main() -> int:
    arguments = parser().parse_args()
    controller_pid = positive_integer(arguments.controller_pid, "controller PID")
    controller_ticks = positive_integer(
        arguments.controller_start_ticks, "controller start ticks",
    )
    require(1 <= arguments.interval_seconds <= 300,
            "interval seconds must be in [1, 300]")
    require(1 <= arguments.minimum_mem_available_gib <= 1024,
            "minimum available memory must be in [1, 1024] GiB")
    require(1 <= arguments.alert_rss_gib < arguments.ceiling_rss_gib <= 1024,
            "RSS thresholds must satisfy 1 <= alert < ceiling <= 1024 GiB")
    require(0 < arguments.maximum_cpu_cores <= 1024,
            "maximum CPU cores must be in (0, 1024]")
    try:
        proc_root = arguments.proc_root.resolve(strict=True)
        proc_metadata = proc_root.lstat()
    except OSError as error:
        raise SampleError(f"could not inspect proc root: {arguments.proc_root}") from error
    require(stat.S_ISDIR(proc_metadata.st_mode), "proc root is not a directory")

    optional = tuple(parse_optional_scope(value) for value in arguments.optional_scope)
    names = [scope.name for scope in optional]
    require("canonical" not in names and len(names) == len(set(names)),
            "optional scope names must be unique and cannot be canonical")
    scopes = (
        Scope("canonical", controller_pid, controller_ticks, "tree", None, True),
        *optional,
    )
    metadata = {
        "alert_rss_kib": arguments.alert_rss_gib * GIB_KIB,
        "argv": sys.argv,
        "ceiling_rss_kib": arguments.ceiling_rss_gib * GIB_KIB,
        "cpu_accounting": (
            "approximate cores from CPU deltas of processes observed live at "
            "the current sample; interval-exited descendants are not recoverable"
        ),
        "interval_seconds": arguments.interval_seconds,
        "kind": "candle-canonical-bootstrap-resource-monitor",
        "maximum_observed_live_cpu_cores": f"{arguments.maximum_cpu_cores:.3f}",
        "minimum_mem_available_kib": arguments.minimum_mem_available_gib * GIB_KIB,
        "proc_root": str(proc_root),
        "python_executable": file_identity(Path(sys.executable)),
        "sampler_source": file_identity(Path(__file__)),
        "schema": 1,
        "scopes": [
            {
                "anchor_pid": scope.anchor_pid,
                "anchor_start_ticks": scope.anchor_start_ticks,
                "mode": scope.mode,
                "name": scope.name,
                "process_group": scope.process_group,
                "required": scope.required,
            }
            for scope in scopes
        ],
    }

    previous_swap = None
    previous_cpu: dict[tuple[int, int], int] = {}
    previous_monotonic = None
    scope_tracking: dict[str, ScopeTracking] = {}
    sequence = 0
    with open_exclusive(arguments.output) as output:
        metadata_line = canonical_json(metadata)
        output.write(metadata_line)
        if not arguments.quiet:
            sys.stdout.buffer.write(metadata_line)
            sys.stdout.buffer.flush()
        while True:
            (sample, previous_swap, previous_cpu, previous_monotonic,
             scope_tracking) = make_sample(
                sequence, scopes, proc_root, previous_swap, previous_cpu,
                previous_monotonic, arguments.alert_rss_gib * GIB_KIB,
                arguments.ceiling_rss_gib * GIB_KIB,
                arguments.minimum_mem_available_gib * GIB_KIB,
                arguments.maximum_cpu_cores, initial=(sequence == 0),
                scope_tracking=scope_tracking,
            )
            sample_line = canonical_json(sample)
            output.write(sample_line)
            output.sync()
            if not arguments.quiet:
                sys.stdout.buffer.write(sample_line)
                sys.stdout.buffer.flush()
            sequence += 1
            if sample["scope_states"]["canonical"] == "closed":
                terminal_line = canonical_json({
                    "kind": "candle-canonical-bootstrap-resource-monitor-terminal",
                    "outcome": "controller-exited",
                    "sample_count": sequence,
                    "schema": 1,
                    "utc": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ",
                    ),
                })
                output.write(terminal_line)
                output.sync()
                if not arguments.quiet:
                    sys.stdout.buffer.write(terminal_line)
                    sys.stdout.buffer.flush()
                break
            if arguments.once:
                break
            time.sleep(arguments.interval_seconds)
        output.seal()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SampleError as error:
        raise SystemExit(f"resource sampler rejected input: {error}")
