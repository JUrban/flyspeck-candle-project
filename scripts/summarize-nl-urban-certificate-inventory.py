#!/usr/bin/env python3
"""Parse the archived Flyspeck nonlinear verifier certificate census.

The archived Urban outputs contain one completed verifier record for almost
every serialized nonlinear parameter.  Each production record reports the
certificate constructor counts and its historical HOL Light verification
time.  Startup self-test statistics occur before the first ``Verifying:``
line and are deliberately ignored.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import NamedTuple


VERIFY_RE = re.compile(
    r"^Verifying: ([0-9]+):\s+(?:[0-9]+,)?\((.*),([0-9]+)\)$"
)
PASS_RE = re.compile(r"^pass = ([0-9]+) \(pass_raw = ([0-9]+)\)$")
MONO_RE = re.compile(r"^mono = ([0-9]+)$")
GLUE_RE = re.compile(r"^glue = ([0-9]+) \(glue_convex = ([0-9]+)\)$")
PASS_MONO_RE = re.compile(r"^pass_mono = ([0-9]+)$")
TIME_RE = re.compile(
    r"^Time\s+(?:[0-9]+,)?\((.*),([0-9]+)\): ([0-9]+(?:\.[0-9]+)?)$"
)


class CertificateRecord(NamedTuple):
    global_index: int
    source_id: str
    leaf_index: int
    passes: int
    pass_raw: int
    mono: int
    glue: int
    glue_convex: int
    pass_mono: int
    historical_total_seconds: float

    @property
    def numerical_terminals(self) -> int:
        return self.passes + self.pass_mono

    @property
    def topology_constructors(self) -> int:
        return self.passes + self.pass_mono + self.mono + self.glue


def quantiles(values: list[int | float]) -> dict[str, int | float]:
    if not values:
        return {}
    ordered = sorted(values)
    result: dict[str, int | float] = {}
    for name, numerator in (
        ("min", 0),
        ("p10", 10),
        ("p25", 25),
        ("p50", 50),
        ("p75", 75),
        ("p90", 90),
        ("p95", 95),
        ("p99", 99),
        ("max", 100),
    ):
        index = ((len(ordered) - 1) * numerator) // 100
        result[name] = ordered[index]
    return result


def _require_complete(active: dict, path: Path, line_number: int) -> None:
    identity = {"global_index", "source_id", "leaf_index"}
    statistics = {
        "passes",
        "pass_raw",
        "mono",
        "glue",
        "glue_convex",
        "pass_mono",
    }
    missing_identity = sorted(identity - set(active))
    if missing_identity:
        raise ValueError(
            f"incomplete verifier identity at {path}:{line_number}: "
            f"{missing_identity}"
        )
    present_statistics = statistics & set(active)
    if not present_statistics:
        # A closed constant inequality bypasses certificate construction in
        # verify_ineq0 and therefore emits no statistics.  Its certificate
        # constructor counts are exactly the verifier's dummy all-zero stats.
        active.update({name: 0 for name in statistics})
        return
    missing = sorted(statistics - set(active))
    if missing:
        raise ValueError(
            f"incomplete verifier record at {path}:{line_number}: {missing}"
        )


def read_records(root: Path) -> list[CertificateRecord]:
    paths = sorted(path for path in root.rglob("stdout") if path.is_file())
    if not paths:
        raise ValueError(f"no archived stdout files found under {root}")
    records: list[CertificateRecord] = []
    for path in paths:
        active: dict | None = None
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            match = VERIFY_RE.match(line)
            if match is not None:
                if active is not None:
                    raise ValueError(
                        f"nested verifier record at {path}:{line_number}"
                    )
                global_index, source_id, leaf_index = match.groups()
                active = {
                    "global_index": int(global_index),
                    "source_id": source_id,
                    "leaf_index": int(leaf_index),
                }
                continue
            if active is None:
                continue
            match = PASS_RE.match(line)
            if match is not None:
                active["passes"], active["pass_raw"] = (
                    int(value) for value in match.groups()
                )
                continue
            match = MONO_RE.match(line)
            if match is not None:
                active["mono"] = int(match.group(1))
                continue
            match = GLUE_RE.match(line)
            if match is not None:
                active["glue"], active["glue_convex"] = (
                    int(value) for value in match.groups()
                )
                continue
            match = PASS_MONO_RE.match(line)
            if match is not None:
                active["pass_mono"] = int(match.group(1))
                continue
            match = TIME_RE.match(line)
            if match is None:
                continue
            source_id, leaf_index, elapsed = match.groups()
            if (
                source_id != active["source_id"]
                or int(leaf_index) != active["leaf_index"]
            ):
                raise ValueError(
                    f"verifier identity drift at {path}:{line_number}"
                )
            _require_complete(active, path, line_number)
            records.append(
                CertificateRecord(
                    **active, historical_total_seconds=float(elapsed)
                )
            )
            active = None
        if active is not None:
            raise ValueError(f"unterminated verifier record in {path}")
    if not records:
        raise ValueError("no archived verifier records found")
    global_indices = [record.global_index for record in records]
    identities = [(record.source_id, record.leaf_index) for record in records]
    if len(set(global_indices)) != len(global_indices):
        raise ValueError("duplicate archived global verifier index")
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate archived source/leaf identity")
    return records


def summarize(records: list[CertificateRecord]) -> dict:
    return {
        "records": len(records),
        "source_ids": len({record.source_id for record in records}),
        "global_index_min": min(record.global_index for record in records),
        "global_index_max": max(record.global_index for record in records),
        "numerical_terminals": sum(
            record.numerical_terminals for record in records
        ),
        "topology_constructors": sum(
            record.topology_constructors for record in records
        ),
        "mono_constructors": sum(record.mono for record in records),
        "historical_total_seconds": sum(
            record.historical_total_seconds for record in records
        ),
        "numerical_terminal_quantiles": quantiles(
            [record.numerical_terminals for record in records]
        ),
        "topology_constructor_quantiles": quantiles(
            [record.topology_constructors for record in records]
        ),
        "historical_total_second_quantiles": quantiles(
            [record.historical_total_seconds for record in records]
        ),
        "scope_note": (
            "Counts and times come from the archived native HOL Light verifier; "
            "they are sampling coordinates, not current Candle measurements."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("urban_output", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(read_records(args.urban_output)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
