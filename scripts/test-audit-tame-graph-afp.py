#!/usr/bin/env python3
"""Focused tests for the historical Flyspeck-Tame source audit."""

from __future__ import annotations

import importlib.util
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "audit-tame-graph-afp.py"
ARCHIVE = (
    PROJECT_ROOT
    / "third_party"
    / "afp-flyspeck-tame-2014-08-28"
    / "afp-Flyspeck-Tame-2014-08-28.tar.gz"
)
SPEC = importlib.util.spec_from_file_location("audit_tame_graph_afp", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class TameGraphAfpAuditTests(unittest.TestCase):
    def test_nested_comments_do_not_create_declarations(self) -> None:
        source = b"""theory X imports Main begin
(* outer (* lemma fake: True *) still comment *)
definition real :: bool where "real = True"
lemma [simp]: "real" by (simp add: real_def)
primrec "quoted" :: "nat => nat" where "quoted 0 = 0"
end
"""
        inventory = AUDIT.declaration_inventory("X.thy", source)
        self.assertEqual(inventory["theory"], "X")
        self.assertEqual(inventory["imports"], ["Main"])
        self.assertEqual(
            [(item["kind"], item["name"]) for item in inventory["declarations"]],
            [("definition", "real"), ("lemma", None), ("primrec", "quoted")],
        )

    def test_member_path_gate(self) -> None:
        self.assertEqual(
            AUDIT.safe_member_path("Flyspeck-Tame/Graph.thy").as_posix(),
            "Flyspeck-Tame/Graph.thy",
        )
        for bad in ("/Flyspeck-Tame/Graph.thy", "Flyspeck-Tame/../x", "Other/x"):
            with self.subTest(path=bad), self.assertRaises(ValueError):
                AUDIT.safe_member_path(bad)

    def test_vendored_release_and_flyspeck_overlap(self) -> None:
        files, contents = AUDIT.read_archive(ARCHIVE)
        self.assertEqual(len(files), 44)
        self.assertEqual(sum(path.endswith(".thy") for path in contents), 35)

        overlap = (
            "ArchCompAux.thy",
            "Completeness.thy",
            "Enumerator.thy",
            "FaceDivision.thy",
            "Graph.thy",
            "ListAux.thy",
            "Plane.thy",
            "Plane1.thy",
            "PlaneGraphIso.thy",
            "RTranCl.thy",
            "Rotation.thy",
            "Tame.thy",
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            theory_root = root / "formal_graph" / "isabelle_tame"
            archive_root = root / "formal_graph" / "archive"
            theory_root.mkdir(parents=True)
            archive_root.mkdir(parents=True)
            for name in overlap:
                raw = contents[name]
                if name == "Tame.thy":
                    raw = raw.replace(
                        b"http://code.google.com/p/flyspeck/source/browse/trunk/"
                        b"text_formalization/tame/tame_defs.hl",
                        b"text_formalization/tame/tame_defs.hl",
                    )
                (theory_root / name).write_bytes(raw)
            (theory_root / "Vector.thy").write_text("theory Vector\n", encoding="utf-8")
            for name in ("Tri.ML", "Quad.ML", "Pent.ML", "Hex.ML"):
                (archive_root / name).write_bytes(contents[f"Archives/{name}"])

            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Tame audit test",
                    "-c",
                    "user.email=tame-audit@example.invalid",
                    "commit",
                    "-qm",
                    "fixture",
                ],
                cwd=root,
                check=True,
            )
            comparison = AUDIT.compare_flyspeck(root, contents)
            self.assertEqual(
                comparison["theory_overlap_summary"],
                {
                    "byte_identical": 11,
                    "comment_url_only": 1,
                    "flyspeck_only": ["Vector.thy"],
                },
            )
            self.assertTrue(
                all(
                    item["relation"] == "byte_identical"
                    for item in comparison["archive_overlap"]
                )
            )


if __name__ == "__main__":
    unittest.main()
