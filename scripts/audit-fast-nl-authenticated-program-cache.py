#!/usr/bin/env python3
"""Audit the prepared cache and source closure for the external NL checker."""

from __future__ import annotations

import hashlib
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
COMPUTE = pathlib.Path(
    "/project/worktrees/cakeml-fast-nl-data-dispatch-v1/"
    "candle/prover/compute"
)
MULTIFAMILY_CHECKER_SOURCE = (
    COMPUTE / "compute_registeredNLExternalWitnessedCheckerScript.sml"
)
CASE16594_CHECKER_SOURCE = (
    COMPUTE / "compute_registeredCase16594ExternalWitnessedCheckerScript.sml"
)
SOURCE_DECODER_SOURCE = COMPUTE / "compute_boundedAnalyticProgramCVScript.sml"
NATIVE_PARSER_SOURCE = COMPUTE / "compute_cvNativeRuntimeScript.sml"
MULTIFAMILY_TRANSLATION_SOURCE = (
    COMPUTE / "compute_registeredNLExternalWitnessedCheckerProgScript.sml"
)
MULTIFAMILY_PROGRAM_SOURCE = (
    COMPUTE / "compute_registeredNLExternalWitnessedFastProgScript.sml"
)
CASE16594_SOURCE_DATA = (
    COMPUTE / "compute_boundedCase16594SourceCVDataScript.sml"
)
GENERIC_PACKED_CHECKER_SOURCE = (
    COMPUTE / "compute_boundedPackedAnalyticCheckScript.sml"
)
GENERIC_PACKED_TRANSLATION_SOURCE = (
    COMPUTE / "compute_boundedPackedAnalyticCheckProgScript.sml"
)
GENERIC_PACKED_RUN = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v693-nl-generic-checker-core-dev-001"
)
GENERIC_PACKED_BUILD_LOGS = (
    GENERIC_PACKED_RUN / "holmake-focused-v8.log",
    GENERIC_PACKED_RUN / "holmake-prog-focused-v3.log",
)
GENERIC_PREPARED_SOURCE = (
    COMPUTE / "compute_boundedAnalyticPreparedPlanScript.sml"
)
GENERIC_PREPARED_SOUND_SOURCE = (
    COMPUTE / "compute_boundedAnalyticPreparedPlanSoundScript.sml"
)
GENERIC_PREPARED_TRANSLATION_SOURCE = (
    COMPUTE / "compute_boundedAnalyticPreparedPlanProgScript.sml"
)
GENERIC_PLAN_SOURCE = COMPUTE / "compute_boundedAnalyticPlanCVScript.sml"
GENERIC_PLAN_TRANSLATION_SOURCE = (
    COMPUTE / "compute_boundedAnalyticPlanCVProgScript.sml"
)
GENERIC_PLAN_BUILD_LOGS = (
    GENERIC_PACKED_RUN / "generic-prepared-plan-logic-v4.log",
    GENERIC_PACKED_RUN / "generic-prepared-plan-prog-v3.log",
    GENERIC_PACKED_RUN / "generic-plan-cv-logic-v2.log",
    GENERIC_PACKED_RUN / "generic-plan-cv-prog-v1.log",
)
GENERIC_PREPARED_SOUND_BUILD_LOG = (
    GENERIC_PACKED_RUN / "generic-prepared-plan-sound-v6.log"
)
MULTIFAMILY_RUN = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v692-fast-nl-payload4-focused-dev-001/"
    "external-multifamily-checker-v2"
)
MULTIFAMILY_BUILD_LOGS = (
    pathlib.Path(
        "/project/flyspeck-candle-runs/"
        "v692-fast-nl-payload4-focused-dev-001/"
        "multifamily-external-checker-prog-build-v3.log"
    ),
    pathlib.Path(
        "/project/flyspeck-candle-runs/"
        "v692-fast-nl-payload4-focused-dev-001/"
        "multifamily-external-fast-program-build-v2.log"
    ),
    pathlib.Path(
        "/project/flyspeck-candle-runs/"
        "v692-fast-nl-payload4-focused-dev-001/"
        "multifamily-external-fast-export-build-v3.log"
    ),
)
CASE10173_CERTIFICATE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "nl-case10173-source-aligned-packed-full4173-v1-dev-001/"
    "case10173-source-aligned-full4173.bin"
)
CASE10173_SOURCE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679k-fast-nl-prepared-input-flat-dev-001/source-program.cvdata"
)
CASE16594_CERTIFICATE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "nl-case16594-packed-checker-input-v6-delta-taylor-box-dev-001/"
    "case16594-delta-specialized-taylor-box.bin"
)
CASE16594_SOURCE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "cv-case16594-native-inputs-full-v4-dev-001/case16594-program.cval"
)


def sha256(path: pathlib.Path) -> str:
    if not path.is_file() or path.is_symlink():
        return ""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


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

    multifamily_sources = {
        MULTIFAMILY_CHECKER_SOURCE: (
            "Definition registered_nl_external_witnessed_checker_def",
            "registered_case10173_external_witnessed_checker",
            "registered_case16594_external_witnessed_checker",
        ),
        CASE16594_CHECKER_SOURCE: (
            "Definition registered_case16594_external_witnessed_checker_def",
            "bounded_analytic_program_of_cv source_program =",
            "SOME bounded_case16594_program",
            "encoded_jobs = Num 0",
            "encoded_roots = Num 0",
            "bounded_packed_chars_case16594_complete_check bytes",
        ),
        SOURCE_DECODER_SOURCE: (
            "Definition bounded_analytic_program_of_cv_def",
            "Definition bounded_analytic_instruction_of_cv_def",
            "Theorem bounded_analytic_program_of_cv_rejects_aliases",
        ),
        NATIVE_PARSER_SOURCE: (
            "Definition cv_native_parse_term_def",
            "Definition cv_native_parse_one_def",
            "Definition cv_external_parse_one_def",
            "Theorem cv_native_parse_one_rejects_malformed",
        ),
        MULTIFAMILY_TRANSLATION_SOURCE: (
            "compute_registeredNLCase16594CheckProg",
            "compute_cvPackedBytesRuntime",
            "compute_cvNativeRuntime",
            "cv_external_parse_one_def",
            "registered_case10173_external_witnessed_checker_def",
            "bounded_analytic_program_of_cv_def",
            "registered_case16594_external_witnessed_checker_def",
            "registered_nl_external_witnessed_checker_def",
        ),
        MULTIFAMILY_PROGRAM_SOURCE: (
            "case cv_external_parse_one source_text of",
            "case cv_flat_parse_list jobs_text of",
            "case cv_flat_parse_list roots_text of",
            "registered_nl_external_witnessed_checker",
        ),
        CASE16594_SOURCE_DATA: (
            "Source program SHA-256: "
            "82f5c7f81b7a6ec292b6426caddaddb1ce7fde5dfbd83c2900a072f679a28dcb",
            "Theorem bounded_case16594_source_program_cv_decodes",
            "SOME bounded_case16594_program",
        ),
        GENERIC_PACKED_CHECKER_SOURCE: (
            "Definition bounded_packed_chars_analytic_input_def",
            "Definition bounded_packed_chars_analytic_cell_def",
            "Definition bounded_packed_chars_analytic_header_def",
            "Definition bounded_packed_chars_analytic_eval_cell_def",
            "Definition bounded_packed_chars_analytic_check_cells_def",
            "Definition bounded_packed_chars_analytic_complete_check_def",
            "cell_count < 4294967296",
            "certificate_count < 4294967296",
            "Theorem bounded_packed_chars_analytic_complete_check_case16594",
            "Theorem bounded_packed_chars_analytic_eval_cell_success_well_formed",
        ),
        GENERIC_PACKED_TRANSLATION_SOURCE: (
            'translation_extends "compute_boundedPackedSequentialCase16594CheckProg"',
            "bounded_packed_chars_analytic_input_def",
            "bounded_packed_chars_analytic_cell_def",
            "bounded_packed_chars_analytic_header_def",
            "bounded_packed_chars_analytic_eval_cell_def",
            "bounded_packed_chars_analytic_check_cells_def",
            "bounded_packed_chars_analytic_complete_check_def",
        ),
        GENERIC_PREPARED_SOURCE: (
            "Definition bounded_analytic_nat_ceil_div_def",
            "if denominator = 0 then 0",
            "Definition bounded_analytic_rational_constant64_def",
            "ceiling_magnitude < 18446744073709551616",
            "Definition bounded_analytic_compile_program_def",
            "Definition bounded_analytic_recognized_specialization_def",
            "Theorem bounded_analytic_compile_program_case16594",
        ),
        GENERIC_PREPARED_SOUND_SOURCE: (
            "Definition bounded_analytic_rational_interval_covers_def",
            "Theorem bounded_analytic_nat_floor_ceil_bounds",
            "Theorem bounded_analytic_nonnegative_interval64_values",
            "Theorem bounded_analytic_negative_interval64_values",
            "Theorem bounded_analytic_rational_constant64_covers",
        ),
        GENERIC_PREPARED_TRANSLATION_SOURCE: (
            'translation_extends "compute_boundedPackedAnalyticCheckProg"',
            "bounded_analytic_rational_constant64_def",
            "bounded_analytic_compile_program_def",
        ),
        GENERIC_PLAN_SOURCE: (
            "Datatype:",
            "bounded_analytic_plan_metadata",
            "if version = 1 then",
            "Definition bounded_analytic64_certificate_count_def",
            "Definition bounded_analytic_source_plan_check_def",
            "Theorem bounded_analytic_source_plan_check_case16594",
        ),
        GENERIC_PLAN_TRANSLATION_SOURCE: (
            'translation_extends "compute_boundedAnalyticPreparedPlanProg"',
            "bounded_analytic_program_of_cv_def",
            "bounded_analytic_plan_metadata_of_cv_def",
            "bounded_analytic_source_plan_check_def",
        ),
    }
    for path, markers in multifamily_sources.items():
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if any(marker not in text for marker in markers):
            errors.append(f"multifamily_source_contract_missing:{path.name}")

    multifamily_program_text = (
        MULTIFAMILY_PROGRAM_SOURCE.read_text(encoding="utf-8")
        if MULTIFAMILY_PROGRAM_SOURCE.is_file()
        else ""
    )
    forbidden_multifamily_program_tokens = (
        "registered_case10173_external_witnessed_checker",
        "registered_case16594_external_witnessed_checker",
        "case10173-source-aligned-full4173.bin",
        "case16594-delta-specialized-taylor-box.bin",
    )
    if any(
        token in multifamily_program_text
        for token in forbidden_multifamily_program_tokens
    ):
        errors.append("multifamily_program_has_case_specific_dispatch")

    for path in MULTIFAMILY_BUILD_LOGS:
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if "Exit status: 0" not in text:
            errors.append(f"multifamily_build_failed:{path.name}")
    export_text = MULTIFAMILY_BUILD_LOGS[-1].read_text(encoding="utf-8")
    if "unverified/sexpr-bootstrap" not in export_text:
        errors.append("multifamily_export_bootstrap_include_missing")

    generic_build_markers = {
        GENERIC_PACKED_BUILD_LOGS[0]: (
            'Saved theorem _______ "bounded_packed_chars_analytic_complete_check_case16594"',
            "Exit status: 0",
        ),
        GENERIC_PACKED_BUILD_LOGS[1]: (
            'Saved theorem _______ "bounded_packed_chars_analytic_complete_check_v_thm"',
            "Exit status: 0",
        ),
    }
    for path, markers in generic_build_markers.items():
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if any(marker not in text for marker in markers):
            errors.append(f"generic_packed_build_failed:{path.name}")

    generic_plan_build_markers = {
        GENERIC_PLAN_BUILD_LOGS[0]: (
            'Saved theorem _______ "bounded_analytic_compile_program_case16594"',
            "Exit status: 0",
        ),
        GENERIC_PLAN_BUILD_LOGS[1]: (
            'Saved theorem _______ "bounded_analytic_compile_program_v_thm"',
            "Exit status: 0",
        ),
        GENERIC_PLAN_BUILD_LOGS[2]: (
            'Saved theorem _______ "bounded_analytic_source_plan_check_case16594"',
            "Exit status: 0",
        ),
        GENERIC_PLAN_BUILD_LOGS[3]: (
            'Saved theorem _______ "bounded_analytic_source_plan_check_v_thm"',
            "Exit status: 0",
        ),
    }
    for path, markers in generic_plan_build_markers.items():
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if any(marker not in text for marker in markers):
            errors.append(f"generic_plan_build_failed:{path.name}")
        if "has a precondition" in text:
            errors.append(f"generic_plan_translation_has_precondition:{path.name}")

    generic_sound_text = (
        GENERIC_PREPARED_SOUND_BUILD_LOG.read_text(encoding="utf-8")
        if GENERIC_PREPARED_SOUND_BUILD_LOG.is_file()
        else ""
    )
    generic_sound_markers = (
        'Saved theorem _______ "bounded_analytic_rational_constant64_covers"',
        "Theory \"compute_boundedAnalyticPreparedPlanSound\" took",
        "Exit status: 0",
    )
    if any(marker not in generic_sound_text for marker in generic_sound_markers):
        errors.append("generic_prepared_sound_build_failed")

    multifamily_results = {
        "run-case10173": "accepted",
        "repeat-case10173": "accepted",
        "run-case16594": "accepted",
        "repeat-case16594": "accepted",
        "reject-case10173-cert-byte": "rejected",
        "reject-case10173-source": "rejected",
        "reject-case10173-jobs": "rejected",
        "reject-case10173-roots": "rejected",
        "reject-case16594-wrong-cert": "rejected",
        "reject-case16594-wrong-source": "rejected",
        "reject-case16594-jobs": "rejected",
        "reject-case16594-roots": "rejected",
    }
    for label, expected in multifamily_results.items():
        stdout_path = MULTIFAMILY_RUN / f"{label}.stdout"
        time_path = MULTIFAMILY_RUN / f"{label}.time"
        stdout = (
            stdout_path.read_text(encoding="utf-8").strip()
            if stdout_path.is_file()
            else ""
        )
        timing = time_path.read_text(encoding="utf-8") if time_path.is_file() else ""
        if stdout != expected or "Exit status: 0" not in timing:
            errors.append(f"multifamily_behavior_missing:{label}")

    expected_hashes = {
        CASE10173_CERTIFICATE:
            "12285dad68ae8c05fb1a39232317305256dc4fc2f87a63ae06a833cc27cad2da",
        CASE10173_SOURCE:
            "b8c3e4726a29f82183dffee2007b9825b4db1925b848866611a46f803b5854a3",
        CASE16594_CERTIFICATE:
            "18f425bec54821d7484c45310eb74a2399d04b6f62bbf81c5a06575e3d5c348a",
        CASE16594_SOURCE:
            "82f5c7f81b7a6ec292b6426caddaddb1ce7fde5dfbd83c2900a072f679a28dcb",
        MULTIFAMILY_RUN / "checker":
            "2bef10702774f960f709285effb88570df766670af07974ba46dc068f7336277",
        GENERIC_PACKED_CHECKER_SOURCE:
            "0c529d2f0b3247063efc5825be8e1aa8e2269017b3ab18096ff1f7c8e7543118",
        GENERIC_PACKED_TRANSLATION_SOURCE:
            "c5cfcdd2478718987b7ac157058a2e4d0d72786f95e431acbda7adeba2a00aa6",
        GENERIC_PREPARED_SOURCE:
            "af8d8a1f9d7cfe3be77b239c953bbde5d5a070941730479fc39ea15303b7e23e",
        GENERIC_PREPARED_SOUND_SOURCE:
            "434bb8ac409f764e1d1a9c1d403e7cecfa193df2976b2602cddbf7cfcdca441d",
        GENERIC_PREPARED_TRANSLATION_SOURCE:
            "bf39d62b591b57cb1e18dd47e07e85bb4415a42515238cc10167caba3fbf044f",
        GENERIC_PLAN_SOURCE:
            "d3285c575e10a04d2dfa8b74f65115d3ec09d4cf25199c43c819169acb1cf00b",
        GENERIC_PLAN_TRANSLATION_SOURCE:
            "996e30009c5542911edf9acc6f872cbf8383cd3c82657bfe2ce58328b60c1320",
    }
    for path, expected in expected_hashes.items():
        if sha256(path) != expected:
            errors.append(f"multifamily_identity_mismatch:{path.name}")

    print(f"status={0 if not errors else 1}")
    print(f"theory_object_count={len(theory_objects)}")
    print(f"missing_companion_count={len(missing_companions)}")
    print(f"program_dependency_count={len(ordered_program_tokens)}")
    print(f"identity_requirement_count={len(identity_requirements)}")
    print(f"evidence_file_count={len(evidence_expectations)}")
    print(f"multifamily_source_count={len(multifamily_sources)}")
    print(f"multifamily_behavior_count={len(multifamily_results)}")
    print(f"multifamily_identity_count={len(expected_hashes)}")
    print(f"error_count={len(errors)}")
    for path in missing_companions[:20]:
        print(f"missing_companion={path}")
    for error in errors:
        print(f"error={error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
