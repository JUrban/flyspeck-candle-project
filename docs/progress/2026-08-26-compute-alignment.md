# Verified compute source alignment — 2026-08-26

## Outcome

The compiled Candle endpoint now has positive, source-aligned coverage for
`COMPUTE_INIT` and `COMPUTE`.  A direct call using Candle's former
`COMPUTE_INIT_THMS` failed below PFT with `Kernel.compute: wrong theorems
provided for initialization`.  Comparing `candle/compute.ml` with the verified
equations in CakeML's `candle/prover/compute/computeScript.sml` isolated the
mismatch: the `Cexp_if` pair case must select the false branch `q1`, while the
Candle source selected `p1`.

Candle commit `b55243eb7776d37957d64b5a99365cd1dd4bd600` corrects that
definition and replaces the downstream convenience theorem that had encoded
the same old semantics.  The complete source file then loaded without an
exception in the compiled executable, and a direct verified-kernel call
returned `|- Cexp_num (NUMERAL _0) = Cexp_num (NUMERAL _0)`.

## Reproducible PFT evidence

The HOL Light compatibility producer loads the corrected `candle/compute.ml`
and dependency-exports all 62 exact theorems in `COMPUTE_INIT_THMS`.  A
deterministic binary generator structurally validates those named saves and
appends 62 `LOAD` commands, `COMPUTE_INIT`, a zero-valued compute expression,
`COMPUTE`, exact `EXPECT`, and `SAVE`.

The locked `compute-zero.pft.bin` has SHA-256
`5f63f5ca8e280bf83e1c9838884130199891569b48912a85b2042a791e0b46cc`.
The compiled endpoint reports:

- 1,311,902 replay commands;
- table limits and peak live objects `(200544,585972,525260)`;
- 62 initialization equations and one checked result named
  `candle$COMPUTE_ZERO`;
- exactly the three authorized HOL Light axioms; and
- an initialized compute context.

The compact dependency export peaked at about 5.4 GiB RSS, close to the
core-only producer envelope, and the final fixture is about 13 MiB.  The full
Candle PFT suite passes with this fixture, both Flyspeck fixtures, the bootstrap
and official traces, and every committed malformed/unauthorized rejection.

## Trust and remaining scope

Neither exporter nor binary generator is trusted.  The generator's transaction
is parsed as hostile PFT input; the compiled verified kernel checks the exact
initialization equations and constructs the compute theorem, while `EXPECT`
checks its hypotheses and conclusion.  The ordinary HOL Light process uses a
placeholder `Kernel.compute` name only so the source wrapper can be defined;
that placeholder is never invoked to create evidence.

This checkpoint fixes the source/release mismatch and proves the primitive's
positive PFT path.  It does not provide a Flyspeck-specific compute equation,
restartable full-foundation export, nonlinear/LP certificates, or full L2
replay.  G2, G8, G9, and G11 therefore remain open or in progress.
