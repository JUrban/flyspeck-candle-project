#!/usr/bin/python3

from __future__ import annotations

import copy
import importlib.util
import math
from pathlib import Path
import sys
import unittest


SUBJECT_PATH = Path(__file__).with_name("direct_release_protocol.py")
SPEC = importlib.util.spec_from_file_location("direct_release_protocol", SUBJECT_PATH)
assert SPEC is not None and SPEC.loader is not None
subject = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = subject
SPEC.loader.exec_module(subject)


def fixture() -> tuple[dict, dict]:
    theorem_records = []
    for index, name in enumerate(subject.FINAL_THEOREM_NAMES):
        theorem_records.append({
            "name": name,
            "theorem_sha256": f"{index + 1:x}" * 64,
            "hypotheses_sha256": f"{index + 5:x}" * 64,
            "conclusion_sha256": f"{index + 9:x}" * 64,
            "global_axioms_sha256": "d" * 64,
            "hypothesis_count": 0,
            "global_axiom_count": 3,
        })
    fingerprints = {
        "status": "observed_uncompared",
        "approved_reference_present": False,
        "serializer": {
            "path": subject.FINGERPRINT_SERIALIZER_PATH,
            "sha256": "e" * 64,
        },
        "theorems": theorem_records,
        "post_state": {
            "kernel_state_sha256": "1" * 64,
            "type_constants_sha256": "2" * 64,
            "term_constants_sha256": "3" * 64,
            "definitions_sha256": "4" * 64,
            "global_axioms_sha256": "d" * 64,
            "type_constant_count": 10,
            "term_constant_count": 20,
            "definition_count": 30,
            "global_axiom_count": 3,
        },
    }
    records = [
        {"index": index, "name": name, "full_digest_md5": f"{index + 1:x}" * 32}
        for index, name in enumerate(subject.FINAL_THEOREM_NAMES)
    ]
    dependency = {
        "schema": 1,
        "kind": "candle-flyspeck-dependency-history-observation",
        "policy": subject.DEPENDENCY_HISTORY_POLICY,
        "status": "observed_uncompared",
        "boundary_id": subject.FINAL_BOUNDARY_ID,
        "record_count": 4,
        "ordered_request_sha256": subject.canonical_sha256(
            list(subject.FINAL_THEOREM_NAMES)
        ),
        "ordered_record_sha256": subject.canonical_sha256(records),
        "records": records,
        "approved_reference_present": False,
        "dependency_history_is_kernel_trace": False,
        "pft_used": False,
        "s2_s3_evidence": False,
    }
    return fingerprints, dependency


class DirectReleaseProtocolTests(unittest.TestCase):
    def test_exact_semantic_projection_is_unapproved_and_nonce_free(self) -> None:
        projection = subject.project_authenticated_semantic_observations(*fixture())
        self.assertEqual(
            [record["name"] for record in projection["theorems"]],
            list(subject.FINAL_THEOREM_NAMES),
        )
        self.assertEqual(set(projection), {
            "schema", "kind", "serializer", "theorems", "post_state",
            "dependency_history",
        })

        def reject_nonce_key(value) -> None:
            if isinstance(value, dict):
                self.assertNotIn("nonce", value)
                for nested in value.values():
                    reject_nonce_key(nested)
            elif isinstance(value, list):
                for nested in value:
                    reject_nonce_key(nested)

        reject_nonce_key(projection)
        self.assertIs(subject.validate_semantic_projection(projection), projection)

        fingerprints, dependency = fixture()
        detached = subject.project_authenticated_semantic_observations(
            fingerprints, dependency,
        )
        fingerprints["theorems"][0]["theorem_sha256"] = "0" * 64
        dependency["records"][0]["full_digest_md5"] = "0" * 32
        self.assertNotEqual(
            detached["theorems"][0]["theorem_sha256"], "0" * 64,
        )
        self.assertNotEqual(
            detached["dependency_history"][0]["full_digest_md5"],
            "0" * 32,
        )

    def test_projection_canonical_bytes_round_trip(self) -> None:
        projection = subject.project_authenticated_semantic_observations(*fixture())
        data = subject.canonical_json_bytes(projection)
        self.assertEqual(
            subject.decode_object(data, "projection"), projection,
        )
        self.assertEqual(
            subject.validate_canonical_semantic_projection_bytes(data), projection,
        )
        with self.assertRaisesRegex(subject.ProtocolError, "not canonical"):
            subject.validate_canonical_semantic_projection_bytes(
                subject.canonical_value_bytes(projection)
            )

    def test_duplicate_and_nonfinite_json_reject(self) -> None:
        with self.assertRaisesRegex(subject.ProtocolError, "duplicate JSON key"):
            subject.decode_object(b'{"schema":1,"schema":2}', "value")
        with self.assertRaisesRegex(subject.ProtocolError, "non-finite"):
            subject.decode_object(b'{"value":NaN}', "value")
        with self.assertRaises(ValueError):
            subject.canonical_json_bytes({"value": math.nan})

    def test_theorem_reorder_and_extra_field_reject(self) -> None:
        fingerprints, dependency = fixture()
        fingerprints["theorems"][0], fingerprints["theorems"][1] = (
            fingerprints["theorems"][1], fingerprints["theorems"][0]
        )
        with self.assertRaisesRegex(subject.ProtocolError, "order/name"):
            subject.project_authenticated_semantic_observations(
                fingerprints, dependency,
            )
        fingerprints, dependency = fixture()
        fingerprints["unexpected"] = False
        with self.assertRaisesRegex(subject.ProtocolError, "fingerprint observation"):
            subject.project_authenticated_semantic_observations(
                fingerprints, dependency,
            )

    def test_boolean_count_rejects_exact_json_type_confusion(self) -> None:
        fingerprints, dependency = fixture()
        fingerprints["post_state"]["definition_count"] = True
        with self.assertRaisesRegex(subject.ProtocolError, "post-state count"):
            subject.project_authenticated_semantic_observations(
                fingerprints, dependency,
            )
        fingerprints, dependency = fixture()
        dependency["record_count"] = True
        with self.assertRaisesRegex(subject.ProtocolError, "identity or claim"):
            subject.project_authenticated_semantic_observations(
                fingerprints, dependency,
            )

    def test_pft_or_pretended_approval_rejects(self) -> None:
        fingerprints, dependency = fixture()
        dependency["pft_used"] = True
        with self.assertRaisesRegex(subject.ProtocolError, "identity or claim"):
            subject.project_authenticated_semantic_observations(
                fingerprints, dependency,
            )
        fingerprints, dependency = fixture()
        fingerprints["approved_reference_present"] = True
        with self.assertRaisesRegex(subject.ProtocolError, "unapproved observation"):
            subject.project_authenticated_semantic_observations(
                fingerprints, dependency,
            )

    def test_dependency_digest_and_order_reject(self) -> None:
        fingerprints, dependency = fixture()
        dependency["ordered_record_sha256"] = "0" * 64
        with self.assertRaisesRegex(subject.ProtocolError, "digest mismatch"):
            subject.project_authenticated_semantic_observations(
                fingerprints, dependency,
            )
        fingerprints, dependency = fixture()
        dependency["records"][2]["index"] = 1
        dependency["ordered_record_sha256"] = subject.canonical_sha256(
            dependency["records"]
        )
        with self.assertRaisesRegex(subject.ProtocolError, "order/name"):
            subject.project_authenticated_semantic_observations(
                fingerprints, dependency,
            )

    def test_projection_cannot_embed_claim_or_approval_bits(self) -> None:
        projection = subject.project_authenticated_semantic_observations(*fixture())
        for field in (
            "pft_used", "direct_s2_execution_approved",
            "direct_s3_coverage_approved", "v1_3_s3_release_approved",
        ):
            mutated = copy.deepcopy(projection)
            mutated[field] = True
            with self.assertRaisesRegex(subject.ProtocolError, "malformed"):
                subject.validate_semantic_projection(mutated)


if __name__ == "__main__":
    unittest.main()
