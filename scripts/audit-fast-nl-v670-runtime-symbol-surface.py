#!/usr/bin/env python3
"""Cheap binary/source audit for the recorded nonlinear float surface."""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
CANDLE = pathlib.Path("/project/worktrees/candle-direct-fast-nl-runtime-v1")
RUNTIME_DIR = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005"
)
RUNTIME = RUNTIME_DIR / "cake"
CLOSURE = CANDLE / "candle/flyspeck_nonlinear_verifier_closure.json"
CENTRAL = CANDLE / "candle/ocaml.ml"
WRAPPER = PROJECT / "tools/fast_nl_v670_runtime_surface_support.ml"
FAILED_LOG = pathlib.Path(
    "/project/flyspeck-candle-runs/"
    "v667-fast-nl-support-probe-dev-001/runtime.log"
)
EXPECTED_RUNTIME_SHA256 = (
    "da10797b39eebae4c43a433b331b1c5aa21c32d582371b454e3f37f2e0e0dee5"
)
EXPECTED_RESOLUTION = {
    "abs_float": "central-candle-compatibility",
    "atan": "exact-closed-expression-normalization",
    "float_of_int": "central-candle-compatibility",
    "float_of_string": "central-candle-compatibility",
    "floor": "central-candle-compatibility",
    "infinity": "central-candle-compatibility",
    "int_of_float": "central-candle-compatibility",
    "log": "verified-runtime-primitive",
    "nan": "central-candle-compatibility",
}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> int:
    print("status=1")
    print(f"error={message}")
    return 1


def raw_runtime(source: str) -> str:
    result = subprocess.run(
        [str(RUNTIME), "--candle"],
        cwd=RUNTIME_DIR,
        input=source,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"raw runtime exit {result.returncode}")
    return result.stdout


def main() -> int:
    for path in (RUNTIME, CLOSURE, CENTRAL, WRAPPER, FAILED_LOG):
        if not path.is_file():
            return fail(f"missing:{path}")
    if sha256(RUNTIME) != EXPECTED_RUNTIME_SHA256:
        return fail("runtime_sha256")

    closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
    compatibility = closure.get("compatibility", {})
    if (
        compatibility.get("float_runtime_identifier_resolution")
        != EXPECTED_RESOLUTION
        or compatibility.get("float_runtime_identifier_use_count") != 94
        or len(compatibility.get("float_runtime_identifier_uses", [])) != 94
    ):
        return fail("closure_float_runtime_inventory")

    central = CENTRAL.read_text(encoding="utf-8")
    central_fragments = (
        "let float_of_int x = Cake.Double.fromInt x",
        "let int_of_float x = Cake.Double.toInt x",
        "let floor x = Cake.Double.floor x",
        "let abs_float = candle_binary64_abs;;",
        "let float_of_string = Float.of_string;;",
    )
    if any(central.count(fragment) != 1 for fragment in central_fragments):
        return fail("central_runtime_surface")

    wrapper = WRAPPER.read_text(encoding="utf-8")
    wrapper_fragments = (
        "let float_of_int x = Cake.Double.fromInt x;;",
        "let int_of_float x = Cake.Double.toInt x;;",
        "let floor x = Cake.Double.floor x;;",
        "match Double.fromString s with",
        "let abs_float = candle_binary64_abs;;",
        "CANDLE_FLYSPECK_V670_RUNTIME_SYMBOL_SURFACE_OK identifiers=9",
        '#use "/project/flyspeck-candle-project/tools/fast_nl_v665_support.ml";;',
    )
    if any(wrapper.count(fragment) != 1 for fragment in wrapper_fragments):
        return fail("wrapper_runtime_surface")

    failed = FAILED_LOG.read_text(encoding="utf-8", errors="replace")
    errors = re.findall(r"^ERROR:.*$", failed, flags=re.MULTILINE)
    expected_error = "ERROR: Undefined variable: float_of_string at line 32"
    if errors != [expected_error]:
        return fail("failed_runtime_evidence")

    try:
        missing_probe = raw_runtime('float_of_string "1.25";;\n')
        replacement_probe = raw_runtime(
            'let float_of_string s = match Double.fromString s with '
            '| None -> failwith "float_of_string" | Some value -> value;;\n'
            'let candle_fast_nl_v670_probe = float_of_string "1.25";;\n'
        )
        log_probe = raw_runtime("let candle_fast_nl_v670_log = log;;\n")
    except (OSError, subprocess.SubprocessError, RuntimeError) as error:
        return fail(f"runtime_probe:{error}")
    if (
        "Undefined variable: float_of_string" not in missing_probe
        or "ERROR:" in replacement_probe
        or "val candle_fast_nl_v670_probe = 1.25: double" not in replacement_probe
        or "ERROR:" in log_probe
    ):
        return fail("runtime_probe_contract")

    print("status=0")
    print("runtime_identifier_count=9")
    print("runtime_identifier_use_count=94")
    print("raw_runtime_missing_float_of_string_count=1")
    print("raw_runtime_replacement_probe_count=1")
    print(f"runtime_sha256={sha256(RUNTIME)}")
    print(f"wrapper_sha256={sha256(WRAPPER)}")
    print(f"failed_log_sha256={sha256(FAILED_LOG)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
