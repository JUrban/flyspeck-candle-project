#!/usr/bin/env python3
"""Exercise the exact S1 finalizer through its publication boundary.

This harness deliberately supplies no external authorization.  It replaces only
the authorization predicate while observing a single invocation, validates the
fully staged archive, and intercepts the final atomic rename.  The finalizer's
exception cleanup then removes the stage, so no S1 archive can be published.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile
import traceback
from typing import Any, Callable


FINALIZER = Path(__file__).with_name("finalize-top100-report.py").resolve()
SPEC = importlib.util.spec_from_file_location(
    "dry_run_exact_finalize_top100_report", FINALIZER,
)
FINALIZER_MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = FINALIZER_MODULE
SPEC.loader.exec_module(FINALIZER_MODULE)


class DryRunError(RuntimeError):
    """The dry-run contract was not satisfied."""


class PublicationBoundaryReached(BaseException):
    """Private sentinel used to make the finalizer clean its staged archive."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DryRunError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    metadata = path.stat(follow_symlinks=False)
    require(stat.S_ISREG(metadata.st_mode), f"not an ordinary file: {path}")
    return {"bytes": metadata.st_size, "sha256": sha256_file(path)}


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def git_head(root: Path) -> str:
    completed = subprocess.run(
        ["/usr/bin/git", "-C", str(root), "rev-parse", "HEAD"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "LANG": "C"},
    )
    return completed.stdout.strip()


def audit_stage(stage: Path, destination: Path) -> dict[str, Any]:
    require(not os.path.lexists(destination),
            "destination exists before publication boundary")
    bundle_path = stage / "bundle.json"
    checksums_path = stage / "SHA256SUMS"
    require(bundle_path.is_file() and not bundle_path.is_symlink(),
            "staged bundle.json is missing or not ordinary")
    require(checksums_path.is_file() and not checksums_path.is_symlink(),
            "staged SHA256SUMS is missing or not ordinary")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    require(bundle.get("schema") == 2 and
            bundle.get("kind") == "candle-great100-two-schema4-run-archive",
            "staged bundle has unexpected schema or kind")
    runs = bundle.get("runs")
    require(isinstance(runs, list) and len(runs) == 2 and
            [len(run.get("logs", [])) for run in runs] == [65, 65],
            "staged bundle does not retain two 65-record runs")
    replay = bundle.get("approval_replay")
    require(isinstance(replay, dict) and replay.get("candidate_count") == 130,
            "staged bundle does not record 130 reference candidates")
    comparison = bundle.get("comparison")
    require(isinstance(comparison, dict) and
            comparison.get("identical_and_independently_approved") is True,
            "staged bundle lacks the exact independent comparison result")

    checksum_rows = checksums_path.read_text(encoding="utf-8").splitlines()
    require(checksum_rows, "staged checksum inventory is empty")
    checked_paths: set[str] = set()
    for row in checksum_rows:
        expected, separator, relative = row.partition("  ")
        require(separator == "  " and len(expected) == 64 and
                all(character in "0123456789abcdef" for character in expected),
                "malformed staged checksum row")
        pure = PurePosixPath(relative)
        require(not pure.is_absolute() and relative == pure.as_posix() and
                all(part not in {"", ".", ".."} for part in pure.parts),
                f"unsafe staged checksum path: {relative!r}")
        require(relative not in checked_paths,
                f"duplicate staged checksum path: {relative}")
        checked_paths.add(relative)
        retained = stage / relative
        require(retained.is_file() and not retained.is_symlink(),
                f"staged checksum target is not ordinary: {relative}")
        require(sha256_file(retained) == expected,
                f"staged checksum mismatch: {relative}")
    require("bundle.json" in checked_paths,
            "staged checksum inventory omits bundle.json")
    require("SHA256SUMS" not in checked_paths,
            "staged checksum inventory improperly self-lists")
    return {
        "bundle": file_record(bundle_path),
        "checksums": file_record(checksums_path),
        "checksum_entry_count": len(checksum_rows),
        "retained_file_count": len(bundle.get("retained_files", {})),
        "run_log_counts": [65, 65],
        "reference_candidate_count": 130,
        "identical_and_independently_approved": True,
    }


def write_report(path: Path, value: dict[str, Any]) -> None:
    path = Path(os.path.abspath(path))
    require(not os.path.lexists(path), f"dry-run report already exists: {path}")
    require(path.parent.is_dir() and not path.parent.is_symlink(),
            f"dry-run report parent is not an ordinary directory: {path.parent}")
    temporary = path.parent / f".{path.name}.tmp-{os.getpid()}"
    require(not os.path.lexists(temporary),
            f"dry-run report temporary path already exists: {temporary}")
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
    )
    try:
        payload = canonical_json_bytes(value)
        view = memoryview(payload)
        while view:
            view = view[os.write(descriptor, view):]
        os.fsync(descriptor)
        os.fchmod(descriptor, 0o444)
    finally:
        os.close(descriptor)
    os.rename(temporary, path)
    parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def run_dry_finalization(
    reports: tuple[Path, Path], destination: Path,
) -> dict[str, Any]:
    destination = Path(os.path.abspath(destination))
    require(not os.path.lexists(destination),
            f"dry-run destination already exists: {destination}")
    parent = destination.parent
    require(parent.is_dir() and not parent.is_symlink(),
            f"dry-run destination parent is not ordinary: {parent}")
    stage_prefix = f".{destination.name}.tmp-"
    stages_before = {path.name for path in parent.glob(f"{stage_prefix}*")}
    project_root = FINALIZER.parent.parent
    state: dict[str, Any] = {
        "authorization_bypass_calls": 0,
        "validated_run_result_counts": [],
        "reference_projection_validations": 0,
        "publication_boundary_reached": False,
        "stage_audit": None,
    }
    marker = {
        "schema": 1,
        "kind": "candle-great100-finalizer-non-authorizing-dry-run",
        "claim": "This marker is not external authorization and cannot authorize S1 publication.",
        "promotion_allowed": False,
    }
    original_authorization: Callable[..., Any] = \
        FINALIZER_MODULE.validate_authorization
    original_validate_report: Callable[..., Any] = \
        FINALIZER_MODULE.validate_report_and_capture_logs
    original_validate_projection: Callable[..., Any] = \
        FINALIZER_MODULE.validate_candidate_identity_projection
    original_rename = FINALIZER_MODULE.os.rename

    with tempfile.TemporaryDirectory(
            prefix="candle-great100-nonauthorizing-dry-run-") as temporary_root:
        marker_path = Path(temporary_root) / "not-authorization.json"
        marker_path.write_bytes(canonical_json_bytes(marker))
        marker_digest = sha256_file(marker_path)

        def bypass_authorization(
            receipt: dict[str, Any], receipt_digest: str,
            receipt_snapshot: Any, *_arguments: Any, **_keywords: Any,
        ) -> None:
            require(receipt == marker,
                    "dry run received an unexpected authorization object")
            require(receipt_digest == marker_digest and
                    receipt_snapshot.identity.sha256 == marker_digest,
                    "dry-run marker identity mismatch")
            state["authorization_bypass_calls"] += 1

        def count_report(*arguments: Any, **keywords: Any) -> Any:
            validated = original_validate_report(*arguments, **keywords)
            state["validated_run_result_counts"].append(len(validated.results))
            return validated

        def count_projection(*arguments: Any, **keywords: Any) -> Any:
            result = original_validate_projection(*arguments, **keywords)
            state["reference_projection_validations"] += 1
            return result

        def intercept_publication(source: Any, target: Any, *args: Any,
                                  **kwargs: Any) -> Any:
            if (Path(os.path.abspath(target)) == destination and
                    Path(source).parent == parent and
                    Path(source).name.startswith(stage_prefix)):
                require(state["authorization_bypass_calls"] == 1,
                        "authorization bypass was not exercised exactly once")
                require(state["validated_run_result_counts"] == [65, 65],
                        "dry run did not validate both 65-record reports")
                require(state["reference_projection_validations"] == 130,
                        "dry run did not validate all 130 reference projections")
                state["stage_audit"] = audit_stage(Path(source), destination)
                state["publication_boundary_reached"] = True
                raise PublicationBoundaryReached()
            return original_rename(source, target, *args, **kwargs)

        FINALIZER_MODULE.validate_authorization = bypass_authorization
        FINALIZER_MODULE.validate_report_and_capture_logs = count_report
        FINALIZER_MODULE.validate_candidate_identity_projection = count_projection
        FINALIZER_MODULE.os.rename = intercept_publication
        try:
            FINALIZER_MODULE.archive(
                reports, destination, marker_path, marker_digest,
            )
            raise DryRunError("finalizer returned without reaching publication")
        except PublicationBoundaryReached:
            pass
        finally:
            FINALIZER_MODULE.validate_authorization = original_authorization
            FINALIZER_MODULE.validate_report_and_capture_logs = \
                original_validate_report
            FINALIZER_MODULE.validate_candidate_identity_projection = \
                original_validate_projection
            FINALIZER_MODULE.os.rename = original_rename

    require(state["publication_boundary_reached"],
            "finalizer did not reach the publication boundary")
    require(not os.path.lexists(destination),
            "dry run unexpectedly published a destination")
    stages_after = {path.name for path in parent.glob(f"{stage_prefix}*")}
    require(stages_after == stages_before,
            "dry-run finalizer left a staging directory behind")
    return {
        **state,
        "marker": marker,
        "finalizer_project_root": str(project_root),
        "finalizer_project_head": git_head(project_root),
        "finalizer": {"path": str(FINALIZER), **file_record(FINALIZER)},
        "report_schema_authority": {
            "schema_version": FINALIZER_MODULE.REPORT_SCHEMA_VERSION,
            "module": {
                "path": str(FINALIZER.with_name(
                    FINALIZER_MODULE.REPORT_SCHEMA_AUTHORITY_NAME,
                )),
                **file_record(FINALIZER.with_name(
                    FINALIZER_MODULE.REPORT_SCHEMA_AUTHORITY_NAME,
                )),
            },
            "definition": {
                "path": str(FINALIZER.with_name(
                    FINALIZER_MODULE.REPORT_SCHEMA_DEFINITION_NAME,
                )),
                **file_record(FINALIZER.with_name(
                    FINALIZER_MODULE.REPORT_SCHEMA_DEFINITION_NAME,
                )),
            },
        },
        "reports": [
            {"path": str(path), **file_record(path)} for path in reports
        ],
        "destination": str(destination),
        "destination_exists": False,
        "staging_cleanup_complete": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "validate real Great100 evidence through the exact finalizer's "
            "publication boundary without external authorization or publication"
        ),
    )
    parser.add_argument("report_one", type=Path)
    parser.add_argument("report_two", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--write-report", required=True, type=Path)
    arguments = parser.parse_args()
    started = utc_now()
    failure: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    try:
        result = run_dry_finalization(
            (Path(os.path.abspath(arguments.report_one)),
             Path(os.path.abspath(arguments.report_two))),
            Path(os.path.abspath(arguments.destination)),
        )
    except BaseException as error:
        failure = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
        }
    report = {
        "schema": 1,
        "kind": "candle-great100-finalizer-non-authorizing-dry-run-report",
        "claim": (
            "Development validation only: no external authorization was "
            "validated and no S1 archive was published."
        ),
        "started_utc": started,
        "completed_utc": utc_now(),
        "state": "passed" if failure is None else "failed",
        "promotion_allowed": False,
        "s1_finalized": False,
        "result": result,
        "failure": failure,
    }
    write_report(arguments.write_report, report)
    if failure is not None:
        raise SystemExit(
            f"dry-run finalization failed: {failure['type']}: "
            f"{failure['message']}"
        )
    print(f"non-authorizing dry run passed: {arguments.write_report}")


if __name__ == "__main__":
    main()
