# Candle nonlinear verification: completing the computational boundary

Research and directional proposal — 28 September 2026  
Updated before handover against worker messages through 704877 and project commit `5b6ecec`.

## A request for the worker

Could you review the architectural diagnosis below against your current work? The aim remains a large reduction in the cost of verified nonlinear checking through reusable soundness proofs and efficient computation. The existing development has established valuable parts of that design, but the newly located native HOL Light benchmark makes the remaining performance gap much clearer.

Please treat this as a proposal to assess and adapt, rather than a request to implement every item. In particular, it would be useful to identify anything already superseded, the smallest experiment that could test the proposed boundary, and which existing theorems can be reused. Substantial reusable proof or preparation work is welcome when it has a credible workload-level payoff. We would prefer that investment over indefinitely optimizing expensive per-box proof adapters.

This concerns the reflected NL development. It does not request interrupting the protected direct Flyspeck/LP run or discarding completed evidence.

### Latest update before handover

The newer trace has been reviewed. It changes the operational position, but does not supply a new end-to-end timing or superseding implementation for the architectural issues below:

- The complete sequential result remains the 1,061-root/1,538-cell baseline. Group discovery reached its 12-hour launcher limit, recovered from the root-1000 checkpoint, and is resolving its final few roots at message 704877. No final grouped result or clean successful-schedule replay is shown yet.
- Discovery tries candidate groups, including failed larger groups and singleton fallbacks. The planned clean replay will execute the retained successful schedule. These are different costs; the elapsed discovery run is not the eventual recurring grouped-checking time.
- The worker is already planning to extend fixed-scale arithmetic through the hot rational path. This note acknowledges that direction. Its additional question is whether source preparation and structural proof obligations can move to a more complete computational boundary.
- The assessment in message 704374 explicitly reviews `Candle_NL_Performance_Research_2026-09-25.md`. It is not a response to this September 28 proposal or its newly located native HOL Light comparison.
- The latest public project commit adds only a progress report: `easy_3.dat` completed and a root-1000 recovery checkpoint was recorded. Direct action 184 remains open. [R24]

It is reasonable to finish the nearly complete discovery and preserve its result. The proposed architectural investigation can then use the existing small harness independently of the longer clean replay; that replay need not become a prerequisite for every experiment here. The grouped comparison will measure preparation sharing within the current design. It will not, by itself, decide whether this design meets the native-HOL-Light performance target.

## 1. Main conclusion

The current implementation contains genuine reflection: general analytic soundness results, shared numerical programs, and computed batch verdicts. It is not simply the old arithmetic proof script with a new name.

However, the completed 1,061-root run still performs substantial symbolic preparation and theorem construction around those computations. The code exposes three specific boundaries worth changing:

1. **Separate the stable formula/program from changing numerical certificates.** Box-dependent square-root hints currently enter annotated expressions and program variants, encouraging repeated source, compilation and encoding work.
2. **Compute the remaining structural checks.** Numerical acceptance is reflected, but source-erasure equality, representation obligations and tree coverage still have theorem-producing adapter work around them. General soundness results for much of this already exist.
3. **Measure and improve the numerical algorithm independently.** The current fixed-scale path remains a hybrid with expensive rational operations. Completing reflection alone does not guarantee native numerical performance.

The proposed destination is a small, reusable proof interface around a complete certificate-checking computation. It need not be one enormous call; bounded batches are compatible with this architecture.

## 2. Evidence and the performance target

### Public snapshot examined

- Project reports were initially audited at `0246c08ea7fded959e46421db08c27aaa0dad605` and refreshed at `5b6ececda5fc59299371e1a67cb2e7c56380e610`, whose added report is v2.41, dated 28 September. The intervening public project change is documentation only.
- Completed sequential checker: `JUrban/candle` at `469166f4e0a56f12eac30977e5f39733381b16cd`, the revision named by the run reports.
- Original Flyspeck source and historical log: `flyspeck/flyspeck` at `1ce0353008eba83d3c76ae9a25c3c242e4802d53`.

The public Candle branch name was behind the revision identified by the reports, so this audit used the exact accessible commit rather than treating the branch tip as authoritative. Later worker changes may supersede particular findings. No new Candle proof runs were executed for this review; implementation findings come from source inspection, and performance observations from retained reports and logs.

### A matched historical comparison

The captured target in `cv_compute_analytic_expr_action296_fixture.ml` matches the complete formula and domain of original input **10172, `(prep-8657368829,0)`**, after removing whitespace. This was checked programmatically, not inferred from a similar name. The original log records 1,061 passing leaves and 1,060 ordinary glue nodes, with no monotonicity nodes. [R1–R3]

| Implementation | Reported elapsed time | Output established |
| --- | ---: | --- |
| Historical verified Flyspeck/native HOL Light | 667.725002 s, approximately 11.13 min | Formal verification and an inequality theorem |
| Current reflected Candle sequential development run | 30,391.012 s, approximately 8.44 h | The 1,061 original leaf/root results, using 1,538 selected final cells |

The raw elapsed-time ratio is **45.514×**. This is a strong warning, not a controlled same-machine slowdown estimate. Hardware, runtime versions, surrounding contention and precise timing boundaries differ. Matching the formula and leaf count does not establish byte-for-byte identity of the historical certificate tree.

The original `Time` field is wall-clock `total_time` from the verifier: it includes function preparation, certificate search and verification, but excludes global library loading and some outer normalization/reporting. Candle's number is externally profiled elapsed time. The current driver returns a list of root theorems; its completion does not itself establish the final direct action-296 theorem. Thus the comparison does not exaggerate the original proof endpoint to Candle's disadvantage. It still needs a contemporary matched baseline. [R3–R6]

These 1,061 roots belong to **one inequality case**, not 1,061 independent Flyspeck inequalities. Neither this runtime nor its ratio should be extrapolated across all NL without a representative workload sample.

The 2013 nonlinear-verification paper reported an approximately 3,000× formal-versus-C++ gap on its experiments. That motivates looking for major savings, but it is not a measured prediction for this checker, this case or the final Flyspeck corpus. A 1,000–10,000× speedup should remain a research ambition with an explicitly named baseline. [R7]

### Current cost evidence

The worker's supplied full-run assessment, message 702149, reports these shares of measured inner time:

| Phase | Share |
| --- | ---: |
| Source preparation | 48.9% |
| Point-plan compilation | 13.6% |
| Final-cell preparation | 12.5% |
| Aggregate computed proof | 16.6% |
| Source extraction and live handoff | 8.4% |

The underlying large full-run phase file was not independently retrieved in this review; these percentages are attributed to that assessment. The public 32-root experiment independently supports the importance of preparation: sharing it reduced an otherwise matched run from 885.927 s to 639.734 s, a 1.3848× speedup, on the same 49 cells and theorem output. [R8]

The implications are limited but useful. Eliminating only the 16.6% aggregate-proof phase would improve the inner total by at most about 1.20×. Eliminating all three preparation phases would give at most 4× if the rest remained unchanged. Neither alone explains how to reach a thousandfold improvement. Also, “aggregate computed proof” includes adapter work; it should not be treated as pure evaluator time.

## 3. What should be retained

The note is not proposing that the worker repeat completed mathematical development.

| Existing result or facility | Role in the proposed path |
| --- | --- |
| Universal analytic/derivative and Taylor soundness | Keep as the mathematical basis; no new per-expression calculus proofs |
| Shared source-program evaluation | Keep; do not return to 43 expanded derivative programs |
| Compact batch verdicts | Keep; avoid exporting large numerical intermediates |
| Certificate-erasure correctness | Reuse to justify changing hints without changing the function |
| General batch and split-tree soundness | Reuse when moving their hypotheses into computed checks |
| Fixed-scale and mixed-representation invariants | Extend where measurements justify it |
| Ordinary untrusted numerical hint generation | Keep outside the proof boundary; only checked hints affect a theorem |
| Small arithmetic and analytic checkpoints | Keep the short development loop |

The public assessment also records negative or marginal experiments involving GCD-fuel representation, endpoint-product sharing and Hessian-only projection. This proposal does not ask to rerun those unchanged. It likewise does not require porting all of HOL4's translation infrastructure before making progress. [R9, R10]

## 4. The specific architectural gaps

### 4.1 The completed driver repeats preparation for the same formula

`candle_action296_adaptive_forest_prove_one` prepares a source for its parent box, constructs a point plan, prepares final cells, obtains an aggregate proof, extracts source results, and performs live handoff/glue. The sequential driver applies that routine to every original root. [R6]

Box preparation calls `candle_q_dim_analytic_jet_prepare_six_with` with a box-specific square-root callback. That routine reconstructs the expression and derives validity, denotation/source correspondence, compilation and encoded-program theorems. Thus recurring preparation includes real proof work, not just reading new coordinates. [R11, R12]

The grouping work shares this cost across some neighboring roots. It is a valid improvement, but its reuse unit is still a suitable box/group. The more ambitious question is whether the stable source connection can survive arbitrary changes to the numerical certificates.

### 4.2 One particularly small reuse opportunity is visible

`candle_q_dim_taylor_model_point_plan_six` builds its rational programs from the vector variables and source expression. Its body does not consult the current box endpoints or the annotated square-root bounds. Nevertheless, the completed driver calls it per original root. This suggests that the plan can be shared by all boxes of the same source, subject to the existing source-identity checks. It is a hypothesis to test, not a measured speedup claim. [R13]

This is worth one inexpensive experiment because it distinguishes avoidable driver repetition from necessary per-box work. It should not become the main architectural project merely because it is easy.

### 4.3 Numerical certificates are entangled with compiled expression variants

Point variants already avoid a complete repeat of the source proof, which is good. However, changed square-root intervals still produce an altered annotated expression, a compilation theorem obtained by rewriting, and an encoded-program theorem. [R13]

For a fixed function, the desired recurring inputs are coordinates, precision choices and checked hints. Ideally, changing those values would not require rebuilding the logical program and reproving its relationship to the source. A stable program with hint slots, or a generically justified checked patching operation, could preserve the current evaluator while changing this interface.

This is a proposed explanation of a measured cost, not proof that one representation change will remove all preparation.

### 4.4 The computed verdict does not yet discharge every structural premise

The batch definitions separate numerical acceptance from certificate-erasure equality. Full batch acceptance requires both. The adapter supplies the latter through rewriting and then derives the combined acceptance theorem. That separation is sound, but leaves work outside fast computation. [R14, R15]

Similarly, a general tree theorem already turns accepted jobs plus tree well-formedness into a root result. The tree adapter receives a well-formedness theorem; it does not make that obligation disappear. The measured tree experiment made topology plus handoff slower despite improving total restored-process time through a better checkpoint. The report correctly distinguishes those effects. [R9, R16, R17]

The next step is therefore more specific than “prove a general tree theorem”: **provide efficient computed certificates for its structural premises and compose them generically**.

Existing encoding proofs must not simply be deleted. Correctness currently relies on the input being the encoding of a valid logical object. A checker accepting externally prepared bytes needs a proved decoder/validator or an equally strong representation theorem. Counting leaves or comparing an output digest does not establish source identity or domain coverage.

### 4.5 The numerical implementation remains expensive in its own right

The examined mixed checker keeps polynomial work in a fixed-scale representation and can retain selected later operations there. Multiplication, square and nonlinear operations still route through rational machinery in this version. Its source and the instruction profiles explain why adding reflection did not eliminate arithmetic costs. [R9, R18]

This suggests extending the existing proved numerical representation at measured conversion or rational hot spots. It does not justify changing every operation at once or assuming that lower precision wins: any loss in bound quality can increase the number of boxes.

## 5. What to learn from tame graphs and original Flyspeck

The current Isabelle tame-graph source evaluates whole graph predicates in `ArchComp`, then `Completeness` uses the resulting facts to instantiate the previously developed completeness argument. That is the useful analogy: the large recurring task lies within executable predicates, while the mathematical connection is general. It is not a promise that arbitrary reflected numerics will run as fast as graph enumeration. [R19, R20]

There is also an execution distinction. Candle's published compute implementation is an interpreter over a restricted computation representation, using host integers; Isabelle code evaluation can execute generated compiled code. Their execution and trust arrangements are not interchangeable. The Candle paper's large speedups compare against conventional in-logic evaluation, not against optimized native Flyspeck verification or C++. [R21]

Original verified NL already had rounded finite-precision arithmetic, arithmetic caches, untrusted certificate search and adaptive precision. Its main verifier builds the evaluation functions before traversing the certificate. We should preserve or improve those advantages rather than present them as new discoveries. [R7, R5, R22]

Consequently, there are two separate engineering questions: how much ordinary proof construction can be eliminated, and how efficiently the chosen numerical algorithm runs through Candle's evaluator. Both need evidence.

## 6. Proposed destination and proof interface

The schematic target is:

```text
check_nl(stable_program, original_box, certificate) = true
  ==> every point in original_box satisfies the encoded inequality
```

This is a specification sketch, not a theorem already present in this exact form. Either program validity is included in `check_nl`, or it is a single reusable premise established when the formula is prepared. The original HOL formula is connected to the program once per distinct expression through a source-correspondence theorem.

The acceptance condition should account computationally for:

- well-formed instructions, indices and numerical representations;
- box validity and the exact original domain;
- sound numerical enclosures and necessary operator-domain guards;
- consistency of hints with the stable source program;
- coverage by the supplied subdivision structure;
- the relevant leaf verdicts and the combination of their conclusions.

A false verdict may mean insufficient precision or an unsuitable certificate; it need not mean the inequality is false. A malformed certificate must not become an accepted proof.

**The important condition is that these requirements do not reappear as expensive per-node host proof obligations.** A final theorem with an unproved “all leaves valid and tree covers the domain” premise would only relocate the work on paper.

### A concrete representation option to consider

Keep a stable compiled instruction sequence per formula. Assign numerical-hint slots to operations that need them. Each box supplies a compact hint table, its precision parameters and a small subdivision record.

One possible incremental implementation is a pure checked patching function that inserts those hints into the existing instruction format inside the computation. Prove once that patching preserves the represented source and that the existing numerical checker still establishes the required bound. Another option is a directly parameterized evaluator. The worker should choose whichever fits the existing representation proofs better.

This can reuse certificate-erasure lemmas, compiler correctness, numerical soundness and tree composition. It should not require a second calculus library or a fresh symbolic differentiator.

The patch/decoder route must check shapes and permitted changes. Untrusted preparation may choose the hints; it may not change an opcode, variable index or coefficient and still claim to represent the original formula.

### Whole-certificate structure without thousands of intermediate theorems

For the initial strict-inequality case, a certificate can describe ordinary splits and accepted leaves. Child boxes can be derived computationally from the parent and split data, so coverage follows from a generic split theorem rather than individual endpoint-equality proofs.

A batch or subtree can return a compact acceptance fact. Existing generic composition results can then combine a bounded number of such facts. This permits memory limits and later parallelism without reinstating one large host proof at every numerical leaf.

The first pilot need not support all of Flyspeck. Broader NL additionally needs an explicit coverage plan for disjunctions, monotonicity restrictions, convexity steps, references to earlier results and any sharp/non-strict cases. Those extensions must be reflected in the theorem statement and certificate language; success on the current split/pass case does not establish them.

## 7. Suggested experiments before a large implementation commitment

### Experiment A: establish the cost ledger and remove obvious repetition

Use existing small checkpoints and authentic inputs. Reuse the established 32-root set for direct comparison, and add a small selection from later regions that stresses failed whole-box acceptance and extra subdivision. Avoid relying only on the first convenient leaf.

Measure separately:

| Cost | Accounting rule |
| --- | --- |
| Stable libraries and generic proofs | One-time setup |
| Source correspondence and stable compilation | Once per distinct expression |
| Certificate search/hint generation | Separate untrusted preparation cost; report cold and reused totals |
| Encoding and structural checks | Recurring unless genuinely cached |
| The actual `Kernel.compute` invocation | Separate from its proof adapter |
| Final theorem assembly | Include the exact root/domain result |

Count calls to source preparation, point-plan construction and variant compilation. Try hoisting the source-only point plan while preserving the existing validations. This should need no new mathematical theorem. Record both success and remaining bottlenecks; do not mistake that small change for the final architecture.

Run native HOL Light on the same case or authentic subcases on the same machine when practical. The historical 667.7-second result is useful immediately; obtaining a perfect full baseline should not block a cheap discriminating prototype. Existing slow Candle measurements can be reused instead of rerunning all controls from scratch.

### Experiment B: test stable program plus data-only certificates

Before investing in a large proof adaptation, an ordinary untrusted implementation may test the proposed data layout and its numerical outputs on those same inputs. It produces no proof credit. Its purpose is to reveal whether preparation can become small and whether the proposed checker is numerically competitive at all.

Keep the current arithmetic initially, so a representation experiment does not also change bounds. Compare increasing batches, for example 1, 8 and 32 boxes, with stable preparation charged once. Include the size of generated data and repeated traversals, not only elapsed time.

If useful, prove the narrowly needed patch/encoding/source-preservation result and connect the same experiment to `Kernel.compute`. The proof-producing measurement should show that changing boxes and hints no longer triggers source reification and compilation theorem construction per box.

### Experiment C: reflect structural acceptance and return a root theorem

On the same bounded workload, use an encoded certificate whose coverage and source consistency are checked computationally. Reuse the existing tree and erasure mathematics. Obtain the root theorem with a small generic handoff.

Include targeted rejection cases: an invalid hint, a changed program instruction, an omitted branch, an inconsistent box and a malformed encoding. These check the new proof boundary; there is no need to build another broad test framework.

Measure topology/encoding and theorem handoff separately. A successful restructuring that makes these phases slower is useful diagnostic evidence, but is not a speedup result.

### Experiment D: address the measured numerical remainder

Once orchestration is separated, compare numerical checking on identical boxes and precision settings. If rational work dominates, extend the current bounded-scale implementation at the measured hot operations. If evaluator overhead dominates, distinguish that from the cost of the numerical algorithm using a genuinely compiled untrusted implementation of the same calculation where practical.

The already-tested generic ordinary interpreter is not a promising replacement merely because it runs outside `Kernel.compute`. A new comparison is worthwhile only if it isolates a new execution or representation question.

For every numerical change, report both cost per accepted region and total cells needed to cover the original domain. A faster operation with wider enclosures can lose overall.

### Decision before the next full run

The useful evidence is a table comparing native HOL Light, the retained current reflected result and the candidate on matched inputs, including amortized preparation and the final theorem. Then choose whether to:

- integrate the new computational boundary;
- improve its numerical representation further;
- investigate the evaluator/compiler route as a separate, larger project; or
- retain the correct prototype while explicitly revising the performance ambition.

A full 1,061-root replay is appropriate after a coherent candidate demonstrates the desired change on the bounded batch. Small percentage improvements over a slow internal baseline are not sufficient evidence for the thousandfold goal. Equally, a costly reusable setup is acceptable if the measured crossover and expected reuse justify it.

## 8. Parallelization and efficient iteration

Parallelism is important for the full workload, and original Flyspeck explicitly supported many independent verifier jobs. It should be planned alongside the architecture, with total processor time distinguished from wall time. It is not a substitute for removing a large per-case efficiency deficit. [R23]

Independent inequalities, certificate subtrees and untrusted preparation provide natural units. A small scaling experiment can test load balance, repeated preparation, resident memory and final combination. Do not assume linear scaling or derive a whole-NL completion date from this one case.

There is a proof-combination question to settle before advertising fully parallel verified throughput: how do facts established in separate Candle processes become the final accepted result? Use an existing sound theorem/evidence transport route if available. Hash agreement by itself is not a kernel proof, and a final serial replay of every numerical check would defeat much of the wall-time saving. Untrusted parallel certificate generation has no such theorem-import problem because the receiving checker still validates its input.

For development, preserve a stable analytic/checker checkpoint, reuse prepared expression data, and restore disposable copies for candidates. Let ordinary data-layout and numerical experiments run in a small harness without the complete verifier. Re-enter the full environment when the candidate's proof boundary is ready for integration. The existing short restore loop is a useful asset, not something to replace.

The latest recovery exposed an output-descriptor issue: resumed output overwrote a copied log prefix, and the worker subsequently preserved the original evidence and constructed a separate canonical stream. That repair concerns evidence handling, not a numerical-checker failure. For performance reporting, distinguish original and resumed execution epochs; a reconstructed log prefix must not acquire fresh timestamps that are then interpreted as the original elapsed proof time. The already-planned clean schedule replay is the natural source for recurring grouped timings, with discovery/recovery costs reported separately. This does not call for another general logging framework.

## 9. What a useful worker response would contain

Please use your judgment about the best order and proof route. A concise response could cover:

1. Which findings still apply to the current code, with any superseding commits.
2. Whether the source-only point plan and stable source proof can be shared across all boxes of this expression.
3. Which remaining structural premises can be discharged by computation using the existing soundness results.
4. A small matched batch experiment, its expected diagnostic outcome and the work it would save if successful.
5. The route from independently checked batches to the final original inequality theorem.

The desired decision is architectural: whether we can make the recurring workload an efficient verified computation, with an affordable proof interface, rather than continuing to accumulate local adapter optimizations. The existing successful proofs are foundations for that decision.

## Sources and reproducibility

Repository sources below are pinned where available. Function names identify exact code paths; the proposed changes and expected benefits are hypotheses, not measured new results.

- **R1 — Candle captured source formula:** [fixture](https://github.com/JUrban/candle/blob/469166f4e0a56f12eac30977e5f39733381b16cd/candle/cv_compute_analytic_expr_action296_fixture.ml).
- **R2 — Original input:** [azure/ineqs.txt](https://github.com/flyspeck/flyspeck/blob/1ce0353008eba83d3c76ae9a25c3c242e4802d53/azure/ineqs.txt), input 10172. The full quoted target and this input compare equal after whitespace removal.
- **R3 — Historical result:** [original log](https://github.com/flyspeck/flyspeck/blob/1ce0353008eba83d3c76ae9a25c3c242e4802d53/azure/results/urban/out/1/10150/2/10199/stdout#L962-L992).
- **R4 — Current complete sequential report:** [v2.39](https://github.com/JUrban/flyspeck-candle-project/blob/0246c08ea7fded959e46421db08c27aaa0dad605/docs/progress/2026-09-28-v2.39-complete-sequential-action296-proof.md). Latest snapshot: [v2.40](https://github.com/JUrban/flyspeck-candle-project/blob/0246c08ea7fded959e46421db08c27aaa0dad605/docs/progress/2026-09-28-v2.40-action296-root800-recovery-checkpoint.md).
- **R5 — Original preparation and timing:** [m_verifier_main.hl](https://github.com/flyspeck/flyspeck/blob/1ce0353008eba83d3c76ae9a25c3c242e4802d53/formal_ineqs/verifier/m_verifier_main.hl#L524-L592); reporting wrapper [azure/main_verifier.hl](https://github.com/flyspeck/flyspeck/blob/1ce0353008eba83d3c76ae9a25c3c242e4802d53/azure/main_verifier.hl).
- **R6 — Current full-run driver:** [adaptive_forest_prove.ml](https://github.com/JUrban/candle/blob/469166f4e0a56f12eac30977e5f39733381b16cd/candle/cv_compute_analytic_expr_action296_adaptive_forest_prove.ml), especially `prove_one`, `prove_sequential`, and the result record.
- **R7 — Original NL method and performance motivation:** Solovyev and Hales, [Formal Verification of Nonlinear Inequalities with Taylor Interval Approximations](https://arxiv.org/html/1301.1702v1), sections 3–5. This is the 2013 development, not a timing table for the final corpus.
- **R8 — Matched grouping experiment:** [v2.35](https://github.com/JUrban/flyspeck-candle-project/blob/0246c08ea7fded959e46421db08c27aaa0dad605/docs/progress/2026-09-28-v2.35-generated-nonlinear-group-schedules.md).
- **R9 — Existing work and measured limitations:** [v2.24](https://github.com/JUrban/flyspeck-candle-project/blob/0246c08ea7fded959e46421db08c27aaa0dad605/docs/progress/2026-09-27-v2.24-compact-tree-handoff-and-performance-note-assessment.md).
- **R10 — Earlier staging rationale:** [cv_compute feasibility response](https://github.com/JUrban/flyspeck-candle-project/blob/0246c08ea7fded959e46421db08c27aaa0dad605/docs/advice/Candle_cv_compute_feasibility_response.md). Its initial wrapper failures are historical, not asserted to remain current.
- **R11 — Box-dependent source preparation:** [box_certificate_prepare.ml](https://github.com/JUrban/candle/blob/469166f4e0a56f12eac30977e5f39733381b16cd/candle/cv_compute_analytic_expr_box_certificate_prepare.ml).
- **R12 — Source, validity, compilation and encoding proofs:** [analytic_expr_jet_prove.ml](https://github.com/JUrban/candle/blob/469166f4e0a56f12eac30977e5f39733381b16cd/candle/cv_compute_analytic_expr_jet_prove.ml#L88-L143).
- **R13 — Point plan and certificate variants:** [certificate_variant_prepare.ml](https://github.com/JUrban/candle/blob/469166f4e0a56f12eac30977e5f39733381b16cd/candle/cv_compute_analytic_expr_certificate_variant_prepare.ml).
- **R14 — Numerical versus full batch acceptance:** [fixed_algebraic_batch.ml](https://github.com/JUrban/candle/blob/469166f4e0a56f12eac30977e5f39733381b16cd/candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_batch.ml).
- **R15 — Computation and host erasure proof:** [fixed_algebraic_batch_prove.ml](https://github.com/JUrban/candle/blob/469166f4e0a56f12eac30977e5f39733381b16cd/candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_batch_prove.ml).
- **R16 — Existing general tree theorem:** [fixed_algebraic_tree.ml](https://github.com/JUrban/candle/blob/469166f4e0a56f12eac30977e5f39733381b16cd/candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_tree.ml).
- **R17 — Tree adapter's separate well-formedness premise:** [fixed_algebraic_tree_prove.ml](https://github.com/JUrban/candle/blob/469166f4e0a56f12eac30977e5f39733381b16cd/candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_tree_prove.ml).
- **R18 — Mixed fixed/rational operations:** [fixed_algebraic_compute.ml](https://github.com/JUrban/candle/blob/469166f4e0a56f12eac30977e5f39733381b16cd/candle/cv_compute_analytic_expr_taylor_model_program_fixed_algebraic_compute.ml), especially the item operations and program-step definition.
- **R19 — Tame-graph computational predicates:** [ArchComp.thy](https://github.com/isabelle-prover/mirror-afp-devel/blob/master/thys/Flyspeck-Tame/Computation/ArchComp.thy), inspected 28 September 2026.
- **R20 — Tame-graph final composition:** [Completeness.thy](https://github.com/isabelle-prover/mirror-afp-devel/blob/master/thys/Flyspeck-Tame/Computation/Completeness.thy) and [Relative_Completeness](https://isa-afp.org/browser_info/current/AFP/Flyspeck-Tame/Relative_Completeness.html), inspected 28 September 2026.
- **R21 — Evaluator architecture and comparison scope:** Abrahamsson et al., [Fast, Verified Computation for HOL ITPs](https://doi.org/10.1007/s10817-025-09719-8), especially sections 1–2, 11–13.
- **R22 — Original rounded arithmetic implementation:** [arith_float.hl](https://github.com/flyspeck/flyspeck/blob/1ce0353008eba83d3c76ae9a25c3c242e4802d53/formal_ineqs/arith/arith_float.hl).
- **R23 — Original parallel verification workflow:** [azure/README.md](https://github.com/flyspeck/flyspeck/blob/1ce0353008eba83d3c76ae9a25c3c242e4802d53/azure/README.md).
- **R24 — Latest pushed operational update:** [v2.41](https://github.com/JUrban/flyspeck-candle-project/blob/5b6ececda5fc59299371e1a67cb2e7c56380e610/docs/progress/2026-09-28-v2.41-easy3-complete-and-action296-root1000-checkpoint.md). The project comparison from `0246c08` to `5b6ecec` contains this one added report.

Full-run percentage source: user-supplied `Pasted markdown(20260928-092800).md`, worker messages 702121–702149. This attribution is distinct from independent inspection of the public 32-root timings.

Latest operational and assessment source: user-supplied `Pasted markdown(20260928-131445).md`, especially messages 704270–704304 (timeout/recovery), 704374 (assessment of the September 25 note), 704401–704479 (descriptor/log repair), and 704877 (latest frontier). These messages are newer than the pushed v2.41 report; no later completion is assumed.
