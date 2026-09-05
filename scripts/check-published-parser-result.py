#!/usr/bin/python3
"""Consumer-side revalidation for a retained Candle parser result tree."""

from __future__ import annotations

import sys

_EARLY_REQUIRED_FLAGS = {
    "debug": 0, "inspect": 0, "interactive": 0, "optimize": 0,
    "dont_write_bytecode": 0, "no_user_site": 1, "no_site": 1,
    "ignore_environment": 1, "verbose": 0, "bytes_warning": 0,
    "quiet": 0, "hash_randomization": 1, "isolated": 1,
    "dev_mode": False, "utf8_mode": 1, "warn_default_encoding": 0,
    "safe_path": True, "int_max_str_digits": 4300,
}
if __name__ == "__main__":
    _early_observed = {
        name: getattr(sys.flags, name) for name in _EARLY_REQUIRED_FLAGS
    }
    if (_early_observed != _EARLY_REQUIRED_FLAGS or
            dict(sys._xoptions) != {} or list(sys.warnoptions) != []):
        raise SystemExit(
            "published parser result rejected: direct execution requires "
            "/usr/bin/python3 -I -S under the exact environment"
        )

import argparse
import json
import os
from pathlib import Path
import stat
import subprocess
import types
from typing import Any


EXACT_ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
GIB = 1024 * 1024 * 1024
MIB = 1024 * 1024
PARSER_TIMEOUT_SECONDS = 7200
PARSER_CPU_SECONDS = 7200
PARSER_PROFILE_RESOURCES = {
    "pilot": {
        "address_space_gib": 16,
        "cml_heap_size_mib": 4096,
    },
    "all-inventory": {
        "address_space_gib": 24,
        "cml_heap_size_mib": 16384,
    },
}
GIT_OPTIONS = (
    "-c", "core.fsmonitor=false",
    "-c", "core.untrackedCache=false",
    "-c", "core.preloadIndex=false",
)


class ResultError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ResultError(message)


def stable_file_bytes(path: Path, label: str) -> bytes:
    try:
        descriptor = os.open(
            path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as error:
        raise ResultError(f"could not open ordinary {label}: {path}") from error
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
    require(stat.S_ISREG(before.st_mode) and before.st_mode == named.st_mode and
            (before.st_dev, before.st_ino, before.st_size,
             before.st_mtime_ns, before.st_ctime_ns) ==
            (after.st_dev, after.st_ino, after.st_size,
             after.st_mtime_ns, after.st_ctime_ns) and
            (named.st_dev, named.st_ino) == (after.st_dev, after.st_ino) and
            len(value) == before.st_size,
            f"{label} changed while reading: {path}")
    require(value, f"empty {label}: {path}")
    return value


def git_run(root: Path, *arguments: str) -> bytes:
    process = subprocess.run(
        ["/usr/bin/git", *GIT_OPTIONS, "-C", str(root), *arguments],
        check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={
            **EXACT_ENVIRONMENT,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_NO_REPLACE_OBJECTS": "1",
        },
    )
    require(process.returncode == 0,
            f"Git authentication failed: {process.stderr.decode(errors='replace').strip()}")
    return process.stdout


def authenticate_source(
    root: Path, expected_head: str, source: Path, label: str,
) -> tuple[bytes, str]:
    require(root.is_absolute() and root.resolve(strict=True) == root,
            f"{label} Git root contains a symlink or alias")
    require(source.is_relative_to(root) and source.resolve(strict=True) == source,
            f"{label} source is outside Git root or contains a symlink")
    top = git_run(root, "rev-parse", "--show-toplevel").decode().strip()
    head = git_run(root, "rev-parse", "HEAD").decode().strip()
    require(top == str(root) and head == expected_head,
            f"{label} Git authority mismatch")
    require(git_run(root, "for-each-ref", "--format=%(refname)", "refs/replace") == b"",
            f"{label} Git replacement refs are present")
    common_value = git_run(root, "rev-parse", "--git-common-dir").decode().strip()
    common = Path(common_value)
    if not common.is_absolute():
        common = (root / common).resolve(strict=True)
    require(not (common / "info/grafts").exists(),
            f"{label} Git grafts are present")
    require(git_run(root, "status", "--porcelain=v1", "--untracked-files=all") == b"",
            f"{label} Git worktree is not clean")
    relative = source.relative_to(root).as_posix()
    source_bytes = stable_file_bytes(source, label)
    blob = git_run(root, "show", f"{expected_head}:{relative}")
    require(blob == source_bytes, f"{label} differs from exact committed blob")
    return source_bytes, head


def load_controller(candle_root: Path, candle_head: str):
    source = candle_root / "candle/flyspeck_parser_diagnostic.py"
    source_bytes, _ = authenticate_source(
        candle_root, candle_head, source, "Candle parser controller",
    )
    module_name = "candle_published_parser_result_controller"
    module = types.ModuleType(module_name)
    module.__file__ = str(source)
    module.__package__ = ""
    sys.modules[module_name] = module
    exec(compile(source_bytes, str(source), "exec", dont_inherit=True), module.__dict__)
    require(module.SOURCE_BYTES == source_bytes and
            stable_file_bytes(source, "Candle parser controller") == source_bytes,
            "Candle parser controller changed during exact source execution")
    # The committed controller deliberately exposes reconstruction only to its
    # direct-script identity.  It was exact-loaded above without running its
    # CLI; present that identity while invoking its read-only validation
    # functions, and retain the consumer itself as the external authority.
    module.__name__ = "__main__"
    module.__spec__ = None
    module.__cached__ = None
    module.sys.argv[0] = str(source)
    return module


def exact_positive_integer(value: Any, label: str) -> int:
    require(type(value) is int and value > 0, f"malformed {label}")
    return value


def expected_resource_limits(profile: str) -> dict[str, Any]:
    require(profile in PARSER_PROFILE_RESOURCES,
            "unknown parser resource-limit profile")
    profile_resources = PARSER_PROFILE_RESOURCES[profile]
    runtime_environment = {
        **EXACT_ENVIRONMENT,
        "CML_HEAP_SIZE": str(profile_resources["cml_heap_size_mib"]),
    }
    return {
        "timeout_seconds": PARSER_TIMEOUT_SECONDS,
        "cpu_seconds": PARSER_CPU_SECONDS,
        "address_space_bytes": profile_resources["address_space_gib"] * GIB,
        "effective_stdout_file_bytes": MIB,
        "effective_stderr_file_bytes": MIB,
        "capture": "fresh-private-ordinary-files-rlimit-fsize",
        "child_process_creation_rlimit_nproc": 0,
        "core_file_bytes": 0,
        "runtime_environment": runtime_environment,
    }


def validate_resource_limits(value: Any, profile: str) -> dict[str, Any]:
    expected = expected_resource_limits(profile)
    require(value == expected, "parser resource limits differ from exact contract")
    return expected


def open_pinned_directory(path: Path, label: str) -> tuple[int, tuple[int, int]]:
    try:
        descriptor = os.open(
            path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
            getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as error:
        raise ResultError(f"could not pin {label}: {path}") from error
    opened = os.fstat(descriptor)
    named = path.stat(follow_symlinks=False)
    require(stat.S_ISDIR(opened.st_mode) and
            (opened.st_dev, opened.st_ino) == (named.st_dev, named.st_ino),
            f"{label} identity changed while opening")
    return descriptor, (opened.st_dev, opened.st_ino)


def require_named_directory_identity(
    descriptor: int, path: Path, identity: tuple[int, int], label: str,
) -> None:
    opened = os.fstat(descriptor)
    named = path.stat(follow_symlinks=False)
    require(stat.S_ISDIR(named.st_mode) and
            (opened.st_dev, opened.st_ino) == identity ==
            (named.st_dev, named.st_ino),
            f"{label} named identity changed during validation")


def transcript_paths(receipt: dict[str, Any], count: int) -> list[str]:
    paths = []
    capability = receipt.get("capability")
    require(isinstance(capability, dict), "missing capability receipt")
    for stream in ("stdout", "stderr"):
        record = capability.get(stream)
        require(isinstance(record, dict) and
                record.get("path") == f"capability.{stream}",
                f"malformed capability {stream} path")
        paths.append(record["path"])
    attempts = receipt.get("attempts")
    require(isinstance(attempts, list) and len(attempts) == count,
            "parser attempt count mismatch")
    for index, attempt in enumerate(attempts):
        require(isinstance(attempt, dict) and attempt.get("index") == index,
                f"malformed parser attempt {index}")
        require(attempt.get("outcome") == "parse-ok",
                f"parser attempt {index} did not parse successfully")
        for stream in ("stdout", "stderr"):
            record = attempt.get(stream)
            expected = f"attempts/{index:03d}.{stream}"
            require(isinstance(record, dict) and record.get("path") == expected,
                    f"malformed parser attempt {index} {stream} path")
            paths.append(expected)
    require(len(paths) == 2 + 2 * count and len(set(paths)) == len(paths),
            "parser transcript path closure mismatch")
    return paths


def _validate_with_pins(arguments: argparse.Namespace) -> dict[str, Any]:
    require(dict(os.environ) == EXACT_ENVIRONMENT,
            "consumer requires exact PATH=/usr/bin:/bin and LC_ALL=C environment")
    project_root = arguments.project_root.resolve(strict=True)
    checker_source = Path(__file__).resolve(strict=True)
    checker_bytes, project_head = authenticate_source(
        project_root, arguments.project_head, checker_source,
        "parser result consumer",
    )
    require(checker_bytes == stable_file_bytes(
                checker_source, "parser result consumer",
            ),
            "parser result consumer changed after authentication")
    candle_root = arguments.candle_root.resolve(strict=True)
    flyspeck_root = arguments.flyspeck_root.resolve(strict=True)
    plan_root = arguments.plan_root.resolve(strict=True)
    result_root = arguments.result_root.resolve(strict=True)
    plan_fd_root = Path(f"/proc/self/fd/{arguments._plan_fd}")
    result_fd_root = Path(f"/proc/self/fd/{arguments._result_fd}")
    for supplied, resolved, label in (
        (arguments.candle_root, candle_root, "Candle"),
        (arguments.flyspeck_root, flyspeck_root, "Flyspeck"),
        (arguments.plan_root, plan_root, "plan"),
        (arguments.result_root, result_root, "result"),
    ):
        require(supplied.is_absolute() and supplied == resolved,
                f"{label} root contains a symlink or alias")

    controller = load_controller(candle_root, arguments.candle_head)
    expected_plan, expected_inputs, expected_host, expected_plan_data = (
        controller.reconstruct_plan_authority(
            candle_root, arguments.candle_head,
            flyspeck_root, arguments.flyspeck_head, arguments.profile,
        )
    )
    plan, plan_data = controller.validate_plan_root(
        plan_root, expected_plan, expected_inputs, expected_host,
    )
    require(plan_data == expected_plan_data,
            "retained plan bytes differ from reconstructed authority")
    count = controller.profile_input_count(plan)
    expected_plan_files = {
        controller.PLAN_NAME: expected_plan_data,
        controller.HOST_RECEIPT_NAME: controller.json_bytes(expected_host),
        **expected_inputs,
    }
    controller.validate_exact_byte_tree(
        plan_fd_root, expected_plan_files,
        controller.PLAN_ROOT_MODE, controller.PLAN_FILE_MODE,
        "consumer-pinned parser plan",
    )
    require_named_directory_identity(
        arguments._plan_fd, plan_root, arguments._plan_identity, "plan root",
    )

    policy = controller._load_direct_runtime_policy(
        candle_root, arguments.candle_head, plan,
    )
    lock = policy.runtime_lock.acquire_build_lock(candle_root)
    try:
        linked, runtime = controller.validate_linked_runtime(
            candle_root, plan, policy,
        )
        require(linked.get("schema") == 6 and
                linked.get("kind") == "candle-linked-pinned-cakeml",
                "parser result consumer requires ordinary schema-6 linked authority")
        linked_path = candle_root / controller.LINKED_RECORD_RELATIVE
        linked_bytes = controller._read_stable_source(linked_path)

        receipt_path = result_fd_root / controller.RESULT_NAME
        receipt_data = controller._read_stable_source(receipt_path)
        receipt = controller.decode_object(receipt_data, "published parser receipt")
        require(receipt.get("outcome") == "parse-pass",
                "published parser result is not parse-pass")
        require(receipt.get("attempt_count") == count,
                "published parser result has the wrong attempt count")
        expected_schema = (
            controller.DIAGNOSTIC_RECEIPT_SCHEMA
            if arguments.profile == controller.PILOT_PROFILE
            else controller.ALL_INVENTORY_RECEIPT_SCHEMA
        )
        require(receipt.get("schema") == expected_schema,
                "published parser receipt schema mismatch")
        require(receipt.get("linked_provenance_schema") == 6 and
                receipt.get("bootstrap_transition") is None,
                "published parser receipt is not bound to ordinary schema 6")

        paths = transcript_paths(receipt, count)
        transcript_files = {
            relative: controller._read_stable_source(result_fd_root / relative)
            for relative in paths
        }
        require(controller.RUNTIME_RESULT_FIELDS.issubset(receipt),
                "published parser runtime result fields are incomplete")
        runtime_result = {
            field: receipt[field] for field in controller.RUNTIME_RESULT_FIELDS
        }
        limits = validate_resource_limits(
            receipt.get("resource_limits"), arguments.profile,
        )
        timeout = limits["timeout_seconds"]
        cpu = limits["cpu_seconds"]
        address_bytes = limits["address_space_bytes"]
        stdout_bytes = limits["effective_stdout_file_bytes"]

        linked_record = receipt.get("linked_provenance")
        require(isinstance(linked_record, dict),
                "missing parser linked-provenance snapshot")
        controller.validate_file_record(
            result_fd_root / "snapshot/linked/cakeml-build-provenance.json",
            linked_record, "published linked provenance snapshot",
            "snapshot/linked/cakeml-build-provenance.json",
        )
        require(linked_record == controller.bytes_record(
                    linked_bytes,
                    "snapshot/linked/cakeml-build-provenance.json",
                ),
                "published result differs from current linked provenance")
        current_runtime = controller.file_record(
            runtime, controller.RUNTIME_RELATIVE.as_posix(),
        )
        retained_runtime = receipt.get("runtime")
        require(isinstance(retained_runtime, dict) and
                retained_runtime.get("bytes") == current_runtime["bytes"] and
                retained_runtime.get("sha256") == current_runtime["sha256"],
                "published result differs from current linked runtime")

        current_controller_execution = controller.collect_controller_execution(
            candle_root, policy,
        )
        expected_receipt = controller.build_diagnostic_receipt(
            plan=plan,
            expected_plan_data=expected_plan_data,
            expected_host=expected_host,
            controller_execution=current_controller_execution,
            runtime_lock_record=lock.record,
            timeout_seconds=timeout,
            max_cpu_seconds=cpu,
            max_address_space_gib=address_bytes // GIB,
            max_output_bytes=stdout_bytes,
            runtime_environment=limits["runtime_environment"],
            linked_bytes=linked_bytes,
            linked=linked,
            transition_snapshot=None,
            runtime_snapshot=retained_runtime,
            runtime_execution=receipt.get("runtime_execution"),
            inventory=receipt.get("snapshot"),
            runtime_result=runtime_result,
            transcript_files=transcript_files,
        )
        require(controller.json_bytes(expected_receipt) == receipt_data,
                "published parser receipt differs from independent reconstruction")
        controller.validate_result_tree(
            result_fd_root, receipt["snapshot"], receipt_data, transcript_files,
        )

        linked_post, runtime_post = controller.validate_linked_runtime(
            candle_root, plan, policy,
        )
        require(linked_post == linked and runtime_post == runtime and
                controller._read_stable_source(linked_path) == linked_bytes and
                controller._read_stable_source(receipt_path) == receipt_data,
                "authority changed during parser result revalidation")

        final_plan, final_inputs, final_host, final_plan_data = (
            controller.reconstruct_plan_authority(
                candle_root, arguments.candle_head,
                flyspeck_root, arguments.flyspeck_head, arguments.profile,
            )
        )
        require(final_plan == expected_plan and final_inputs == expected_inputs and
                final_host == expected_host and final_plan_data == expected_plan_data,
                "plan or Flyspeck authority changed during result revalidation")
        controller.validate_exact_byte_tree(
            plan_fd_root, expected_plan_files,
            controller.PLAN_ROOT_MODE, controller.PLAN_FILE_MODE,
            "final consumer-pinned parser plan",
        )
        controller.validate_result_tree(
            result_fd_root, receipt["snapshot"], receipt_data, transcript_files,
        )
        require_named_directory_identity(
            arguments._plan_fd, plan_root, arguments._plan_identity, "plan root",
        )
        require_named_directory_identity(
            arguments._result_fd, result_root, arguments._result_identity,
            "result root",
        )
    finally:
        lock.close()

    return {
        "gate": "published-parser-result-pass",
        "profile": arguments.profile,
        "schema": expected_schema,
        "linked_provenance_schema": 6,
        "attempt_count": count,
        "outcome": "parse-pass",
        "result_root": str(result_root),
        "consumer_project_head": project_head,
    }


def validate(arguments: argparse.Namespace) -> dict[str, Any]:
    plan_root = arguments.plan_root.resolve(strict=True)
    result_root = arguments.result_root.resolve(strict=True)
    plan_fd, plan_identity = open_pinned_directory(plan_root, "plan root")
    result_fd = -1
    try:
        result_fd, result_identity = open_pinned_directory(
            result_root, "result root",
        )
        arguments._plan_fd = plan_fd
        arguments._plan_identity = plan_identity
        arguments._result_fd = result_fd
        arguments._result_identity = result_identity
        return _validate_with_pins(arguments)
    finally:
        if result_fd >= 0:
            os.close(result_fd)
        os.close(plan_fd)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--project-head", required=True)
    parser.add_argument("--profile", choices=("pilot", "all-inventory"), required=True)
    parser.add_argument("--plan-root", type=Path, required=True)
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--candle-root", type=Path, required=True)
    parser.add_argument("--candle-head", required=True)
    parser.add_argument("--flyspeck-root", type=Path, required=True)
    parser.add_argument("--flyspeck-head", required=True)
    arguments = parser.parse_args()
    print(json.dumps(validate(arguments), sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ResultError, OSError, UnicodeError, ValueError,
            subprocess.SubprocessError) as error:
        raise SystemExit(f"published parser result rejected: {error}") from error
