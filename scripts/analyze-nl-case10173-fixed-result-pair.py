#!/usr/bin/env python3
"""Compare two DEVELOPMENT/NON-RELEASE fixed-scale result streams."""

import argparse
from fractions import Fraction
import json
import statistics


MARKER = "CANDLE_NL_NATIVE_FIXED_SCALE_RESULT "


def read_results(path):
    results = {}
    with open(path, encoding="utf-8") as source:
        for line in source:
            if not line.startswith(MARKER):
                continue
            fields = dict(item.split("=", 1) for item in line.split()[1:])
            index = int(fields["index"])
            if index != len(results):
                raise RuntimeError("result index drift")
            results[index] = Fraction(fields["upper"])
    if not results:
        raise RuntimeError("empty result stream")
    return results


def distribution(values):
    values = sorted(float(value) for value in values)
    return {
        "minimum": min(values),
        "median": statistics.median(values),
        "mean": statistics.fmean(values),
        "maximum": max(values),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline")
    parser.add_argument("candidate")
    arguments = parser.parse_args()
    baseline = read_results(arguments.baseline)
    candidate = read_results(arguments.candidate)
    if baseline.keys() != candidate.keys():
        raise RuntimeError("result-set drift")
    differences = [candidate[index] - baseline[index] for index in baseline]
    print(json.dumps({
        "schema": "candle-nl-fixed-result-pair-v1",
        "status": "DEVELOPMENT_NON_RELEASE",
        "cells": len(differences),
        "candidate_tighter": sum(value < 0 for value in differences),
        "equal": sum(value == 0 for value in differences),
        "candidate_wider": sum(value > 0 for value in differences),
        "candidate_minus_baseline": distribution(differences),
        "baseline_minimum_margin_below_zero": float(-max(baseline.values())),
        "candidate_minimum_margin_below_zero": float(-max(candidate.values())),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
