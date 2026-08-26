# Direct producer and bounded-stream checkpoint — 2026-08-26

## Outcome

The primary roadmap route is now implemented far enough to cross both producer
boundaries: HOL Light emits Candle PFT directly, and the compiled CakeML/Candle
endpoint reconstructs its output.  The deterministic batch exporter produced a
six-target HOL Light bootstrap fixture with all required definitions, ordinary
primitive inference rules, the `num` type definition, and the three standard
HOL Light axioms.  Candle accepted the exact axioms by structural identity and
returned deterministic theorem, axiom, table, and command evidence.

The online exporter also passed a compiled end-to-end slot-recycling test.
This closes the immediate unbounded-table defect found during the first
Flyspeck foundation run, but it does not yet close G2: a fresh tested-pin run,
segmented restart evidence, and a measured Flyspeck target replay are still
required.

## Locked repository checkpoints

- Candle: `5d0c854c63874731707f52e1b88820493581e254`
- HOL4 fixture producer: `6dc37788c18e3404294bf137067046bae5904ad0`
- HOL Light current producer: `8db51a0de545f9f9d069274700348c6ea7d37275`
- HOL Light Flyspeck-tested compatibility producer:
  `fa5e1542f32ebb9d5b20181f9529715c301792d0`, based on
  `d8366986e22555c4e4c8ff49667d646d15c35f14`
- Flyspeck loader: `b47082d7b6079f00fe22308ffab225f3e0d2b285`

The compatibility worktree is separate from the current-master worktree so a
successful tested-pin replay cannot silently claim current HOL Light source
compatibility.

## Direct bootstrap evidence

`hol-light-bootstrap.pft.bin` has SHA-256
`80cf9472bcaf61c1f4bc51d2b540ee90e640acfba9a54580145dc0c2f879e7b3`.
The compiled endpoint reports:

- 8,817 decoded commands, including the header;
- table limits and peak live objects `(1148,2735,4919)`;
- six exact saved targets: `TRUTH`, `ETA_AX`, `SELECT_AX`, `INFINITY_AX`,
  the abstraction half of `num_tydef`, and `BOOL_CASES_AX`; and
- exactly three consumed axioms, all admitted by canonical structural identity
  rather than by name alone.

The current producer still generates this fixture byte-for-byte.  The complete
Candle harness also accepts the 1,181-command official HOL4 preamble and rejects
the unauthorized axiom, same-name axiom impostor, and all thirteen malformed
trace variants.

## Bounded streaming design and evidence

After `start_pft_stream`, the kernel writes each primitive inference before
returning its theorem.  The returned theorem retains only its PFT theorem ID,
so large post-start proof DAGs are not retained in the HOL process.  Definition
evidence from the pre-stream core is imported lazily.

At safe theorem boundaries the producer now:

1. emits deletion ranges for memoized type and term objects;
2. clears their producer tables and reuses the released IDs;
3. queues theorem releases only after OCaml proves their HOL theorem objects
   unreachable; and
4. drains the release queue between complete PFT commands, then reuses those
   theorem IDs.

The footer records peak slots rather than cumulative objects.  A forced-GC
smoke trace had SHA-256
`e8b0ca405e80601d30c6c935cb242b954f4b4fa78441ffeae606c45ec6562323`.
The compiled endpoint replayed 389 commands with limits and peak live objects
`(13,14,21)`, saved the exact target `|- T`, and consumed no axioms.  The trace
contained hundreds of producer commands while requiring only 21 theorem
slots.  This test also exercised type and term deletion ranges.  The batch
bootstrap fixture remained byte-identical after the change.

## Resource comparison and re-evaluation

A retained-DAG load of `Multivariate/flyspeck.ml` reached roughly 19 GiB RSS
and was stopped.  The first online-stream baseline passed that failure point
and remained near 10.6 GiB RSS while writing more than 3 GiB of trace through
the real-analysis portion of the Flyspeck foundation.  That process loaded the
pre-recycling implementation, so its cumulative footer is deliberately not a
replay acceptance artifact; it is a resource and command-volume baseline.

The finding changes the next run: merely bounding producer memory was
insufficient because Candle allocates the footer-declared slot arrays.  The
fresh compatibility run must use the committed deletion/reuse implementation,
save representative targets before closing, and replay the result in the
compiled endpoint.  Streaming bytes may vary with garbage-collection timing,
but theorem identities and replay evidence remain deterministic.

## Loader checkpoint and remaining risks

Flyspeck's loader now resolves `FLYSPECK_DIR` and `HOLLIGHT_DIR` instead of
hard-coding a developer home directory, validates marker files, and retains
convenient checkout-relative fallbacks.  The source order still comes from
Flyspeck's checked-in `Build.build_sequence_*` lists.

Open acceptance work includes:

- replaying ordinary, arithmetic/compute-heavy, and certificate-heavy
  Flyspeck targets from the tested pin;
- measuring peak slots and resources on those traces and adding restartable
  segmentation rather than relying on one multi-gigabyte file;
- auditing how much pre-stream core evidence remains live in Candle;
- attaching the compiled endpoint precisely to Candle/CakeML's soundness
  theorem; and
- closing the nonlinear and linear-program evidence paths required for L2.
