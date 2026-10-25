#!/usr/bin/env python3
"""Fail-closed gate for project integration runs longer than one hour."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Callable


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
DEFAULT_LEDGER = PROJECT / "docs/long-run-hazard-ledger.json"
NORMALIZATION = PROJECT / "scripts/preflight-fast-nl-v663-normalization.sh"
LITERAL_CLOSURE = PROJECT / "scripts/audit-fast-nl-support-source-closure.py"
MODULE_CLOSURE = PROJECT / "scripts/audit-fast-nl-support-module-closure.py"
ACTION_OVERLAY_PARTITION = (
    PROJECT / "scripts/audit-fast-nl-v668-action-overlay-partition.py"
)
RUNTIME_SYMBOL_SURFACE = (
    PROJECT / "scripts/audit-fast-nl-v670-runtime-symbol-surface.py"
)
THEOREM_GATE = PROJECT / "scripts/run-fast-nl-first-original-theorem-gate-v1.sh"
THEOREM_RUNNER = PROJECT / "scripts/run-fast-nl-exact-one-call-v1.sh"


@dataclass
class CheckResult:
    ok: bool
    detail: str


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_receipt(path: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def run_checked(command: list[str], timeout: int = 180) -> CheckResult:
    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return CheckResult(False, f"command_error={error}")
    lines = completed.stdout.splitlines()
    summary = [
        line
        for line in lines
        if re.match(
            r"^(status|.*_count|missing_.*|stale_.*|unresolved_.*|"
            r"dynamic_.*|parse_error.*)=",
            line,
        )
    ]
    if not summary:
        summary = lines[-8:]
    detail = f"exit={completed.returncode} " + " | ".join(summary[:16])
    return CheckResult(completed.returncode == 0, detail)


def check_runtime_provenance(config: dict, _: pathlib.Path) -> CheckResult:
    runtime = pathlib.Path(config["runtime_dir"])
    binary = runtime / "cake"
    manifest_path = runtime / "DEVELOPMENT-NONPROMOTABLE.json"
    receipt_path = pathlib.Path(config["x64_receipt"])
    for path in (binary, manifest_path, receipt_path):
        if not path.is_file():
            return CheckResult(False, f"missing={path}")
    actual = sha256(binary)
    if actual != config["runtime_sha256"]:
        return CheckResult(False, f"runtime_sha256={actual}")
    receipt = parse_receipt(receipt_path)
    heads = config["required_heads"]
    expected_receipt = {
        "status": "0",
        "last_phase": "complete",
        "cake_head": heads["cakeml"],
        "compiler_source_head": heads["compiler_source"],
        "candle_head": heads["candle"],
        "hol_head": heads["hol4"],
        "runtime": str(runtime),
    }
    for key, expected in expected_receipt.items():
        if receipt.get(key) != expected:
            return CheckResult(False, f"receipt_{key}={receipt.get(key)!r}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    repositories = manifest.get("repositories", {})
    expected_manifest = {
        "cakeml": heads["cakeml"],
        "candle": heads["candle"],
        "hol4": heads["hol4"],
    }
    for name, expected in expected_manifest.items():
        actual_head = repositories.get(name, {}).get("commit")
        if actual_head != expected:
            return CheckResult(False, f"manifest_{name}={actual_head!r}")
    return CheckResult(True, f"runtime_sha256={actual} heads=exact")


def check_source_worktrees_clean(config: dict, _: pathlib.Path) -> CheckResult:
    for text_path, expected_head in config["source_worktrees"].items():
        path = pathlib.Path(text_path)
        try:
            head = subprocess.check_output(
                ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
            ).strip()
            status = subprocess.check_output(
                ["git", "-C", str(path), "status", "--porcelain"], text=True
            )
        except (OSError, subprocess.CalledProcessError) as error:
            return CheckResult(False, f"git_error={path}:{error}")
        if head != expected_head:
            return CheckResult(False, f"wrong_head={path}:{head}")
        if status:
            return CheckResult(False, f"dirty_worktree={path}")
    return CheckResult(True, f"clean_worktree_count={len(config['source_worktrees'])}")


def check_normalization(_: dict, __: pathlib.Path) -> CheckResult:
    return run_checked([str(NORMALIZATION)], timeout=60)


def check_literal_closure(_: dict, __: pathlib.Path) -> CheckResult:
    return run_checked([str(LITERAL_CLOSURE)], timeout=120)


def check_module_closure(_: dict, __: pathlib.Path) -> CheckResult:
    return run_checked([str(MODULE_CLOSURE)], timeout=120)


def check_action_overlay_partition(_: dict, __: pathlib.Path) -> CheckResult:
    return run_checked([str(ACTION_OVERLAY_PARTITION)], timeout=30)


def check_runtime_symbol_surface(_: dict, __: pathlib.Path) -> CheckResult:
    return run_checked([str(RUNTIME_SYMBOL_SURFACE)], timeout=60)


def check_checkpoint_integrity(config: dict, _: pathlib.Path) -> CheckResult:
    seen: set[pathlib.Path] = set()
    for receipt_text in config["checkpoint_receipts"]:
        receipt_path = pathlib.Path(receipt_text)
        if not receipt_path.is_file():
            return CheckResult(False, f"missing_receipt={receipt_path}")
        receipt = parse_receipt(receipt_path)
        checkpoint_text = receipt.get("checkpoint")
        expected_sha = receipt.get("checkpoint_sha256")
        expected_size = receipt.get("checkpoint_size_bytes")
        if not checkpoint_text or not expected_sha or not expected_size:
            return CheckResult(False, f"incomplete_receipt={receipt_path}")
        checkpoint = pathlib.Path(checkpoint_text)
        if not checkpoint.is_file():
            return CheckResult(False, f"missing_checkpoint={checkpoint}")
        if checkpoint.stat().st_size != int(expected_size):
            return CheckResult(False, f"checkpoint_size={checkpoint}")
        if checkpoint not in seen and sha256(checkpoint) != expected_sha:
            return CheckResult(False, f"checkpoint_sha256={checkpoint}")
        seen.add(checkpoint)
    return CheckResult(True, f"authenticated_checkpoint_count={len(seen)}")


def short_probe_input_manifest(paths: list[pathlib.Path]) -> tuple[str, str]:
    """Return the canonical input manifest text and its SHA-256 digest."""

    lines = []
    for path in paths:
        resolved = path.resolve()
        lines.append(f"{resolved}\t{sha256(resolved)}")
    text = "\n".join(lines) + "\n"
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_short_runtime_probe(config: dict, _: pathlib.Path) -> CheckResult:
    """Require a bounded runtime smoke test over the exact planned support bytes."""

    probe = config.get("short_runtime_probe")
    if not isinstance(probe, dict):
        return CheckResult(False, "short_probe_config=missing")
    required_keys = {
        "receipt",
        "maximum_elapsed_seconds",
        "predecessor_checkpoint_receipt",
        "required_files",
    }
    missing_keys = sorted(required_keys - set(probe))
    if missing_keys:
        return CheckResult(False, f"short_probe_config_missing={missing_keys[0]}")

    required_files = [pathlib.Path(item) for item in probe["required_files"]]
    if not required_files:
        return CheckResult(False, "short_probe_required_files=empty")
    for path in required_files:
        if not path.is_file():
            return CheckResult(False, f"short_probe_input_missing={path}")
    _, manifest_sha = short_probe_input_manifest(required_files)

    predecessor_receipt_path = pathlib.Path(probe["predecessor_checkpoint_receipt"])
    if not predecessor_receipt_path.is_file():
        return CheckResult(False, f"short_probe_predecessor_missing={predecessor_receipt_path}")
    predecessor = parse_receipt(predecessor_receipt_path)
    predecessor_sha = predecessor.get("checkpoint_sha256")
    if not predecessor_sha:
        return CheckResult(False, "short_probe_predecessor_sha=missing")

    receipt_path = pathlib.Path(probe["receipt"])
    if not receipt_path.is_file():
        return CheckResult(False, f"short_probe_receipt_missing={receipt_path}")
    receipt = parse_receipt(receipt_path)
    expected = {
        "receipt_kind": "development-fast-nl-short-runtime-probe-v1",
        "release_evidence": "false",
        "status": "0",
        "runtime_sha256": config["runtime_sha256"],
        "predecessor_checkpoint_sha256": predecessor_sha,
        "input_manifest_sha256": manifest_sha,
        "ready_marker_count": "1",
        "source_error_count": "0",
        "pending_source_id_count": "0",
    }
    for key, expected_value in expected.items():
        if receipt.get(key) != expected_value:
            return CheckResult(False, f"short_probe_{key}={receipt.get(key)!r}")
    try:
        elapsed = float(receipt["elapsed_seconds"])
        maximum = float(probe["maximum_elapsed_seconds"])
    except (KeyError, TypeError, ValueError) as error:
        return CheckResult(False, f"short_probe_elapsed_error={error}")
    if elapsed < 0 or elapsed > maximum or maximum > 3600:
        return CheckResult(
            False,
            f"short_probe_elapsed_seconds={elapsed} maximum_seconds={maximum}",
        )
    return CheckResult(
        True,
        f"short_probe_elapsed_seconds={elapsed} input_manifest_sha256={manifest_sha}",
    )


def check_predecessor_identity_coverage(config: dict, _: pathlib.Path) -> CheckResult:
    """Reject checkpoints created before the candidate identity table existed."""

    probe = config.get("short_runtime_probe")
    if not isinstance(probe, dict):
        return CheckResult(False, "predecessor_identity_config=missing")
    source_receipt_text = probe.get("source_configuration_receipt")
    required_inputs_text = probe.get("source_configuration_inputs")
    expected_count = config.get("required_authenticated_fast_nl_source_count")
    if (
        not isinstance(source_receipt_text, str)
        or not isinstance(required_inputs_text, list)
        or not isinstance(expected_count, int)
    ):
        return CheckResult(False, "predecessor_identity_config=incomplete")
    source_receipt_path = pathlib.Path(source_receipt_text)
    if not source_receipt_path.is_file():
        return CheckResult(False, f"source_configuration_receipt_missing={source_receipt_path}")
    source_receipt = parse_receipt(source_receipt_path)
    if source_receipt.get("authenticated_fast_nl_source_count") != str(expected_count):
        return CheckResult(
            False,
            "authenticated_fast_nl_source_count="
            f"{source_receipt.get('authenticated_fast_nl_source_count')!r}",
        )
    source_checkpoint_text = source_receipt.get("checkpoint")
    if not source_checkpoint_text:
        return CheckResult(False, "source_configuration_checkpoint=missing")

    manifest_path = source_receipt_path.parent / "input-files.sha256"
    if not manifest_path.is_file():
        return CheckResult(False, f"source_configuration_manifest_missing={manifest_path}")
    manifest_lines = set(manifest_path.read_text(encoding="utf-8").splitlines())
    for text_path in required_inputs_text:
        path = pathlib.Path(text_path).resolve()
        if not path.is_file():
            return CheckResult(False, f"source_configuration_input_missing={path}")
        expected_line = f"{sha256(path)}  {path}"
        if expected_line not in manifest_lines:
            return CheckResult(False, f"source_configuration_input_unbound={path}")

    predecessor_path = pathlib.Path(probe["predecessor_checkpoint_receipt"])
    if not predecessor_path.is_file():
        return CheckResult(False, f"identity_predecessor_receipt_missing={predecessor_path}")
    predecessor = parse_receipt(predecessor_path)
    try:
        configured_checkpoint = pathlib.Path(source_checkpoint_text).resolve()
        observed_base = pathlib.Path(predecessor["base_checkpoint"]).resolve()
    except KeyError:
        return CheckResult(False, "identity_predecessor_base_checkpoint=missing")
    if observed_base != configured_checkpoint:
        return CheckResult(
            False,
            f"identity_predecessor_base_checkpoint={observed_base}",
        )
    return CheckResult(
        True,
        f"authenticated_fast_nl_source_count={expected_count} predecessor_lineage=exact",
    )


def controller_run_target(controller: pathlib.Path) -> pathlib.Path | None:
    text = controller.read_text(encoding="utf-8")
    match = re.search(r"(?m)^run=(/[^\s]+)$", text)
    return pathlib.Path(match.group(1)) if match else None


def check_bounded_controller(config: dict, controller: pathlib.Path) -> CheckResult:
    if not controller.is_file():
        return CheckResult(False, f"missing_controller={controller}")
    text = controller.read_text(encoding="utf-8")
    required = (
        "set -euo pipefail",
        "check-long-run-hazards.py",
        "FAST_NL_BASE_TIMEOUT_SECONDS",
        "FAST_NL_ACTION49_TIMEOUT_SECONDS",
        "FAST_NL_SUPPORT_TIMEOUT_SECONDS",
        "FAST_NL_CALL_TIMEOUT_SECONDS",
    )
    missing = [item for item in required if item not in text]
    if missing:
        return CheckResult(False, f"missing_controller_contract={','.join(missing)}")
    timeouts: dict[str, int] = {}
    for name in required[2:]:
        match = re.search(rf"(?m)^export {name}=([0-9]+)$", text)
        if not match:
            return CheckResult(False, f"nonliteral_timeout={name}")
        timeouts[name] = int(match.group(1))
    maximum = (
        timeouts["FAST_NL_BASE_TIMEOUT_SECONDS"]
        + timeouts["FAST_NL_ACTION49_TIMEOUT_SECONDS"]
        + timeouts["FAST_NL_SUPPORT_TIMEOUT_SECONDS"]
        + 2 * timeouts["FAST_NL_CALL_TIMEOUT_SECONDS"]
    )
    if maximum > int(config["maximum_total_seconds"]):
        return CheckResult(False, f"declared_maximum_seconds={maximum}")
    return CheckResult(
        True,
        f"declared_maximum_seconds={maximum} controller_sha256={sha256(controller)}",
    )


def check_theorem_controller_contract(_: dict, controller: pathlib.Path) -> CheckResult:
    if not controller.is_file():
        return CheckResult(False, f"missing_controller={controller}")
    controller_text = controller.read_text(encoding="utf-8")
    gate_text = THEOREM_GATE.read_text(encoding="utf-8")
    runner_text = THEOREM_RUNNER.read_text(encoding="utf-8")
    required_controller = ("run-fast-nl-first-original-theorem-gate-v1.sh",)
    required_gate = (
        '"$scripts/run-fast-nl-exact-one-call-v1.sh" theorem',
        '"$scripts/run-fast-nl-exact-one-call-v1.sh" theorem-repeat',
        "theorem_digest=48c97d39af116042909b7896d0d83123",
        "cells=4173 chunks=1 equations=344 assumptions=0 axiom_growth=0",
        "fast_timing_ok=1",
        "repeat_call_digest == \"$first_call_digest\"",
    )
    required_runner = (
        "fast_numerical_max_seconds=120",
        "numerical_watchdog_seconds=180",
        "numerical_timing_count -eq 1",
        "CANDLE_REGISTERED_FULL_CALL_REGISTERED_NUMERICAL_BEGIN",
        "CANDLE_REGISTERED_FULL_CALL_REGISTERED_NUMERICAL_END",
        "sha256sum -c \"$base_dir/checkpoint.sha256\"",
    )
    for label, text, required in (
        ("controller", controller_text, required_controller),
        ("gate", gate_text, required_gate),
        ("runner", runner_text, required_runner),
    ):
        missing = [item for item in required if item not in text]
        if missing:
            return CheckResult(False, f"{label}_missing={missing[0]}")
    return CheckResult(True, "two_fresh_calls=required exact_digest=required fast_watchdog=required")


def check_resource_headroom(config: dict, _: pathlib.Path) -> CheckResult:
    memory: dict[str, int] = {}
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            match = re.search(r"([0-9]+)", value)
            if match:
                memory[key] = int(match.group(1))
    available_gib = memory.get("MemAvailable", 0) / (1024 * 1024)
    minimum = float(config["minimum_available_memory_gib"])
    if available_gib < minimum:
        return CheckResult(False, f"available_memory_gib={available_gib:.2f}")
    # The gate command itself contains the controller path as an argument.
    # Exclude the gate and its launcher ancestry so that this audit does not
    # mistake its own shell/time wrappers for an already-running controller.
    ancestry = {os.getpid()}
    ancestor = os.getppid()
    while ancestor > 1 and ancestor not in ancestry:
        ancestry.add(ancestor)
        status_path = pathlib.Path(f"/proc/{ancestor}/status")
        try:
            status_text = status_path.read_text(encoding="utf-8")
        except OSError:
            break
        match = re.search(r"(?m)^PPid:\s*([0-9]+)$", status_text)
        if not match:
            break
        ancestor = int(match.group(1))
    listing = subprocess.check_output(["ps", "-eo", "pid=,args="], text=True)
    pattern = re.compile(config["active_controller_pattern"])
    active = []
    for line in listing.splitlines():
        match = re.match(r"\s*([0-9]+)\s+(.*)", line)
        if match and int(match.group(1)) not in ancestry and pattern.search(match.group(2)):
            active.append(match.group(1))
    maximum = int(config["maximum_active_matching_controllers"])
    if len(active) > maximum:
        return CheckResult(False, f"active_matching_controllers={','.join(active)}")
    return CheckResult(True, f"available_memory_gib={available_gib:.2f} active_matching_controllers=0")


def check_fresh_run_target(_: dict, controller: pathlib.Path) -> CheckResult:
    if not controller.is_file():
        return CheckResult(False, f"missing_controller={controller}")
    target = controller_run_target(controller)
    if target is None:
        return CheckResult(False, "literal_run_target=missing")
    if target.exists():
        return CheckResult(False, f"run_target_exists={target}")
    return CheckResult(True, f"fresh_run_target={target}")


CHECKS: dict[str, Callable[[dict, pathlib.Path], CheckResult]] = {
    "runtime_provenance": check_runtime_provenance,
    "source_worktrees_clean": check_source_worktrees_clean,
    "normalization_contract": check_normalization,
    "literal_source_closure": check_literal_closure,
    "module_load_order_closure": check_module_closure,
    "action_overlay_partition_contract": check_action_overlay_partition,
    "runtime_symbol_surface": check_runtime_symbol_surface,
    "checkpoint_integrity": check_checkpoint_integrity,
    "predecessor_identity_coverage": check_predecessor_identity_coverage,
    "short_runtime_probe": check_short_runtime_probe,
    "bounded_controller": check_bounded_controller,
    "fast_theorem_controller_contract": check_theorem_controller_contract,
    "resource_headroom": check_resource_headroom,
    "fresh_run_target": check_fresh_run_target,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", required=True)
    parser.add_argument("--controller", required=True, type=pathlib.Path)
    parser.add_argument("--ledger", type=pathlib.Path, default=DEFAULT_LEDGER)
    parser.add_argument("--receipt", type=pathlib.Path)
    args = parser.parse_args()

    started = time.monotonic()
    ledger_bytes = args.ledger.read_bytes()
    ledger = json.loads(ledger_bytes)
    if ledger.get("schema_version") != 1:
        print("status=1\nledger_error=unsupported_schema")
        return 1
    config = ledger.get("scopes", {}).get(args.scope)
    if config is None:
        print(f"status=1\nledger_error=unknown_scope:{args.scope}")
        return 1

    hazards = [item for item in ledger.get("hazards", []) if item.get("scope") == args.scope]
    ids = [item.get("id") for item in hazards]
    schema_errors = []
    if len(ids) != len(set(ids)):
        schema_errors.append("duplicate_hazard_id")
    required_fields = {
        "id",
        "scope",
        "classification",
        "first_evidence",
        "failure_mode",
        "root_cause",
        "check_id",
        "enforcement",
    }
    for hazard in hazards:
        missing = sorted(required_fields - set(hazard))
        if missing:
            schema_errors.append(f"{hazard.get('id','<unknown>')}:{','.join(missing)}")
        if hazard.get("check_id") not in CHECKS:
            schema_errors.append(f"{hazard.get('id','<unknown>')}:unknown_check")

    results: dict[str, CheckResult] = {}
    if not schema_errors:
        for check_id in sorted({item["check_id"] for item in hazards}):
            results[check_id] = CHECKS[check_id](config, args.controller.resolve())

    ok = not schema_errors and all(result.ok for result in results.values())
    lines = [
        "receipt_kind=development-long-run-hazard-preflight-v1",
        "release_evidence=false",
        f"status={0 if ok else 1}",
        f"scope={args.scope}",
        f"ledger_sha256={hashlib.sha256(ledger_bytes).hexdigest()}",
        f"controller={args.controller.resolve()}",
        f"controller_sha256={sha256(args.controller.resolve()) if args.controller.is_file() else '-'}",
        f"hazard_count={len(hazards)}",
        f"check_count={len(results)}",
        f"failed_check_count={sum(not result.ok for result in results.values())}",
        f"schema_error_count={len(schema_errors)}",
    ]
    for error in schema_errors:
        lines.append(f"schema_error={error}")
    for check_id in sorted(results):
        result = results[check_id]
        lines.append(f"check={check_id}\tstatus={0 if result.ok else 1}\t{result.detail}")
    lines.append(f"elapsed_seconds={time.monotonic() - started:.3f}")
    output = "\n".join(lines) + "\n"
    sys.stdout.write(output)
    if args.receipt is not None:
        if args.receipt.exists():
            print(f"refusing_existing_receipt={args.receipt}", file=sys.stderr)
            return 1
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(output, encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
