# Response to `audit1.md` — 2026-08-27

Reviewed input SHA-256:
`03be4c7935505eb480201775872be8dd0d87b1b38b31c03e9c6f4da182df5acf`.

## Verdict

The audit's central criticism is accepted.  A complete
`Flyspeck source -> HOL Light -> PFT -> compiled Candle` replay is strong
independent validation, but it is not source substitution and cannot satisfy
roadmap v1.3 milestone S2 or S3.  The governing release target is therefore S3
direct source execution, while the already-running PFT computation continues
as a subordinate P1 validation lane.

The audit also correctly rejects two possible evidence shortcuts: saved PFT
fixtures are not the Great 100 source corpus, and parser-only support for
OCaml `open` is not the verified Dopen gate.  Both must be closed using the
specific semantic, inference, proof, and fingerprint evidence required by the
v1.3 roadmap.

## Corrections already applied

- `README.md`, `manifest.lock.toml`, and `docs/requirements-v1.3.md` now name
  S3, not the older L2 replay result, as the production target.
- The manifest forbids a HOL Light runtime, PFT producer, or unchecked theorem
  import in an S2/S3 production run.
- PFT output is labeled independent hostile-input and differential evidence;
  its final theorem cannot close a source-execution gate.
- A clean, machine-readable 65-load Great 100 baseline is running separately
  from the PFT producer.  Failures remain release failures and are inventoried
  rather than hidden by fixture coverage.
- Verified Dopen/current-CakeML reconciliation and a corpus-derived
  compatibility ledger are active critical-path work streams.

## Current evidence and open gates

The first Great 100 baseline failure is already informative: after loading
`Library/floor.ml`, Candle rejects `100/bertrand.ml` before the declaration
`let num_of_float =`.  The full baseline is being allowed to continue so that
the repair plan is based on the complete compatibility-class inventory rather
than the first symptom.

The Dopen audit has established that the historical patch is not an
end-to-end verified implementation on current CakeML: declaration/environment
semantics and proof-stack obligations must be specified and rebuilt.  A
pinned OCaml oracle slice is the first committed artifact, not proof of gate
completion.

The immediate critical path is:

1. close the compatibility ledger and verified Dopen proof stack;
2. make all 65 Great 100 loads green with canonical semantic fingerprints;
3. implement the deterministic, manifest-rooted direct Flyspeck loader;
4. reach direct nonlinear and LP leaves and close their complete inventories;
5. qualify cumulative scale, deterministic checkpoints, and negative tests;
6. obtain two clean identical S3 runs plus one matching resume run.

## Retained PFT value and claim boundary

The live PFT run is not discarded.  Its canonical theorem and assumption
evidence, complete certificate coverage, resource history, restart behavior,
and compiled replay will form a demanding cross-check against the later direct
source run.  Its completion marker must say full HOL Light-to-PFT-to-Candle
validation and must never say that Candle replaced HOL Light.

This response closes the audit's labeling and planning objection.  It does not
close any implementation gate in the governing S3 ledger.
