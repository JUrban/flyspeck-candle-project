#!/usr/bin/env python3
"""Measure the current reflected p=0 worklist in a fresh Candle process."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import select
import subprocess
import time
from pathlib import Path


READY = "CANDLE_CV_TAME_P0_WORKLIST_PREPARED_READY DEVELOPMENT_NON_RELEASE"
RESULT = (
    "CANDLE_CV_TAME_P0_WORKLIST_PREFIX_OK DEVELOPMENT_NON_RELEASE fuel=1000 "
    "visited=239 final_visits=0 stage0_children=239 retained_children=238 "
    "final_pruned=1 maximum_frontier=30 frontier=0 finals=0 complete=true"
)
DONE = "CANDLE_TAME_P0_AUDIT_COMMAND_DONE DEVELOPMENT_NON_RELEASE"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def constrained_child() -> None:
    os.sched_setaffinity(0, {0, 1})
    ceiling = 20 * 1024 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (ceiling, ceiling))


def read_until(
    process: subprocess.Popen[str], transcript, marker: str, timeout: float
) -> None:
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"timeout waiting for {marker}")
        readable, _, _ = select.select([process.stdout], [], [], remaining)
        if not readable:
            raise TimeoutError(f"timeout waiting for {marker}")
        line = process.stdout.readline()
        if line == "":
            raise RuntimeError(
                f"Candle exited with {process.poll()} before marker {marker}"
            )
        transcript.write(line)
        transcript.flush()
        if marker in line:
            return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candle-binary", required=True, type=Path)
    parser.add_argument("--runtime-cwd", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=False)
    transcript_path = args.output_dir / "candle.log"
    receipt_path = args.output_dir / "receipt.json"
    input_path = args.output_dir / "input.ml"
    input_text = (
        '#use "hol.ml";;\n'
        f'load_path := "{args.source_root}" :: !load_path;;\n'
        'needs "candle/prepare_cv_compute_tame_graph_worklist_p0.ml";;\n'
    )
    input_path.write_text(input_text, encoding="utf-8")

    start = time.monotonic()
    with transcript_path.open("w", encoding="utf-8") as transcript:
        process = subprocess.Popen(
            [str(args.candle_binary), "--candle"],
            cwd=args.runtime_cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            preexec_fn=constrained_child,
        )
        try:
            process.stdin.write(input_text)
            process.stdin.flush()
            read_until(process, transcript, READY, 1800.0)
            prepared = time.monotonic()

            process.stdin.write(
                "let candle_tame_audit_result = "
                "candle_cv_tame_worklist_run_p0_prefix 1000;;\n"
                f'print_endline "{DONE}";;\n'
            )
            process.stdin.flush()
            read_until(process, transcript, RESULT, 600.0)
            read_until(process, transcript, DONE, 60.0)
            evaluated = time.monotonic()

            process.stdin.close()
            return_code = process.wait(timeout=60.0)
            finished = time.monotonic()
            if return_code != 0:
                raise RuntimeError(f"Candle exit status {return_code}")
        except BaseException:
            process.kill()
            process.wait()
            raise

    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    receipt = {
        "status": "DEVELOPMENT_NON_RELEASE",
        "result_marker": RESULT,
        "preparation_elapsed_seconds": round(prepared - start, 6),
        "evaluator_and_output_elapsed_seconds": round(evaluated - prepared, 6),
        "handoff_elapsed_seconds": round(finished - evaluated, 6),
        "total_elapsed_seconds": round(finished - start, 6),
        "peak_child_rss_kib": usage.ru_maxrss,
        "cpu_affinity": [0, 1],
        "virtual_memory_ceiling_bytes": 20 * 1024 * 1024 * 1024,
        "candle_binary": str(args.candle_binary),
        "candle_binary_sha256": sha256(args.candle_binary),
        "source_root": str(args.source_root),
        "prepare_source_sha256": sha256(
            args.source_root / "candle/prepare_cv_compute_tame_graph_worklist_p0.ml"
        ),
        "worklist_source_sha256": sha256(
            args.source_root / "candle/cv_compute_tame_graph_worklist.ml"
        ),
        "transition_source_sha256": sha256(
            args.source_root / "candle/cv_compute_tame_graph_transition.ml"
        ),
        "input_sha256": sha256(input_path),
        "transcript_sha256": sha256(transcript_path),
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
