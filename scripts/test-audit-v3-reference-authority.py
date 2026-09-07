#!/usr/bin/env python3
"""Focused tests for the V3 reference-authority reviewer."""

import copy
import importlib.util
from pathlib import Path
import unittest


SUBJECT_PATH = Path(__file__).with_name("audit-v3-reference-authority.py")
SPEC = importlib.util.spec_from_file_location("audit_v3_authority", SUBJECT_PATH)
SUBJECT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SUBJECT)


class AuthorityReviewTest(unittest.TestCase):
    @staticmethod
    def diagnostic_result():
        digest = lambda character: character * 64
        return {
            "name": "100/test",
            "status": "PASS",
            "exact_state_status": "exact_theorem_and_state_matched",
            "v3_fingerprints": {
                "status": "exact_theorem_and_state_matched",
                "promotion_eligible": False,
                "s1_evidence": False,
                "serializer": {"sha256": SUBJECT.V3_SERIALIZER_SHA256},
                "theorems": [{
                    "name": "TEST",
                    "theorem": {"sha256": digest("1")},
                    "hypotheses": {"sha256": digest("2")},
                    "conclusion": {"sha256": digest("3")},
                    "global_axioms": {"sha256": digest("4")},
                    "hypothesis_count": 0,
                    "global_axiom_count": 3,
                }],
                "post_state": {
                    "kernel_state": {"sha256": digest("5")},
                    "type_constants": {"sha256": digest("6")},
                    "type_constant_count": 24,
                    "term_constants": {"sha256": digest("7")},
                    "term_constant_count": 360,
                    "definitions": {"sha256": digest("8")},
                    "definition_count": 316,
                    "global_axioms": {"sha256": digest("4")},
                    "global_axiom_count": 3,
                },
            },
        }

    def test_diagnostic_projection_is_exact_approval_identity_shape(self):
        projection = SUBJECT.diagnostic_projection(self.diagnostic_result())
        self.assertEqual(projection["serializer"], {
            "path": "candle/fingerprint_v3.ml",
            "sha256": SUBJECT.V3_SERIALIZER_SHA256,
        })
        self.assertEqual(projection["theorems"][0]["theorem_sha256"], "1" * 64)
        self.assertNotIn("bytes", projection["theorems"][0])
        self.assertEqual(projection["post_state"]["definition_count"], 316)

    def test_diagnostic_rejects_promotion_or_serializer_substitution(self):
        for path, value in (
                (("v3_fingerprints", "promotion_eligible"), True),
                (("v3_fingerprints", "serializer", "sha256"), "0" * 64),
                (("status",), "FAIL")):
            changed = copy.deepcopy(self.diagnostic_result())
            parent = changed
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(SUBJECT.AuditError):
                SUBJECT.diagnostic_projection(changed)

    def test_candidate_projection_remains_unapproved(self):
        identity = SUBJECT.diagnostic_projection(self.diagnostic_result())
        candidate = {"candidate_identities": {
            "status": "observed_uncompared",
            "expected_identities_present": False,
            "approval_sha256": None,
            **identity,
        }}
        self.assertEqual(SUBJECT.candidate_projection(candidate), identity)
        candidate["candidate_identities"]["approval_sha256"] = "0" * 64
        with self.assertRaises(SUBJECT.AuditError):
            SUBJECT.candidate_projection(candidate)


if __name__ == "__main__":
    unittest.main()
