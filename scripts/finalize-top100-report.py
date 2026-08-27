#!/usr/bin/env python3
"""Validate and archive a successful Candle Great 100 regression report."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_name(name: str) -> str:
    return name.replace("/", "_").replace("-", "_")


def validate(report: dict[str, object]) -> list[dict[str, object]]:
    if report.get("schema") != 1 or report.get("suite") != "top100":
        raise ValueError("not a schema-1 top100 report")
    if report.get("test_count") != 65:
        raise ValueError("Great 100 report must contain 65 test entries")
    counts = report.get("counts")
    if counts != {"PASS": 65, "FAIL": 0, "TIMEOUT": 0}:
        raise ValueError(f"Great 100 suite did not pass completely: {counts}")
    if report.get("candle_git_status") != []:
        raise ValueError("Candle worktree was not clean during the suite")
    results = report.get("results")
    if not isinstance(results, list) or len(results) != 65:
        raise ValueError("malformed Great 100 result table")
    if any(result.get("status") != "PASS" for result in results):
        raise ValueError("non-passing result in Great 100 table")
    if len({result.get("name") for result in results}) != 65:
        raise ValueError("duplicate Great 100 result name")
    return results


def archive(source_report: Path, destination: Path) -> None:
    report = json.loads(source_report.read_text(encoding="utf-8"))
    results = validate(report)
    source_logs = [Path(str(result["log_path"])) for result in results]
    missing = [str(path) for path in source_logs if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing regression logs: {', '.join(missing)}")
    if destination.exists():
        raise FileExistsError(f"archive destination already exists: {destination}")

    log_dir = destination / "logs"
    log_dir.mkdir(parents=True)
    checksum_rows: list[tuple[str, str]] = []
    for index, (result, source_log) in enumerate(zip(results, source_logs), 1):
        relative_log = Path("logs") / f"{index:02d}-{safe_name(str(result['name']))}.log"
        archived_log = destination / relative_log
        shutil.copyfile(source_log, archived_log)
        log_sha = sha256(archived_log)
        result["source_log_path"] = result["log_path"]
        result["log_path"] = str(relative_log)
        result["log_sha256"] = log_sha
        checksum_rows.append((log_sha, str(relative_log)))

    report["archive_schema"] = 1
    report["source_report_sha256"] = sha256(source_report)
    archived_report = destination / "report.json"
    archived_report.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    checksum_rows.append((sha256(archived_report), "report.json"))
    checksum_rows.sort(key=lambda row: row[1])
    (destination / "SHA256SUMS").write_text(
        "".join(f"{digest}  {path}\n" for digest, path in checksum_rows),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    archive(args.report.resolve(), args.destination.resolve())


if __name__ == "__main__":
    main()
