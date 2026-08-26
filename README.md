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

Current work is Phase 1 / Gate 1: align and harden the existing Candle PFT
consumer against the current HOL4 PFT writer, build both sides, and establish a
positive/negative trace suite.

## Layout

- `manifest.lock.toml`: immutable source and toolchain identities.
- `docs/requirements.md`: roadmap-derived gates and evidence required to close
  them.
- `docs/progress/`: dated, evidence-backed interim reports.
- `scripts/verify-lock.sh`: checks local source identities and roadmap hash.

Nothing in the producer, translator, merger, or orchestration repository is in
the logical trust boundary.  Release traces are hostile input to the compiled
Candle checker.
