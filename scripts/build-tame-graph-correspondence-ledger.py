#!/usr/bin/env python3
"""Build the initial Isabelle-to-HOL tame-graph correspondence ledger.

This is deliberately an inventory and triage artifact.  An existing binding or
translation-ledger entry is a lead to a proof, never evidence that the two
definitions or theorems correspond.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


DEFINITION_KINDS = {
    "abbreviation",
    "datatype",
    "definition",
    "fun",
    "function",
    "inductive",
    "inductive_set",
    "primrec",
    "typedef",
}
PROOF_KINDS = {"corollary", "lemma", "lemmas", "proposition", "theorem", "theorems"}
HOL_SOURCES = (
    "formal_graph/isabelle_hollight_translation.hl",
    "text_formalization/tame/tame_defs2.hl",
    "text_formalization/tame/tame_list.hl",
    "text_formalization/tame/import_tame_classification.hl",
)
ANCHORS = (
    ("ArchComp", "pre_iso_test3", "authentic triangle archive structural computation"),
    ("ArchComp", "same3", "authentic parameter-0 enumeration/archive computation"),
    ("ArchCompProps", "combine_evals_filter", "computed verdict to coverage theorem"),
    ("ArchCompProps", "tameEnumFilter", "parameterized executable enumerator"),
    ("ArchCompProps", "TameEnum_tameEnumFilter", "enumerator semantic equivalence"),
    ("TameEnum", "next_tame", "tame-preserving checked transition"),
    ("TameEnumProps", "next_tame_comp", "tame completion preservation"),
    ("Generator", "next_tame0", "pruned generator"),
    ("GeneratorProps", "next_tame0_comp", "pruning completeness"),
    ("Completeness", "completeness", "full classification aggregation"),
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def strip_nested_comments(text: str) -> str:
    output: list[str] = []
    depth = 0
    index = 0
    while index < len(text):
        pair = text[index : index + 2]
        if pair == "(*":
            depth += 1
            output.extend("  ")
            index += 2
        elif pair == "*)" and depth:
            depth -= 1
            output.extend("  ")
            index += 2
        else:
            character = text[index]
            output.append(character if depth == 0 or character == "\n" else " ")
            index += 1
    if depth:
        raise ValueError("unterminated OCaml comment")
    return "".join(output)


def git_head(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def parse_translation_entries(raw: bytes) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = strip_nested_comments(raw.decode("utf-8"))
    definitions: list[dict[str, Any]] = []
    for block in re.findall(r"\bliz_add\s*\{(.*?)\};;", text, flags=re.DOTALL):
        name_match = re.search(r'\bliz_name\s*=\s*"([^"]+)"\s*;', block)
        location_matches = re.findall(
            r'\bliz_loc\s*=\s*\(\s*(tamefile|holfile)\s+"([^"]+)"\s*,'
            r"\s*([0-9]+)\s*,\s*([0-9]+)\s*\)\s*;",
            block,
        )
        hol_match = re.search(r"\bliz_holl\s*=\s*`([^`]*)`\s*;", block, flags=re.DOTALL)
        theorem_match = re.search(r"\bliz_thm\s*=\s*([^;]+);", block)
        if not name_match:
            continue
        source = None
        if location_matches:
            location_kind, path, start, end = location_matches[-1]
            source = {
                "kind": location_kind,
                "path": path,
                "line_start": int(start),
                "line_end": int(end),
            }
        definitions.append(
            {
                "isabelle_name": name_match.group(1),
                "source": source,
                "hol_term": hol_match.group(1).strip() if hol_match else None,
                "hol_theorem_binding": theorem_match.group(1).strip() if theorem_match else None,
            }
        )

    types: list[dict[str, Any]] = []
    for block in re.findall(r"\bliz_ty\s*\{(.*?)\};;", text, flags=re.DOTALL):
        isa_match = re.search(r'\bliz_t\s*=\s*"([^"]+)"\s*;', block)
        hol_match = re.search(r'\bliz_h\s*=\s*"([^"]+)"\s*;', block)
        location_match = re.search(
            r'\bliz_ty_loc\s*=\s*\(\s*(?:tamefile\s+)?"([^"]*)"\s*,'
            r"\s*([0-9]+)\s*,\s*([0-9]+)\s*\)\s*;",
            block,
        )
        if isa_match and hol_match:
            types.append(
                {
                    "isabelle_type": isa_match.group(1),
                    "hol_type": hol_match.group(1),
                    "source": (
                        {
                            "path": location_match.group(1),
                            "line_start": int(location_match.group(2)),
                            "line_end": int(location_match.group(3)),
                        }
                        if location_match
                        else None
                    ),
                }
            )
    return definitions, types


def theory_closure(theories: dict[str, dict[str, Any]], roots: list[str]) -> tuple[list[str], list[str]]:
    visited: set[str] = set()
    external: set[str] = set()

    def visit(name: str) -> None:
        if name in visited:
            return
        if name not in theories:
            external.add(name)
            return
        visited.add(name)
        for dependency in theories[name]["imports"]:
            visit(dependency)

    for root in roots:
        visit(root)
    return sorted(visited), sorted(external)


def hol_binding_inventory(flyspeck_root: Path) -> tuple[dict[str, list[str]], list[dict[str, Any]]]:
    bindings: dict[str, list[str]] = {}
    sources: list[dict[str, Any]] = []
    for relative in HOL_SOURCES:
        path = flyspeck_root / relative
        raw = path.read_bytes()
        uncommented = strip_nested_comments(raw.decode("utf-8"))
        names = sorted(set(re.findall(r"^\s*let\s+([A-Za-z_][A-Za-z0-9_']*)\s*=", uncommented, re.MULTILINE)))
        for name in names:
            bindings.setdefault(name, []).append(relative)
        sources.append(
            {"path": relative, "sha256": sha256(raw), "size": len(raw), "binding_count": len(names)}
        )
    return bindings, sources


def declaration_status(
    declaration: dict[str, Any],
    mappings: list[dict[str, Any]],
    hol_bindings: dict[str, list[str]],
) -> tuple[str, str]:
    kind = declaration["kind"]
    name = declaration["name"]
    if mappings:
        return "existing_translation_entry_unvalidated", "definition_correspondence"
    if name and name in hol_bindings:
        return "same_name_hol_binding_unvalidated", "definition_correspondence"
    if kind in DEFINITION_KINDS:
        return "missing_definition_correspondence", "definition_correspondence"
    if kind in PROOF_KINDS:
        return "proof_dependency_unclassified", "proof_result"
    return "structural_command_unclassified", "structural_command"


def build_ledger(inventory_path: Path, flyspeck_root: Path) -> dict[str, Any]:
    inventory_raw = inventory_path.read_bytes()
    inventory = json.loads(inventory_raw)
    if inventory.get("artifact_kind") != "afp_flyspeck_tame_historical_source_inventory":
        raise ValueError("wrong historical source inventory kind")
    theories = {
        item["theory"]: item
        for item in inventory["isabelle_inventory"]["theories"]
        if item["theory"]
    }
    parameter0_closure, parameter0_external = theory_closure(theories, ["ArchComp"])
    completeness_closure, completeness_external = theory_closure(theories, ["Completeness"])

    translation_path = flyspeck_root / HOL_SOURCES[0]
    translation_raw = translation_path.read_bytes()
    mappings, type_mappings = parse_translation_entries(translation_raw)
    mapping_index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for mapping in mappings:
        source = mapping["source"]
        if source and source["kind"] == "tamefile":
            theory = Path(source["path"]).stem
            mapping_index.setdefault((theory, mapping["isabelle_name"]), []).append(mapping)
    hol_bindings, hol_sources = hol_binding_inventory(flyspeck_root)

    declarations: list[dict[str, Any]] = []
    closure_set = set(completeness_closure)
    for theory_name in completeness_closure:
        theory = theories[theory_name]
        for declaration in theory["declarations"]:
            name = declaration["name"]
            matched = mapping_index.get((theory_name, name), []) if name else []
            status, obligation = declaration_status(declaration, matched, hol_bindings)
            declarations.append(
                {
                    "id": f"{theory_name}:{declaration['line']}:{declaration['kind']}:{name or '<unnamed>'}",
                    "theory": theory_name,
                    "source_path": theory["path"],
                    "line": declaration["line"],
                    "kind": declaration["kind"],
                    "name": name,
                    "source_header": declaration["source_header"],
                    "status": status,
                    "obligation": obligation,
                    "existing_translation_entries": matched,
                    "same_name_hol_bindings": hol_bindings.get(name, []) if name else [],
                    "parameter0_theory_closure": theory_name in set(parameter0_closure),
                    "theorem_level_relevance": "unclassified",
                }
            )

    anchor_records: list[dict[str, Any]] = []
    by_theory_name = {(item["theory"], item["name"]): item for item in declarations}
    for theory, name, role in ANCHORS:
        declaration = by_theory_name.get((theory, name))
        if declaration is None:
            raise ValueError(f"missing required anchor declaration: {theory}.{name}")
        anchor_records.append(
            {
                "theory": theory,
                "name": name,
                "role": role,
                "declaration_id": declaration["id"],
                "status": declaration["status"],
            }
        )

    status_counts = Counter(item["status"] for item in declarations)
    kind_counts = Counter(item["kind"] for item in declarations)
    mapped_keys = set(mapping_index)
    declaration_keys = {
        (item["theory"], item["name"])
        for item in declarations
        if item["name"] is not None
    }
    mapping_without_recovered_declaration = [
        mapping
        for key in sorted(mapped_keys - declaration_keys)
        for mapping in mapping_index[key]
    ]

    return {
        "schema_version": 1,
        "artifact_kind": "tame_graph_isabelle_hol_correspondence_ledger",
        "status": "DEVELOPMENT_NON_RELEASE",
        "authority_boundary": (
            "Inventory and triage only. Existing names, bindings, and legacy liz_add "
            "records are not correspondence proofs. Every accepted definition and "
            "general soundness result still requires kernel-checked HOL evidence."
        ),
        "source_inventory": {
            "path": inventory_path.as_posix(),
            "sha256": sha256(inventory_raw),
            "afp_archive_sha256": inventory["upstream"]["archive_sha256"],
        },
        "flyspeck_source": {
            "git_commit": git_head(flyspeck_root),
            "files": hol_sources,
        },
        "theory_closures": {
            "parameter0_computation": {
                "roots": ["ArchComp"],
                "theories": parameter0_closure,
                "external_imports": parameter0_external,
                "scope_note": (
                    "Theory-import closure for pre_iso_test3 and same3; theorem-level "
                    "dependency minimization remains open."
                ),
            },
            "full_completeness": {
                "roots": ["Completeness"],
                "theories": completeness_closure,
                "external_imports": completeness_external,
            },
            "excluded_historical_theories": sorted(set(theories) - closure_set),
        },
        "existing_translation_ledger": {
            "definition_entry_count": len(mappings),
            "type_entry_count": len(type_mappings),
            "type_entries": type_mappings,
            "entries_without_recovered_declaration": mapping_without_recovered_declaration,
        },
        "anchors": anchor_records,
        "summary": {
            "declaration_count": len(declarations),
            "by_kind": dict(sorted(kind_counts.items())),
            "by_status": dict(sorted(status_counts.items())),
            "parameter0_theory_count": len(parameter0_closure),
            "full_completeness_theory_count": len(completeness_closure),
        },
        "declarations": declarations,
        "next_review_gate": (
            "Resolve theorem-level relevance for the parameter-0 anchors and replace "
            "every used unvalidated/missing correspondence with a proved HOL theorem "
            "or a documented implementation route that avoids the declaration."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--flyspeck-root", required=True, type=Path)
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--write", type=Path)
    output.add_argument("--check", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ledger = build_ledger(args.inventory, args.flyspeck_root.resolve())
    encoded = canonical_bytes(ledger)
    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_bytes(encoded)
        print(
            "TAME_GRAPH_CORRESPONDENCE_LEDGER_WRITTEN "
            f"path={args.write} sha256={sha256(encoded)} "
            f"declarations={ledger['summary']['declaration_count']}"
        )
        return 0
    expected = args.check.read_bytes()
    if expected != encoded:
        raise SystemExit(
            "TAME_GRAPH_CORRESPONDENCE_LEDGER_MISMATCH "
            f"expected_sha256={sha256(expected)} actual_sha256={sha256(encoded)}"
        )
    print(
        "TAME_GRAPH_CORRESPONDENCE_LEDGER_OK "
        f"sha256={sha256(encoded)} declarations={ledger['summary']['declaration_count']}"
    )
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
