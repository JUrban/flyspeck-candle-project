# Flyspeck in Candle

This repository coordinates the implementation needed for Candle/CakeML to
execute the pinned Flyspeck/HOL Light source workload.  The governing v1.3
release target is S3: direct source execution plus HOL-side nonlinear/LP
evidence closure, with no HOL Light runtime in the production path and with the
Isabelle tame-graph classification retained as an explicit premise.  S2 is the
decisive source-substitution milestone and S4 is tracked separately.

The parallel PFT validation architecture is specifically
`Flyspeck source -> HOL Light producer -> hostile PFT -> compiled Candle`.
It can prove that Candle reconstructs the complete HOL-side proof and evidence,
but it does **not** satisfy S2 or S3.  It is retained as an independent checker,
differential oracle, and distribution artifact while verified Dopen, OCaml
compatibility, the direct loader, and source-driven evidence closure form the
primary critical path.

The upstream repositories are checked out as sibling directories under
`../repos/`.  Development happens on `codex/*` branches in those repositories;
this repository holds the locked manifest, cross-repository tooling, acceptance
criteria, and progress reports.

Current work is at the Gate 1 / Gate 2 boundary.  The compiled Candle endpoint
consumes both official HOL4-writer traces and a direct HOL Light bootstrap
trace, rejects the committed malformed/unauthorized suite, enforces exact
standard-axiom identities, and returns deterministic replay evidence.  The
HOL Light producer can write primitive inferences online with bounded producer
memory and can safely delete and reuse replay slots.  The tested-pin producer
has now emitted two real theorems from Flyspeck's `general/hol-library.hl`, and
the compiled endpoint replayed their exact statements under the locked axiom
policy.  Pinned, digest-checked extractions of Flyspeck's original
list/refinement and real-arithmetic/refinement proof blocks also replay exactly,
completing the three-class producer route selection.  Candle's compute source
is now aligned with the verified kernel's pair-condition equation, and a
source-derived 62-equation fixture positively exercises `COMPUTE_INIT` and
`COMPUTE` through the compiled endpoint.  The bounded producer now also has a
proved DMTCP checkpoint/kill/restore boundary and a head-locked supervisor for
the real Flyspeck `main` and `full` source sequences.  The complete LP archive
inventory is pinned, long LP/nonlinear phases have internal restart boundaries,
and the full target now eliminates both HOL-side premises to leave only the
Isabelle tame-classification premise.  The remaining acceptance work includes
measuring, completing, and replaying that full run and a Flyspeck-specific
compute-heavy leaf.

## Layout

- `manifest.lock.toml`: immutable source and toolchain identities.
- `docs/requirements-v1.3.md`: governing source-substitution gates and evidence.
- `docs/requirements.md`: superseded v1.2 PFT-validation ledger retained for
  the independent replay lane.
- `docs/full-l2-runbook.md`: fresh/resume operation, evidence outputs, and the
  DMTCP trust boundary for the full L2 run.
- `docs/progress/`: dated, evidence-backed interim reports.
- `scripts/verify-lock.sh`: checks local source identities and roadmap hash.
- `scripts/test-producer-resume.sh`: destructive-process restart smoke test.
- `scripts/run-restartable-flyspeck-export.sh`: resumable real-build exporter
  and compiled replay supervisor.

New supervised runs default to uncompressed DMTCP images because the producer
retains only its latest image and the installed DMTCP documents substantially
lower checkpoint latency in this mode.  Set `CANDLE_PFT_DMTCP_GZIP=1` to opt
into compression.  The setting is locked in the run state; state directories
created before this option was added retain their historical gzip mode, which
the supervisor adopts automatically on resume unless an explicit conflicting
override is supplied.

Nothing in the producer, translator, merger, or orchestration repository is in
the logical trust boundary.  Release traces are hostile input to the compiled
Candle checker.
