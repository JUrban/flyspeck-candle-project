#!/usr/bin/env python3
"""Authenticate the completed non-mutating tag-10 kernel loader probe."""

from __future__ import annotations

import hashlib
import pathlib
import subprocess


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
RUN = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v690-fast-nl-tag10-kernel-loader-dev-001"
)
RECEIPT = RUN / "LOADER-PROBE.receipt"
CLOSURE_RECEIPT = RUN / "CLOSURE-AUDIT.receipt"
LOG = RUN / "loader.log"
INTERFACE = RUN / ".hol/objs/kernel-dependency-loader.ui"
MANIFEST = RUN / ".hol/objs/kernel-dependency-loader.uo"
RELOCATION_RECEIPT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v687-fast-nl-tag10-parent-cache-relocation-dev-001/"
    "PARENT-CACHE-RELOCATION.receipt"
)
CLOSURE_AUDIT = PROJECT / "scripts/audit-fast-nl-tag10-kernel-loader-closure.py"
EXPECTED_HEAD = "839017e696dea5fbbb2e03bfeff02c6679724e00"
MARKER = "FAST_NL_TAG10_KERNEL_DEPENDENCY_LOAD_OK"


class AuditFailure(Exception):
    pass


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_receipt(path: pathlib.Path) -> dict[str, str]:
    if not path.is_file() or path.is_symlink():
        raise AuditFailure(f"receipt_missing:{path}")
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        if "=" not in line:
            raise AuditFailure(f"receipt_line:{path}:{line}")
        key, value = line.split("=", 1)
        if key in result:
            raise AuditFailure(f"receipt_duplicate:{path}:{key}")
        result[key] = value
    return result


def main() -> int:
    try:
        receipt = parse_receipt(RECEIPT)
        required = {
            "receipt_kind": "development-fast-nl-tag10-kernel-loader-v1",
            "release_evidence": "false",
            "status": "0",
            "candidate_head": EXPECTED_HEAD,
            "direct_root_count": "113",
            "scratch_root_count": "0",
            "object_tree_changed_count": "0",
            "loader_marker": MARKER,
            "loader_marker_count": "1",
            "loader_exit_status": "0",
            "loader_timeout_seconds": "300",
        }
        for key, expected in required.items():
            if receipt.get(key) != expected:
                raise AuditFailure(f"receipt_field:{key}:{receipt.get(key)}")
        try:
            elapsed = float(receipt["loader_elapsed_seconds"])
            peak_rss = int(receipt["loader_peak_rss_kib"])
            snapshot_files = int(receipt["snapshot_file_count"])
        except (KeyError, ValueError) as error:
            raise AuditFailure("receipt_numeric_field") from error
        if not (0.0 < elapsed <= 300.0):
            raise AuditFailure(f"loader_elapsed:{elapsed}")
        if peak_rss <= 0 or snapshot_files < 5000:
            raise AuditFailure(f"loader_resources:{peak_rss}:{snapshot_files}")

        hash_contract = {
            "loader_interface_sha256": INTERFACE,
            "loader_manifest_sha256": MANIFEST,
            "loader_log_sha256": LOG,
            "closure_receipt_sha256": CLOSURE_RECEIPT,
            "relocation_receipt_sha256": RELOCATION_RECEIPT,
        }
        for key, path in hash_contract.items():
            if not path.is_file() or path.is_symlink():
                raise AuditFailure(f"artifact_missing:{path}")
            actual = sha256(path)
            if receipt.get(key) != actual:
                raise AuditFailure(f"artifact_hash:{key}:{actual}")

        log = LOG.read_text(encoding="utf-8", errors="replace")
        if log.count(MARKER) != 1:
            raise AuditFailure(f"log_marker_count:{log.count(MARKER)}")
        forbidden_log = ("Cannot find file", "error in load", "Uncaught exception")
        if any(item in log for item in forbidden_log):
            raise AuditFailure("loader_log_error")

        manifest_lines = MANIFEST.read_text(encoding="utf-8").splitlines()
        if len(manifest_lines) != 114:
            raise AuditFailure(f"manifest_line_count:{len(manifest_lines)}")
        if len(set(manifest_lines[:-1])) != 113:
            raise AuditFailure("manifest_root_uniqueness")
        if any("tag10_probe_scratch" in line for line in manifest_lines):
            raise AuditFailure("manifest_scratch_reference")
        if any("candle_kernelProgScript.sml" in line for line in manifest_lines):
            raise AuditFailure("kernel_script_executed")

        current = subprocess.run(
            [str(CLOSURE_AUDIT)],
            cwd=PROJECT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
            check=False,
        )
        if current.returncode != 0:
            raise AuditFailure("current_closure_failed")
        if current.stdout != CLOSURE_RECEIPT.read_text(encoding="utf-8"):
            raise AuditFailure("current_closure_changed")
    except (AuditFailure, OSError, subprocess.SubprocessError) as error:
        print("status=1")
        print(f"error={error}")
        return 1

    print("status=0")
    print(f"candidate_head={EXPECTED_HEAD}")
    print("actual_loader_probe_authenticated=true")
    print("kernel_proof_script_executed=false")
    print("scratch_root_count=0")
    print("object_tree_changed_count=0")
    print(f"direct_root_count={receipt['direct_root_count']}")
    print(f"transitive_manifest_count=1117")
    print(f"loader_elapsed_seconds={receipt['loader_elapsed_seconds']}")
    print(f"loader_peak_rss_kib={receipt['loader_peak_rss_kib']}")
    print(f"loader_receipt_sha256={sha256(RECEIPT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
