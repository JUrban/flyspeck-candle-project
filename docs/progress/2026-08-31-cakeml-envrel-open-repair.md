# CakeML open-environment relation repair

Date: 2026-08-31 UTC

## Outcome

The exact-head warm reverse-dependency gate at CakeML `32580b0b...` exposed
the first complete build of the previously unbuilt `env_rel_open` candidate.
The initial failure and a subsequent proof-search cost are repaired in CakeML
commit:

- commit `731f386bc95b528d46fa4e081b3d14ba8a26edc0`;
- tree `172d1c642bf5e35c478e781172391a5d93f18d96`;
- branch `codex/flyspeck-v13-runtime-stack`;
- one changed file,
  `compiler/inference/proofs/envRelScript.sml` (`40+`, `46-`).

This is a proof-only change.  It neither changes the runtime/compiler source
program nor qualifies a compiled Candle artifact.

## Failure evidence

Warm attempt
`/project/flyspeck-candle-runs/cakeml-parser-dopen-warm-proof-32580b0b-attempt-004`
ran from `2026-08-31T05:17:10Z` to `05:33:39Z`.  It passed
`x64_targetProof` and `x64_configProof`, then failed while building
`envRelTheory.uo` at `env_rel_open_tenv_exists`.

The sealed receipt records exit 1, exact CakeML/HOL4 heads, a 112.5-GiB
address-space limit, and identical pre/post hashes for the reused stage-3
bootstrap products.  Its SHA-256 identities are:

| Object | SHA-256 |
| --- | --- |
| receipt | `d2378aee5a1c70e1150f96b75dad9d85b573a9b9b22a8f334727a8b55e965e76` |
| log | `8cf56b5c82167ad61b09ed3ae4f85c01a71603dc11f79aae7766367971e77ec0` |
| timing | `552a92c742a4f20b143baf41c1e1fa05bd172eedee80735d7355b8e5b8d922c2` |
| runner | `83e963396e9a21df52485d42a37efb32e01d0476b2b595e90cfa9c0072967468` |

## Repair

The two existence bridges now instantiate
`nsOpen_some_from_same_mod_domain` with the source component fact and the
module-domain equivalence from `env_rel`.  Their record witnesses are closed
with the exact constructor/type namespace equalities from `env_rel_sound`.

The original `env_rel_open` proof expanded both well-formedness relations and
then gave six large `nsAll` contexts to unrestricted `metis`.  The first full
focused attempt kernel-saved both existence theorems but spent 12m50s in the
following unchanged theorem before it was intentionally interrupted.  The
replacement proof:

1. applies `ienv_ok_open_ienv` and `tenv_ok_open_tenv` before expansion;
2. extracts the exact component-success equalities;
3. establishes explicit `nsLookup` transport for both value namespaces;
4. establishes explicit `nsLookupMod` transport for both module domains; and
5. unfolds only `env_rel`, soundness, completeness, and empty-expression
   lookup at the final small obligations.

This preserves exact value payloads in both soundness and completeness.
Module-domain equivalence is used only for the module-domain conjunct.

## Focused developer evidence

Focused attempt 004 completed `Holmake -j1 --mt=1 envRelTheory.uo` with exit
zero in 35.37 seconds wall time, 1,073,668 KiB maximum RSS, zero major faults,
and zero swaps.  The theory body took 5.7 seconds.  The log saves all three
open-environment theorems and exports `envRel`:

- root:
  `/project/flyspeck-candle-runs/cakeml-envrel-open-focused-32580b0b-attempt-004`;
- log SHA-256:
  `770990be8edb2b8d2862d7f92ddba06925b0dec2bf50de5e3f987260836773fb`;
- timing SHA-256:
  `fcb5a57039a50b9b3635e08baeb20fb4d7e4971d1461cb08ac7583b11afa3208`.

An independent exact-tree source review accepted the proof with no P0/P1
correctness finding.  It correctly raised a P2 evidence qualification:
attempt 004 finished 29 seconds before the Git commit and does not itself
record the eventual commit/tree or HOL4 head.  It is therefore only focused
pre-commit developer evidence, not exact-commit qualification.

## Exact-head qualification

The provenance-bearing warm replacement is running at:

`/project/flyspeck-candle-runs/cakeml-parser-dopen-warm-proof-731f386b-attempt-005`

It started at `2026-08-31T06:00:08Z`, binds CakeML `731f386b...` and HOL4
`a390cbab...`, uses `-j1 --mt=1` under the 112.5-GiB limit, and has runner
SHA-256
`5071883100ba822262f92f06b7bf07ab4f0d05675ed95077b5fa44f4e57f8a88`.
At this report checkpoint it had passed `infer_eComplete` and was building
`infer_eSound`, with nine of the ten invalidated theories remaining.

The pristine-cold replay and all Candle promotion remain on HOLD until this
exact-head warm gate passes.  Candle staging commit `103691ef...` pins the
parent CakeML head and will require another additive proof-only provenance
refresh after qualification; its generated ML bytes are expected, but not
assumed, to remain identical.
