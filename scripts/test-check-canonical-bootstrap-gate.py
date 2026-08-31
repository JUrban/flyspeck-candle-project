#!/usr/bin/python3

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SUBJECT_PATH = Path(__file__).with_name("check-canonical-bootstrap-gate.py")
CONTROLLER_PATH = Path(__file__).with_name("run-canonical-bootstrap-replay.sh")
SPEC = importlib.util.spec_from_file_location("canonical_bootstrap_gate", SUBJECT_PATH)
assert SPEC is not None and SPEC.loader is not None
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


class CanonicalBootstrapGateTests(unittest.TestCase):
    def git(self, root: Path, *arguments: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *arguments], check=True,
            text=True, stdout=subprocess.PIPE,
        ).stdout.strip()

    def commit(self, root: Path, message: str) -> str:
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run([
            "git", "-C", str(root), "-c", "user.name=Gate Test", "-c",
            "user.email=gate@example.invalid", "commit", "-qm", message,
        ], check=True)
        return self.git(root, "rev-parse", "HEAD")

    def make_git_root(self, parent: Path, name: str) -> tuple[Path, str]:
        root = parent / name
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / "tracked").write_text(name, encoding="ascii")
        return root, self.commit(root, "fixture")

    def make_project(self, parent: Path) -> tuple[Path, str]:
        project, _initial = self.make_git_root(parent, "project")
        scripts = project / "scripts"
        scripts.mkdir()
        shutil.copy2(CONTROLLER_PATH, scripts / CONTROLLER_PATH.name)
        shutil.copy2(SUBJECT_PATH, scripts / SUBJECT_PATH.name)
        return project, self.commit(project, "authenticated replay tools")

    def make_cakeml(self, parent: Path) -> tuple[Path, str]:
        root = parent / "cakeml"
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / "tracked").write_text("cakeml", encoding="ascii")
        (root / ".gitignore").write_text(
            "misc/cakeml-heap\n"
            "cv_translator/cake_compile_heap\n"
            ".hol/\n"
            "compiler/bootstrap/compilation/x64/64/cake.S\n"
            "compiler/bootstrap/compilation/x64/64/config_enc_str.txt\n",
            encoding="ascii",
        )
        for _name, directory, _target, _receipt, _log in subject.REPLAY_STAGES:
            (root / directory).mkdir(parents=True, exist_ok=True)
        return root, self.commit(root, "pristine CakeML fixture")

    def write_receipts_and_products(self, replay: Path, cakeml: Path,
                                    hol4: Path) -> None:
        for _name, _directory, target, receipt, log in subject.REPLAY_STAGES:
            values = [
                f'"{hol4}/bin/Holmake -j1 --mt=1 {target}"',
                "1.00", "0.10", "100%", "0:01.10",
                *("0" for _ in range(16)), "4096", "0",
            ]
            self.assertEqual(len(values), len(subject.TIME_FIELDS))
            (replay / receipt).write_text("".join(
                f"\t{field}: {value}\n"
                for field, value in zip(subject.TIME_FIELDS, values, strict=True)
            ), encoding="utf-8")
            (replay / log).write_text(f"completed {target}\n", encoding="utf-8")
        for relative in subject.CAKEML_POSTCONDITIONS:
            path = cakeml / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"output {relative}\n", encoding="ascii")

    def fixture(self, parent: Path):
        candle, candle_head = self.make_git_root(parent, "candle")
        cakeml, cakeml_head = self.make_cakeml(parent)
        hol4, hol4_head = self.make_git_root(parent, "hol4")
        project, project_head = self.make_project(parent)
        replay = parent / "replay"
        replay.mkdir()

        identity_process = subprocess.Popen(
            ["/bin/sleep", "60"], start_new_session=True,
        )
        try:
            controller_identity = subject.read_live_process_identity(
                Path("/proc"), identity_process.pid,
            )
        finally:
            identity_process.terminate()
            identity_process.wait(timeout=5)

        sidecars = {
            "stage": "complete\n",
            "started_utc": "2026-08-28T23:59:59Z\n",
            "finished_utc": "2026-08-29T00:00:00Z\n",
            "controller_pid": f"{controller_identity['pid']}\n",
            "controller_pgid": f"{controller_identity['pgid']}\n",
            "controller_start_ticks": f"{controller_identity['start_ticks']}\n",
            "controller_project_root": f"{project}\n",
            "controller_project_head": f"{project_head}\n",
            "controller_script_relative": f"{subject.REPLAY_CONTROLLER_RELATIVE}\n",
            "gate_script_relative": f"{subject.REPLAY_GATE_RELATIVE}\n",
            "cakeml_root": f"{cakeml}\n",
            "cakeml_head": f"{cakeml_head}\n",
            "hol4_root": f"{hol4}\n",
            "hol4_head": f"{hol4_head}\n",
            "cakeml_ignored_products_preflight": "none\n",
            "build_parallelism": "-j1 --mt=1\n",
            "address_space_limit_kib": "117964800\n",
        }
        for relative, value in sidecars.items():
            (replay / relative).write_text(value, encoding="utf-8")
        for source_name, digest_name in (
            (CONTROLLER_PATH.name, "controller_script_sha256"),
            (SUBJECT_PATH.name, "gate_script_sha256"),
        ):
            value = (project / "scripts" / source_name).read_bytes()
            (replay / digest_name).write_text(
                f"{hashlib.sha256(value).hexdigest()}\n", encoding="ascii",
            )

        preflight = subject.build_pristine_preflight(
            project, project_head, cakeml, cakeml_head, hol4, hol4_head,
            controller_identity, require_pristine=True,
        )
        (replay / subject.PRISTINE_PREFLIGHT_RELATIVE).write_bytes(
            subject.canonical_json_bytes(preflight),
        )
        self.write_receipts_and_products(replay, cakeml, hol4)
        manifest = subject.build_terminal_manifest(
            replay, project, project_head, cakeml, cakeml_head, hol4, hol4_head,
        )
        manifest_bytes = subject.canonical_json_bytes(manifest)
        (replay / subject.TERMINAL_MANIFEST_RELATIVE).write_bytes(manifest_bytes)
        manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()

        proc = parent / "proc"
        proc.mkdir()
        (proc / "meminfo").write_text(
            "MemAvailable: 130000000 kB\n", encoding="ascii",
        )
        return type("Arguments", (), {
            "replay_root": replay,
            "replay_controller_pid": controller_identity["pid"],
            "replay_process_group": controller_identity["pgid"],
            "replay_controller_start_ticks": controller_identity["start_ticks"],
            "terminal_manifest_sha256": manifest_digest,
            "candle_root": candle,
            "candle_head": candle_head,
            "cakeml_root": cakeml,
            "cakeml_head": cakeml_head,
            "hol4_root": hol4,
            "hol4_head": hol4_head,
            "attempt_root": parent / "attempt-001",
            "minimum_mem_available_gib": 120,
            "proc_root": proc,
            "project_root": project,
            "project_head": project_head,
        })()

    def assert_gate_rejects(self, arguments, pattern: str) -> None:
        with self.assertRaisesRegex(subject.GateError, pattern):
            subject.validate_gate(arguments)

    def test_complete_fresh_gate_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            result = subject.validate_gate(arguments)
            self.assertEqual(result["gate"], "canonical-cakeml-bootstrap-ready")
            self.assertEqual(result["live_holmake_pids"], [])
            self.assertEqual(result["live_replay_process_group_members"], [])

    def test_incomplete_replay_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            (arguments.replay_root / "stage").write_text(
                "compiler64ProgTheory.uo\n", encoding="ascii",
            )
            self.assert_gate_rejects(arguments, "not completed")

    def test_v1_publication_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            preflight_path = (
                arguments.replay_root / subject.PRISTINE_PREFLIGHT_RELATIVE
            )
            preflight, _ = subject.load_canonical_json(
                preflight_path, "test pristine preflight",
            )
            preflight["schema"] = 1
            preflight["kind"] = "canonical-cakeml-cold-pristine-preflight-v1"
            preflight_path.write_bytes(subject.canonical_json_bytes(preflight))
            self.assert_gate_rejects(arguments, "preflight authority mismatch")

    def test_live_holmake_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            process = arguments.proc_root / "123"
            process.mkdir()
            (process / "comm").write_text("Holmake\n", encoding="ascii")
            (process / "exe").symlink_to("/tool/Holmake")
            self.assert_gate_rejects(arguments, "Holmake is still live")

    def test_existing_attempt_root_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            arguments.attempt_root.mkdir()
            self.assert_gate_rejects(arguments, "already exists")

    def test_nonempty_ignored_product_preflight_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            (arguments.replay_root / "cakeml_ignored_products_preflight").write_text(
                "present\n", encoding="ascii",
            )
            self.assert_gate_rejects(arguments, "preflight mismatch")

    def test_replay_controller_digest_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            (arguments.replay_root / "controller_script_sha256").write_text(
                f"{'0' * 64}\n", encoding="ascii",
            )
            self.assert_gate_rejects(arguments, "digest mismatch")

    def test_replay_gate_digest_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            (arguments.replay_root / "gate_script_sha256").write_text(
                f"{'0' * 64}\n", encoding="ascii",
            )
            self.assert_gate_rejects(arguments, "digest mismatch")

    def test_wrong_recorded_roots_and_heads_fail(self):
        cases = (
            ("controller_project_root", "/wrong/project\n"),
            ("controller_project_head", f"{'0' * 40}\n"),
            ("cakeml_root", "/wrong/cakeml\n"),
            ("cakeml_head", f"{'1' * 40}\n"),
            ("hol4_root", "/wrong/hol4\n"),
            ("hol4_head", f"{'2' * 40}\n"),
        )
        for sidecar, replacement in cases:
            with self.subTest(sidecar=sidecar), tempfile.TemporaryDirectory() as temporary:
                arguments = self.fixture(Path(temporary))
                (arguments.replay_root / sidecar).write_text(
                    replacement, encoding="ascii",
                )
                self.assert_gate_rejects(arguments, f"{sidecar} mismatch")

    def test_nonzero_time_receipt_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            receipt = arguments.replay_root / subject.TIME_RECEIPTS[3]
            receipt.write_text(
                receipt.read_text(encoding="utf-8").replace(
                    "\tExit status: 0", "\tExit status: 1",
                ), encoding="utf-8",
            )
            self.assert_gate_rejects(arguments, "exit zero")

    def test_valid_receipt_splice_fails_manifest_join(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            receipt = arguments.replay_root / subject.TIME_RECEIPTS[1]
            receipt.write_text(
                receipt.read_text(encoding="utf-8").replace(
                    "\tUser time (seconds): 1.00",
                    "\tUser time (seconds): 2.00",
                ), encoding="utf-8",
            )
            self.assert_gate_rejects(arguments, "terminal manifest")

    def test_product_splice_fails_manifest_join(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            product = arguments.cakeml_root / subject.CAKEML_POSTCONDITIONS[4]
            product.write_text("spliced product\n", encoding="ascii")
            self.assert_gate_rejects(arguments, "terminal manifest")

    def test_assume_unchanged_tracked_drift_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            subprocess.run([
                "git", "-C", str(arguments.cakeml_root), "update-index",
                "--assume-unchanged", "tracked",
            ], check=True)
            (arguments.cakeml_root / "tracked").write_text(
                "hidden drift", encoding="ascii",
            )
            self.assert_gate_rejects(arguments, "assume-unchanged")

    def test_skip_worktree_tracked_drift_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            subprocess.run([
                "git", "-C", str(arguments.cakeml_root), "update-index",
                "--skip-worktree", "tracked",
            ], check=True)
            (arguments.cakeml_root / "tracked").write_text(
                "hidden drift", encoding="ascii",
            )
            self.assert_gate_rejects(arguments, "skip-worktree")

    def test_tracked_git_mode_drift_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            (arguments.cakeml_root / "tracked").chmod(0o755)
            self.assert_gate_rejects(arguments, "Git mode mismatch")

    def test_tracked_path_type_drift_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            tracked = arguments.cakeml_root / "tracked"
            tracked.unlink()
            tracked.symlink_to(".gitignore")
            self.assert_gate_rejects(arguments, "ordinary file")

    def test_orphaned_replay_process_group_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            process = arguments.proc_root / "123"
            process.mkdir()
            (process / "stat").write_text(
                f"123 (child with spaces) S 1 {arguments.replay_process_group} "
                f"{arguments.replay_process_group} 0 0 0 0 0 0 0 0 "
                "0 0 0 0 0 0 0 100\n",
                encoding="ascii",
            )
            self.assert_gate_rejects(arguments, "process group")

    def test_symlinked_time_receipt_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            receipt = arguments.replay_root / subject.TIME_RECEIPTS[0]
            target = arguments.replay_root / "relabeled-time"
            receipt.rename(target)
            receipt.symlink_to(target.name)
            self.assert_gate_rejects(arguments, "ordinary")

    def test_truncated_time_receipt_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            receipt = arguments.replay_root / subject.TIME_RECEIPTS[0]
            receipt.write_text("".join(
                receipt.read_text(encoding="utf-8").splitlines(keepends=True)[:2]
            ), encoding="utf-8")
            self.assert_gate_rejects(arguments, "field count")

    def test_malformed_time_numeric_field_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            receipt = arguments.replay_root / subject.TIME_RECEIPTS[0]
            receipt.write_text(
                receipt.read_text(encoding="utf-8").replace(
                    "\tUser time (seconds): 1.00",
                    "\tUser time (seconds): one",
                ), encoding="utf-8",
            )
            self.assert_gate_rejects(arguments, "CPU fields")

    def test_reordered_time_fields_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            receipt = arguments.replay_root / subject.TIME_RECEIPTS[0]
            lines = receipt.read_text(encoding="utf-8").splitlines(keepends=True)
            lines[1], lines[2] = lines[2], lines[1]
            receipt.write_text("".join(lines), encoding="utf-8")
            self.assert_gate_rejects(arguments, "field mismatch")

    def test_trailing_time_junk_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            receipt = arguments.replay_root / subject.TIME_RECEIPTS[0]
            with receipt.open("a", encoding="utf-8") as output:
                output.write("trailing junk\n")
            self.assert_gate_rejects(arguments, "field count")

    def test_pinned_replay_pid_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            arguments.replay_controller_pid = 888888
            self.assert_gate_rejects(arguments, "pinned launch")

    def test_pinned_replay_start_ticks_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            arguments.replay_controller_start_ticks += 1
            self.assert_gate_rejects(arguments, "pinned launch")

    def test_pinned_manifest_digest_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            arguments.terminal_manifest_sha256 = "0" * 64
            self.assert_gate_rejects(arguments, "pinned publication digest")

    def test_coordinated_direct_rebuild_fails_pinned_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            receipt = arguments.replay_root / subject.TIME_RECEIPTS[1]
            receipt_lines = receipt.read_text(encoding="utf-8").splitlines()
            receipt_lines[1] = "\tUser time (seconds): 999.00"
            receipt.write_text("\n".join(receipt_lines) + "\n", encoding="utf-8")
            product = arguments.cakeml_root / subject.CAKEML_POSTCONDITIONS[4]
            product.write_text("coordinated replacement\n", encoding="ascii")
            manifest = subject.build_terminal_manifest(
                arguments.replay_root, arguments.project_root,
                arguments.project_head, arguments.cakeml_root,
                arguments.cakeml_head, arguments.hol4_root,
                arguments.hol4_head,
            )
            (arguments.replay_root / subject.TERMINAL_MANIFEST_RELATIVE).write_bytes(
                subject.canonical_json_bytes(manifest),
            )
            self.assert_gate_rejects(arguments, "pinned publication digest")

    def test_fifo_small_file_fails_without_reading(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fifo"
            os.mkfifo(path)
            with self.assertRaisesRegex(subject.GateError, "ordinary file"):
                subject.stable_file_bytes(path, "hostile FIFO")

    def test_oversize_json_fails_at_stat_cap(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "huge.json"
            with path.open("wb") as output:
                output.truncate(subject.SMALL_FILE_MAX_BYTES + 1)
            with self.assertRaisesRegex(subject.GateError, "exceeds size cap"):
                subject.load_canonical_json(path, "hostile JSON")

    def test_never_live_terminal_publisher_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            arguments = self.fixture(Path(temporary))
            (arguments.replay_root / subject.TERMINAL_MANIFEST_RELATIVE).unlink()
            completed = subprocess.run(
                [
                    "/usr/bin/python3", "-I", "-S",
                    str(arguments.project_root / subject.REPLAY_GATE_RELATIVE),
                    "--internal-publish-manifest",
                    "--replay-root", str(arguments.replay_root),
                    "--controller-pid", str(arguments.replay_controller_pid),
                    "--controller-pgid", str(arguments.replay_process_group),
                    "--project-root", str(arguments.project_root),
                    "--project-head", arguments.project_head,
                    "--cakeml-root", str(arguments.cakeml_root),
                    "--cakeml-head", arguments.cakeml_head,
                    "--hol4-root", str(arguments.hol4_root),
                    "--hol4-head", arguments.hol4_head,
                ],
                check=False, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("caller is not the recorded controller", completed.stderr)
            self.assertFalse(
                (arguments.replay_root / subject.TERMINAL_MANIFEST_RELATIVE).exists(),
            )


class CanonicalBootstrapControllerTests(unittest.TestCase):
    git = CanonicalBootstrapGateTests.git
    commit = CanonicalBootstrapGateTests.commit
    make_git_root = CanonicalBootstrapGateTests.make_git_root
    make_project = CanonicalBootstrapGateTests.make_project
    make_cakeml = CanonicalBootstrapGateTests.make_cakeml

    def make_fake_hol4(self, parent: Path) -> tuple[Path, str]:
        hol4 = parent / "hol4"
        hol4.mkdir()
        subprocess.run(["git", "init", "-q", str(hol4)], check=True)
        holmake = hol4 / "bin" / "Holmake"
        holmake.parent.mkdir()
        holmake.write_text("""#!/usr/bin/env bash
set -euo pipefail
[[ ! -e /proc/self/fd/9 ]]
target=${3:?missing-target}
root=$PWD
while [[ $root != / && ! -f $root/FAKE_CAKEML_ROOT ]]; do
  root=$(/usr/bin/dirname "$root")
done
[[ -f $root/FAKE_CAKEML_ROOT ]]
case "$target" in
  cakeml-heap)
    [[ $PWD == "$root/misc" ]]
    /usr/bin/printf base >"$root/misc/cakeml-heap"
    ;;
  cake_compile_heap)
    [[ -s $root/misc/cakeml-heap ]]
    /usr/bin/printf compiler >"$root/cv_translator/cake_compile_heap"
    ;;
  compiler64ProgTheory.uo)
    [[ -s $root/cv_translator/cake_compile_heap ]]
    /usr/bin/mkdir -p "$root/compiler/bootstrap/translation/.hol/objs"
    /usr/bin/printf translation >\
      "$root/compiler/bootstrap/translation/.hol/objs/compiler64ProgTheory.uo"
    ;;
  x64BootstrapTheory.uo)
    [[ -s $root/compiler/bootstrap/translation/.hol/objs/compiler64ProgTheory.uo ]]
    /usr/bin/mkdir -p \
      "$root/compiler/bootstrap/compilation/x64/64/.hol/objs"
    /usr/bin/printf x64 >\
      "$root/compiler/bootstrap/compilation/x64/64/.hol/objs/x64BootstrapTheory.uo"
    /usr/bin/printf assembly >\
      "$root/compiler/bootstrap/compilation/x64/64/cake.S"
    /usr/bin/printf config >\
      "$root/compiler/bootstrap/compilation/x64/64/config_enc_str.txt"
    ;;
  x64BootstrapProofTheory.uo)
    [[ -s $root/compiler/bootstrap/compilation/x64/64/.hol/objs/x64BootstrapTheory.uo ]]
    [[ -s $root/compiler/bootstrap/compilation/x64/64/cake.S ]]
    [[ -s $root/compiler/bootstrap/compilation/x64/64/config_enc_str.txt ]]
    /usr/bin/mkdir -p \
      "$root/compiler/bootstrap/compilation/x64/64/proofs/.hol/objs"
    /usr/bin/printf proof >\
      "$root/compiler/bootstrap/compilation/x64/64/proofs/.hol/objs/x64BootstrapProofTheory.uo"
    ;;
  *) exit 90 ;;
esac
/usr/bin/printf 'completed %s\\n' "$target"
""", encoding="ascii")
        holmake.chmod(0o755)
        return hol4, self.commit(hol4, "fake Holmake")

    def controller_fixture(self, parent: Path):
        project, project_head = self.make_project(parent)
        cakeml, cakeml_head = self.make_cakeml(parent)
        (cakeml / "FAKE_CAKEML_ROOT").write_text("fixture\n", encoding="ascii")
        cakeml_head = self.commit(cakeml, "fake replay marker")
        hol4, hol4_head = self.make_fake_hol4(parent)
        return project, project_head, cakeml, cakeml_head, hol4, hol4_head

    def run_controller(self, project: Path, run_root: Path, cakeml: Path,
                       cakeml_head: str, hol4: Path, hol4_head: str):
        return subprocess.run(
            ["unshare", "-Urpf", "--mount-proc", "/bin/bash", "-c",
             'setsid "$@" & child=$!; wait "$child"', "controller-wrapper",
             str(project / subject.REPLAY_CONTROLLER_RELATIVE), str(run_root),
             str(cakeml), cakeml_head, str(hol4), hol4_head],
            check=False, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, start_new_session=True,
            env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
        )

    def test_fake_holmake_enforces_base_before_four_stage_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            (project, _project_head, cakeml, cakeml_head,
             hol4, hol4_head) = self.controller_fixture(parent)
            run_root = parent / "cold-replay"
            completed = self.run_controller(
                project, run_root, cakeml, cakeml_head, hol4, hol4_head,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertRegex(completed.stdout, r"\A[0-9a-f]{64}\n\Z")
            manifest, _value = subject.load_canonical_json(
                run_root / subject.TERMINAL_MANIFEST_RELATIVE,
                "test terminal manifest",
            )
            self.assertEqual(
                [stage["name"] for stage in manifest["stages"]],
                [stage[0] for stage in subject.REPLAY_STAGES],
            )
            self.assertEqual(len(manifest["products"]), 7)
            self.assertEqual(
                [stage["index"] for stage in manifest["stages"]],
                list(range(5)),
            )
            self.assertEqual(
                manifest["controller_identity"],
                {
                    "pid": int((run_root / "controller_pid").read_text()),
                    "pgid": int((run_root / "controller_pgid").read_text()),
                    "start_ticks": int(
                        (run_root / "controller_start_ticks").read_text()
                    ),
                },
            )
            self.assertEqual(manifest["schema"], 2)
            self.assertEqual(manifest["kind"], subject.MANIFEST_KIND)
            self.assertGreater(manifest["controller_identity"]["start_ticks"], 0)

    def test_stale_ignored_cache_rejected_before_run_root_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            (project, _project_head, cakeml, cakeml_head,
             hol4, hol4_head) = self.controller_fixture(parent)
            (cakeml / "misc" / "cakeml-heap").write_text(
                "stale\n", encoding="ascii",
            )
            run_root = parent / "must-not-exist"
            completed = self.run_controller(
                project, run_root, cakeml, cakeml_head, hol4, hol4_head,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("ignored build products", completed.stderr)
            self.assertFalse(run_root.exists())

    def test_live_start_ticks_splice_prevents_terminal_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            (project, _project_head, cakeml, cakeml_head,
             hol4, _hol4_head) = self.controller_fixture(parent)
            holmake = hol4 / "bin" / "Holmake"
            source = holmake.read_text(encoding="ascii")
            holmake.write_text(
                source.replace(
                    "  x64BootstrapProofTheory.uo)\n",
                    "  x64BootstrapProofTheory.uo)\n"
                    "    /usr/bin/printf '999999999999\\n' >"
                    "\"$root/../cold-replay/controller_start_ticks\"\n",
                ),
                encoding="ascii",
            )
            hol4_head = self.commit(hol4, "splice controller start ticks")
            run_root = parent / "cold-replay"
            completed = self.run_controller(
                project, run_root, cakeml, cakeml_head, hol4, hol4_head,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                "terminal publisher differs from authenticated controller identity",
                completed.stderr,
            )
            self.assertFalse(
                (run_root / subject.TERMINAL_MANIFEST_RELATIVE).exists(),
            )
            self.assertNotEqual(
                (run_root / "stage").read_text(encoding="ascii"), "complete\n",
            )

    def test_dead_controller_cannot_republish_coordinated_splice(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            (project, project_head, cakeml, cakeml_head,
             hol4, hol4_head) = self.controller_fixture(parent)
            run_root = parent / "cold-replay"
            completed = self.run_controller(
                project, run_root, cakeml, cakeml_head, hol4, hol4_head,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            receipt = run_root / subject.TIME_RECEIPTS[1]
            receipt_lines = receipt.read_text(encoding="utf-8").splitlines()
            receipt_lines[1] = "\tUser time (seconds): 999.00"
            receipt.write_text("\n".join(receipt_lines) + "\n", encoding="utf-8")
            product = cakeml / subject.CAKEML_POSTCONDITIONS[4]
            product.write_text("coordinated replacement\n", encoding="ascii")
            (run_root / subject.TERMINAL_MANIFEST_RELATIVE).unlink()

            replacement = subprocess.run(
                [
                    "/usr/bin/python3", "-I", "-S",
                    str(project / subject.REPLAY_GATE_RELATIVE),
                    "--internal-publish-manifest",
                    "--replay-root", str(run_root),
                    "--controller-pid",
                    (run_root / "controller_pid").read_text().strip(),
                    "--controller-pgid",
                    (run_root / "controller_pgid").read_text().strip(),
                    "--project-root", str(project),
                    "--project-head", project_head,
                    "--cakeml-root", str(cakeml),
                    "--cakeml-head", cakeml_head,
                    "--hol4-root", str(hol4),
                    "--hol4-head", hol4_head,
                ],
                check=False, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
            )
            self.assertNotEqual(replacement.returncode, 0)
            self.assertIn(
                "caller is not the recorded controller", replacement.stderr,
            )
            self.assertFalse(
                (run_root / subject.TERMINAL_MANIFEST_RELATIVE).exists(),
            )

    def test_arbitrary_shell_cannot_recreate_publications(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            (project, project_head, cakeml, cakeml_head,
             hol4, hol4_head) = self.controller_fixture(parent)
            run_root = parent / "cold-replay"
            completed = self.run_controller(
                project, run_root, cakeml, cakeml_head, hol4, hol4_head,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            (cakeml / subject.CAKEML_POSTCONDITIONS[4]).write_text(
                "attacker replacement\n", encoding="ascii",
            )
            for relative in (
                "controller_start_ticks", subject.PRISTINE_PREFLIGHT_RELATIVE,
                subject.TERMINAL_MANIFEST_RELATIVE,
            ):
                (run_root / relative).unlink()

            attacker = parent / "attacker-shell.sh"
            attacker.write_text(
                "#!/bin/bash\n"
                "set -euo pipefail\n"
                "controller=$1\n"
                "shift\n"
                "exec 9<\"$controller\"\n"
                "pgid=$(/usr/bin/ps -o pgid= -p \"$$\")\n"
                "pgid=${pgid//[[:space:]]/}\n"
                "/usr/bin/printf '%s\\n' \"$$\" >\"$1/controller_pid\"\n"
                "/usr/bin/printf '%s\\n' \"$pgid\" >\"$1/controller_pgid\"\n"
                "/usr/bin/python3 -I -S \"$2\" "
                "--internal-write-preflight "
                "--replay-root \"$1\" --controller-pid \"$$\" "
                "--controller-pgid \"$pgid\" "
                "--project-root \"$3\" --project-head \"$4\" "
                "--cakeml-root \"$5\" --cakeml-head \"$6\" "
                "--hol4-root \"$7\" --hol4-head \"$8\"\n",
                encoding="ascii",
            )
            attacker.chmod(0o755)
            replacement = subprocess.run(
                [
                    str(attacker),
                    str(project / subject.REPLAY_CONTROLLER_RELATIVE),
                    str(run_root), str(project / subject.REPLAY_GATE_RELATIVE),
                    str(project), project_head, str(cakeml), cakeml_head,
                    str(hol4), hol4_head,
                ],
                check=False, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, start_new_session=True,
                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
            )
            self.assertNotEqual(replacement.returncode, 0)
            self.assertIn(
                "command line differs from canonical invocation",
                replacement.stderr,
            )
            self.assertFalse((run_root / "controller_start_ticks").exists())
            self.assertFalse(
                (run_root / subject.PRISTINE_PREFLIGHT_RELATIVE).exists(),
            )
            self.assertFalse(
                (run_root / subject.TERMINAL_MANIFEST_RELATIVE).exists(),
            )


if __name__ == "__main__":
    unittest.main()
