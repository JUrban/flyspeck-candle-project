#!/usr/bin/env python3
"""Self-test for Great 100 report validation and archival."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from copy import deepcopy
from pathlib import Path


SCRIPT = Path(__file__).with_name("finalize-top100-report.py")
SPEC = importlib.util.spec_from_file_location("finalize_top100_report", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="candle-top100-finalizer.") as temp:
        root = Path(temp)
        results = []
        for index in range(65):
            log = root / f"source-{index}.log"
            log.write_text(f"PASS {index}\n", encoding="utf-8")
            results.append(
                {
                    "name": f"100/test-{index}",
                    "status": "PASS",
                    "log_path": str(log),
                }
            )
        report = {
            "schema": 1,
            "suite": "top100",
            "test_count": 65,
            "counts": {"PASS": 65, "FAIL": 0, "TIMEOUT": 0},
            "candle_git_status": [],
            "results": results,
        }
        report_path = root / "source-report.json"
        report_path.write_text(json.dumps(report), encoding="utf-8")
        failed_report = deepcopy(report)
        failed_report["counts"] = {"PASS": 64, "FAIL": 1, "TIMEOUT": 0}
        try:
            MODULE.validate(failed_report)
        except ValueError:
            pass
        else:
            raise AssertionError("incomplete Great 100 report was accepted")
        destination = root / "archive"
        MODULE.archive(report_path, destination)
        archived = json.loads(
            (destination / "report.json").read_text(encoding="utf-8"))
        assert archived["archive_schema"] == 1
        assert len(archived["results"]) == 65
        assert all(result["log_sha256"] for result in archived["results"])
        assert len((destination / "SHA256SUMS").read_text().splitlines()) == 66
    print("PASS: Great 100 report finalizer")


if __name__ == "__main__":
    main()
