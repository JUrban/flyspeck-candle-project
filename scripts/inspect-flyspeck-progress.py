#!/usr/bin/env python3
"""Classify progress in a live or completed direct-Flyspeck Candle log.

This is a read-only operator aid.  Its output is diagnostic and never grants
action, S2, S3, qualification, or release credit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Iterable


ACTION_RE = re.compile(r"CANDLE_FLYSPECK_STRATUM_ACTION_OK\s+\S+\s+(\d+)\b")
ARCHIVE_RE = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")
FILE_RE = re.compile(r"^Verifying\s+(.+[.]dat)\s*$")
CERTIFICATE_RE = re.compile(r"^\((\d+)\)\s+(\d+)/(\d+)\s*$")
TERMINALS_RE = re.compile(r"terminals\s*=\s*(\d+)\s*:\s*(.*)$")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
INTERESTING = (
    b"CANDLE_FLYSPECK_",
    b"Verifying",
    b"Linear programs verified",
    b"Constructing the final linear programming result",
    b"final linear programming result is constructed",
    b"terminals =",
    b"Exception",
    b"Error in included file",
)


def _lines(stream: Iterable[bytes]) -> Iterable[str]:
    for raw_line in stream:
        # Decoded certificate values can occupy very large REPL lines.  They
        # have no progress information, so avoid decoding them at all.
        if len(raw_line) > 256 * 1024 and not any(
            marker in raw_line for marker in INTERESTING
        ):
            continue
        yield ANSI_RE.sub("", raw_line.decode("utf-8", errors="replace")).strip()


def inspect_lines(lines: Iterable[str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "flyspeck-progress-v1",
        "claim": "diagnostic only; not action, S2, S3, or release evidence",
        "phase": "unknown",
    }
    for line in lines:
        if not line:
            continue

        action = ACTION_RE.search(line)
        if action:
            result["last_committed_action"] = int(action.group(1))
            result["phase"] = "source_actions"

        archive = ARCHIVE_RE.fullmatch(line)
        if archive:
            result["archive_completed"] = int(archive.group(1))
            result["archive_total"] = int(archive.group(2))
            result["phase"] = "good_list_archive"

        if "CANDLE_FLYSPECK_V220_POST170_CHECKPOINT_READY" in line:
            result["phase"] = "post170_checkpoint_ready"
        if "CANDLE_FLYSPECK_V220_PRE184_CHECKPOINT_READY" in line:
            result["phase"] = "pre184_checkpoint_ready"
        if "Verifying linear programs" in line:
            result["phase"] = "lp_verification"

        verified_file = FILE_RE.fullmatch(line)
        if verified_file:
            path = Path(verified_file.group(1))
            result["lp_file"] = path.name
            result["phase"] = "lp_file"

        certificate = CERTIFICATE_RE.fullmatch(line)
        if certificate:
            result["lp_files_remaining_including_current"] = int(
                certificate.group(1)
            )
            result["lp_certificate_index"] = int(certificate.group(2))
            result["lp_certificate_total_in_file"] = int(certificate.group(3))
            result["phase"] = "lp_certificate"

        terminals = TERMINALS_RE.search(line)
        if terminals:
            result["terminal_total"] = int(terminals.group(1))
            result["terminal_completed"] = len(
                re.findall(r"\b\d+\b", terminals.group(2))
            )
            result["phase"] = "lp_terminal_proof"

        if "_DECODE_BEGIN" in line:
            result["phase"] = "focused_decode"
        if "_DECODED" in line:
            result["phase"] = "focused_decoded"
        if "_VERIFY_BEGIN" in line:
            result["phase"] = "focused_verification"
        if "_CERTIFICATE_PASS" in line:
            result["phase"] = "focused_certificate_pass"
        if "Linear programs verified" in line:
            result["phase"] = "lp_all_certificates_verified"
        if "Constructing the final linear programming result" in line:
            result["phase"] = "lp_final_assembly"
        if "final linear programming result is constructed" in line:
            result["phase"] = "lp_final_theorem_constructed"

        if line.startswith("Exception") or "Error in included file" in line:
            result["phase"] = "failure"
            result["last_error"] = line

    return result


def inspect_log(path: Path) -> dict[str, Any]:
    stat = path.stat()
    with path.open("rb") as stream:
        result = inspect_lines(_lines(stream))
    result["log"] = str(path.resolve())
    result["log_bytes"] = stat.st_size
    result["log_mtime_ns"] = stat.st_mtime_ns
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(json.dumps(inspect_log(args.log), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
