#!/usr/bin/env python3
"""Summarize diagnostic native/reflected bounds on matched NL boxes."""

from __future__ import annotations

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import re


SUMMARY = re.compile(
    r"^CANDLE_NL_NATIVE_BOX_SUMMARY mode=(?P<mode>\S+) boxes=(?P<boxes>\d+) "
    r"accepted=(?P<accepted>\d+) unstable=(?P<unstable>\d+) "
    r"wall_seconds=(?P<wall>\S+) checksum=(?P<checksum>\S+)$"
)
RESULT = re.compile(
    r"^CANDLE_NL_NATIVE_BOX_RESULT index=(?P<index>\d+) "
    r"specialized_upper=(?P<specialized>\S+) generic_upper=(?P<generic>\S+) "
    r"generic_minus_specialized=(?P<delta>\S+) "
    r"specialized_accept=(?P<specialized_accept>[01]) "
    r"generic_accept=(?P<generic_accept>[01])$"
)


def quantiles(values: list[float]) -> dict[str, float]:
    ordered = sorted(value for value in values if math.isfinite(value))
    if not ordered:
        return {}

    def at(fraction: float) -> float:
        return ordered[round(fraction * (len(ordered) - 1))]

    return {
        "minimum": ordered[0],
        "p10": at(0.10),
        "median": at(0.50),
        "p90": at(0.90),
        "maximum": ordered[-1],
    }


def load_native(path: Path) -> tuple[dict[str, object], dict[int, dict[str, float | bool]]]:
    summaries: dict[str, object] = {}
    rows: dict[int, dict[str, float | bool]] = {}
    for line in path.read_text().splitlines():
        match = SUMMARY.match(line)
        if match:
            summaries[match["mode"]] = {
                "boxes": int(match["boxes"]),
                "accepted": int(match["accepted"]),
                "unstable": int(match["unstable"]),
                "wall_seconds": float(match["wall"]),
                "checksum": float(match["checksum"]),
            }
            continue
        match = RESULT.match(line)
        if match:
            index = int(match["index"])
            if index in rows:
                raise ValueError(f"duplicate native index: {index}")
            rows[index] = {
                "specialized_upper": float(match["specialized"]),
                "generic_upper": float(match["generic"]),
                "generic_minus_specialized": float(match["delta"]),
                "specialized_accept": match["specialized_accept"] == "1",
                "generic_accept": match["generic_accept"] == "1",
            }
    if not summaries or not rows:
        raise ValueError(f"missing native results in {path}")
    return summaries, rows


def load_reflected(path: Path) -> dict[int, Fraction]:
    rows: dict[int, Fraction] = {}
    for line in path.read_text().splitlines():
        index_text, bound_text = line.split("\t")
        index = int(index_text)
        if index in rows:
            raise ValueError(f"duplicate reflected index: {index}")
        rows[index] = Fraction(bound_text)
    if not rows:
        raise ValueError(f"empty reflected results: {path}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--reflected", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    summaries, native = load_native(args.native)
    result: dict[str, object] = {
        "schema": "candle-nl-certificate-box-comparison-v1",
        "status": "DEVELOPMENT_NON_RELEASE",
        "native_summaries": summaries,
        "native_box_count": len(native),
        "native_distributions": {
            key: quantiles([float(row[key]) for row in native.values()])
            for key in (
                "specialized_upper",
                "generic_upper",
                "generic_minus_specialized",
            )
        },
    }

    if args.reflected is not None:
        reflected = load_reflected(args.reflected)
        common = sorted(set(native) & set(reflected))
        if not common:
            raise ValueError("native/reflected datasets have no common indices")
        reflected_values = [float(reflected[index]) for index in common]
        result["matched_reflected"] = {
            "box_count": len(common),
            "accepted": sum(value < 0 for value in reflected_values),
            "upper": quantiles(reflected_values),
            "reflected_minus_specialized": quantiles([
                float(reflected[index]) - float(native[index]["specialized_upper"])
                for index in common
            ]),
            "reflected_minus_generic": quantiles([
                float(reflected[index]) - float(native[index]["generic_upper"])
                for index in common
            ]),
        }

    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    temporary.replace(args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
