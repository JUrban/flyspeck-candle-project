# Flyspeck in Candle

This repository coordinates the implementation needed to check the HOL Light
side of Flyspeck with Candle.  The default release target is roadmap level L2:
kernel replay plus HOL-side nonlinear/LP evidence closure, while retaining the
Isabelle tame-graph classification as an explicit premise.  L1 is the first
integration milestone and L3 is tracked separately.

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
- `docs/requirements.md`: roadmap-derived gates and evidence required to close
  them.
- `docs/progress/`: dated, evidence-backed interim reports.
- `scripts/verify-lock.sh`: checks local source identities and roadmap hash.
- `scripts/test-producer-resume.sh`: destructive-process restart smoke test.
- `scripts/run-restartable-flyspeck-export.sh`: resumable real-build exporter
  and compiled replay supervisor.

Nothing in the producer, translator, merger, or orchestration repository is in
the logical trust boundary.  Release traces are hostile input to the compiled
Candle checker.
