#!/usr/bin/python3

from __future__ import annotations

import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest


SCRIPTS = Path(__file__).parent


def load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fixture = load(
    "pristine_request_generator_fixture",
    SCRIPTS / "test-pristine-direct-reference-protocol.py",
)
subject = load(
    "generate_pristine_direct_reference_request",
    SCRIPTS / "generate-pristine-direct-reference-request.py",
)
subject._PROTOCOL = fixture.subject
protocol = fixture.subject


class PristineRequestGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        semantic, coverage = fixture.common_projections()
        cls.inventory = coverage["original_source_inventory"]
        cls.plan = fixture.make_plan(
            1, "0123456789abcdef" * 4, semantic, coverage,
        )
        # Keep the exact-byte fixture independent of this checkout's path.
        cls.plan["authority"]["repositories"]["project"]["path"] = (
            "/project/reference-project"
        )
        protocol.validate_raw_plan(cls.plan)
        cls.source, cls.request = subject.generate_unapproved_raw_request(
            cls.plan, cls.inventory,
        )
        cls.text = cls.source.decode("ascii")

    def test_exact_deterministic_source_and_raw_request_binding(self) -> None:
        source_again, request_again = subject.generate_unapproved_raw_request(
            copy.deepcopy(self.plan), copy.deepcopy(self.inventory),
        )
        self.assertEqual(source_again, self.source)
        self.assertEqual(request_again, self.request)
        self.assertEqual(
            self.request["request_source"],
            {
                "path": "request.ml",
                "bytes": len(self.source),
                "sha256": hashlib.sha256(self.source).hexdigest(),
            },
        )
        self.assertIs(
            protocol.validate_raw_request(self.request, self.plan), self.request,
        )
        self.assertTrue(self.source.endswith(b"flush stdout;;\n"))
        self.assertEqual(
            hashlib.sha256(self.source).hexdigest(),
            "6abb746184b05fecab39f0e99b35e3e5707c542551e7dd50ae625b48578bb85a",
        )
        for field in ("approval_included", "pft_used", "s2_s3_evidence"):
            self.assertIs(self.request[field], False)

    def test_exact_action_lp_native_and_session_sequence_is_structural(self) -> None:
        positions = [
            self.text.index("CANDLE_PRISTINE_DIRECT_REFERENCE_START_V3"),
            self.text.index("candle_pristine_emit_native \"bootstrap\" None;;"),
            self.text.index("loadt \"/project/reference-flyspeck/"
                            "text_formalization/build/strictbuild.hl\";;"),
            self.text.index("candle_pristine_run_range 0 177;;"),
            self.text.index("module Lp_certificate = struct"),
            self.text.index("candle_pristine_run_range 178 183;;"),
            self.text.index("Verify_all.cert_dir := "),
            self.text.index("candle_pristine_run_range 184 296;;"),
            self.text.index("loadt \"/project/reference-project/"
                            "candle/flyspeck_l2_target.ml\";;"),
            self.text.index("loadt \"/project/reference-project/"
                            "candle/fingerprint.ml\";;"),
            self.text.index("(* Exact ten-line semantic-v3 session"),
            self.text.rindex("CANDLE_PRISTINE_DIRECT_REFERENCE_COMPLETE_V3"),
            self.text.index("flush stdout;;"),
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Array.of_list Build.build_sequence_full;;", self.text)
        self.assertIn("flyspeck_needs target;", self.text)
        self.assertIn("candle_pristine_emit_native \"action\" (Some index);",
                      self.text)
        self.assertIn("CANDLE_PRISTINE_DIRECT_LP_SUCCESS_V3", self.text)
        self.assertIn("if !candle_pristine_lp_success_count <> 39 ||", self.text)
        self.assertIn("\"184\" ^ \"\\t\" ^ string_of_int input_index",
                      self.text)

    def test_semantic_tail_is_exact_direct_ten_record_protocol(self) -> None:
        semantic = [
            line for line in self.text.splitlines()
            if line.startswith(
                'print_endline ("CANDLE_PRISTINE_DIRECT_SEMANTIC_V3"'
            )
        ]
        self.assertEqual(len(semantic), 10)
        self.assertEqual(
            [
                "THEOREM" if '^ "THEOREM" ^' in line else
                "POST_STATE" if '^ "POST_STATE" ^' in line else
                "DEPENDENCY" if '^ "DEPENDENCY" ^' in line else
                "COMPLETE" if '^ "COMPLETE" ^' in line else "unknown"
                for line in semantic
            ],
            ["THEOREM"] * 4 + ["POST_STATE"] + ["DEPENDENCY"] * 4 +
            ["COMPLETE"],
        )
        tail = self.text[self.text.index("(* Exact ten-line semantic-v3 session"):]
        theorem_positions = [tail.index(name) for name in protocol.FINAL_THEOREM_NAMES]
        self.assertEqual(theorem_positions, sorted(theorem_positions))
        self.assertEqual(tail.count("candle_s1_theorem_parts"), 4)
        self.assertEqual(tail.count("Serialization.full_digest_thm"), 4)
        self.assertEqual(tail.count(self.plan["session_nonce"]), 10)
        self.assertIn("candle_s1_kernel_state_parts ();;", tail)
        self.assertNotIn("CANDLE_FINGERPRINT_V2", self.text)
        self.assertNotIn("CANDLE_STATE_FINGERPRINT_V2", self.text)
        self.assertNotIn("candle_s1_emit_fingerprint", self.text)
        self.assertNotIn("candle_s1_emit_state_fingerprint", self.text)
        self.assertNotIn("replace", tail.lower())

    def test_nonce_ordinal_names_and_ocaml_escaping_are_not_aliased(self) -> None:
        plan = copy.deepcopy(self.plan)
        alternate_nonce = "fedcba9876543210" * 4
        plan["session_nonce"] = alternate_nonce
        plan["reference_ordinal"] = 2
        source, request = subject.generate_unapproved_raw_request(
            plan, self.inventory,
        )
        self.assertNotEqual(source, self.source)
        self.assertNotEqual(request["request_source"],
                            self.request["request_source"])
        text = source.decode("ascii")
        self.assertEqual(text.count(alternate_nonce), 11)
        self.assertIn('^ "2" ^ "\\t" ^ "07-final_assembly-through-296"', text)
        self.assertEqual(subject._ocaml_string('a"b\\c\td'),
                         '"a\\"b\\\\c\\td"')
        with self.assertRaisesRegex(
            subject.RequestGenerationError, "forbidden character",
        ):
            subject._ocaml_string("line\nbreak")

    def test_inventory_and_protocol_splices_fail_before_rendering(self) -> None:
        inventory = copy.deepcopy(self.inventory)
        inventory["records"][0]["original_sha256"] = "0" * 64
        inventory["ordered_record_sha256"] = protocol.canonical_sha256(
            inventory["records"]
        )
        with self.assertRaisesRegex(
            subject.RequestGenerationError, "plan authority",
        ):
            subject.generate_unapproved_raw_request(self.plan, inventory)

        duplicate = copy.deepcopy(self.inventory)
        target = duplicate["records"][0]
        victim = duplicate["records"][-1]
        victim["path"] = "zz-generator-hostile/" + Path(target["path"]).name
        victim["key"] = victim["repository"] + ":" + victim["path"]
        victim["original_md5"] = target["original_md5"]
        duplicate["records"].sort(key=lambda record: record["key"])
        for index, record in enumerate(duplicate["records"]):
            record["index"] = index
        duplicate["ordered_record_sha256"] = protocol.canonical_sha256(
            duplicate["records"]
        )
        plan = copy.deepcopy(self.plan)
        record = protocol.content_record(duplicate)
        plan["authority"]["inputs"]["source_inventory"].update(record)
        with self.assertRaisesRegex(
            subject.RequestGenerationError, "ambiguous stock loader identity",
        ):
            subject.generate_unapproved_raw_request(plan, duplicate)

        original = subject._PROTOCOL
        incompatible = ModuleType("incompatible_pristine_protocol")
        incompatible.__dict__.update(protocol.__dict__)
        incompatible.MARKER_CONTRACT = copy.deepcopy(protocol.MARKER_CONTRACT)
        incompatible.MARKER_CONTRACT["nonce_in_every_marker"] = 1
        subject._PROTOCOL = incompatible
        try:
            with self.assertRaisesRegex(
                subject.RequestGenerationError, "marker contract",
            ):
                subject.generate_unapproved_raw_request(
                    self.plan, self.inventory,
                )
        finally:
            subject._PROTOCOL = original

    def test_no_generator_surface_accepts_semantics_or_promotion_inputs(self) -> None:
        self.assertEqual(
            {
                name for name in dir(subject)
                if name.startswith("generate_") or name.startswith("build_")
            },
            {"generate_unapproved_raw_request"},
        )
        for forbidden in (
            b"approved_reference_present", b"promotion_allowed",
            b"cross_runtime_coverage", b"raw_candidate",
        ):
            self.assertNotIn(forbidden, self.source)


if __name__ == "__main__":
    unittest.main()
