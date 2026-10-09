#!/usr/bin/env python3
"""Compare a streaming forest execution with an all-node numerical oracle."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


ALL_RESULT = re.compile(r"\bindex=([0-9]+)\b.*?\bupper=([^ ]+)")
STREAM_RESULT = re.compile(
    r"\bvisit=([0-9]+)\b.*?\bnode=([0-9]+)\b.*?\bupper=([^ ]+)"
    r".*?\bdecision=(prune|split|reject)\b"
    r".*?\bdomain_subdivision=([01])\b"
)


@dataclass(frozen=True)
class Node:
    index: int
    component: int
    parent: int
    side: int
    depth: int
    leaf: bool
    axis: int


def fields(line: str) -> dict[str, str]:
    return dict(item.split("=", 1) for item in line.split()[1:])


def read_topology(path: Path) -> tuple[list[Node], list[int], dict[int, tuple[int, int]]]:
    nodes: list[Node] = []
    roots: list[int] = []
    child_sides: dict[int, dict[int, int]] = {}
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        columns = line.split("\t")
        if len(columns) != 7:
            raise ValueError(f"{path}:{line_number}: malformed topology row")
        index, component, parent, side, depth, kind, axis = columns
        node = Node(
            int(index), int(component), int(parent), int(side), int(depth),
            kind == "leaf", int(axis)
        )
        if node.index != len(nodes) or kind not in {"leaf", "node"}:
            raise ValueError(f"{path}:{line_number}: topology identity drift")
        if node.leaf and node.axis != 0:
            raise ValueError(f"{path}:{line_number}: leaf split-axis drift")
        nodes.append(node)
        if node.parent == -1:
            if node.side != -1 or node.depth != 0:
                raise ValueError(f"{path}:{line_number}: malformed root")
            roots.append(node.index)
        else:
            if not 0 <= node.parent < node.index or node.side not in {0, 1}:
                raise ValueError(f"{path}:{line_number}: malformed edge")
            parent_node = nodes[node.parent]
            if (parent_node.leaf or parent_node.component != node.component or
                    node.depth != parent_node.depth + 1):
                raise ValueError(f"{path}:{line_number}: edge identity drift")
            sides = child_sides.setdefault(node.parent, {})
            if node.side in sides:
                raise ValueError(f"{path}:{line_number}: duplicate child side")
            sides[node.side] = node.index
    children: dict[int, tuple[int, int]] = {}
    for node in nodes:
        sides = child_sides.get(node.index, {})
        if node.leaf:
            if sides:
                raise ValueError(f"leaf {node.index} has children")
        elif set(sides) != {0, 1}:
            raise ValueError(f"internal node {node.index} lacks children")
        else:
            children[node.index] = sides[0], sides[1]
    return nodes, roots, children


def read_all_bounds(path: Path, count: int) -> list[Fraction]:
    bounds: dict[int, Fraction] = {}
    for line in path.read_text().splitlines():
        if not line.startswith("CANDLE_NL_NATIVE_FIXED_SCALE_RESULT "):
            continue
        match = ALL_RESULT.search(line)
        if match is None:
            raise ValueError("malformed all-node result")
        index = int(match.group(1))
        if index in bounds:
            raise ValueError(f"duplicate all-node result {index}")
        bounds[index] = Fraction(match.group(2))
    if set(bounds) != set(range(count)):
        raise ValueError("all-node result set drift")
    return [bounds[index] for index in range(count)]


def expected_traversal(
    nodes: list[Node], roots: list[int], children: dict[int, tuple[int, int]],
    bounds: list[Fraction]
) -> tuple[list[tuple[int, Fraction, str]], dict[str, int | bool]]:
    visited: list[tuple[int, Fraction, str]] = []
    terminal_nodes = 0
    terminal_internal_nodes = 0
    rejected_internal_nodes = 0
    rejected_leaves = 0
    maximum_depth = 0

    def walk(index: int) -> None:
        nonlocal terminal_nodes, terminal_internal_nodes
        nonlocal rejected_internal_nodes, rejected_leaves, maximum_depth
        node = nodes[index]
        maximum_depth = max(maximum_depth, node.depth)
        if bounds[index] < 0:
            decision = "prune"
            terminal_nodes += 1
            if not node.leaf:
                terminal_internal_nodes += 1
        elif node.leaf:
            decision = "reject"
            rejected_leaves += 1
        else:
            decision = "split"
            rejected_internal_nodes += 1
        visited.append((index, bounds[index], decision))
        if decision == "split":
            left, right = children[index]
            walk(left)
            walk(right)

    for root in roots:
        walk(root)
    return visited, {
        "complete_acceptance": rejected_leaves == 0,
        "components": len(roots),
        "total_nodes": len(nodes),
        "visited_nodes": len(visited),
        "terminal_nodes": terminal_nodes,
        "terminal_internal_nodes": terminal_internal_nodes,
        "rejected_internal_nodes": rejected_internal_nodes,
        "rejected_leaves": rejected_leaves,
        "maximum_depth": maximum_depth,
    }


def read_stream(path: Path) -> tuple[list[tuple[int, Fraction, str]], int, dict[str, str]]:
    records: list[tuple[int, Fraction, str]] = []
    domain_subdivisions = 0
    summary: dict[str, str] | None = None
    ok = False
    for line in path.read_text().splitlines():
        if line.startswith("CANDLE_NL_NATIVE_STREAMING_RESULT "):
            match = STREAM_RESULT.search(line)
            if match is None:
                raise ValueError("malformed streaming result")
            visit = int(match.group(1))
            if visit != len(records):
                raise ValueError("stream visit-order drift")
            records.append((int(match.group(2)), Fraction(match.group(3)),
                            match.group(4)))
            domain_subdivisions += int(match.group(5))
        elif line.startswith("CANDLE_NL_NATIVE_STREAMING_SUMMARY "):
            if summary is not None:
                raise ValueError("duplicate streaming summary")
            summary = fields(line)
        elif line.startswith("CANDLE_NL_NATIVE_STREAMING_FOREST_OK "):
            ok = True
    if summary is None or not ok:
        raise ValueError("incomplete streaming transcript")
    return records, domain_subdivisions, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("topology", type=Path)
    parser.add_argument("all_results", type=Path)
    parser.add_argument("stream_results", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    nodes, roots, children = read_topology(args.topology)
    bounds = read_all_bounds(args.all_results, len(nodes))
    expected, expected_summary = expected_traversal(
        nodes, roots, children, bounds)
    actual, domain_subdivisions, stream_summary = read_stream(
        args.stream_results)
    if actual != expected:
        for visit, pair in enumerate(zip(actual, expected)):
            if pair[0] != pair[1]:
                raise ValueError(
                    f"stream/all-node drift at visit {visit}: "
                    f"{pair[0]} != {pair[1]}"
                )
        raise ValueError("stream/all-node result length drift")
    for key, expected_value in expected_summary.items():
        if key == "complete_acceptance":
            continue
        if int(stream_summary[key]) != expected_value:
            raise ValueError(f"stream summary drift for {key}")

    output = {
        "schema": "candle-nl-streaming-forest-validation-v1",
        "status": "DEVELOPMENT_NON_RELEASE",
        **expected_summary,
        "domain_subdivisions": domain_subdivisions,
        "mode": stream_summary["mode"],
        "bounds_and_order_match_all_node_oracle": True,
    }
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
