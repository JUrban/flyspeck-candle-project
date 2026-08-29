# Direct evidence-v3 independent re-review — 2026-08-29

## Verdict

**FAIL: one P1 runtime blocker remains at outer action 295.**

The re-review covered Candle direct-evidence branch commits through
`451b7ad9494ca35e859e76b3a9c0c23062de27cb`.  The two earlier evidence-reader
findings are repaired: schema-3 completed receipts now require exact success
state, action identities, closure records, and boundary-appropriate
fingerprints; the selected closure now excludes `build/use_serialization.hl`
and `update_database_310.ml`, introduces `serialization.hl` and
`update_database_400.ml` only at action 295, and distinguishes outer, nested,
generated-control, and derivation-only roles.  The exact earlier forged receipt
is rejected.  The late-interrupt failed-receipt edge is retained after
`451b7ad`.

The focused independent Python run passed 76/76 tests:

```text
python3 -m unittest \
  candle.test_flyspeck_stratum_runtime \
  candle.test_flyspeck_normalize \
  candle.test_flyspeck_manifest

Ran 76 tests in 3.059s — OK
```

Those tests do not exercise the remaining nested-directive interaction.

## P1: the action-295 nested source action corrupts the outer action protocol

The selected normalization of
`text_formalization/general/serialization.hl` replaces the OCaml-version
conditional with:

```ocaml
#flyspeck_loadt "general/update_database_400.ml";;
```

This phrase executes while the outer generated driver is already processing
`#flyspeck_needs "general/serialization.hl"`.

The currently verified boot has one global
`Cakeml.pendingLoadedSourceId`, not a stack.  The outer `#flyspeck_needs` sets
that slot to the serialization identity before pushing the source.  The nested
`#flyspeck_loadt` overwrites the same slot with the update-database identity,
then its appended completion phrase adds that identity to
`loadedSourceIds` and clears the slot.  When the outer appended completion
phrase resumes, it sees `None` and aborts with
`missing Flyspeck source identity`.

There is a second independent incompatibility even if the pending slot were
not lost.  The setup-side outer transition accepts a new action only when

```ocaml
current = expected_outer_identity :: previous
```

but the nested `#flyspeck_loadt` also prepends the update-database identity.
The action-295 delta therefore contains at least two identities and is rejected
as an unexpected loader-identity delta.

The new closure classifies `update_database_400.ml` as an expected nested
source that is not loader-observed.  That classification is inaccurate for
the current source: `#flyspeck_loadt` is precisely a custom loader action that
updates the exported logical ledger.

Relevant exact locations are:

- Candle `candle/flyspeck_normalizations.json`, operation
  `PROJECT-TOPLOOP-S3-UPDATE-DATABASE-001-STATIC-LOAD`;
- CakeML `candle/prover/candle_boot.ml`, the outer pending-identity protocol
  around lines 842--865 and nested `#flyspeck_loadt` protocol around
  lines 893--915;
- Candle `candle/flyspeck_stratum_setup.ml`, the flat ledger-delta check around
  lines 110--132.

The added native-OCaml transition fixture is useful but insufficient: it
manually mutates a flat ledger and tests `load`, `skip-ledger`, and mismatch.
It does not run one custom source action nested inside another and therefore
cannot expose either pending-slot overwrite or the two-identity delta.

## Smallest credible repair boundary

Do not launch or approve a final direct run under this protocol.  Repair needs
either:

1. a newly verified/rebuilt boot with stack-safe nested source-action state and
   nonce-bound nested events, followed by an outer transition that validates
   the exact nested-plus-outer delta; or
2. a separately justified semantics-preserving redesign that removes the
   nested custom directive while retaining the exact selected 4.14.1 branch,
   load order, source identity, and fail-closed behavior.

Whichever route is chosen needs a compiled nested-directive fixture before a
long run.  The existing evidence must remain nonpromotable, as it already
declares.

## Other re-review results

- The exact original failed-to-completed receipt counterexample is rejected.
- Closure counters observed independently were: count 0 = 99; count 295 =
  389; count 296 = 393; final count 297 = 399.  The first two contain neither
  serialization branch; count 296 and final contain only serialization plus
  `update_database_400.ml`, never the opt-in loader or `_310` branch.
- Generated executed controls and derivation-only `flyspeck_full_build.ml` are
  separated from observed outer and expected nested records.
- The documentation now honestly limits `Filename.temp_file` preservation to
  proof state, source-action semantics, and semantic fingerprints, and records
  the two intentionally removed diagnostic stdout lines.
- Schema 2 remains disjoint and all evidence-v3 records remain explicitly
  nonpromotable.

## Resolution and final scoped verdict

The P1 above was repaired and independently re-reviewed at these exact
revisions:

- CakeML `0e97a1ab86924e905e1d1c893191651197b82f6e`;
- Candle `baac7909f1dae44928e8990a2926370444801fa4`.

CakeML now keeps pending source identities in a LIFO stack.  A successful
nested load commits its identity before the resumed outer load commits its
own, while an evaluator error clears the entire pending stack.  Candle action
295 requires the exact head-first logical-ledger delta
`[serialization; update_database_400]`; missing, reordered, extra, or skipped
nested identities fail before the action marker.  The nested source is now
classified as `observed-nested-source`.

A later integration check also found that the boundary checker still projected
the old three-field action-event tuple after events gained an exact expected
delta.  Candle `baac790` changes that projection to the four-field event and
adds a compiled OCaml extraction regression.  The complete Candle Python suite
passed 224/224 in the parent check.  The final independent focused check passed
120/120, the exact CakeML compiled stack fixture passed 1/1, and diff checks
were clean.

**Final scoped verdict: PASS with no remaining P0/P1/P2 finding in this
nested-ledger repair.**  This is not approval for a release run.  A fresh
runtime must still be proof-built from the pinned CakeML source and exercised
end to end.  The separately documented lack of a complete physical-loader
trace and canonical lexical-alias resolution also remains nonpromotable.
