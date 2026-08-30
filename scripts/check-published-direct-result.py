#!/usr/bin/python3
"""Independently revalidate one retained direct Flyspeck stratum result.

This consumer never promotes a result to S1, S2, or S3.  It establishes only
that a completed schema-5 receipt, or an explicitly requested schema-6
receipt, still matches its exact current Candle/Flyspeck/plan/link authority
and retained snapshot/transcript bytes.  For schema 6, an explicit comparison
mode emits the compiled candidate descriptor only after that full validation.
"""

from __future__ import annotations

import sys


_EARLY_REQUIRED_FLAGS = {
    "debug": 0, "inspect": 0, "interactive": 0, "optimize": 0,
    "dont_write_bytecode": 0, "no_user_site": 1, "no_site": 1,
    "ignore_environment": 1, "verbose": 0, "bytes_warning": 0,
    "quiet": 0, "hash_randomization": 1, "isolated": 1,
    "dev_mode": False, "utf8_mode": 0, "warn_default_encoding": 0,
    "safe_path": True, "int_max_str_digits": 4300,
}
if __name__ == "__main__":
    _early_observed = {
        name: getattr(sys.flags, name) for name in _EARLY_REQUIRED_FLAGS
    }
    if (_early_observed != _EARLY_REQUIRED_FLAGS or
            dict(sys._xoptions) != {} or list(sys.warnoptions) != []):
        raise SystemExit(
            "published direct result rejected: direct execution requires "
            "/usr/bin/python3 -I -S under LC_ALL=C.UTF-8"
        )

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import types
from typing import Any


CONSUMER_ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LC_ALL": "C.UTF-8"}
RUNTIME_BASE_ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
GIB = 1024 * 1024 * 1024
MIB = 1024 * 1024
MAX_DIRECT_LOG_BYTES = 512 * MIB
GIT_OPTIONS = (
    "-c", "core.fsmonitor=false",
    "-c", "core.untrackedCache=false",
    "-c", "core.preloadIndex=false",
)
CONTROLLER_RELATIVES = (
    "candle/cakeml_artifact_provenance.py",
    "candle/cakeml_bootstrap_transition.py",
    "candle/flyspeck_stratum_plan.py",
    "candle/flyspeck_stratum_runtime.py",
    "candle/reference_protocol.py",
    "candle/runtime_lock.py",
)
CONTROL_INPUT_PATHS = {
    "instrumented_prefix": "control/instrumented-prefix.ml",
    "runtime_config": "control/runtime-config.ml",
    "stdin": "control/stdin.ml",
    "postlude": "control/postlude.ml",
}


class ResultError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ResultError(message)


def _pairs_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        require(key not in value, f"duplicate JSON key: {key}")
        value[key] = item
    return value


def decode_object(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=_pairs_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ResultError(f"cannot decode {label}: {error}") from error
    require(isinstance(value, dict), f"{label} is not an object")
    return value


def stable_file_bytes(
    path: Path, label: str, *, allow_empty: bool = False,
    max_bytes: int | None = None,
) -> bytes:
    try:
        descriptor = os.open(
            path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as error:
        raise ResultError(f"could not open ordinary {label}: {path}") from error
    try:
        before = os.fstat(descriptor)
        require(max_bytes is None or before.st_size <= max_bytes,
                f"{label} exceeds the consumer size cap")
        chunks = []
        while block := os.read(descriptor, 1024 * 1024):
            chunks.append(block)
        after = os.fstat(descriptor)
        named = path.stat(follow_symlinks=False)
    finally:
        os.close(descriptor)
    value = b"".join(chunks)
    require(
        stat.S_ISREG(before.st_mode) and before.st_mode == named.st_mode and
        (before.st_dev, before.st_ino, before.st_size,
         before.st_mtime_ns, before.st_ctime_ns) ==
        (after.st_dev, after.st_ino, after.st_size,
         after.st_mtime_ns, after.st_ctime_ns) and
        (named.st_dev, named.st_ino) == (after.st_dev, after.st_ino) and
        len(value) == before.st_size,
        f"{label} changed while reading: {path}",
    )
    require(allow_empty or bool(value), f"empty {label}: {path}")
    return value


def data_record(data: bytes) -> dict[str, Any]:
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "md5": hashlib.md5(data, usedforsecurity=False).hexdigest(),
    }


def require_record(data: bytes, record: Any, label: str) -> None:
    require(isinstance(record, dict), f"malformed {label} record")
    observed = data_record(data)
    require(all(record.get(field) == observed[field]
                for field in ("bytes", "sha256", "md5")),
            f"{label} bytes differ from retained record")


def git_run(root: Path, *arguments: str) -> bytes:
    process = subprocess.run(
        ["/usr/bin/git", *GIT_OPTIONS, "-C", str(root), *arguments],
        check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={
            **RUNTIME_BASE_ENVIRONMENT,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
        },
    )
    require(process.returncode == 0,
            "Git authentication failed: " +
            process.stderr.decode(errors="replace").strip())
    return process.stdout


def authenticate_git_root(root: Path, expected_head: str, label: str) -> str:
    require(root.is_absolute() and root.resolve(strict=True) == root,
            f"{label} Git root contains a symlink or alias")
    top = git_run(root, "rev-parse", "--show-toplevel").decode().strip()
    head = git_run(root, "rev-parse", "HEAD").decode().strip()
    require(top == str(root) and head == expected_head,
            f"{label} Git authority mismatch")
    require(git_run(
                root, "for-each-ref", "--format=%(refname)", "refs/replace",
            ) == b"", f"{label} Git replacement refs are present")
    common_value = git_run(root, "rev-parse", "--git-common-dir").decode().strip()
    common = Path(common_value)
    if not common.is_absolute():
        common = (root / common).resolve(strict=True)
    require(not (common / "info/grafts").exists(),
            f"{label} Git grafts are present")
    require(git_run(
                root, "status", "--porcelain=v1", "--untracked-files=all",
            ) == b"", f"{label} Git worktree is not clean")
    return head


def authenticate_sources(
    root: Path, expected_head: str, relatives: tuple[str, ...], label: str,
) -> dict[str, bytes]:
    authenticate_git_root(root, expected_head, label)
    result = {}
    for relative in relatives:
        source = root / relative
        require(source.resolve(strict=True) == source,
                f"{label} source contains a symlink: {relative}")
        data = stable_file_bytes(source, f"{label} source {relative}")
        require(git_run(root, "show", f"{expected_head}:{relative}") == data,
                f"{label} source differs from exact committed blob: {relative}")
        result[relative] = data
    return result


def exact_source_module(name: str, path: Path, data: bytes) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = ""
    module.__candle_source_bytes__ = data
    module.__candle_source_sha256__ = hashlib.sha256(data).hexdigest()
    sys.modules[name] = module
    try:
        exec(compile(data, str(path), "exec", dont_inherit=True), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def load_controller(candle_root: Path, candle_head: str):
    sources = authenticate_sources(
        candle_root, candle_head, CONTROLLER_RELATIVES,
        "Candle direct controller",
    )
    paths = {relative: candle_root / relative for relative in CONTROLLER_RELATIVES}
    provenance_relative = "candle/cakeml_artifact_provenance.py"
    provenance = sources[provenance_relative]
    # The transition helper and the direct runner use distinct private names
    # for the same authenticated provenance source.
    exact_source_module(
        "_candle_bootstrap_transition_provenance",
        paths[provenance_relative], provenance,
    )
    bindings = (
        ("_candle_stratum_cakeml_artifact_provenance", provenance_relative),
        ("_candle_stratum_cakeml_bootstrap_transition",
         "candle/cakeml_bootstrap_transition.py"),
        ("_candle_stratum_flyspeck_stratum_plan",
         "candle/flyspeck_stratum_plan.py"),
        ("_candle_stratum_runtime_lock", "candle/runtime_lock.py"),
        ("_candle_stratum_reference_protocol", "candle/reference_protocol.py"),
    )
    for name, relative in bindings:
        exact_source_module(name, paths[relative], sources[relative])
    runtime_relative = "candle/flyspeck_stratum_runtime.py"
    module = exact_source_module(
        "candle_published_direct_result_controller",
        paths[runtime_relative], sources[runtime_relative],
    )
    require(module.RUNNER_SOURCE_BYTES == sources[runtime_relative] and
            stable_file_bytes(
                paths[runtime_relative], "Candle direct controller",
            ) == sources[runtime_relative],
            "Candle direct controller changed during exact source execution")
    module.__name__ = "__main__"
    module.__spec__ = None
    module.__cached__ = None
    module.sys.argv[0] = str(paths[runtime_relative])
    return module


def open_pinned_directory(path: Path, label: str) -> tuple[int, tuple[int, int]]:
    try:
        descriptor = os.open(
            path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW |
            getattr(os, "O_CLOEXEC", 0),
        )
    except OSError as error:
        raise ResultError(f"could not pin {label}: {path}") from error
    try:
        opened = os.fstat(descriptor)
        named = path.stat(follow_symlinks=False)
        require(stat.S_ISDIR(opened.st_mode) and
                (opened.st_dev, opened.st_ino) == (named.st_dev, named.st_ino),
                f"{label} identity changed while opening")
    except Exception:
        os.close(descriptor)
        raise
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


def validate_held_runtime_lock(lock: Any, candle_root: Path) -> None:
    """Require the held descriptor still names the current build directory."""
    require(type(getattr(lock, "fd", None)) is int and lock.fd >= 0 and
            isinstance(getattr(lock, "record", None), dict),
            "malformed held runtime lock")
    opened = os.fstat(lock.fd)
    build_path = candle_root / "candle/build"
    named = os.stat(build_path, follow_symlinks=False)
    expected = {
        "path": str(build_path),
        "object": "directory_inode",
        "mode": "shared",
        "device": opened.st_dev,
        "inode": opened.st_ino,
    }
    require(stat.S_ISDIR(opened.st_mode) and stat.S_ISDIR(named.st_mode) and
            (named.st_dev, named.st_ino) == (opened.st_dev, opened.st_ino) and
            lock.record == expected,
            "held runtime lock object differs from current build directory")


def validate_resource_contract(
    receipt: dict[str, Any], timeout_seconds: int, cpu_seconds: int,
    address_space_gib: int, output_file_gib: int,
    cml_heap_size: str | None, cml_stack_size: str | None,
) -> None:
    require(all(type(value) is int and value > 0 for value in (
                timeout_seconds, cpu_seconds, address_space_gib, output_file_gib,
            )), "expected direct resource values must be positive integers")
    require(cpu_seconds <= 172800 and address_space_gib <= 120 and
            output_file_gib <= 16,
            "expected direct resource values exceed the controller contract")
    require(receipt.get("timeout_seconds") == timeout_seconds and
            receipt.get("resource_limits") == {
                "cpu_seconds": cpu_seconds,
                "address_space_bytes": address_space_gib * GIB,
                "output_file_bytes": output_file_gib * GIB,
            }, "direct resource limits differ from the explicit contract")
    runtime_environment = dict(RUNTIME_BASE_ENVIRONMENT)
    for name, value in (
        ("CML_HEAP_SIZE", cml_heap_size),
        ("CML_STACK_SIZE", cml_stack_size),
    ):
        if value is not None:
            require(value.isascii() and value.isdecimal() and
                    value[0] != "0" and int(value) > 0,
                    f"malformed explicit {name}")
            runtime_environment[name] = value
    require(receipt.get("runtime_environment") == runtime_environment,
            "direct runtime environment differs from the exact contract")


def expected_action_projection(
    controller: Any, prepared: dict[str, Any],
) -> list[dict[str, Any]]:
    return [{
        "index": index,
        "source_sha256": action["source_sha256"],
        "logical_source_delta": action["logical_source_delta"],
        "logical_source_delta_sha256": action["logical_source_delta_sha256"],
    } for index, action in enumerate(prepared["actions"])]


def retained_controller_projection(
    current: dict[str, Any],
) -> dict[str, Any]:
    """Project live controller evidence into the snapshot's closed schema."""
    sources = []
    for label, source in sorted(current["local_sources"].items()):
        sources.append({
            "label": label,
            "source_path": source["source_path"],
            "execution_binding": source["execution_binding"],
            "path": f"controller/python-source/{label}",
            **{field: source[field] for field in ("bytes", "sha256", "md5")},
        })
    python_runtime = current["python_runtime"]
    executable = python_runtime["executable"]
    executable_data = stable_file_bytes(
        Path(executable["path"]), "current controller Python executable",
    )
    executable_record = data_record(executable_data)
    require(all(executable.get(field) == executable_record[field]
                for field in ("bytes", "sha256")),
            "current controller Python executable bytes differ")
    elf_objects = []
    for path_string, expected in sorted(
        python_runtime["elf_closure"]["files"].items()
    ):
        data = stable_file_bytes(
            Path(path_string), "current controller Python ELF object",
        )
        observed = data_record(data)
        require(all(expected.get(field) == observed[field]
                    for field in ("bytes", "sha256")),
                "current controller Python ELF object bytes differ")
        elf_objects.append({
            "source_path": path_string,
            "path": (
                "controller/python-runtime-elf/" +
                f"{expected['sha256'][:16]}-{Path(path_string).name}"
            ),
            **data_record(data),
        })
    host_tools = []
    for label, tool in sorted(current["host_tools"].items()):
        host_tools.append({
            "label": label,
            "invocation_path": tool["invocation_path"],
            "resolved_path": tool["resolved_path"],
            "symlink_target": tool["symlink_target"],
            "path": f"controller/host-tools/{label}-{Path(tool['resolved_path']).name}",
            **{field: tool[field] for field in ("bytes", "sha256", "md5")},
        })
    return {
        "source_root": current["source_root"],
        "direct_script_startup": current["direct_script_startup"],
        "commit_binding": current["commit_binding"],
        "python_startup_flags": current["python_startup_flags"],
        "python_startup_options": current["python_startup_options"],
        "initial_top_level_compilation_in_host_trust_boundary":
            current["initial_top_level_compilation_in_host_trust_boundary"],
        "local_sources": sources,
        "python_runtime": {
            "execution_binding": python_runtime["execution_binding"],
            "version": python_runtime["version"],
            "executable": {
                "source_path": executable["path"],
                "path": f"controller/python-runtime/{Path(executable['path']).name}",
                **data_record(executable_data),
            },
            "elf_policy": python_runtime["elf_closure"]["policy"],
            "elf_dynamic_path_tags":
                python_runtime["elf_closure"]["dynamic_path_tags"],
            "elf_roles": python_runtime["elf_closure"]["roles"],
            "virtual_elf_objects":
                python_runtime["elf_closure"]["virtual_objects"],
            "elf_objects": elf_objects,
        },
        "host_tools": host_tools,
        "git_environment": current["git_environment"],
        "broader_python_standard_library_in_host_trust_boundary": True,
    }


def validate_pinned_plan_tree(
    controller: Any, plan_fd_root: Path, prepared: dict[str, Any],
    plan_sha256: str,
) -> None:
    """Validate exact plan bytes and closure through the pinned descriptor."""
    plan = prepared["plan"]
    require(plan_sha256 == prepared["plan_record"]["sha256"],
            "explicit direct plan SHA-256 differs from current authority")
    plan_data = stable_file_bytes(plan_fd_root / "plan.json", "pinned direct plan")
    require(data_record(plan_data) == prepared["plan_record"] and
            plan_data == controller.flyspeck_stratum_plan.json_bytes(plan),
            "pinned direct plan bytes differ from reconstructed authority")
    materialization_name = controller.flyspeck_stratum_plan.HOST_MATERIALIZATION
    materialization_data = stable_file_bytes(
        plan_fd_root / materialization_name, "pinned direct materialization",
    )
    materialization = decode_object(
        materialization_data, "pinned direct materialization",
    )
    require(data_record(materialization_data) == prepared["materialization_record"] and
            materialization_data ==
            controller.flyspeck_stratum_plan.json_bytes(materialization),
            "pinned direct materialization differs from current authority")
    schedule = controller.flyspeck_stratum_plan.make_host_schedule(
        plan, plan_sha256,
    )
    schedule_data = stable_file_bytes(
        plan_fd_root / "host-schedule-template.json", "pinned host schedule",
    )
    require(schedule_data == controller.flyspeck_stratum_plan.json_bytes(schedule),
            "pinned host schedule differs from reconstructed authority")
    expected_files = {
        "plan.json", materialization_name, "host-schedule-template.json",
    }
    for boundary in plan["boundaries"] + plan["diagnostic_cutpoints"]:
        record = boundary["cumulative_prefix"]
        relative = Path(record["path"])
        require(not relative.is_absolute() and ".." not in relative.parts and
                relative.as_posix() == record["path"],
                "unsafe authenticated direct-prefix path")
        data = stable_file_bytes(
            plan_fd_root / relative, f"pinned direct prefix {relative}",
        )
        require_record(data, record, f"pinned direct prefix {relative}")
        expected_files.add(relative.as_posix())
    files, directories = _ordinary_tree(plan_fd_root, "direct plan")
    require(files == expected_files and directories == {"."},
            "pinned direct plan tree closure mismatch")
    require(stat.S_IMODE(plan_fd_root.stat().st_mode) ==
            controller.flyspeck_stratum_plan.PLAN_ROOT_MODE,
            "pinned direct plan root mode mismatch")
    for relative in expected_files:
        require(stat.S_IMODE((plan_fd_root / relative).stat().st_mode) ==
                controller.flyspeck_stratum_plan.PLAN_FILE_MODE,
                f"pinned direct plan file mode mismatch: {relative}")


def _ordinary_tree(
    root: Path, label: str = "direct result",
) -> tuple[set[str], set[str]]:
    files: set[str] = set()
    directories = {"."}
    for current, directory_names, file_names in os.walk(
        root, topdown=True, followlinks=False,
    ):
        current_path = Path(current)
        for name in directory_names:
            path = current_path / name
            metadata = path.stat(follow_symlinks=False)
            relative = path.relative_to(root).as_posix()
            require(stat.S_ISDIR(metadata.st_mode),
                    f"non-directory or symlink in {label}: {relative}")
            directories.add(relative)
        for name in file_names:
            path = current_path / name
            metadata = path.stat(follow_symlinks=False)
            relative = path.relative_to(root).as_posix()
            require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1,
                    f"non-ordinary or multiply linked file in {label}: {relative}")
            files.add(relative)
    return files, directories


def validate_closed_result_tree(
    result_root: Path, receipt: dict[str, Any], receipt_data: bytes,
    snapshot: dict[str, Any], controller: Any,
) -> None:
    inputs = receipt.get("inputs")
    require(isinstance(inputs, dict), "missing direct receipt input closure")
    snapshot_files = snapshot.get("files")
    require(isinstance(snapshot_files, list), "missing direct snapshot files")
    expected_records: dict[str, dict[str, Any]] = {}
    for record in snapshot_files:
        require(isinstance(record, dict) and isinstance(record.get("path"), str),
                "malformed direct snapshot file record")
        relative = Path(record["path"])
        require(not relative.is_absolute() and ".." not in relative.parts and
                relative.as_posix() == record["path"],
                "unsafe direct snapshot file path")
        path = f"snapshot/{record['path']}"
        require(path not in expected_records,
                f"duplicate direct snapshot file path: {path}")
        expected_records[path] = record

    for field, relative in CONTROL_INPUT_PATHS.items():
        require(relative not in expected_records,
                f"duplicate direct control path: {relative}")
        expected_records[relative] = inputs.get(field)
    expected_records.update({
        "snapshot.json": inputs.get("runtime_snapshot"),
        "attempt.json": receipt.get("initial_attempt"),
        "candle.log": receipt.get("log"),
    })
    require(all(isinstance(record, dict) for record in expected_records.values()),
            "direct result is missing a retained file record")
    expected_files = set(expected_records) | {"receipt.json"}
    expected_directories = {"."}
    for relative in expected_files:
        expected_directories.update(
            parent.as_posix() for parent in Path(relative).parents
            if parent != Path(".")
        )
    observed_files, observed_directories = _ordinary_tree(result_root)
    require(observed_files == expected_files,
            "direct result contains unrecorded or missing files")
    require(observed_directories == expected_directories,
            "direct result contains unrecorded or missing directories")

    for relative, record in expected_records.items():
        path = result_root / relative
        data = stable_file_bytes(
            path, f"direct result {relative}", allow_empty=True,
            max_bytes=(MAX_DIRECT_LOG_BYTES if relative == "candle.log" else None),
        )
        require_record(data, record, f"direct result {relative}")
        expected_mode = (
            0o555
            if relative == "snapshot/candle/candle/build/cake" else 0o444
        )
        require(stat.S_IMODE(path.stat(follow_symlinks=False).st_mode) ==
                expected_mode,
                f"direct result retained file mode mismatch: {relative}")
        del data
    retained_receipt = stable_file_bytes(result_root / "receipt.json", "direct receipt")
    require(retained_receipt == receipt_data == controller.json_bytes(receipt),
            "direct receipt bytes are not exact canonical JSON")
    require(stat.S_IMODE((result_root / "receipt.json").stat(
                follow_symlinks=False,
            ).st_mode) == 0o444,
            "direct receipt file mode mismatch")
    for relative in sorted(expected_directories - {"."}):
        require(stat.S_IMODE((result_root / relative).stat(
                    follow_symlinks=False,
                ).st_mode) == 0o555,
                f"direct result retained directory mode mismatch: {relative}")


def validate_current_bindings(
    controller: Any, receipt: dict[str, Any], prepared: dict[str, Any],
    candle_root: Path, linked: dict[str, Any], boundary: str,
    candle_head: str, cakeml_head: str, hol4_head: str,
    evidence_schema: int = 5,
) -> None:
    inputs = receipt.get("inputs")
    require(isinstance(inputs, dict) and
            set(inputs) == controller.DIRECT_INPUT_FIELDS,
            "published direct result has malformed input closure")
    require(evidence_schema in (5, 6) and
            receipt.get("schema") == evidence_schema and
            receipt.get("kind") == "candle-flyspeck-compiled-stratum-attempt" and
            receipt.get("state") == "completed" and
            receipt.get("validation_error") is None and
            receipt.get("timed_out") is False and
            receipt.get("exit_code") == 0 and
            receipt.get("postflight_reauthenticated") is True and
            receipt.get("s2_s3_evidence") is False,
            "published direct result is not a completed nonpromotable pass")
    require(receipt.get("boundary_id") == boundary and
            receipt.get("diagnostic_only") is prepared["diagnostic_only"] and
            receipt.get("action_count") == len(prepared["actions"]) and
            receipt.get("action_markers_validated") == len(prepared["actions"]),
            "published direct result differs from the selected boundary")
    require(receipt.get("repositories") == {
                "candle": candle_head,
                "flyspeck": prepared["plan"]["repositories"]["flyspeck_commit"],
            }, "published direct result repository closure differs")
    require(linked.get("candle_commit") == candle_head and
            linked.get("cakeml_commit") == cakeml_head and
            linked.get("hol4_commit") == hol4_head,
            "linked runtime differs from explicit Candle/CakeML/HOL4 authority")
    expected_actions = expected_action_projection(controller, prepared)
    require(receipt.get("expected_action_events") == expected_actions and
            receipt.get("ordered_expected_action_sha256") ==
            controller.canonical_sha256(expected_actions) and
            receipt.get("expected_logical_source_closure") ==
            prepared["logical_source_closure"],
            "published direct result differs from reconstructed source authority")
    require(inputs.get("plan") == prepared["plan_record"] and
            inputs.get("host_materialization") ==
            prepared["materialization_record"] and
            inputs.get("manifest") == prepared["manifest_record"] and
            inputs.get("linked_provenance") == prepared["linked_record"] and
            inputs.get("authenticated_prefix") == prepared["prefix_record"],
            "published direct result input records differ from current plan")
    harness_fields = {
        "setup": controller.SETUP_RELATIVE.as_posix(),
        "check": controller.CHECK_RELATIVE.as_posix(),
        "fingerprint_serializer": controller.FINGERPRINT_RELATIVE.as_posix(),
        "l2_target": controller.L2_TARGET_RELATIVE.as_posix(),
    }
    require(all(inputs.get(field) == prepared["harness_records"][relative]
                for field, relative in harness_fields.items()),
            "published direct result harness records differ from current plan")
    linked_path = candle_root / controller.LINKED_RECORD_RELATIVE
    linked_data = stable_file_bytes(linked_path, "current linked provenance")
    require(decode_object(linked_data, "current linked provenance") == linked and
            linked_data == controller.json_bytes(linked) and
            data_record(linked_data) == inputs["linked_provenance"],
            "published direct result differs from current linked provenance")
    runtime_data = stable_file_bytes(
        candle_root / "candle/build/cake", "current linked runtime",
    )
    retained_runtime = inputs.get("runtime_executable")
    require(isinstance(retained_runtime, dict) and
            all(retained_runtime.get(field) == data_record(runtime_data)[field]
                for field in ("bytes", "sha256", "md5")),
            "published direct result differs from current linked runtime")


def validate_archived_link_authority(
    controller: Any, result_fd_root: Path, receipt: dict[str, Any],
    linked: dict[str, Any], candle_root: Path, cakeml_head: str, hol4_head: str,
) -> None:
    """Bind archived link/bootstrap/log/cake bytes to current schema-6 state."""
    inputs = receipt["inputs"]
    linked_relative = "snapshot/candle/candle/build/cakeml-build-provenance.json"
    archived_linked_data = stable_file_bytes(
        result_fd_root / linked_relative, "archived linked provenance",
    )
    archived_linked = decode_object(
        archived_linked_data, "archived linked provenance",
    )
    current_linked_data = stable_file_bytes(
        candle_root / controller.LINKED_RECORD_RELATIVE,
        "current linked provenance",
    )
    require(archived_linked == linked and archived_linked_data == current_linked_data and
            archived_linked_data == controller.json_bytes(archived_linked) and
            data_record(archived_linked_data) ==
            inputs["archived_linked_provenance"],
            "archived linked provenance differs from current authority")

    bootstrap_relative = "snapshot/candle/candle/build/bootstrap-provenance.json"
    archived_bootstrap_data = stable_file_bytes(
        result_fd_root / bootstrap_relative, "archived bootstrap provenance",
    )
    archived_bootstrap = decode_object(
        archived_bootstrap_data, "archived bootstrap provenance",
    )
    current_bootstrap_data = stable_file_bytes(
        candle_root / "candle/build/bootstrap-provenance.json",
        "current linked bootstrap provenance",
    )
    current_bootstrap = decode_object(
        current_bootstrap_data, "current linked bootstrap provenance",
    )
    require(archived_bootstrap == current_bootstrap and
            archived_bootstrap_data == current_bootstrap_data ==
            controller.json_bytes(archived_bootstrap) and
            data_record(archived_bootstrap_data) ==
            inputs["archived_bootstrap_provenance"] and
            all(archived_bootstrap.get(field) == expected for field, expected in (
                ("candle_commit", linked["candle_commit"]),
                ("cakeml_commit", cakeml_head),
                ("hol4_commit", hol4_head),
            )), "archived bootstrap provenance differs from linked authority")
    require(all(linked["bootstrap_record"].get(field) ==
                data_record(current_bootstrap_data)[field]
                for field in ("bytes", "sha256")),
            "current bootstrap provenance differs from linked record")

    archived_preflight_data = stable_file_bytes(
        result_fd_root / "snapshot/candle/candle/build/bootstrap-preflight.json",
        "archived bootstrap preflight",
    )
    archived_preflight = decode_object(
        archived_preflight_data, "archived bootstrap preflight",
    )
    current_preflight_data = stable_file_bytes(
        candle_root / "candle/build/bootstrap-preflight.json",
        "current linked bootstrap preflight",
    )
    current_preflight = decode_object(
        current_preflight_data, "current linked bootstrap preflight",
    )
    require(archived_preflight == current_preflight and
            archived_preflight_data == current_preflight_data ==
            controller.json_bytes(archived_preflight) and
            all(linked["bootstrap_preflight"].get(field) ==
                data_record(current_preflight_data)[field]
                for field in ("bytes", "sha256")) and
            all(archived_bootstrap["preflight"].get(field) ==
                data_record(current_preflight_data)[field]
                for field in ("bytes", "sha256")),
            "archived bootstrap preflight differs from linked authority")

    archived_log_data = stable_file_bytes(
        result_fd_root / "snapshot/candle/candle/build/bootstrap.log",
        "archived bootstrap log", allow_empty=True,
    )
    current_log_data = stable_file_bytes(
        candle_root / "candle/build/bootstrap.log",
        "current linked bootstrap log", allow_empty=True,
    )
    require(archived_log_data == current_log_data and
            data_record(archived_log_data) == inputs["archived_bootstrap_log"] and
            all(linked["bootstrap_log"].get(field) ==
                data_record(current_log_data)[field]
                for field in ("bytes", "sha256")),
            "archived bootstrap log differs from linked authority")

    archived_cake = result_fd_root / "snapshot/candle/candle/build/cake"
    archived_cake_data = stable_file_bytes(archived_cake, "archived linked runtime")
    current_cake_data = stable_file_bytes(
        candle_root / "candle/build/cake", "current linked runtime",
    )
    require(archived_cake_data == current_cake_data and
            data_record(archived_cake_data) == {
                field: inputs["runtime_executable"][field]
                for field in ("bytes", "sha256", "md5")
            }, "archived runtime executable differs from current linked runtime")
    controller.cakeml_artifact_provenance.validate_elf_dynamic_closure(
        archived_cake, linked["runtime_elf_closure"],
    )


def reconstruct_snapshot_records(
    controller: Any, candle_root: Path, prepared: dict[str, Any],
    linked: dict[str, Any], retained_controller: dict[str, Any],
) -> list[dict[str, Any]]:
    """Reconstruct the producer's exact ordered snapshot inventory."""
    records: dict[str, dict[str, Any]] = {}

    def add_record(
        path: str, classification: str, record: dict[str, Any],
    ) -> None:
        relative = Path(path)
        require(not relative.is_absolute() and ".." not in relative.parts and
                relative.as_posix() == path,
                f"unsafe reconstructed snapshot path: {path}")
        candidate = {
            "path": path,
            **{field: record[field] for field in ("bytes", "sha256", "md5")},
            "classes": [classification],
        }
        previous = records.get(path)
        if previous is None:
            records[path] = candidate
        else:
            require(all(previous[field] == candidate[field]
                        for field in ("bytes", "sha256", "md5")),
                    f"reconstructed snapshot collision differs: {path}")
            if classification not in previous["classes"]:
                previous["classes"].append(classification)

    def current_file_record(
        path: Path, expected: dict[str, Any], label: str,
    ) -> dict[str, Any]:
        data = stable_file_bytes(path, label, allow_empty=True)
        observed = data_record(data)
        require(all(expected.get(field) == observed[field]
                    for field in ("bytes", "sha256") if field in expected) and
                ("md5" not in expected or expected["md5"] == observed["md5"]),
                f"{label} differs from current authority")
        return observed

    for binding in prepared["source_runtime"]:
        repository = binding["repository"]
        add_record(
            f"{repository}/{binding['path']}", f"source:{repository}", binding,
        )
    for relative in (
        controller.SOURCE_DIGEST_RELATIVE,
        controller.SETUP_RELATIVE,
        controller.CHECK_RELATIVE,
        controller.FINGERPRINT_RELATIVE,
        controller.L2_TARGET_RELATIVE,
    ):
        add_record(
            f"candle/{relative.as_posix()}", "runtime-harness",
            prepared["harness_records"][relative.as_posix()],
        )
    linked_outputs = linked["outputs"]
    for name, expected in sorted(linked_outputs.items()):
        observed = current_file_record(
            candle_root / "candle/build" / name, expected,
            f"current linked snapshot input {name}",
        )
        add_record(f"candle/candle/build/{name}", "linked-runtime", observed)
    for name in ("config_enc_str.txt", "candle_boot.ml"):
        observed = current_file_record(
            candle_root / "candle/build" / name, linked_outputs[name],
            f"current linked root input {name}",
        )
        add_record(f"candle/{name}", "linked-root-input", observed)
    linked_observed = current_file_record(
        candle_root / controller.LINKED_RECORD_RELATIVE,
        prepared["linked_record"], "current linked provenance record",
    )
    add_record(
        f"candle/{controller.LINKED_RECORD_RELATIVE.as_posix()}",
        "linked-provenance-record", linked_observed,
    )
    for path_string, expected in sorted(
        linked["runtime_elf_closure"]["files"].items()
    ):
        observed = current_file_record(
            Path(path_string), expected, "current linked runtime ELF object",
        )
        add_record(
            f"runtime-elf/{expected['sha256'][:16]}-{Path(path_string).name}",
            "archived-runtime-elf", observed,
        )
    for item in prepared["normalized_runtime"]:
        add_record(f"overlay/{item['relative']}", "normalized", item)
    for item in prepared["generated_runtime"]:
        prefix = (
            "generated"
            if item["class"] == "lp-certificate-prepared" else "flyspeck"
        )
        add_record(
            f"{prefix}/{item['relative']}", f"generated:{item['class']}", item,
        )
    for item in prepared["process_runtime"]:
        add_record(f"candle/{item['relative']}", "process-input", item)
    add_record(
        f"plan/{prepared['prefix_record']['path']}",
        "authenticated-prefix", prepared["prefix_record"],
    )
    for item in retained_controller["local_sources"]:
        add_record(item["path"], "controller-python-source", item)
    python_runtime = retained_controller["python_runtime"]
    add_record(
        python_runtime["executable"]["path"],
        "controller-python-executable", python_runtime["executable"],
    )
    for item in python_runtime["elf_objects"]:
        add_record(item["path"], "controller-python-runtime-elf", item)
    for item in retained_controller["host_tools"]:
        add_record(item["path"], "controller-host-tool", item)
    return list(records.values())


def validate_snapshot_against_current_authority(
    controller: Any, snapshot: dict[str, Any], candle_root: Path,
    prepared: dict[str, Any], linked: dict[str, Any],
    retained_controller: dict[str, Any],
) -> None:
    expected = reconstruct_snapshot_records(
        controller, candle_root, prepared, linked, retained_controller,
    )
    require(snapshot.get("files") == expected and
            snapshot.get("file_count") == len(expected) and
            snapshot.get("ordered_file_sha256") ==
            controller.canonical_sha256(expected),
            "runtime snapshot inventory differs from current authority")


def build_gate_result(
    arguments: argparse.Namespace, prepared: dict[str, Any], result_root: Path,
) -> dict[str, Any]:
    return {
        "gate": "published-direct-result-pass",
        "schema": 5,
        "boundary_id": arguments.boundary,
        "action_count": len(prepared["actions"]),
        "state": "completed",
        "scheduling_authority": not prepared["diagnostic_only"],
        "promotion": False,
        "s2_s3_evidence": False,
        "result_root": str(result_root),
        "consumer_project_head": arguments.project_head,
    }


def build_schema6_capture_result(
    protocol: Any,
    arguments: argparse.Namespace,
    receipt: dict[str, Any],
    plan: dict[str, Any],
    receipt_data: bytes,
    plan_data: bytes,
) -> dict[str, Any]:
    """Build one unapproved content-bound capture from already-held sources."""
    require(arguments.evidence_schema == 6 and
            receipt_data == protocol.canonical_json_bytes(receipt) and
            plan_data == protocol.canonical_json_bytes(plan),
            "schema-6 capture sources are not exact canonical JSON")
    expected_authority = {
        "policy": protocol.AUTHENTICATED_CAPTURE_POLICY,
        "consumer_project_commit": arguments.project_head,
        "candle_commit": arguments.candle_head,
        "cakeml_commit": arguments.cakeml_head,
        "hol4_commit": arguments.hol4_head,
        "flyspeck_commit": arguments.flyspeck_head,
    }
    capture = protocol.build_authenticated_schema6_capture(
        receipt, plan, expected_authority,
    )
    require(capture["receipt"] == data_record(receipt_data) and
            capture["authenticated_plan"] == data_record(plan_data) and
            capture["authority"] == expected_authority and
            capture["promotion"] is False and
            capture["approval_included"] is False and
            capture["direct_s2_execution_approved"] is False and
            capture["direct_s3_coverage_approved"] is False and
            capture["v1_3_s3_release_approved"] is False and
            capture["pft_used"] is False and
            capture["s2_s3_evidence"] is False,
            "schema-6 capture differs from held source bytes")
    return capture


def _assemble_compiled_comparison_descriptor(
    protocol: Any,
    arguments: argparse.Namespace,
    capture: dict[str, Any],
    receipt: dict[str, Any],
    checker_relative: str,
    authenticated_sources: dict[str, bytes],
) -> dict[str, Any]:
    """Assemble output only after the enclosing CLI authenticates raw state."""
    source_inventory = [
        {"path": relative, **data_record(data)}
        for relative, data in sorted(authenticated_sources.items())
    ]
    matching_entrypoints = [
        record for record in source_inventory
        if record["path"] == checker_relative
    ]
    require(len(matching_entrypoints) == 1,
            "compiled comparison consumer entrypoint is not authenticated")
    entrypoint = matching_entrypoints[0]
    candidate_authority = {
        "policy": protocol.COMPARISON_CANDIDATE_AUTHORITY_POLICY,
        "authenticator": protocol.COMPILED_COMPARISON_AUTHENTICATOR,
        "project_commit": arguments.project_head,
        "runtime_commit": arguments.candle_head,
        "entrypoint": entrypoint,
        "sources": source_inventory,
    }
    descriptor = {
        "schema": 1,
        "kind": protocol.AUTHENTICATED_COMPARISON_DESCRIPTOR_KIND,
        "role": protocol.COMPILED_COMPARISON_ROLE,
        "ordinal": 0,
        "candidate": data_record(protocol.canonical_json_bytes(capture)),
        "authenticated_nonce": {
            "kind": protocol.COMPILED_COMPARISON_NONCE_KIND,
            "value": receipt["attempt_nonce"],
        },
        "authenticated_plan": capture["authenticated_plan"],
        "semantic_projection": capture["semantic_projection"],
        "coverage_projection": capture["coverage_projection"],
        "candidate_authority": candidate_authority,
        "pft_used": False,
    }
    protocol._validate_authenticated_comparison_descriptor(
        descriptor, role=protocol.COMPILED_COMPARISON_ROLE, ordinal=0,
    )
    require(
        descriptor["candidate_authority"]["entrypoint"] == entrypoint and
        descriptor["candidate_authority"]["sources"] == source_inventory and
        descriptor["pft_used"] is False,
        "compiled comparison descriptor differs from exact consumer",
    )
    return descriptor


def _validate_with_pins(arguments: argparse.Namespace) -> dict[str, Any]:
    require(dict(os.environ) == CONSUMER_ENVIRONMENT,
            "consumer requires exact PATH=/usr/bin:/bin and LC_ALL=C.UTF-8 environment")
    project_root = arguments.project_root.resolve(strict=True)
    checker_source = Path(__file__).resolve(strict=True)
    checker_relative = checker_source.relative_to(project_root).as_posix()
    protocol_relative = "scripts/direct_release_protocol.py"
    consumer_relatives = (
        (checker_relative, protocol_relative)
        if arguments.evidence_schema == 6 else (checker_relative,)
    )
    consumer_sources = authenticate_sources(
        project_root, arguments.project_head, consumer_relatives,
        "direct result consumer",
    )
    checker = consumer_sources[checker_relative]
    require(checker == stable_file_bytes(checker_source, "direct result consumer"),
            "direct result consumer changed after authentication")
    project_protocol = None
    if arguments.evidence_schema == 6:
        project_protocol = exact_source_module(
            "_candle_flyspeck_direct_release_protocol",
            project_root / protocol_relative,
            consumer_sources[protocol_relative],
        )

    candle_root = arguments.candle_root.resolve(strict=True)
    flyspeck_root = arguments.flyspeck_root.resolve(strict=True)
    plan_root = arguments.plan_root.resolve(strict=True)
    result_root = arguments.result_root.resolve(strict=True)
    for supplied, resolved, label in (
        (arguments.candle_root, candle_root, "Candle"),
        (arguments.flyspeck_root, flyspeck_root, "Flyspeck"),
        (arguments.plan_root, plan_root, "plan"),
        (arguments.result_root, result_root, "result"),
    ):
        require(supplied.is_absolute() and supplied == resolved,
                f"{label} root contains a symlink or alias")
    authenticate_git_root(flyspeck_root, arguments.flyspeck_head, "Flyspeck")
    controller = load_controller(candle_root, arguments.candle_head)

    plan_fd_root = Path(f"/proc/self/fd/{arguments._plan_fd}")
    result_fd_root = Path(f"/proc/self/fd/{arguments._result_fd}")
    schema6_output: dict[str, Any] | None = None
    lock = controller.runtime_lock.acquire_build_lock(candle_root)
    try:
        validate_held_runtime_lock(lock, candle_root)
        linked = controller.cakeml_bootstrap_transition.validate_linked_record(
            candle_root,
        )
        require(linked.get("schema") == 6 and
                linked.get("kind") == "candle-linked-pinned-cakeml" and
                linked.get("candle_commit") == arguments.candle_head and
                linked.get("cakeml_commit") == arguments.cakeml_head and
                linked.get("hol4_commit") == arguments.hol4_head,
                "direct result consumer requires ordinary schema-6 linked authority")
        current_controller_execution = controller.collect_controller_execution(
            candle_root,
        )
        controller.bind_controller_sources_to_commit(
            current_controller_execution, candle_root, arguments.candle_head,
        )
        controller.validate_controller_execution(
            current_controller_execution, candle_root, arguments.candle_head,
        )
        prepared = controller.validate_plan(
            candle_root, linked, plan_root, arguments.boundary,
        )
        require(prepared["plan"]["repositories"]["flyspeck_commit"] ==
                arguments.flyspeck_head and
                prepared["flyspeck_root"] == flyspeck_root,
                "direct plan differs from explicit Flyspeck authority")
        validate_pinned_plan_tree(
            controller, plan_fd_root, prepared, arguments.plan_sha256,
        )
        require_named_directory_identity(
            arguments._plan_fd, plan_root, arguments._plan_identity, "plan root",
        )

        receipt_path = result_fd_root / "receipt.json"
        receipt_data = stable_file_bytes(receipt_path, "published direct receipt")
        receipt = decode_object(receipt_data, "published direct receipt")
        snapshot_data = stable_file_bytes(
            result_fd_root / "snapshot.json", "published direct snapshot record",
        )
        snapshot = decode_object(snapshot_data, "published direct snapshot record")
        require(snapshot_data == controller.json_bytes(snapshot),
                "published direct snapshot is not canonical JSON")
        log_record = receipt.get("log")
        require(isinstance(log_record, dict) and
                type(log_record.get("bytes")) is int and
                0 < log_record["bytes"] <= MAX_DIRECT_LOG_BYTES,
                "published direct log exceeds the consumer size cap")
        validate_resource_contract(
            receipt, arguments.timeout_seconds, arguments.max_cpu_seconds,
            arguments.max_address_space_gib, arguments.max_output_file_gib,
            arguments.cml_heap_size, arguments.cml_stack_size,
        )
        validate_current_bindings(
            controller, receipt, prepared, candle_root, linked,
            arguments.boundary, arguments.candle_head,
            arguments.cakeml_head, arguments.hol4_head,
            arguments.evidence_schema,
        )
        require(receipt.get("runtime_lock") == lock.record,
                "published direct result lock differs from held runtime lock")
        require(receipt["inputs"].get("controller_execution") ==
                snapshot.get("controller_execution"),
                "receipt and snapshot controller identities differ")
        retained_controller = receipt["inputs"]["controller_execution"]
        controller.validate_direct_controller_binding(
            retained_controller, arguments.candle_head,
        )
        require(retained_controller == retained_controller_projection(
                    current_controller_execution,
                ), "retained controller execution differs from current authority")
        validate_snapshot_against_current_authority(
            controller, snapshot, candle_root, prepared, linked,
            retained_controller,
        )
        require_record(snapshot_data, receipt["inputs"].get("runtime_snapshot"),
                       "runtime snapshot record")
        validate_archived_link_authority(
            controller, result_fd_root, receipt, linked, candle_root,
            arguments.cakeml_head, arguments.hol4_head,
        )
        attempt_data = stable_file_bytes(
            result_fd_root / "attempt.json", "published initial attempt",
        )
        attempt = decode_object(attempt_data, "published initial attempt")
        initial_fields = (
            controller.DIRECT_V6_ATTEMPT_FIELDS
            if arguments.evidence_schema == 6 else
            controller.DIRECT_V5_ATTEMPT_FIELDS
        )
        initial_projection = {field: receipt[field] for field in initial_fields}
        initial_projection["state"] = "running"
        require(attempt == initial_projection and
                attempt_data == controller.json_bytes(initial_projection),
                "published initial attempt differs from completed receipt")

        validate_closed_result_tree(
            result_fd_root, receipt, receipt_data, snapshot, controller,
        )
        controller.validate_runtime_snapshot(snapshot, result_root)
        runtime_path = result_root / "snapshot/candle/candle/build/cake"
        log_path = result_root / "candle.log"
        validate_evidence = (
            controller.validate_direct_evidence_v6_artifact
            if arguments.evidence_schema == 6 else
            controller.validate_direct_evidence_v5_artifact
        )
        validate_evidence(
            receipt, receipt=True, log_path=log_path,
            runtime_executable_path=runtime_path,
        )

        linked_post = controller.cakeml_bootstrap_transition.validate_linked_record(
            candle_root,
        )
        prepared_post = controller.validate_plan(
            candle_root, linked_post, plan_root, arguments.boundary,
        )
        require(linked_post == linked and
                prepared_post["plan_record"] == prepared["plan_record"] and
                prepared_post["materialization_record"] ==
                prepared["materialization_record"] and
                prepared_post["manifest_record"] == prepared["manifest_record"] and
                prepared_post["prefix_record"] == prepared["prefix_record"] and
                prepared_post["actions"] == prepared["actions"] and
                prepared_post["logical_source_closure"] ==
                prepared["logical_source_closure"],
                "direct authority changed during result revalidation")
        controller.validate_controller_execution(
            current_controller_execution, candle_root, arguments.candle_head,
        )
        validate_pinned_plan_tree(
            controller, plan_fd_root, prepared_post, arguments.plan_sha256,
        )
        validate_archived_link_authority(
            controller, result_fd_root, receipt, linked_post, candle_root,
            arguments.cakeml_head, arguments.hol4_head,
        )
        validate_snapshot_against_current_authority(
            controller, snapshot, candle_root, prepared_post, linked_post,
            retained_controller,
        )
        final_consumer_sources = authenticate_sources(
            project_root, arguments.project_head, consumer_relatives,
            "final direct result consumer",
        )
        require(final_consumer_sources == consumer_sources,
                "direct result consumer authority changed during validation")
        authenticate_git_root(
            flyspeck_root, arguments.flyspeck_head, "final Flyspeck",
        )
        require(stable_file_bytes(receipt_path, "final direct receipt") ==
                receipt_data,
                "direct receipt changed during revalidation")
        validate_closed_result_tree(
            result_fd_root, receipt, receipt_data, snapshot, controller,
        )
        require_named_directory_identity(
            arguments._plan_fd, plan_root, arguments._plan_identity, "plan root",
        )
        require_named_directory_identity(
            arguments._result_fd, result_root, arguments._result_identity,
            "result root",
        )
        validate_held_runtime_lock(lock, candle_root)
        if arguments.evidence_schema == 6:
            require(project_protocol is not None,
                    "schema-6 capture protocol was not authenticated")
            final_plan_data = stable_file_bytes(
                plan_fd_root / "plan.json", "final captured direct plan",
            )
            capture = build_schema6_capture_result(
                project_protocol, arguments, receipt, prepared_post["plan"],
                receipt_data, final_plan_data,
            )
            schema6_output = capture
            if arguments.comparison_candidate:
                descriptor = _assemble_compiled_comparison_descriptor(
                    project_protocol, arguments, capture, receipt,
                    checker_relative, final_consumer_sources,
                )
                require(descriptor["candidate_authority"]["entrypoint"] == {
                            "path": checker_relative, **data_record(checker),
                        }, "compiled descriptor entrypoint changed")
                schema6_output = descriptor
    finally:
        lock.close()

    if schema6_output is not None:
        return schema6_output
    return build_gate_result(arguments, prepared, result_root)


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
    parser.add_argument("--plan-root", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--boundary", required=True)
    parser.add_argument("--candle-root", type=Path, required=True)
    parser.add_argument("--candle-head", required=True)
    parser.add_argument("--cakeml-head", required=True)
    parser.add_argument("--hol4-head", required=True)
    parser.add_argument("--flyspeck-root", type=Path, required=True)
    parser.add_argument("--flyspeck-head", required=True)
    parser.add_argument("--timeout-seconds", type=int, required=True)
    parser.add_argument("--max-cpu-seconds", type=int, required=True)
    parser.add_argument("--max-address-space-gib", type=int, required=True)
    parser.add_argument("--max-output-file-gib", type=int, required=True)
    parser.add_argument(
        "--evidence-schema", type=int, choices=(5, 6), default=5,
    )
    parser.add_argument(
        "--comparison-candidate", action="store_true",
        help=(
            "emit the authenticated compiled comparison descriptor "
            "(schema 6 only)"
        ),
    )
    parser.add_argument("--cml-heap-size")
    parser.add_argument("--cml-stack-size")
    arguments = parser.parse_args()
    require(not arguments.comparison_candidate or arguments.evidence_schema == 6,
            "compiled comparison candidate requires evidence schema 6")
    for value, label, length in (
        (arguments.project_head, "project head", 40),
        (arguments.candle_head, "Candle head", 40),
        (arguments.cakeml_head, "CakeML head", 40),
        (arguments.hol4_head, "HOL4 head", 40),
        (arguments.flyspeck_head, "Flyspeck head", 40),
        (arguments.plan_sha256, "plan SHA-256", 64),
    ):
        require(len(value) == length and
                all(character in "0123456789abcdef" for character in value),
                f"malformed exact {label}")
    print(json.dumps(validate(arguments), sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ResultError, OSError, UnicodeError, ValueError, KeyError,
            TypeError, AttributeError, IndexError,
            subprocess.SubprocessError) as error:
        raise SystemExit(f"published direct result rejected: {error}") from error
