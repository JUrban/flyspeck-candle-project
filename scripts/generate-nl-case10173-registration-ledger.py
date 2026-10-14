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
import math
from pathlib import Path


CELL_COUNT = 4173
CHUNK_SIZE = 16
SCHEMA = "candle-nl-case10173-registration-ledger-v1"
SHARED_DATA_THEORY = "compute_registeredCase10173HistoricalSharedCeqsData"
SHARED_EVAL_THEORY = "compute_registeredCase10173HistoricalSharedCeqsEval"
SHARED_CEQS = "registered_case10173_historical_shared_ceqs"
GROUP_SIZE = 16
GROUP_DEPTH = 4
LEDGER_GROUP_COUNT = (CELL_COUNT + CHUNK_SIZE * GROUP_SIZE - 1) // (
    CHUNK_SIZE * GROUP_SIZE
)
LEDGER_DEPTH = math.ceil(math.log2(LEDGER_GROUP_COUNT))
LEDGER_DATA_THEORY = "compute_registeredCase10173HistoricalLedgerData"
LEDGER_EVAL_THEORY = "compute_registeredCase10173HistoricalLedgerEval"
LEDGER_PREFIX = "registered_case10173_historical_ledger"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def definition_rhs(source: str, name: str) -> str:
    """Return the generated HOL definition's right-hand-side source text."""
    marker = f"Definition {name}_def:"
    try:
        definition_start = source.index(marker) + len(marker)
        definition_end = source.index("\nEnd", definition_start)
        equals = source.index("=\n", definition_start, definition_end) + 2
    except ValueError as error:
        raise ValueError(f"malformed generated definition: {name}") from error
    return source[equals:definition_end]


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


def group_names(index: int) -> dict[str, str]:
    stem = f"compute_registeredCase10173HistoricalLedgerGroup{index}"
    return {
        "index": str(index),
        "data_theory": f"{stem}Data",
        "eval_theory": f"{stem}Eval",
        "data_file": f"{stem}DataScript.sml",
        "eval_file": f"{stem}EvalScript.sml",
        "prefix": f"registered_case10173_historical_ledger_group{index}",
    }


def balanced_pair(leaves: list[str], depth: int, padding: str) -> str:
    """Render a perfect pair tree so every real leaf has identical fuel depth."""
    expected = 1 << depth
    if len(leaves) > expected:
        raise ValueError(
            f"too many balanced-tree leaves: count={len(leaves)} capacity={expected}"
        )
    level = leaves + [padding] * (expected - len(leaves))
    while len(level) > 1:
        level = [
            f"Pair ({level[index]}) ({level[index + 1]})"
            for index in range(0, len(level), 2)
        ]
    return level[0]


def render_ledger_group_data(
    index: int, group_chunks: list[dict[str, object]]
) -> str:
    item = group_names(index)
    ancestors = "\n  ".join(str(chunk["data_theory"]) for chunk in group_chunks)
    cexp_leaves = [
        "registered_case10173_historical_chunk_"
        f"at{chunk['start']}_count{chunk['count']}_cexp"
        for chunk in group_chunks
    ]
    result_leaves = ["Num 1" for _ in group_chunks]
    cexp_tree = balanced_pair(cexp_leaves, GROUP_DEPTH, "Num 1")
    result_tree = balanced_pair(result_leaves, GROUP_DEPTH, "Num 1")
    return f'''(*****************************************************************************
 * Mechanically composed exact-result group {index} for the bounded genuine
 * case-10173 registration ledger.  Perfect depth preserves evaluator fuel.
 *****************************************************************************)
Theory {item["data_theory"]}
Ancestors
  compute
  {SHARED_DATA_THEORY}
  {ancestors}
Libs bossLib preamble

Definition {item["prefix"]}_cexp_def:
  {item["prefix"]}_cexp : compute_exp =
    {cexp_tree}
End

Definition {item["prefix"]}_result_def:
  {item["prefix"]}_result : cv =
    {result_tree}
End

val _ = export_theory ();
'''


def render_ledger_group_eval(
    index: int, group_chunks: list[dict[str, object]]
) -> str:
    item = group_names(index)
    ancestors = "\n  ".join(str(chunk["eval_theory"]) for chunk in group_chunks)
    leaf_theorems = "\n     ".join(
        "registered_case10173_historical_chunk_"
        f"at{chunk['start']}_count{chunk['count']}_pure_eval,"
        for chunk in group_chunks
    )
    fuel = 100000 + GROUP_DEPTH
    return f'''(*****************************************************************************
 * Mechanically composed proof-producing group {index} for the bounded
 * genuine case-10173 registration ledger.
 *****************************************************************************)
Theory {item["eval_theory"]}[no_sig_docs]
Ancestors
  compute_evalPure
  {item["data_theory"]}
  {ancestors}
Libs bossLib preamble

Theorem {item["prefix"]}_pure_eval_value:
  compute_eval_pure {fuel} {SHARED_CEQS} {item["prefix"]}_cexp =
    SOME (from_cv {item["prefix"]}_result)
Proof
  simp
    [{item["prefix"]}_cexp_def,
     {item["prefix"]}_result_def,
     {leaf_theorems}
     compute_eval_pure_def,
     compute_execTheory.from_cv_def]
QED

val _ = export_theory ();
'''


def render_ledger_data(groups: list[dict[str, object]]) -> str:
    ancestors = "\n  ".join(str(group["data_theory"]) for group in groups)
    cexp_leaves = [f"{group['prefix']}_cexp" for group in groups]
    result_leaves = [f"{group['prefix']}_result" for group in groups]
    cexp_tree = balanced_pair(cexp_leaves, LEDGER_DEPTH, "Num 1")
    result_tree = balanced_pair(result_leaves, LEDGER_DEPTH, "Num 1")
    return f'''(*****************************************************************************
 * Mechanically composed complete 4,173-cell exact-result ledger for genuine
 * case 10173.  The tree is balanced so every group uses its proved fuel.
 *****************************************************************************)
Theory {LEDGER_DATA_THEORY}
Ancestors
  compute
  {SHARED_DATA_THEORY}
  {ancestors}
Libs bossLib preamble

Definition {LEDGER_PREFIX}_cexp_def:
  {LEDGER_PREFIX}_cexp : compute_exp =
    {cexp_tree}
End

Definition {LEDGER_PREFIX}_result_def:
  {LEDGER_PREFIX}_result : cv =
    {result_tree}
End

val _ = export_theory ();
'''


def render_ledger_eval(groups: list[dict[str, object]]) -> str:
    ancestors = "\n  ".join(str(group["eval_theory"]) for group in groups)
    group_theorems = "\n     ".join(
        f"{group['prefix']}_pure_eval_value," for group in groups
    )
    fuel = 100000 + GROUP_DEPTH + LEDGER_DEPTH
    return f'''(*****************************************************************************
 * Proof-producing composition of every exact case-10173 numerical chunk.
 * This theorem is a bounded first-inequality authority, not the reusable
 * packed word/object refinement required for the full nonlinear corpus.
 *****************************************************************************)
Theory {LEDGER_EVAL_THEORY}[no_sig_docs]
Ancestors
  compute_evalPure
  {LEDGER_DATA_THEORY}
  {ancestors}
Libs bossLib preamble

Theorem {LEDGER_PREFIX}_pure_eval_value:
  compute_eval_pure {fuel} {SHARED_CEQS} {LEDGER_PREFIX}_cexp =
    SOME (from_cv {LEDGER_PREFIX}_result)
Proof
  simp
    [{LEDGER_PREFIX}_cexp_def,
     {LEDGER_PREFIX}_result_def,
     {group_theorems}
     compute_eval_pure_def,
     compute_execTheory.from_cv_def]
QED

val _ = export_theory ();
'''


def render_shared_data(ceqs_rhs: str) -> str:
    return f'''(*****************************************************************************
 * Mechanically normalized shared equation environment for the bounded
 * genuine case-10173 registration ledger.
 *****************************************************************************)
Theory {SHARED_DATA_THEORY}
Ancestors compute
Libs bossLib preamble

Definition {SHARED_CEQS}_def:
  {SHARED_CEQS} :
    (mlstring # (mlstring list # compute_exp)) list =
{ceqs_rhs}
End

val _ = export_theory ();
'''


def render_shared_eval() -> str:
    return f'''(*****************************************************************************
 * One-time cv translation of the shared case-10173 equation environment.
 *****************************************************************************)
Theory {SHARED_EVAL_THEORY}[no_sig_docs]
Ancestors
  compute_evalPure
  {SHARED_DATA_THEORY}
Libs
  bossLib preamble cv_transLib

val _ = cv_trans {SHARED_CEQS}_def;

val _ = export_theory ();
'''


def render_normalized_data(
    start: int,
    count: int,
    item: dict[str, str],
    cexp_rhs: str,
    result_rhs: str,
) -> str:
    prefix = f"registered_case10173_historical_chunk_{item['identifier']}"
    return f'''(*****************************************************************************
 * Mechanically normalized genuine case-10173 checked-call cells
 * [{start},{start + count}).  The common equation environment is shared.
 *****************************************************************************)
Theory {item["data_theory"]}
Ancestors compute {SHARED_DATA_THEORY}
Libs bossLib preamble

Definition {prefix}_ceqs_def:
  {prefix}_ceqs :
    (mlstring # (mlstring list # compute_exp)) list =
    {SHARED_CEQS}
End

Definition {prefix}_cexp_def:
  {prefix}_cexp : compute_exp =
{cexp_rhs}
End

Definition {prefix}_result_def:
  {prefix}_result : cv =
{result_rhs}
End

val _ = export_theory ();
'''


def render_eval(
    start: int,
    count: int,
    item: dict[str, str],
    normalized_shared_ceqs: bool = False,
) -> str:
    identifier = item["identifier"]
    prefix = f"registered_case10173_historical_chunk_{identifier}"
    if normalized_shared_ceqs:
        ancestors = f"  {SHARED_EVAL_THEORY}\n  {item['data_theory']}"
        translations = f"val _ = cv_trans {prefix}_cexp_def;"
        eval_ceqs = SHARED_CEQS
        ceqs_rewrite = f"     {prefix}_ceqs_def,\n"
    else:
        ancestors = f"  compute_evalPure\n  {item['data_theory']}"
        translations = (
            f"val _ = cv_trans {prefix}_ceqs_def;\n"
            f"val _ = cv_trans {prefix}_cexp_def;"
        )
        eval_ceqs = f"{prefix}_ceqs"
        ceqs_rewrite = ""
    return f'''(*****************************************************************************
 * Mechanically generated proof-producing evaluation of genuine case-10173
 * cells [{start},{start + count}).  The aligned job/root chunk was sliced
 * before HOL4 source registration.
 *****************************************************************************)
Theory {item["eval_theory"]}[no_sig_docs]
Ancestors
{ancestors}
Libs
  bossLib preamble cv_transLib

{translations}

val {prefix}_pure_eval =
  time cv_eval
    ``compute_eval_pure 100000
        {eval_ceqs}
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
{ceqs_rewrite}     {prefix}_result_def,
     compute_execTheory.from_cv_def]
QED

val _ = export_theory ();
'''


def generate(
    data_dir: Path,
    output_dir: Path,
    normalize_shared_ceqs: bool = False,
) -> dict[str, object]:
    if not data_dir.is_dir():
        raise ValueError(f"data directory does not exist: {data_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    if normalize_shared_ceqs and data_dir.resolve() == output_dir.resolve():
        raise ValueError(
            "normalized output directory must differ from exported data directory"
        )

    chunks: list[dict[str, object]] = []
    shared_ceqs_body_sha256: str | None = None
    shared_ceqs_rhs: str | None = None
    start = 0
    while start < CELL_COUNT:
        count = min(CHUNK_SIZE, CELL_COUNT - start)
        item = names(start, count)
        source_data_path = data_dir / item["data_file"]
        if not source_data_path.is_file():
            raise ValueError(f"missing exported data theory: {source_data_path}")
        # HOL4's generated concrete syntax contains UTF-8 quotation marks
        # even though every identity marker checked below is ASCII.
        source = source_data_path.read_text(encoding="utf-8")
        expected_markers = (
            f'Theory {item["data_theory"]}',
            f'registered_case10173_historical_chunk_{item["identifier"]}_ceqs',
            f'registered_case10173_historical_chunk_{item["identifier"]}_cexp',
            f'registered_case10173_historical_chunk_{item["identifier"]}_result',
        )
        for marker in expected_markers:
            if marker not in source:
                raise ValueError(
                    f"data theory identity drift in {source_data_path}: {marker}"
                )

        prefix = f"registered_case10173_historical_chunk_{item['identifier']}"
        ceqs_rhs = definition_rhs(source, f"{prefix}_ceqs")
        ceqs_body_sha256 = text_sha256(ceqs_rhs)
        if shared_ceqs_body_sha256 is None:
            shared_ceqs_body_sha256 = ceqs_body_sha256
            shared_ceqs_rhs = ceqs_rhs
            if normalize_shared_ceqs:
                (output_dir / f"{SHARED_DATA_THEORY}Script.sml").write_text(
                    render_shared_data(ceqs_rhs), encoding="utf-8"
                )
                (output_dir / f"{SHARED_EVAL_THEORY}Script.sml").write_text(
                    render_shared_eval(), encoding="ascii"
                )
        elif ceqs_body_sha256 != shared_ceqs_body_sha256:
            raise ValueError(
                f"equation environment drift in {source_data_path}: "
                f"expected={shared_ceqs_body_sha256} actual={ceqs_body_sha256}"
            )

        data_path = source_data_path
        if normalize_shared_ceqs:
            data_path = output_dir / item["data_file"]
            data_path.write_text(
                render_normalized_data(
                    start,
                    count,
                    item,
                    definition_rhs(source, f"{prefix}_cexp"),
                    definition_rhs(source, f"{prefix}_result"),
                ),
                encoding="utf-8",
            )
        eval_path = output_dir / item["eval_file"]
        eval_path.write_text(
            render_eval(start, count, item, normalize_shared_ceqs),
            encoding="ascii",
        )
        chunks.append(
            {
                "start": start,
                "count": count,
                "end": start + count,
                "source_data_file": str(source_data_path.resolve()),
                "source_data_sha256": sha256(source_data_path),
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

    shared_files: dict[str, object] | None = None
    if normalize_shared_ceqs:
        shared_data_path = output_dir / f"{SHARED_DATA_THEORY}Script.sml"
        shared_eval_path = output_dir / f"{SHARED_EVAL_THEORY}Script.sml"
        shared_files = {
            "data_file": str(shared_data_path.resolve()),
            "data_sha256": sha256(shared_data_path),
            "eval_file": str(shared_eval_path.resolve()),
            "eval_sha256": sha256(shared_eval_path),
        }

    groups: list[dict[str, object]] = []
    for group_index, chunk_offset in enumerate(range(0, len(chunks), GROUP_SIZE)):
        group_chunks = chunks[chunk_offset : chunk_offset + GROUP_SIZE]
        item = group_names(group_index)
        group_data_path = output_dir / item["data_file"]
        group_eval_path = output_dir / item["eval_file"]
        group_data_path.write_text(
            render_ledger_group_data(group_index, group_chunks),
            encoding="ascii",
        )
        group_eval_path.write_text(
            render_ledger_group_eval(group_index, group_chunks),
            encoding="ascii",
        )
        groups.append(
            {
                **item,
                "chunk_start_index": chunk_offset,
                "chunk_count": len(group_chunks),
                "first_cell": int(group_chunks[0]["start"]),
                "end_cell": int(group_chunks[-1]["end"]),
                "data_path": str(group_data_path.resolve()),
                "data_sha256": sha256(group_data_path),
                "eval_path": str(group_eval_path.resolve()),
                "eval_sha256": sha256(group_eval_path),
            }
        )

    ledger_data_path = output_dir / f"{LEDGER_DATA_THEORY}Script.sml"
    ledger_eval_path = output_dir / f"{LEDGER_EVAL_THEORY}Script.sml"
    ledger_data_path.write_text(render_ledger_data(groups), encoding="ascii")
    ledger_eval_path.write_text(render_ledger_eval(groups), encoding="ascii")
    aggregate = {
        "group_size": GROUP_SIZE,
        "group_depth": GROUP_DEPTH,
        "group_count": len(groups),
        "ledger_depth": LEDGER_DEPTH,
        "fuel": 100000 + GROUP_DEPTH + LEDGER_DEPTH,
        "data_theory": LEDGER_DATA_THEORY,
        "eval_theory": LEDGER_EVAL_THEORY,
        "data_file": str(ledger_data_path.resolve()),
        "data_sha256": sha256(ledger_data_path),
        "eval_file": str(ledger_eval_path.resolve()),
        "eval_sha256": sha256(ledger_eval_path),
        "groups": groups,
    }
    manifest: dict[str, object] = {
        "schema": SCHEMA,
        "status": "DEVELOPMENT_NON_RELEASE",
        "cell_count": CELL_COUNT,
        "chunk_size": CHUNK_SIZE,
        "chunk_count": len(chunks),
        "final_chunk_size": int(chunks[-1]["count"]),
        "shared_ceqs_body_sha256": shared_ceqs_body_sha256,
        "normalized_shared_ceqs": normalize_shared_ceqs,
        "shared_files": shared_files,
        "aggregate": aggregate,
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
    parser.add_argument("--normalize-shared-ceqs", action="store_true")
    args = parser.parse_args()
    manifest = generate(
        args.data_dir,
        args.output_dir,
        normalize_shared_ceqs=args.normalize_shared_ceqs,
    )
    print(f'schema={manifest["schema"]}')
    print(f'cells={manifest["cell_count"]}')
    print(f'chunks={manifest["chunk_count"]}')
    print(f'final_chunk={manifest["final_chunk_size"]}')
    print(f'manifest={args.output_dir / "ledger-manifest.json"}')


if __name__ == "__main__":
    main()
