#!/usr/bin/env python3

import argparse
import importlib.util
import json
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "build-nonpromotable-candle-development.py"
SPEC = importlib.util.spec_from_file_location("development_candle_link", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


class DevelopmentCandleLinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.cakeml = self.root / "cakeml"
        self.candle = self.root / "candle"
        self.hol4 = self.root / "hol4"
        self._make_cakeml_fixture()
        self._make_candle_fixture()
        self._write(self.hol4, "README", "HOL4 fixture\n")
        self.cakeml_commit = self._commit(self.cakeml)
        self.candle_commit = self._commit(self.candle)
        self.hol4_commit = self._commit(self.hol4)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def _write(root: Path, relative: str, data: str) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)

    @staticmethod
    def _commit(root: Path) -> str:
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run([
            "git", "-C", str(root), "-c", "user.name=Test",
            "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture",
        ], check=True)
        return subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True, stdout=subprocess.PIPE, text=True,
        ).stdout.strip()

    def _make_cakeml_fixture(self) -> None:
        self._write(
            self.cakeml, "compiler/bootstrap/compilation/x64/64/cake.S", "old\n",
        )
        self._write(
            self.cakeml,
            "compiler/bootstrap/compilation/x64/64/config_enc_str.txt",
            "config\n",
        )
        self._write(self.cakeml, "candle/prover/candle_boot.ml", "boot\n")
        self._write(
            self.cakeml, "basis/basis_ffi.c",
            "#!/usr/bin/python3\n"
            "import sys\n"
            "if sys.argv[1:] == ['--types']:\n"
            " sys.stderr.write('Option.valOf: a option -> a\\n')\n"
            " sys.stderr.write('Double.fromString: string -> Double.double option\\n')\n"
            "elif sys.argv[1:] == ['--candle-parser-diagnostic-capability-v1']:\n"
            " sys.stdout.write('CANDLE_CAMLPARSER_DIAGNOSTIC_CAPABILITY_V1\\t'"
            "+ 'caml_parser$run\\tstdin-exact-bytes\\tparser-only\\t'"
            "+ 'no-inference\\tno-evaluation\\n')\n"
            "elif sys.argv[1:] == ['--candle']:\n"
            " assert sys.stdin.buffer.read() == "
            "b'let candle_development_smoke = 1;;\\n'\n"
            " sys.stdout.write('# val candle_development_smoke = 1: int\\n# ')\n"
            "else:\n raise SystemExit(2)\n",
        )
        self._write(
            self.cakeml, "compiler/bootstrap/compilation/x64/Makefile",
            "cake:\n\tcp basis_ffi.c cake\n\tchmod +x cake\n",
        )

    def _make_candle_fixture(self) -> None:
        self._write(
            self.candle, "candle/cake.S.patch", "1c1\n< old\n---\n> new\n",
        )
        self._write(
            self.candle, "candle/insulate.py",
            "from pathlib import Path\n"
            "import sys\n"
            "data = Path(sys.argv[1]).read_text()\n"
            "assert 'Option.valOf' in data and 'Double.fromString' in data\n"
            "Path(sys.argv[2]).write_text('generated\\n')\n",
        )

    def arguments(self, name="result") -> argparse.Namespace:
        return argparse.Namespace(
            cakeml_root=self.cakeml,
            cakeml_commit=self.cakeml_commit,
            candle_root=self.candle,
            candle_commit=self.candle_commit,
            hol4_root=self.hol4,
            hol4_commit=self.hol4_commit,
            output_root=self.root / name,
        )

    def test_success_is_immutable_and_explicitly_nonpromotable(self) -> None:
        receipt = subject.run(self.arguments())
        result = self.root / "result"
        self.assertFalse(receipt["promotion_allowed"])
        self.assertFalse(receipt["ordinary_linked_provenance_produced"])
        self.assertEqual(
            receipt["repositories"]["hol4"]["commit"], self.hol4_commit,
        )
        self.assertEqual(receipt["types"]["command"], ["./cake", "--types"])
        self.assertEqual(
            receipt["capability"]["command"],
            ["./cake", subject.CAPABILITY_ARGUMENT],
        )
        self.assertEqual(
            receipt["candle_smoke"]["command"],
            ["/usr/bin/timeout", "30s", "./cake", "--candle"],
        )
        self.assertEqual(
            (result / "candle-smoke.stdin").read_bytes(),
            subject.CANDLE_SMOKE_INPUT,
        )
        self.assertEqual((result / "cake.S").read_text(), "new\n")
        self.assertIn("Option.valOf", (result / "types.txt").read_text())
        self.assertEqual(stat.S_IMODE(result.stat().st_mode), 0o555)
        self.assertEqual(stat.S_IMODE((result / "cake").stat().st_mode), 0o555)
        published = json.loads((result / "DEVELOPMENT-NONPROMOTABLE.json").read_text())
        self.assertEqual(published, receipt)

    def test_dirty_source_is_rejected_before_output(self) -> None:
        (self.candle / "candle/insulate.py").write_text("changed\n")
        with self.assertRaisesRegex(subject.ContractError, "worktree is dirty"):
            subject.run(self.arguments())
        self.assertFalse((self.root / "result").exists())

    def test_wrong_head_is_rejected_before_output(self) -> None:
        arguments = self.arguments()
        arguments.cakeml_commit = "b" * 40
        with self.assertRaisesRegex(subject.ContractError, "HEAD mismatch"):
            subject.run(arguments)
        self.assertFalse((self.root / "result").exists())

    def test_wrong_candle_boot_selection_is_rejected(self) -> None:
        ffi = self.cakeml / "basis/basis_ffi.c"
        ffi.write_text(
            ffi.read_text().replace(
                "sys.stdout.write('# val candle_development_smoke = 1: int\\n# ')",
                "sys.stdout.write('wrong boot\\n')",
            )
        )
        self.cakeml_commit = self._commit(self.cakeml)
        with self.assertRaisesRegex(
            subject.ContractError, "did not select and evaluate the Candle boot",
        ):
            subject.run(self.arguments())
        self.assertFalse((self.root / "result").exists())


if __name__ == "__main__":
    unittest.main()
