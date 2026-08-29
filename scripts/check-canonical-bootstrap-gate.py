#!/usr/bin/python3
"""Read-only fail-closed gate for the final-head canonical CakeML bootstrap."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import subprocess


GIT_ENVIRONMENT = {
    "PATH": "/usr/bin:/bin",
    "LC_ALL": "C",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_TERMINAL_PROMPT": "0",
}
TIME_RECEIPTS = (
    "01-cake-compile-heap.time",
    "02-compiler64Prog.time",
    "03-x64Bootstrap.time",
    "04-x64BootstrapProof.time",
)
CAKEML_POSTCONDITIONS = (
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


def git_output(root: Path, *arguments: str) -> str:
    process = subprocess.run(
        ["/usr/bin/git", "-C", str(root), *arguments],
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
    observed = git_output(root, "rev-parse", "HEAD").strip()
    require(observed == expected_head, f"{label} head mismatch: {observed}")
    status = git_output(root, "status", "--porcelain=v1", "--untracked-files=all")
    require(status == "", f"{label} worktree is not clean")


def read_positive_pid(path: Path) -> int:
    try:
        value = int(path.read_text(encoding="ascii").strip())
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
            executable = os.readlink(child / "exe")
        except (FileNotFoundError, PermissionError, ProcessLookupError, OSError):
            continue
        if command_name == "Holmake" or Path(executable).name == "Holmake":
            result.append(int(child.name))
    return sorted(result)


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


def validate_gate(arguments: argparse.Namespace) -> dict[str, object]:
    replay = ordinary_exact_directory(arguments.replay_root, "replay root")
    candle = ordinary_exact_directory(arguments.candle_root, "Candle root")
    cakeml = ordinary_exact_directory(arguments.cakeml_root, "CakeML root")
    hol4 = ordinary_exact_directory(arguments.hol4_root, "HOL4 root")
    proc_root = ordinary_exact_directory(arguments.proc_root, "proc root")

    validate_git(candle, arguments.candle_head, "Candle")
    validate_git(cakeml, arguments.cakeml_head, "CakeML")
    validate_git(hol4, arguments.hol4_head, "HOL4")

    require((replay / "stage").read_text(encoding="ascii") == "complete\n",
            "cold replay has not completed all four stages")
    require((replay / "finished_utc").is_file() and
            (replay / "finished_utc").stat().st_size > 0,
            "cold replay has no completion timestamp")
    controller_pid = read_positive_pid(replay / "controller_pid")
    require(not (proc_root / str(controller_pid)).exists(),
            f"cold replay controller is still live: {controller_pid}")
    for relative in TIME_RECEIPTS:
        path = replay / relative
        require(path.is_file() and path.stat().st_size > 0,
                f"missing cold replay time receipt: {path}")
    for relative in CAKEML_POSTCONDITIONS:
        path = cakeml / relative
        require(path.is_file() and path.stat().st_size > 0,
                f"missing cold replay postcondition: {path}")

    holmake = live_holmake_pids(proc_root)
    require(not holmake, f"Holmake is still live: {holmake}")
    available_kib = memory_available_kib(proc_root)
    required_kib = arguments.minimum_mem_available_gib * 1024 * 1024
    require(available_kib >= required_kib,
            f"insufficient MemAvailable: {available_kib} KiB < {required_kib} KiB")
    require(not os.path.lexists(arguments.attempt_root),
            f"canonical attempt root already exists: {arguments.attempt_root}")
    ordinary_exact_directory(arguments.attempt_root.parent, "attempt parent")

    return {
        "gate": "canonical-cakeml-bootstrap-ready",
        "candle_head": arguments.candle_head,
        "cakeml_head": arguments.cakeml_head,
        "hol4_head": arguments.hol4_head,
        "replay_controller_pid": controller_pid,
        "mem_available_kib": available_kib,
        "minimum_mem_available_kib": required_kib,
        "attempt_root": str(arguments.attempt_root),
        "live_holmake_pids": holmake,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-root", type=Path, required=True)
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
    print(json.dumps(validate_gate(arguments), sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (GateError, OSError, UnicodeError) as error:
        raise SystemExit(f"canonical bootstrap gate rejected: {error}") from error
