# Review: Candle reflected tame-graph classification plan

Reviewed document: `docs/Candle_tame_graph_reflection_plan_2026-10-05.md`
on branch `codex/flyspeck-v13-great100-compatibility-localizer`
(commit `2df9f8f`).

Review date: 2026-10-06

## Verdict

The trust architecture and the claim discipline are sound, and the factual
baseline checks out against the sources. Two things need to change before the
plan is used to schedule work:

1. It contains no scale numbers. The numbers AFP itself records show that the
   "witness-carrying" backend, as specified, does not avoid the search, and
   that the two backends should be merged into one design.
2. Stage 3 (general soundness in HOL) is the dominant cost, is under-scoped in
   the text, and is scheduled after work that does not reduce its risk.

## What was checked, and against what

| Source | Identity |
| --- | --- |
| Flyspeck | `flyspeck/flyspeck` at the pinned `1ce0353008eba83d3c76ae9a25c3c242e4802d53` |
| AFP | `isabelle-prover/mirror-afp-devel` at `fb3d00198a99` (2014-07-05), the last commit touching `thys/Flyspeck-Tame` before 2014-08-28; the next one is dated 2014-09-09 |
| Candle | `JUrban/candle`, branch `codex/tame-graph-reflection-v1`, head `02c4d95` |

Not checked: the release tarball itself and its SHA-256. `isa-afp.org` was not
reachable from the review environment, so the AFP comparison is against the
git mirror, not the tarball. The release branch could in principle differ from
the development mirror; the hash agreement below makes that unlikely for the
listed files.

### Confirmed

- `formal_graph/isabelle_tame` contains exactly 13 theory files.
- All ten SHA-256 values in the plan's table match the mirror commit above.
- `Tri.ML`, `Quad.ML`, `Pent.ML`, `Hex.ML` are byte-identical between Flyspeck
  and AFP, with 9 / 1,253 / 16,080 / 2,373 graphs (total 19,715).
- `Completeness.thy` is byte-identical; `Tame.thy` differs only in the
  source-URL comment on line 3.
- The plan's statement of `import_tame_classification` is character-for-character
  the definition in `general/the_kepler_conjecture.hl`, with
  `archive = set_of_list tame_archive_lists`.
- The HOL definitions `next_plane`, `planeGraphsP`, `PlaneGraphs` in
  `tame_defs2.hl` have the shape the partition theorem assumes
  (`(Seed p,g) IN RTranCl (next_plane p) /\ finalGraph g`).
- The tameness constants agree between `Tame.thy` and
  `tame/import_tame_classification.hl` (`squanderTarget = 15410`,
  `excessTCount = 6295`, `squanderFace 6 = 7120`, the `squanderVertex` table,
  `tame10` as `13 <= n <= 15`).
- The first work packet has started: `candle/cv_compute_tame_graph_data.ml`
  provides face / fgraph / vertex-map encoders, round-trip and injectivity
  theorems, and strict rejecting validators, with negative tests.

### Small discrepancies in the baseline section

- The 11 byte-identical overlapping files already include `Completeness.thy`
  (`ArchCompAux`, `Completeness`, `Enumerator`, `FaceDivision`, `Graph`,
  `ListAux`, `Plane`, `Plane1`, `PlaneGraphIso`, `RTranCl`, `Rotation`). The
  plan lists it as a separate bullet, which reads as 12 identical files.
- `Vector.thy` is in the Flyspeck checkout but has no counterpart in the AFP
  entry at the mirror commit. The plan does not account for it.
- The proposition `import_tame_classification` is defined in
  `general/the_kepler_conjecture.hl` (with a second copy in
  `formal_graph/isabelle_hollight_translation.hl`). The file
  `tame/import_tame_classification.hl` defines tameness and `iso_fgraph` but
  not the proposition, contrary to the "Existing assets" bullet.

## Major findings

### 1. The plan has no scale baseline, and one exists

`ArchStat.thy` in the AFP entry (marked "FIXME dead code!?") records the size
of the `next_tame` search tree:

| p | nodes generated | final graphs | archive classes |
| --- | ---: | ---: | ---: |
| 0 | 312,764 | 501 | 9 |
| 1 | 134,291,356 | 27,050 | 1,105 |
| 2 | 1,401,437,009 | 301,560 | 15,991 |
| 3 | 334,466,383 | 19,120 | 1,657 |
| total | 1,870,507,512 | 348,231 | 18,762 |

The recorded time is "11 hours" in code-generated PolyML, about 21 µs per
node on hardware of that period.

Consequences:

- These counts predate the July 2014 constants (the archive column is
  9 / 1,105 / 15,991 / 1,657, not 9 / 1,253 / 16,080 / 2,373). The final
  counts are unknown and must be regenerated; `p = 3` in particular will be
  larger, since its archive grew by 43%.
- The full enumeration is roughly 6,000 times the `p = 0` partition. If the
  `p = 0` replay takes one minute in `Kernel.compute`, the whole replay is on
  the order of four days; at ten minutes it is about six weeks.
- As far as I can see the work is serial. Chunk theorems proved in separate
  Candle processes cannot be combined without the theorem import that the
  project forbids.

**Recommendation.** Put the node counts in the plan, regenerate them for the
final constants with an instrumented reference run, and give Stage 2 a numeric
go/no-go gate: measured `p = 0` evaluator time multiplied by the measured
node ratio must fit an agreed wall-clock budget.

### 2. Witness-carrying replay, as specified, does not avoid the search

The plan says witness-carrying replay "can avoid repeating expensive search".
Under its own rules it cannot: an *expanded* node has its exact `next_tame`
successors recomputed by the checker, and every successor must be a declared
node. The checker therefore visits the same 1.9 × 10⁹ nodes. A certificate
that declares each node explicitly would be hundreds of gigabytes.

What an untrusted producer can actually save is narrow:

- the isomorphism *search* at final graphs (replaced by checking a map), and
- the trie, hash and worklist machinery around it.

The realistic design is a single backend: a fuel-bounded depth-first replay of
`next_tame` inside `Kernel.compute`, consuming a hint stream only at final
graphs that pass `is_tame`. Each hint is an index into the archive, a vertex
map, and an orientation flag (since `is_Iso` permits reversal). That is about
3.5 × 10⁵ hints, a few megabytes.

This design also removes AFP material from the port: `Worklist.thy`
(`while_option`), `Tries.thy`, `Maps.thy`, `Quasi_Order.thy`, the `hash` /
`qsort` / `samet` definitions, `ArchCompProps.thy`, and the correctness proof
of the searching `iso_test` in `PlaneGraphIso.thy`. That is on the order of
1,000 to 1,500 lines that need no HOL counterpart.

The lower bound should stay a deterministic computation. A separated-set
witness for each pruning decision would cost one hint per expanded node, which
is the wrong order of magnitude.

**Recommendation.** Replace "two computation styles" with one: algorithm
replay plus leaf hints. Drop the Stage 2 item that races the two styles.

### 3. Chunking can be simpler than authenticated frontiers

With a deterministic replay, chunk boundaries need not be certificate data.
A formulation that keeps composition purely logical:

```
covers p A S <=>
  !s g. s IN S /\ (s,g) IN RTranCl (next_plane p) /\
        finalGraph g /\ tame g
        ==> ?y. y IN A /\ iso_fgraph (fgraph g) y
```

with these rules, each a general theorem:

- `covers p A {}`, and `covers` distributes over union;
- a final `s` with a checked isomorphism to some `y IN A` is covered;
- a final `s` satisfying `inv` and failing `is_tame` is covered
  (`untame_negFin`, via `total_weight_lowerbound`);
- a non-final `s` satisfying `inv` is covered if `set (next_tame p s)` is.

The last rule is available directly. `filterout_untame_succs` and
`filter_tame_succs` in `TameProps.thy` are stated for an arbitrary start
graph satisfying the invariant, not only for `Seed`, so the per-node form of
`next_tame0_comp` / `next_tame_comp` does not need a new argument.

The checker soundness theorem is then
`check fuel hints stack = SOME hints' ==> covers p A (set stack)`. A chunk is
a sublist of a frontier computed once inside the logic, and composition is the
union rule. No frontier authentication, ordering, or truncation tests are
needed for soundness; they remain useful as diagnostics.

### 4. The "duplicate" certificate case is not supported by AFP

The AFP worklist is a tree traversal. It never merges non-final graphs; it
only collects final graphs modulo isomorphism. There is no AFP theorem that
isomorphic non-final states have isomorphic sets of completions under
`next_plane`, and such a theorem is not straightforward: `next_plane` chooses
`minimalFace` and `minimalVertex` using heights and list order, neither of
which is preserved by an fgraph isomorphism. AFP proves only that
`next_plane` steps are `next_plane0` steps, not the converse up to
isomorphism.

For final graphs the case is unnecessary, since each one is matched to the
archive directly.

**Recommendation.** Remove "duplicate" from the first design, or mark it
explicitly as new mathematics with no proof guide.

### 5. Stage 3 is the real cost and is under-scoped

The plan lists nine theories as "omitted important inputs". Those are the
small ones. Line counts in the AFP entry (15,298 total):

| Theory | Lines |
| --- | ---: |
| `FaceDivisionProps` | 4,942 |
| `Invariants` | 2,826 |
| `ScoreProps` | 725 |
| `PlaneProps` | 680 |
| `GeneratorProps` | 537 |
| `GraphProps` | 437 |
| `EnumeratorProps` | 429 |
| `LowerBound` | 297 |
| `TameProps`, `TameEnumProps`, `Plane1Props` | 160 |

That is about 11,000 lines of proof that the completeness of pruning rests
on, most of it establishing that `inv` is preserved by `next_plane`. HOL
Light proofs of the same facts will be longer. `tame_list.hl` (14,428 lines)
may supply some structural lemmas, but it was written for a different purpose
(showing that restricted hypermaps arise as plane graphs).

Nothing in Stages 1 and 2 retires this risk, and Stage 2 produces a
computation whose meaning is not yet tied to HOL terms, which sits awkwardly
with the Stage 0 exit gate.

**Recommendations.**

- Start a statement-level skeleton now, in parallel with Stage 1: translate
  the AFP lemma statements into HOL, and derive the partition theorem with
  those statements as explicit hypotheses. The remaining holes become a
  countable burndown, in the same style as the project's named premises.
- Make Stage 0 item 4 deliver a line-weighted estimate, not only a
  classification, and treat it as a gate for committing to Stage 3.
- Fix the typed HOL executable specification first and derive the `cval`
  programs from it, so Stage 2 measurements are of the program that will be
  proved.
- Record why proof transport from Isabelle was rejected. The requirements
  allow "transport or reproof" for S4; the plan chooses reproof silently.

### 6. The `p = 0` prototype is a weak proxy

With `maxGon = 3` every face is a triangle. The `p = 0` run never exercises:

- quadrilaterals: `separated₃` and the quad branch of `deleteAround`;
- exceptional faces: `tame12o`, `admissible₃`, the `e ≠ 0` branches of
  `excessAtType`, and the `except ≠ 0` branch of `tame11b`;
- `polysizes` with more than one candidate size.

Differential and negative tests on `p = 0` therefore leave the most intricate
pruning code untested, and its per-node cost is not representative.

**Recommendation.** Add a bounded `p = 2` subtree to Stage 2 (a fixed number
of nodes in deterministic order), compared against an instrumented reference
for node, pruned and final counts.

### 7. The Isabelle oracle is weaker than the plan implies

In the AFP release:

- `same3` and the four `pre_iso_test` lemmas are proved `by eval`;
- `same4`, `same5`, `same6` are proved `by cond_eval`, which is
  `Skip_Proof.cheat_tac` unless `ISABELLE_FULL_TEST=true`;
- the archives enter as ML values through `Code_Runtime.polyml_as_definition`.

So there is no kernel-checked Isabelle fact about the enumeration, and in a
default build there is no evaluated fact at all for `p ≥ 1`. "Agreement with
AFP `same3`" means agreement with a code-generator run. Comparisons for the
larger partitions need an explicit full-test run or the exported code.

This also strengthens the case for the lane: the S4 result would be the first
kernel-level check of the enumeration, strictly stronger than the Isabelle
original. The plan's motivation should say so.

## Minor points

- **Archive binding.** Define the four parts inside HOL as filters of
  `tame_archive_lists` by maximum face size, or let hints index
  `tame_archive_lists` directly. The `.ML` files then become diagnostics only,
  and Stage 5 step 2 ("rewrite the resulting archive union") disappears. Today
  the link between `archive_all.ml` and the `.ML` files is an OCaml-level MD5
  check in `make_archive.hl`.
- **Ledger location.** `isabelle_hollight_translation.hl` and
  `make_archive.hl` are not listed in `build.hl`, and the ledger file
  re-declares the tame definitions rather than referring to the loaded ones.
  Its 119 entries cover the statement side only. An extended ledger should
  bind to the theorems actually loaded by the direct manifest.
- **"Terminal non-tame".** `tame13a` is never decided, only refuted through
  the lower bound. A final graph that passes `is_tame` must be matched to the
  archive whether or not it is tame, and the archive may contain non-tame
  graphs. The certificate-case wording should say this.
- **Direction of the archive check.** Only "enumerated ⊆ archive up to
  isomorphism" is needed. AFP's `samet` also checks the converse. The expected
  partition sizes are a meaningful consistency check only if the converse is
  checked too; the plan should state that archive minimality is not a goal.
- **`enum` and arrays.** The shared `Enumerator.thy` uses a tabulated `enum`
  over `IArray`. `Kernel.compute` has no arrays, so the reflected version
  needs either `enumerator` directly or a list-encoded table, with the
  equivalence proved.
- **Refinement tooling.** The current data layer writes each `cval` function
  twice by hand (pattern-matching definition and all-variable compute
  equation). The generator needs on the order of a hundred functions. A small
  translator from first-order typed HOL definitions to `cval` programs with
  refinement theorems would pay for itself before Stage 2.
- **Archive encoding cost.** Proving the `cval` literal for
  `tame_archive_lists` is ordinary inference over a 9 MB term. It should be
  listed among the measured preparation costs.

## Suggested edits to the plan

1. Add a "Scale baseline" section with the `ArchStat.thy` counts, the caveat
   about the constants, and the serial-execution assumption.
2. Rewrite "Proposed trusted architecture" around one backend: deterministic
   replay with leaf hints.
3. Replace the five certificate cases with three checked outcomes for a
   visited node: expanded, final and matched, final and rejected by `is_tame`.
   Pruning is computed, not declared.
4. State the `covers` formulation, or an equivalent, as the target of Stage 3,
   and move the statement-level skeleton into the first work packet.
5. Add the bounded `p = 2` subtree and the numeric go/no-go to the Stage 2
   exit gate.
6. Correct the three baseline discrepancies and add the Isabelle-oracle
   caveat to "Claims deliberately deferred".
