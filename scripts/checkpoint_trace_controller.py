#!/usr/bin/python3
"""Continuous local ptrace lifecycle diagnostic.

This prototype exists to exercise process-tree coverage that the checkpoint
scaffold does not yet provide.  It is intentionally non-promotable: the
controller and observer run under the same unprotected uid, so every assurance
and release flag in the returned report remains false even after a locally
complete trace.
"""

from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import stat
import struct
import time
from typing import Any


class TraceControllerError(RuntimeError):
    """The local lifecycle diagnostic failed closed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TraceControllerError(message)


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ) + "\n").encode("utf-8")


PACKET_SCHEMA = 1
PACKET_KIND = "candle-checkpoint-local-trace-packet-v1"
REPORT_KIND = "candle-checkpoint-local-trace-diagnostic-v1"
TRUST_SCOPE = "same-uid-unprotected-local-diagnostic-only-v1"
MAX_PACKET_BYTES = 64 * 1024
WALL = getattr(os, "__WALL", 0x40000000)

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
PR_SET_CHILD_SUBREAPER = 36
FORBIDDEN_TARGET = re.compile(r"pft", re.IGNORECASE)
EVENT_NAMES = {
    PTRACE_EVENT_FORK: "fork",
    PTRACE_EVENT_VFORK: "vfork",
    PTRACE_EVENT_CLONE: "clone",
    PTRACE_EVENT_EXEC: "exec",
    PTRACE_EVENT_EXIT: "exit-stop",
}


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
    return library


def _ptrace(request: int, pid: int, data: int = 0) -> None:
    result = _libc().ptrace(request, pid, None, ctypes.c_void_p(data))
    if result != 0:
        error_number = ctypes.get_errno()
        raise TraceControllerError(
            f"ptrace request {request} failed for pid {pid}: errno {error_number}"
        )


def _ptrace_event_message(pid: int) -> int:
    message = ctypes.c_ulong()
    result = _libc().ptrace(
        PTRACE_GETEVENTMSG, pid, None, ctypes.byref(message),
    )
    if result != 0:
        error_number = ctypes.get_errno()
        raise TraceControllerError(
            f"ptrace event message failed for pid {pid}: errno {error_number}"
        )
    return int(message.value)


def _set_subreaper() -> None:
    if _libc().prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
        error_number = ctypes.get_errno()
        raise TraceControllerError(
            f"could not enable child subreaper: errno {error_number}"
        )


def _decode_proc_stat(data: bytes) -> dict[str, int | str]:
    try:
        text = data.decode("ascii")
        left = text.index("(")
        right = text.rindex(")")
        pid = int(text[:left].strip())
        fields = text[right + 2:].split()
        require(len(fields) >= 20, "short /proc stat record")
        return {
            "pid": pid,
            "state": fields[0],
            "parent_pid": int(fields[1]),
            "process_group_id": int(fields[2]),
            "session_id": int(fields[3]),
            "start_ticks": int(fields[19]),
        }
    except (UnicodeError, ValueError) as error:
        raise TraceControllerError("malformed /proc stat record") from error


def _namespace_identity(pid: int, name: str) -> dict[str, int | str]:
    path = Path(f"/proc/{pid}/ns/{name}")
    value = path.stat()
    return {
        "name": name,
        "device": value.st_dev,
        "inode": value.st_ino,
        "target": os.readlink(path),
    }


def _pidfd_identity(descriptor: int) -> dict[str, int | str]:
    value = os.fstat(descriptor)
    return {
        "device": value.st_dev,
        "inode": value.st_ino,
        "mode": f"{stat.S_IMODE(value.st_mode):04o}",
    }


def _process_identity(pid: int, pidfd: int) -> dict[str, Any]:
    proc = Path(f"/proc/{pid}")
    before = _decode_proc_stat((proc / "stat").read_bytes())
    executable_path = os.readlink(proc / "exe")
    executable = (proc / "exe").stat()
    namespaces = {
        name: _namespace_identity(pid, name)
        for name in ("mnt", "net", "pid", "user")
    }
    after = _decode_proc_stat((proc / "stat").read_bytes())
    require(before == after, f"process {pid} changed identity during capture")
    return {
        **before,
        "executable": {
            "path": executable_path,
            "device": executable.st_dev,
            "inode": executable.st_ino,
            "mode": f"{stat.S_IMODE(executable.st_mode):04o}",
        },
        "namespaces": namespaces,
        "pidfd": _pidfd_identity(pidfd),
    }


def _open_identity(pid: int) -> tuple[int, dict[str, Any]]:
    require(hasattr(os, "pidfd_open"), "kernel lacks pidfd_open")
    try:
        descriptor = os.pidfd_open(pid, 0)
    except OSError as error:
        raise TraceControllerError(f"could not pin pid {pid}") from error
    try:
        return descriptor, _process_identity(pid, descriptor)
    except BaseException:
        os.close(descriptor)
        raise


def _kill_pidfd(descriptor: int, pid: int) -> None:
    try:
        if hasattr(signal, "pidfd_send_signal"):
            signal.pidfd_send_signal(descriptor, signal.SIGKILL, None, 0)
        else:
            os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _exact_launch(argv: list[str], environment: dict[str, str]) -> None:
    require(isinstance(argv, list) and argv and
            all(isinstance(item, str) and item and "\0" not in item
                for item in argv), "malformed trace argv")
    executable = argv[0]
    require(executable.startswith("/") and
            Path(executable).resolve(strict=True) == Path(executable) and
            Path(executable).is_file(),
            "trace executable must be an absolute ordinary canonical path")
    require(FORBIDDEN_TARGET.search("\n".join(argv)) is None,
            "forbidden target namespace in trace argv")
    require(isinstance(environment, dict) and environment and
            all(isinstance(name, str) and name and "=" not in name and
                "\0" not in name and isinstance(value, str) and
                "\0" not in value for name, value in environment.items()),
            "malformed trace environment")
    require(FORBIDDEN_TARGET.search("\n".join(
                f"{name}={value}" for name, value in environment.items()
            )) is None,
            "forbidden target namespace in trace environment")


@dataclass
class _Tracee:
    pidfd: int
    identity: dict[str, Any]
    options_set: bool


class _Emitter:
    def __init__(self, channel: socket.socket) -> None:
        self.channel = channel
        self.controller_pid = os.getpid()
        self.sequence = 0

    def send(self, event: str, payload: dict[str, Any]) -> None:
        packet = {
            "schema": PACKET_SCHEMA,
            "kind": PACKET_KIND,
            "controller_pid": self.controller_pid,
            "sequence": self.sequence,
            "monotonic_ns": time.monotonic_ns(),
            "event": event,
            "payload": payload,
        }
        data = canonical_json_bytes(packet)
        require(len(data) <= MAX_PACKET_BYTES, "trace packet is too large")
        sent = self.channel.send(data)
        require(sent == len(data), "short trace packet send")
        self.sequence += 1


def _spawn_tracee(
    argv: list[str], environment: dict[str, str], channel: socket.socket,
) -> int:
    pid = os.fork()
    if pid == 0:
        try:
            channel.close()
            os.setpgid(0, 0)
            devnull = os.open("/dev/null", os.O_RDWR | os.O_CLOEXEC)
            try:
                for descriptor in (0, 1, 2):
                    os.dup2(devnull, descriptor)
            finally:
                if devnull > 2:
                    os.close(devnull)
            result = _libc().ptrace(PTRACE_TRACEME, 0, None, None)
            if result != 0:
                os._exit(126)
            os.kill(os.getpid(), signal.SIGSTOP)
            os.execve(argv[0], argv, environment)
        except BaseException:
            os._exit(127)
    return pid


def _proc_parent_map() -> dict[int, tuple[int, str]]:
    processes: dict[int, tuple[int, str]] = {}
    try:
        entries = list(Path("/proc").iterdir())
    except OSError as error:
        raise TraceControllerError("could not scan /proc") from error
    for entry in entries:
        if not entry.name.isdecimal():
            continue
        try:
            value = _decode_proc_stat((entry / "stat").read_bytes())
        except (OSError, TraceControllerError):
            continue
        processes[int(value["pid"])] = (
            int(value["parent_pid"]), str(value["state"]),
        )
    return processes


def _find_untraced_descendants(
    controller_pid: int, tracees: dict[int, _Tracee],
) -> list[int]:
    processes = _proc_parent_map()
    known = set(tracees)
    offenders: list[int] = []
    for pid, (_, state) in processes.items():
        if pid == controller_pid or pid in known or state in {"Z", "X", "x"}:
            continue
        visited: set[int] = set()
        parent = processes.get(pid, (0, ""))[0]
        while parent > 1 and parent not in visited:
            if parent == controller_pid or parent in known:
                offenders.append(pid)
                break
            visited.add(parent)
            parent = processes.get(parent, (0, ""))[0]
    return sorted(set(offenders))


def _cleanup_tracees(tracees: dict[int, _Tracee]) -> None:
    for pid, process in list(tracees.items()):
        _kill_pidfd(process.pidfd, pid)
    deadline = time.monotonic() + 2.0
    while tracees and time.monotonic() < deadline:
        try:
            pid, _ = os.waitpid(-1, WALL | os.WNOHANG)
        except ChildProcessError:
            break
        if pid == 0:
            time.sleep(0.005)
            continue
        process = tracees.pop(pid, None)
        if process is not None:
            os.close(process.pidfd)
    for process in tracees.values():
        os.close(process.pidfd)
    tracees.clear()


def _trace_workload(
    emitter: _Emitter, argv: list[str], environment: dict[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    tracees: dict[int, _Tracee] = {}
    event_counts = {name: 0 for name in (
        "fork", "vfork", "clone", "exec", "exit-stop", "terminal",
        "signal-stop",
    )}
    root_pid = _spawn_tracee(argv, environment, emitter.channel)
    locally_closed = False
    try:
        stopped_pid, status = os.waitpid(root_pid, WALL | os.WUNTRACED)
        require(stopped_pid == root_pid and os.WIFSTOPPED(status) and
                os.WSTOPSIG(status) == signal.SIGSTOP,
                "root tracee did not enter the pre-exec stop")
        root_pidfd, root_identity = _open_identity(root_pid)
        tracees[root_pid] = _Tracee(root_pidfd, root_identity, True)
        _ptrace(PTRACE_SETOPTIONS, root_pid, PTRACE_OPTIONS)
        emitter.send("tracee-launch", {
            "root_pid": root_pid,
            "process": root_identity,
            "ptrace_options": [
                "TRACEFORK", "TRACEVFORK", "TRACECLONE", "TRACEEXEC",
                "TRACEEXIT", "EXITKILL",
            ],
        })
        _ptrace(PTRACE_CONT, root_pid)
        deadline = time.monotonic() + timeout_seconds
        next_scan = 0.0

        while tracees:
            require(time.monotonic() < deadline, "trace workload timed out")
            try:
                pid, status = os.waitpid(-1, WALL | os.WNOHANG | os.WUNTRACED)
            except ChildProcessError as error:
                raise TraceControllerError(
                    "traced process tree vanished before terminal closure"
                ) from error
            if pid == 0:
                now = time.monotonic()
                if now >= next_scan:
                    offenders = _find_untraced_descendants(
                        os.getpid(), tracees,
                    )
                    require(not offenders,
                            f"untraced descendant detected: {offenders}")
                    next_scan = now + 0.010
                time.sleep(0.001)
                continue

            process = tracees.get(pid)
            require(process is not None,
                    f"unregistered child status observed for pid {pid}")
            if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                event_counts["terminal"] += 1
                emitter.send("terminal", {
                    "process": process.identity,
                    "exit_code": os.WEXITSTATUS(status)
                        if os.WIFEXITED(status) else None,
                    "signal": os.WTERMSIG(status)
                        if os.WIFSIGNALED(status) else None,
                })
                os.close(process.pidfd)
                del tracees[pid]
                continue

            require(os.WIFSTOPPED(status), f"unexpected wait status for pid {pid}")
            stop_signal = os.WSTOPSIG(status)
            ptrace_event = status >> 16
            delivery_signal = stop_signal

            if ptrace_event in {
                PTRACE_EVENT_FORK, PTRACE_EVENT_VFORK, PTRACE_EVENT_CLONE,
            }:
                child_pid = _ptrace_event_message(pid)
                require(child_pid > 0 and child_pid not in tracees,
                        "duplicate or malformed ptrace child event")
                child_pidfd, child_identity = _open_identity(child_pid)
                tracees[child_pid] = _Tracee(
                    child_pidfd, child_identity, False,
                )
                name = EVENT_NAMES[ptrace_event]
                event_counts[name] += 1
                emitter.send(name, {
                    "parent": process.identity,
                    "child": child_identity,
                })
                delivery_signal = 0
            elif ptrace_event == PTRACE_EVENT_EXEC:
                current_identity = _process_identity(pid, process.pidfd)
                require(current_identity["start_ticks"] ==
                        process.identity["start_ticks"] and
                        current_identity["pidfd"] == process.identity["pidfd"],
                        "process identity changed across exec")
                process.identity = current_identity
                event_counts["exec"] += 1
                emitter.send("exec", {"process": current_identity})
                delivery_signal = 0
            elif ptrace_event == PTRACE_EVENT_EXIT:
                event_counts["exit-stop"] += 1
                emitter.send("exit-stop", {
                    "process": process.identity,
                    "kernel_exit_status": _ptrace_event_message(pid),
                })
                delivery_signal = 0
            else:
                if stop_signal == signal.SIGSTOP and not process.options_set:
                    _ptrace(PTRACE_SETOPTIONS, pid, PTRACE_OPTIONS)
                    process.options_set = True
                    delivery_signal = 0
                else:
                    event_counts["signal-stop"] += 1
                    emitter.send("signal-stop", {
                        "process": process.identity,
                        "signal": stop_signal,
                    })
            _ptrace(PTRACE_CONT, pid, delivery_signal)

        offenders = _find_untraced_descendants(os.getpid(), tracees)
        require(not offenders,
                f"untraced descendants remained after closure: {offenders}")
        try:
            unknown_pid, _ = os.waitpid(-1, WALL | os.WNOHANG)
        except ChildProcessError:
            unknown_pid = 0
        require(unknown_pid == 0,
                f"unregistered child terminal status for pid {unknown_pid}")
        locally_closed = True
        return {
            "root_pid": root_pid,
            "event_counts": event_counts,
            "active_tracees": 0,
            "local_trace_closed": True,
        }
    finally:
        if not locally_closed:
            _cleanup_tracees(tracees)


def _controller_main(
    channel: socket.socket, argv: list[str], environment: dict[str, str],
    timeout_seconds: float,
) -> int:
    emitter = _Emitter(channel)
    try:
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        _set_subreaper()
        own_pidfd, own_identity = _open_identity(os.getpid())
        try:
            emitter.send("controller", {
                "trust_scope": TRUST_SCOPE,
                "process": own_identity,
                "subreaper": True,
            })
        finally:
            os.close(own_pidfd)
        summary = _trace_workload(
            emitter, argv, environment, timeout_seconds,
        )
        emitter.send("result", summary)
        emitter.send("done", {"outcome": "local-trace-closed"})
        return 0
    except BaseException as error:
        try:
            emitter.send("error", {
                "type": type(error).__name__,
                "message": str(error),
            })
            emitter.send("done", {"outcome": "local-trace-rejected"})
        except BaseException:
            pass
        return 1
    finally:
        channel.close()


@dataclass
class TraceSession:
    controller_pid: int
    controller_pidfd: int
    channel: socket.socket
    next_sequence: int = 0
    collected: bool = False

    def close(self) -> None:
        self.channel.close()
        if self.controller_pidfd >= 0:
            os.close(self.controller_pidfd)
            self.controller_pidfd = -1


def start_trace(
    argv: list[str], environment: dict[str, str], timeout_seconds: float = 30.0,
) -> TraceSession:
    _exact_launch(argv, environment)
    require(isinstance(timeout_seconds, (int, float)) and
            not isinstance(timeout_seconds, bool) and
            0 < timeout_seconds <= 300,
            "trace timeout must be in (0, 300] seconds")
    socket_type = socket.SOCK_SEQPACKET | getattr(socket, "SOCK_CLOEXEC", 0)
    observer, controller = socket.socketpair(socket.AF_UNIX, socket_type)
    observer.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    pid = os.fork()
    if pid == 0:
        observer.close()
        status = _controller_main(
            controller, list(argv), dict(environment), float(timeout_seconds),
        )
        os._exit(status)
    controller.close()
    try:
        pidfd = os.pidfd_open(pid, 0)
    except BaseException:
        observer.close()
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        os.waitpid(pid, 0)
        raise
    observer.settimeout(float(timeout_seconds) + 10.0)
    return TraceSession(pid, pidfd, observer)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for name, item in pairs:
        require(name not in value, "duplicate JSON key in trace packet")
        value[name] = item
    return value


def receive_packet(session: TraceSession) -> dict[str, Any] | None:
    credentials_size = struct.calcsize("3i")
    try:
        data, ancillary, flags, _ = session.channel.recvmsg(
            MAX_PACKET_BYTES + 1, socket.CMSG_SPACE(credentials_size),
        )
    except TimeoutError as error:
        raise TraceControllerError("trace controller event stream timed out") from error
    if not data:
        return None
    require(len(data) <= MAX_PACKET_BYTES and flags == 0,
            "truncated or oversized trace packet")
    credentials = [
        struct.unpack("3i", item[:credentials_size])
        for level, kind, item in ancillary
        if level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS and
        len(item) >= credentials_size
    ]
    require(credentials == [(
                session.controller_pid, os.getuid(), os.getgid(),
            )],
            "trace packet sender credentials do not match the controller")
    try:
        packet = json.loads(
            data.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys,
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise TraceControllerError("malformed trace packet JSON") from error
    require(isinstance(packet, dict) and set(packet) == {
                "schema", "kind", "controller_pid", "sequence",
                "monotonic_ns", "event", "payload",
            } and packet.get("schema") == PACKET_SCHEMA and
            packet.get("kind") == PACKET_KIND and
            packet.get("controller_pid") == session.controller_pid and
            type(packet.get("sequence")) is int and
            packet["sequence"] == session.next_sequence and
            type(packet.get("monotonic_ns")) is int and
            packet["monotonic_ns"] > 0 and
            isinstance(packet.get("event"), str) and packet["event"] and
            isinstance(packet.get("payload"), dict) and
            canonical_json_bytes(packet) == data,
            "trace packet contract mismatch")
    session.next_sequence += 1
    return packet


def _process_identities(packet: dict[str, Any]) -> list[dict[str, Any]]:
    payload = packet["payload"]
    return [
        value for name, value in payload.items()
        if name in {"process", "parent", "child"} and isinstance(value, dict)
    ]


def _validate_identity_stream(packets: list[dict[str, Any]]) -> None:
    identities: dict[int, tuple[int, tuple[int, int]]] = {}
    for packet in packets:
        for identity in _process_identities(packet):
            require(type(identity.get("pid")) is int and identity["pid"] > 0 and
                    type(identity.get("start_ticks")) is int and
                    identity["start_ticks"] > 0 and
                    isinstance(identity.get("pidfd"), dict) and
                    type(identity["pidfd"].get("device")) is int and
                    type(identity["pidfd"].get("inode")) is int,
                    "malformed process identity in trace stream")
            stable = (
                identity["start_ticks"],
                (identity["pidfd"]["device"], identity["pidfd"]["inode"]),
            )
            previous = identities.setdefault(identity["pid"], stable)
            require(previous == stable,
                    "pid identity changed within trace event stream")


def collect_trace(
    session: TraceSession, initial_packets: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    require(not session.collected, "trace session was already collected")
    packets = list(initial_packets or [])
    try:
        while True:
            packet = receive_packet(session)
            if packet is None:
                break
            packets.append(packet)
    finally:
        session.channel.close()
    _, status = os.waitpid(session.controller_pid, 0)
    session.collected = True
    os.close(session.controller_pidfd)
    session.controller_pidfd = -1
    require(packets and packets[-1]["event"] == "done" and
            sum(packet["event"] == "done" for packet in packets) == 1,
            "trace controller did not close its event stream")
    _validate_identity_stream(packets)
    controller_exit_code = (
        os.WEXITSTATUS(status) if os.WIFEXITED(status) else None
    )
    controller_signal = (
        os.WTERMSIG(status) if os.WIFSIGNALED(status) else None
    )
    errors = [packet["payload"] for packet in packets
              if packet["event"] == "error"]
    locally_closed = (
        controller_exit_code == 0 and controller_signal is None and not errors and
        packets[-1]["payload"].get("outcome") == "local-trace-closed"
    )
    return {
        "schema": 1,
        "kind": REPORT_KIND,
        "trust_scope": TRUST_SCOPE,
        "outcome": (
            "local-trace-closed" if locally_closed else "local-trace-rejected"
        ),
        "local_trace_closed": locally_closed,
        "controller": {
            "pid": session.controller_pid,
            "exit_code": controller_exit_code,
            "signal": controller_signal,
        },
        "packet_count": len(packets),
        "ordered_packet_sha256": hashlib.sha256(b"".join(
            canonical_json_bytes(packet) for packet in packets
        )).hexdigest(),
        "packets": packets,
        "errors": errors,
        "os_evidence_authenticated": False,
        "trusted_lifecycle": False,
        "approval_status": "unapproved-local-prototype",
        "promotion_allowed": False,
        "s2_evidence": False,
        "s3_evidence": False,
        "pft_used": False,
        "limitations": [
            "controller and observer share the same unprotected uid",
            "no protected launcher, cgroup, storage, signer, or finalizer",
            "local ptrace and credential observations are diagnostic only",
            "tracee standard streams are redirected to /dev/null",
        ],
    }


def run_trace(
    argv: list[str], environment: dict[str, str], timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    return collect_trace(start_trace(argv, environment, timeout_seconds))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("argv", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    argv = arguments.argv
    if argv and argv[0] == "--":
        argv = argv[1:]
    report = run_trace(
        argv, {"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        arguments.timeout_seconds,
    )
    os.write(1, canonical_json_bytes(report))


if __name__ == "__main__":
    try:
        main()
    except (OSError, TraceControllerError, ValueError) as error:
        raise SystemExit(f"local trace diagnostic rejected: {error}") from error
