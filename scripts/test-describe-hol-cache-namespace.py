#!/usr/bin/env python3
"""Focused tests for the development HOL cache namespace preflight."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).with_name("describe-hol-cache-namespace.py")
SPEC = importlib.util.spec_from_file_location("describe_hol_cache_namespace", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class CacheNamespaceTests(unittest.TestCase):
    def test_compact_digest_is_order_independent_and_exact(self) -> None:
        left = {"b": [2, 1], "a": {"z": True}}
        right = {"a": {"z": True}, "b": [2, 1]}
        expected = hashlib.sha256(
            b'{"a":{"z":true},"b":[2,1]}'
        ).hexdigest()
        self.assertEqual(MODULE.compact_sha256(left), expected)
        self.assertEqual(MODULE.compact_sha256(right), expected)

    def test_canonical_json_is_sorted_and_newline_terminated(self) -> None:
        self.assertEqual(
            MODULE.canonical_json({"z": 1, "a": 2}),
            b'{\n  "a": 2,\n  "z": 1\n}\n',
        )

    def test_parse_ldd_accepts_named_and_loader_routes(self) -> None:
        parsed = MODULE.parse_ldd(
            "linux-vdso.so.1 (0x00007fff)\n"
            "libpolyml.so.9 => /usr/lib/libpolyml.so.9 (0x1234)\n"
            "/lib64/ld-linux-x86-64.so.2 (0xabcd)\n"
        )
        self.assertEqual(parsed, [
            ("libpolyml.so.9", Path("/usr/lib/libpolyml.so.9")),
            ("ld-linux-x86-64.so.2", Path("/lib64/ld-linux-x86-64.so.2")),
        ])

    def test_parse_ldd_rejects_missing_or_unrecognized_routes(self) -> None:
        with self.assertRaisesRegex(MODULE.PreflightFailure, "unresolved"):
            MODULE.parse_ldd("libbad.so => not found\n")
        with self.assertRaisesRegex(MODULE.PreflightFailure, "unrecognized"):
            MODULE.parse_ldd("statically linked\n")
        with self.assertRaisesRegex(MODULE.PreflightFailure, "no file-backed"):
            MODULE.parse_ldd("linux-vdso.so.1 (0x1234)\n")
        with self.assertRaisesRegex(MODULE.PreflightFailure, "duplicate"):
            MODULE.parse_ldd(
                "libc.so.6 => /lib/libc.so.6 (0x1234)\n"
                "libc.so.6 => /lib/libc.so.6 (0x5678)\n"
            )

    def test_dynamic_closure_rejects_ldd_stderr(self) -> None:
        completed = subprocess.CompletedProcess(
            ["ldd", "binary"], 0,
            stdout="libc.so.6 => /lib/libc.so.6 (0x1234)\n",
            stderr="unexpected warning\n",
        )
        with mock.patch.object(MODULE, "run", return_value=completed):
            with self.assertRaisesRegex(MODULE.PreflightFailure, "stderr"):
                MODULE.dynamic_closure(Path("/binary"), "binary")

    def test_dynamic_closure_allows_exact_dependency_free_extension(self) -> None:
        completed = subprocess.CompletedProcess(
            ["ldd", "extension.so"], 0,
            stdout="\tstatically linked\n", stderr="",
        )
        with mock.patch.object(MODULE, "run", return_value=completed):
            identity, local = MODULE.dynamic_closure(
                Path("/extension.so"), "extension", allow_no_dependencies=True,
            )
            self.assertEqual(identity["dependencies"], [])
            self.assertEqual(local["dependencies"], [])
            with self.assertRaises(MODULE.PreflightFailure):
                MODULE.dynamic_closure(Path("/extension.so"), "extension")

    def test_validate_target_is_fail_closed(self) -> None:
        for value in (
            "compiler64ProgTheory.uo",
            "compiler/bootstrap/translation/compiler64ProgTheory.uo",
        ):
            self.assertEqual(MODULE.validate_target(value), value)
        for value in ("", "/absolute", "../escape", "a/../escape", "two words"):
            with self.subTest(value=value):
                with self.assertRaises(MODULE.PreflightFailure):
                    MODULE.validate_target(value)

    def test_cli_limits_parallelism_and_cache_modes(self) -> None:
        common = [
            "--project-root", "/project", "--expected-project-head", "c" * 40,
            "--hol4-root", "/hol4", "--expected-hol4-head", "a" * 40,
            "--cakeml-root", "/cakeml", "--expected-cakeml-head", "b" * 40,
            "--target-directory", "compiler/bootstrap/translation",
            "--target", "fooTheory.uo", "--mt", "1",
            "--cache-mode", "cache-dir-mtime",
        ]
        parsed = MODULE.parse_arguments([*common, "--jobs", "2"])
        self.assertEqual((parsed.jobs, parsed.mt), (2, 1))
        for replacement in (
            [*common, "--jobs", "3"],
            [item for item in common if item != "cache-dir-mtime"]
            + ["bad-mode", "--jobs", "1"],
        ):
            with self.subTest(arguments=replacement):
                with self.assertRaises(SystemExit):
                    MODULE.parse_arguments(replacement)

    def test_core_argument_validation_rejects_boolean_integers(self) -> None:
        base = argparse.Namespace(
            jobs=1, mt=1, cache_mode="cache-dir-mtime",
            target=MODULE.V1_TARGET,
            target_directory=MODULE.V1_TARGET_DIRECTORY,
        )
        MODULE.validate_arguments(base)
        for field, value in (("jobs", True), ("mt", True)):
            altered = argparse.Namespace(**vars(base))
            setattr(altered, field, value)
            with self.subTest(field=field):
                with self.assertRaises(MODULE.PreflightFailure):
                    MODULE.validate_arguments(altered)
        for field, value in (
            ("target", "otherTheory.uo"),
            ("target_directory", "compiler/benchmarks"),
        ):
            altered = argparse.Namespace(**vars(base))
            setattr(altered, field, value)
            with self.subTest(field=field):
                with self.assertRaises(MODULE.PreflightFailure):
                    MODULE.validate_arguments(altered)

    def test_receipt_namespace_digest_excludes_local_paths(self) -> None:
        namespace = {
            "schema": MODULE.NAMESPACE_SCHEMA,
            "build": {"jobs": 1, "mt": 1},
        }
        digest = MODULE.compact_sha256(namespace)
        receipt_a = {
            "namespace": namespace,
            "namespace_sha256": digest,
            "local_paths": {"hol4_root": "/one"},
        }
        receipt_b = {
            "namespace": namespace,
            "namespace_sha256": digest,
            "local_paths": {"hol4_root": "/two"},
        }
        self.assertNotEqual(json.dumps(receipt_a), json.dumps(receipt_b))
        self.assertEqual(
            receipt_a["namespace_sha256"], receipt_b["namespace_sha256"],
        )

    def test_stable_file_record_detects_change_during_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "file"
            path.write_bytes(b"stable")
            identity = MODULE.stable_file_record(path, "fixture")
            self.assertEqual(identity["bytes"], 6)
            self.assertEqual(identity["sha256"], hashlib.sha256(b"stable").hexdigest())
            actual = path.stat()
            changed = list(MODULE._stable_stat(actual))
            changed[6] += 1
            fake_after = mock.Mock()
            for field, value in zip(
                ("st_dev", "st_ino", "st_mode", "st_nlink", "st_uid", "st_gid",
                 "st_size", "st_mtime_ns", "st_ctime_ns"),
                changed,
            ):
                setattr(fake_after, field, value)
            with mock.patch.object(MODULE.os, "fstat", side_effect=[actual, fake_after]):
                with self.assertRaisesRegex(MODULE.PreflightFailure, "changed"):
                    MODULE.stable_file_record(path, "fixture")

    def test_target_directory_is_relative_existing_and_canonical(self) -> None:
        root = Path(os.path.realpath("/tmp"))
        self.assertEqual(MODULE.validate_target_directory(root, "."), ".")
        for value in ("", "/absolute", "../escape", "a/../escape", "missing"):
            with self.subTest(value=value):
                with self.assertRaises(MODULE.PreflightFailure):
                    MODULE.validate_target_directory(root, value)

    def test_git_root_must_be_toplevel_and_cakeml_ignored_state_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            subprocess.run(["/usr/bin/git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["/usr/bin/git", "-C", str(root), "config", "user.email", "test@example"],
                check=True,
            )
            subprocess.run(
                ["/usr/bin/git", "-C", str(root), "config", "user.name", "Test"],
                check=True,
            )
            (root / ".gitignore").write_text("*.o\n", encoding="utf-8")
            (root / "tracked").write_text("tracked\n", encoding="utf-8")
            subprocess.run(
                ["/usr/bin/git", "-C", str(root), "add", ".gitignore", "tracked"],
                check=True,
            )
            subprocess.run(
                ["/usr/bin/git", "-C", str(root), "commit", "-qm", "fixture"],
                check=True,
            )
            head = subprocess.check_output(
                ["/usr/bin/git", "-C", str(root), "rev-parse", "HEAD"], text=True,
            ).strip()
            clean = MODULE.authenticate_git_root(
                root, head, "fixture", require_no_ignored=True,
            )
            self.assertEqual(clean["ignored_artifacts"]["count"], 0)
            (root / "tracked").chmod(0o600)
            mode_changed = MODULE.authenticate_git_root(
                root, head, "fixture", require_no_ignored=True,
            )
            self.assertNotEqual(
                clean["worktree_shape"]["ordered_tracked_content_sha256"],
                mode_changed["worktree_shape"]["ordered_tracked_content_sha256"],
            )
            (root / "tracked").chmod(0o644)
            subprocess.run(
                ["/usr/bin/git", "-C", str(root), "update-index",
                 "--assume-unchanged", "tracked"],
                check=True,
            )
            (root / "tracked").write_text("forged\n", encoding="utf-8")
            with self.assertRaisesRegex(MODULE.PreflightFailure, "index flag"):
                MODULE.authenticate_git_root(
                    root, head, "fixture", require_no_ignored=True,
                )
            (root / "tracked").write_text("tracked\n", encoding="utf-8")
            subprocess.run(
                ["/usr/bin/git", "-C", str(root), "update-index",
                 "--no-assume-unchanged", "tracked"],
                check=True,
            )
            (root / "nested").mkdir()
            with self.assertRaisesRegex(MODULE.PreflightFailure, "Git top level"):
                MODULE.authenticate_git_root(
                    root / "nested", head, "fixture", require_no_ignored=True,
                )
            with self.assertRaisesRegex(MODULE.PreflightFailure, "extra directory"):
                MODULE.authenticate_git_root(
                    root, head, "fixture", require_no_ignored=True,
                )
            (root / "nested").rmdir()
            (root / "ignored.o").write_bytes(b"ignored\n")
            with self.assertRaisesRegex(MODULE.PreflightFailure, "ignored artifacts"):
                MODULE.authenticate_git_root(
                    root, head, "fixture", require_no_ignored=True,
                )
            bound = MODULE.authenticate_git_root(
                root, head, "fixture", require_no_ignored=False,
            )
            self.assertEqual(
                bound["ignored_artifacts"]["policy"],
                "explicit-toolchain-closure-only-v1",
            )

    def test_toolchain_tree_binds_regular_files_and_symlink_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            tree = root / "tree"
            tree.mkdir()
            target = root / "target"
            target.write_bytes(b"target\n")
            (tree / "regular").write_bytes(b"regular\n")
            (tree / "link").symlink_to(target)
            first = MODULE.toolchain_tree_inventory(tree, root, "fixture tree")
            self.assertEqual(first["entry_count"], 2)
            target.write_bytes(b"changed\n")
            second = MODULE.toolchain_tree_inventory(tree, root, "fixture tree")
            self.assertNotEqual(
                first["ordered_inventory_sha256"],
                second["ordered_inventory_sha256"],
            )

    def test_toolchain_tree_normalizes_relocated_absolute_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            inventories = []
            for name in ("one", "two"):
                root = (Path(temporary) / name).resolve()
                tree = root / "sigobj"
                target = root / "src/target"
                target.parent.mkdir(parents=True)
                tree.mkdir()
                target.write_bytes(b"same\n")
                (tree / "link").symlink_to(target)
                inventories.append(
                    MODULE.toolchain_tree_inventory(tree, root, "fixture tree")
                )
            self.assertEqual(inventories[0], inventories[1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
