#!/usr/bin/env python3
"""Instantiate the audited stock projection plan probe for one exact record."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re


PROJECT = pathlib.Path("/project/flyspeck-candle-project")
CANONICAL = PROJECT / "tools" / "nl_stock_projection_plan_probe.ml"
CANONICAL_SHA256 = "3237d6625b1362eea98df8a1f95be5243740df8dee08b8ef8a6f2d8dfa64dd10"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ocaml_string(value: str) -> str:
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError("source identity must be one non-NUL line")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def instantiate(source: str, source_id: str, parameter_index: int) -> str:
    if parameter_index < 0:
        raise ValueError("parameter index must be nonnegative")
    source_pattern = r'^let source_id = "prep-1395142356";;$'
    index_pattern = r"^let parameter_index = 3;;$"
    source, source_count = re.subn(
        source_pattern,
        lambda _: f"let source_id = {ocaml_string(source_id)};;",
        source,
        flags=re.MULTILINE,
    )
    source, index_count = re.subn(
        index_pattern,
        f"let parameter_index = {parameter_index};;",
        source,
        flags=re.MULTILINE,
    )
    if source_count != 1 or index_count != 1:
        raise ValueError(
            f"canonical placeholder drift: source={source_count} index={index_count}"
        )
    provenance = (
        "(* GENERATED stock projection instance; DEVELOPMENT / NON-RELEASE. *)\n"
        f"(* canonical_sha256={CANONICAL_SHA256} *)\n"
        f"(* source_id_sha256={sha256_bytes(source_id.encode('utf-8'))} "
        f"parameter_index={parameter_index} *)\n"
    )
    return provenance + source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--parameter-index", required=True, type=int)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    arguments = parser.parse_args()

    canonical_bytes = CANONICAL.read_bytes()
    actual_hash = sha256_bytes(canonical_bytes)
    if actual_hash != CANONICAL_SHA256:
        raise SystemExit(
            f"canonical source identity mismatch: expected={CANONICAL_SHA256} "
            f"actual={actual_hash}"
        )
    if arguments.output.exists():
        raise SystemExit(f"refusing to overwrite output: {arguments.output}")
    if not arguments.output.parent.is_dir():
        raise SystemExit(f"output parent does not exist: {arguments.output.parent}")

    generated = instantiate(
        canonical_bytes.decode("utf-8"),
        arguments.source_id,
        arguments.parameter_index,
    )
    arguments.output.write_text(generated, encoding="utf-8")
    output_hash = sha256_bytes(generated.encode("utf-8"))
    print("status=0")
    print(f"canonical_sha256={actual_hash}")
    print(f"source_id={arguments.source_id}")
    print(f"parameter_index={arguments.parameter_index}")
    print(f"output={arguments.output}")
    print(f"output_sha256={output_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
