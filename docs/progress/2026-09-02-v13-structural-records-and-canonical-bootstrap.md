# v1.3 structural records, tuple arguments, and canonical bootstrap

Date: 2026-09-02 UTC

## Claim boundary

This report records development proofs, an exact-corpus lexical audit, and the
completion of the older canonical bootstrap transition base.  The frontend
branch has not yet produced a current-head runtime or passed the formal
20/400 gates.  Nothing here is S1, S2, S3, or whole-Flyspeck release evidence,
and the continuing PFT run is not counted toward any direct Candle gate.

## Canonical f2 bootstrap completion

Canonical attempt
`cakeml-canonical-bootstrap-f2f50a4-attempt-004` completed all 18 forced
targets with exit status zero.  The pinned revisions are:

- Candle `f2f50a44b438385031d75041c9bae35b94b01eae`;
- CakeML `c2e26f43c35080d57fc18aba42d4023590b6daba`; and
- HOL4 `a390cbabd3a4521bab4ee20281e3e42933a8a3ae`.

The exact `Holmake -j1 cake.S` run took 7:26:24, used 100% CPU, reached a
maximum RSS of 67,810,864 KiB, and reported no swap.  Publication produced:

| Object | SHA-256 |
|---|---|
| `bootstrap.log` | `9959c8342b9a5fbbf5abb123f48ecfcd8c303ece547257d7bc8742cb5275a624` |
| `bootstrap-preflight.json` | `17f1c9dd4c8c5ecee5d2d55e3040379ada0137208194185105d43879aa7eea69` |
| `bootstrap-provenance.json` | `69728dda772acfbb0ee113e5284685b8794fb8013e3a8f2416ed3ee8c50c4b6e` |
| regenerated `cake.S` | `952954d17a494bc53b9b7f18f4e078fc0f66d753101ff657877c09c320781e31` |
| regenerated `config_enc_str.txt` | `fe8ae19307aafc620fd40a12900527a1758ed1bcdcc7d4c121649735c0b869aa` |

The 41,588,191-byte `cake.S` and 7,146,613-byte configuration postimages are
ordinary fresh files recorded by the schema-5 provenance controller.  This
closes the bootstrap-dependency-transition work at f2.  It is a valid base for
diagnostic transition work, but it cannot qualify the newer frontend commits
or substitute for their eventual clean same-head build.

## Exact structural-record audit

Project commit `d004cbc` added a reproducible byte-lexical audit over the exact
quotation-aware 400-input parser plan.  Its immutable result is
`nonpromotable-structural-record-audit-ac15ba0-attempt-001`, with summary
SHA-256
`a571cc6d88cde9cf43f2bfe849084abdcf41c8cba93ce381f29f90b7efac830e`.

The audit found:

| Item | Count |
|---|---:|
| prepared inputs | 400 |
| inputs declaring structural record types | 9 |
| structural record types | 17 |
| declared fields | 89 |
| mutable fields | 7 |
| constructions | 1,087 |
| functional updates | 13 |
| projections | 374 |
| direct assignments | 3 |
| structural record patterns | 0 |
| duplicate field labels in a lexical module | 0 |

There are ten distinct construction field sets, and a separate exact-set
comparison found that each matches a declared structural-record field set.
Seven declared record types have no construction in the selected inputs.  The
three assignments are `lpvalue`, `lpvalue`, and `diagnostic` in prepared input
257; all three fields are declared mutable.  Input 066 also exercises mutable
cells, and chained projection includes the exact `vd.val_type.desc` form.

The audit is deliberately lexical.  The field-set comparison is useful design
evidence, not OCaml typing or label-resolution evidence.  Field-only helper
names are justified only by the exact zero-duplicate corpus result; source or
scope drift requires re-audit.

## Proved structural-record implementation

CakeML branch `codex/flyspeck-v13-frontend-batch` commit `60f1f95ea` adds the
bounded structural-record implementation.  It keeps the existing qualified
fake-record syntax intact and adds:

- bare structural type declarations with immutable and mutable fields;
- deterministic hidden constructors derived from sorted field names;
- unqualified construction, functional update, projection, and assignment;
- repeated projections, including chained `vd.val_type.desc`;
- CakeML references for mutable cells and dereferencing projections;
- direct assignment through `Opassign`; and
- fresh reference cells when a functional update copies a mutable record.

The last point is semantically essential: sharing a mutable cell between the
old and functionally updated record would not implement OCaml record-copy
behaviour.  Setter helpers are generated only for mutable structural fields.
Structural record patterns remain unsupported because the exact corpus count
is zero.

The focused command
`Holmake -j2 camlPtreeConversionTheory camlTestsTheory` passed both targets in
7:06.82, with peak RSS 2,611,436 KiB, 107% CPU, and no swap.  Tests include an
explicit mutable-record AST, fresh-cell functional updates, direct assignment,
qualified-record compatibility, and chained projection.

## Tuple arguments and isolated optional syntax

Flyspeck also uses OCaml's unparenthesized tuple function arguments, including
`fun s, tm -> ...` and `fun (_,b,_),(u,v) -> ...`.  CakeML previously rejected
these deliberately to avoid confusing constructor application with curried
arguments.

Commit `58da58c68` accepts only the unambiguous comma-tail form: one or more
commas separating base patterns.  It continues to parse `fun Some x -> ...` as
two curried arguments.  The full grammar, conversion, and parser-test replay
passed 3/3 theories in 10:35.06, with peak RSS 3,457,208 KiB, 106% CPU, and no
swap.  The test suite includes the exact nested Flyspeck shape and a mixed
curried/tuple case.

General optional-argument support is not justified by the selected graph.
Candle commit `7921a8f` instead narrows the existing exact-hash fail-closed
normalization of `eval_command`: its unused `?(silent=false)` parameter is
erased, and the selected graph still contains no active `eval_command` call or
active `~silent` label.  All 44 focused normalization/manifest tests pass, the
normalized-top-level checker reports zero selected dynamic compiler
references, and the full manifest check reports 297 roots, 400 source nodes,
and 43 generated inputs.

This is not optional-argument compatibility.  Any source drift, call,
labelled argument, reflection, or external input invalidates the refinement.

## Translation and resource discipline

The first combined parser-translation attempt successfully translated the new
record helpers but was stopped before completion when its approximately
38 GiB RSS overlapped the canonical x64 bootstrap and PFT, pushing the three
large jobs above the user's approximately 120 GiB allowance.  Its warm theory
products were retained.  After the canonical job completed, the final
translation was restarted from frontend head `58da58c68`.

`Holmake -j2 caml_parserProgTheory` then passed 2/2 theories in 43:58.71, with
peak RSS 35,637,532 KiB, 105% CPU, and no swap.  The run translated the tuple
argument path through `ptree_Patterns`, translated every structural-record
constructor/projection/update/set helper, generated the main mutually
recursive `ptree_Expr` value theorems, proved `ptree_Expr_preconds`, updated all
of those theorems with discharged preconditions, and translated the public
`caml_parser$run_parser` and `caml_parser$run` entry points.

This implements the useful part of the external speed advice: batch related
frontend repairs, use a cheap focused proof/test gate, retain same-worktree
warm products, and defer a new whole bootstrap until the batch is quiet.  It
does not weaken the clean serial release qualification contract.

## Next gates

1. Produce a clearly non-promotable current-head development runtime.
2. Run 20/20 and then all 400 quotation-aware parser inputs.
3. Localize only the residual failures and repeat a bounded repair batch.
4. Once 400/400 is quiet, repin Candle to the final CakeML frontend commit and
   run pristine proof replay, clean canonical bootstrap, ordinary same-head
   link, formal 20/400, compatibility, and direct whole-Flyspeck S2/S3.
