# Candle NL first fast theorem: live gate map

Date: 2026-11-04 UTC; updated 2026-11-07 UTC

Status: **DEVELOPMENT / NON-RELEASE**

This is the short, current execution map for the first original Flyspeck
nonlinear theorem through the fast case-16594 route.  It supersedes informal
uses of "close" but does not replace the detailed implementation ledger in
`Candle_NL_first_fast_theorem_implementation_plan_v2_2026-10-26.md`.

## Headline

- Direct Flyspeck: **297/297**, green and checkpointed.
- LP: **complete**, green and checkpointed.
- Genuine case-16594 numerical checker: **167/167 instruction positions** and
  **875/875 cells** accepted.
- Explicit-radius whole-call executable: **defined and typechecked** against
  the prepared Candle state; its numerical and 1,749-token topology parts
  consume the same canonical job stream.
- Existing case-10173 stock-route reference: the general fixed-nonlinear
  checker took **434.364 seconds** for the complete 4,173-cell numerical and
  topology verdict, **46.468 seconds** for theorem handoff, and **480.933
  seconds** through the exact source theorem, at about **17.15 GiB** peak RSS.
  The earlier **401.740-second** result was an unproved raw-only run.  This is
  one genuine data point for a general checker, not an all-NL projection.
- The closed per-cell HOL4 regression prefix is **349/875** cells (0--348).
  It is now parked: G3 already supplies the arbitrary-valid-cell theorem, so
  extending this closed prefix is not a production G4/G5C gate.
- First original Flyspeck NL theorem through the fast route: **0/1**.
- G6 is **DONE** for the case-16594 callback.  The complete type-inferred
  executable accepts the genuine **875-cell / 1,749-token** payload in
  **4:42.29** at **6,142,976 KiB** peak RSS.  Certificate, source, cell,
  token, job, dimension, truncated-cell, truncated-job and truncated-token
  mutations all return the required fail-closed `None` result through the
  exact same binary.
- The direct split, leaf, glue, arbitrary transition and complete recursive
  runner are all formally proved equal to evaluation of the unchanged
  ordinary Flyspeck topology source.  The earlier greater-than-80-GiB failure
  is eliminated rather than hidden by a larger heap.

The highest closed first-case executable gate is now **G6**; the highest
closed first-case logic gate remains **G5C**.  G4 has a proved generic
whole-call composition theorem, a kernel-checked genuine cell-0 singleton,
the complete assumption-free 875-job geometry contract, and an exact
875-job/1,749-token representation seam.  G5C's witnessed whole-call theorem
closes the remaining case-16594 production-payload evaluator refinement.  The
case-16594, payload-generic/program-fixed G5C callback and its
`compute_fast_eval_ok` theorem are now closed; the plan-generic G5P callback
required by the all-NL production design remains pending.  The complete
genuine numerical and direct-topology phases now execute together through one
type-inferred callback.  The original-statement adapter remains untested.

The numerical result is not yet the original HOL theorem.  The missing work
is the proved semantic composition from the accepted fast computation to the
original statement.

## Gates

| Gate | Layer | Status | Exit criterion |
|---|---|---|---|
| G0. Genuine data and numerical execution | computation | **DONE** | The authenticated source, certificate plan, 167-position program, and all 875 cells accept through the fixed fast checker. |
| G1. Ordinary instruction-family bridge | logic | **DONE** | Every ordinary family has a generic evaluator-to-exact-object theorem, including certificate-cursor preservation for inverse, square root, and arctangent. |
| S0. End-to-end contract skeleton | representation/control | **DONE** | The Candle whole-call target and HOL4 `compute_fast_eval_ok` target typecheck against the real equation set. The callback authenticates all four runtime payload roles and its two clock obligations fit under `compute_default_clock = 10^9`. |
| G2. Six specialized delta instructions | logic | **DONE** | All six specialized evaluator results are connected to exact object states for arbitrary valid inputs. The three product-delta coordinates and the three negative-delta coordinates each use one generic production evaluator/refinement theorem rather than captured cell computations. |
| G3. Complete ordinary trace and leaf semantics | logic/clock | **DONE** | Generic ordinary and specialized steps compose through all 167 positions for an arbitrary valid explicit-radius cell; the entry result implies that cell's `m_cell_pass`; a structural ordinary-evaluator clock bound is exported. |
| G4. Whole jobs and topology | representation/logic | **DONE for case 16594** | The generic checker consumes packed cells and jobs in lockstep, rejects failed entries and length mismatches, derives every matching leaf from one authenticated source program, and combines those leaves through the proved topology invariant. The complete 875-job geometry contract is assumption-free and certificate-parametric; all 875 source-box identities and all 1,749 token roles match the authenticated plan. G5C closes the exact production-call/reference-source/singleton-root instantiation. Its executable verdict is supplied by `Kernel.compute`, not by 875 closed HOL4 entry theorems. |
| G5C. Case-16594 fast callback | HOL4 logic | **DONE** | Commit `5b009642d` proves `compute_fast_eval_ok` for the witnessed whole-call callback. Runtime certificate bytes, boxes, radii, packed cells and jobs are data, but the checker authenticates the case-16594 875-by-31 header and canonical 167 code/source streams. It recomputes all runtime packets through G3 and evaluates only the compact topology through the proved pure evaluator. Numerical or topology failure and equation-set mismatch fail closed. This is payload-generic and program-fixed, not the all-NL production callback. |
| G5P. Plan-generic fast callback | HOL4 logic/runtime architecture | **PENDING** | Decode and compile an arbitrary supported versioned source/evidence plan, recognize deltas through the checked compiler, support variable certificate and cell counts, and prove the ordinary-evaluator refinement over the compiled trace. A structurally distinct genuine family must pass unchanged callback source. |
| G6. Pre-bootstrap callback/dispatcher probe | executable representation | **DONE for case-16594 callback** | The complete generated program passes CakeML type inference and the exact same binary accepts the genuine 875-cell / 1,749-token payload in 4:42.29 at 6,142,976 KiB peak RSS. It rejects certificate, source, cell, token, job, dimension and all three truncation mutations by returning exactly `None`. Generic HOL4 refinements cover exact split, leaf, glue, arbitrary transition and the complete recursive direct runner. This remains development evidence, not a changed-kernel Candle runtime. |
| G7. Analytic and original-statement adapter | logic | **PENDING** | The authenticated root `m_cell_pass` is converted by the existing case-16594 reconstruction to a typechecked conditional theorem with the literal original conclusion and audited assumptions. |
| G8. Verified runtime and prepared state | build/runtime | **PENDING** | The owner has explicitly chosen case-only demonstrator or plan-generic production scope; the exact chosen callback bytes pass the verified rebuild preflight and build; the minimum compatible Flyspeck/NL predecessor state is reconstructed and its cold elapsed time and peak RSS are measured. |
| G9. First fast original theorem | integration | **PENDING** | A fresh compatible run takes the fast branch and produces the literal original theorem, recording preparation, checking, decoding/handoff, total elapsed time, peak RSS, and theorem assumptions. |

### Audit-driven S0/G4 probe

The audit review exposed that the earlier map did not represent the whole
runtime and reconstruction path.  A bounded implementation packet therefore
defined an explicit-radius whole-call executable and a conditional soundness
skeleton before authorizing any long build.

The representation deliberately keeps the legacy topology job shape
unchanged:

```text
job = (outer_boxes,(center_boxes,source_boxes))
source descriptor = (plan_codes,(source_instructions,packed_cells))
packed cell = (radii,certificates)
```

The numerical checker consumes `packed_cells` and `jobs` in lockstep.  It
rejects nonzero terminators, stream-length mismatches, and any failed entry.
The same `jobs` value is then supplied to the compact topology runner, so the
two halves cannot silently use different job lists.

The executable and its conditional contract skeleton typechecked together in
109 seconds against the real prepared Candle state.  The skeleton proves the
whole-call component decomposition, conversion of the encoded topology run to
the logical topology runner, and a root `m_cell_pass` conclusion conditional
on three explicit obligations: canonical job representation, the per-job
leaf theorems, and the generalized topology contract.  This closes the Candle
half of the S0 syntax/type probe; it does **not** close G4.

The two exact sources are now preserved on the isolated Candle branch in
commit `0ad3bf38`; they are no longer dependent on an untracked worktree.

A bounded attempt at the generalized topology proof found useful type/layout
hazards, including an initial packed representation that would have broken
the existing logical job decoder.  That layout was corrected.  The remaining
topology theorem was left explicit rather than entering a tactic-fragile or
hour-scale proof loop.  The HOL4 callback/clock skeleton remains the other S0
half.

## Current exact blocker

### Current boundary (2026-11-06)

G3 is closed.  On the isolated Candle branch, commits `abd5726e` through
`5bcce532` now prove the reusable G4 path:

1. the generalized topology contract follows from the replay invariants;
2. all successful executions of the same planned 167-action source program
   have the same certificate-erased source expression, even when their boxes,
   radii, certificates, and runtime states differ;
3. each accepted reflected job yields the matching `m_cell_pass` leaf;
4. packed cells and jobs are traversed in exact lockstep, and a per-job result
   is accepted only when it is exactly `Cexp_num 1`; and
5. a successful whole reflected call yields the root `m_cell_pass` theorem.

The final clean source-only probe took **113 seconds** from the authenticated
prepared checkpoint.  It used checkpoint SHA-256
`5d69e6e41e3603e72b1a74d65d72a83be88e5e912f42849a42f16e204e9003db`
and source-set SHA-256
`a5e0c2e2c3ab116cef00994e5fc5707b4d715c1f1dc183e7931c51074a2c2f27`.

This is a generic conditional theorem, not the first original theorem.  The
first real-data seam is now also proved on genuine cell 0.  Commits `d8e1c20c`
and `f8c73ea6` construct its one-job/one-leaf whole call, prove both geometry
contracts, prove the exact singleton executable equation from the per-entry
verdict, and apply the generic theorem to the root.

The first probe accidentally reused pre-tight fixture bindings from the v3612
checkpoint and is not counted.  The accepted repeat freshly streamed the
current tight correspondence, 134-packet fixture, 167-action plan, exact call,
generic G4 modules, and singleton theorem.  It closed with the original frozen
radii in **127 seconds**, with source-set SHA-256
`d220908e10e90afd6672fcef41f8c10ab103a8b9c8918899b99acb8c07b2d955`.
This confirms the v4.365 tight-box repair; no radius change is required.

Audit 5 exposed that the subsequent closed per-cell HOL4 lift was no longer on
this production path once G3 had closed generically.  That lift is therefore
parked at committed cells 0--348.  It remains useful as a regression oracle:
it exercised distinct genuine packets, found a converter-identity hazard and
a stale non-clock-aware helper, and validates the generic theorem on many
inputs.  It does **not** gate G4 or G5C and no decision currently requires its
completion.

The next bounded production blockers are now separated correctly:

1. freeze the corrected 875 packed cells, the already matched 875 jobs, all
   1,749 tokens, and the singleton root in the exact production call;
2. implement the G5C callback that executes the fixed checker on those runtime
   payloads and derive its case-16594 `compute_fast_eval_ok` theorem from G3 plus
   whole-list/topology composition;
3. instantiate the existing Candle whole-success theorem with the resulting
   whole equality and reference source witness, then typecheck G7; and
4. exercise that exact callback through G6 before any runtime rebuild.

The complete geometry proof found nine of 5,250 coordinates whose packed
radius rounded inward by one scale-2^40 unit.  One uniform unit of radius
padding proved all coordinates and the recaptured compiled checker accepted
all 875 cells in 10.82 seconds; LR-202 preserves this discriminator.  The
kernel proof took 35m53s and is not being replayed during adapter edits.  A
separate 166-second representation probe matched all 875 source boxes and the
875/874 token counts.  An optional nonempty-reference convenience wrapper was
stopped after a tactic-level free-variable/generalization failure and remains
uncommitted (LR-203); the existing generic theorem remains the authority.

The original case-16594 HOL4 callback refinement has since closed.  Commits `05f7bd2be`, `018caa4f2`,
`be242c42a`, and `5b009642d` authenticate the complete runtime payload,
generalize the evaluator clock, refine the fixed numerical and compact
topology results to the unchanged ordinary whole call, and prove the final
witnessed callback sound.  The numerical matcher never reruns the generic
arbitrary-rational checker: only the compact topology expression crosses the
generic pure evaluator, and its `compute_exp` result is converted by the
existing proved `compute_exp_to_cv` handoff.  The current G6 correction replaces
only that last topology execution mechanism after proving it equivalent; it
does not change the ordinary whole-call semantics.

This closes G5C logic, not G5P and not the first theorem.  G6 is now also
closed for the case-16594 callback: the complete type-inferred executable
accepts the exact 875-cell / 1,749-token call, and the full role mutation
matrix fails closed.  G7 still has to typecheck the
root-to-original-statement adapter.  No verified runtime build is authorized
by G5C/G6 alone, and audit 6 still requires an owner scope decision before
G8 because the all-NL G5P callback remains pending.

In parallel, the freed build slots are assigned to the capped stock-route
projection: join the existing 812-source/7,814-selected-leaf inventory with
certificate cell/topology sizes, measure a stratified 20--30-inequality batch,
and report compute, handoff, RSS, and error-bounded total CPU-hour estimates.
No runtime rebuild or hour-scale replay is justified for the first-theorem
path at this step.

### Historical path to the current boundary

The genuine cell-0 fixed-word trace and its exact analytic meaning now close
on commit `abb3694f67`.  The checker executes all **167** authenticated
instructions, consumes all 31 typed certificates, emits the 134 diagnostic
intervals, and leaves exactly one Taylor result.  Its measured `cv_eval`
execution is **1.8 seconds** on a fixed-word box proved to enclose the
authenticated production box.

The resulting theorem is no longer tied to the legacy exact-rational
certificate stream.  A bounded comparison showed that **122 of 134** emitted
word intervals do not enclose the corresponding legacy payload intervals;
the two streams are different witnesses with different guard margins.  The
v4.355 proposal to prove one 134-item payload identity is therefore retracted.
The corrected proof treats the 31 fixed-word certificates as untrusted
witnesses checked independently by the successful evaluator.

The generic refinement theorem now turns that checked execution into an exact
object-q analytic run for the authenticated source program, using the proved
source/prepared-plan relation and proved enclosure of the authenticated center
and outer boxes.  The final object result has a valid domain, a strictly
negative completed upper bound, and satisfies the six-dimensional ordinary
acceptance contract.  Follow-up commit `31f6a133b` transfers that contract to
the authenticated source expression and production boxes.  This completes the
HOL4 numerical-to-exact-analytic semantic core for the first genuine leaf.

G2b is complete.  One structural theorem now composes the generic production
entry theorem through the actual two-list recursion and the canonical 21
upper-triangular index pairs.  It does not replay 21 captured numerical
results.  The exact clean source built in 1m08.3s wall with 1,948,144 KiB peak
RSS.

The positive product-delta track G2c is complete.  The production six-gradient
and complete-Hessian results are proved equal to the corresponding object-level
constructors used by `bounded_object_q_delta_four_coordinate_cv`.  Generic
success/length theorems now cover the signed-term selection and all-six gradient
construction.  A production source-item theorem also proves that, given the
center-jet and outer-Hessian evaluator results, recompletion returns the exact
six-field runtime state; its companion theorem connects that state to the
analytic `BoundedObjectQTaylor` value.  The production delta interval-sum
left fold, shared by the center and Hessian calculations, now has a generic
exact evaluator theorem for arbitrary encoded interval lists as well.  The
production delta value and complete six-component gradient calls now also
have exact arbitrary-input evaluator theorems; the gradient proof sequences
all 21 interval products and six signed component sums from the real source.
The compact production delta Hessian is now covered too: its actual 21-row
source constructor, generic row summation, and final packed 21-entry result
all have exact evaluator theorems for arbitrary six-element encoded inputs.

The production center-jet half of G2c-3 is complete.  The proof
uses the authenticated source bodies for the delta-product jet, its six-value
environment wrapper, and `candle_cv_q_dim_jet_make`; it sequences the generic
delta value, gradient, and Hessian theorems and returns the exact object-level
jet for arbitrary encoded six-element environments and any coordinate below
six.  It is not a captured coordinate-0 computation.

The packed outer-Hessian half is now complete too.  Its arbitrary-input
theorem evaluates the six outer-box lookups, the compact 21-entry delta
Hessian, the center-box six-gradient, the production gradient-completion
constructor, the selected coordinate interval, and the final product-Hessian
call.  The result is exactly the object-level outer Hessian already used by
the semantic source-item relation; it is not a captured cell-0 value.

G2c is now complete.  One generic theorem composes the exact center jet and
outer Hessian through the production source-item/recompletion wrapper for any
coordinate below six and arbitrary valid six-element radius, center-box, and
outer-box inputs.  Explicit corollaries instantiate that theorem at the three
authenticated positive coordinates 0, 1, and 2.  The result is the complete
six-field runtime state used by the existing analytic source-item relation;
it is not a closed computation over captured cell-0 values.

G2 is now complete.  The corresponding negative-delta production source-item
family has one arbitrary-coordinate exact evaluator/refinement theorem.  From
the ordinary fixed-word success and coverage evidence it derives the exact
object-q Taylor value, coverage of that value by the word result, the exact
production `compute_eval` result, and runtime equivalence of the returned
six-field source state.  The genuine coordinates 3, 4, and 5 are instances of
that theorem; no captured cell values are used.

The current G3 blocker is no longer the first ordinary evaluator/semantic
handoff.  The unified step and its general-prefix induction now compose that
handoff, the fixed-word trace, and the flat certificate cursor.  A genuine
authenticated trace through the first complete ordinary stretch, instructions
0--33, is green (`d7c8f5c3f`), and the semantic trace has a proved append rule
(`68776e5be`).  The early splice probe at the first specialized positions 34
and 35 then found a narrower representation obligation: production runtime
radii are exact-rational CVs, while the fixed-word semantic run uses their
word-derived CV representations.  They are related by the existing authenticated
`LIST_REL` relation but are not required to be byte-identical.

Commit `45af1b789` closes that transport obligation generically.  The positive
product-delta and negative-delta evaluator/refinement theorems now accept any
encoded runtime radii related to the semantic radii and return a runtime state
refining the same exact object-q result.  The exact theory build took 65.17
seconds with 2,022,136 KiB peak RSS.  The next exact task is the concrete joint
splice through positions 34 and 35, followed by repetition of that bounded
pattern through all 167 positions.  The resulting
entry result must still be connected to the existing Candle theorem
`candle_cv_q_packed_object_dispatch_entry_accept_cell_pass` (or its smaller
source-certificate contract) and a genuine cell-0 `m_cell_pass`
instantiation.  G4 still has the executable and conditional contract skeleton
described above, but not its discharged 875-leaf/topology premises.  G3
through G9 remain open.

Further focused G3 work has now made the remaining trace structure explicit.
The six certificate-free instruction families share one joint
word/object/evaluator theorem (`fd56a5670`).  Square root, inverse, and
arctangent have corresponding certified joins, and the authenticated cell-0
packet ledger supplies their 5/2/8-field guards.  Commit `47118a893` now
combines all nine general-code families under one packet-suffix invariant.
The fast 134-field payload is also proved distinct from the legacy payload
(`5b4117f84`), so no legacy-payload identity remains in the plan.

Commit `b17dee352` adds the general all-ordinary-prefix induction and its first
genuine authenticated instantiation.  The concrete theorem consumes source
and prepared instructions 0--9 from the canonical 167-position program,
threads the exact word trace and packet ledger, and records the matching
object-q semantic and production-evaluator trace while retaining the exact
suffix for instruction 10.  This prefix includes the first polynomial,
pi-half, square-root, inverse, multiplication, and arctangent steps, including
the first certificate-consuming operations.  Its fresh exact build took
1m49.28s and 4,249,736 KiB peak RSS.  This closes G3d as a representation and
composition test; it does not close the full trace or a leaf theorem.

### G3 finite checklist

| Subgate | Status | Exit criterion |
|---|---|---|
| G3a. Cell-0 semantic source result | **DONE** | Exact 167-step fixed-word result, exact-object analytic meaning, and source acceptance. |
| G3b. Unified general-code joint step | **DONE** | One theorem joins all nine ordinary/certificate-consuming families while preserving the packet suffix. |
| G3c. Specialized delta joins | **DONE** | Six generic delta adapters, three positive and three negative, including transport from authenticated exact-rational runtime radii to the related fixed-word semantic radii. |
| G3d. Authenticated 0--9 prefix | **DONE** | The genuine prefix crosses the first certificate-free and certificate-consuming families and leaves the exact word/object/runtime states and packet suffix. |
| G3e. Full 167-step trace | **DONE** | General induction plus the six specialized positions yields the ordinary evaluator result under a structural clock bound. |
| G3f. Arbitrary-cell leaf theorem | **DONE** | Successful accepted-cell inputs yield the matching `m_cell_pass`; cell 0 is a concrete instantiation, not the theorem's scope. |

The earlier cell-0 vertical slice was only a representation test.  The later
quantified trace and leaf theorems, rather than that slice, close G3.

### G2c finite checklist

| Subgate | Status | Exit criterion |
|---|---|---|
| G2c-1. Product formula layer | **DONE** | Production center value, six-gradient, and canonical 21-entry Hessian have exact evaluator theorems and object-semantic identities. |
| G2c-2. Delta intermediates | **DONE** | The interval-sum, production delta value, complete six-component gradient, exact 21-row Hessian constructor, generic row sums, and final packed delta Hessian all evaluate exactly for arbitrary encoded inputs. |
| G2c-3. Center jet and outer Hessian | **DONE** | The exact production center jet and packed outer Hessian evaluate for arbitrary valid six-element environments and coordinates below six, through the authenticated production source bodies. |
| G2c-4. Recompletion and three instances | **DONE** | The production source-item call evaluates to its complete exact runtime state for arbitrary valid inputs and coordinates below six; explicit coordinate 0, 1, and 2 corollaries are exported. |

These are subgates of G2c, not additional top-level gates.  If any of them
requires a new mathematical result rather than evaluator composition or an
existing semantic identity, the planning estimate must be revised before a
long build or full replay.

## Local proof-stack estimate and uncertainty

The earlier **2--4 optimistic / 3--7 planning-day** range compressed several
different risks and is retired as a work-control estimate.  It may be retained
only as historical context for the local proof stack; it is not an end-to-end
delivery estimate.  The per-packet table below now controls G3--G8 separately.
It still cannot responsibly estimate compatible-state reconstruction or the
fresh confirmation run until the S0/G6/G8 preflights measure them.

The estimate must be revised immediately if any of these assumptions fails:

1. the six now-proved delta step results do not fit the existing recursive
   state relation;
2. the fixed verdict differs from the ordinary final Boolean on the exact
   authenticated representation; or
3. the generalized topology contract does not follow from the existing replay
   invariants without new mathematics; or
4. the existing analytic/original-statement adapter needs a new mathematical
   theorem rather than an instantiation or representation bridge.

No such failure is currently known, but none of G3--G9 is counted as complete
until its exact exit criterion is met.

### Per-packet controls

| Work packet | Planning effort | Feedback cap |
|---|---:|---:|
| G3b--G3d joint step and prefix | 0.5--1.5 focused days | 3 minutes per exact theory build; reduce any failure before a longer run. |
| G3e--G3f trace and leaf | 1--3 focused days | 10 minutes for a bounded concrete trace, 3 minutes for local theorem edits. |
| G4 topology adapter | 1--3 focused days, high uncertainty | 10 minutes per focused probe; after one focused day without a stable invariant, publish the exact goal and re-estimate. |
| S0 HOL4 half and G5C callback | 1--3 focused days after G3/G4 stabilize | 10 minutes per callback/clock probe; no bootstrap. |
| G6 compiled probe | 0.5--1 focused day | 30 minutes per exact integration probe; a fallback branch blocks G8. |
| G7 original handoff | 0.5--2 focused days | 10 minutes per focused proof probe. |
| G8 verified build/runtime | external fresh-checkout reference is 8--10 elapsed hours; exact local callback closure still requires a measured preflight | One frozen attempt only after G3--G7 and source closure are green; explain any material difference from the 8--10-hour reference before launch. |
| G8 state reconstruction and G9 | not yet responsibly estimated | Require a measured minimum-state preflight before launch. |

Completion reports must record actual elapsed time and peak RSS.  These are
planning controls, not guarantees or an end-to-end delivery estimate.

## Working rules

1. The public metric remains **first original theorem 0/1** until G9 passes.
2. Do not call the result "close" as a calendar claim.  Report the highest
   completed gate and the current subgate instead.
3. Keep proof edit loops below three minutes.  Silence at the cap is a harness
   failure to diagnose, not grounds for a longer timeout.
4. Do not start a runtime rebuild or hour-scale run before G3--G6 are green on
   exact source bytes and G8 has a measured minimum-state reconstruction
   preflight.  Continue to use bounded whole-call development probes when they
   answer a specific representation or proof question.
5. Any newly discovered obligation must be attached to one of these gates,
   given an exit criterion, and reflected in the estimate.  It must not appear
   as untracked "one more thing".
6. Commit each coherent theorem gate and record its clean build time, peak RSS,
   assumptions, and exact successor gate.

## When it is fair to say “close”

The project is technically well-supported and the route is finite, but it is
not yet fair to use “close” as a delivery estimate.  A defensible threshold is
after G7: at that point the complete call has a proved ordinary meaning, the
fast callback is connected to it, and the original-statement adapter has
typechecked, leaving the verified runtime/state construction and the fresh
confirmation run.  Even then, G8 may still expose a material build or
state-reconstruction cost.  Until G7, report the highest completed gate and
**first theorem 0/1**; currently that is **G3 complete, with generic G4
composition proved and its authenticated real-data instantiation pending**.
