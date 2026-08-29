# Authenticated all-inventory parser profile

Date: 2026-08-29 UTC

## Result

The parser-only acceleration gate now has two explicit, non-relabelable
profiles on Candle branch `codex/flyspeck-v13-runtime-integration-v4`:

- `pilot`: plan schema 1, receipt schema 4, and exactly 20 ready inputs;
- `all-inventory`: plan schema 2, receipt schema 5, and exactly 400 ready
  inputs with one fresh parser attempt per input.

The all-inventory implementation was committed at
`cf374cbd12e1e7b281473472c097d36a7c247c10`.  A hostile review found no P0
issue but identified four P1 contract weaknesses: permissive schema-1
recognition, incomplete schema-5 snapshot closure, coercive JSON numeric
comparisons, and validation only before final directory publication.  It also
found stale operator documentation.  These findings were fixed at
`c24fb8ab2a400158ceeababe094edce168077e76`.

The final implementation requires exact schema-specific top-level and input
field sets, exact integer types, complete authority and prepared-plan
inventories for both profiles, complete original-source and transcript
inventories, and exact result-tree closure.  Publication retains stable
directory descriptors, performs descriptor-relative no-replace rename,
checks the published inode identity, and revalidates the opened tree after the
rename.  Read-only modes are not claimed as same-UID immutability; downstream
consumers must always revalidate the closed evidence.

An independent follow-up review of the publication changes reported no
remaining P0, P1, or P2 finding.  It injected failures during directory-open
and post-rename checks and observed no leaked descriptors.  The dedicated
parser suite passes 56 tests under `/usr/bin/python3 -I -S`; the complete
lightweight Candle discovery passes 330 tests.

## Exact committed materialization

Source-only materialization was rerun from the clean final Candle head.  The
committed descriptor check passed with all 400 manifest nodes, and the plan
was published at:

`/project/flyspeck-candle-runs/all-inventory-materialization-c24fb8a`

The result contains 402 files and occupies 54 MiB.  Its exact identities are:

- plan SHA-256:
  `4aa03a97ed058658cfda901dfd1e67dc13f5fe080b907c93150082a58126c60f`;
- host-materialization SHA-256:
  `82a5f5e83328f8e2a41138b2efb085e57062f7c357aa1e4eee59e6a32df26eaa`;
- 400 inputs, 400 ready, zero unsupported;
- 382 exact-original and 18 exact-normalized inputs;
- 727 authenticated loader sites; and
- 400 distinct ordered source keys and prepared paths.

This is still source preparation, not a parser result and never S1/S2/S3
evidence.  The protocol CakeML commit
`964406486a52e1a53a94eade4cf86a666dc8055a` remains in the cold proof replay.
After that replay succeeds, the next critical-path steps are to update the
pin, run the canonical cache-disabled x64 bootstrap and link, run the exact
20-input pilot, then run this 400-input profile from a newly reconstructed
plan at the final Candle head.

## Concurrent evidence status

At the closest checkpoint, the cold replay had completed
`candle_kernelProg` and advanced through `candle_kernel_vals` and
`candle_prover_inv` to closure marker `[↓32]`, with one Holmake and no live
swap pressure.  The schema-v9 reference sweep had published 18 of 130 targets
with zero failures or interruptions.  No native HOL cache, linked parser
runtime, pilot process, or all-inventory parser process was used for this
implementation checkpoint.
