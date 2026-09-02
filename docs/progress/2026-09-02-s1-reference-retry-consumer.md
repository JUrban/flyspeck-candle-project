# S1 reference retry-consumer repair — 2026-09-02

## Finding

The independently audited schema-v9 reference root
`s1-reference-v9-csdp-two-sweep-652a18a-95bb84f` is closed at 130/130
selected successes.  It also preserves one interrupted sweep-2 attempt for
`100/independence` and selects the authenticated `attempt-0002` retry.  The
receipt has one failure-ledger entry and no publication interruption.

The current Candle approval consumer and project finalizer nevertheless
required every row to contain only `attempt-0001`, required the aggregate
failure count to be zero, and reconstructed successful artifact paths with a
literal `attempt-0001`.  Therefore the accepted reference root could not have
entered the current-binary comparison path.  This was a fail-closed consumer
defect, not a defect in the retained reference execution.

A second stale equality check required the retained producer collector to be
byte-identical to the later Candle approval consumer.  The actual producer
collector SHA-256 is `f91d1fdb...`; the current descendant reviewer validator
is `22af9401...`.  The project finalizer already requires these roles to be
different.  Candle now validates the producer path/head/at-head hash and binds
it to the authenticated collection contract, while replaying the retained
artifacts with the current committed consumer.  This restores the intended
independent-review boundary without accepting an unbound producer.

## Repair boundary

Candle branch `codex/flyspeck-v13-s1-reference-retry-approval`, based on
`cb3bbcb7127b04154536b6f8ca6e8b8498d62774`, now accepts a retry only when:

- attempt names form a contiguous `attempt-0001` through `attempt-N` sequence;
- every attempt before `N` is exactly `interrupted` and retains canonical
  candidate, plan, request, and transcript records;
- attempt `N` is the sole selected complete attempt;
- the success receipt and every controller artifact use attempt `N`; and
- the aggregate failure count and ordered failure ledger exactly equal the
  interrupted row projections.

Publication interruptions remain forbidden.  Gaps, reordering, overwritten
attempts, malformed interruption artifacts, an earlier selected success, or a
different aggregate ledger fail closed.

The same policy is implemented independently in
`scripts/finalize-top100-report.py`.  The exact retained production receipt was
read through the repaired Candle consumer: schema 4, 130 successes, and the
expected sweep-2 target-036 `attempt-0002` nonce
`4829c2fe93bd0c2c6e8d6a2e1a4568cf9e15a5d71ed927719a9ef55f818008e3`
were accepted.

## Verification and status

- Candle `test_top100_manifest`: 14/14 pass, including a retained interrupted
  attempt plus retry, a distinct producer/reviewer validator, and negative
  sequence/ledger mutations.
- Finalizer focused positive and retry-corruption tests: 3/3 pass.
- Full finalizer suite: 66 functional tests passed; one assertion expected the
  former generic diagnostic and was updated to the new stricter `attempt
  sequence` diagnostic.  Its focused rerun passes.

The consumer repair by itself only makes the audited reference collection
consumable; it does not qualify the current Candle binary, establish S1, or
advance S2/S3.  The canonical bootstrap, ordinary link, and 20/400 parser
gates remain ahead of approval installation and the two current-binary
Great-100 runs.

## Approval assembly

After the repair passed, the independent review decision at project commit
`424532f2895f4bc6c9f3eb30df9e9c2d27ac3831` was materialized on the same
separate Candle branch.  Commit
`4c20d9d` (`Approve audited Great 100 reference identities`) retains 1,172
ordinary single-link evidence files for the 130 selected attempts plus the
collection contract/receipt.  The approval contains 65 ordered target records,
two nonce-distinct runs per target, and all 97 expected theorem identities.

- approval SHA-256:
  `57adc0ce2968d155c56c918ef96447cd89c330dd6ffc4203e717f203deeb37f0`;
- inventory contract SHA-256:
  `3021163dbf52b66cb8e8f733b5eb7c409ccd9f21b94e20d55cb3569388fb8d99`;
- regenerated manifest SHA-256:
  `2c5d99eea9847f2ec9e9556dd8076b5505c45d47f7c33fd7135259d5e99b875d`;
- retained evidence apparent size: approximately 2.5 GiB; and
- structural audit: zero symlinks or multiply linked files.

The complete approval consumer replay passed once during assembly, and the
independent manifest `--check` replay passed again with 65 targets, 66 source
files, and the one explicit exclusion.  This is an approved reference input,
not current-binary S1 evidence.  It must be integrated only after the retained
`cb3bbcb...` parser gates, then linked at its new exact head before the two
current Candle Great-100 runs.
