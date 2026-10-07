#!/usr/bin/env python3
"""Compare matched Taylor-bound stages from the specialized and fixed lanes."""

import argparse
import json
from fractions import Fraction
from pathlib import Path


SPECIALIZED_PREFIX = "CANDLE_NL_NATIVE_SPECIALIZED_STAGE "
FIXED_PREFIX = "CANDLE_NL_NATIVE_FIXED_SCALE_STAGE "
SCALARS = ("center", "linear", "quadratic", "recomposed_upper", "upper")


def parse_scalar(value: str, *, upper: bool = False) -> Fraction:
    if upper:
        value = value.split(":", 1)[1]
    return Fraction(value)


def read_stages(path: Path, prefix: str) -> dict[int, dict[str, Fraction]]:
    stages: dict[int, dict[str, Fraction]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith(prefix):
            continue
        fields = dict(token.split("=", 1) for token in line.split()[1:])
        index = int(fields["index"])
        if index in stages:
            raise ValueError(f"duplicate stage index {index} in {path}")
        stages[index] = {
            "center": parse_scalar(fields["center"], upper=True),
            "linear": parse_scalar(fields["linear"]),
            "quadratic": parse_scalar(fields["quadratic"]),
            "recomposed_upper": parse_scalar(fields["recomposed_upper"]),
            "upper": parse_scalar(fields["upper"]),
            "accept": Fraction(int(fields["accept"])),
        }
    if not stages:
        raise ValueError(f"no stage records in {path}")
    return stages


def as_float(value: Fraction) -> float:
    return float(value.numerator) / float(value.denominator)


def summarize(candidate: dict[int, dict[str, Fraction]],
              reference: dict[int, dict[str, Fraction]]) -> dict:
    if candidate.keys() != reference.keys():
        raise ValueError("stage index sets differ")
    indices = sorted(reference)
    result = {
        "boxes": len(indices),
        "accepted": sum(int(candidate[index]["accept"]) for index in indices),
        "reference_accepted": sum(
            int(reference[index]["accept"]) for index in indices
        ),
        "components": {},
    }
    for component in SCALARS:
        candidate_values = [candidate[index][component] for index in indices]
        reference_values = [reference[index][component] for index in indices]
        differences = [
            candidate_value - reference_value
            for candidate_value, reference_value
            in zip(candidate_values, reference_values)
        ]
        ratios = [
            candidate_value / reference_value
            for candidate_value, reference_value
            in zip(candidate_values, reference_values)
            if reference_value != 0
        ]
        result["components"][component] = {
            "candidate_mean": as_float(sum(candidate_values) / len(indices)),
            "reference_mean": as_float(sum(reference_values) / len(indices)),
            "difference_mean": as_float(sum(differences) / len(indices)),
            "difference_min": as_float(min(differences)),
            "difference_max": as_float(max(differences)),
            "ratio_mean": as_float(sum(ratios) / len(ratios)),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("specialized")
    parser.add_argument("generic")
    parser.add_argument("historical")
    args = parser.parse_args()

    specialized = read_stages(Path(args.specialized), SPECIALIZED_PREFIX)
    generic = read_stages(Path(args.generic), FIXED_PREFIX)
    historical = read_stages(Path(args.historical), FIXED_PREFIX)
    output = {
        "specialized_reference": str(Path(args.specialized).resolve()),
        "generic_vs_specialized": summarize(generic, specialized),
        "historical_vs_specialized": summarize(historical, specialized),
        "historical_vs_generic": summarize(historical, generic),
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
