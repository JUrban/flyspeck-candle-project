#!/usr/bin/env python3
"""Load the exact production-kernel dependency closure without Holmake."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import pathlib
import resource
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
AUDIT_PATH = PROJECT / "scripts/audit-fast-nl-tag10-kernel-loader-closure.py"
RUN = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v690-fast-nl-tag10-kernel-loader-dev-001"
)
CLOSURE_RECEIPT = RUN / "CLOSURE-AUDIT.receipt"
RELOCATION_RECEIPT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v687-fast-nl-tag10-parent-cache-relocation-dev-001/"
    "PARENT-CACHE-RELOCATION.receipt"
)
HOL = pathlib.Path("/project/worktrees/HOL-cakeml-dopen-v13/bin/hol")
HOL_STATE = pathlib.Path("/project/worktrees/HOL-cakeml-dopen-v13/bin/hol.state")
MARKER = "FAST_NL_TAG10_KERNEL_DEPENDENCY_LOAD_OK"
TIMEOUT_SECONDS = 300


class ProbeFailure(Exception):
    pass


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_audit_module():
    spec = importlib.util.spec_from_file_location("tag10_loader_audit", AUDIT_PATH)
    if spec is None or spec.loader is None:
        raise ProbeFailure("audit_module_spec")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_receipt(path: pathlib.Path, markers: tuple[str, ...]) -> None:
    if not path.is_file() or path.is_symlink():
        raise ProbeFailure(f"receipt_missing:{path}")
    lines = set(path.read_text(encoding="utf-8").splitlines())
    for marker in markers:
        if marker not in lines:
            raise ProbeFailure(f"receipt_marker:{path}:{marker}")


def snapshot(paths: list[pathlib.Path]) -> dict[str, tuple[int, int, int]]:
    result: dict[str, tuple[int, int, int]] = {}
    for root in paths:
        if not root.is_dir():
            raise ProbeFailure(f"snapshot_root_missing:{root}")
        for path in root.iterdir():
            if not path.is_file() or path.is_symlink():
                continue
            stat = path.stat()
            result[str(path)] = (stat.st_size, stat.st_mtime_ns, stat.st_mode)
    return result


def run_loader(command: list[str], log: pathlib.Path) -> tuple[int, float, int]:
    before_rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    started = time.monotonic()
    with log.open("wb") as output:
        process = subprocess.Popen(
            command,
            cwd=str(AUDIT.PROVER),
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            returncode = process.wait(timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            returncode = 124
    elapsed = time.monotonic() - started
    after_rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return returncode, elapsed, max(before_rss, after_rss)


AUDIT = load_audit_module()


def main() -> int:
    receipt = RUN / "LOADER-PROBE.receipt"
    log = RUN / "loader.log"
    root_base = RUN / "kernel-dependency-loader"
    synthetic_objects = RUN / ".hol/objs"
    interface = synthetic_objects / "kernel-dependency-loader.ui"
    manifest = synthetic_objects / "kernel-dependency-loader.uo"
    marker_source = RUN / "kernel-dependency-loader-marker.sml"
    try:
        if any(
            path.exists()
            for path in (receipt, log, interface, manifest, marker_source)
        ):
            raise ProbeFailure("probe_output_exists")
        require_receipt(
            CLOSURE_RECEIPT,
            (
                "status=0",
                "direct_module_count=113",
                "scratch_manifest_reference_count=0",
                "missing_object_count=0",
                "missing_interface_count=0",
                "missing_generated_theory_artifact_count=0",
            ),
        )
        require_receipt(
            RELOCATION_RECEIPT,
            (
                "status=0",
                "relocated_theory_count=34",
                "relocated_manifest_count=68",
                "remaining_scratch_manifest_count=0",
                "proof_data_changed=false",
            ),
        )
        if not HOL.is_file() or not HOL_STATE.is_file():
            raise ProbeFailure("hol_runtime_missing")
        synthetic_objects.mkdir(parents=True)

        modules = AUDIT.direct_modules()
        hints = AUDIT.dependency_hints()
        roots = [AUDIT.choose_direct(module, hints) for module in modules]
        if len(roots) != 113 or len(set(roots)) != 113:
            raise ProbeFailure(f"root_inventory:{len(roots)}:{len(set(roots))}")
        if any(AUDIT.SCRATCH_COMPUTE in path.parents for path in roots):
            raise ProbeFailure("scratch_root_selected")

        marker_source.write_text(
            f'val _ = print "{MARKER}\\n";\n', encoding="utf-8"
        )
        # Poly's object loader requires the interface manifest even when the
        # synthetic root exports no interface names.  Holmake emits the same
        # empty .ui file for ordinary theory scripts.
        interface.write_text("", encoding="utf-8")
        manifest.write_text(
            "\n".join(str(path) for path in roots)
            + "\n"
            + str(marker_source)
            + "\n",
            encoding="utf-8",
        )

        snapshot_roots = sorted(
            set(AUDIT.CAKEML.rglob(".hol/objs"))
            | {AUDIT.HOLDIR / "sigobj"},
            key=str,
        )
        before = snapshot(snapshot_roots)
        command = [
            str(HOL),
            "--gcthreads=1",
            "--maxheap",
            "32768",
            "run",
            f"--holstate={HOL_STATE}",
            str(root_base),
        ]
        returncode, elapsed, peak_rss_kib = run_loader(command, log)
        after = snapshot(snapshot_roots)
        changed = sorted(
            set(before) ^ set(after)
            | {path for path in set(before) & set(after) if before[path] != after[path]}
        )
        log_text = log.read_text(encoding="utf-8", errors="replace")
        marker_count = log_text.count(MARKER)
        if returncode != 0:
            raise ProbeFailure(f"loader_status:{returncode}")
        if marker_count != 1:
            raise ProbeFailure(f"loader_marker_count:{marker_count}")
        if changed:
            raise ProbeFailure(f"object_tree_changed:{changed[0]}")

        receipt.write_text(
            "\n".join(
                (
                    "receipt_kind=development-fast-nl-tag10-kernel-loader-v1",
                    "release_evidence=false",
                    "status=0",
                    f"candidate_head={AUDIT.EXPECTED_HEAD}",
                    f"direct_root_count={len(roots)}",
                    f"snapshot_root_count={len(snapshot_roots)}",
                    f"snapshot_file_count={len(before)}",
                    "scratch_root_count=0",
                    "object_tree_changed_count=0",
                    f"loader_marker={MARKER}",
                    f"loader_marker_count={marker_count}",
                    f"loader_exit_status={returncode}",
                    f"loader_elapsed_seconds={elapsed:.3f}",
                    f"loader_peak_rss_kib={peak_rss_kib}",
                    f"loader_timeout_seconds={TIMEOUT_SECONDS}",
                    f"loader_interface_sha256={sha256(interface)}",
                    f"loader_manifest_sha256={sha256(manifest)}",
                    f"loader_log_sha256={sha256(log)}",
                    f"closure_receipt_sha256={sha256(CLOSURE_RECEIPT)}",
                    f"relocation_receipt_sha256={sha256(RELOCATION_RECEIPT)}",
                    f"hol_sha256={sha256(HOL)}",
                    f"hol_state_sha256={sha256(HOL_STATE)}",
                    "completed_utc="
                    + datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "",
                )
            ),
            encoding="utf-8",
        )
        print(receipt.read_text(encoding="utf-8"), end="")
        return 0
    except (OSError, ProbeFailure, subprocess.SubprocessError) as error:
        receipt.write_text(
            "\n".join(
                (
                    "receipt_kind=development-fast-nl-tag10-kernel-loader-v1",
                    "release_evidence=false",
                    "status=1",
                    f"error={error}",
                    "completed_utc="
                    + datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "",
                )
            ),
            encoding="utf-8",
        )
        print(receipt.read_text(encoding="utf-8"), end="")
        return 1


if __name__ == "__main__":
    sys.exit(main())
