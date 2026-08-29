# Parser runtime pin preparation

Date: 2026-08-29 UTC

## Result

An isolated Candle branch now pins the complete parser-diagnostic CakeML
runtime stack while keeping every runtime and release gate closed.  The branch
is `codex/flyspeck-v13-runtime-pin-964406486`, at exact commit
`6f4345057185214016dd7f051a0f3b503950480e`.

The manifest now selects CakeML branch `codex/flyspeck-v13-runtime-stack` at
exact commit `964406486a52e1a53a94eade4cf86a666dc8055a` and HOL4 commit
`a390cbabd3a4521bab4ee20281e3e42933a8a3ae`.  Its integration record also
binds parser protocol schema 2 and the exact translation, x64 evaluation, and
x64 proof targets:

- `compiler/bootstrap/translation/compiler64ProgTheory.uo`;
- `compiler/bootstrap/compilation/x64/64/x64BootstrapTheory.uo`; and
- `compiler/bootstrap/compilation/x64/64/proofs/x64BootstrapProofTheory.uo`.

The activation status deliberately remains
`verified-source-stack-integration-pending-compiler-rebuild-and-corpus-run`.
Pinning source does not qualify machine code, permit a parser pilot, or close
S1, S2, or S3.

## Regenerated authority

The exact 400-node Flyspeck manifest was reconstructed from clean pinned
Flyspeck commit `1ce0353008eba83d3c76ae9a25c3c242e4802d53`.  The new generated identities
are:

- manifest: 820,818 bytes, SHA-256
  `0e2798eb9b643c0d602768de0a2c159f482904d1fe2acbdca9acd3d0ceb8bb70`;
- 20-input pilot descriptor: 14,715 bytes, SHA-256
  `93afbdd9e4ba2c546ca20c28c707875e9e7b2b14ac1e655c4943a421abb9c06b`;
- 400-input all-inventory descriptor: 206,558 bytes, SHA-256
  `f407e98f5cdcab161c49fbc50c0a655a32806e6b90d8522ecd39363fe799e9a6`.

The all-inventory source-preparation helper's closed authority table was
updated to those exact manifest and descriptor byte records.  This is
required independently of the descriptors' own canonical-selection checks;
leaving the old records in place correctly caused source preparation to fail
before reading the corpus.

## Validation

- fresh manifest check: 297 roots, 400 source nodes, 43 generated inputs;
- strict parser descriptor checks: 20 exact pilot nodes and 400 exact
  all-inventory nodes;
- closed all-inventory/preparation suite: 72 tests passed in 127.331 seconds;
- complete lightweight Candle discovery: 330 tests passed in 164.411 seconds;
- both Candle commits are clean: `b59d6d0d96d2eca7b5bb3c939b52e00c6c5e3f22`
  pins and regenerates the authority artifacts, and
  `6f4345057185214016dd7f051a0f3b503950480e` refreshes the helper's exact
  authority records.

No parser process, pilot, all-inventory runtime, native HOL cache, or second
Holmake was launched.  The existing cold proof replay remained the sole
Holmake and advanced through `to_flatProg` successfully before entering
`to_closProg`, with no live swap traffic or resource alert.

## Next gate

The branch is preparation only until the cold replay completes all four
stages.  On success, the critical path is the exact cache-disabled canonical
x64 bootstrap from this committed Candle authority, native link and provenance
validation, a fresh 20-input parser pilot, and then a newly materialized
400-input parser run.  Parser failures will then be repaired in batches before
starting direct S1/S2/S3 source execution.
