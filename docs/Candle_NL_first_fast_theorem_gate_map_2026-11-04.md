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
- First original Flyspeck NL theorem through the fast route: **0/1**.

The numerical result is not yet the original HOL theorem.  The missing work
is the proved semantic composition from the accepted fast computation to the
original statement.

## Gates

| Gate | Status | Exit criterion |
|---|---|---|
| G0. Genuine data and numerical execution | **DONE** | The authenticated case-16594 source, certificate plan, 167-position program, and all 875 cells execute and accept through the fixed fast checker. |
| G1. Ordinary instruction-family bridge | **DONE** | Every ordinary family has a generic evaluator-to-exact-object stack theorem, including certificate-cursor preservation for inverse, square root, and arctangent.  These theorems cover the 161 ordinary positions without position-specific proofs. |
| G2. Six specialized delta instructions | **IN PROGRESS** | All six authenticated delta positions have evaluator results connected to complete exact analytic jets.  The three negative-derivative cases are covered.  For the three `4*x_i*delta` cases, center value and the full six-component gradient are covered; the product Hessian is the current subgate. |
| G2a. Generic product-Hessian entry | **IN PROGRESS** | One theorem evaluates the production entry constructor and identifies its exact product-rule interval for arbitrary valid row, column, and product coordinate. |
| G2b. Complete 21-entry product Hessian | **PENDING** | The entry theorem is composed through the production upper-triangular Hessian constructor, with its row/order contract proved. |
| G2c. Three complete product-delta jets | **PENDING** | Center value, six gradient entries, and 21 Hessian entries are packaged as the exact analytic result for each of the three authenticated product specializations. |
| G3. Whole 167-position semantic trace | **PENDING** | The existing generic recursive traversal is instantiated with the ordinary and specialized step theorems; it proves exact stack/certificate-cursor preservation and the final ordinary Boolean for the authenticated complete program. |
| G4. Fast one-call correspondence | **PENDING** | The compact fixed-checker verdict is proved equal to the ordinary complete-call result and supplies `compute_fast_eval_ok` for the authenticated call.  Mutated source, certificate, plan, and equation-set inputs reject. |
| G5. Analytic acceptance and original theorem | **PENDING** | The complete accepted result is fed through the existing universal analytic/Taylor soundness and original-statement adapter, yielding the literal original case-16594 Flyspeck theorem with audited assumptions and axioms. |
| G6. Fresh end-to-end confirmation | **PENDING** | A fresh run takes the fast branch, produces the same original theorem, and records preparation, checker execution, decoding, theorem handoff, total elapsed time, and peak RSS. |

## Current exact blocker

The G2a proof already unfolds and proves the real production evaluator's base
product and both conditional product-rule additions.  The remaining local
obligation is to reuse the already-proved generic scale-by-four evaluator for
the four row/column equality cases.  A new focused build on 2026-11-04 did not
reach its diagnostic marker inside the three-minute cap, so it did **not**
pass.  The cap was not raised.  Before another proof attempt, the focused
harness must expose whether time is being spent restoring/scanning or in the
final tactic itself.

This is a narrow immediate proof obligation.  Passing it will not by itself
make the first theorem complete: G2b through G6 will still remain.

## Planning estimate and uncertainty

This is an engineering estimate, not a guarantee:

- optimistic, if the remaining joins reuse the existing theorem shapes
  directly: **2--4 focused development days**;
- planning range allowing for local representation or theorem-shape repairs:
  **4--8 focused development days**.

The estimate excludes an all-NL production deployment and any later one-time
verified runtime/compiler rebuild.  It is only for the first original theorem
and its fresh fast-path confirmation.

The estimate must be revised immediately if any of these assumptions fails:

1. the 21-entry constructor cannot be composed from the generic entry theorem;
2. the six delta step results do not fit the existing recursive state relation;
3. the fixed verdict differs from the ordinary final Boolean on the exact
   authenticated representation; or
4. the existing analytic/original-statement adapter needs a new mathematical
   theorem rather than an instantiation or representation bridge.

No such failure is currently known, but none of G3--G5 is counted as complete
until its exact theorem exports.

## Working rules

1. The public metric remains **first original theorem 0/1** until G5 passes.
2. Do not call the result "close" as a calendar claim.  Report the highest
   completed gate and the current subgate instead.
3. Keep proof edit loops below three minutes.  Silence at the cap is a harness
   failure to diagnose, not grounds for a longer timeout.
4. Do not start a whole-case replay, runtime rebuild, or hour-scale run before
   G3 and G4 are green on exact source bytes.
5. Any newly discovered obligation must be attached to one of these gates,
   given an exit criterion, and reflected in the estimate.  It must not appear
   as untracked "one more thing".
6. Commit each coherent theorem gate and record its clean build time, peak RSS,
   assumptions, and exact successor gate.

## When it is fair to say “close”

The project is technically well-supported and the route is finite, but it is
not yet fair to use “close” as a delivery estimate.  A defensible threshold is
after G3 and G4: at that point the exact 167-position computation has a proved
ordinary meaning and the fast one-call verdict is connected to it, leaving the
known analytic/original-statement handoff and confirmation run.  Until then,
report **G2 in progress; first theorem 0/1**.
