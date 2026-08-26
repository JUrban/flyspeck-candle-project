# First real Flyspeck leaf and scale re-evaluation — 2026-08-26

## Accepted artifact

The tested-pin HOL Light producer loaded Flyspeck's checked-in
`text_formalization/general/hol-library.hl` directly and emitted both theorems
defined by that file:

- `flyspeck$IMAGE_DELETE_INJ_COMPAT`;
- `flyspeck$HAS_SIZE_2_EXISTS`.

The source is Flyspeck commit
`b47082d7b6079f00fe22308ffab225f3e0d2b285`; the producer is compatibility
commit `fa5e1542f32ebb9d5b20181f9529715c301792d0`.  This deliberately avoids the
large `Multivariate/flyspeck.ml` umbrella and establishes a genuine
Flyspeck-owned ordinary leaf before attempting the heavier representative
classes.

The committed trace has SHA-256
`c64751d819bffa16d4e7abe7c31bb1836ba3958dd60c5bfbe545495f99dec025`.
Its compiled replay evidence is:

- 171,560 commands including the header;
- table limits and peak live objects `(19125,57241,91135)`;
- the two exact saved target identities above;
- exactly `ETA_AX`, `SELECT_AX`, and `INFINITY_AX`, admitted by structural
  identity; and
- no compute initialization.

Both targets have an `EXPECT` command, so the compiled endpoint rejects any
hypothesis or conclusion mismatch before saving the theorem.  The full Candle
test harness, including malformed and unauthorized inputs, passes with this
fixture.  The producer run stayed near the core-only resource envelope: the
last observed RSS was about 5.1 GiB and the trace is about 1.6 MiB.

## Opcode audit

The new structural inspector independently parses command framing and reports
opcode coverage without constructing logical objects.  This Flyspeck trace
exercises every ordinary primitive inference rule, both term and type
instantiation, new specification, new type definition, axioms, theorem
deletion, exact expectation, and saving.  The remaining major positive-path
gap is the stateful `COMPUTE_INIT`/`COMPUTE` path.

## Foundation resource result

A fresh bounded-table run of `Multivariate/flyspeck.ml` was stopped at the
resource guardrail after about 15 minutes.  It had produced an incomplete
564 MiB trace and reached about 12.5 GiB RSS while still growing.  The worker
was terminated and only that incomplete temporary trace was removed.

This shows that replay-slot recycling fixes the footer/table-allocation defect
but does not bound HOL Light's own state for the monolithic umbrella loader.
The next full-foundation attempt must reduce the loaded dependency slice or add
a continuation design that supports real segment boundaries; repeating the
same monolithic run is not acceptance work.

## Compiled compute-context skew

A generated `COMPUTE_INIT` fixture initially failed with
`Kernel.compute: wrong theorems provided for initialization`.  A direct check
inside the compiled endpoint then called `Kernel.compute` with the source-level
`COMPUTE_INIT_THMS` list, bypassing PFT entirely, and failed identically.
Saving and loading all 62 theorems preserved the list exactly.

Therefore the failure is below PFT serialization: the downloaded compiled
artifact's embedded compute context does not accept the current source list.
No weakened comparison or misleading fixture was committed.  Positive compute
coverage now requires a source-aligned compiled endpoint or recovery of the
artifact's exact historical equation set and provenance.

## Acceptance impact

The ordinary clean-manifest part of G3 and Gate 2 now has concrete evidence.
G3 remains in progress because list/refinement and arithmetic or
certificate-heavy leaves are still required.  G2 remains in progress because
the monolithic foundation exceeded the conservative resource ceiling and no
restartable segment format exists yet.  G9 and the full L2 conclusion remain
open.
