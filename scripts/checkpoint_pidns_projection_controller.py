#!/usr/bin/python3
"""Private-PID-namespace checkpoint projection task trace diagnostic.

This experimental controller combines the exact read-only mount projection
with kernel ptrace birth events.  It is deliberately non-promotable: traced
legacy-clone threads are supported while clone3 returns ENOSYS, host files and
the host network remain visible, and no result is S2/S3 or release evidence.

The controller never enumerates host ``/proc``.  It inspects only ``self``, PID
1, and exact PIDs/TIDs learned from fork or ptrace events.
"""

from __future__ import annotations

import array
import copy
import ctypes
from dataclasses import dataclass, field
import errno
import hashlib
import os
from pathlib import Path
import platform
import select
import signal
import socket
import stat
import struct
import time
from typing import Any, Callable

import checkpoint_os_authenticator as auth


class PidnsProjectionError(auth.AuthenticationError):
    """The task-aware PID-namespace diagnostic failed closed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PidnsProjectionError(message)


SCHEMA = 2
PACKET_KIND = "candle-checkpoint-pidns-projection-event-v2"
ACK_KIND = "candle-checkpoint-pidns-projection-ack-v2"
REPORT_KIND = "candle-checkpoint-pidns-projection-diagnostic-v2"
POLICY = (
    "same-uid-private-user-pid-mount-namespace-task-aware-"
    "ptrace-projection-v2"
)
MAX_PACKET_BYTES = 128 * 1024
WALL = getattr(os, "__WALL", 0x40000000)

CLONE_PTRACE = 0x00002000
CLONE_PARENT = 0x00008000
CLONE_THREAD = 0x00010000
CLONE_NEWNS = 0x00020000
CLONE_NEWCGROUP = 0x02000000
CLONE_NEWUTS = 0x04000000
CLONE_NEWIPC = 0x08000000
CLONE_NEWUSER = 0x10000000
CLONE_NEWPID = 0x20000000
CLONE_NEWNET = 0x40000000
CLONE_UNTRACED = 0x00800000

PR_SET_PDEATHSIG = 1
PR_SET_NO_NEW_PRIVS = 38
PR_SET_SECCOMP = 22
SECCOMP_MODE_FILTER = 2
SECCOMP_RET_KILL_PROCESS = 0x80000000
SECCOMP_RET_ERRNO = 0x00050000
SECCOMP_RET_ALLOW = 0x7FFF0000
AUDIT_ARCH_X86_64 = 0xC000003E
X32_SYSCALL_BIT = 0x40000000
PROC_SUPER_MAGIC = 0x9FA0

PTRACE_TRACEME = 0
PTRACE_CONT = 7
PTRACE_SETOPTIONS = 0x4200
PTRACE_GETEVENTMSG = 0x4201
PTRACE_O_TRACEFORK = 0x00000002
PTRACE_O_TRACEVFORK = 0x00000004
PTRACE_O_TRACECLONE = 0x00000008
PTRACE_O_TRACEEXEC = 0x00000010
PTRACE_O_TRACEEXIT = 0x00000040
PTRACE_O_EXITKILL = 0x00100000
PTRACE_EVENT_FORK = 1
PTRACE_EVENT_VFORK = 2
PTRACE_EVENT_CLONE = 3
PTRACE_EVENT_EXEC = 4
PTRACE_EVENT_EXIT = 6
PTRACE_OPTIONS = (
    PTRACE_O_TRACEFORK | PTRACE_O_TRACEVFORK | PTRACE_O_TRACECLONE |
    PTRACE_O_TRACEEXEC | PTRACE_O_TRACEEXIT | PTRACE_O_EXITKILL
)
EVENT_NAMES = {
    PTRACE_EVENT_FORK: "fork",
    PTRACE_EVENT_VFORK: "vfork",
    PTRACE_EVENT_CLONE: "clone",
    PTRACE_EVENT_EXEC: "exec",
    PTRACE_EVENT_EXIT: "exit-stop",
}

# The tracee may create ordinary processes and legacy-clone threads but cannot
# escape the ptrace relationship or alter namespaces/mounts.  clone3 is ENOSYS
# so libc can take the audited legacy-clone fallback.
WORKLOAD_CLONE_FORBIDDEN = (
    CLONE_UNTRACED | CLONE_PTRACE | CLONE_PARENT |
    CLONE_NEWNS | CLONE_NEWCGROUP | CLONE_NEWUTS | CLONE_NEWIPC |
    CLONE_NEWUSER | CLONE_NEWPID | CLONE_NEWNET
)
WORKLOAD_KILL_SYSCALLS_X86_64 = (
    # ptrace and cross-process memory/descriptor APIs cannot target PID 1.
    101, 310, 311, 312, 438, 440,
    # chroot/pivot, legacy and new mount APIs, and namespace transitions.
    155, 161, 165, 166, 272, 308, 428, 429, 430, 431, 432, 433, 442,
)
MANAGER_KILL_SYSCALLS_X86_64 = (
    56, 57, 58, 59, 155, 161, 165, 166, 272, 308, 322, 428, 429,
    430, 431, 432, 433, 435, 442,
)


class _SockFilter(ctypes.Structure):
    _fields_ = [
        ("code", ctypes.c_ushort),
        ("jt", ctypes.c_ubyte),
        ("jf", ctypes.c_ubyte),
        ("value", ctypes.c_uint),
    ]


class _SockFprog(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_ushort),
        ("filters", ctypes.POINTER(_SockFilter)),
    ]


def _libc() -> ctypes.CDLL:
    library = ctypes.CDLL(None, use_errno=True)
    library.ptrace.argtypes = [
        ctypes.c_uint, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
    ]
    library.ptrace.restype = ctypes.c_long
    library.prctl.argtypes = [
        ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong,
        ctypes.c_ulong,
    ]
    library.prctl.restype = ctypes.c_int
    library.statfs.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
    library.statfs.restype = ctypes.c_int
    return library


def _prctl(option: int, argument: int, label: str) -> None:
    if _libc().prctl(option, argument, 0, 0, 0) != 0:
        number = ctypes.get_errno()
        raise PidnsProjectionError(
            f"{label} failed: errno {number} "
            f"({errno.errorcode.get(number, 'UNKNOWN')})"
        )


def _set_parent_death_signal(*, allow_invisible_parent: bool = False) -> None:
    parent = os.getppid()
    _prctl(PR_SET_PDEATHSIG, signal.SIGKILL, "parent-death signal")
    require(os.getppid() == parent and
            (parent > 0 or allow_invisible_parent),
            "parent changed while parent-death signal was installed")


def _ptrace(
    request: int, pid: int, data: int = 0, *, context: str = "",
    allow_esrch: bool = False,
) -> bool:
    if _libc().ptrace(request, pid, None, ctypes.c_void_p(data)) != 0:
        number = ctypes.get_errno()
        if allow_esrch and number == errno.ESRCH:
            return False
        raise PidnsProjectionError(
            f"ptrace request {request} failed for inner pid {pid}: "
            f"errno {number}" + (f" during {context}" if context else "")
        )
    return True


def _ptrace_event_message(pid: int) -> int:
    value = ctypes.c_ulong()
    if _libc().ptrace(
        PTRACE_GETEVENTMSG, pid, None, ctypes.byref(value),
    ) != 0:
        number = ctypes.get_errno()
        raise PidnsProjectionError(
            f"ptrace event-message read failed for inner pid {pid}: "
            f"errno {number}"
        )
    return int(value.value)


def _install_filter(
    *, kill_syscalls: tuple[int, ...], clone_policy: bool,
) -> None:
    require(platform.machine() == "x86_64" and
            struct.pack("=I", 1) == struct.pack("<I", 1),
            "PID-namespace diagnostic supports little-endian x86_64 only")
    instructions: list[_SockFilter] = [
        _SockFilter(0x20, 0, 0, 4),
        _SockFilter(0x15, 1, 0, AUDIT_ARCH_X86_64),
        _SockFilter(0x06, 0, 0, SECCOMP_RET_KILL_PROCESS),
        _SockFilter(0x20, 0, 0, 0),
        _SockFilter(0x45, 0, 1, X32_SYSCALL_BIT),
        _SockFilter(0x06, 0, 0, SECCOMP_RET_KILL_PROCESS),
    ]
    for syscall_number in kill_syscalls:
        instructions.extend([
            _SockFilter(0x15, 0, 1, syscall_number),
            _SockFilter(0x06, 0, 0, SECCOMP_RET_KILL_PROCESS),
        ])
    if clone_policy:
        # clone3 cannot be inspected by classic BPF; ENOSYS is the explicit
        # libc-fallback policy rather than an untraced escape.
        instructions.extend([
            _SockFilter(0x15, 0, 1, 435),
            _SockFilter(0x06, 0, 0, SECCOMP_RET_ERRNO | errno.ENOSYS),
            # If this is not legacy clone, jump over the clone argument checks.
            _SockFilter(0x15, 0, 3, 56),
            _SockFilter(0x20, 0, 0, 16),
            _SockFilter(0x45, 0, 1, WORKLOAD_CLONE_FORBIDDEN),
            _SockFilter(0x06, 0, 0, SECCOMP_RET_KILL_PROCESS),
        ])
    instructions.append(_SockFilter(0x06, 0, 0, SECCOMP_RET_ALLOW))
    filters = (_SockFilter * len(instructions))(*instructions)
    program = _SockFprog(len(filters), filters)
    _prctl(PR_SET_NO_NEW_PRIVS, 1, "no_new_privs")
    if _libc().prctl(
        PR_SET_SECCOMP, SECCOMP_MODE_FILTER, ctypes.addressof(program), 0, 0,
    ) != 0:
        number = ctypes.get_errno()
        raise PidnsProjectionError(
            f"seccomp installation failed: errno {number} "
            f"({errno.errorcode.get(number, 'UNKNOWN')})"
        )


def _decode_proc_stat(data: bytes) -> dict[str, int | str]:
    try:
        text = data.decode("ascii")
        left = text.index("(")
        right = text.rindex(")")
        fields = text[right + 2:].split()
        require(len(fields) >= 20, "short exact /proc stat record")
        return {
            "pid": int(text[:left].strip()),
            "state": fields[0],
            "parent_pid": int(fields[1]),
            "process_group_id": int(fields[2]),
            "session_id": int(fields[3]),
            "start_ticks": int(fields[19]),
        }
    except (UnicodeError, ValueError) as error:
        raise PidnsProjectionError("malformed exact /proc stat record") from error


def _decode_proc_status(data: bytes, label: str) -> dict[str, str]:
    try:
        lines = data.decode("ascii").splitlines()
    except UnicodeError as error:
        raise PidnsProjectionError(f"malformed {label} status") from error
    result: dict[str, str] = {}
    for line in lines:
        if ":" in line:
            name, value = line.split(":", 1)
            result[name] = value.strip()
    return result


def _proc_status(pid: str | int) -> dict[str, str]:
    try:
        data = Path(f"/proc/{pid}/status").read_bytes()
    except OSError as error:
        raise PidnsProjectionError(
            f"cannot read exact /proc/{pid}/status"
        ) from error
    return _decode_proc_status(data, f"/proc/{pid}")


def _read_proc_task_file(directory_fd: int, name: str) -> bytes:
    require(name in {"stat", "status"}, "unexpected proc task file request")
    descriptor = os.open(
        name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
        dir_fd=directory_fd,
    )
    try:
        pieces: list[bytes] = []
        total = 0
        while True:
            piece = os.read(descriptor, 16 * 1024)
            if not piece:
                break
            total += len(piece)
            require(total <= 1024 * 1024, "oversize exact proc task record")
            pieces.append(piece)
        return b"".join(pieces)
    finally:
        os.close(descriptor)


def _integer_vector(value: str, label: str) -> list[int]:
    try:
        values = [int(item) for item in value.split()]
    except ValueError as error:
        raise PidnsProjectionError(f"malformed {label} vector") from error
    require(values and all(item > 0 for item in values),
            f"empty or nonpositive {label} vector")
    return values


def _namespace_identity(name: str, pid: str | int = "self") -> dict[str, Any]:
    require(name in {"mnt", "user", "pid", "pid_for_children"},
            "unknown namespace identity request")
    path = f"/proc/{pid}/ns/{name}"
    try:
        link = os.readlink(path)
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
        try:
            value = os.fstat(descriptor)
        finally:
            os.close(descriptor)
    except OSError as error:
        raise PidnsProjectionError(
            f"cannot inspect exact {name} namespace for {pid}"
        ) from error
    require(stat.S_ISREG(value.st_mode) and value.st_nlink == 1,
            f"exact {name} namespace object differs")
    return {
        "name": name,
        "link": link,
        "device": value.st_dev,
        "inode": value.st_ino,
    }


def _pidfd_identity(descriptor: int) -> dict[str, Any]:
    value = os.fstat(descriptor)
    return {
        "device": value.st_dev,
        "inode": value.st_ino,
        "mode": f"{stat.S_IMODE(value.st_mode):04o}",
    }


def _pidfd_outer_identity(descriptor: int) -> dict[str, Any]:
    try:
        text = Path(f"/proc/self/fdinfo/{descriptor}").read_text(
            encoding="ascii",
        )
    except OSError as error:
        raise PidnsProjectionError("cannot read transferred pidfd info") from error
    values: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            name, value = line.split(":", 1)
            values[name] = value.strip()
    require("Pid" in values and "NSpid" in values,
            "transferred pidfd lacks PID namespace identity")
    try:
        outer_pid = int(values["Pid"])
    except ValueError as error:
        raise PidnsProjectionError("malformed transferred pidfd PID") from error
    return {
        "outer_pid": outer_pid,
        "nspid": _integer_vector(values["NSpid"], "pidfd NSpid"),
        "pidfd": _pidfd_identity(descriptor),
    }


def _process_identity(inner_tgid: int, pidfd: int) -> dict[str, Any]:
    proc = Path(f"/proc/{inner_tgid}")
    before = _decode_proc_stat((proc / "stat").read_bytes())
    status = _proc_status(inner_tgid)
    nspid = _integer_vector(status.get("NSpid", ""), "process NSpid")
    nstgid = _integer_vector(status.get("NStgid", ""), "process NStgid")
    require(nspid[-1] == inner_tgid and nstgid[-1] == inner_tgid and
            int(status.get("Pid", "0")) == inner_tgid and
            int(status.get("Tgid", "0")) == inner_tgid,
            "process identity path is not the thread-group leader")
    try:
        executable_path = os.readlink(proc / "exe")
        executable = (proc / "exe").stat()
    except OSError as error:
        raise PidnsProjectionError(
            f"cannot inspect exact executable for inner tgid {inner_tgid}"
        ) from error
    after = _decode_proc_stat((proc / "stat").read_bytes())
    require(before == after, "process identity changed during exact capture")
    return {
        # inner_pid is retained for compatibility with the process-only
        # diagnostic packet readers; inner_tgid is the unambiguous v2 name.
        "inner_pid": inner_tgid,
        "inner_tgid": inner_tgid,
        "nspid_visible_from_inner_proc": nspid,
        "nstgid_visible_from_inner_proc": nstgid,
        **before,
        "executable": {
            "path": executable_path,
            "device": executable.st_dev,
            "inode": executable.st_ino,
            "mode": f"{stat.S_IMODE(executable.st_mode):04o}",
        },
        "pid_namespace": _namespace_identity("pid", inner_tgid),
        "pidfd": _pidfd_identity(pidfd),
    }


def _open_process_identity(inner_tgid: int) -> tuple[int, dict[str, Any]]:
    require(hasattr(os, "pidfd_open"), "kernel lacks pidfd_open")
    try:
        descriptor = os.pidfd_open(inner_tgid, 0)
    except OSError as error:
        raise PidnsProjectionError(
            f"cannot pin process leader {inner_tgid}"
        ) from error
    try:
        return descriptor, _process_identity(inner_tgid, descriptor)
    except BaseException:
        os.close(descriptor)
        raise


def _task_directory_identity(descriptor: int) -> dict[str, Any]:
    value = os.fstat(descriptor)
    require(stat.S_ISDIR(value.st_mode), "held proc task object is not a directory")
    return {
        "device": value.st_dev,
        "inode": value.st_ino,
        "mode": f"{stat.S_IMODE(value.st_mode):04o}",
        "link_count": value.st_nlink,
    }


def _open_task_identity(
    inner_tid: int, *, expected_tgid: int | None = None,
) -> tuple[int, dict[str, Any]]:
    """Pin and authenticate exact ``/proc/<tgid>/task/<tid>`` identity.

    The direct ``/proc/<tid>`` alias is used only to learn the tgid for a
    kernel-reported stopped TID.  All identity evidence comes from, and the
    retained descriptor names, the exact task-directory path.
    """
    require(type(inner_tid) is int and inner_tid > 1,
            "invalid kernel-reported inner tid")
    alias_fd = -1
    task_fd = -1
    try:
        alias_fd = os.open(
            f"/proc/{inner_tid}",
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        alias_status = _decode_proc_status(
            _read_proc_task_file(alias_fd, "status"),
            f"/proc/{inner_tid}",
        )
        inner_tgid = int(alias_status.get("Tgid", "0"))
        require(inner_tgid > 1 and
                (expected_tgid is None or inner_tgid == expected_tgid),
                "kernel-reported task has an unexpected thread group")
        task_fd = os.open(
            f"/proc/{inner_tgid}/task/{inner_tid}",
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        directory_before = _task_directory_identity(task_fd)
        stat_before = _decode_proc_stat(
            _read_proc_task_file(task_fd, "stat"),
        )
        status = _decode_proc_status(
            _read_proc_task_file(task_fd, "status"),
            f"/proc/{inner_tgid}/task/{inner_tid}",
        )
        stat_after = _decode_proc_stat(
            _read_proc_task_file(task_fd, "stat"),
        )
        directory_after = _task_directory_identity(task_fd)
        nspid = _integer_vector(status.get("NSpid", ""), "task NSpid")
        nstgid = _integer_vector(status.get("NStgid", ""), "task NStgid")
        require(directory_before == directory_after and
                stat_before == stat_after and
                stat_before["pid"] == inner_tid and
                int(status.get("Pid", "0")) == inner_tid and
                int(status.get("Tgid", "0")) == inner_tgid and
                nspid[-1] == inner_tid and nstgid[-1] == inner_tgid,
                "exact held proc task identity changed or mismatched")
        alias_nspid = _integer_vector(
            alias_status.get("NSpid", ""), "task-alias NSpid",
        )
        alias_nstgid = _integer_vector(
            alias_status.get("NStgid", ""), "task-alias NStgid",
        )
        require(alias_nspid == nspid and alias_nstgid == nstgid and
                int(alias_status.get("Pid", "0")) == inner_tid,
                "direct task alias and exact task directory differ")
        identity = {
            "inner_tid": inner_tid,
            "inner_tgid": inner_tgid,
            "nspid_visible_from_inner_proc": nspid,
            "nstgid_visible_from_inner_proc": nstgid,
            "start_ticks": stat_before["start_ticks"],
            "observed_parent_process_inner_pid_untrusted":
                stat_before["parent_pid"],
            "process_group_id": stat_before["process_group_id"],
            "session_id": stat_before["session_id"],
            "state": stat_before["state"],
            "task_directory": directory_before,
            "task_directory_held": True,
        }
        os.close(alias_fd)
        alias_fd = -1
        result_fd = task_fd
        task_fd = -1
        return result_fd, identity
    except (OSError, ValueError) as error:
        if isinstance(error, PidnsProjectionError):
            raise
        raise PidnsProjectionError(
            f"cannot pin exact proc task identity for inner tid {inner_tid}"
        ) from error
    finally:
        for descriptor in (alias_fd, task_fd):
            if descriptor >= 0:
                os.close(descriptor)


def _proc_mount_records() -> list[dict[str, Any]]:
    try:
        records = Path("/proc/self/mountinfo").read_text(
            encoding="ascii",
        ).splitlines()
    except OSError as error:
        raise PidnsProjectionError("cannot read exact proc mountinfo") from error
    matches: list[dict[str, Any]] = []
    for line in records:
        left, separator, right = line.partition(" - ")
        fields = left.split()
        tail = right.split()
        if separator and len(fields) >= 6 and len(tail) >= 3 and fields[4] == "/proc":
            matches.append({
                "mount_id": int(fields[0]),
                "parent_mount_id": int(fields[1]),
                "root": fields[3],
                "mount_point": fields[4],
                "mount_options": fields[5].split(","),
                "filesystem_type": tail[0],
                "super_options": tail[2].split(","),
            })
    return matches


def _procfs_evidence(previous_mount_ids: set[int]) -> dict[str, Any]:
    buffer = ctypes.create_string_buffer(256)
    if _libc().statfs(b"/proc", ctypes.byref(buffer)) != 0:
        number = ctypes.get_errno()
        raise PidnsProjectionError(f"statfs(/proc) failed: errno {number}")
    magic = struct.unpack_from("=q", buffer.raw)[0]
    require(magic == PROC_SUPER_MAGIC, "fresh /proc is not procfs")
    new_records = [
        item for item in _proc_mount_records()
        if item["mount_id"] not in previous_mount_ids
    ]
    require(len(new_records) == 1,
            "fresh /proc mount does not have one new mount identity")
    mount_record = new_records[0]
    require(mount_record is not None and
            mount_record["filesystem_type"] == "proc" and
            mount_record["root"] == "/" and
            {"rw", "nosuid", "nodev", "noexec"}.issubset(
                set(mount_record["mount_options"])
            ), "fresh /proc mount contract differs")
    self_status = _proc_status("self")
    init_status = _proc_status(1)
    require(_integer_vector(self_status.get("NSpid", ""), "self NSpid")[-1] == 1 and
            _integer_vector(init_status.get("NSpid", ""), "init NSpid")[-1] == 1,
            "fresh procfs is not rooted in the new PID namespace")
    return {"magic": magic, "mount": mount_record}


def _install_fresh_procfs() -> dict[str, Any]:
    previous_mount_ids = {
        item["mount_id"] for item in _proc_mount_records()
    }
    auth._projection_mount(
        "proc", "/proc", "proc",
        auth.MS_NOSUID | auth.MS_NODEV | auth.MS_NOEXEC,
    )
    evidence = _procfs_evidence(previous_mount_ids)
    pid = _namespace_identity("pid")
    pid_for_children = _namespace_identity("pid_for_children")
    require(pid["inode"] == pid_for_children["inode"],
            "PID-1 pid and pid-for-children namespaces differ")
    evidence["pid_namespace"] = pid
    evidence["pid_for_children_namespace"] = pid_for_children
    return evidence


def _status_security(pid: str | int) -> dict[str, str]:
    status = _proc_status(pid)
    names = (
        "CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb", "NoNewPrivs",
        "Seccomp", "Seccomp_filters", "State",
    )
    return {name: status.get(name, "") for name in names}


def _lifelines_alive(descriptors: tuple[int, int]) -> None:
    poller = select.poll()
    for descriptor in descriptors:
        poller.register(descriptor, select.POLLIN | select.POLLHUP | select.POLLERR)
    for descriptor, events in poller.poll(0):
        if events & (select.POLLHUP | select.POLLERR):
            raise PidnsProjectionError(
                f"controller lifeline {descriptor} was lost"
            )


@dataclass
class _ProcessIdentity:
    """Thread-group identity; only this record owns a leader pidfd."""

    pidfd: int
    identity: dict[str, Any]
    tasks: set[int] = field(default_factory=set)
    executable_epoch: int = 0


@dataclass
class _TaskIdentity:
    """Per-task identity pinned by its exact proc task-directory FD."""

    directory_fd: int
    identity: dict[str, Any]
    options_set: bool
    birth_registered: bool
    birth: dict[str, Any] | None


def _task_evidence(task: _TaskIdentity) -> dict[str, Any]:
    result = copy.deepcopy(task.identity)
    result["birth"] = copy.deepcopy(task.birth)
    return result


def _require_held_task_identity(task: _TaskIdentity) -> None:
    current = _task_directory_identity(task.directory_fd)
    recorded = task.identity["task_directory"]
    require(
        {key: current[key] for key in ("device", "inode", "mode")} ==
        {key: recorded[key] for key in ("device", "inode", "mode")} and
        current["link_count"] <= recorded["link_count"],
        "held exact proc task-directory identity changed",
    )


def _capture_task(
    inner_tid: int, processes: dict[int, _ProcessIdentity],
    *, expected_tgid: int | None = None,
) -> tuple[_TaskIdentity, _ProcessIdentity, bool]:
    task_fd, task_identity = _open_task_identity(
        inner_tid, expected_tgid=expected_tgid,
    )
    inner_tgid = int(task_identity["inner_tgid"])
    process = processes.get(inner_tgid)
    created_process = False
    try:
        if process is None:
            require(inner_tid == inner_tgid,
                    "new thread group was first observed through a nonleader")
            pidfd, process_identity = _open_process_identity(inner_tgid)
            process = _ProcessIdentity(pidfd, process_identity)
            processes[inner_tgid] = process
            created_process = True
        require(inner_tid not in process.tasks,
                "duplicate exact task identity capture")
        task = _TaskIdentity(task_fd, task_identity, False, False, None)
        process.tasks.add(inner_tid)
        task_fd = -1
        return task, process, created_process
    except BaseException:
        if created_process:
            processes.pop(inner_tgid, None)
            os.close(process.pidfd)
        raise
    finally:
        if task_fd >= 0:
            os.close(task_fd)


def _close_task(
    inner_tid: int, tasks: dict[int, _TaskIdentity],
    processes: dict[int, _ProcessIdentity],
) -> tuple[_TaskIdentity, bool]:
    task = tasks.pop(inner_tid)
    inner_tgid = int(task.identity["inner_tgid"])
    process = processes[inner_tgid]
    require(inner_tid in process.tasks,
            "task/process membership differs at close")
    process.tasks.remove(inner_tid)
    os.close(task.directory_fd)
    process_closed = not process.tasks
    if process_closed:
        os.close(process.pidfd)
        del processes[inner_tgid]
    return task, process_closed


class _Emitter:
    def __init__(
        self, channel: socket.socket, challenge: str, controller_outer_pid: int,
    ) -> None:
        self.channel = channel
        self.challenge = challenge
        self.controller_outer_pid = controller_outer_pid
        self.sequence = 0

    def send(
        self, event: str, payload: dict[str, Any], *, transfer_pidfd: int = -1,
    ) -> bytes:
        body = dict(payload)
        body["transferred_pidfd"] = transfer_pidfd >= 0
        packet = {
            "schema": SCHEMA,
            "kind": PACKET_KIND,
            "policy": POLICY,
            "challenge": self.challenge,
            "controller_outer_pid": self.controller_outer_pid,
            "sequence": self.sequence,
            "event": event,
            "monotonic_ns": time.monotonic_ns(),
            "payload": body,
            "approval_included": False,
            "controller_supplied_pft_input": False,
        }
        raw = auth.canonical_json_bytes(packet)
        require(len(raw) <= MAX_PACKET_BYTES, "controller packet is too large")
        ancillary = []
        if transfer_pidfd >= 0:
            descriptors = array.array("i", [transfer_pidfd])
            ancillary = [(
                socket.SOL_SOCKET, socket.SCM_RIGHTS, descriptors.tobytes(),
            )]
        sent = self.channel.sendmsg([raw], ancillary)
        require(sent == len(raw), "short controller packet send")
        self.sequence += 1
        return raw


def _spawn_traceme_workload(
    executable_fd: int, argv: list[str], environment: dict[str, str],
    manager_fds: tuple[int, ...],
) -> int:
    pid = os.fork()
    if pid == 0:
        try:
            for descriptor in manager_fds:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            require(os.getppid() == 1,
                    "projected workload parent is not namespace PID 1")
            _set_parent_death_signal()
            devnull = os.open("/dev/null", os.O_RDWR | os.O_CLOEXEC)
            try:
                for descriptor in (0, 1, 2):
                    os.dup2(devnull, descriptor)
            finally:
                if devnull > 2:
                    os.close(devnull)
            if _libc().ptrace(PTRACE_TRACEME, 0, None, None) != 0:
                os._exit(124)
            _install_filter(
                kill_syscalls=WORKLOAD_KILL_SYSCALLS_X86_64,
                clone_policy=True,
            )
            auth._drop_projection_capabilities()
            os.kill(os.getpid(), signal.SIGSTOP)
            auth._close_projection_exec_descriptors()
            os.execve(executable_fd, argv, environment)
        except BaseException:
            os._exit(125)
    return pid


def _kill_pidfd(descriptor: int, pid: int) -> None:
    try:
        if hasattr(signal, "pidfd_send_signal"):
            signal.pidfd_send_signal(descriptor, signal.SIGKILL, None, 0)
        else:
            os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _cleanup_tracees(
    tasks: dict[int, _TaskIdentity],
    processes: dict[int, _ProcessIdentity],
) -> None:
    for tgid, process in list(processes.items()):
        _kill_pidfd(process.pidfd, tgid)
    deadline = time.monotonic() + 3.0
    while tasks and time.monotonic() < deadline:
        try:
            pid, _ = os.waitpid(-1, WALL | os.WNOHANG)
        except ChildProcessError:
            break
        if pid == 0:
            time.sleep(0.002)
            continue
        task = tasks.pop(pid, None)
        if task is not None:
            os.close(task.directory_fd)
            process = processes.get(int(task.identity["inner_tgid"]))
            if process is not None:
                process.tasks.discard(pid)
    for task in tasks.values():
        os.close(task.directory_fd)
    tasks.clear()
    for process in processes.values():
        os.close(process.pidfd)
    processes.clear()


def _refresh_after_exec(
    event_tid: int, former_tid: int,
    tasks: dict[int, _TaskIdentity],
    processes: dict[int, _ProcessIdentity],
) -> tuple[_TaskIdentity, _ProcessIdentity, dict[str, Any]]:
    """Apply Linux exec TID rekey and the thread-group exec collapse."""
    require(former_tid in tasks,
            "exec event names an unregistered former task")
    former_task = tasks[former_tid]
    tgid = int(former_task.identity["inner_tgid"])
    require(event_tid == tgid and tgid in processes,
            "exec event did not rekey to the process leader tgid")
    process = processes[tgid]
    require(former_tid in process.tasks,
            "exec former task is absent from its process")

    previous_process = copy.deepcopy(process.identity)
    previous_task = _task_evidence(former_task)
    collapsed: list[dict[str, Any]] = []
    for tid in sorted(process.tasks):
        old_task = tasks.pop(tid)
        if tid != former_tid:
            collapsed.append(_task_evidence(old_task))
        os.close(old_task.directory_fd)
    process.tasks.clear()

    task_fd, task_identity = _open_task_identity(
        event_tid, expected_tgid=tgid,
    )
    refreshed = _TaskIdentity(
        task_fd, task_identity, True, former_task.birth_registered,
        copy.deepcopy(former_task.birth),
    )
    tasks[event_tid] = refreshed
    process.tasks.add(event_tid)
    current_process = _process_identity(tgid, process.pidfd)
    require(current_process["pidfd"] == previous_process["pidfd"],
            "leader pidfd identity changed across exec")
    nonleader_rekey = former_tid != event_tid
    if not nonleader_rekey:
        require(current_process["start_ticks"] ==
                previous_process["start_ticks"],
                "leader process start identity changed across exec")
    process.executable_epoch += 1
    process.identity = current_process
    transition = {
        "event_inner_tid": event_tid,
        "former_inner_tid": former_tid,
        "nonleader_tid_rekey": nonleader_rekey,
        "collapsed_inner_tids": [
            int(item["inner_tid"]) for item in collapsed
        ],
        "collapsed_tasks": collapsed,
        "previous_task": previous_task,
        "previous_process_start_ticks": previous_process["start_ticks"],
        "current_process_start_ticks": current_process["start_ticks"],
        "executable_epoch": process.executable_epoch,
    }
    return refreshed, process, transition


def _trace_until_closed(
    emitter: _Emitter, root_tgid: int,
    root_process: _ProcessIdentity, root_task: _TaskIdentity,
    timeout_seconds: float, lifelines: tuple[int, int],
) -> dict[str, Any]:
    processes = {root_tgid: root_process}
    tasks = {root_tgid: root_task}
    next_birth_sequence = 1
    counts = {
        name: 0 for name in (
            "fork", "vfork", "clone", "exec", "exit-stop", "terminal",
            "signal-stop", "provisional-child-stop", "process-birth",
            "thread-birth", "exec-rekey", "exec-collapse-task",
            "exit-resume-esrch",
        )
    }
    terminals: list[dict[str, Any]] = []
    closed = False
    try:
        _ptrace(PTRACE_CONT, root_tgid, 0)
        deadline = time.monotonic() + timeout_seconds
        while tasks:
            require(time.monotonic() < deadline,
                    "projected task tree timed out")
            _lifelines_alive(lifelines)
            try:
                pid, wait_status = os.waitpid(
                    -1, WALL | os.WNOHANG | os.WUNTRACED,
                )
            except ChildProcessError as error:
                raise PidnsProjectionError(
                    "projected trace tree vanished before closure"
                ) from error
            if pid == 0:
                time.sleep(0.001)
                continue
            task = tasks.get(pid)
            if (task is None and os.WIFSTOPPED(wait_status) and
                    os.WSTOPSIG(wait_status) == signal.SIGSTOP):
                task, process, created_process = _capture_task(pid, processes)
                tasks[pid] = task
                tgid = int(task.identity["inner_tgid"])
                if not created_process:
                    require(tgid in processes,
                            f"unregistered provisional thread {pid}")
                counts["provisional-child-stop"] += 1
                emitter.send(
                    "provisional-child-stop",
                    {
                        "process": process.identity,
                        "task": _task_evidence(task),
                        "provisional_process": created_process,
                    },
                    transfer_pidfd=(process.pidfd if created_process else -1),
                )
                # Do not release a provisional child until the parent's
                # kernel birth event registers the exact edge.
                continue
            require(task is not None,
                    f"unregistered exact task status for {pid}")
            _require_held_task_identity(task)
            task_tgid = int(task.identity["inner_tgid"])
            process = processes[task_tgid]
            if os.WIFEXITED(wait_status) or os.WIFSIGNALED(wait_status):
                require(task.birth_registered,
                        f"task {pid} terminated before birth event")
                terminal = {
                    "inner_pid": task_tgid,
                    "inner_tid": pid,
                    "process": process.identity,
                    "task": _task_evidence(task),
                    "exit_code": (
                        os.WEXITSTATUS(wait_status)
                        if os.WIFEXITED(wait_status) else None
                    ),
                    "signal": (
                        os.WTERMSIG(wait_status)
                        if os.WIFSIGNALED(wait_status) else None
                    ),
                }
                terminals.append(terminal)
                counts["terminal"] += 1
                _, process_closed = _close_task(pid, tasks, processes)
                terminal["process_closed"] = process_closed
                emitter.send("terminal", terminal)
                continue
            require(os.WIFSTOPPED(wait_status),
                    f"unexpected wait status for task {pid}")
            stop_signal = os.WSTOPSIG(wait_status)
            ptrace_event = wait_status >> 16
            delivery_signal = stop_signal
            registered_child_to_release: int | None = None
            if ptrace_event in {
                PTRACE_EVENT_FORK, PTRACE_EVENT_VFORK, PTRACE_EVENT_CLONE,
            }:
                child_tid = _ptrace_event_message(pid)
                require(child_tid > 1, "malformed ptrace task birth event")
                child = tasks.get(child_tid)
                transfer_pidfd = -1
                if child is None:
                    child, child_process, created_process = _capture_task(
                        child_tid, processes,
                    )
                    tasks[child_tid] = child
                    if created_process:
                        transfer_pidfd = child_process.pidfd
                else:
                    require(not child.birth_registered,
                            "duplicate task birth event")
                    child_process = processes[int(child.identity["inner_tgid"])]
                    created_process = child_tid == int(child.identity["inner_tgid"])
                    _ptrace(PTRACE_SETOPTIONS, child_tid, PTRACE_OPTIONS)
                    child.options_set = True
                    registered_child_to_release = child_tid
                event = EVENT_NAMES[ptrace_event]
                child_tgid = int(child.identity["inner_tgid"])
                if ptrace_event in {PTRACE_EVENT_FORK, PTRACE_EVENT_VFORK}:
                    require(created_process,
                            f"{event} event produced a nonleader task")
                if created_process:
                    require(child_tgid == child_tid,
                            "process birth leader identity differs")
                    birth_kind = event
                    counts["process-birth"] += 1
                else:
                    require(ptrace_event == PTRACE_EVENT_CLONE and
                            child_tgid == task_tgid,
                            "thread birth process identity differs")
                    birth_kind = "clone-thread"
                    counts["thread-birth"] += 1
                birth = {
                    "sequence": next_birth_sequence,
                    "kind": birth_kind,
                    "parent_inner_tid": pid,
                    "parent_inner_tgid": task_tgid,
                }
                next_birth_sequence += 1
                child.birth = birth
                child.birth_registered = True
                counts[event] += 1
                emitter.send(
                    event,
                    {
                        "parent_inner_pid": task_tgid,
                        "parent_inner_tid": pid,
                        "process": child_process.identity,
                        "task": _task_evidence(child),
                        "birth": birth,
                    },
                    transfer_pidfd=transfer_pidfd,
                )
                delivery_signal = 0
            elif ptrace_event == PTRACE_EVENT_EXEC:
                former_tid = _ptrace_event_message(pid)
                current_task, current_process, transition = _refresh_after_exec(
                    pid, former_tid, tasks, processes,
                )
                task = current_task
                process = current_process
                counts["exec"] += 1
                counts["exec-rekey"] += int(
                    transition["nonleader_tid_rekey"]
                )
                counts["exec-collapse-task"] += len(
                    transition["collapsed_inner_tids"]
                )
                emitter.send("exec", {
                    "process": process.identity,
                    "task": _task_evidence(task),
                    "exec_transition": transition,
                })
                delivery_signal = 0
            elif ptrace_event == PTRACE_EVENT_EXIT:
                counts["exit-stop"] += 1
                emitter.send("exit-stop", {
                    "process": process.identity,
                    "task": _task_evidence(task),
                    "kernel_exit_status": _ptrace_event_message(pid),
                })
                delivery_signal = 0
            elif stop_signal == signal.SIGSTOP and not task.options_set:
                _ptrace(PTRACE_SETOPTIONS, pid, PTRACE_OPTIONS)
                task.options_set = True
                delivery_signal = 0
            else:
                counts["signal-stop"] += 1
                emitter.send("signal-stop", {
                    "process": process.identity,
                    "task": _task_evidence(task),
                    "signal": stop_signal,
                })
            resumed = _ptrace(
                PTRACE_CONT, pid, delivery_signal,
                context=(
                    f"task resume after ptrace event {ptrace_event} "
                    f"and stop signal {stop_signal}"
                ),
                allow_esrch=ptrace_event == PTRACE_EVENT_EXIT,
            )
            if not resumed:
                counts["exit-resume-esrch"] += 1
            # A provisional child's initial stop can precede its parent's
            # birth-event stop.  Register the kernel edge while both remain
            # stopped, then release the parent before the newly bound child.
            if registered_child_to_release is not None:
                _ptrace(
                    PTRACE_CONT, registered_child_to_release, 0,
                    context="registered provisional child release",
                )

        try:
            unknown, _ = os.waitpid(-1, WALL | os.WNOHANG)
        except ChildProcessError:
            unknown = 0
        require(unknown == 0,
            f"unregistered terminal task status for {unknown}")
        root_terminal = next(
            (item for item in terminals
             if item["inner_tid"] == root_tgid), None,
        )
        require(root_terminal is not None and
                root_terminal["exit_code"] == 0 and
                root_terminal["signal"] is None,
                "projected root process did not exit zero")
        closed = True
        return {
            "root_inner_pid": root_tgid,
            "event_counts": counts,
            "terminal_count": len(terminals),
            "active_processes": 0,
            "active_tasks": 0,
            "local_process_trace_closed": True,
            "local_task_trace_closed": True,
        }
    finally:
        if not closed:
            _cleanup_tracees(tasks, processes)


def _close_publication_copy(publication: auth.PublicationPin) -> None:
    descriptors = [publication.directory_fd, *publication.image_fds]
    for descriptor in sorted(set(descriptors)):
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _close_unlisted_self_fds(keep: set[int]) -> None:
    """Close inherited descriptors after enumerating only this process's fds."""
    directory_fd = os.open(
        "/proc/self/fd", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    try:
        names = os.listdir(directory_fd)
    finally:
        os.close(directory_fd)
    for name in names:
        if not name.isdecimal():
            continue
        descriptor = int(name)
        if descriptor <= 2 or descriptor in keep or descriptor == directory_fd:
            continue
        try:
            os.close(descriptor)
        except OSError as error:
            if error.errno != errno.EBADF:
                raise


def _manager_main(
    channel: socket.socket, outer_lifeline: int, bootstrap_lifeline: int,
    publication: auth.PublicationPin, staged_seal: Any,
    preflight: Any, argv_prefix: list[str], environment: dict[str, str],
    challenge: str, timeout_seconds: float, outer_uid: int, outer_gid: int,
    ioctl_runner: Callable[[int, int, bytearray, bool], object] | None,
) -> int:
    emitter: _Emitter | None = None
    mount_state: Any | None = None
    processes: dict[int, _ProcessIdentity] = {}
    tasks: dict[int, _TaskIdentity] = {}
    try:
        require(os.getpid() == 1, "manager is not PID 1 in the new namespace")
        _set_parent_death_signal(allow_invisible_parent=True)
        require(os.read(bootstrap_lifeline, 1) == b"C",
                "bootstrap did not close its duplicate controller socket")
        channel.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        channel.settimeout(timeout_seconds)
        initial_status = _proc_status("self")
        nspid = _integer_vector(initial_status.get("NSpid", ""), "manager NSpid")
        require(len(nspid) >= 2 and nspid[-1] == 1,
                "manager lacks nested PID-1 identity")
        outer_pid = nspid[0]
        outer_stat = _decode_proc_stat(Path("/proc/self/stat").read_bytes())
        require(outer_stat["pid"] == outer_pid,
                "manager outer stat and NSpid differ")
        emitter = _Emitter(channel, challenge, outer_pid)
        emitter.send("manager", {
            "nspid": nspid,
            "inner_pid": 1,
            "outer_start_ticks": outer_stat["start_ticks"],
            "outer_uid": outer_uid,
            "outer_gid": outer_gid,
            "namespace_uid": os.getuid(),
            "namespace_gid": os.getgid(),
            "pid_namespace": _namespace_identity("pid"),
            "user_namespace": _namespace_identity("user"),
        })

        os.unshare(CLONE_NEWNS)
        auth._projection_mount(None, "/", None, auth.MS_REC | auth.MS_PRIVATE)
        procfs = _install_fresh_procfs()
        mount_state = auth._prepare_checkpoint_projection_mounts(
            publication, staged_seal, preflight.root,
            root_fd=preflight.root_fd,
            root_parent_fd=preflight.root_parent_fd,
            root_name=preflight.root_name,
            outer_uid=outer_uid, outer_gid=outer_gid,
            ioctl_runner=ioctl_runner,
        )
        os.close(preflight.root_fd)
        preflight.root_fd = -1
        os.close(preflight.root_parent_fd)
        preflight.root_parent_fd = -1
        _close_publication_copy(publication)
        _close_unlisted_self_fds({
            channel.fileno(), outer_lifeline, bootstrap_lifeline,
            mount_state.mounted_root_fd, preflight.executable_fd,
        })

        root_pid = _spawn_traceme_workload(
            preflight.executable_fd,
            argv_prefix + mount_state.target_paths,
            environment,
            (
                channel.fileno(), outer_lifeline, bootstrap_lifeline,
                mount_state.mounted_root_fd,
            ),
        )
        os.close(preflight.executable_fd)
        preflight.executable_fd = -1
        stopped, wait_status = os.waitpid(root_pid, WALL | os.WUNTRACED)
        require(stopped == root_pid and os.WIFSTOPPED(wait_status) and
                os.WSTOPSIG(wait_status) == signal.SIGSTOP,
                "projected root did not reach its exact pre-exec stop")
        root_pidfd, root_identity = _open_process_identity(root_pid)
        try:
            root_task_fd, root_task_identity = _open_task_identity(
                root_pid, expected_tgid=root_pid,
            )
        except BaseException:
            os.close(root_pidfd)
            raise
        root_process = _ProcessIdentity(
            root_pidfd, root_identity, {root_pid}, 0,
        )
        root_task = _TaskIdentity(
            root_task_fd, root_task_identity, True, True,
            {
                "sequence": 0,
                "kind": "root",
                "parent_inner_tid": 1,
                "parent_inner_tgid": 1,
            },
        )
        processes[root_pid] = root_process
        tasks[root_pid] = root_task
        _ptrace(PTRACE_SETOPTIONS, root_pid, PTRACE_OPTIONS)

        _install_filter(
            kill_syscalls=MANAGER_KILL_SYSCALLS_X86_64,
            clone_policy=False,
        )
        manager_security = auth._drop_projection_capabilities()
        manager_self_pidfd = os.pidfd_open(1, 0)
        manager_identity = {
            "outer_pid": outer_pid,
            "inner_pid": 1,
            "nspid_visible_from_inner_proc": _integer_vector(
                _proc_status("self").get("NSpid", ""), "inner manager NSpid",
            ),
            "pid_namespace": _namespace_identity("pid"),
            "pid_for_children_namespace":
                _namespace_identity("pid_for_children"),
            "mount_namespace": _namespace_identity("mnt"),
            "user_namespace": _namespace_identity("user"),
            "pidfd": _pidfd_identity(manager_self_pidfd),
        }
        os.close(manager_self_pidfd)
        require(manager_identity["nspid_visible_from_inner_proc"] == [1],
                "fresh procfs exposes a nonlocal manager PID")
        ready_raw = emitter.send("ready", {
            "manager": manager_identity,
            "procfs": procfs,
            "projection_root": str(preflight.root),
            "publication_manifest_sha256":
                publication.evidence["ordered_manifest_sha256"],
            "staged_seal_sha256":
                staged_seal.evidence["ordered_image_seal_sha256"],
            "working_directory": mount_state.working_directory,
            "projected": mount_state.projected,
            "target_paths": mount_state.target_paths,
            "manager_security": manager_security,
            "root_process": root_identity,
            "root_task": _task_evidence(root_task),
            "root_security": _status_security(root_pid),
            "ptrace_options": [
                "TRACEFORK", "TRACEVFORK", "TRACECLONE", "TRACEEXEC",
                "TRACEEXIT", "EXITKILL",
            ],
            "clone_policy": {
                "fork": "allowed-traced-process",
                "vfork": "allowed-traced-process",
                "legacy_clone": "allowed-traced-process-or-thread",
                "clone3": "errno-ENOSYS",
                "threads": "allowed-traced-legacy-clone",
                "CLONE_UNTRACED": "killed",
            },
            "host_filesystem_hidden": False,
            "host_pid_namespace_hidden": False,
            "primary_procfs_rooted_in_private_pid_namespace": True,
            "network_namespace_private": False,
            "pft_exclusion_enforced": False,
            "dmtcp_compatibility_tested": False,
        }, transfer_pidfd=root_pidfd)
        credentials_size = struct.calcsize("3i")
        recv_flags = getattr(socket, "MSG_CMSG_CLOEXEC", 0)
        ack_raw, ancillary, flags, _ = channel.recvmsg(
            MAX_PACKET_BYTES + 1, socket.CMSG_SPACE(credentials_size),
            recv_flags,
        )
        credentials = [
            struct.unpack("3i", data[:credentials_size])
            for level, kind, data in ancillary
            if level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS and
            len(data) >= credentials_size
        ]
        require(ack_raw and len(ack_raw) <= MAX_PACKET_BYTES and
                flags & ~recv_flags == 0 and
                credentials == [(0, 0, 0)],
                "READY ACK lacks exact ancestor credentials")
        ack = auth._decode_exact_json(
            ack_raw, "PID-namespace projection READY ACK",
        )
        require(isinstance(ack, dict) and set(ack) == {
                    "schema", "kind", "policy", "challenge",
                    "controller_outer_pid", "ready_sha256",
                    "approval_included", "controller_supplied_pft_input",
                } and type(ack.get("schema")) is int and ack["schema"] == SCHEMA and
                ack.get("kind") == ACK_KIND and ack.get("policy") == POLICY and
                ack.get("challenge") == challenge and
                ack.get("controller_outer_pid") == outer_pid and
                ack.get("ready_sha256") == hashlib.sha256(ready_raw).hexdigest() and
                ack.get("approval_included") is False and
                ack.get("controller_supplied_pft_input") is False and
                auth.canonical_json_bytes(ack) == ack_raw,
                "READY ACK differs from exact stopped-root challenge")
        _lifelines_alive((outer_lifeline, bootstrap_lifeline))
        processes.clear()
        tasks.clear()
        summary = _trace_until_closed(
            emitter, root_pid, root_process, root_task, timeout_seconds,
            (outer_lifeline, bootstrap_lifeline),
        )
        mount_state.close()
        mount_state = None
        emitter.send("result", summary)
        emitter.send("done", {"outcome": "local-task-trace-closed"})
        channel.close()
        return 0
    except BaseException as error:
        if tasks or processes:
            _cleanup_tracees(tasks, processes)
        if mount_state is not None:
            mount_state.close()
        if emitter is not None:
            try:
                emitter.send("error", {
                    "type": type(error).__name__, "message": str(error),
                })
                emitter.send("done", {"outcome": "local-task-trace-rejected"})
            except BaseException:
                pass
        channel.close()
        return 125


def _bootstrap_main(
    channel: socket.socket, outer_lifeline_read: int,
    publication: auth.PublicationPin, staged_seal: Any, preflight: Any,
    argv_prefix: list[str], environment: dict[str, str], challenge: str,
    timeout_seconds: float,
    ioctl_runner: Callable[[int, int, bytearray, bool], object] | None,
) -> int:
    try:
        _set_parent_death_signal()
        outer_uid = os.getuid()
        outer_gid = os.getgid()
        os.unshare(CLONE_NEWUSER)
        auth._write_projection_user_map(outer_uid, outer_gid)
        os.unshare(CLONE_NEWPID)
        bootstrap_read, bootstrap_write = os.pipe2(os.O_CLOEXEC)
        manager = os.fork()
        if manager == 0:
            os.close(bootstrap_write)
            status = _manager_main(
                channel, outer_lifeline_read, bootstrap_read,
                publication, staged_seal, preflight, argv_prefix, environment,
                challenge, timeout_seconds, outer_uid, outer_gid, ioctl_runner,
            )
            os._exit(status)
        channel.close()
        require(os.write(bootstrap_write, b"C") == 1,
                "bootstrap socket-closure gate write was short")
        os.close(bootstrap_read)
        preflight.close()
        _close_publication_copy(publication)
        _, wait_status = os.waitpid(manager, 0)
        os.close(bootstrap_write)
        if os.WIFEXITED(wait_status):
            return os.WEXITSTATUS(wait_status)
        if os.WIFSIGNALED(wait_status):
            return 128 + os.WTERMSIG(wait_status)
        return 125
    except BaseException:
        try:
            channel.close()
        except BaseException:
            pass
        return 125


@dataclass
class PidnsProjectionSession:
    bootstrap_pid: int
    bootstrap_pidfd: int
    channel: socket.socket
    challenge: str
    timeout_seconds: float
    started_monotonic: float
    projection_root: Path
    outer_lifeline_write: int
    parent_namespaces: dict[str, dict[str, Any]]
    prelaunch_recheck: dict[str, Any]
    executable: dict[str, Any]
    publication_manifest_sha256: str
    staged_seal_sha256: str
    expected_projected: list[dict[str, Any]]
    expected_target_paths: list[str]
    argv_prefix: list[str]
    environment: dict[str, str]
    manager_outer_pid: int | None = None
    manager_pidfd: int = -1
    next_sequence: int = 0
    acknowledged: bool = False
    finished: bool = False
    packets: list[dict[str, Any]] = field(default_factory=list)
    raw_packets: list[bytes] = field(default_factory=list)
    transferred_pidfds: list[dict[str, Any]] = field(default_factory=list)

    def close(self) -> None:
        if not self.finished:
            _abort_session(self)
            self.finished = True
        try:
            self.channel.close()
        except OSError:
            pass
        for item in self.transferred_pidfds:
            descriptor = int(item.get("descriptor", -1))
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                item["descriptor"] = -1
        for descriptor_name in ("manager_pidfd", "bootstrap_pidfd"):
            descriptor = int(getattr(self, descriptor_name))
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                setattr(self, descriptor_name, -1)
        if self.outer_lifeline_write >= 0:
            try:
                os.close(self.outer_lifeline_write)
            except OSError:
                pass
            self.outer_lifeline_write = -1

    def __enter__(self) -> "PidnsProjectionSession":
        return self

    def __exit__(self, *_arguments: object) -> None:
        self.close()


def start_pidns_projection_trace(
    publication: auth.PublicationPin, staged_seal: Any, *,
    projection_root: str | os.PathLike[str], argv_prefix: list[str],
    executable_authority: dict[str, Any], environment: dict[str, str],
    challenge: str, timeout_seconds: float = 30.0,
    ioctl_runner: Callable[[int, int, bytearray, bool], object] | None = None,
) -> PidnsProjectionSession:
    require(isinstance(challenge, str) and auth.HEX64.fullmatch(challenge) is not None,
            "PID-namespace diagnostic challenge must be exact lowercase SHA-256")
    preflight = auth._checkpoint_projection_preflight(
        publication, staged_seal, projection_root=projection_root,
        argv_prefix=argv_prefix, executable_authority=executable_authority,
        environment=environment, timeout_seconds=timeout_seconds,
        ioctl_runner=ioctl_runner,
    )
    parent_namespaces = {
        name: _namespace_identity(name) for name in ("mnt", "user", "pid")
    }
    socket_type = socket.SOCK_SEQPACKET | getattr(socket, "SOCK_CLOEXEC", 0)
    observer: socket.socket | None = None
    manager_channel: socket.socket | None = None
    outer_read = -1
    outer_write = -1
    try:
        observer, manager_channel = socket.socketpair(socket.AF_UNIX, socket_type)
        observer.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        outer_read, outer_write = os.pipe2(os.O_CLOEXEC)
        bootstrap = os.fork()
    except BaseException:
        if observer is not None:
            observer.close()
        if manager_channel is not None:
            manager_channel.close()
        for descriptor in (outer_read, outer_write):
            if descriptor >= 0:
                os.close(descriptor)
        preflight.close()
        raise
    if bootstrap == 0:
        observer.close()
        os.close(outer_write)
        status = _bootstrap_main(
            manager_channel, outer_read, publication, staged_seal, preflight,
            list(argv_prefix), dict(environment), challenge,
            float(timeout_seconds), ioctl_runner,
        )
        os._exit(status)
    manager_channel.close()
    os.close(outer_read)
    preflight.close()
    try:
        bootstrap_pidfd = os.pidfd_open(bootstrap, 0)
    except BaseException:
        observer.close()
        os.close(outer_write)
        try:
            os.kill(bootstrap, signal.SIGKILL)
        except ProcessLookupError:
            pass
        os.waitpid(bootstrap, 0)
        raise
    observer.settimeout(float(timeout_seconds))
    expected_target_paths = [
        f"./{item['path']}"
        for item in publication.evidence["ordered_images"]
    ]
    expected_projected = [{
        "path": item["path"],
        "source": str(preflight.source / item["path"]),
        "target": f"./{item['path']}",
        "device": item["identity"]["device"],
        "inode": item["identity"]["inode"],
        "fsverity_digest": expected["measurement"]["digest"],
        "read_only_mount": True,
    } for item, expected in zip(
        publication.evidence["ordered_images"],
        staged_seal.evidence["images"], strict=True,
    )]
    return PidnsProjectionSession(
        bootstrap_pid=bootstrap, bootstrap_pidfd=bootstrap_pidfd,
        channel=observer, challenge=challenge,
        timeout_seconds=float(timeout_seconds), started_monotonic=time.monotonic(),
        projection_root=preflight.root,
        outer_lifeline_write=outer_write,
        parent_namespaces=parent_namespaces,
        prelaunch_recheck=copy.deepcopy(preflight.recheck.evidence),
        executable=copy.deepcopy(preflight.executable),
        publication_manifest_sha256=
            publication.evidence["ordered_manifest_sha256"],
        staged_seal_sha256=staged_seal.evidence["ordered_image_seal_sha256"],
        expected_projected=expected_projected,
        expected_target_paths=expected_target_paths,
        argv_prefix=list(argv_prefix), environment=copy.deepcopy(environment),
    )


def _decode_packet(raw: bytes) -> dict[str, Any]:
    packet = auth._decode_exact_json(raw, "PID-namespace controller packet")
    require(isinstance(packet, dict) and set(packet) == {
                "schema", "kind", "policy", "challenge",
                "controller_outer_pid", "sequence", "event", "monotonic_ns",
                "payload", "approval_included", "controller_supplied_pft_input",
            } and type(packet.get("schema")) is int and packet["schema"] == SCHEMA and
            packet.get("kind") == PACKET_KIND and packet.get("policy") == POLICY and
            type(packet.get("controller_outer_pid")) is int and
            packet["controller_outer_pid"] > 0 and
            type(packet.get("sequence")) is int and packet["sequence"] >= 0 and
            isinstance(packet.get("event"), str) and packet["event"] and
            type(packet.get("monotonic_ns")) is int and
            packet["monotonic_ns"] > 0 and
            isinstance(packet.get("payload"), dict) and
            type(packet["payload"].get("transferred_pidfd")) is bool and
            packet.get("approval_included") is False and
            packet.get("controller_supplied_pft_input") is False and
            auth.canonical_json_bytes(packet) == raw,
            "PID-namespace controller packet schema differs")
    return packet


def _validate_task_evidence(task: Any, *, require_birth: bool) -> None:
    required = {
        "inner_tid", "inner_tgid", "nspid_visible_from_inner_proc",
        "nstgid_visible_from_inner_proc", "start_ticks",
        "observed_parent_process_inner_pid_untrusted", "process_group_id",
        "session_id",
        "state", "task_directory", "task_directory_held", "birth",
    }
    require(isinstance(task, dict) and set(task) == required and
            type(task.get("inner_tid")) is int and task["inner_tid"] > 1 and
            type(task.get("inner_tgid")) is int and task["inner_tgid"] > 1 and
            task.get("nspid_visible_from_inner_proc", [])[-1:] ==
                [task["inner_tid"]] and
            task.get("nstgid_visible_from_inner_proc", [])[-1:] ==
                [task["inner_tgid"]] and
            type(task.get("start_ticks")) is int and task["start_ticks"] > 0 and
            task.get("task_directory_held") is True and
            isinstance(task.get("task_directory"), dict) and
            set(task["task_directory"]) == {
                "device", "inode", "mode", "link_count",
            }, "task evidence schema or exact identity differs")
    birth = task["birth"]
    if require_birth:
        require(isinstance(birth, dict) and set(birth) == {
                    "sequence", "kind", "parent_inner_tid",
                    "parent_inner_tgid",
                } and type(birth.get("sequence")) is int and
                birth["sequence"] >= 0 and
                isinstance(birth.get("kind"), str) and birth["kind"] and
                type(birth.get("parent_inner_tid")) is int and
                birth["parent_inner_tid"] > 0 and
                type(birth.get("parent_inner_tgid")) is int and
                birth["parent_inner_tgid"] > 0,
                "registered task birth evidence differs")
    else:
        require(birth is None, "provisional task unexpectedly has birth evidence")


def _validate_event_task_binding(
    session: PidnsProjectionSession, packet: dict[str, Any],
) -> None:
    event = packet["event"]
    payload = packet["payload"]
    task = payload.get("task")
    if task is None:
        return
    process = payload.get("process")
    require(isinstance(process, dict) and
            type(process.get("inner_tgid")) is int and
            process.get("inner_pid") == process["inner_tgid"] ==
                task["inner_tgid"] and
            isinstance(process.get("pidfd"), dict),
            "task event is not bound to one process-leader identity")
    process_authority_received = any(
        item["identity"]["nspid"][-1] == task["inner_tgid"]
        for item in session.transferred_pidfds
    )
    require(process_authority_received,
            "task event precedes its process-leader pidfd authority")
    if task["inner_tid"] != task["inner_tgid"]:
        require(payload["transferred_pidfd"] is False,
                "nonleader task illegally transferred a pidfd")

    if event == "provisional-child-stop":
        require(type(payload.get("provisional_process")) is bool and
                payload["provisional_process"] ==
                    (task["inner_tid"] == task["inner_tgid"]) and
                payload["transferred_pidfd"] ==
                    payload["provisional_process"],
                "provisional task/process authority differs")
    elif event in {"fork", "vfork", "clone"}:
        birth = payload.get("birth")
        require(birth == task["birth"] and
                payload.get("parent_inner_tid") ==
                    birth["parent_inner_tid"] and
                payload.get("parent_inner_pid") ==
                    birth["parent_inner_tgid"],
                "task birth edge differs from kernel event packet")
        if birth["kind"] == "clone-thread":
            require(event == "clone" and
                    task["inner_tid"] != task["inner_tgid"] and
                    payload["transferred_pidfd"] is False,
                    "thread clone classification differs")
        else:
            require(birth["kind"] == event and
                    task["inner_tid"] == task["inner_tgid"],
                    "process birth classification differs")
    elif event == "exec":
        transition = payload.get("exec_transition")
        require(isinstance(transition, dict) and set(transition) == {
                    "event_inner_tid", "former_inner_tid",
                    "nonleader_tid_rekey", "collapsed_inner_tids",
                    "collapsed_tasks", "previous_task",
                    "previous_process_start_ticks",
                    "current_process_start_ticks", "executable_epoch",
                } and transition["event_inner_tid"] == task["inner_tid"] ==
                    task["inner_tgid"] and
                transition["nonleader_tid_rekey"] ==
                    (transition["former_inner_tid"] !=
                     transition["event_inner_tid"]) and
                transition["current_process_start_ticks"] ==
                    process["start_ticks"] and
                [item.get("inner_tid")
                 for item in transition["collapsed_tasks"]] ==
                    transition["collapsed_inner_tids"],
                "exec task rekey/collapse evidence differs")
        _validate_task_evidence(
            transition["previous_task"], require_birth=True,
        )
        for collapsed in transition["collapsed_tasks"]:
            _validate_task_evidence(collapsed, require_birth=True)
        require(transition["former_inner_tid"] ==
                transition["previous_task"]["inner_tid"] and
                all(item["inner_tgid"] == task["inner_tgid"]
                    for item in transition["collapsed_tasks"]),
                "exec previous/collapsed task group differs")
    elif event == "terminal":
        require(type(payload.get("process_closed")) is bool and
                type(payload.get("inner_tid")) is int and
                payload["inner_tid"] == task["inner_tid"] and
                payload.get("inner_pid") == task["inner_tgid"],
                "terminal task identity differs")
    else:
        require(event in {"exit-stop", "signal-stop"},
                "unexpected packet carrying task evidence")


def receive_pidns_projection_packet(
    session: PidnsProjectionSession,
) -> dict[str, Any] | None:
    require(not session.finished, "PID-namespace session is already finished")
    credentials_size = struct.calcsize("3i")
    ancillary_space = (
        socket.CMSG_SPACE(credentials_size) +
        socket.CMSG_SPACE(array.array("i").itemsize)
    )
    remaining = (
        session.started_monotonic + session.timeout_seconds - time.monotonic()
    )
    require(remaining > 0, "PID-namespace controller event stream timed out")
    session.channel.settimeout(remaining)
    recv_flags = getattr(socket, "MSG_CMSG_CLOEXEC", 0)
    try:
        raw, ancillary, flags, _ = session.channel.recvmsg(
            MAX_PACKET_BYTES + 1, ancillary_space,
            recv_flags,
        )
    except TimeoutError as error:
        raise PidnsProjectionError(
            "PID-namespace controller event stream timed out"
        ) from error
    if not raw:
        return None
    require(len(raw) <= MAX_PACKET_BYTES and flags & ~recv_flags == 0,
            "truncated PID-namespace controller packet")
    credentials: list[tuple[int, int, int]] = []
    received_fds: list[int] = []
    for level, kind, data in ancillary:
        if level != socket.SOL_SOCKET:
            continue
        if kind == socket.SCM_CREDENTIALS:
            require(len(data) >= credentials_size,
                    "short controller SCM credentials")
            credentials.append(struct.unpack("3i", data[:credentials_size]))
        elif kind == socket.SCM_RIGHTS:
            values = array.array("i")
            usable = len(data) - (len(data) % values.itemsize)
            values.frombytes(data[:usable])
            received_fds.extend(values.tolist())
    try:
        packet = _decode_packet(raw)
        require(packet["challenge"] == session.challenge and
                packet["sequence"] == session.next_sequence,
                "controller challenge or sequence differs")
        sender_pid = packet["controller_outer_pid"]
        require(credentials == [(sender_pid, os.getuid(), os.getgid())],
                "controller packet lacks exact kernel credentials")
        if session.manager_outer_pid is None:
            require(packet["event"] == "manager" and session.next_sequence == 0,
                    "first controller packet is not MANAGER")
            session.manager_outer_pid = sender_pid
            session.manager_pidfd = os.pidfd_open(sender_pid, 0)
            status = _proc_status(sender_pid)
            process_stat = _decode_proc_stat(
                Path(f"/proc/{sender_pid}/stat").read_bytes(),
            )
            nspid = _integer_vector(status.get("NSpid", ""), "outer manager NSpid")
            require(nspid == packet["payload"].get("nspid") and nspid[-1] == 1 and
                    process_stat["pid"] == sender_pid and
                    process_stat["start_ticks"] ==
                        packet["payload"].get("outer_start_ticks") and
                    _namespace_identity("pid", sender_pid) ==
                        packet["payload"].get("pid_namespace") and
                    _namespace_identity("user", sender_pid) ==
                        packet["payload"].get("user_namespace") and
                    packet["payload"].get("outer_uid") == os.getuid() and
                    packet["payload"].get("outer_gid") == os.getgid() and
                    packet["payload"].get("namespace_uid") == 0 and
                    packet["payload"].get("namespace_gid") == 0,
                    "MANAGER exact namespace identity differs")
        else:
            require(sender_pid == session.manager_outer_pid,
                    "controller sender changed within session")
        expected_fd = packet["payload"]["transferred_pidfd"]
        require(len(received_fds) == (1 if expected_fd else 0),
                "controller pidfd transfer count differs")
        if received_fds:
            descriptor = received_fds[-1]
            outer_identity = _pidfd_outer_identity(descriptor)
            process = packet["payload"].get("process")
            if process is None:
                process = packet["payload"].get("root_process")
            require(isinstance(process, dict) and
                    outer_identity["nspid"][-1] == process.get("inner_pid") and
                    outer_identity["pidfd"] == process.get("pidfd"),
                    "transferred pidfd does not bind packet process")
            session.transferred_pidfds.append({
                "sequence": packet["sequence"],
                "event": packet["event"],
                "descriptor": descriptor,
                "identity": outer_identity,
            })
            received_fds.pop()
        task = packet["payload"].get("task")
        if task is not None:
            _validate_task_evidence(
                task,
                require_birth=packet["event"] != "provisional-child-stop",
            )
            _validate_event_task_binding(session, packet)
        session.next_sequence += 1
        session.packets.append(packet)
        session.raw_packets.append(raw)
        return packet
    except BaseException:
        for descriptor in received_fds:
            os.close(descriptor)
        raise


def _validate_ready(
    session: PidnsProjectionSession, packet: dict[str, Any],
) -> None:
    require(packet["event"] == "ready" and not session.acknowledged,
            "expected one unacknowledged READY packet")
    payload = packet["payload"]
    required = {
        "transferred_pidfd", "manager", "procfs", "projection_root",
        "publication_manifest_sha256", "staged_seal_sha256",
        "working_directory", "projected", "target_paths", "manager_security",
        "root_process", "root_task", "root_security", "ptrace_options",
        "clone_policy",
        "host_filesystem_hidden", "host_pid_namespace_hidden",
        "primary_procfs_rooted_in_private_pid_namespace",
        "network_namespace_private", "pft_exclusion_enforced",
        "dmtcp_compatibility_tested",
    }
    require(set(payload) == required and payload["transferred_pidfd"] is True and
            payload["projection_root"] == str(session.projection_root) and
            payload["publication_manifest_sha256"] ==
                session.publication_manifest_sha256 and
            payload["staged_seal_sha256"] == session.staged_seal_sha256 and
            payload["host_filesystem_hidden"] is False and
            payload["host_pid_namespace_hidden"] is False and
            payload["primary_procfs_rooted_in_private_pid_namespace"] is True and
            payload["network_namespace_private"] is False and
            payload["pft_exclusion_enforced"] is False and
            payload["dmtcp_compatibility_tested"] is False and
            payload["ptrace_options"] == [
                "TRACEFORK", "TRACEVFORK", "TRACECLONE", "TRACEEXEC",
                "TRACEEXIT", "EXITKILL",
            ] and payload["clone_policy"] == {
                "fork": "allowed-traced-process",
                "vfork": "allowed-traced-process",
                "legacy_clone": "allowed-traced-process-or-thread",
                "clone3": "errno-ENOSYS",
                "threads": "allowed-traced-legacy-clone",
                "CLONE_UNTRACED": "killed",
            }, "READY policy fields differ")
    manager = payload["manager"]
    require(manager.get("inner_pid") == 1 and
            manager.get("outer_pid") == session.manager_outer_pid and
            manager.get("pidfd") == _pidfd_identity(session.manager_pidfd) and
            manager.get("pid_namespace") == payload["procfs"]["pid_namespace"],
            "READY manager identity differs")
    require(session.parent_namespaces["pid"]["inode"] !=
            manager["pid_namespace"]["inode"] and
            session.parent_namespaces["mnt"]["inode"] !=
            manager["mount_namespace"]["inode"] and
            session.parent_namespaces["user"]["inode"] !=
            manager["user_namespace"]["inode"],
            "READY did not enter fresh user/PID/mount namespaces")
    root_pidfd = session.transferred_pidfds[-1]
    require(root_pidfd["sequence"] == packet["sequence"] and
            root_pidfd["identity"]["nspid"][-1] == 2,
            "READY root pidfd transfer differs")
    root_task = payload["root_task"]
    _validate_task_evidence(root_task, require_birth=True)
    require(root_task["inner_tid"] == root_task["inner_tgid"] == 2 and
            root_task["birth"] == {
                "sequence": 0,
                "kind": "root",
                "parent_inner_tid": 1,
                "parent_inner_tgid": 1,
            }, "READY root task identity differs")
    outer_root_pid = root_pidfd["identity"]["outer_pid"]
    root_status = _proc_status(outer_root_pid)
    root_security = payload["root_security"]
    for name in (
        "CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb", "NoNewPrivs",
        "Seccomp", "Seccomp_filters",
    ):
        require(root_status.get(name, "") == root_security.get(name, ""),
                f"READY root security field {name} differs")
    require(all(root_security.get(name) == "0000000000000000" for name in (
                "CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb",
            )) and root_security.get("NoNewPrivs") == "1" and
            root_security.get("Seccomp") == "2" and
            root_status.get("State", "").startswith("t"),
            "READY root is not stopped and authority-free")
    require(root_security.get("State") == root_status.get("State") and
            _namespace_identity("pid", outer_root_pid) ==
                manager["pid_namespace"] and
            _namespace_identity("mnt", outer_root_pid) ==
                manager["mount_namespace"] and
            _namespace_identity("user", outer_root_pid) ==
                manager["user_namespace"],
            "READY root namespace or stop identity differs")
    manager_status = _proc_status(session.manager_outer_pid)
    for name, value in payload["manager_security"].items():
        if name not in {"securebits", "cap_last_cap"}:
            require(manager_status.get(name, "") == value,
                    f"READY manager security field {name} differs")
    require(payload["target_paths"] == session.expected_target_paths and
            payload["projected"] == session.expected_projected,
            "READY projected authority or target order differs")
    cwd_fd = os.open(
        f"/proc/{session.manager_outer_pid}/cwd",
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    try:
        cwd = os.fstat(cwd_fd)
    finally:
        os.close(cwd_fd)
    root_cwd_fd = os.open(
        f"/proc/{outer_root_pid}/cwd",
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
    )
    try:
        root_cwd = os.fstat(root_cwd_fd)
    finally:
        os.close(root_cwd_fd)
    require(payload["working_directory"] == {
                "device": cwd.st_dev, "inode": cwd.st_ino, "mode": "0700",
            } and cwd.st_dev == root_cwd.st_dev and
            cwd.st_ino == root_cwd.st_ino and
            stat.S_IMODE(cwd.st_mode) == stat.S_IMODE(root_cwd.st_mode) == 0o700 and
            not any(session.projection_root.iterdir()),
            "READY held cwd or outer projection view differs")


def acknowledge_pidns_projection_ready(
    session: PidnsProjectionSession,
) -> dict[str, Any]:
    require(session.packets and session.packets[-1]["event"] == "ready",
            "cannot ACK before exact READY")
    _validate_ready(session, session.packets[-1])
    ready_raw = session.raw_packets[-1]
    ack = {
        "schema": SCHEMA,
        "kind": ACK_KIND,
        "policy": POLICY,
        "challenge": session.challenge,
        "controller_outer_pid": session.manager_outer_pid,
        "ready_sha256": hashlib.sha256(ready_raw).hexdigest(),
        "approval_included": False,
        "controller_supplied_pft_input": False,
    }
    raw = auth.canonical_json_bytes(ack)
    require(session.channel.send(raw) == len(raw), "short READY ACK send")
    session.acknowledged = True
    return ack


def _abort_session(session: PidnsProjectionSession) -> None:
    if session.manager_pidfd >= 0 and session.manager_outer_pid is not None:
        _kill_pidfd(session.manager_pidfd, session.manager_outer_pid)
        poller = select.poll()
        poller.register(session.bootstrap_pidfd, select.POLLIN)
        # Give B a bounded chance to reap M and propagate its failure before
        # using the outer bootstrap kill as the final backstop.
        if not poller.poll(2000):
            _kill_pidfd(session.bootstrap_pidfd, session.bootstrap_pid)
    elif session.bootstrap_pidfd >= 0:
        _kill_pidfd(session.bootstrap_pidfd, session.bootstrap_pid)
    try:
        os.waitpid(session.bootstrap_pid, 0)
    except ChildProcessError:
        pass


def finish_pidns_projection_trace(
    session: PidnsProjectionSession, *, require_success: bool = True,
) -> dict[str, Any]:
    require(not session.finished, "PID-namespace session was already finished")
    failure: BaseException | None = None
    try:
        while True:
            packet = receive_pidns_projection_packet(session)
            if packet is None:
                break
    except BaseException as error:
        failure = error
        _abort_session(session)
    finally:
        try:
            session.channel.close()
        except OSError:
            pass
    wait_status: int | None = None
    if failure is None:
        deadline = session.started_monotonic + session.timeout_seconds
        while time.monotonic() < deadline:
            waited, status = os.waitpid(session.bootstrap_pid, os.WNOHANG)
            if waited == session.bootstrap_pid:
                wait_status = status
                break
            time.sleep(0.002)
        if wait_status is None:
            failure = PidnsProjectionError("bootstrap did not terminate in time")
            _abort_session(session)
    else:
        try:
            _, wait_status = os.waitpid(session.bootstrap_pid, os.WNOHANG)
        except ChildProcessError:
            pass
    session.finished = True
    bootstrap_exit = (
        os.WEXITSTATUS(wait_status)
        if wait_status is not None and os.WIFEXITED(wait_status) else None
    )
    bootstrap_signal = (
        os.WTERMSIG(wait_status)
        if wait_status is not None and os.WIFSIGNALED(wait_status) else None
    )
    events = [packet["event"] for packet in session.packets]
    errors = [packet["payload"] for packet in session.packets
              if packet["event"] == "error"]
    results = [packet["payload"] for packet in session.packets
               if packet["event"] == "result"]
    done = [packet["payload"] for packet in session.packets
            if packet["event"] == "done"]
    succeeded = (
        failure is None and bootstrap_exit == 0 and bootstrap_signal is None and
        session.acknowledged and not errors and
        events[:2] == ["manager", "ready"] and
        events.count("manager") == events.count("ready") == 1 and
        events.count("result") == events.count("done") == 1 and
        events[-2:] == ["result", "done"] and len(results) == len(done) == 1 and
        results[0].get("local_process_trace_closed") is True and
        results[0].get("local_task_trace_closed") is True and
        results[0].get("active_processes") == 0 and
        results[0].get("active_tasks") == 0 and
        done[0] == {
            "outcome": "local-task-trace-closed",
            "transferred_pidfd": False,
        } and
        not any(session.projection_root.iterdir())
    )
    report = {
        "schema": SCHEMA,
        "kind": REPORT_KIND,
        "policy": POLICY,
        "challenge": session.challenge,
        "outcome": (
            "local-task-trace-closed" if succeeded
            else "local-task-trace-rejected"
        ),
        "local_process_trace_closed": succeeded,
        "local_task_trace_closed": succeeded,
        "bootstrap": {
            "outer_pid": session.bootstrap_pid,
            "exit_code": bootstrap_exit,
            "signal": bootstrap_signal,
        },
        "manager_outer_pid": session.manager_outer_pid,
        "publication_manifest_sha256": session.publication_manifest_sha256,
        "staged_seal_sha256": session.staged_seal_sha256,
        "prelaunch_recheck": session.prelaunch_recheck,
        "parent_namespaces": session.parent_namespaces,
        "argv_prefix": session.argv_prefix,
        "environment": session.environment,
        "executable": session.executable,
        "packet_count": len(session.packets),
        "ordered_packet_sha256": hashlib.sha256(
            b"".join(session.raw_packets)
        ).hexdigest(),
        "packets": copy.deepcopy(session.packets),
        "transferred_processes": [{
            key: copy.deepcopy(value) for key, value in item.items()
            if key != "descriptor"
        } for item in session.transferred_pidfds],
        "errors": copy.deepcopy(errors),
        "collection_error": (
            None if failure is None else
            {"type": type(failure).__name__, "message": str(failure)}
        ),
        "elapsed_seconds": time.monotonic() - session.started_monotonic,
        "claim": (
            "same-uid task-aware PID/mount projection diagnostic; host-file, "
            "network, protected-history, DMTCP, release, S2, and S3 boundaries "
            "remain open"
        ),
        "os_evidence_authenticated": False,
        "runtime_qualified": False,
        "promotion_allowed": False,
        "s2_evidence": False,
        "s3_evidence": False,
        "pft_exclusion_enforced": False,
        "host_filesystem_hidden": False,
        "host_pid_namespace_hidden": False,
        "primary_procfs_rooted_in_private_pid_namespace": succeeded,
        "network_namespace_private": False,
        "dmtcp_compatibility_tested": False,
        "threads_supported": succeeded,
        "thread_identity_scope": (
            "held-exact-inner-proc-task-directories" if succeeded else None
        ),
        "leader_pidfds_only": succeeded,
        "approval_included": False,
        "controller_supplied_pft_input": False,
        "pft_use_status": "not-observed-or-excluded",
    }
    session.close()
    if require_success and not succeeded:
        detail = (
            str(failure) if failure is not None else
            errors[0].get("message", "controller rejected") if errors else
            f"bootstrap exit={bootstrap_exit} signal={bootstrap_signal}"
        )
        raise PidnsProjectionError(
            f"PID-namespace projection diagnostic failed: {detail}"
        )
    return report


def run_pidns_projection_trace_diagnostic(
    publication: auth.PublicationPin, staged_seal: Any, **arguments: Any,
) -> auth._Observation:
    session = start_pidns_projection_trace(
        publication, staged_seal, **arguments,
    )
    try:
        manager = receive_pidns_projection_packet(session)
        require(manager is not None and manager["event"] == "manager",
                "controller did not emit MANAGER")
        ready = receive_pidns_projection_packet(session)
        require(ready is not None and ready["event"] == "ready",
                "controller did not emit READY")
        ack = acknowledge_pidns_projection_ready(session)
        report = finish_pidns_projection_trace(session)
    except BaseException:
        if not session.finished:
            _abort_session(session)
            session.finished = True
            session.close()
        raise
    report["action_gate_ack"] = ack
    return auth._make_observation("checkpoint-pidns-projection", report, False)
