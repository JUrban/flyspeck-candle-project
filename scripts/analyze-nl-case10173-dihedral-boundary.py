#!/usr/bin/env python3
"""Compare historical and fixed-scale dihedral data on matched boxes.

This is a development diagnostic.  It compares two untrusted native
implementations; it does not establish any theorem or enclosure relation.
"""

import argparse
from fractions import Fraction
import json
import math
import statistics


DIMENSIONS = 6
HESSIAN_ENTRIES = [
    (row, column)
    for row in range(DIMENSIONS)
    for column in range(row, DIMENSIONS)
]


def fields(line):
    result = {}
    for item in line.split()[1:]:
        key, value = item.split("=", 1)
        result[key] = value
    return result


def interval(text, conversion):
    lower, upper = text.split(":", 1)
    return conversion(lower), conversion(upper)


def vector(text, conversion):
    return [interval(item, conversion) for item in text.split(",")]


def parse_output(path, diagnostic_marker, conversion, hessian_key):
    diagnostics = {}
    full_bounds = {}
    with open(path, encoding="utf-8") as source:
        for line in source:
            if line.startswith(diagnostic_marker + " "):
                row = fields(line)
                index = int(row["index"])
                diagnostics[index] = {
                    "lower": conversion(row["lower"]),
                    "upper": conversion(row["upper"]),
                    "center": interval(row["center"], conversion),
                    "gradient": vector(row["center_gradient"], conversion),
                    "hessian": (
                        [conversion(item) for item in row[hessian_key].split(",")]
                        if hessian_key == "hessian_abs"
                        else vector(row[hessian_key], conversion)
                    ),
                }
            elif line.startswith("CANDLE_NL_NATIVE_BOX_RESULT "):
                row = fields(line)
                full_bounds[int(row["index"])] = conversion(
                    row["specialized_upper"]
                )
            elif line.startswith("CANDLE_NL_NATIVE_FIXED_SCALE_RESULT "):
                row = fields(line)
                full_bounds[int(row["index"])] = conversion(row["upper"])
    return diagnostics, full_bounds


def parse_boxes(path, count):
    boxes = {}
    with open(path, encoding="utf-8") as source:
        for line in source:
            columns = line.rstrip("\n").split("\t")
            index = int(columns[0])
            if index >= count:
                break
            lower = [Fraction(item) for item in columns[1].split(",")]
            upper = [Fraction(item) for item in columns[2].split(",")]
            boxes[index] = [float((high - low) / 2) for low, high in zip(lower, upper)]
    return boxes


def absolute_upper(value):
    return max(abs(float(value[0])), abs(float(value[1])))


def components(diagnostic, radii, signed_hessian):
    center_lower = float(diagnostic["center"][0])
    linear = sum(
        radius * absolute_upper(gradient)
        for radius, gradient in zip(radii, diagnostic["gradient"])
    )
    quadratic = 0.0
    for entry_index, (row, column) in enumerate(HESSIAN_ENTRIES):
        entry = diagnostic["hessian"][entry_index]
        magnitude = absolute_upper(entry) if signed_hessian else float(entry)
        factor = 0.5 if row == column else 1.0
        quadratic += factor * radii[row] * radii[column] * magnitude
    return center_lower, linear, quadratic


def distribution(values):
    ordered = sorted(values)
    return {
        "minimum": min(ordered),
        "median": statistics.median(ordered),
        "mean": statistics.fmean(ordered),
        "p90": ordered[math.ceil(0.9 * len(ordered)) - 1],
        "maximum": max(ordered),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("historical_output")
    parser.add_argument("fixed_output")
    parser.add_argument("boxes")
    arguments = parser.parse_args()

    historical, historical_full = parse_output(
        arguments.historical_output,
        "CANDLE_NL_NATIVE_ANGLE_DIAGNOSTIC",
        float,
        "hessian_abs",
    )
    fixed, fixed_full = parse_output(
        arguments.fixed_output,
        "CANDLE_NL_NATIVE_FIXED_SCALE_ANGLE_DIAGNOSTIC",
        Fraction,
        "hessian",
    )
    if historical.keys() != fixed.keys() or historical.keys() != historical_full.keys():
        raise RuntimeError("historical/fixed diagnostic index drift")
    if fixed.keys() != fixed_full.keys():
        raise RuntimeError("fixed result index drift")
    boxes = parse_boxes(arguments.boxes, len(fixed))
    if boxes.keys() != fixed.keys():
        raise RuntimeError("box index drift")

    lower_differences = []
    upper_differences = []
    width_ratios = []
    component_excess = {"center": [], "linear": [], "quadratic": []}
    hessian_ratios = [[] for _ in HESSIAN_ENTRIES]
    hessian_excess_contributions = [[] for _ in HESSIAN_ENTRIES]
    rejected = []

    for index in sorted(fixed):
        old = historical[index]
        new = fixed[index]
        lower_differences.append(float(new["lower"]) - old["lower"])
        upper_differences.append(float(new["upper"]) - old["upper"])
        old_width = old["upper"] - old["lower"]
        width_ratios.append(
            (float(new["upper"]) - float(new["lower"])) / old_width
        )
        old_components = components(old, boxes[index], False)
        new_components = components(new, boxes[index], True)
        component_excess["center"].append(new_components[0] - old_components[0])
        component_excess["linear"].append(new_components[1] - old_components[1])
        component_excess["quadratic"].append(new_components[2] - old_components[2])

        for entry_index, (row, column) in enumerate(HESSIAN_ENTRIES):
            old_magnitude = float(old["hessian"][entry_index])
            new_magnitude = absolute_upper(new["hessian"][entry_index])
            if old_magnitude > 0:
                hessian_ratios[entry_index].append(new_magnitude / old_magnitude)
            factor = 0.5 if row == column else 1.0
            hessian_excess_contributions[entry_index].append(
                factor
                * boxes[index][row]
                * boxes[index][column]
                * (new_magnitude - old_magnitude)
            )
        if fixed_full[index] >= 0:
            rejected.append(index)

    entry_rows = []
    for entry_index, entry in enumerate(HESSIAN_ENTRIES):
        entry_rows.append(
            {
                "entry": "%d,%d" % entry,
                "magnitude_ratio": distribution(hessian_ratios[entry_index]),
                "mean_excess_taylor_contribution": statistics.fmean(
                    hessian_excess_contributions[entry_index]
                ),
            }
        )
    entry_rows.sort(
        key=lambda row: row["mean_excess_taylor_contribution"], reverse=True
    )

    result = {
        "schema": "candle-nl-dihedral-boundary-comparison-v1",
        "status": "DEVELOPMENT_NON_RELEASE",
        "boxes": len(fixed),
        "historical_full_accepted": sum(value < 0 for value in historical_full.values()),
        "fixed_partial_full_accepted": sum(value < 0 for value in fixed_full.values()),
        "fixed_rejected_indices": rejected,
        "fixed_minus_historical_angle_lower": distribution(lower_differences),
        "fixed_minus_historical_angle_upper": distribution(upper_differences),
        "angle_width_ratio_fixed_over_historical": distribution(width_ratios),
        "fixed_minus_historical_lower_bound_components": {
            key: distribution(values) for key, values in component_excess.items()
        },
        "hessian_entries_by_mean_excess_taylor_contribution": entry_rows,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
