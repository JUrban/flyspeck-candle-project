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

Current work is Phase 1 / Gate 1.  The source-level Candle endpoint now consumes
an official HOL4-writer trace and rejects the committed malformed/unauthorized
suite.  The remaining Gate 1 work is to cover the full command surface, make
the axiom policy release-grade, expose deterministic replay evidence, and tie
the endpoint to a compiled Candle/CakeML soundness statement.

## Layout

- `manifest.lock.toml`: immutable source and toolchain identities.
- `docs/requirements.md`: roadmap-derived gates and evidence required to close
  them.
- `docs/progress/`: dated, evidence-backed interim reports.
- `scripts/verify-lock.sh`: checks local source identities and roadmap hash.

Nothing in the producer, translator, merger, or orchestration repository is in
the logical trust boundary.  Release traces are hostile input to the compiled
Candle checker.
