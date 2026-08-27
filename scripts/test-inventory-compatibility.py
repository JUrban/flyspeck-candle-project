#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


inventory = load_module("compatibility_inventory", SCRIPT_DIR / "inventory_compatibility.py")


class InventorySyntaxTests(unittest.TestCase):
    def scan(self, text: str, path: str = "fixture.ml"):
        return inventory.scan_text("fixture", "0" * 40, path, text)

    def test_classifies_required_constructs(self):
        text = """\
(* open Hidden *)
open A.B;;
let x = let open C in y
let z = D.(x)
let op = D.E.( ++ )
let q = `x == y`;;
let p = a == b;;
let _ = Cake.Runtime.customFFI "system" bytes;;
module M = N.O;;
module F (X:S) = struct end;;
module type S = sig end;;
include I.J;;
"""
        findings, notes = self.scan(text)
        self.assertEqual(notes, [])
        categories = [finding["category"] for finding in findings]
        self.assertEqual(
            categories,
            [
                "open.declaration",
                "open.local_let",
                "open.local_parenthesized",
                "open.local_parenthesized",
                "pointer_equality.infix_use",
                "ffi.custom_call",
                "module.declaration_alias",
                "module.declaration_functor",
                "module.type_declaration",
                "module.include",
            ],
        )
        pointer = next(item for item in findings if item["category"] == "pointer_equality.infix_use")
        self.assertEqual(pointer["details"]["semantic_purpose"], "unresolved_static_analysis")
        self.assertEqual(pointer["details"]["static_operand_category"], "identifier_operands")
        ffi = next(item for item in findings if item["category"] == "ffi.custom_call")
        self.assertEqual(ffi["details"]["command_literal_raw"], "system")
        local_opens = [
            item for item in findings
            if item["category"] == "open.local_parenthesized"
        ]
        self.assertEqual(
            [item["details"]["body_form"] for item in local_opens],
            ["general_expression", "operator_reference"],
        )
        self.assertEqual(local_opens[1]["details"]["operator"], "++")

    def test_masks_literals_comments_and_hol_terms(self):
        text = """\
let s = "open Hidden; a == b; Runtime.customFFI \\\"bad\\\" x";;
(* module M = struct let x = a != b end *)
let theorem = `p ==> q`;;
let actual = left != right;;
"""
        findings, notes = self.scan(text)
        self.assertEqual(notes, [])
        self.assertEqual([item["category"] for item in findings], ["pointer_equality.infix_use"])
        self.assertEqual(findings[0]["details"]["operator"], "!=")

    def test_nested_comment_and_camlp_quotation_are_masked(self):
        text = "(* outer (* open X *) end *)\n<:expr< module M = struct end >>\nopen Y;;\n"
        findings, notes = self.scan(text)
        self.assertEqual(notes, [])
        self.assertEqual([item["category"] for item in findings], ["open.declaration"])

    def test_pa_j_backticks_do_not_desynchronize_lexer(self):
        text = "lexer [ `IDENT | \"(*\" | -> failwith \"x\" ];\nopen Parser_support;;\n"
        findings, notes = self.scan(text, "pa_j/generated.ml")
        self.assertEqual(notes, [])
        self.assertEqual([item["category"] for item in findings], ["open.declaration"])
        self.assertEqual(findings[0]["source_dialect"], "camlp_legacy_generated_ml")

    def test_vhl_double_dash_comment_is_not_pointer_syntax(self):
        text = "-- theorem p ==> q and (x == y).\nmodule Visible.\n"
        findings, notes = self.scan(text, "theory/example.vhl")
        self.assertEqual(notes, [])
        self.assertEqual([item["category"] for item in findings], ["module.declaration_other"])
        self.assertEqual(findings[0]["source_dialect"], "verification_source_vhl")

    def test_unclosed_construct_is_reported(self):
        _, notes = self.scan("open A;;\n(* truncated")
        self.assertEqual([note.kind for note in notes], ["unterminated_comment"])

    def test_finding_id_is_deterministic(self):
        first, _ = self.scan("open A;;\n")
        second, _ = self.scan("open A;;\n")
        self.assertEqual(first, second)


class InventoryCliTests(unittest.TestCase):
    def run_git(self, repo: Path, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), *args], check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout.strip()

    def test_cli_is_byte_reproducible_and_ignores_untracked_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            repos = root / "repos"
            repos.mkdir()
            heads = {}
            for name, source in {
                "candle": "open Base;;\nlet same = x == y;;\n",
                "flyspeck": "let _ = Runtime.customFFI \"chdir\" bytes;;\n",
            }.items():
                repo = repos / name
                repo.mkdir()
                self.run_git(repo, "init", "-q")
                self.run_git(repo, "config", "user.email", "test@example.invalid")
                self.run_git(repo, "config", "user.name", "Inventory Test")
                (repo / "source.ml").write_text(source, encoding="utf-8")
                self.run_git(repo, "add", "source.ml")
                self.run_git(repo, "commit", "-qm", "fixture")
                (repo / "untracked.ml").write_text("open Ignored;;\n", encoding="utf-8")
                heads[name] = self.run_git(repo, "rev-parse", "HEAD")

            scope = root / "scope.toml"
            scope.write_text(
                "\n".join(
                    [
                        "schema_version = 1",
                        'inventory_id = "fixture"',
                        'roadmap_version = "1.3"',
                        f'roadmap_sha256 = "{"0" * 64}"',
                        'scope_kind = "fixture"',
                        'extensions = [".ml"]',
                        "[repositories.candle]",
                        'path = "candle"',
                        f'pinned_commit = "{heads["candle"]}"',
                        "[repositories.flyspeck]",
                        'path = "flyspeck"',
                        f'pinned_commit = "{heads["flyspeck"]}"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            output = root / "output"
            command = [
                sys.executable, str(SCRIPT_DIR / "inventory_compatibility.py"),
                "--scope", str(scope), "--repos-root", str(repos),
                "--output-dir", str(output),
            ]
            subprocess.run(command, check=True, stdout=subprocess.PIPE, text=True)
            first = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in output.iterdir()}
            subprocess.run(command, check=True, stdout=subprocess.PIPE, text=True)
            second = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in output.iterdir()}
            self.assertEqual(first, second)
            summary = json.loads((output / "inventory-summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["totals"]["source_files_scanned"], 2)
            self.assertEqual(summary["counts"]["by_category"]["ffi.custom_call"], 1)
            self.assertEqual(summary["counts"]["by_category"]["open.declaration"], 1)
            self.assertEqual(summary["counts"]["by_category"]["pointer_equality.infix_use"], 1)
            self.assertEqual(summary["counts"]["by_category"]["module.first_class_pack"], 0)


if __name__ == "__main__":
    unittest.main()
