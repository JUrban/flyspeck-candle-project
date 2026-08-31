#!/usr/bin/python3
"""Read-only fail-closed gate for the final-head canonical CakeML bootstrap."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import resource
import re
import stat
import subprocess


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
TIME_RECEIPTS = (
    "00-cakeml-heap.time",
    "01-cake-compile-heap.time",
    "02-compiler64Prog.time",
    "03-x64Bootstrap.time",
    "04-x64BootstrapProof.time",
)
TIME_TARGETS = (
    "cakeml-heap",
    "cake_compile_heap",
    "compiler64ProgTheory.uo",
    "x64BootstrapTheory.uo",
    "x64BootstrapProofTheory.uo",
)
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


def stable_file_bytes(path: Path, label: str, *, nonempty: bool = True) -> bytes:
    try:
        descriptor = os.open(
            path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as error:
        raise GateError(f"could not open ordinary {label}: {path}") from error
    try:
        before = os.fstat(descriptor)
        chunks = []
        while block := os.read(descriptor, 1024 * 1024):
            chunks.append(block)
        after = os.fstat(descriptor)
        named = path.stat(follow_symlinks=False)
    finally:
        os.close(descriptor)
    value = b"".join(chunks)
    require(stat.S_ISREG(before.st_mode) and
            (before.st_dev, before.st_ino, before.st_size,
             before.st_mtime_ns, before.st_ctime_ns) ==
            (after.st_dev, after.st_ino, after.st_size,
             after.st_mtime_ns, after.st_ctime_ns) and
            (named.st_dev, named.st_ino) == (after.st_dev, after.st_ino) and
            len(value) == before.st_size,
            f"{label} changed while reading: {path}")
    require(not nonempty or value, f"empty {label}: {path}")
    return value


def git_output(root: Path, *arguments: str) -> str:
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
    return process.stdout.decode("utf-8", errors="strict")


def validate_git(root: Path, expected_head: str, label: str) -> None:
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
    require(not os.path.lexists(graft_path) or
            (graft_path.is_file() and graft_path.stat().st_size == 0),
            f"{label} Git grafts are present")
    status = git_output(root, "status", "--porcelain=v1", "--untracked-files=all")
    require(status == "", f"{label} worktree is not clean")


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


def read_positive_pid(path: Path) -> int:
    try:
        value = int(stable_file_bytes(
            path, "replay controller PID",
        ).decode("ascii").strip())
    except (OSError, UnicodeError, ValueError) as error:
        raise GateError(f"malformed replay controller PID: {path}") from error
    require(value > 1, f"malformed replay controller PID: {value}")
    return value


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
    replay: Path, project_root: Path, project_head: str,
) -> str:
    require(stable_file_bytes(
                replay / "controller_project_root",
                "cold replay controller project root",
            ) == f"{project_root}\n".encode(),
            "cold replay controller project root mismatch")
    require(stable_file_bytes(
                replay / "controller_project_head",
                "cold replay controller project head",
            ) == f"{project_head}\n".encode(),
            "cold replay controller project head mismatch")
    require(stable_file_bytes(
                replay / "controller_script_relative",
                "cold replay controller relative path",
            ) == f"{REPLAY_CONTROLLER_RELATIVE}\n".encode(),
            "cold replay controller relative path mismatch")
    require(stable_file_bytes(
                replay / "cakeml_ignored_products_preflight",
                "cold replay ignored-product preflight",
            ) == b"none\n",
            "cold replay did not record an empty ignored-product preflight")
    controller = project_root / REPLAY_CONTROLLER_RELATIVE
    live = stable_file_bytes(controller, "cold replay controller source")
    committed = git_output(
        project_root, "show", f"{project_head}:{REPLAY_CONTROLLER_RELATIVE}",
    ).encode()
    require(live == committed,
            "cold replay controller source differs from committed authority")
    digest = hashlib.sha256(live).hexdigest()
    require(stable_file_bytes(
                replay / "controller_script_sha256",
                "cold replay controller source digest",
            ) == f"{digest}\n".encode(),
            "cold replay controller source digest mismatch")
    return digest


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
    controller_digest = validate_replay_controller_authority(
        replay, project_root, arguments.project_head,
    )

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
    controller_pid = read_positive_pid(replay / "controller_pid")
    require(controller_pid == arguments.replay_controller_pid,
            "cold replay controller PID differs from pinned launch identity")
    require(not (proc_root / str(controller_pid)).exists(),
            f"cold replay controller is still live: {controller_pid}")
    group_members = process_group_members(proc_root, arguments.replay_process_group)
    require(not group_members,
            f"cold replay process group is still live: {group_members}")
    for relative, target in zip(TIME_RECEIPTS, TIME_TARGETS, strict=True):
        path = replay / relative
        validate_time_receipt(path, hol4, target)
    for relative in CAKEML_POSTCONDITIONS:
        path = cakeml / relative
        stable_file_bytes(path, "cold replay postcondition")

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
        "mem_available_kib": available_kib,
        "minimum_mem_available_kib": required_kib,
        "attempt_root": str(arguments.attempt_root),
        "live_holmake_pids": holmake,
        "live_replay_process_group_members": group_members,
        "inherited_soft_limits": inherited_limits,
        "replay_controller_sha256": controller_digest,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--project-head", required=True)
    parser.add_argument("--replay-root", type=Path, required=True)
    parser.add_argument("--replay-controller-pid", type=int, required=True)
    parser.add_argument("--replay-process-group", type=int, required=True)
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
            arguments.replay_process_group > 1,
            "replay launch identity must use positive non-system IDs")
    project_head = validate_self_authority(
        arguments.project_root, arguments.project_head,
    )
    result = validate_gate(arguments)
    result["project_gate_head"] = project_head
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (GateError, OSError, UnicodeError) as error:
        raise SystemExit(f"canonical bootstrap gate rejected: {error}") from error
