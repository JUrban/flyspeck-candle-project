# Full Flyspeck L2 export and Candle replay

Run from the project checkout after `scripts/verify-lock.sh` succeeds.  The
repository layout and OCaml switch are locked by `manifest.lock.toml`; the
supervisor additionally refuses dirty producer, Flyspeck, or Candle checkouts.

```sh
./scripts/run-restartable-flyspeck-export.sh \
  full /absolute/path/full-l2.pft.bin /absolute/path/full-l2-state
```

The same command resumes an interrupted run.  The state directory locks the
sequence, output path, three logical repository heads, source/work checkpoint
intervals, DMTCP compression mode, and the LP/archive/nonlinear input hashes.
Changing one of those values is a hard error.  Runs created before the
compression lock use their historical gzip mode; new runs default to
uncompressed images because only the latest image is retained and checkpoint
latency matters more than image size.  Set `CANDLE_PFT_DMTCP_GZIP=1` before a
fresh invocation if storage is constrained.

The producer records a flushed PFT boundary before asking DMTCP to checkpoint
and kill it.  On restore, it verifies the in-memory logical counters, truncates
any stale post-boundary trace tail, and continues from the exact HOL process
state.  The supervisor retries a failed restored generation from the last
recorded boundary, using a new monotonically numbered generation log.  Source
files checkpoint in groups of ten, each LP certificate shard is a work unit,
and serialized nonlinear cases checkpoint in groups of 25 by default.

DMTCP images are executable process state.  Restore only images created by the
same trusted local run; never accept one as proof evidence or from an untrusted
source.  The final `.pft.bin` remains hostile input and is accepted only after
the compiled CakeML/Candle checker reconstructs it.

On successful export the supervisor writes:

- `status.tsv`, ending in `complete` with the final byte and table counters;
- `opcodes.json`, a structural command inventory;
- `SHA256SUMS`, pinning the final PFT bytes;
- `resources.tsv`, periodic peak-process RSS and CPU samples across the full
  supervisor process tree (producer, restarts, structural inspection, and
  compiled replay), plus trace and checkpoint sizes;
- `resource-summary.txt`, the corresponding peak values, sample span, final
  status, trace size, and trace SHA-256;
- `logs/generation-NNNN.log`, preserving every producer attempt; and
- `replay.log`, which must contain both `Success!` and
  `CANDLE_FULL_REPLAY_OK` and no `EXCEPTION:` line.

The full replay admits only the three structurally pinned HOL Light standard
axioms and requires these saved targets in order:

1. `flyspeck$Linear_programming_results.linear_programming_results_th`;
2. `flyspeck$Mk_all_ineq.the_nonlinear_inequalities`;
3. `flyspeck$The_kepler_conjecture.tame_nonlinear_imp_kepler_conjecture`; and
4. `flyspeck$Candle_flyspeck_l2.tame_imp_kepler_conjecture`.

The fourth theorem has statement
`import_tame_classification ==> the_kepler_conjecture`.  This is the selected
L2 boundary: Candle checks the HOL-side LP and nonlinear evidence, while the
Isabelle tame-classification result remains an explicit premise.
