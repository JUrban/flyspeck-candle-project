#!/usr/bin/env python3
"""Plan an adaptive forest replay from complete per-node native bounds."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


RESULT_RE = re.compile(r"\bindex=([0-9]+)\b.*?\bupper=([^ ]+)")


@dataclass(frozen=True)
class Node:
    index: int
    component: int
    parent: int
    side: int
    depth: int
    kind: str
    axis: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("topology", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("jobs", type=Path)
    parser.add_argument("filtered_jobs", type=Path)
    parser.add_argument("summary", type=Path)
    return parser.parse_args()


def read_topology(path: Path) -> list[Node]:
    nodes: list[Node] = []
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        fields = line.split("\t")
        if len(fields) != 7:
            raise ValueError(f"{path}:{line_number}: expected seven fields")
        index, component, parent, side, depth, kind, axis = fields
        node = Node(
            int(index), int(component), int(parent), int(side), int(depth),
            kind, int(axis)
        )
        if node.index != len(nodes):
            raise ValueError(f"{path}:{line_number}: non-sequential index")
        if node.kind not in {"leaf", "node"}:
            raise ValueError(f"{path}:{line_number}: bad node kind")
        if node.kind == "leaf" and node.axis != 0:
            raise ValueError(f"{path}:{line_number}: leaf has split axis")
        nodes.append(node)
    if not nodes:
        raise ValueError("empty topology")
    return nodes


def read_bounds(path: Path, expected: int) -> list[Fraction]:
    bounds: dict[int, Fraction] = {}
    for line in path.read_text().splitlines():
        if not line.startswith("CANDLE_NL_NATIVE_FIXED_SCALE_RESULT "):
            continue
        match = RESULT_RE.search(line)
        if match is None:
            raise ValueError(f"malformed result line: {line[:120]}")
        index = int(match.group(1))
        if index in bounds:
            raise ValueError(f"duplicate result index {index}")
        bounds[index] = Fraction(match.group(2))
    if set(bounds) != set(range(expected)):
        raise ValueError("result index set does not match topology")
    return [bounds[index] for index in range(expected)]


def validate_topology(nodes: list[Node]) -> tuple[list[int], dict[int, tuple[int, int]]]:
    roots: list[int] = []
    children: dict[int, dict[int, int]] = {}
    for node in nodes:
        if node.parent == -1:
            if node.side != -1 or node.depth != 0:
                raise ValueError(f"malformed root {node.index}")
            roots.append(node.index)
            continue
        if not 0 <= node.parent < node.index:
            raise ValueError(f"bad parent at node {node.index}")
        parent = nodes[node.parent]
        if parent.kind != "node" or node.side not in {0, 1}:
            raise ValueError(f"bad edge at node {node.index}")
        if node.depth != parent.depth + 1 or node.component != parent.component:
            raise ValueError(f"edge identity drift at node {node.index}")
        sides = children.setdefault(node.parent, {})
        if node.side in sides:
            raise ValueError(f"duplicate child side at node {node.index}")
        sides[node.side] = node.index
    paired: dict[int, tuple[int, int]] = {}
    for node in nodes:
        sides = children.get(node.index, {})
        if node.kind == "node":
            if set(sides) != {0, 1}:
                raise ValueError(f"internal node {node.index} lacks two children")
            paired[node.index] = sides[0], sides[1]
        elif sides:
            raise ValueError(f"leaf {node.index} has children")
    if len({nodes[root].component for root in roots}) != len(roots):
        raise ValueError("component root identities are not unique")
    return roots, paired


def subtree_sizes(nodes: list[Node], children: dict[int, tuple[int, int]]) -> list[int]:
    sizes = [0] * len(nodes)
    for node in reversed(nodes):
        if node.kind == "leaf":
            sizes[node.index] = 1
        else:
            left, right = children[node.index]
            sizes[node.index] = 1 + sizes[left] + sizes[right]
    return sizes


def main() -> None:
    args = parse_args()
    nodes = read_topology(args.topology)
    bounds = read_bounds(args.results, len(nodes))
    roots, children = validate_topology(nodes)
    sizes = subtree_sizes(nodes, children)

    visited: list[int] = []
    terminal_nodes = 0
    terminal_internal_nodes = 0
    rejected_internal_nodes = 0
    rejected_leaves: list[int] = []
    skipped_nodes = 0
    maximum_depth = 0

    def walk(index: int) -> None:
        nonlocal terminal_nodes, terminal_internal_nodes
        nonlocal rejected_internal_nodes, skipped_nodes, maximum_depth
        node = nodes[index]
        visited.append(index)
        maximum_depth = max(maximum_depth, node.depth)
        if bounds[index] < 0:
            terminal_nodes += 1
            if node.kind == "node":
                terminal_internal_nodes += 1
                skipped_nodes += sizes[index] - 1
            return
        if node.kind == "leaf":
            rejected_leaves.append(index)
            return
        rejected_internal_nodes += 1
        left, right = children[index]
        walk(left)
        walk(right)

    for root in roots:
        walk(root)

    job_lines = args.jobs.read_text().splitlines()
    if len(job_lines) != len(nodes):
        raise ValueError("job count does not match topology")
    filtered: list[str] = []
    for new_index, old_index in enumerate(visited):
        fields = job_lines[old_index].split("\t")
        if len(fields) != 5 or int(fields[0]) != old_index:
            raise ValueError(f"malformed job {old_index}")
        fields[0] = str(new_index)
        filtered.append("\t".join(fields))
    args.filtered_jobs.write_text("\n".join(filtered) + "\n")

    summary = {
        "schema": "candle-nl-adaptive-forest-replay-v1",
        "status": "DEVELOPMENT_NON_RELEASE",
        "complete_acceptance": not rejected_leaves,
        "components": len(roots),
        "total_nodes": len(nodes),
        "visited_nodes": len(visited),
        "skipped_nodes": skipped_nodes,
        "visited_fraction": len(visited) / len(nodes),
        "node_reduction_fraction": 1 - len(visited) / len(nodes),
        "terminal_nodes": terminal_nodes,
        "terminal_internal_nodes": terminal_internal_nodes,
        "rejected_internal_nodes": rejected_internal_nodes,
        "rejected_leaves": rejected_leaves,
        "maximum_visited_depth": maximum_depth,
        "visited_node_indices": visited,
    }
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in summary.items()
                      if key != "visited_node_indices"}, sort_keys=True))


if __name__ == "__main__":
    main()
