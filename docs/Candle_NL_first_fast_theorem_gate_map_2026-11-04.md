# Candle NL first fast theorem: live gate map

Date: 2026-11-04 UTC

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
- First original Flyspeck NL theorem through the fast route: **0/1**.

The numerical result is not yet the original HOL theorem.  The missing work
is the proved semantic composition from the accepted fast computation to the
original statement.

## Gates

| Gate | Layer | Status | Exit criterion |
|---|---|---|---|
| G0. Genuine data and numerical execution | computation | **DONE** | The authenticated source, certificate plan, 167-position program, and all 875 cells accept through the fixed fast checker. |
| G1. Ordinary instruction-family bridge | logic | **DONE** | Every ordinary family has a generic evaluator-to-exact-object theorem, including certificate-cursor preservation for inverse, square root, and arctangent. |
| S0. End-to-end contract skeleton | representation/control | **IN PROGRESS** | The Candle whole-call target and HOL4 `compute_fast_eval_ok` target typecheck against the real equation set, with every remaining premise assigned below. The Candle half now typechecks; the HOL4 callback/clock half is pending. |
| G2. Six specialized delta instructions | logic | **IN PROGRESS** | All six specialized evaluator results are connected to exact object states for arbitrary valid inputs. The product-delta wrapper is current; the three negative cases still need the generic evaluator join despite their existing mathematical refinement and genuine closed probes. |
| G3. Complete ordinary trace and leaf semantics | logic/clock | **PENDING** | Generic ordinary and specialized steps compose through all 167 positions for an arbitrary valid explicit-radius cell; the entry result implies that cell's `m_cell_pass`; a structural ordinary-evaluator clock bound is exported. |
| G4. Whole jobs and topology | representation/logic | **IN PROGRESS** | The 875 canonical variable jobs and packed-cell stream are consumed in lockstep, malformed or unequal streams reject, every accepted entry supplies the matching source-box leaf theorem, and the 1,749-token run combines those exact leaves to the authenticated singleton root. |
| G5. Generic fast callback | HOL4 logic | **PENDING** | A plan-driven witnessed callback refines the exact four-argument whole call under `compute_default_clock = 10^9`; altered equation sets, source/plan, packed cells, jobs, or topology reject. |
| G6. Development runtime integration | runtime/representation | **PENDING** | The exact frozen callback is installed in a development runtime, the genuine call records a fast-branch hit, and lightweight compiled tests cover all payload roles and mutations. |
| G7. Analytic and original-statement adapter | logic | **PENDING** | The authenticated root `m_cell_pass` is converted by the existing case-16594 reconstruction to a typechecked conditional theorem with the literal original conclusion and audited assumptions. |
| G8. Verified runtime and prepared state | build/runtime | **PENDING** | The exact callback bytes pass the verified rebuild preflight and build; the minimum compatible Flyspeck/NL predecessor state is reconstructed and its cold elapsed time and peak RSS are measured. |
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

A bounded attempt at the generalized topology proof found useful type/layout
hazards, including an initial packed representation that would have broken
the existing logical job decoder.  That layout was corrected.  The remaining
topology theorem was left explicit rather than entering a tactic-fragile or
hour-scale proof loop.  The HOL4 callback/clock skeleton remains the other S0
half.

## Current exact blocker

G2b is complete.  One structural theorem now composes the generic production
entry theorem through the actual two-list recursion and the canonical 21
upper-triangular index pairs.  It does not replay 21 captured numerical
results.  The exact clean source built in 1m08.3s wall with 1,948,144 KiB peak
RSS.

The current gate is G2c.  The production six-gradient and complete-Hessian
results are proved equal to the corresponding object-level constructors used
by `bounded_object_q_delta_four_coordinate_cv`.  Generic success/length
theorems now cover the signed-term selection and all-six gradient
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

The production center-jet half of G2c-3 is now complete as well.  The proof
uses the authenticated source bodies for the delta-product jet, its six-value
environment wrapper, and `candle_cv_q_dim_jet_make`; it sequences the generic
delta value, gradient, and Hessian theorems and returns the exact object-level
jet for arbitrary encoded six-element environments and any coordinate below
six.  It is not a captured coordinate-0 computation.

G2c-2 is therefore complete.  The remaining G2c component work is composition
of the production packed outer Hessian with its already-proved semantic value
on arbitrary valid inputs.  Then instantiate the source-item
wrapper for authenticated coordinates 0, 1, and 2.  G3 through G9 remain
after it; G4 has the executable and conditional contract skeleton described
above, but not its discharged leaf/topology premises.

### G2c finite checklist

| Subgate | Status | Exit criterion |
|---|---|---|
| G2c-1. Product formula layer | **DONE** | Production center value, six-gradient, and canonical 21-entry Hessian have exact evaluator theorems and object-semantic identities. |
| G2c-2. Delta intermediates | **DONE** | The interval-sum, production delta value, complete six-component gradient, exact 21-row Hessian constructor, generic row sums, and final packed delta Hessian all evaluate exactly for arbitrary encoded inputs. |
| G2c-3. Center jet and outer Hessian | **HALF DONE** | The exact production center jet now evaluates for arbitrary valid six-element environments and coordinates below six.  The remaining half is the production packed outer-Hessian evaluator. |
| G2c-4. Recompletion and three instances | **IN PROGRESS** | Recompletion is proved both executable and semantically related once the two component results hold.  Instantiation for authenticated coordinates 0, 1, and 2 remains. |

These are subgates of G2c, not additional top-level gates.  If any of them
requires a new mathematical result rather than evaluator composition or an
existing semantic identity, the planning estimate must be revised before a
long build or full replay.

## Local proof-stack estimate and uncertainty

This is an engineering estimate, not a guarantee:

- optimistic, if the remaining joins reuse the existing theorem shapes
  directly: **2--4 focused development days**;
- planning range allowing for local representation or theorem-shape repairs:
  **3--7 focused development days**.

This range applies only to the local semantic proof stack through G7, assuming
the existing theorem shapes compose as expected.  It is **not** an end-to-end
delivery estimate.  It excludes the HOL4 callback implementation, development
runtime integration, the verified runtime/compiler rebuild, reconstruction of
a compatible Flyspeck/NL prepared state, and the fresh confirmation run.  Those
runtime and reconstruction costs must be measured by S0/G6/G8 preflights before
an end-to-end calendar estimate is stated.

The estimate must be revised immediately if any of these assumptions fails:

1. the six delta step results do not fit the existing recursive state relation;
2. the fixed verdict differs from the ordinary final Boolean on the exact
   authenticated representation; or
3. the generalized topology contract does not follow from the existing replay
   invariants without new mathematics; or
4. the existing analytic/original-statement adapter needs a new mathematical
   theorem rather than an instantiation or representation bridge.

No such failure is currently known, but none of G3--G9 is counted as complete
until its exact exit criterion is met.

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
**first theorem 0/1**; currently that is **G2 in progress, S0 and G4 partially
exercised**.
