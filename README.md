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
memory and can safely delete and reuse replay slots.  The next acceptance step
is a bounded rerun at the Flyspeck-tested HOL Light pin followed by exact replay
of representative Flyspeck targets; Gate 1 still needs its final explicit
compiled-soundness audit.

## Layout

- `manifest.lock.toml`: immutable source and toolchain identities.
- `docs/requirements.md`: roadmap-derived gates and evidence required to close
  them.
- `docs/progress/`: dated, evidence-backed interim reports.
- `scripts/verify-lock.sh`: checks local source identities and roadmap hash.

Nothing in the producer, translator, merger, or orchestration repository is in
the logical trust boundary.  Release traces are hostile input to the compiled
Candle checker.
