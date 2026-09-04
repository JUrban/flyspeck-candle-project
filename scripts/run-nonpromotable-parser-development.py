#!/usr/bin/env python3
"""Run an authenticated parser plan with an explicitly development runtime.

This runner exists only for frontend iteration.  It deliberately does not
consume or manufacture Candle's ordinary linked-runtime provenance and every
published result is categorically non-promotable.  The formal parser
diagnostic controller remains the only route to a promotable parser receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import resource
import stat
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any


CAPABILITY_ARGUMENT = "--candle-parser-diagnostic-capability-v1"
RUN_ARGUMENT = "--candle-parser-diagnostic-v1"
CAPABILITY_LINE = (
    b"CANDLE_CAMLPARSER_DIAGNOSTIC_CAPABILITY_V1\t"
    b"caml_parser$run\tstdin-exact-bytes\tparser-only\t"
    b"no-inference\tno-evaluation\n"
)
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
PROFILE_CONTRACTS = {
    "pilot": {
        "count": 20,
        "schema": 2,
        "kind": "candle-flyspeck-caml-parser-diagnostic-plan",
        "result_kind": "nonpromotable-development-parser-pilot",
    },
    "all-inventory": {
        "count": 400,
        "schema": 3,
        "kind": "candle-flyspeck-caml-parser-all-inventory-diagnostic-plan",
        "result_kind": "nonpromotable-development-parser-all-inventory",
    },
}
SOURCE_PATH = Path(__file__).resolve()
SOURCE_BYTES = SOURCE_PATH.read_bytes()


class ContractError(ValueError):
    """A development-run input did not satisfy its explicit contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def _pairs_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def decode_object(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ContractError(f"cannot decode {label}: {error}") from error
    require(isinstance(value, dict), f"{label} is not an object")
    return value


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def bytes_record(data: bytes, path: str | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    if path is not None:
        record["path"] = path
    return record


def read_regular(path: Path, label: str) -> bytes:
    try:
        before = path.lstat()
        data = path.read_bytes()
        after = path.lstat()
    except OSError as error:
        raise ContractError(f"cannot read {label}: {path}: {error}") from error
    require(
        stat.S_ISREG(before.st_mode)
        and (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        and len(data) == before.st_size,
        f"{label} is not a stable ordinary file: {path}",
    )
    return data


def safe_relative(value: Any, label: str) -> Path:
    require(isinstance(value, str), f"{label} path is not a string")
    path = Path(value)
    require(
        value == path.as_posix()
        and not path.is_absolute()
        and value not in {"", "."}
        and ".." not in path.parts,
        f"unsafe {label} path: {value!r}",
    )
    return path


def validate_plan(plan_root: Path, profile: str) -> tuple[dict[str, Any], bytes, list[bytes]]:
    contract = PROFILE_CONTRACTS[profile]
    plan_data = read_regular(plan_root / "plan.json", "parser plan")
    plan = decode_object(plan_data, "parser plan")
    promotion = plan.get("promotion")
    inputs = plan.get("inputs")
    count = contract["count"]
    require(plan.get("schema") == contract["schema"], "parser plan schema mismatch")
    require(plan.get("kind") == contract["kind"], "parser plan kind mismatch")
    require(
        isinstance(promotion, dict)
        and promotion.get("eligible") is False
        and promotion.get("s1_evidence") is False
        and promotion.get("s2_evidence") is False
        and promotion.get("s3_evidence") is False,
        "parser plan is not explicitly non-promotable",
    )
    require(
        plan.get("input_count") == plan.get("ready_count") == count
        and plan.get("unsupported_count") == 0
        and isinstance(inputs, list)
        and len(inputs) == count,
        "parser plan does not contain the exact ready profile",
    )
    if profile == "all-inventory":
        require(plan.get("profile", {}).get("id") == profile,
                "all-inventory profile identity mismatch")

    prepared_inputs = []
    for index, entry in enumerate(inputs):
        require(
            isinstance(entry, dict)
            and entry.get("index") == index
            and entry.get("status") == "ready",
            f"malformed parser input record: {index}",
        )
        prepared = entry.get("prepared_input")
        require(isinstance(prepared, dict), f"missing prepared input: {index}")
        relative = safe_relative(prepared.get("path"), f"prepared input {index}")
        data = read_regular(plan_root / relative, f"prepared input {index}")
        require(
            prepared == bytes_record(data, relative.as_posix()),
            f"prepared input identity mismatch: {index}",
        )
        prepared_inputs.append(data)
    return plan, plan_data, prepared_inputs


def validate_development_link_receipt(
    receipt_path: Path, runtime_path: Path, runtime_data: bytes,
) -> tuple[bytes, dict[str, str]]:
    require(receipt_path.is_absolute(), "development link receipt path must be absolute")
    require(
        receipt_path == runtime_path.parent / "DEVELOPMENT-NONPROMOTABLE.json",
        "development runtime and link receipt are not a single published bundle",
    )
    receipt_data = read_regular(receipt_path, "development link receipt")
    receipt = decode_object(receipt_data, "development link receipt")
    require(
        receipt.get("schema") == 1
        and receipt.get("kind") == "nonpromotable-candle-development-link",
        "development link receipt identity mismatch",
    )
    require(
        receipt.get("promotion_allowed") is False
        and receipt.get("s1_evidence") is False
        and receipt.get("s2_evidence") is False
        and receipt.get("s3_evidence") is False
        and receipt.get("ordinary_linked_provenance_produced") is False,
        "development link receipt does not preserve the non-promotable boundary",
    )
    products = receipt.get("products")
    require(isinstance(products, dict), "development link receipt products missing")
    require(
        products.get("cake") == bytes_record(runtime_data, "cake"),
        "development runtime identity differs from link receipt",
    )
    repositories = receipt.get("repositories")
    require(isinstance(repositories, dict), "development link repositories missing")
    commits: dict[str, str] = {}
    for key, label in (("cakeml", "CakeML"), ("candle", "Candle"), ("hol4", "HOL4")):
        identity = repositories.get(key)
        require(isinstance(identity, dict), f"development link {label} identity missing")
        commit = identity.get("commit")
        root = identity.get("root")
        require(
            isinstance(commit, str)
            and HEX40_RE.fullmatch(commit) is not None
            and identity.get("tracked_worktree_clean") is True
            and isinstance(root, str)
            and Path(root).is_absolute(),
            f"development link {label} identity malformed",
        )
        commits[key] = commit
    return receipt_data, commits


def process_limits(cpu_seconds: int, address_space_bytes: int, output_bytes: int):
    def apply() -> None:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(
            resource.RLIMIT_AS, (address_space_bytes, address_space_bytes),
        )
        resource.setrlimit(resource.RLIMIT_FSIZE, (output_bytes, output_bytes))
    return apply


def invoke(
    runtime: Path,
    arguments: list[str],
    stdin: bytes,
    timeout_seconds: int,
    cpu_seconds: int,
    address_space_bytes: int,
    output_bytes: int,
    cml_heap_size_mib: int,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [str(runtime), *arguments],
            input=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            close_fds=True,
            cwd="/",
            env={
                "PATH": "/usr/bin:/bin",
                "LC_ALL": "C",
                "CML_HEAP_SIZE": str(cml_heap_size_mib),
            },
            timeout=timeout_seconds,
            start_new_session=True,
            preexec_fn=process_limits(cpu_seconds, address_space_bytes, output_bytes),
        )
        stdout = completed.stdout
        stderr = completed.stderr
        require(
            len(stdout) <= output_bytes and len(stderr) <= output_bytes,
            "runtime output exceeded the development cap",
        )
        return {
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "exit_code": completed.returncode,
            "timed_out": False,
            "stdout": stdout,
            "stderr": stderr,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "exit_code": None,
            "timed_out": True,
            "stdout": error.stdout or b"",
            "stderr": error.stderr or b"",
        }


def classify(result: dict[str, Any], nonce: str) -> str:
    require(re.fullmatch(r"[0-9a-f]{64}", nonce) is not None, "invalid request nonce")
    ok = (
        b"CANDLE_CAMLPARSER_DIAGNOSTIC_V1\t"
        + nonce.encode() + b"\tOK\n"
    )
    parse_error = (
        b"CANDLE_CAMLPARSER_DIAGNOSTIC_V1\t"
        + nonce.encode() + b"\tPARSE_ERROR\n"
    )
    if (
        not result["timed_out"]
        and result["exit_code"] == 0
        and result["stderr"] == b""
        and result["stdout"] == ok
    ):
        return "parse-ok"
    if (
        not result["timed_out"]
        and result["exit_code"] == 65
        and result["stdout"] == parse_error
    ):
        return "parse-error"
    if result["timed_out"]:
        return "timeout"
    return "runtime-failure"


def write_readonly(path: Path, data: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o444)


def run(arguments: argparse.Namespace) -> dict[str, Any]:
    require(arguments.timeout_seconds > 0, "timeout must be positive")
    require(arguments.max_cpu_seconds > 0, "CPU limit must be positive")
    require(arguments.max_address_space_gib > 0, "address-space limit must be positive")
    require(arguments.max_output_mib > 0, "output limit must be positive")
    require(arguments.cml_heap_size_mib > 0, "CakeML heap size must be positive")
    require(
        arguments.max_address_space_gib * 1024
        >= arguments.cml_heap_size_mib + 4096,
        "address-space limit must leave at least 4 GiB beyond the CakeML heap",
    )
    require(arguments.plan_root.is_absolute(), "plan root must be absolute")
    require(arguments.runtime.is_absolute(), "runtime path must be absolute")
    require(
        arguments.runtime_link_receipt.is_absolute(),
        "development link receipt path must be absolute",
    )
    require(arguments.output_root.is_absolute(), "output root must be absolute")
    require(arguments.output_root.parent.is_dir(), "output parent does not exist")
    require(not arguments.output_root.exists(), "output root already exists")

    plan, plan_data, prepared_inputs = validate_plan(
        arguments.plan_root, arguments.profile,
    )
    runtime_data = read_regular(arguments.runtime, "development runtime")
    runtime_mode = arguments.runtime.lstat().st_mode
    require(runtime_mode & 0o111, "development runtime is not executable")
    link_receipt_data, runtime_commits = validate_development_link_receipt(
        arguments.runtime_link_receipt, arguments.runtime, runtime_data,
    )
    runtime_record = bytes_record(runtime_data)
    runtime_record.update({
        "path": str(arguments.runtime),
        "cakeml_commit": runtime_commits["cakeml"],
        "candle_patch_commit": runtime_commits["candle"],
        "hol4_commit": runtime_commits["hol4"],
        "development_link_receipt": bytes_record(
            link_receipt_data, str(arguments.runtime_link_receipt),
        ),
        "ordinary_linked_provenance_consumed": False,
        "execution": "private-copy-of-captured-runtime-bytes",
    })
    address_space_bytes = arguments.max_address_space_gib * 1024**3
    output_bytes = arguments.max_output_mib * 1024**2
    with tempfile.TemporaryDirectory(
        prefix=f".{arguments.output_root.name}.runtime-",
        dir=arguments.output_root.parent,
    ) as execution_directory:
        execution_runtime = Path(execution_directory) / "runtime"
        with execution_runtime.open("xb") as stream:
            stream.write(runtime_data)
            stream.flush()
            os.fsync(stream.fileno())
        execution_runtime.chmod(0o555)
        require(
            bytes_record(read_regular(execution_runtime, "private runtime image"))
            == bytes_record(runtime_data),
            "private runtime image differs from captured bytes",
        )
        capability = invoke(
            execution_runtime, [CAPABILITY_ARGUMENT], b"",
            arguments.timeout_seconds, arguments.max_cpu_seconds,
            address_space_bytes, output_bytes, arguments.cml_heap_size_mib,
        )
        require(
            not capability["timed_out"]
            and capability["exit_code"] == 0
            and capability["stdout"] == CAPABILITY_LINE
            and capability["stderr"] == b"",
            "development runtime failed the exact parser-only capability handshake",
        )

        staging = Path(tempfile.mkdtemp(
            prefix=f".{arguments.output_root.name}.pending-",
            dir=arguments.output_root.parent,
        ))
        attempts = []
        counts: Counter[str] = Counter()
        started = time.monotonic()
        for index, (entry, prepared) in enumerate(zip(plan["inputs"], prepared_inputs)):
            nonce = f"{index:064x}"
            result = invoke(
                execution_runtime, [RUN_ARGUMENT, nonce], prepared,
                arguments.timeout_seconds, arguments.max_cpu_seconds,
                address_space_bytes, output_bytes, arguments.cml_heap_size_mib,
            )
            outcome = classify(result, nonce)
            counts[outcome] += 1
            stdout_relative = f"attempts/{index:03d}.stdout"
            stderr_relative = f"attempts/{index:03d}.stderr"
            write_readonly(staging / stdout_relative, result["stdout"])
            write_readonly(staging / stderr_relative, result["stderr"])
            attempts.append({
                "index": index,
                "source_key": entry["source_key"],
                "nonce": nonce,
                "prepared_bytes": len(prepared),
                "prepared_sha256": hashlib.sha256(prepared).hexdigest(),
                "elapsed_seconds": result["elapsed_seconds"],
                "exit_code": result["exit_code"],
                "timed_out": result["timed_out"],
                "outcome": outcome,
                "stdout": bytes_record(result["stdout"], stdout_relative),
                "stderr": bytes_record(result["stderr"], stderr_relative),
            })

    pass_count = counts["parse-ok"]
    expected_count = PROFILE_CONTRACTS[arguments.profile]["count"]
    receipt = {
        "schema": 2,
        "kind": PROFILE_CONTRACTS[arguments.profile]["result_kind"],
        "claim": (
            "development-only parser observation; not inference, evaluation, "
            "a theorem, S1, S2, S3, or release evidence"
        ),
        "promotion_allowed": False,
        "s1_evidence": False,
        "s2_evidence": False,
        "s3_evidence": False,
        "ordinary_linked_provenance_consumed": False,
        "controller": bytes_record(SOURCE_BYTES, str(SOURCE_PATH)),
        "profile": arguments.profile,
        "outcome": (
            "development-parse-pass"
            if pass_count == expected_count else "development-parse-fail"
        ),
        "plan": {
            **bytes_record(plan_data, "plan.json"),
            "source_path": str(arguments.plan_root / "plan.json"),
            "repositories": plan["repositories"],
        },
        "runtime": runtime_record,
        "capability": {
            "argument": CAPABILITY_ARGUMENT,
            "stdin_sha256": EMPTY_SHA256,
            "exit_code": capability["exit_code"],
            "stdout": bytes_record(capability["stdout"], "capability.stdout"),
            "stderr": bytes_record(capability["stderr"], "capability.stderr"),
        },
        "limits": {
            "timeout_seconds_per_process": arguments.timeout_seconds,
            "cpu_seconds_per_process": arguments.max_cpu_seconds,
            "address_space_gib_per_process": arguments.max_address_space_gib,
            "cml_heap_size_mib_per_process": arguments.cml_heap_size_mib,
            "output_mib_per_stream": arguments.max_output_mib,
        },
        "child_environment": {
            "CML_HEAP_SIZE": str(arguments.cml_heap_size_mib),
            "LC_ALL": "C",
            "PATH": "/usr/bin:/bin",
        },
        "attempt_count": len(attempts),
        "outcome_counts": dict(sorted(counts.items())),
        "parse_ok_count": pass_count,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "attempts": attempts,
    }
    write_readonly(staging / "plan.json", plan_data)
    write_readonly(staging / "capability.stdout", capability["stdout"])
    write_readonly(staging / "capability.stderr", capability["stderr"])
    write_readonly(staging / "DEVELOPMENT-NONPROMOTABLE.json", json_bytes(receipt))
    for directory, directories, _files in os.walk(staging, topdown=False):
        for name in directories:
            (Path(directory) / name).chmod(0o555)
    staging.chmod(0o555)
    staging.rename(arguments.output_root)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=tuple(PROFILE_CONTRACTS), required=True)
    parser.add_argument("--plan-root", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--runtime-link-receipt", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--max-cpu-seconds", type=int, default=600)
    parser.add_argument("--max-address-space-gib", type=int, default=16)
    parser.add_argument("--max-output-mib", type=int, default=1)
    parser.add_argument("--cml-heap-size-mib", type=int, default=4096)
    arguments = parser.parse_args()
    receipt = run(arguments)
    print(
        f"{receipt['kind']}: {receipt['outcome']} "
        f"({receipt['parse_ok_count']}/{receipt['attempt_count']} parse-ok)"
    )
    return 0 if receipt["outcome"] == "development-parse-pass" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ContractError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f"development parser run rejected: {error}") from error
