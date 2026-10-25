#!/usr/bin/env python3
"""Render or verify the generated v665 nonlinear-verifier input fragments."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
CANDLE_ROOT = pathlib.Path("/project/worktrees/candle-direct-fast-nl-runtime-v1")
FLYSPECK_ROOT = pathlib.Path(
    "/project/worktrees/flyspeck-cv-nonlinear-closure-v11-manifest-d6"
)
BOOTSTRAP_FORMAL_ROOT = pathlib.Path(
    "/project/worktrees/flyspeck-strictbuild-bootstrap-v1/formal_ineqs"
)
CLOSURE = CANDLE_ROOT / "candle/flyspeck_nonlinear_verifier_closure.json"
OVERLAY_ROOT = pathlib.Path(
    "/project/flyspeck-candle-runs/cv-first-leaf-predecessor-checkpoint-v37/overlay"
)
DATA_OUTPUT = PROJECT / "tools/fast_nl_v665_verifier_data.ml"
COMPAT_OUTPUT = PROJECT / "tools/fast_nl_v665_verifier_runtime_compat.ml"
BASE_IDENTITIES = pathlib.Path(
    "/project/flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001/extra-source-identities.ml"
)
BASE_NORMALIZATIONS = pathlib.Path(
    "/project/flyspeck-candle-runs/v355-postsetup-checkpoint-dev-001/overlay-data-v355.ml"
)
EXPECTED_FLYSPECK_HEAD = "d6cdcd9f3e45f4ceb5fd1ba08f5b5ec4ce6a65eb"
EXPECTED_COMPAT_SHA256 = (
    "b20e594edbbdc50ada14c739ae3341967b7333772fd589cf60ec34cf3cef9360"
)
BOOTSTRAP_SUPPORT_SOURCES = (
    "arith/interval_arith.hl",
    "lib/ssrbool.hl",
    "lib/ssreflect/sections.hl",
    "lib/ssreflect/ssreflect.hl",
    "lib/ssrfun.hl",
    "lib/ssrnat.hl",
    "misc/misc_vars.hl",
    "misc/report.hl",
    "taylor/theory/taylor_interval-compiled.hl",
    "trig/matan.hl",
    "trig/series.hl",
)


def md5(path: pathlib.Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    digest.update(path.read_bytes())
    return digest.hexdigest()


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ml_string(value: str) -> str:
    if any(character in value for character in ('"', "\\", "\n", "\r")):
        raise ValueError(f"unsupported ML string character in {value!r}")
    return f'"{value}"'


def authenticated_closure() -> dict:
    head = subprocess.check_output(
        ["git", "-C", str(FLYSPECK_ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    if head != EXPECTED_FLYSPECK_HEAD:
        raise ValueError(f"wrong verifier Flyspeck head: {head}")
    payload = json.loads(CLOSURE.read_text(encoding="utf-8"))
    if (
        payload.get("schema") != 1
        or payload.get("root")
        != "flyspeck:formal_ineqs/verifier/m_verifier_main.hl"
        or payload.get("repositories", {}).get("flyspeck", {}).get("commit")
        != EXPECTED_FLYSPECK_HEAD
        or payload.get("counts", {}).get("selected_source_nodes") != 90
        or payload.get("counts", {}).get("normalized_sources") != 29
    ):
        raise ValueError("unexpected canonical verifier closure contract")
    roots = {"candle": CANDLE_ROOT, "flyspeck": FLYSPECK_ROOT}
    nodes = payload.get("source_nodes", {})
    if not isinstance(nodes, dict) or len(nodes) != 90:
        raise ValueError("unexpected canonical verifier source-node count")
    for key, node in nodes.items():
        root = roots.get(node.get("repository"))
        logical = node.get("logical_relative_path")
        if root is None or not isinstance(logical, str):
            raise ValueError(f"malformed verifier source node: {key}")
        source = root / logical
        if (
            not source.is_file()
            or md5(source) != node.get("md5")
            or sha256(source) != node.get("sha256")
        ):
            raise ValueError(f"verifier source identity mismatch: {source}")
        normalization = node.get("normalization")
        if normalization is not None:
            overlay = OVERLAY_ROOT / node["repository"] / logical
            if (
                not overlay.is_file()
                or overlay.stat().st_size != normalization.get("normalized_bytes")
                or md5(overlay) != normalization.get("normalized_md5")
                or sha256(overlay) != normalization.get("normalized_sha256")
            ):
                raise ValueError(f"verifier normalization mismatch: {overlay}")
    return payload


def render_data() -> str:
    payload = authenticated_closure()
    nodes = payload["source_nodes"]
    identities: list[tuple[str, str, str]] = []
    normalizations: list[tuple[str, str, str]] = []
    for node in sorted(nodes.values(), key=lambda item: item["logical_relative_path"]):
        repository = node["repository"]
        logical = node["logical_relative_path"]
        if repository == "flyspeck":
            source = FLYSPECK_ROOT / logical
            identities.append((str(source), source.name, node["md5"]))
        normalization = node.get("normalization")
        if normalization is not None:
            if repository != "flyspeck":
                raise ValueError("unexpected normalized non-Flyspeck verifier node")
            source = FLYSPECK_ROOT / logical
            overlay = OVERLAY_ROOT / repository / logical
            normalizations.append(
                (str(source), str(overlay), normalization["normalized_md5"])
            )

    matan_paths = [
        CANDLE_ROOT / "candle/cv_compute_exact_interval_matan_series.ml",
        CANDLE_ROOT / "candle/cv_compute_exact_interval_matan_series_program.ml",
    ]
    for source in matan_paths:
        if not source.is_file():
            raise ValueError(f"missing matan prerequisite: {source}")
        identities.append((str(source), source.name, md5(source)))
    for logical in BOOTSTRAP_SUPPORT_SOURCES:
        source = BOOTSTRAP_FORMAL_ROOT / logical
        if not source.is_file():
            raise ValueError(f"missing bootstrap support source: {source}")
        identities.append((str(source), source.name, md5(source)))
    compat_text = render_compat()
    compat_md5 = hashlib.md5(
        compat_text.encode("ascii"), usedforsecurity=False
    ).hexdigest()
    identities.append((str(COMPAT_OUTPUT), COMPAT_OUTPUT.name, compat_md5))
    if len(identities) != 76 or len(normalizations) != 29:
        raise ValueError(
            f"v665 generated count mismatch: {len(identities)} identities, "
            f"{len(normalizations)} normalizations"
        )

    lines = [
        "(* Generated DEVELOPMENT / NON-RELEASE data for the exact canonical",
        "   nonlinear-verifier closure used by the first fast NL theorem.",
        "   Regenerate/check with scripts/render-fast-nl-v665-inputs.py. *)",
        "let candle_fast_nl_v665_verifier_source_identities = [",
    ]
    lines.extend(
        f"  ({ml_string(path)},({ml_string(name)},{ml_string(digest)}));"
        for path, name, digest in identities
    )
    lines.extend(
        [
            "];;",
            "",
            "if List.length candle_fast_nl_v665_verifier_source_identities <> 76 then",
            '  failwith "v665 verifier source identity count mismatch";;',
            "",
            "let candle_fast_nl_v665_verifier_normalized_sources = [",
        ]
    )
    lines.extend(
        f"  ({ml_string(source)},{ml_string(target)},{ml_string(digest)});"
        for source, target, digest in normalizations
    )
    lines.extend(
        [
            "];;",
            "",
            "if List.length candle_fast_nl_v665_verifier_normalized_sources <> 29 then",
            '  failwith "v665 verifier normalization count mismatch";;',
        ]
    )
    return "\n".join(lines) + "\n"


def load_smoke_module():
    source = CANDLE_ROOT / "candle/flyspeck_nonlinear_verifier_smoke.py"
    sys.path.insert(0, str(source.parent))
    spec = importlib.util.spec_from_file_location("v665_verifier_smoke", source)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot import {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render_compat() -> str:
    module = load_smoke_module()
    text, record = module.authenticate_big_int_compatibility(CANDLE_ROOT)
    if (
        hashlib.sha256(text.encode("ascii")).hexdigest()
        != EXPECTED_COMPAT_SHA256
        or record.get("overlay", {}).get("sha256") != EXPECTED_COMPAT_SHA256
    ):
        raise ValueError("canonical runtime compatibility overlay drift")
    header = (
        "(* Generated DEVELOPMENT / NON-RELEASE runtime compatibility block.\n"
        "   Its exact body is authenticated by flyspeck_nonlinear_verifier_smoke.py;\n"
        "   it must move into a freshly linked runtime before release use. *)\n"
    )
    return header + text


def authenticate_combined_tables(generated_data: str) -> tuple[int, int]:
    """Check complete one-shot tables before paying for HOL startup."""

    identity_pattern = re.compile(
        r'^\s*\("([^"]+)",\("([^"]+)","([0-9a-f]{32})"\)\);$',
        flags=re.MULTILINE,
    )
    normalization_pattern = re.compile(
        r'^\s*\("([^"]+)","([^"]+)","([0-9a-f]{32})"\);$',
        flags=re.MULTILINE,
    )
    base_identities = identity_pattern.findall(
        BASE_IDENTITIES.read_text(encoding="utf-8")
    )
    generated_identity_text, generated_normalization_text = generated_data.split(
        "let candle_fast_nl_v665_verifier_normalized_sources", 1
    )
    generated_identities = identity_pattern.findall(generated_identity_text)
    identities = base_identities + generated_identities
    identity_paths = [row[0] for row in identities]
    if (
        len(base_identities) != 207
        or len(generated_identities) != 76
        or len(identities) != 283
        or len(set(identity_paths)) != 283
    ):
        raise ValueError("combined v665 source identity table is not unique and complete")
    for text_path, basename, expected_md5 in identities:
        path = pathlib.Path(text_path)
        if (
            not path.is_file()
            or path.name != basename
            or md5(path) != expected_md5
        ):
            raise ValueError(f"combined v665 source identity mismatch: {path}")

    base_normalizations = normalization_pattern.findall(
        BASE_NORMALIZATIONS.read_text(encoding="utf-8")
    )
    generated_normalizations = normalization_pattern.findall(
        generated_normalization_text
    )
    normalizations = base_normalizations + generated_normalizations
    original_paths = [row[0] for row in normalizations]
    if (
        len(base_normalizations) != 56
        or len(generated_normalizations) != 29
        or len(normalizations) != 85
        or len(set(original_paths)) != 85
    ):
        raise ValueError("combined v665 normalization table is not unique and complete")
    for _, text_target, expected_md5 in normalizations:
        target = pathlib.Path(text_target)
        # Three base targets are deliberately rewritten by setup.ml.  Their
        # refreshed values are authenticated by the separate normalization
        # audit, so check only targets whose recorded row is still current.
        if target.is_file() and md5(target) == expected_md5:
            continue
        if text_target.endswith("text_formalization/build/strictbuild.hl"):
            continue
        if text_target.endswith("text_formalization/general/serialization.hl"):
            continue
        if text_target.endswith("text_formalization/nonlinear/mk_all_ineq.hl"):
            continue
        raise ValueError(f"combined v665 normalization target mismatch: {target}")
    return len(identities), len(normalizations)


def check() -> int:
    failures = 0
    generated_data = render_data()
    for path, expected in (
        (DATA_OUTPUT, generated_data),
        (COMPAT_OUTPUT, render_compat()),
    ):
        if not path.is_file():
            print(f"missing={path}")
            failures += 1
        elif path.read_text(encoding="ascii") != expected:
            print(f"mismatch={path}")
            failures += 1
        else:
            print(f"verified={path}\tsha256={hashlib.sha256(expected.encode()).hexdigest()}")
    try:
        identity_count, normalization_count = authenticate_combined_tables(
            generated_data
        )
        print(f"combined_identity_count={identity_count}")
        print(f"combined_normalization_count={normalization_count}")
        print("combined_duplicate_count=0")
    except (OSError, ValueError) as error:
        print(f"combined_table_error={error}")
        failures += 1
    print(f"status={int(bool(failures))}")
    print(f"failure_count={failures}")
    return int(bool(failures))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("data", "compat", "check"))
    arguments = parser.parse_args()
    if arguments.mode == "data":
        sys.stdout.write(render_data())
        return 0
    if arguments.mode == "compat":
        sys.stdout.write(render_compat())
        return 0
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
