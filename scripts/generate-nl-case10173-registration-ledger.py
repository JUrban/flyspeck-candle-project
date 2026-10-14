#!/usr/bin/env python3
"""Generate the bounded HOL4 evaluation ledger for Flyspeck case 10173.

The Candle exporter writes 261 aligned data theories covering the 4,173
authenticated jobs and root records.  This script validates complete,
non-overlapping coverage by filename and theory identifiers, emits the small
proof-producing ``compute_eval_pure`` theory for every chunk, and records the
exact source identities in a deterministic manifest.

This is a DEVELOPMENT / NON-RELEASE fallback for the first inequality.  It
does not replace the reusable packed word/object refinement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


CELL_COUNT = 4173
CHUNK_SIZE = 16
SCHEMA = "candle-nl-case10173-registration-ledger-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def names(start: int, count: int) -> dict[str, str]:
    title = f"At{start}Count{count}"
    identifier = f"at{start}_count{count}"
    stem = f"compute_registeredCase10173HistoricalChunk{title}"
    return {
        "title": title,
        "identifier": identifier,
        "data_theory": f"{stem}Data",
        "eval_theory": f"{stem}Eval",
        "data_file": f"{stem}DataScript.sml",
        "eval_file": f"{stem}EvalScript.sml",
    }


def render_eval(start: int, count: int, item: dict[str, str]) -> str:
    identifier = item["identifier"]
    prefix = f"registered_case10173_historical_chunk_{identifier}"
    return f'''(*****************************************************************************
 * Mechanically generated proof-producing evaluation of genuine case-10173
 * cells [{start},{start + count}).  The aligned job/root chunk was sliced
 * before HOL4 source registration.
 *****************************************************************************)
Theory {item["eval_theory"]}
Ancestors
  compute_evalPure
  {item["data_theory"]}
Libs
  bossLib preamble cv_transLib

val _ = cv_trans {prefix}_ceqs_def;
val _ = cv_trans {prefix}_cexp_def;

val {prefix}_pure_eval =
  time cv_eval
    ``compute_eval_pure 100000
        {prefix}_ceqs
        {prefix}_cexp``;

val _ = save_thm
  ("{prefix}_pure_eval",
   {prefix}_pure_eval);

Theorem {prefix}_pure_eval_value:
  compute_eval_pure 100000
      {prefix}_ceqs
      {prefix}_cexp =
    SOME (from_cv {prefix}_result)
Proof
  simp
    [{prefix}_pure_eval,
     {prefix}_result_def,
     compute_execTheory.from_cv_def]
QED

val _ = export_theory ();
'''


def generate(data_dir: Path, output_dir: Path) -> dict[str, object]:
    if not data_dir.is_dir():
        raise ValueError(f"data directory does not exist: {data_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks: list[dict[str, object]] = []
    start = 0
    while start < CELL_COUNT:
        count = min(CHUNK_SIZE, CELL_COUNT - start)
        item = names(start, count)
        data_path = data_dir / item["data_file"]
        if not data_path.is_file():
            raise ValueError(f"missing exported data theory: {data_path}")
        # HOL4's generated concrete syntax contains UTF-8 quotation marks
        # even though every identity marker checked below is ASCII.
        source = data_path.read_text(encoding="utf-8")
        expected_markers = (
            f'Theory {item["data_theory"]}',
            f'registered_case10173_historical_chunk_{item["identifier"]}_ceqs',
            f'registered_case10173_historical_chunk_{item["identifier"]}_cexp',
            f'registered_case10173_historical_chunk_{item["identifier"]}_result',
        )
        for marker in expected_markers:
            if marker not in source:
                raise ValueError(f"data theory identity drift in {data_path}: {marker}")

        eval_path = output_dir / item["eval_file"]
        eval_path.write_text(render_eval(start, count, item), encoding="ascii")
        chunks.append(
            {
                "start": start,
                "count": count,
                "end": start + count,
                "data_file": str(data_path.resolve()),
                "data_sha256": sha256(data_path),
                "eval_file": str(eval_path.resolve()),
                "eval_sha256": sha256(eval_path),
                "data_theory": item["data_theory"],
                "eval_theory": item["eval_theory"],
            }
        )
        start += count

    expected_data_names = {
        names(int(chunk["start"]), int(chunk["count"]))["data_file"]
        for chunk in chunks
    }
    actual_data_names = {
        path.name
        for path in data_dir.glob(
            "compute_registeredCase10173HistoricalChunkAt*DataScript.sml"
        )
    }
    if actual_data_names != expected_data_names:
        missing = sorted(expected_data_names - actual_data_names)
        unexpected = sorted(actual_data_names - expected_data_names)
        raise ValueError(
            f"data ledger membership drift: missing={missing} unexpected={unexpected}"
        )

    manifest: dict[str, object] = {
        "schema": SCHEMA,
        "status": "DEVELOPMENT_NON_RELEASE",
        "cell_count": CELL_COUNT,
        "chunk_size": CHUNK_SIZE,
        "chunk_count": len(chunks),
        "final_chunk_size": int(chunks[-1]["count"]),
        "chunks": chunks,
    }
    manifest_path = output_dir / "ledger-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    manifest = generate(args.data_dir, args.output_dir)
    print(f'schema={manifest["schema"]}')
    print(f'cells={manifest["cell_count"]}')
    print(f'chunks={manifest["chunk_count"]}')
    print(f'final_chunk={manifest["final_chunk_size"]}')
    print(f'manifest={args.output_dir / "ledger-manifest.json"}')


if __name__ == "__main__":
    main()
