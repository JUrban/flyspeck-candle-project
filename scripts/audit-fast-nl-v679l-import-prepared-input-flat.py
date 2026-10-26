#!/usr/bin/env python3
"""Preflight and authenticate the bounded tag-10 flat-input checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import subprocess


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
CANDIDATE = pathlib.Path("/project/worktrees/candle-fast-nl-historical-tag10-v1")
BASE = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-direct-source-interface-v678"
)
EXPORT = pathlib.Path(
    "/project/flyspeck-candle-runs/v679k-fast-nl-prepared-input-flat-dev-001"
)
INPUT = pathlib.Path(
    "/project/flyspeck-candle-runs/v679l-fast-nl-prepared-input-flat-input-dev-001"
)
OUTPUT = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v666-fast-nl-canonical-verifier-predecessor-dev-001/"
    "post-tag10-flat-input-v679l"
)
RUNNER = PROJECT / "scripts/run-fast-nl-v679l-import-prepared-input-flat.sh"
PREAMBLE = PROJECT / "tools/fast_nl_v679l_import_prepared_input_preamble.ml"
CODEC = PROJECT / "tools/fast_nl_registered_input_flat_codec.ml"
IMPORTER = PROJECT / "tools/fast_nl_v679l_import_prepared_input_flat.ml"
BASE_SHA256 = "980d06be6fb7b418a018fddfd3cdd0bece5bd5f1ba83695264cc532dd742fce1"
CANDIDATE_HEAD = "85276ec10e3fd2f6df6114350aa773da9b327a4e"
MARKER = (
    "CANDLE_FLYSPECK_V679L_PREPARED_INPUT_FLAT_CHECKPOINT_READY "
    "DEVELOPMENT_NON_RELEASE cells=4173 numerical_compute=0 "
    "assumptions=0 axiom_growth=0"
)
DATA = {
    "source-program.cvdata": ("b8c3e4726a29f82183dffee2007b9825b4db1925b848866611a46f803b5854a3", 1),
    "encoded-jobs.cvdata": ("2f094bb7cdbde7fe5a2a967c75fa01f4d10040e496cd7504eeec9b8eaa2f8ae8", 4173),
    "roots.cvdata": ("18e4714a6ec39e50d2fe3ab755ddc27400a8a6dfc7b2fa99b617b10c78f5aa8e", 4173),
}
SOURCES = {
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_compute.ml": "5bbf53ebc14fa98bad9f65b3984f4819d519c75e5490e51af0a1a26b5444e676",
    "candle/cv_compute_analytic_expr_fixed_scale_historical_root_certificate_sound.ml": "1fb77c8796652bba92b0da73386f981ea7ff4a367eb865c2760b4783ebec124c",
    "candle/cv_compute_analytic_expr_fixed_scale_historical_root_certificate_compute.ml": "e31a76bb5c4fcfa73840025b6f5afbb54a18f7e190759440c988630b0ea3c2b3",
    "candle/cv_compute_analytic_expr_case10173_historical_dihedral_checked_compute.ml": "0a8d536bba53cf602de2beefcc3b1c97643e0870b76ac2a813532069d3dbfcb9",
}


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def line_count(path: pathlib.Path) -> int:
    with path.open("rb") as source:
        return sum(block.count(b"\n") for block in iter(lambda: source.read(4 * 1024 * 1024), b""))


def fields(path: pathlib.Path) -> dict[str, str]:
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            result[key] = value
    return result


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def preflight() -> int:
    required = (
        RUNNER,
        PREAMBLE,
        CODEC,
        IMPORTER,
        BASE / "CHECKPOINT-READY",
        BASE / "checkpoint.sha256",
        EXPORT / "PROBE-PASSED",
        EXPORT / "input-probe.receipt",
        EXPORT / "runtime.log",
        EXPORT / "prepared-input-flat.sha256",
    )
    if any(not path.is_file() or path.is_symlink() for path in required):
        return fail("missing_or_symlinked_preflight_authority")
    if not os.access(RUNNER, os.X_OK):
        return fail("runner_not_executable")
    if BASE_SHA256 not in (BASE / "checkpoint.sha256").read_text(encoding="utf-8"):
        return fail("predecessor_checkpoint_identity")

    export_receipt = fields(EXPORT / "input-probe.receipt")
    if (
        export_receipt.get("expected_marker")
        != "CANDLE_FLYSPECK_V679K_PREPARED_INPUT_FLAT_OK"
        or int(export_receipt.get("elapsed_seconds", "901")) > 900
        or (EXPORT / "runtime.log").read_text(
            encoding="utf-8", errors="replace"
        ).count("CANDLE_FLYSPECK_V679K_PREPARED_INPUT_FLAT_OK")
        != 1
    ):
        return fail("flat_export_receipt")
    manifest = (EXPORT / "prepared-input-flat.sha256").read_text(encoding="utf-8")
    for name, (expected_hash, expected_lines) in DATA.items():
        path = EXPORT / name
        if (
            not path.is_file()
            or path.is_symlink()
            or sha256(path) != expected_hash
            or line_count(path) != expected_lines
            or manifest.count(expected_hash) != 1
        ):
            return fail(f"flat_data_contract:{name}")

    head = subprocess.check_output(
        ["git", "-C", str(CANDIDATE), "rev-parse", "HEAD"], text=True
    ).strip()
    status = subprocess.check_output(
        ["git", "-C", str(CANDIDATE), "status", "--porcelain"], text=True
    )
    if head != CANDIDATE_HEAD or status:
        return fail("candidate_repository_contract")
    for logical, expected_hash in SOURCES.items():
        source = CANDIDATE / logical
        if not source.is_file() or source.is_symlink() or sha256(source) != expected_hash:
            return fail(f"candidate_source_identity:{logical}")

    runner = RUNNER.read_text(encoding="utf-8")
    preamble = PREAMBLE.read_text(encoding="utf-8")
    codec = CODEC.read_text(encoding="utf-8")
    importer = IMPORTER.read_text(encoding="utf-8")
    if (
        runner.count("FAST_NL_PHASE_TIMEOUT_SECONDS=1200") != 1
        or runner.count("audit-fast-nl-v679l-import-prepared-input-flat.py") != 1
        or runner.count("$audit") != 2
        or runner.count("run-fast-nl-restored-checkpoint-phase-v1.sh") != 1
        or preamble.count("axioms ()") != 1
        or "parse_term" in codec
        or "string_of_term" in codec
        or codec.count("Candle_fast_nl_registered_input_flat_codec") != 1
        or importer.count("Candle_fast_nl_v679l_prepared_input") != 2
        or importer.count(MARKER) != 1
        or "candle_q_dim_analytic_jet_compute" in importer
        or any("new_axiom" in text for text in (preamble, codec, importer))
    ):
        return fail("flat_import_source_contract")

    print("status=0")
    print("cells=4173")
    print("numerical_compute=0")
    print("timeout_seconds=1200")
    print(f"candidate_head={CANDIDATE_HEAD}")
    print(f"predecessor_checkpoint_sha256={BASE_SHA256}")
    return 0


def postflight() -> int:
    if preflight() != 0:
        return 1
    required = (
        INPUT / "driver.ml",
        INPUT / "driver.sha256",
        INPUT / "fragments.sha256",
        OUTPUT / "CHECKPOINT-READY",
        OUTPUT / "checkpoint.receipt",
        OUTPUT / "checkpoint.sha256",
        OUTPUT / "runtime.log",
        OUTPUT / "runtime-log.sha256",
    )
    if any(not path.is_file() or path.is_symlink() for path in required):
        return fail("flat_import_checkpoint_missing")
    receipt = fields(OUTPUT / "checkpoint.receipt")
    if (
        receipt.get("receipt_kind")
        != "development-fast-nl-v679l-tag10-flat-input-checkpoint-v1"
        or receipt.get("release_evidence") != "false"
        or receipt.get("driver_mode") != "direct"
        or receipt.get("driver_sha256") != sha256(INPUT / "driver.ml")
        or receipt.get("expected_marker") != MARKER
        or receipt.get("base_checkpoint", "").endswith(".dmtcp") is False
    ):
        return fail("flat_import_checkpoint_receipt")
    if receipt.get("base_checkpoint"):
        if sha256(pathlib.Path(receipt["base_checkpoint"])) != BASE_SHA256:
            return fail("flat_import_base_checkpoint_identity")
    checkpoint = pathlib.Path(receipt.get("checkpoint", ""))
    if (
        not checkpoint.is_file()
        or checkpoint.is_symlink()
        or sha256(checkpoint) != receipt.get("checkpoint_sha256")
    ):
        return fail("flat_import_checkpoint_identity")
    log_path = OUTPUT / "runtime.log"
    log = log_path.read_text(encoding="utf-8", errors="replace")
    if (
        log.count(MARKER) != 1
        or sha256(log_path) not in (OUTPUT / "runtime-log.sha256").read_text(encoding="utf-8")
        or any(text in log for text in ("EXCEPTION:", "ERROR:", "Parsing failed", "Fatal error", "Out of memory"))
    ):
        return fail("flat_import_runtime_contract")

    print("status=0")
    print("cells=4173")
    print("numerical_compute=0")
    print("assumptions=0")
    print("axiom_growth=0")
    print(f"checkpoint_sha256={sha256(checkpoint)}")
    print(f"runtime_log_sha256={sha256(log_path)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    arguments = parser.parse_args()
    return preflight() if arguments.preflight else postflight()


if __name__ == "__main__":
    raise SystemExit(main())
