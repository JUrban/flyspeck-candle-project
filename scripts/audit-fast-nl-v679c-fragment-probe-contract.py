#!/usr/bin/env python3
"""Authenticate why the first tag-10 probe failed and the bounded replacement."""

from __future__ import annotations

import hashlib
import pathlib
import subprocess


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
FAILED = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679c-fast-nl-tag10-logical-probe-dev-001"
)
BASE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-direct-source-interface-v678"
)
LEDGER_PROBE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679-fast-nl-loaded-source-ledger-probe-dev-001/runtime.log"
)
RUNNER = PROJECT / "scripts/run-fast-nl-v679c-tag10-fragment-probe.sh"
PREAMBLE = PROJECT / "tools/fast_nl_v679c_tag10_fragment_preamble.ml"
POSTCHECK = PROJECT / "tools/fast_nl_v679c_tag10_fragment_postcheck.ml"
BASE_SHA256 = "980d06be6fb7b418a018fddfd3cdd0bece5bd5f1ba83695264cc532dd742fce1"
RUNTIME = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005/"
    "cake"
)
QUOTED_DRIVER = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v679c-fast-nl-tag10-logical-fragment-input-dev-001/driver.ml"
)
QUOTED_DRIVER_SHA256 = (
    "ed11deca19eac20b8e37a97a25252c06ea98550a327a3808235e000280b93c40"
)
PREREQUISITE_IDENTITIES = (
    "cv_compute_analytic_expr_taylor_model_program_fixed_nonlinear_program_sound.ml:eafcaa12f247044ac203c57776593be9",
    "cv_compute_analytic_expr_fixed_scale_historical_dihedral_sound.ml:ac10f6bebc801f4c5746e00e78adc45f",
    "cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_sound.ml:393018a4878384295220afb6fb307ba1",
    "cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_item_sound.ml:9251e88f4dfe107a690e266c39adb18c",
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def main() -> int:
    required = (
        FAILED / "PROBE-FAILED",
        FAILED / "runtime.log",
        BASE / "CHECKPOINT-READY",
        BASE / "checkpoint.sha256",
        BASE / "checkpoint.receipt",
        LEDGER_PROBE,
        RUNNER,
        PREAMBLE,
        POSTCHECK,
        RUNTIME,
        QUOTED_DRIVER,
    )
    if any(not path.is_file() or path.is_symlink() for path in required):
        return fail("missing_or_symlinked_probe_contract_authority")

    failed_log = (FAILED / "runtime.log").read_text(
        encoding="utf-8", errors="replace"
    )
    if (
        failed_log.count("CANDLE_RESTORE_INPUT_ACK nonce=") != 1
        or failed_log.count("unauthenticated Candle source action:") != 1
        or "candle-fast-nl-historical-tag10-v1" not in failed_log
        or "CANDLE_FLYSPECK_V679C_TAG10_LOGICAL_PROOF_OK" in failed_log
    ):
        return fail("failed_probe_signature_drift")

    checkpoint_line = (BASE / "checkpoint.sha256").read_text(
        encoding="utf-8"
    )
    if BASE_SHA256 not in checkpoint_line:
        return fail("fragment_predecessor_identity")
    receipt = (BASE / "checkpoint.receipt").read_text(encoding="utf-8")
    if (
        "receipt_kind=development-fast-nl-v678-direct-source-interface-checkpoint-v1"
        not in receipt
        or f"checkpoint_sha256={BASE_SHA256}" not in receipt
    ):
        return fail("fragment_predecessor_receipt")

    ledger = LEDGER_PROBE.read_text(encoding="utf-8", errors="replace")
    if any(identity not in ledger for identity in PREREQUISITE_IDENTITIES):
        return fail("fragment_prerequisite_identity")

    runner = RUNNER.read_text(encoding="utf-8")
    required_runner = (
        str(BASE),
        "FAST_NL_INPUT_PROBE_TIMEOUT_SECONDS=600",
        "audit-fast-nl-v679-tag10-candidate.py",
        "awk '!/^needs",
        "run-fast-nl-restored-input-probe-v1.sh",
        "v679c-fast-nl-tag10-logical-fragment-probe-v2-dev-001",
        'for parse_source in "$preamble" "$postcheck"',
    )
    if any(text not in runner for text in required_runner):
        return fail("bounded_fragment_runner_contract")
    if runner.count("historical_dihedral_program_compute.ml") != 1 or \
       runner.count("historical_dihedral_item_sound.ml") != 1 or \
       runner.count("historical_dihedral_program_logical_sound.ml") != 1:
        return fail("bounded_fragment_source_partition")
    if '<"$input/driver.ml"' in runner:
        return fail("quotation_unsupported_parser_scope")

    if sha256(QUOTED_DRIVER) != QUOTED_DRIVER_SHA256:
        return fail("quoted_driver_identity")
    diagnostic = subprocess.run(
        [
            str(RUNTIME),
            "--candle-parser-diagnostic-v1",
            "a" * 64,
        ],
        input=QUOTED_DRIVER.read_bytes(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=5,
        check=False,
    )
    output = diagnostic.stdout.decode("utf-8", errors="replace")
    if (
        diagnostic.returncode == 0
        or "PARSE_ERROR" not in output
        or "Parsing failed at line 44" not in output
        or "LEXER ERROR" not in output
    ):
        return fail("quoted_driver_parser_failure_signature")

    for glue in (PREAMBLE, POSTCHECK):
        parsed = subprocess.run(
            [
                str(RUNTIME),
                "--candle-parser-diagnostic-v1",
                "b" * 64,
            ],
            input=glue.read_bytes(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=5,
            check=False,
        )
        if parsed.returncode != 0 or not parsed.stdout.endswith(b"\tOK\n"):
            return fail(f"quotation_free_glue_parser:{glue.name}")

    preamble = PREAMBLE.read_text(encoding="utf-8")
    postcheck = POSTCHECK.read_text(encoding="utf-8")
    if (
        preamble.count("axioms ()") != 1
        or postcheck.count("axioms ()") != 1
        or "TAG10_FRAGMENT_LOGICAL_PROOF_OK" not in postcheck
        or "new_axiom" in preamble
        or "new_axiom" in postcheck
    ):
        return fail("fragment_proof_driver_contract")

    print("status=0")
    print("failed_probe_reached_candidate_proof=false")
    print("replacement_method=exact_fragment_bytes")
    print("replacement_timeout_seconds=600")
    print("combined_boot_parser_supports_hol_quotations=false")
    print("quotation_free_glue_parser_count=2")
    print(f"predecessor_checkpoint_sha256={BASE_SHA256}")
    print(f"runner_sha256={sha256(RUNNER)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
