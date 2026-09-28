# Response to the Candle NL architecture review

Date: 2026-09-28 UTC

Status: DEVELOPMENT / NON-RELEASE

Responds to:

- `Candle_NL_Architecture_Review_and_Proposal_2026-09-28.md`;
- with the earlier `Candle_NL_Performance_Research_2026-09-25.md` and the
  retained project measurements used as supporting context.

## Direct Flyspeck status

- Direct actions reached / passed remain **185 / 184**.
- The protected action-184 LP worker is healthy on one computation core. At
  the review snapshot it was in `formal_lp/glpk/binary/easy_4.dat`, file
  counter 6, and had completed item 371 of 868.
- The final LP-construction marker has not occurred. The exact checkpoint
  monitor and authenticated actions-185--296 continuation remain unchanged.
- The fresh complete action-296 generated-schedule proof replay is also
  healthy. At the review snapshot it was proving scheduled root 28, with
  stable 2,253,704 KiB RSS and no exception.
- This review changed no direct source, runtime, checkpoint, proof input, or
  retained evidence byte.

## Decision

The September 28 proposal materially improves the explanation of the
remaining gap. Its central diagnosis applies to the current implementation:
the proof path has genuine reflection and reusable analytic soundness, but
the stable source program, changing numerical certificates, and structural
certificate checks are not yet separated at the most useful boundary.

The proposed direction is therefore adopted, with one staging refinement.
The project should not build another calculus layer or replace the existing
checker wholesale. It should first expose the missing data interface around
the already proved analytic, erasure, fixed-algebraic, batch, and tree
results. Numerical representation work remains an independent measured lane.

## Verified performance target

The historical comparison in the note was checked against the local pinned
Flyspeck source and result log:

- original input 10172, `(prep-8657368829,0)`, has the same complete target
  and domain as the action-296 fixture;
- the original log records 1,061 pass leaves, 1,060 ordinary glue nodes, no
  monotonicity nodes, and `Time 667.725002` seconds;
- the complete Candle sequential development proof records 1,061 original
  roots, 1,538 selected final cells, and 30,391.012 seconds; and
- the raw elapsed-time ratio is **45.514x**.

This is not a controlled slowdown measurement. The machines, runtimes, and
timing boundaries differ, and the Candle run consumes an already selected
policy rather than reproducing exactly the historical search. It is still a
strong architectural warning: the current grouping-scale improvement cannot
close the observed gap.

The complete sequential phase profile gives the following shares of its
30,391.012-second wall interval:

| Phase | Calls | Wall seconds | Complete-run share |
|---|---:|---:|---:|
| Source preparation | 1,061 | 14,579.210 | 47.97% |
| Point-plan compilation | 1,061 | 4,058.032 | 13.35% |
| Final-cell preparation | 1,061 | 3,720.724 | 12.24% |
| Aggregate proof | 1,061 | 4,940.711 | 16.26% |
| Source extraction | 1,061 | 877.950 | 2.89% |
| Live handoff and glue | 1,061 | 1,638.363 | 5.39% |

The first three preparation phases occupy **73.57%** of total elapsed time.
Even their hypothetical complete removal would leave about 8,032 seconds,
roughly twelve times the historical elapsed time. Both the proof boundary and
the numerical implementation therefore matter.

## Findings against the current code

### The point plan can be shared once per expression

`candle_q_dim_taylor_model_point_plan_six` reads only the six vector
variables and the original source term. It does not read the prepared
expression's square-root payloads or the current box endpoints. Its use-site
already checks the original function and source term by logical identity.

The v1.93 work made such a plan reusable across cells beneath one prepared
source, but the complete sequential driver still constructs one per original
root. The bounded grouping driver constructs one per retained group. The
recovered schedule has 876 groups, so the clean replay still performs 876
identical source-only compilations.

Hoisting this plan once per authenticated expression requires no new
mathematical theorem. On the sequential profile, perfect removal of the
repeated 4,058-second phase has only an approximately **1.15x** whole-run
ceiling. It is nevertheless the cheapest faithful discriminator and should
be done before a larger interface change.

### Stable source proof and changing certificates remain entangled

The action-296 plan already contains one authenticated source theorem.
However, `candle_q_dim_analytic_jet_prepare_box_six` invokes the full analytic
preparer with a box-specific square-root callback. That reconstructs the
annotated expression and its validity, denotation/source correspondence,
compilation, and program-encoding theorems for every root or group.

Point variants are lighter: they preserve the base function/source identity
and do not repeat the original source proof. They still construct a new
certificate-annotated expression and run proof-producing compilation and
encoding for every selected final cell.

This is the most credible explanation of the measured preparation majority.
A durable interface should compile and authenticate a stable instruction
skeleton once, then supply whole-box and center square-root certificates as
checked ordinary data.

### Structural checking is reflected only partly

The fixed-algebraic batch already computes one compact numerical acceptance
flag. The surrounding adapter still:

- proves certificate-erasure equalities by rewriting every cell expression;
- constructs job/program encoding equalities on the host side;
- receives tree well-formedness as a theorem; and
- extracts or transports results through host theorem construction.

The existing exact-tree experiment showed why merely moving topology into a
different theorem adapter is insufficient: its topology proof plus handoff
was 21.2% slower than the established extraction/glue path on the matched
batch. The appropriate next step is a compact encoded structure whose source
identity, shape, boxes, and coverage are checked by computation under a
general soundness theorem.

This is a secondary target until preparation is reduced. Source extraction
plus live handoff and glue were 8.28% of the complete sequential wall time,
not the primary 73.57% preparation cost.

### Numerical arithmetic remains a separate bottleneck

The fixed-algebraic path keeps polynomial blocks, and late negation/addition,
in fixed scale where its invariant permits that. Multiplication, square,
inverse, square root, arctangent, and associated conversions still use the
rational Taylor representation.

The measured fixed-scale hybrid reduced the genuine 64-box compute phase by
2.56x and the complete proof path by 2.15x. That establishes rational
normalization as a real cost, but does not close the historical gap. Stable
program/certificate separation and measured expansion of the bounded-scale
backend should proceed as complementary work rather than competing
explanations.

Evaluator startup is not a leading hypothesis: existing empty/constant
controls put it around tens of milliseconds, and production calls already
batch multiple boxes.

## Reusable proof assets

The proposed checker can build on existing results rather than starting a
second verification architecture:

- universal analytic value, derivative, Hessian, and centered-Taylor
  soundness;
- analytic source reification and compilation correctness;
- certificate erasure preserving value, derivatives, Hessians, and source
  denotation;
- the proved tagged fixed/rational execution invariant;
- one-verdict batch correctness and source-level acceptance;
- exact split-tree composition and the general root soundness theorem; and
- the existing live source theorem connecting the reflected function to the
  original Flyspeck formula.

The missing reusable lemma should characterize either a parameterized
evaluator or a checked patching function. In schematic form:

```text
patch_checked stable_program hints = SOME concrete_program
  ==> concrete_program changes only declared square-root payload slots
      /\ concrete_program represents the same erased analytic source
```

The batch checker can then consume one stable program, one whole-box hint
table, and a list of center-hint/box jobs. Shape and hint-count failures must
return rejection, not fall through to an unrelated program.

## Bounded experimental sequence

### 1. Hoist the source-only point plan

Use the retained roots-0--31 generated policy and schedule. Construct one
point plan from the authenticated action-296 source and reuse it across every
group. Require:

- 32 original roots and 49 selected cells;
- the established theorem digest
  `7f5df8d12a23b58b73fee9e254b83753`;
- no hypotheses or new axioms; and
- one charged plan construction followed by zero group-local plan
  constructions.

This experiment isolates avoidable driver repetition. It is not presented as
the final architecture.

### 2. Test a stable program plus data-only certificates

On the same authentic cells, first implement an explicitly untrusted data
layout while retaining the current arithmetic and exact hint values. Compare
1, 8, and 32 boxes, charging stable source preparation once. Measure:

- stable source authentication and compilation;
- untrusted whole-box and center hint generation;
- recurring data construction and encoding;
- `Kernel.compute` execution;
- structural validation; and
- final theorem assembly.

The untrusted prototype earns no proof credit. It decides whether the layout
actually removes recurring construction before substantial proof work is
committed.

### 3. Prove the narrow patch/parameter interface

If the data layout is useful, prove the generic source-preservation and
decoder/shape results and connect the same call to `Kernel.compute`. Reuse the
current erasure and compiler results. Do not introduce per-expression
calculus proofs or per-box compilation theorems under a different name.

Required adversarial rejection cases are:

- wrong hint count or malformed numerical representation;
- an invalid square-root enclosure;
- a changed opcode, polynomial coefficient, or variable index;
- an inconsistent job box;
- a missing or duplicated branch; and
- a gap, overlap, or changed root domain in the subdivision structure.

### 4. Reflect structural acceptance

Extend the bounded call to check program/hint consistency, job well-formedness
and exact split-tree coverage. The desired theorem boundary is schematically:

```text
check_nl stable_program original_box certificate = true
  ==> every point in original_box satisfies the encoded inequality
```

The source-correspondence theorem is established once per distinct
expression. The existing general tree theorem then converts one accepted
encoded tree into the exact `m_cell_pass` root result, and the existing source
theorem rewrites that result to the original Flyspeck function.

Bounded batches should initially be combined in one Candle process through
the existing kernel theorems. Cross-process theorem transport is a separate
soundness question; untrusted certificate preparation may be parallelized
without solving it.

### 5. Resume numerical optimization on the resulting boundary

Profile identical accepted boxes after recurring source construction is no
longer dominant. Extend fixed-scale execution only at measured rational hot
operations, reporting both time per box and the number of cells required to
cover the original domain. Wider bounds that force more subdivision are a
regression even if an individual instruction becomes cheaper.

## Integration rule

The active complete generated-schedule replay remains the authoritative
measurement of preparation grouping in the current design. It need not gate
the bounded stable-program prototype. No second 1,061-root replay is justified
until a candidate preserves the exact bounded theorem result and demonstrates
a material recurring-cost reduction.

Once that evidence exists, the full action-296 comparison should report:

- exact original-root and final-cell counts;
- exact aggregate theorem digest and source theorem;
- stable versus recurring preparation;
- numerical compute and structural-check time;
- final theorem handoff;
- peak memory; and
- a contemporary same-machine native comparison when practical.

This staging preserves all completed proof guarantees while moving the
recurring workload toward the intended computational-checker boundary.
