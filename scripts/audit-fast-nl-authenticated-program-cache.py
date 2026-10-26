#!/usr/bin/env python3
"""Audit the prepared cache and source closure for the external NL checker."""

from __future__ import annotations

import pathlib
import sys


CACHE = pathlib.Path(
    "/project/worktrees/cakeml-nl-packed-refinement-v1/"
    "candle/prover/compute/.hol/objs"
)
SIGNED_SOURCE = pathlib.Path(
    "/project/worktrees/cakeml-nl-packed-refinement-v1/"
    "candle/prover/compute/compute_boundedSignedProgScript.sml"
)
PROGRAM_SOURCE = pathlib.Path(
    "/project/worktrees/cakeml-fast-nl-data-dispatch-v1/"
    "candle/prover/compute/"
    "compute_registeredCase10173Tag10WitnessedFastProgScript.sml"
)
CHECKER_SOURCE = pathlib.Path(
    "/project/worktrees/cakeml-fast-nl-data-dispatch-v1/"
    "candle/prover/compute/"
    "compute_registeredCase10173ExternalWitnessedCheckerScript.sml"
)
IDENTITY_SOURCE = pathlib.Path(
    "/project/worktrees/cakeml-fast-nl-data-dispatch-v1/"
    "candle/prover/compute/"
    "compute_registeredCase10173ExternalCheckerIdentityScript.sml"
)
RUN = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v692-fast-nl-payload4-focused-dev-001/"
    "external-authenticated-checker-v2"
)
LOAD_LOG = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v692-fast-nl-payload4-focused-dev-001/"
    "authenticated-prog-load-probe-v1.log"
)
BUILD_LOG = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v692-fast-nl-payload4-focused-dev-001/"
    "external-authenticated-prog-build-v6.log"
)
IDENTITY_LOG = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v692-fast-nl-payload4-focused-dev-001/"
    "external-checker-identity-build-v1.log"
)


def main() -> int:
    errors: list[str] = []

    theory_objects = sorted(CACHE.glob("*Theory.uo")) if CACHE.is_dir() else []
    missing_companions: list[str] = []
    for obj in theory_objects:
        stem = obj.with_suffix("")
        for suffix in (".ui", ".sig", ".sml", ".dat"):
            companion = stem.with_suffix(suffix)
            if not companion.is_file():
                missing_companions.append(companion.name)
    if not theory_objects:
        errors.append("theory_object_set_missing")
    if missing_companions:
        errors.append("generated_theory_companions_incomplete")

    signed_text = (
        SIGNED_SOURCE.read_text(encoding="utf-8")
        if SIGNED_SOURCE.is_file()
        else ""
    )
    signed_sig = CACHE / "compute_boundedSignedProgTheory.sig"
    signed_sig_text = (
        signed_sig.read_text(encoding="utf-8") if signed_sig.is_file() else ""
    )
    signed_requirements = (
        "bounded_signed_word64_mul_floor_decimal_def",
        "bounded_signed_word64_mul_ceil_decimal_def",
    )
    signed_exports = (
        "bounded_signed_word64_mul_floor_decimal_v_thm",
        "bounded_signed_word64_mul_ceil_decimal_v_thm",
    )
    if any(token not in signed_text for token in signed_requirements):
        errors.append("signed_decimal_translation_source_missing")
    if any(token not in signed_sig_text for token in signed_exports):
        errors.append("signed_decimal_translation_export_missing")

    program_text = (
        PROGRAM_SOURCE.read_text(encoding="utf-8")
        if PROGRAM_SOURCE.is_file()
        else ""
    )
    ordered_program_tokens = (
        "cv_packed_bytes_chunk_limit_def",
        "cv_pack_byte_chunk_aux_def",
        "compute_cvPackedBytesTheory.cv_unpack_byte_chunk_def",
        "compute_pureFastTheory.compute_exp_to_cv_def",
        "registered_case10173_historical_chunk16_cexp_def",
        "registered_case10173_genuine_source_program_def",
        "registered_case10173_decimal_authenticated_fast_checker_def",
        "registered_case10173_external_witnessed_checker_def",
    )
    positions = [program_text.find(token) for token in ordered_program_tokens]
    if any(position < 0 for position in positions):
        errors.append("program_translation_dependency_missing")
    elif positions != sorted(positions):
        errors.append("program_translation_dependency_order")
    forbidden_program_tokens = (
        "registered_case10173_genuine_packed_certificate",
        "case10173-source-aligned-full4173.bin",
        "encoded-jobs.cvdata",
        "roots.cvdata",
    )
    if any(token in program_text for token in forbidden_program_tokens):
        errors.append("program_embeds_full_case_payload")

    checker_text = (
        CHECKER_SOURCE.read_text(encoding="utf-8")
        if CHECKER_SOURCE.is_file()
        else ""
    )
    identity_text = (
        IDENTITY_SOURCE.read_text(encoding="utf-8")
        if IDENTITY_SOURCE.is_file()
        else ""
    )
    identity_requirements = (
        (
            checker_text,
            "Definition registered_case10173_external_witnessed_checker_def",
        ),
        (
            program_text,
            "compute_registeredCase10173ExternalWitnessedCheckerTheory."
            "registered_case10173_external_witnessed_checker_def",
        ),
        (
            identity_text,
            "Theorem registered_case10173_external_witnessed_checker_eq_tag10",
        ),
        (
            identity_text,
            "registered_case10173_tag10_witnessed_checker",
        ),
    )
    if any(token not in text for text, token in identity_requirements):
        errors.append("external_checker_identity_contract_missing")

    evidence_expectations = {
        LOAD_LOG: ("Exit status: 0",),
        BUILD_LOG: ("Exit status: 0",),
        IDENTITY_LOG: (
            'Saved theorem _______ "registered_case10173_external_witnessed_checker_eq_tag10"',
            "Exit status: 0",
        ),
        RUN / "run-exact.stdout": ("accepted",),
        RUN / "run-exact-repeat.stdout": ("accepted",),
        RUN / "mutation-certificate.stdout": ("rejected",),
        RUN / "mutation-source.stdout": ("rejected",),
        RUN / "mutation-jobs.stdout": ("rejected",),
        RUN / "mutation-roots.stdout": ("rejected",),
    }
    for path, markers in evidence_expectations.items():
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if any(marker not in text for marker in markers):
            errors.append(f"evidence_missing:{path.name}")

    print(f"status={0 if not errors else 1}")
    print(f"theory_object_count={len(theory_objects)}")
    print(f"missing_companion_count={len(missing_companions)}")
    print(f"program_dependency_count={len(ordered_program_tokens)}")
    print(f"identity_requirement_count={len(identity_requirements)}")
    print(f"evidence_file_count={len(evidence_expectations)}")
    print(f"error_count={len(errors)}")
    for path in missing_companions[:20]:
        print(f"missing_companion={path}")
    for error in errors:
        print(f"error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
