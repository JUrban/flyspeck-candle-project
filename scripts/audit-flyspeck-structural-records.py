#!/usr/bin/python3
"""Audit structural-record syntax in an exact Flyspeck parser plan.

This is a byte-lexical development audit.  It deliberately makes no parsing,
typing, reachability, semantics, S1, S2, or S3 claim.  Its purpose is to make
the record surface that a future CakeML frontend change must cover explicit
and reproducible before that change is designed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


OUTPUT_ROOT_MODE = 0o555
OUTPUT_FILE_MODE = 0o444
PRIVATE_MODE = 0o700


class AuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def line_number(source: bytes, offset: int) -> int:
    return source.count(b"\n", 0, offset) + 1


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    start: int
    end: int


def _is_name_start(byte: int) -> bool:
    return 0x41 <= byte <= 0x5A or 0x61 <= byte <= 0x7A or byte == 0x5F


def _is_name_byte(byte: int) -> bool:
    return _is_name_start(byte) or 0x30 <= byte <= 0x39 or byte == 0x27


def _skip_comment(source: bytes, index: int) -> int:
    start = index
    depth = 1
    index += 2
    while index < len(source):
        if source[index:index + 2] == b"(*":
            depth += 1
            index += 2
        elif source[index:index + 2] == b"*)":
            depth -= 1
            index += 2
            if depth == 0:
                return index
        else:
            index += 1
    raise AuditError(f"unterminated comment at byte {start}")


def _skip_quoted(source: bytes, index: int, delimiter: int, label: str) -> int:
    start = index
    index += 1
    while index < len(source):
        byte = source[index]
        index += 1
        if byte == 0x5C and index < len(source):
            index += 1
        elif byte == delimiter:
            return index
    raise AuditError(f"unterminated {label} at byte {start}")


def _char_or_type_variable(source: bytes, index: int) -> tuple[Token | None, int]:
    start = index
    index += 1
    if index >= len(source):
        return None, index
    if source[index] == 0x5C:
        return None, _skip_quoted(source, start, 0x27, "character literal")
    if index + 1 < len(source) and source[index + 1] == 0x27:
        return None, index + 2
    if _is_name_start(source[index]):
        end = index + 1
        while end < len(source) and _is_name_byte(source[end]):
            end += 1
        if end < len(source) and source[end] == 0x27:
            return None, end + 1
        return Token("type-variable", source[index:end].decode("ascii"), start, end), end
    return None, index


def tokenize(source: bytes) -> list[Token]:
    tokens: list[Token] = []
    index = 0
    paired = {b";;", b"<-", b"->", b"::", b"&&", b"||"}
    singles = b"{}()[]:;=.,|"
    while index < len(source):
        if source[index:index + 2] == b"(*":
            index = _skip_comment(source, index)
            continue
        byte = source[index]
        if byte == 0x22:
            index = _skip_quoted(source, index, 0x22, "string")
            continue
        if byte == 0x27:
            token, index = _char_or_type_variable(source, index)
            if token is not None:
                tokens.append(token)
            continue
        pair = source[index:index + 2]
        if pair in paired:
            tokens.append(Token("symbol", pair.decode("ascii"), index, index + 2))
            index += 2
            continue
        if byte in singles:
            tokens.append(Token("symbol", chr(byte), index, index + 1))
            index += 1
            continue
        if _is_name_start(byte):
            end = index + 1
            while end < len(source) and _is_name_byte(source[end]):
                end += 1
            tokens.append(Token("name", source[index:end].decode("ascii"), index, end))
            index = end
            continue
        index += 1
    return tokens


def scopes(tokens: list[Token]) -> list[tuple[str, ...]]:
    """Return a conservative lexical module path for every token."""
    result: list[tuple[str, ...]] = []
    blocks: list[tuple[str, str | None]] = []
    pending_modules: list[str] = []
    for index, token in enumerate(tokens):
        result.append(tuple(name for _kind, name in blocks if name is not None))
        if (
            token.value == "module" and index + 1 < len(tokens)
            and tokens[index + 1].kind == "name"
            and tokens[index + 1].value != "type"
        ):
            pending_modules.append(tokens[index + 1].value)
        elif token.value == "struct":
            name = pending_modules.pop() if pending_modules else None
            blocks.append(("struct", name))
        elif token.value in {"sig", "begin"}:
            blocks.append((token.value, None))
        elif token.value == "end" and blocks:
            blocks.pop()
        elif token.value == ";;":
            pending_modules.clear()
    return result


def delimiter_depths(tokens: list[Token]) -> list[tuple[int, int, int]]:
    paren = bracket = brace = 0
    result = []
    for token in tokens:
        result.append((paren, bracket, brace))
        if token.value == "(":
            paren += 1
        elif token.value == ")":
            paren = max(0, paren - 1)
        elif token.value == "[":
            bracket += 1
        elif token.value == "]":
            bracket = max(0, bracket - 1)
        elif token.value == "{":
            brace += 1
        elif token.value == "}":
            brace = max(0, brace - 1)
    return result


def matching_braces(tokens: list[Token]) -> dict[int, int]:
    stack: list[int] = []
    result: dict[int, int] = {}
    for index, token in enumerate(tokens):
        if token.value == "{":
            stack.append(index)
        elif token.value == "}":
            require(bool(stack), f"unmatched closing brace at byte {token.start}")
            opened = stack.pop()
            result[opened] = index
    require(not stack, f"unmatched opening brace at byte {tokens[stack[-1]].start}" if stack else "")
    return result


DECLARATION_BOUNDARIES = {"type", "let", "module", "class", "exception", "external"}


def structural_type_name(
    tokens: list[Token], depths: list[tuple[int, int, int]], brace_index: int,
) -> str | None:
    if brace_index < 3 or tokens[brace_index - 1].value != "=":
        return None
    baseline = depths[brace_index]
    name = tokens[brace_index - 2]
    if name.kind != "name" or not name.value[:1].islower():
        return None
    cursor = brace_index - 3
    clause = None
    while cursor >= 0:
        if depths[cursor] != baseline:
            cursor -= 1
            continue
        value = tokens[cursor].value
        if value in {"type", "and", "let", ";;"}:
            clause = value
            break
        if value in DECLARATION_BOUNDARIES:
            return None
        cursor -= 1
    if clause == "type":
        return name.value
    if clause != "and":
        return None
    cursor -= 1
    while cursor >= 0:
        if depths[cursor] == baseline and tokens[cursor].value in {"type", "let", ";;"}:
            return name.value if tokens[cursor].value == "type" else None
        cursor -= 1
    return None


def top_level_segments(
    tokens: list[Token], depths: list[tuple[int, int, int]], opened: int, closed: int,
) -> list[tuple[int, int]]:
    baseline = depths[opened]
    inner = (baseline[0], baseline[1], baseline[2] + 1)
    starts = [opened + 1]
    for index in range(opened + 1, closed):
        if depths[index] == inner and tokens[index].value == ";":
            starts.append(index + 1)
    ends = starts[1:] + [closed]
    return [(start, end) for start, end in zip(starts, ends) if start < end]


def field_declarations(
    tokens: list[Token], depths: list[tuple[int, int, int]], opened: int, closed: int,
) -> list[dict]:
    fields = []
    for start, end in top_level_segments(tokens, depths, opened, closed):
        segment = [token for token in tokens[start:end] if token.value != ";"]
        if not segment:
            continue
        mutable = segment[0].value == "mutable"
        offset = 1 if mutable else 0
        if (
            len(segment) > offset + 1 and segment[offset].kind == "name"
            and segment[offset + 1].value == ":"
        ):
            fields.append({"name": segment[offset].value, "mutable": mutable})
    return fields


def assigned_fields(
    tokens: list[Token], depths: list[tuple[int, int, int]], start: int, end: int,
) -> list[str]:
    if start >= end:
        return []
    baseline = depths[start]
    result = []
    for index in range(start, end - 1):
        if (
            depths[index] == baseline and tokens[index].kind == "name"
            and tokens[index].value[:1].islower() and tokens[index + 1].value == "="
        ):
            result.append(tokens[index].value)
    return sorted(set(result))


def pattern_fields(
    tokens: list[Token], depths: list[tuple[int, int, int]], opened: int, closed: int,
) -> list[str]:
    result = []
    for start, end in top_level_segments(tokens, depths, opened, closed):
        segment = tokens[start:end]
        if segment and segment[0].kind == "name" and segment[0].value[:1].islower():
            result.append(segment[0].value)
    return sorted(set(result))


def audit_source(source: bytes, index: int, source_key: str) -> dict:
    tokens = tokenize(source)
    token_scopes = scopes(tokens)
    depths = delimiter_depths(tokens)
    brace_pairs = matching_braces(tokens)
    types = []
    uses = []
    structural_braces: set[int] = set()

    for opened, closed in sorted(brace_pairs.items()):
        type_name = structural_type_name(tokens, depths, opened)
        if type_name is not None:
            fields = field_declarations(tokens, depths, opened, closed)
            require(fields, f"empty/unrecognized structural record {source_key}:{type_name}")
            structural_braces.add(opened)
            types.append({
                "type_name": type_name,
                "module_path": list(token_scopes[opened]),
                "line": line_number(source, tokens[opened].start),
                "fields": fields,
            })

    for opened, closed in sorted(brace_pairs.items()):
        if opened in structural_braces:
            continue
        previous = tokens[opened - 1] if opened else None
        if previous is not None and (
            previous.value == "of"
            or previous.kind == "name" and previous.value[:1].isupper()
        ):
            continue
        baseline = depths[opened]
        inner = (baseline[0], baseline[1], baseline[2] + 1)
        with_indices = [
            position for position in range(opened + 1, closed)
            if depths[position] == inner and tokens[position].value == "with"
        ]
        if with_indices:
            fields = assigned_fields(tokens, depths, with_indices[0] + 1, closed)
            if fields:
                uses.append({
                    "kind": "update",
                    "module_path": list(token_scopes[opened]),
                    "line": line_number(source, tokens[opened].start),
                    "fields": fields,
                })
            continue
        fields = assigned_fields(tokens, depths, opened + 1, closed)
        if fields:
            uses.append({
                "kind": "construction",
                "module_path": list(token_scopes[opened]),
                "line": line_number(source, tokens[opened].start),
                "fields": fields,
            })
            continue
        fields = pattern_fields(tokens, depths, opened, closed)
        if fields:
            uses.append({
                "kind": "pattern",
                "module_path": list(token_scopes[opened]),
                "line": line_number(source, tokens[opened].start),
                "fields": fields,
            })

    for position, token in enumerate(tokens[:-1]):
        if token.value != "." or tokens[position + 1].kind != "name":
            continue
        field = tokens[position + 1]
        if not field.value[:1].islower() or position == 0:
            continue
        receiver = tokens[position - 1]
        if receiver.kind == "name" and receiver.value[:1].isupper():
            continue
        assignment = position + 2 < len(tokens) and tokens[position + 2].value == "<-"
        uses.append({
            "kind": "assignment" if assignment else "projection",
            "module_path": list(token_scopes[position]),
            "line": line_number(source, token.start),
            "field": field.value,
        })

    return {
        "index": index,
        "source_key": source_key,
        "structural_types": types,
        "uses": uses,
    }


def aggregate(records: list[dict]) -> dict:
    label_owners: dict[tuple[tuple[str, ...], str], list[dict]] = {}
    for record in records:
        for type_record in record["structural_types"]:
            for field in type_record["fields"]:
                key = (tuple(type_record["module_path"]), field["name"])
                label_owners.setdefault(key, []).append({
                    "source_key": record["source_key"],
                    "type_name": type_record["type_name"],
                    "line": type_record["line"],
                    "mutable": field["mutable"],
                })
    duplicates = [
        {"module_path": list(module), "field": field, "owners": owners}
        for (module, field), owners in sorted(label_owners.items()) if len(owners) > 1
    ]
    kinds = ["construction", "update", "pattern", "projection", "assignment"]
    return {
        "input_count": len(records),
        "inputs_with_structural_types": sum(bool(r["structural_types"]) for r in records),
        "structural_type_count": sum(len(r["structural_types"]) for r in records),
        "field_declaration_count": sum(
            len(t["fields"]) for r in records for t in r["structural_types"]
        ),
        "mutable_field_declaration_count": sum(
            f["mutable"] for r in records for t in r["structural_types"] for f in t["fields"]
        ),
        "use_counts": {
            kind: sum(u["kind"] == kind for r in records for u in r["uses"])
            for kind in kinds
        },
        "duplicate_field_label_count": len(duplicates),
        "duplicate_field_labels": duplicates,
    }


def run(plan_root: Path, output_root: Path) -> dict:
    require(not output_root.exists(), f"output root already exists: {output_root}")
    plan_path = plan_root / "plan.json"
    plan_data = plan_path.read_bytes()
    try:
        plan = json.loads(plan_data)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuditError(f"cannot decode parser plan: {error}") from error
    inputs = plan.get("inputs")
    require(
        plan.get("schema") == 3
        and plan.get("kind") == "candle-flyspeck-caml-parser-all-inventory-diagnostic-plan"
        and isinstance(inputs, list) and len(inputs) == 400,
        "structural-record audit requires quotation-aware all-inventory plan schema 3",
    )
    all_records = []
    records = []
    for expected_index, entry in enumerate(inputs):
        require(entry.get("index") == expected_index, "non-canonical plan input order")
        prepared = entry.get("prepared_input")
        require(isinstance(prepared, dict), f"missing prepared input: {expected_index}")
        path = plan_root / prepared["path"]
        source = path.read_bytes()
        require(
            len(source) == prepared["bytes"] and sha256(source) == prepared["sha256"],
            f"prepared input drift: {expected_index}",
        )
        record = audit_source(source, expected_index, entry["source_key"])
        all_records.append(record)
        if record["structural_types"] or record["uses"]:
            records.append(record)
    totals = aggregate(all_records)
    summary = {
        "schema": 1,
        "kind": "nonpromotable-flyspeck-structural-record-byte-lexical-audit",
        "promotion_allowed": False,
        "s1_evidence": False,
        "s2_evidence": False,
        "s3_evidence": False,
        "limitations": [
            "byte-lexical classification, not an OCaml or Candle parse",
            "module paths are conservative lexical scopes",
            "projection classification excludes uppercase module/constructor paths",
            "no typing, label resolution, evaluation, reachability, or semantics claim",
        ],
        "plan": {"path": str(plan_path), "bytes": len(plan_data), "sha256": sha256(plan_data)},
        "totals": totals,
        "records": records,
    }
    data = canonical_bytes(summary)
    output_root.mkdir(mode=PRIVATE_MODE)
    output = output_root / "structural-record-audit.json"
    output.write_bytes(data)
    output.chmod(OUTPUT_FILE_MODE)
    output_root.chmod(OUTPUT_ROOT_MODE)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    arguments = parser.parse_args()
    summary = run(arguments.plan_root.resolve(strict=True), arguments.output_root)
    print(json.dumps(summary["totals"], sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (AuditError, OSError) as error:
        raise SystemExit(f"structural-record audit rejected: {error}") from error
