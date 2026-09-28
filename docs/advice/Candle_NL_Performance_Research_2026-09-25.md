# Why reflected Flyspeck nonlinear checking is not yet dramatically faster

Independent source review, 25 September 2026.

**Assessment:** reflection remains a plausible route to large improvements, but the current prototype combines removal of arithmetic proof steps with several substantial new costs. Its performance does not measure the benefit of reflection in isolation. There are now specific, testable implementation explanations for the small gains. No new runtime speedup is claimed by this review.

The most useful contributions are a source-level count of unnecessary work in constant nodes, identification of GCD fuel construction, repeated evaluator setup, and proof-producing computation inside an untrusted hint generator. These observations do not require abandoning the reusable analytic soundness theorem.

## Evidence and scope

I retrieved and read repository source directly, including commits named in the worker's latest reports rather than relying only on branch tips:

| Source | Snapshot inspected |
|---|---|
| Candle centered/rounded prototype and supporting arithmetic | `473eeadceaac8658a8a948793eeed9d85d06902d` |
| Candle older analytic adapter and comparison | `a1ea0a44e1bf910238db7d7b16b180c7dc0d15ae`, supplemented with files at `473eead` |
| Project reports v1.77–v1.81 | `815d1c3c874a7f5a3d328d58d9bcc722dccb02da` |
| CakeML implementation of Candle's compute primitive | `dcc03f2866f05b1db18b9f45c731ce45c3a3133e` |
| Flyspeck formal and informal interval/Taylor code | `40e3e6dc7cb424b7db10a0155c2e6728e6f31924` |

The latest supplied session trace describes later soundness-proof work. This review does not assume that every live worker edit is present in these snapshots, or that the inspected CakeML source independently authenticates the worker's running executable. Reported benchmark times are the worker's measurements; I did not rerun Candle here. The source-level operation count below was independently calculated and checked with a short Python transcription.

## 1. What the historical comparison establishes

The 2013 Solovyev–Hales paper reports a 2,000–4,000-fold formal/informal difference on selected Flyspeck inequality sets. This is a concrete comparison with C++ numerical verification, not a universal factor for all implementations or the entire final proof. Its formal implementation already used bounded-precision arithmetic, caching, and certificate hints to avoid unnecessary Taylor work. [P1]

Tame-graph reflection executed generated ML after general correctness reasoning. That is a useful architectural precedent, but not a benchmark of Candle's numerical interpreter. [P2]

Candle's compute facility evaluates a first-order language with integer-and-pair values. Its large published gains were against proof-producing evaluation mechanisms. It does not automatically compile the supplied numerical checker to a specialized native floating-point program. [P3]

Thus two questions must be separated: how much proof construction reflection removes, and how efficiently the resulting numerical algorithm executes.

## 2. The actual current results

There is already a modest verified speedup on the earlier polynomial certificate. Report v1.79 records two matched runs: reflected leaf proof averages 14.213 seconds versus 16.061 seconds for legacy; including final assembly, 19.203 versus 21.066 seconds, approximately an 8.8% reduction. This followed removal of repeated finish computations and expensive generic theorem rewriting. It demonstrates that proof-boundary engineering matters. [R79]

The harder action-296 non-polynomial example is separate. The earlier forward interval-jet approach needed 71 successful subcells and 78 attempts for a leaf that legacy closed directly. Its Hessian bounds were much looser. The centered approach now closes the same parent using two children; v1.81 reports 39.41 seconds including restore, preparation and diagnostics, but without the completed parent theorem. That is not directly comparable with the 42.35-second legacy complete proof. [R80, R81]

Neither result estimates total Flyspeck NL time or establishes an orders-of-magnitude improvement.

## 3. Concrete source findings

### A. Outward rounding has bounded growth, but has not replaced the fraction engine

The centered implementation rounds results to denominator `10^12` at instruction boundaries. Inside those instructions it still calls general exact-rational addition, multiplication and normalization. Taylor error accumulation explicitly uses the extended GCD normalizer. Matrix operations retain the ordinary normalized interval primitives. [C1, C2, C3]

This distinction matters: limiting the size of values passed between instructions removes an important failure mode, but does not make internal arithmetic cheap. The implementation still cross-multiplies denominators, performs Euclidean GCD computations, divides and validates the resulting quotients, and constructs nested pair values.

A genuine fixed-point backend would operate directly on scaled integers: addition at a shared scale requires no denominator multiplication or GCD; multiplication requires scaling and directed rounding. That is a possible later refinement, not something the current rounding wrapper already implements. Changing rounding placement can change bound tightness, so compare accepted boxes as well as arithmetic time.

### B. Even a constant node performs substantial Taylor reconstruction

In `cv_compute_analytic_expr_taylor_model_program_compute.ml`, polynomial constants and variables both call `candle_cv_q_dim_taylor_model_result_complete`. That function rounds the center and Hessian, reconstructs a whole-box value bound and all gradient bounds, and rounds them again. Constants go through this path despite having zero gradient and zero Hessian. [C1]

For a well-shaped dimension-n result, the value/gradient reconstruction performs the following normalized scalar additions and multiplications:

| Component | Normalized operations |
|---|---:|
| Center-gradient absolute dot product | `2n` |
| Radius-weighted Hessian sum | `2n² + 2n` |
| Half-Hessian multiplication and error addition | `2` |
| Adding the error interval to the center value | `2` |
| Reconstructing all gradient bounds | `2n² + 2n` |
| **Total** | **`4n² + 6n + 4`** |

At n=6 this is **184 normalizations: 99 additions and 85 multiplications**. This counts only completion's reconstructed value and gradients. It excludes the original instruction, rounding, comparisons, domain guards and interpretation overhead. The inspected definitions do not short-circuit these sums when their entries are zero. [C1, C3]

This is a static execution-count result, not a timing prediction. It shows why a compact source expression can still generate a great deal of numerical work. Special handling of constants, zeros, identities and known sparse derivatives deserves measurement before assuming that interpreter compilation is the only remaining route.

### C. Each normalization builds a list just to limit GCD iteration

The normalizer's first Euclidean chunk receives fuel encoded as **128 nested `Cexp_pair` constructors**. The fast interpreter evaluates arguments eagerly; its translation represents these pairs as operations, not a pre-evaluated shared constant value. Consequently, each initial chunk constructs that fuel value again, even when the actual GCD needs very few iterations. Additional chunks are conditional; the extended normalizer does not always execute 1,024 GCD steps. [C2, K2]

The 184 normalizations above therefore entail at least **23,552 fuel-pair constructions** at the interpreter level for one six-dimensional completion. This excludes the pairs representing the actual numerical results.

Possible local experiments include passing a once-built fuel value through the computation or proving an equivalent numeric-countdown implementation. These preserve the bounded normalization policy. A fixed-scale backend could avoid most GCD calls entirely. The relative benefit needs a profile; this review does not assign a speedup factor.

### D. Eager execution computes results that are immediately discarded

The centered multiplication code invokes the complete whole-box jet multiplier and then projects only its Hessian. Under the inspected call-by-value interpreter, the unused value and gradient are computed too. Analogous full-jet projections occur for nonlinear primitives. [C1, C4, K2]

Separately, interval multiplication calculates its four endpoint products twice: once for the minimum and once for the maximum. No sharing binding connects the two groups. [C5]

These are opportunities for computational refinements with reusable equivalence proofs: dedicated Hessian operations, sharing endpoint products, and avoiding unnecessary dense components. They need not change the analytic theorem or weaken any guard. Dense 6×6 Hessians also carry 36 entries where symmetry permits 21 independent entries; that change is more involved and should be justified by measurement.

### E. A checkpoint does not cache the compute primitive's compiled equation table

The inspected `compute_def` performs, on every call: initialization-theorem checking, code-equation validation, constant/arity checks, `build_funs`, input translation, execution, and conversion of the result back to a HOL term. `build_funs` compiles all supplied equations, not merely functions executed along this input's path. [K1, K2]

Keeping ML theorem lists in a checkpoint saves library loading, but does not remove this per-call pipeline. The centered two-cell test makes a traced-program call and a finish call for each child. Its traced result includes the computed Taylor data and diagnostic guard information, so it also crosses a larger HOL-term boundary than a compact acceptance bit would. [C6]

The likely remedies depend on measurement: a narrower equation set, an internal loop over several boxes, an acceptance-only result, or eventually a verified persistent compiled context. Such a context cannot simply bypass equation checking; its validity must be retained by the kernel interface and soundness argument.

### F. Untrusted hint preparation is doing proof-producing arithmetic

`candle_q_point_sqrt_callback` invokes `REAL_RAT_REDUCE_CONV` on a substituted rational expression, takes the right-hand side of the resulting theorem, and uses it to propose square-root endpoints. The theorem is not retained by this callback. The checker subsequently validates those proposals. [C7]

Moreover, the two-cell driver calls `candle_q_dim_analytic_jet_prepare_point_six` for each child. That function re-enters the source preparation/reification path with the new certificate callback. Fixed source authentication and changing per-box hint data are therefore not yet fully separated in this path. [C6, C7, C8]

This is a concrete answer to the earlier question about work that could happen outside Candle. Ordinary arithmetic could propose these endpoints without manufacturing a proof of the proposal calculation, provided the existing exact guard and source correspondence remain decisive. The source expression could be authenticated once while the changing certificates are supplied as data. This is an opportunity to exploit the existing certificate-erasure/general-soundness direction, not a reason to develop per-expression calculus proofs.

## 4. What is already present, and should not be suggested as if new

- The worker already uses one source program and shared jets, rather than 43 expanded derivative programs.
- Centered reconstruction, outward rounding, domain checks and cached whole-box bounds are already implemented numerically.
- The earlier analytic path already avoids computing a center Hessian where only first derivatives are needed.
- Checkpoints have already removed repeated long library loads from ordinary proof edits.
- Flyspeck already has informal numerical implementations, constant folding, common-subexpression references, adaptive precision and certificate-driven shortcuts. Its informal implementation can provide a useful comparison without recreating the whole original C++ system. [F1, F2]

The fresh questions are whether the implementation of these ideas is economical and where the remaining cost sits.

## 5. A small experiment that separates the explanations

Use existing fixtures/checkpoints. Freeze the formula, boxes, certificate data, arithmetic precision and source theorem. Include several distinct boxes and more than one representative expression where supported. Charge reusable preparation once. Time cold preparation separately from warm runs with, for example, 1, 8 and 64 boxes; avoid using identical repeated boxes as the only evidence because caching can distort the result.

| Measurement | What it distinguishes |
|---|---|
| `Kernel.compute` returning a constant with the same full equation list | Fixed validation/compilation cost before useful numerical work |
| Current checker, returning full diagnostics versus only an acceptance verdict | Result conversion and diagnostic overhead |
| One internal batch of boxes versus separate calls | Repeated setup, input conversion and theorem-boundary costs |
| Same centered rounded algorithm as ordinary executable code, compared with `Kernel.compute` | Interpreter/encoding overhead, holding the numerical algorithm fixed |
| Existing Flyspeck informal evaluator at matched precision and boxes | Algorithm/arithmetic differences relative to the legacy numerical method |
| Complete proof after computed acceptance | Remaining theorem handoff, source reconstruction and certificate gluing |

For the numerical calls, count normalizations/GCD iterations, fuel constructions, integer sizes, constructor operations and rejected/subdivided boxes where cheap. A standalone constant/variable completion test and a shared-fuel variant would directly test findings B–C without loading the full verifier. Equality of computed outputs should be checked when testing an intended exact refinement.

The constant-return control is only an estimate of setup cost. Subtracting it mechanically from a large call ignores input-size, GC and cache effects; internal phase timing is preferable if available. An ordinary-code transcription is diagnostic until separately verified and must not authorize proof results.

Interpretation:

- Large fixed cost: reuse validated setup or amortize through internal batches.
- Large output/handoff cost: keep intermediate data inside computation and return compact acceptance evidence.
- Slow ordinary centered evaluator too: improve arithmetic representation, sharing or numerical algorithm before rebuilding the kernel.
- Fast ordinary evaluator but slow reflected execution: inspect fuel/data allocation, evaluator specialization and eventually verified compilation.
- Fast boxes but many more subdivisions: improve enclosure quality or recover certificate shortcuts; faster arithmetic alone may not help enough.

## 6. How radical a change might ultimately be warranted?

The soundness theorem should describe what accepted bounds establish about the source formula, with representation and execution refinements underneath. That allows the current proof investment to survive changes in arithmetic or evaluator implementation.

A credible sequence is: complete the current genuine-leaf proof; run the discriminating measurements; remove demonstrated repeated/unused work; investigate a proper bounded-precision backend and compact certificate loop if those dominate. Verified compilation or specialization of the computational checker is a larger possible step if interpreter cost remains decisive. Native floating-point support would require its own justified semantic connection; arbitrary native output must not be accepted as a theorem.

Relevant precedent exists beyond tame graphs. Rocq's Interval package separates arithmetic and execution choices, including machine floating point where supported and native rather than VM computation. It explicitly trades greater setup cost for faster long computations. This supports investigating both layers, not treating “reflection” as a complete numerical implementation strategy. [P4]

The later HOL computation paper also discusses specializing the interpreter before execution; its reported preliminary gain is about twofold, not thousands-fold. Porting translation automation alone should not be confused with compiling the numerical algorithm to native code. [P5]

**The present evidence does not show that reflection has failed. It shows that this prototype still performs a substantial amount of avoidable interpreted work. The next useful contribution is to measure those specific costs while preserving the general correctness proof, rather than promise a 1,000× factor or launch an unmeasured rewrite.**

## Sources

P1. Solovyev and Hales, [Formal Verification of Nonlinear Inequalities with Taylor Interval Approximations](https://arxiv.org/pdf/1301.1702), §§3–5.

P2. Hales et al., [A Formal Proof of the Kepler Conjecture](https://arxiv.org/pdf/1501.02155), §§5,7.

P3. Abrahamsson and Myreen, [Fast, Verified Computation for Candle](https://research.chalmers.se/publication/537247/file/537247_Fulltext.pdf), §§2,6–9.

P4. [Rocq Interval documentation](https://coqinterval.gitlabpages.inria.fr/), precision and execution parameters.

P5. [Fast, Verified Computation for HOL ITPs](https://link.springer.com/article/10.1007/s10817-025-09719-8), §§7,9,12.

R79. [Project v1.79 comparison](https://github.com/JUrban/flyspeck-candle-project/blob/815d1c3c874a7f5a3d328d58d9bcc722dccb02da/docs/progress/2026-09-25-v1.79-reflected-proof-linking-and-checkpoint-boundary.md).

R80. [Project v1.80 real non-polynomial leaf](https://github.com/JUrban/flyspeck-candle-project/blob/815d1c3c874a7f5a3d328d58d9bcc722dccb02da/docs/progress/2026-09-25-v1.80-live-action296-reflected-leaf.md).

R81. [Project v1.81 centered two-cell calculation](https://github.com/JUrban/flyspeck-candle-project/blob/815d1c3c874a7f5a3d328d58d9bcc722dccb02da/docs/progress/2026-09-25-v1.81-centered-taylor-two-cell.md).

C1. [Centered Taylor-model implementation](https://github.com/JUrban/candle/blob/473eeadceaac8658a8a948793eeed9d85d06902d/candle/cv_compute_analytic_expr_taylor_model_program_compute.ml), especially `result_complete`, `poly_constant`, `result_mul`, and `compute_eqs`.

C2. [Rational normalization](https://github.com/JUrban/candle/blob/473eeadceaac8658a8a948793eeed9d85d06902d/candle/cv_compute_exact_rational_normalize.ml) and [extended normalization](https://github.com/JUrban/candle/blob/473eeadceaac8658a8a948793eeed9d85d06902d/candle/cv_compute_exact_rational_normalize_extended.ml).

C3. [Extended Taylor accumulation](https://github.com/JUrban/candle/blob/473eeadceaac8658a8a948793eeed9d85d06902d/candle/cv_compute_analytic_expr_extended_taylor.ml).

C4. [Dense jet implementation](https://github.com/JUrban/candle/blob/473eeadceaac8658a8a948793eeed9d85d06902d/candle/cv_compute_polynomial_expr_dim_jet_compute.ml), especially `candle_cv_q_dim_jet_mul`.

C5. [Interval multiplication](https://github.com/JUrban/candle/blob/473eeadceaac8658a8a948793eeed9d85d06902d/candle/cv_compute_exact_interval_mul_core.ml), `candle_cv_q_interval_mul`.

C6. [Two-cell test driver](https://github.com/JUrban/candle/blob/473eeadceaac8658a8a948793eeed9d85d06902d/candle/test_cv_compute_analytic_expr_action296_first_leaf_taylor_model.ml).

C7. [Point certificate preparation](https://github.com/JUrban/candle/blob/473eeadceaac8658a8a948793eeed9d85d06902d/candle/cv_compute_analytic_expr_point_certificate_prepare.ml).

C8. [Source preparation and proof adapter](https://github.com/JUrban/candle/blob/473eeadceaac8658a8a948793eeed9d85d06902d/candle/cv_compute_analytic_expr_jet_prove.ml).

K1. [Candle kernel compute pipeline](https://github.com/JUrban/cakeml/blob/dcc03f2866f05b1db18b9f45c731ce45c3a3133e/candle/prover/compute/computeScript.sml), `compute_def`.

K2. [Candle fast interpreter](https://github.com/JUrban/cakeml/blob/dcc03f2866f05b1db18b9f45c731ce45c3a3133e/candle/prover/compute/compute_execScript.sml), `exec_def`, `to_ce_def`, `build_funs_def`.

F1. [Flyspeck formal interval evaluator](https://github.com/JUrban/flyspeck/blob/40e3e6dc7cb424b7db10a0155c2e6728e6f31924/formal_ineqs/arith/eval_interval.hl).

F2. [Flyspeck informal Taylor evaluator](https://github.com/JUrban/flyspeck/blob/40e3e6dc7cb424b7db10a0155c2e6728e6f31924/formal_ineqs/informal/informal_taylor.hl), together with the adjacent informal arithmetic and evaluator modules.
