#!/usr/bin/env python3
"""Audit the literal source-load closure of the first fast-NL support files.

This is a development preflight for the authenticated Candle loader.  It
resolves literal ``needs``, ``loadt``, ``loads``, ``flyspeck_needs``, and
``#use`` requests using the exact support search-path order, walks their
transitive closure, and compares every resolved node with the source-identity
and alias authorities installed by the v663 setup.

The audit deliberately fails on dynamic or unresolved requests.  It does not
execute HOL Light and is not theorem evidence; its purpose is to prevent a
sequence of expensive checkpoint restores that each discover one omitted
manifest node.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import sys
from collections import deque


PROJECT = pathlib.Path("/project")
CANDLE_CURRENT = PROJECT / "worktrees/candle-direct-fast-nl-runtime-v1"
FLYSPECK_BOOTSTRAP = PROJECT / "worktrees/flyspeck-strictbuild-bootstrap-v1"
FORMAL_INEQS = FLYSPECK_BOOTSTRAP / "formal_ineqs"
SNAPSHOT = (
    PROJECT
    / "flyspeck-candle-runs/v352-full-boundary-materialization-heap16-dev-005"
    / "snapshot"
)
SNAPSHOT_CANDLE = SNAPSHOT / "candle"
SNAPSHOT_FLYSPECK = SNAPSHOT / "flyspeck"
FIXTURE = (
    PROJECT
    / "flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001"
)

ENTRY_REQUESTS = (
    "candle/cv_compute_analytic_expr_case10173_historical_registered_original_prove.ml",
    "candle/benchmark_cv_compute_registered_hol4_export.ml",
    "candle/benchmark_cv_compute_analytic_expr_case10173_historical_registered_input.ml",
    "candle/benchmark_cv_compute_analytic_expr_case10173_historical_registered_topology_capture.ml",
)

# support.ml prepends these three roots in list order, so the final lookup
# order is reversed.  The remaining roots are the relevant inherited paths
# from the authenticated post-action-49 state.
SEARCH_ROOTS = (
    CANDLE_CURRENT,
    FLYSPECK_BOOTSTRAP,
    FORMAL_INEQS,
    SNAPSHOT_FLYSPECK / "jHOLLight",
    SNAPSHOT_FLYSPECK / "formal_ineqs",
    SNAPSHOT_FLYSPECK / "text_formalization",
    SNAPSHOT_CANDLE,
)

EXTRA_IDENTITIES = FIXTURE / "extra-source-identities.ml"
IDENTITY_EXTENSION = (
    PROJECT
    / "flyspeck-candle-project/tools/fast_nl_v664_support_identity_extension.ml"
)
ALIASES = FIXTURE / "fast-nl-source-aliases.ml"
BASE_IDENTITIES = CANDLE_CURRENT / "candle/flyspeck_source_digests.ml"

LOAD_RE = re.compile(
    r"(?:\b(?:needs|loadt|loads|flyspeck_needs)\s*(?:\(\s*)?|#use\s+)"
    r"\"([^\"\\]+)\""
)
LOAD_CALL_RE = re.compile(r"\b(?:needs|loadt|loads|flyspeck_needs)\b")
EXTRA_RE = re.compile(
    r'^\s*\("([^\"]+)",\("[^\"]+","([0-9a-f]{32})"\)\);\s*$'
)
ALIAS_RE = re.compile(
    r'^\s*\("([^\"]+)","([^\"]+)","([0-9a-f]{32})"\);\s*$'
)
BASE_RE = re.compile(
    r'^\s*\("(candle|flyspeck)","([^\"]+)","([0-9a-f]{32})"\);\s*$'
)


def strip_comments(text: str) -> str:
    """Remove nested OCaml comments while preserving string literals."""

    out: list[str] = []
    index = 0
    depth = 0
    in_string = False
    in_hol_quote = False
    escaped = False
    while index < len(text):
        pair = text[index : index + 2]
        char = text[index]
        if depth:
            if pair == "(*":
                depth += 1
                index += 2
            elif pair == "*)":
                depth -= 1
                index += 2
            else:
                index += 1
            continue
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if in_hol_quote:
            out.append(char)
            if char == "`":
                in_hol_quote = False
            index += 1
            continue
        if pair == "(*":
            depth = 1
            index += 2
        else:
            out.append(char)
            if char == '"':
                in_string = True
            elif char == "`":
                in_hol_quote = True
            index += 1
    if depth:
        raise ValueError("unterminated OCaml comment")
    if in_string:
        raise ValueError("unterminated OCaml string")
    if in_hol_quote:
        raise ValueError("unterminated HOL quotation")
    return "".join(out)


def md5(path: pathlib.Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_and_literal_loads(path: pathlib.Path) -> tuple[str, list[str]]:
    text = path.read_text(encoding="utf-8")
    source = strip_comments(text)
    return source, LOAD_RE.findall(source)


def resolve(request: str) -> pathlib.Path | None:
    candidate = pathlib.Path(request)
    if candidate.is_absolute():
        return candidate.resolve(strict=False) if candidate.is_file() else None
    for root in SEARCH_ROOTS:
        candidate = root / request
        if candidate.is_file():
            return candidate.resolve()
    return None


def parse_authority() -> tuple[dict[pathlib.Path, str], set[pathlib.Path]]:
    identities: dict[pathlib.Path, str] = {}
    aliases: set[pathlib.Path] = set()

    for authority in (EXTRA_IDENTITIES, IDENTITY_EXTENSION):
        if not authority.is_file():
            continue
        for line in authority.read_text(encoding="utf-8").splitlines():
            match = EXTRA_RE.match(line)
            if match:
                identities[pathlib.Path(match.group(1)).resolve()] = match.group(2)

    for line in ALIASES.read_text(encoding="utf-8").splitlines():
        match = ALIAS_RE.match(line)
        if match:
            alias = pathlib.Path(match.group(1)).resolve()
            canonical = pathlib.Path(match.group(2)).resolve()
            identities[alias] = match.group(3)
            identities[canonical] = match.group(3)
            aliases.add(alias)

    base_roots = {
        "candle": SNAPSHOT_CANDLE,
        "flyspeck": SNAPSHOT_FLYSPECK,
    }
    for line in BASE_IDENTITIES.read_text(encoding="utf-8").splitlines():
        match = BASE_RE.match(line)
        if match:
            path = (base_roots[match.group(1)] / match.group(2)).resolve()
            identities[path] = match.group(3)

    return identities, aliases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--emit-missing-ml",
        action="store_true",
        help="emit ML identity entries for all missing resolved nodes",
    )
    args = parser.parse_args()

    identities, aliases = parse_authority()
    queue: deque[tuple[str, pathlib.Path | None]] = deque(
        (request, None) for request in ENTRY_REQUESTS
    )
    visited: set[pathlib.Path] = set()
    edges: list[tuple[pathlib.Path | None, str, pathlib.Path]] = []
    unresolved: list[tuple[pathlib.Path | None, str]] = []
    dynamic_markers: list[tuple[pathlib.Path, int, str]] = []

    while queue:
        request, parent = queue.popleft()
        path = resolve(request)
        if path is None:
            unresolved.append((parent, request))
            continue
        edges.append((parent, request, path))
        if path in visited:
            continue
        visited.add(path)
        try:
            source, requests = source_and_literal_loads(path)
        except (OSError, UnicodeDecodeError, ValueError) as error:
            print(f"parse_error={path}: {error}", file=sys.stderr)
            return 2
        for line_number, line in enumerate(source.splitlines(), start=1):
            if LOAD_CALL_RE.search(line) and not LOAD_RE.search(line):
                dynamic_markers.append((path, line_number, line.strip()))
        queue.extend((child, path) for child in requests)

    missing = sorted(
        (path for path in visited if path not in identities), key=str
    )
    stale_authority: list[tuple[pathlib.Path, str, str]] = []
    for path in sorted(visited, key=str):
        expected = identities.get(path)
        if expected is not None:
            actual = md5(path)
            if actual != expected:
                stale_authority.append((path, expected, actual))

    print(f"status={int(bool(unresolved or dynamic_markers or stale_authority or missing))}")
    print(f"entry_count={len(ENTRY_REQUESTS)}")
    print(f"resolved_node_count={len(visited)}")
    print(f"resolved_edge_count={len(edges)}")
    print(f"authority_path_count={len(identities)}")
    print(f"alias_path_count={len(aliases)}")
    print(f"missing_identity_count={len(missing)}")
    print(f"unresolved_request_count={len(unresolved)}")
    print(f"dynamic_request_count={len(dynamic_markers)}")
    print(f"stale_authority_count={len(stale_authority)}")

    for path in missing:
        digest = md5(path)
        parents = sorted(
            {
                str(parent) if parent is not None else "<entry>"
                for parent, _, child in edges
                if child == path
            }
        )
        print(f"missing_identity={path}\tmd5={digest}\tparents={','.join(parents)}")
        if args.emit_missing_ml:
            print(f'  ("{path}",(\"{path.name}\",\"{digest}\"));')

    for parent, request in unresolved:
        print(f"unresolved_request={parent or '<entry>'}\t{request}")
    for path, line_number, line in dynamic_markers:
        print(f"dynamic_request={path}:{line_number}\t{line}")
    for path, expected, actual in stale_authority:
        print(f"stale_authority={path}\texpected={expected}\tactual={actual}")

    return 1 if unresolved or dynamic_markers or stale_authority or missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
