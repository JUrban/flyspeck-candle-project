#!/usr/bin/env python3
"""Authenticate and inventory the historical AFP Flyspeck-Tame release.

The release archive is an input/specification for the reflected tame-graph
work.  It is not proof authority: every executable definition used by Candle
still needs a HOL correspondence theorem and a proved checker-soundness path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tarfile
from pathlib import Path, PurePosixPath
from typing import Any


ARCHIVE_NAME = "afp-Flyspeck-Tame-2014-08-28.tar.gz"
ARCHIVE_SHA256 = "54aa014cc8de1bc178ef68cc4e88932aefe9a61dcd17712ae714f39ae411102c"
ARCHIVE_SIZE = 514162
RELEASE_URL = "https://isa-afp.org/release/afp-Flyspeck-Tame-2014-08-28.tar.gz"
ENTRY_URL = "https://isa-afp.org/entries/Flyspeck-Tame.html"
ROOT = PurePosixPath("Flyspeck-Tame")

DECLARATION_RE = re.compile(
    r"^\s*(definition|abbreviation|primrec|fun|function|datatype|typedef|"
    r"lemma|lemmas|theorem|theorems|corollary|proposition|inductive|"
    r"inductive_set|locale|class|instantiation|interpretation|sublocale|"
    r"instance|ML|code_[A-Za-z_]+)\b(.*)$"
)
NAME_RE = re.compile(r'^\s*(?:"([^" ]+)"|([^\s:\[=(]+))')
THEORY_RE = re.compile(
    r"\btheory\s+([^\s]+)\s+imports\s+(.*?)\s+begin\b", re.DOTALL
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def strip_nested_comments(text: str) -> str:
    """Replace Isabelle nested comments with whitespace, retaining newlines."""
    result: list[str] = []
    index = 0
    depth = 0
    while index < len(text):
        pair = text[index : index + 2]
        if pair == "(*":
            depth += 1
            result.extend("  ")
            index += 2
        elif pair == "*)" and depth:
            depth -= 1
            result.extend("  ")
            index += 2
        else:
            char = text[index]
            result.append(char if depth == 0 or char == "\n" else " ")
            index += 1
    if depth:
        raise ValueError("unterminated Isabelle comment")
    return "".join(result)


def declaration_inventory(path: str, raw: bytes) -> dict[str, Any]:
    text = raw.decode("utf-8")
    uncommented = strip_nested_comments(text)
    theory_match = THEORY_RE.search(uncommented)
    theory = None
    imports: list[str] = []
    if theory_match:
        theory = theory_match.group(1)
        imports = re.findall(r'"([^"]+)"|([^\s]+)', theory_match.group(2))
        imports = [quoted or plain for quoted, plain in imports]

    declarations: list[dict[str, Any]] = []
    for line_number, line in enumerate(uncommented.splitlines(), 1):
        match = DECLARATION_RE.match(line)
        if not match:
            continue
        kind, remainder = match.groups()
        name_match = NAME_RE.match(remainder)
        name = None
        if name_match:
            candidate = name_match.group(1) or name_match.group(2)
            if candidate not in {"where", "assumes", "shows", "fixes"}:
                name = candidate
        declarations.append(
            {
                "kind": kind,
                "line": line_number,
                "name": name,
                "source_header": line.strip(),
            }
        )
    return {
        "path": path,
        "theory": theory,
        "imports": imports,
        "declarations": declarations,
    }


def safe_member_path(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe archive member path: {name!r}")
    if path.parts[0] != ROOT.name:
        raise ValueError(f"archive member outside {ROOT}: {name!r}")
    return path


def read_archive(archive: Path) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    archive_raw = archive.read_bytes()
    if len(archive_raw) != ARCHIVE_SIZE:
        raise ValueError(
            f"archive size mismatch: expected {ARCHIVE_SIZE}, got {len(archive_raw)}"
        )
    actual_sha = sha256(archive_raw)
    if actual_sha != ARCHIVE_SHA256:
        raise ValueError(
            f"archive SHA-256 mismatch: expected {ARCHIVE_SHA256}, got {actual_sha}"
        )

    files: list[dict[str, Any]] = []
    contents: dict[str, bytes] = {}
    seen: set[str] = set()
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            path = safe_member_path(member.name.rstrip("/"))
            normalized = path.as_posix()
            if normalized in seen:
                raise ValueError(f"duplicate archive member: {normalized}")
            seen.add(normalized)
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError(f"non-regular archive member: {normalized}")
            handle = tar.extractfile(member)
            if handle is None:
                raise ValueError(f"cannot read archive member: {normalized}")
            raw = handle.read()
            if len(raw) != member.size:
                raise ValueError(f"truncated archive member: {normalized}")
            relative = path.relative_to(ROOT).as_posix()
            contents[relative] = raw
            files.append(
                {
                    "path": relative,
                    "sha256": sha256(raw),
                    "size": len(raw),
                }
            )
    files.sort(key=lambda item: item["path"])
    return files, contents


def git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def exact_tame_comment_delta(afp: bytes, flyspeck: bytes) -> bool:
    old = (
        b"http://code.google.com/p/flyspeck/source/browse/trunk/"
        b"text_formalization/tame/tame_defs.hl"
    )
    new = b"text_formalization/tame/tame_defs.hl"
    return old in afp and afp.replace(old, new) == flyspeck


def compare_flyspeck(
    flyspeck_root: Path, contents: dict[str, bytes]
) -> dict[str, Any]:
    theory_root = flyspeck_root / "formal_graph" / "isabelle_tame"
    archive_root = flyspeck_root / "formal_graph" / "archive"
    local_theories = sorted(path.name for path in theory_root.glob("*.thy"))
    afp_theories = sorted(
        path for path in contents if "/" not in path and path.endswith(".thy")
    )
    overlap = sorted(set(local_theories) & set(afp_theories))
    comparisons: list[dict[str, Any]] = []
    exact_count = 0
    comment_only_count = 0
    for name in overlap:
        afp_raw = contents[name]
        local_raw = (theory_root / name).read_bytes()
        if afp_raw == local_raw:
            relation = "byte_identical"
            exact_count += 1
        elif name == "Tame.thy" and exact_tame_comment_delta(afp_raw, local_raw):
            relation = "comment_url_only"
            comment_only_count += 1
        else:
            relation = "different"
        comparisons.append(
            {
                "afp_path": name,
                "flyspeck_path": f"formal_graph/isabelle_tame/{name}",
                "relation": relation,
                "afp_sha256": sha256(afp_raw),
                "flyspeck_sha256": sha256(local_raw),
            }
        )

    archive_comparisons: list[dict[str, Any]] = []
    for name in ("Tri.ML", "Quad.ML", "Pent.ML", "Hex.ML"):
        afp_raw = contents[f"Archives/{name}"]
        local_raw = (archive_root / name).read_bytes()
        archive_comparisons.append(
            {
                "afp_path": f"Archives/{name}",
                "flyspeck_path": f"formal_graph/archive/{name}",
                "relation": "byte_identical" if afp_raw == local_raw else "different",
                "sha256": sha256(afp_raw),
            }
        )

    if len(overlap) != 12 or exact_count != 11 or comment_only_count != 1:
        raise ValueError(
            "unexpected theory overlap: "
            f"overlap={len(overlap)} exact={exact_count} "
            f"comment_only={comment_only_count}"
        )
    if any(item["relation"] != "byte_identical" for item in archive_comparisons):
        raise ValueError("Flyspeck archive files differ from the AFP release")
    if sorted(set(local_theories) - set(afp_theories)) != ["Vector.thy"]:
        raise ValueError("unexpected Flyspeck-only Isabelle theory set")

    return {
        "flyspeck_git_commit": git_head(flyspeck_root),
        "theory_overlap": comparisons,
        "theory_overlap_summary": {
            "byte_identical": exact_count,
            "comment_url_only": comment_only_count,
            "flyspeck_only": ["Vector.thy"],
        },
        "archive_overlap": archive_comparisons,
    }


def build_report(archive: Path, flyspeck_root: Path) -> dict[str, Any]:
    files, contents = read_archive(archive)
    theories = [
        declaration_inventory(path, contents[path])
        for path in sorted(contents)
        if path.endswith(".thy")
    ]
    declaration_count = sum(len(item["declarations"]) for item in theories)
    unnamed_count = sum(
        1
        for item in theories
        for declaration in item["declarations"]
        if declaration["name"] is None
    )
    return {
        "schema_version": 1,
        "artifact_kind": "afp_flyspeck_tame_historical_source_inventory",
        "authority_boundary": (
            "Historical source and comparison metadata only; this artifact is "
            "not a HOL theorem, a correspondence proof, or a classification result."
        ),
        "upstream": {
            "archive_name": ARCHIVE_NAME,
            "archive_sha256": ARCHIVE_SHA256,
            "archive_size": ARCHIVE_SIZE,
            "entry_url": ENTRY_URL,
            "license": "BSD License",
            "release_date": "2014-08-28",
            "release_url": RELEASE_URL,
            "root": ROOT.as_posix(),
        },
        "archive_files": files,
        "archive_file_count": len(files),
        "isabelle_inventory": {
            "theory_count": len(theories),
            "declaration_occurrence_count": declaration_count,
            "unnamed_declaration_occurrence_count": unnamed_count,
            "theories": theories,
        },
        "flyspeck_comparison": compare_flyspeck(flyspeck_root, contents),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--flyspeck-root", required=True, type=Path)
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--write", type=Path)
    output.add_argument("--check", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args.archive.resolve(), args.flyspeck_root.resolve())
    encoded = canonical_bytes(report)
    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_bytes(encoded)
        print(
            "TAME_GRAPH_AFP_INVENTORY_WRITTEN "
            f"path={args.write} sha256={sha256(encoded)} "
            f"files={report['archive_file_count']} "
            f"theories={report['isabelle_inventory']['theory_count']} "
            f"declarations={report['isabelle_inventory']['declaration_occurrence_count']}"
        )
        return 0

    expected = args.check.read_bytes()
    if expected != encoded:
        raise SystemExit(
            "TAME_GRAPH_AFP_INVENTORY_MISMATCH "
            f"expected_sha256={sha256(expected)} actual_sha256={sha256(encoded)}"
        )
    print(
        "TAME_GRAPH_AFP_INVENTORY_OK "
        f"sha256={sha256(encoded)} files={report['archive_file_count']} "
        f"theories={report['isabelle_inventory']['theory_count']} "
        f"declarations={report['isabelle_inventory']['declaration_occurrence_count']}"
    )
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
