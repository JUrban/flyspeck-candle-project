#!/usr/bin/env python3
"""Deterministic lexical inventory of OCaml-family compatibility constructs.

The scanner is intentionally conservative.  It recognizes syntax after masking
comments and literal/quotation bodies, but it is not an OCaml type checker and
never assigns semantic intent to pointer equality or compatibility status to a
source occurrence.  See docs/compatibility-inventory.md for the evidence
boundary.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import subprocess
import sys
import tomllib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


GENERATOR_NAME = "inventory_compatibility.py"
GENERATOR_VERSION = 1
UPPER = r"[A-Z][A-Za-z0-9_']*"
LOWER = r"[a-z_][A-Za-z0-9_']*"
SIMPLE_PATH = rf"{UPPER}(?:\s*\.\s*{UPPER})*"
# Covers the module-path forms accepted by the inventory classifier.  It does
# not attempt to parse arbitrary module expressions.
PATH = rf"{SIMPLE_PATH}(?:\s*\(\s*{SIMPLE_PATH}\s*\))?(?:\s*\.\s*{UPPER})*"
CAMLP_QUOTATION_START = re.compile(r"<:[A-Za-z_][A-Za-z0-9_']*<")
RAW_STRING_START = re.compile(r"\{([a-z_][A-Za-z0-9_']*)?\|")
CHAR_LITERAL = re.compile(r"'(?:\\[^\n]|[^'\\\n])'")
FINDING_CATEGORIES = [
    "open.declaration",
    "open.local_let",
    "open.local_parenthesized",
    "module.include",
    "module.declaration_structure",
    "module.declaration_alias",
    "module.declaration_functor",
    "module.declaration_first_class_unpack",
    "module.declaration_other",
    "module.type_declaration",
    "module.first_class_pack",
    "module.first_class_unpack",
    "pointer_equality.infix_use",
    "pointer_equality.operator_binding",
    "pointer_equality.operator_reference",
    "ffi.custom_call",
    "ffi.ocaml_external_declaration",
]
MODULE_PATH_FORMS = ["simple", "dotted", "functor_application", "anonymous_structure", "unparsed_expression"]


@dataclass(frozen=True)
class LexicalNote:
    kind: str
    offset: int
    detail: str


def _blank(chars: list[str], start: int, end: int) -> None:
    for index in range(start, end):
        if chars[index] != "\n":
            chars[index] = " "


def mask_noncode(text: str, *, mask_hol_quotations: bool = True) -> tuple[str, list[LexicalNote]]:
    """Mask comments/literals/quotations while preserving offsets/newlines."""

    chars = list(text)
    notes: list[LexicalNote] = []
    length = len(text)
    index = 0
    while index < length:
        if text.startswith("(*", index):
            start = index
            depth = 1
            index += 2
            while index < length and depth:
                if text.startswith("(*", index):
                    depth += 1
                    index += 2
                elif text.startswith("*)", index):
                    depth -= 1
                    index += 2
                else:
                    index += 1
            if depth:
                notes.append(LexicalNote("unterminated_comment", start, "nested OCaml comment"))
            _blank(chars, start, index)
            continue

        # Camlp quotation, e.g. <:expr< ... >>.  These bodies contain OCaml
        # syntax as data and must not be counted as executed declarations.
        quotation = CAMLP_QUOTATION_START.match(text, index)
        if quotation:
            start = index
            index = quotation.end()
            end = text.find(">>", index)
            if end == -1:
                notes.append(LexicalNote("unterminated_camlp_quotation", start, "<:name< ... >>"))
                index = length
            else:
                index = end + 2
            _blank(chars, start, index)
            continue

        # OCaml quoted strings: {id| ... |id}.  The delimiter identifier may be
        # empty.  Check this before ordinary punctuation handling.
        raw = RAW_STRING_START.match(text, index)
        if raw:
            start = index
            delimiter = raw.group(1) or ""
            index = raw.end()
            closing = f"|{delimiter}}}"
            end = text.find(closing, index)
            if end == -1:
                notes.append(LexicalNote("unterminated_quoted_string", start, closing))
                index = length
            else:
                index = end + len(closing)
            _blank(chars, start, index)
            continue

        if text[index] == '"':
            start = index
            index += 1
            escaped = False
            while index < length:
                char = text[index]
                index += 1
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    break
            else:
                notes.append(LexicalNote("unterminated_string", start, "double-quoted string"))
            _blank(chars, start, index)
            continue

        # HOL Light quotations use paired backticks.  Masking these is critical:
        # == inside a quoted HOL term is implication, not OCaml pointer equality.
        if mask_hol_quotations and text[index] == "`":
            start = index
            end = text.find("`", index + 1)
            if end == -1:
                notes.append(LexicalNote("unterminated_hol_quotation", start, "` ... `"))
                index = length
            else:
                index = end + 1
            _blank(chars, start, index)
            continue

        # Mask unambiguous character literals, but do not confuse OCaml type
        # variables ('a) or identifier primes (x') with literals.
        char_literal = CHAR_LITERAL.match(text, index)
        if char_literal:
            start = index
            index = char_literal.end()
            _blank(chars, start, index)
            continue

        index += 1

    return "".join(chars), notes


def line_column(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    last_newline = text.rfind("\n", 0, offset)
    column = offset + 1 if last_newline == -1 else offset - last_newline
    return line, column


def line_excerpt(text: str, offset: int, limit: int = 240) -> str:
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    if end == -1:
        end = len(text)
    excerpt = text[start:end].strip()
    return excerpt if len(excerpt) <= limit else excerpt[: limit - 1] + "…"


def normalize_path(path: str) -> str:
    return re.sub(r"\s+", "", path)


def module_path_form(path: str | None) -> str | None:
    if path is None:
        return None
    compact = normalize_path(path)
    if compact == "struct":
        return "anonymous_structure"
    if "(" in compact:
        return "functor_application"
    if re.fullmatch(UPPER, compact):
        return "simple"
    if re.fullmatch(rf"{UPPER}(?:\.{UPPER})+", compact):
        return "dotted"
    return "unparsed_expression"


def pointer_operand_shape(masked_line: str, operator_start: int, operator_end: int) -> tuple[str, str, str]:
    left_text = masked_line[:operator_start].rstrip()
    right_text = masked_line[operator_end:].lstrip()
    atom = rf"(?:{LOWER}|{UPPER}(?:\.{UPPER})*|true|false|None|\[\]|\(\)|-?[0-9]+)"
    left_match = re.search(rf"({atom})$", left_text)
    right_match = re.match(rf"({atom})", right_text)
    left = left_match.group(1) if left_match else "<expression>"
    right = right_match.group(1) if right_match else "<expression>"

    identifiers = re.compile(rf"(?:{LOWER}|{UPPER}(?:\.{UPPER})*)$")
    immediates = re.compile(r"(?:true|false|None|\[\]|\(\)|-?[0-9]+)$")
    if left != "<expression>" and left == right and identifiers.fullmatch(left):
        shape = "syntactic_self_comparison"
    elif immediates.fullmatch(left) and immediates.fullmatch(right):
        shape = "immediate_syntax_operands"
    elif identifiers.fullmatch(left) and identifiers.fullmatch(right):
        shape = "identifier_operands"
    elif ((identifiers.fullmatch(left) and immediates.fullmatch(right)) or
          (immediates.fullmatch(left) and identifiers.fullmatch(right))):
        shape = "identifier_and_immediate_syntax"
    else:
        shape = "expression_operand_present"
    return shape, left, right


def pointer_review_hints(excerpt: str) -> list[str]:
    lowered = excerpt.lower()
    hints: list[str] = []
    for hint, words in (
        ("hash_or_cons_lexeme", ("hash", "hcons", "hashcons", "consed")),
        ("cache_or_memo_lexeme", ("cache", "memo")),
        ("cycle_or_visited_lexeme", ("cycle", "visited", "seen")),
        ("sentinel_or_dummy_lexeme", ("sentinel", "dummy", "marker")),
    ):
        if any(word in lowered for word in words):
            hints.append(hint)
    return hints


class FindingBuilder:
    def __init__(self, repository: str, commit: str, source_path: str, text: str, source_sha256: str):
        self.repository = repository
        self.commit = commit
        self.source_path = source_path
        self.text = text
        self.source_sha256 = source_sha256
        self.findings: list[dict[str, Any]] = []
        self.spans: set[tuple[int, int, str]] = set()
        self.line_starts = [0]
        self.line_starts.extend(match.end() for match in re.finditer("\n", text))

    def location(self, offset: int) -> tuple[int, int]:
        line_index = bisect.bisect_right(self.line_starts, offset) - 1
        return line_index + 1, offset - self.line_starts[line_index] + 1

    def add(
        self,
        category: str,
        start: int,
        end: int,
        *,
        lexeme: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        span_key = (start, end, category)
        if span_key in self.spans:
            return
        self.spans.add(span_key)
        line, column = self.location(start)
        end_line, end_column = self.location(end)
        visible_lexeme = (lexeme if lexeme is not None else self.text[start:end]).strip()
        identity = "\0".join(
            [self.repository, self.commit, self.source_path, str(line), str(column), category, visible_lexeme]
        )
        finding_id = "CF-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
        finding = {
            "schema_version": 1,
            "finding_id": finding_id,
            "category": category,
            "repository": self.repository,
            "repository_commit": self.commit,
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "location": {
                "line": line,
                "column": column,
                "end_line": end_line,
                "end_column": end_column,
            },
            "lexeme": visible_lexeme[:300],
            "excerpt": line_excerpt(self.text, start),
            "details": details or {},
        }
        self.findings.append(finding)


def scan_text(
    repository: str,
    commit: str,
    source_path: str,
    text: str,
    source_sha256: str | None = None,
) -> tuple[list[dict[str, Any]], list[LexicalNote]]:
    if source_sha256 is None:
        source_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    # pa_j contains legacy/revised Camlp lexer source where backticks are lexer
    # tokens, not HOL quotations.  Treating arbitrary pairs as HOL terms would
    # desynchronize the masker and hide executed source.
    masked, notes = mask_noncode(text, mask_hol_quotations=not source_path.startswith("pa_j/"))
    builder = FindingBuilder(repository, commit, source_path, text, source_sha256)

    # Local let-open must be identified before the general open matcher.
    local_open_spans: list[tuple[int, int]] = []
    for match in re.finditer(rf"\blet\s+open(?P<bang>!)?\s+(?P<path>{PATH})\s+in\b", masked):
        path = match.group("path")
        local_open_spans.append(match.span())
        builder.add(
            "open.local_let",
            match.start(),
            match.end(),
            details={
                "module_path": normalize_path(path),
                "module_path_form": module_path_form(path),
                "override_warning_suppression": bool(match.group("bang")),
                "semantic_status": "syntax_only",
            },
        )

    # OCaml's M.(expr) local-open shorthand.
    for match in re.finditer(rf"(?<![A-Za-z0-9_'])\b(?P<path>{SIMPLE_PATH})\s*\.\s*\(", masked):
        path = match.group("path")
        builder.add(
            "open.local_parenthesized",
            match.start(),
            match.end(),
            details={
                "module_path": normalize_path(path),
                "module_path_form": module_path_form(path),
                "semantic_status": "syntax_only",
            },
        )

    for match in re.finditer(rf"\bopen(?P<bang>!)?\s+(?P<path>{PATH}|struct\b)", masked):
        if any(start <= match.start() < end for start, end in local_open_spans):
            continue
        path = match.group("path")
        builder.add(
            "open.declaration",
            match.start(),
            match.end(),
            details={
                "module_path": normalize_path(path),
                "module_path_form": module_path_form(path),
                "override_warning_suppression": bool(match.group("bang")),
                "semantic_status": "syntax_only",
            },
        )

    # Includes expose a module signature/structure but are not equivalent to
    # open.  They are kept as a distinct compatibility category.
    for match in re.finditer(rf"\binclude\s+(?P<path>{PATH}|struct\b)", masked):
        path = match.group("path")
        builder.add(
            "module.include",
            match.start(),
            match.end(),
            details={
                "module_path": normalize_path(path),
                "module_path_form": module_path_form(path),
                "semantic_status": "syntax_only",
            },
        )

    # Module declarations are classified from their syntax.  This does not
    # imply that the declaration belongs to the eventual load closure.
    module_pattern = re.compile(
        rf"(?m)^[ \t]*(?P<local>let\s+)?module\s+(?P<recursive>rec\s+)?"
        rf"(?P<name>{UPPER})(?P<tail>[^\n]*?)(?=;;|$)"
    )
    for match in module_pattern.finditer(masked):
        tail = match.group("tail")
        full = match.group(0)
        details: dict[str, Any] = {
            "module_name": match.group("name"),
            "local_binding": bool(match.group("local")),
            "recursive": bool(match.group("recursive")),
            "semantic_status": "syntax_only",
        }
        if re.search(r"\bfunctor\s*\(|^\s*\(", tail):
            category = "module.declaration_functor"
            details["module_path"] = None
            details["module_path_form"] = None
        elif re.search(r"=\s*struct\b", tail):
            category = "module.declaration_structure"
            details["module_path"] = None
            details["module_path_form"] = None
        else:
            alias = re.search(rf"=\s*(?P<path>{PATH})\s*(?:$|;;|:)" , tail)
            if alias:
                path = alias.group("path")
                category = "module.declaration_alias"
                details["module_path"] = normalize_path(path)
                details["module_path_form"] = module_path_form(path)
            elif re.search(r"=\s*\(\s*val\b", tail):
                category = "module.declaration_first_class_unpack"
                details["module_path"] = None
                details["module_path_form"] = "unparsed_expression"
            else:
                category = "module.declaration_other"
                details["module_path"] = None
                details["module_path_form"] = "unparsed_expression"
        builder.add(category, match.start(), match.end(), lexeme=full, details=details)

    for match in re.finditer(rf"(?m)^[ \t]*module\s+type\s+(?P<name>{UPPER})\b[^\n]*", masked):
        builder.add(
            "module.type_declaration",
            match.start(),
            match.end(),
            details={"module_type_name": match.group("name"), "semantic_status": "syntax_only"},
        )

    for match in re.finditer(r"\(\s*module\b", masked):
        builder.add(
            "module.first_class_pack",
            match.start(),
            match.end(),
            details={"semantic_status": "syntax_only"},
        )

    for match in re.finditer(r"\(\s*val\b[^\n)]*:\s*(?:module\s+)?", masked):
        builder.add(
            "module.first_class_unpack",
            match.start(),
            match.end(),
            details={"semantic_status": "syntax_only"},
        )

    # Physical equality.  Semantic intent is deliberately unresolved.  Only
    # operator and operand-shape facts visible in the source are classified.
    for match in re.finditer(r"(?<![=])(?P<op>==|!=)(?!=)", masked):
        line_start = masked.rfind("\n", 0, match.start()) + 1
        line_end = masked.find("\n", match.end())
        if line_end == -1:
            line_end = len(masked)
        masked_line = masked[line_start:line_end]
        relative_start = match.start() - line_start
        relative_end = match.end() - line_start
        before = masked[:match.start()].rstrip()
        after = masked[match.end():]
        parenthesized = before.endswith("(") and re.match(r"\s*\)", after) is not None
        if parenthesized:
            close = re.match(r"\s*\)", after)
            assert close is not None
            after_close = after[close.end():]
            if re.match(r"\s*=", after_close):
                category = "pointer_equality.operator_binding"
                syntactic_role = "operator_binding"
            else:
                category = "pointer_equality.operator_reference"
                syntactic_role = "operator_reference"
            shape, left, right = "not_applicable", "<operator>", "<operator>"
        else:
            category = "pointer_equality.infix_use"
            syntactic_role = "infix_use"
            shape, left, right = pointer_operand_shape(masked_line, relative_start, relative_end)
        excerpt = line_excerpt(text, match.start())
        builder.add(
            category,
            match.start(),
            match.end(),
            details={
                "operator": match.group("op"),
                "token_category": "double_equal" if match.group("op") == "==" else "bang_equal",
                "syntactic_role": syntactic_role,
                "static_operand_category": shape,
                "left_operand_excerpt": left,
                "right_operand_excerpt": right,
                "operator_resolution": "unresolved_without_name_resolution",
                "builtin_semantics_if_unshadowed": "physical_equal" if match.group("op") == "==" else "physical_not_equal",
                "semantic_purpose": "unresolved_static_analysis",
                "review_hints_not_classifications": pointer_review_hints(excerpt),
            },
        )

    # Runtime.customFFI is the custom CakeML boundary used by Candle.  Keep the
    # command as a literal only when that is directly visible after the call.
    custom_ffi_pattern = re.compile(rf"\b(?P<callee>(?:{UPPER}\.)*customFFI)\b")
    for match in custom_ffi_pattern.finditer(masked):
        remainder = text[match.end(): match.end() + 400]
        literal = re.match(r"\s*\"(?P<command>(?:\\.|[^\"\\])*)\"", remainder)
        details = {
            "callee": match.group("callee"),
            "command_form": "literal" if literal else "dynamic_or_unparsed",
            "command_literal_raw": literal.group("command") if literal else None,
            "semantic_status": "call_site_only",
        }
        builder.add("ffi.custom_call", match.start(), match.end(), details=details)

    # Conventional OCaml external declarations are another trust-boundary
    # signal.  Camlp quotation bodies have already been masked.
    external_pattern = re.compile(rf"\bexternal\s+(?P<name>{LOWER}|\([^\n)]*\))\s*:")
    for match in external_pattern.finditer(masked):
        builder.add(
            "ffi.ocaml_external_declaration",
            match.start(),
            match.end(),
            details={"binding_name": match.group("name"), "semantic_status": "declaration_only"},
        )

    builder.findings.sort(key=lambda item: (item["location"]["line"], item["location"]["column"], item["category"]))
    return builder.findings, notes


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout


def tracked_source_files(repo: Path, extensions: set[str]) -> list[str]:
    output = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    paths = [entry.decode("utf-8", "surrogateescape") for entry in output.split(b"\0") if entry]
    return sorted(path for path in paths if Path(path).suffix in extensions)


def decode_source(raw: bytes) -> tuple[str, str]:
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        # Legacy Flyspeck tooling includes non-UTF-8 bytes.  Latin-1 is a
        # deterministic one-byte mapping and preserves source locations.
        return raw.decode("latin-1"), "latin-1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_summary(
    scope: dict[str, Any],
    scope_sha256: str,
    repositories: dict[str, Any],
    findings: list[dict[str, Any]],
    lexical_notes: list[dict[str, Any]],
    findings_sha256: str,
) -> dict[str, Any]:
    raw_by_category = Counter(item["category"] for item in findings)
    by_category = {category: raw_by_category[category] for category in FINDING_CATEGORIES}
    by_repository = Counter(item["repository"] for item in findings)
    raw_path_forms = Counter(
        item["details"].get("module_path_form")
        for item in findings
        if item["details"].get("module_path_form") is not None
    )
    path_forms = {form: raw_path_forms[form] for form in MODULE_PATH_FORMS}
    pointer_tokens = Counter(
        item["details"]["token_category"]
        for item in findings
        if item["category"].startswith("pointer_equality.")
    )
    pointer_shapes = Counter(
        item["details"]["static_operand_category"]
        for item in findings
        if item["category"] == "pointer_equality.infix_use"
    )
    pointer_roles = Counter(
        item["details"]["syntactic_role"]
        for item in findings
        if item["category"].startswith("pointer_equality.")
    )
    ffi_commands = Counter(
        item["details"]["command_form"]
        for item in findings
        if item["category"] == "ffi.custom_call"
    )
    return {
        "schema_version": 1,
        "inventory_id": scope["inventory_id"],
        "scope_kind": scope["scope_kind"],
        "roadmap": {
            "version": scope["roadmap_version"],
            "sha256": scope["roadmap_sha256"],
        },
        "generator": {"name": GENERATOR_NAME, "version": GENERATOR_VERSION},
        "scope_sha256": scope_sha256,
        "reproducible_command": "scripts/update-compatibility-inventory.sh /project/repos",
        "repositories": repositories,
        "extensions": scope["extensions"],
        "totals": {
            "source_files_scanned": sum(repo["source_files_scanned"] for repo in repositories.values()),
            "source_bytes_scanned": sum(repo["source_bytes_scanned"] for repo in repositories.values()),
            "findings": len(findings),
            "lexical_notes": len(lexical_notes),
        },
        "counts": {
            "by_category": by_category,
            "by_repository": dict(sorted(by_repository.items())),
            "by_category_and_repository": {
                category: {
                    repository: sum(
                        item["category"] == category and item["repository"] == repository
                        for item in findings
                    )
                    for repository in sorted(repositories)
                }
                for category in FINDING_CATEGORIES
            },
            "files_with_findings_by_category": {
                category: len({
                    (item["repository"], item["source_path"])
                    for item in findings if item["category"] == category
                })
                for category in FINDING_CATEGORIES
            },
            "by_module_path_form": path_forms,
            "pointer_by_token": dict(sorted(pointer_tokens.items())),
            "pointer_by_syntactic_role": dict(sorted(pointer_roles.items())),
            "pointer_by_static_operand_category": dict(sorted(pointer_shapes.items())),
            "custom_ffi_by_command_form": dict(sorted(ffi_commands.items())),
            "lexical_notes_by_kind": dict(sorted(Counter(note["kind"] for note in lexical_notes).items())),
        },
        "artifacts": {
            "findings_jsonl": "inventory-findings.jsonl",
            "findings_sha256": findings_sha256,
            "lexical_notes_json": "inventory-lexical-notes.json",
        },
        "evidence_boundary": {
            "dependency_closure_known": False,
            "semantic_intent_inferred": False,
            "pointer_purpose_default": "unresolved_static_analysis",
            "notes": [
                "Findings are lexical syntax occurrences in tracked snapshot files, not proven production dependencies.",
                "Comments, strings, HOL quotations, character literals, OCaml quoted strings, and Camlp quotation bodies are masked.",
                "Pointer-equality purpose requires review; review hints are lexical signals, not classifications.",
                "A lexical note marks an input the conservative masker could not close and must be reviewed.",
            ],
        },
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--repos-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-dirty", action="store_true", help="development only; summary records dirty state")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    scope_raw = args.scope.read_bytes()
    scope = tomllib.loads(scope_raw.decode("utf-8"))
    if scope.get("schema_version") != 1:
        raise SystemExit("unsupported inventory scope schema")
    extensions = set(scope["extensions"])
    all_findings: list[dict[str, Any]] = []
    all_notes: list[dict[str, Any]] = []
    repo_summary: dict[str, Any] = {}

    for repository, config in sorted(scope["repositories"].items()):
        repo = (args.repos_root / config["path"]).resolve()
        if not (repo / ".git").exists():
            raise SystemExit(f"{repository}: not a git repository: {repo}")
        head = run_git(repo, "rev-parse", "HEAD").strip()
        if head != config["pinned_commit"]:
            raise SystemExit(f"{repository}: HEAD {head} != pinned {config['pinned_commit']}")
        dirty_output = run_git(repo, "status", "--porcelain", "--untracked-files=no")
        dirty = bool(dirty_output)
        if dirty and not args.allow_dirty:
            raise SystemExit(f"{repository}: tracked worktree is dirty; refuse non-reproducible inventory")

        files = tracked_source_files(repo, extensions)
        bytes_scanned = 0
        encodings: Counter[str] = Counter()
        repo_findings = 0
        for source_path in files:
            raw = (repo / source_path).read_bytes()
            bytes_scanned += len(raw)
            text, encoding = decode_source(raw)
            encodings[encoding] += 1
            findings, notes = scan_text(
                repository,
                head,
                source_path,
                text,
                hashlib.sha256(raw).hexdigest(),
            )
            all_findings.extend(findings)
            repo_findings += len(findings)
            for note in notes:
                line, column = line_column(text, note.offset)
                all_notes.append(
                    {
                        "repository": repository,
                        "repository_commit": head,
                        "source_path": source_path,
                        "location": {"line": line, "column": column},
                        "kind": note.kind,
                        "detail": note.detail,
                    }
                )
        repo_summary[repository] = {
            "path_key": config["path"],
            "commit": head,
            "dirty": dirty,
            "source_files_scanned": len(files),
            "source_bytes_scanned": bytes_scanned,
            "encodings": dict(sorted(encodings.items())),
            "findings": repo_findings,
        }

    all_findings.sort(
        key=lambda item: (
            item["repository"], item["source_path"], item["location"]["line"],
            item["location"]["column"], item["category"],
        )
    )
    all_notes.sort(key=lambda item: (item["repository"], item["source_path"], item["location"]["line"], item["kind"]))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    findings_path = args.output_dir / "inventory-findings.jsonl"
    with findings_path.open("w", encoding="utf-8", newline="\n") as handle:
        for finding in all_findings:
            handle.write(json.dumps(finding, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n")
    findings_sha256 = sha256_file(findings_path)
    write_json(args.output_dir / "inventory-lexical-notes.json", all_notes)
    summary = build_summary(
        scope,
        hashlib.sha256(scope_raw).hexdigest(),
        repo_summary,
        all_findings,
        all_notes,
        findings_sha256,
    )
    write_json(args.output_dir / "inventory-summary.json", summary)
    print(
        f"inventory: {summary['totals']['source_files_scanned']} files, "
        f"{summary['totals']['findings']} findings, {summary['totals']['lexical_notes']} lexical notes"
    )
    print(f"findings sha256: {findings_sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
