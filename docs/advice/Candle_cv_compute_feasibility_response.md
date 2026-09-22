# Candle `cv_compute` feasibility response

Date: 2026-09-19 UTC  
Status: assessment and DEVELOPMENT / NON-RELEASE probes; no Flyspeck speedup or release claim

## Executive conclusion

Bringing useful parts of HOL4's `cv_trans`/`cv_eval` approach to Candle is
technically feasible, and the trusted part need not grow: Candle already contains
a verified first-order computation primitive that returns kernel theorems.  The
missing work is the proof-producing translation, representation, and integration
layer outside the kernel.

It is not yet justified to port the general HOL4 translator.  There are two
reasons:

1. The computation wrapper in the exact current Candle source is not compatible
   with the initialization contract of the verified primitive in the exact
   development executable.  A fresh-base call currently fails closed with
   `Kernel.compute: wrong theorems provided for initialization`.  The mismatch is
   localized to the `Cexp_if` equation for pair-valued conditions and a narrow
   correction already exists on another Candle branch, but it still needs to be
   adopted and independently tested on the active branch.
2. The expensive Flyspeck LP and nonlinear paths are mostly ML programs that
   construct theorems.  `cv_trans` translates logical function definitions, not
   ML tactics.  A translator port by itself therefore would not accelerate those
   paths.  We first need to isolate a substantial logical computation or build a
   reflected checker with a Candle proof of correctness.

The recommended decision is therefore:

- repair and smoke-test the existing primitive as a bounded Stage 0;
- build one manually encoded, proof-producing prototype before attempting a
  general translator;
- benchmark inclusive cost on real Flyspeck inputs; and
- port a broader translator only if that benchmark shows material end-to-end
  benefit.

This work can remain a side lane while the current cumulative LP run proceeds.
The assessment probes used separate fresh states and did not alter or interrupt
that run.

## 1. What exists in the exact Candle configuration

### Verified primitive and current exposure

There are two distinct facilities whose similar names should not be conflated:

- Root `compute.ml`, loaded by `hol_lib.ml`, is HOL Light's conventional
  rewrite/conversion facility and exposes `Compute.EVAL_CONV`.
- `candle/compute.ml` defines the untyped computation value type
  `cval = Cexp_num num | Cexp_pair cval cval`, characteristic equations for
  arithmetic, pairs, equality and conditionals, and a wrapper around
  `Kernel.compute`.  Normal `hol.ml`/`hol_lib.ml` startup does not load this file.

The active direct-Flyspeck source is Candle
`f13946ab560f1eb0a653a48d7b499d47623e8a35`.  The development runtime used by
the current direct work has SHA-256
`3aaa248c0d5d6c96fa8e36445d1a945a751f0cf11a8b734a6142e9fab1088b2b` and was
built from CakeML `cc36ecadde2d13d377e26ccb9610a450c477f737`, Candle
`1109fdfcf3c754e80d3e14bce6cb0caad6977bb9`, and HOL4
`a390cbabd3a4521bab4ee20281e3e42933a8a3ae`.  It is explicitly a non-promotable
development binary.

The primitive is compiled into that executable, but it is **not usable through
the current wrapper yet**.  Fresh-base probe `v244` loaded the unchanged wrapper
successfully, exposed `compute`, and then rejected even the small call
`Cexp_add (Cexp_num 123) (Cexp_num 456)` at initialization.  The exact mismatch
is:

- active `candle/compute.ml`: `Cexp_if (Cexp_pair ...) p q = p`;
- compiled verified kernel's required theorem: `Cexp_if (Cexp_pair ...) p q = q`.

CakeML commit `1af98e502` changed the verified contract to the latter equation.
Candle commit `b55243eb7` contains the corresponding wrapper correction, but is
not an ancestor of the active branch.  It is a strong lead, not yet active-branch
evidence.  Stage 0 should apply the minimal semantic correction on an isolated
branch, compare every initialization theorem and its order against
`compute_thms`, and require a fresh-base theorem-producing smoke test plus
regressions.  The kernel correctly fails closed today.

Evidence for the authoritative fresh-base probe:

- directory: `/project/flyspeck-candle-runs/v244-cv-compute-fresh-base-v66-001`;
- log: 1,273,453 bytes, SHA-256
  `7f592f6619da40b716efe20c06685f30d36feb59e93d1c6327c65b0edb31a631`;
- wrapper source SHA-256:
  `cf327c067fa7cb127ed14bb5909cbbecb9f9ac48b13f59d576c9ca2230cbb6d9`.

Two earlier checkpoint-based probes are only diagnostic: the unchanged wrapper
first met a relocated-loader cache identity guard (`v242`), and a run-local
control then met a late-state `CHOOSE_TAC` failure (`v243`).  Neither is used to
judge primitive semantics; the clean fresh-base probe is authoritative.

### What HOL4 supplies

The local HOL4 tree has a mature implementation under
`src/num/theories/cv_compute/`.  Its layers are approximately:

- the small `cv_computeLib` bridge to the kernel primitive;
- `cv_rep` representation relations and correctness infrastructure;
- `cv_type` support for deriving conversions for datatypes;
- `cv_trans` function translation, recursion, precondition and termination
  machinery; and
- `cv_eval`-style user automation and preprocessing.

HOL4 supports useful families including booleans, naturals, characters,
integers, rationals, words, options, pairs, sums and lists.  Those capabilities
are relevant design material, but the SML implementation cannot simply be
copied into Candle.  It depends heavily on HOL4-specific modules and databases,
including `HolKernel`, `DefnBase`, `TypeBase`, `Theory`, `ThmSetData`, parsing,
and total-definition machinery.  Candle is a HOL Light environment with
different theorem APIs, naming, definition packages, and numeral conventions.

The reusable portion is therefore:

- the architecture and proof decomposition;
- object-logic definitions and theorem statements that can be translated into
  HOL Light form;
- representation choices and many proof ideas; and
- the benchmark and correctness methodology.

The non-reusable portion is most of the automation plumbing.  A first useful
version needs Candle/HOL Light-native code for theorem discovery, equation
registration, datatype representation, recursive call analysis, termination
and precondition obligations, and theorem synthesis.

After the Stage 0 contract correction, all of this can remain outside the
verified kernel.  The automation may fail, or produce a candidate equation, but
only the existing kernel primitive and ordinary Candle inference rules produce
the accepted theorem.

## 2. Real Flyspeck costs and plausible targets

### What is measured

The present measurements are inclusive and deliberately do not pretend to be a
phase breakdown:

| Workload | Observed Candle result | Inclusive observation |
|---|---:|---:|
| Focused `hard_2.dat` | 17/17 terminal proofs | about 14m28s, including checkpoint restore and source closure |
| Focused `hard_10.dat` | 58/58 terminal proofs over 71 split nodes | about 24m, including restore and source closure |
| Current cumulative `hard_1.dat` | 272/2,899 terminal numbers emitted at the assessment sample | about 6,838s elapsed; about 17.2 GiB RSS; one CPU |

The pinned 39-shard LP corpus contains 19,715 certificates, 43,078 terminal
nodes, 24,656 split nodes, and 3,016,420 terminal constraint records.  These
counts are workload metadata, not proof completion evidence.

Current instrumentation does **not** separately measure Marshal decoding,
logical arithmetic, conversion work, theorem construction, frontend work, or
garbage collection.  Consequently no percentage speedup can yet be forecast
responsibly.

### What can and cannot be translated

The current LP routine `prove_flyspeck_lp_step1` is an ML theorem-construction
program.  It calls operations such as `INST`, `TRANS`, `AP_TERM`,
`MY_PROVE_HYP`, conversions, `add_step'`, and `add_cancel_step`.  It is not an
object-logic function and is not a direct `cv_trans` input.  The nonlinear path
similarly combines serialized theorem leaves with ML-side reconstruction; its
23,242-parameter and 7,479-leaf scales identify possible costs but do not make
the tactic itself translatable.

Plausible logical targets are:

1. **Technical integration target:** `compute_all` in
   `formal_lp/hypermap/computations/list_hypermap_computations.hl`.  It evaluates
   ordinary list/pair/natural-number hypermap functions such as `list_of_faces`,
   `list_of_darts`, and `good_list` using handwritten conversions.  This is a
   good low-risk test of representations and theorem handoff, although it is not
   yet known to dominate runtime.
2. **Performance target:** a pure exact-arithmetic component of one LP terminal,
   such as checking a serialized linear combination and its rational/integer
   side conditions.  This requires factoring the data computation from the ML
   proof assembly and proving that a successful logical check implies the exact
   proposition consumed by the existing verifier.
3. **Larger target:** a reflected LP or interval/nonlinear certificate checker.
   This could amortize theorem construction and plausibly deliver the largest
   gain, but only after a once-proved checker-correctness theorem.  It is a
   substantive verification project, not a consequence of merely porting
   `cv_trans`.

Host file I/O, Marshal decoding, source parsing, namespace/frontend work, and
the unavoidable final theorem-interface work remain unaffected.  Faster
arithmetic conversions alone may help locally, but a large gain probably needs
coarser reflected checking so that the primitive evaluates many arithmetic
steps behind one correctness theorem.

## 3. Smallest useful prototype

The cheapest evidence-producing sequence is:

### Stage 0: make the existing primitive real

1. Adopt only the pair-condition correction from Candle `b55243eb7` on an
   isolated active-branch descendant.
2. Mechanically compare the complete ordered initialization-theorem list with
   the CakeML `compute_thms` contract; do not stop after the first match.
3. From a fresh `hol.ml` state, load `candle/compute.ml` and obtain kernel
   theorems for arithmetic, conditional, equality and nested-pair examples.
4. Add a negative/order-contract regression and normal HOL/Great100 smoke tests.

Estimated effort: **1--3 engineering days**, including active-branch integration
and tests.  The code change may be tiny; the estimate is for trustworthy
validation.  This is an estimate, not a commitment.

### Stage 1: manual representation and real theorem handoff

Manually define `to_cv`/`from_cv` encodings and round-trip/representation
theorems for the minimum types used by `compute_all`: booleans, naturals, pairs,
and lists.  Hand-author computation equations for a small closed slice of
`list_of_faces`/`list_of_darts`/`good_list`, prove their correspondence to the
ordinary definitions, and return the same ordinary HOL theorem expected by the
existing call site.

This avoids building general translation automation before the primitive,
representations, and theorem handoff have been exercised together.  Estimated
effort: **1--2 weeks**, with roughly a factor-of-two uncertainty due to
termination equations and the exact dependency closure.

### Stage 2: performance-bearing LP leaf

Profile one terminal and factor one pure exact-arithmetic predicate over its
actual certificate data.  Encode it manually, prove the checker lemma, and run
it behind the existing verifier interface.  Only this stage can answer whether
the idea reduces meaningful LP time.  A target-specific reflected checker is
roughly **3--8 weeks** if the logical predicate is already cleanly separable.

A general, ergonomic Candle equivalent of HOL4's datatype and recursive-function
translator is more likely **2--4 person-months**, potentially longer if totality,
preconditions, higher-order preprocessing, and a broad standard-library
ecosystem are required.  It should not be authorized from paper benchmarks
alone.

## 4. How the accelerated path still produces the required theorem

The sound path is:

```text
authenticated Flyspeck input
  -> ordinary HOL value/term
  -> proved representation theorem into cval
  -> verified Kernel.compute evaluation theorem
  -> proved from_cv/to_cv or checker-correctness theorem
  -> ordinary HOL theorem with the existing conclusion and hypotheses
  -> existing Flyspeck conversion/verifier interface
```

For a translated function `f`, the key theorem has the shape “the cval program
represents `f` on represented inputs”, with explicit preconditions where the
logical function is partial.  Datatype encodings need round-trip or relational
theorems.  Recursive functions need proved computation equations and whatever
termination theorem the ordinary HOL definition requires.

For a reflected checker, prove once in Candle that `check certificate input =
true` implies the precise Flyspeck proposition.  Each use then consists of:

1. a theorem connecting authenticated input data to its logical encoding;
2. a kernel-compute theorem reducing the checker to true; and
3. an application of the checker-correctness theorem.

No result from a separate HOL4 session, native OCaml evaluator, or external
worker is assumed.  Such systems may generate inputs or provide an oracle for
testing, but Candle must authenticate the bytes and construct the theorem.  The
accelerated path must preserve the original conclusion, hypotheses, and allowed
axioms; equivalence checks should fingerprint all three.

The least disruptive integration is a new conversion behind the existing
conversion/verifier API, with a conservative fallback to the current proof path
during development.  Release use should fail closed if representation,
precondition, or input authentication cannot be proved.

## 5. Benchmark and decision gates

### Benchmark workloads

Use fresh copies of a clean predecessor state for every failed experiment, as
with the existing Flyspeck checkpoint discipline.  A useful ladder is:

1. one actual `compute_all` call, to validate theorem equivalence and integration;
2. one small, one median, and one heavy LP-terminal arithmetic component;
3. all 17 terminals of the real `hard_2.dat` certificate; and
4. only after success, a larger/deeper certificate such as `hard_10.dat`.

The current full action-184 run should not be restarted merely for this work.
Use the focused state and reserve a fresh cumulative replay for a coherent,
successful integration batch.

### Measurements

Compare old and new paths on the same runtime, source identities, checkpoint,
input hashes and theorem target.  Record separately:

- restore and source-load time;
- input decoding and reification;
- translation/setup (distinguishing reusable from per-call work);
- kernel evaluation;
- theorem reconstruction and interface conversion;
- total wall and CPU time;
- peak RSS and, where available, allocation/GC statistics; and
- conclusion, hypotheses and axiom fingerprints of the resulting theorem.

Use repeated warm in-process calls to expose reusable setup, plus repeated fresh
states to capture honest end-to-end cost.  Instrumentation should first measure
the existing path's phase split; otherwise optimizing arithmetic could target a
minor fraction of the runtime.

### Suggested gates

- **Proceed broadly:** at least 3x improvement for the targeted real component
  and a credible projection of at least 25% or two hours saved on a material
  cumulative boundary, with no theorem-interface or memory regression.
- **Narrow the scope:** strong local acceleration but less than 10% projected
  end-to-end gain; retain it only for the few dominating logical checks.
- **Defer:** less than 2x inclusive improvement, theorem construction remains the
  dominant cost, or representation/setup memory offsets the evaluator gain.

These are engineering decision thresholds, not claims about results already
observed.

Process-level parallelism is the nearer-term way to reduce wall time for
independent certificates, but it does not reduce total CPU and requires a sound
theorem-result combination path.  The current single worker's roughly 17.2 GiB
RSS also limits useful fan-out.  The two approaches are complementary: shard
independent inputs across a bounded number of processes, and make each process's
logical checker cheaper.  Raw booleans or unauthenticated theorems from workers
are not an acceptable merge interface.

## Recommended next decision

Proceed with Stage 0 and one manual `compute_all` theorem-handoff prototype when
that does not impede the active Flyspeck run.  In parallel, add phase timing to
one focused LP terminal.  Do **not** begin the general `cv_trans` port until:

- the fresh-base primitive smoke test passes on the active bytes;
- a real ordinary-Flyspeck theorem is produced through the cval path; and
- inclusive profiling identifies a sufficiently large logical cost center.

If those conditions hold, the next prototype should be a narrowly reflected
exact-linear-arithmetic leaf checker.  Generalize datatype/function translation
only after that checker meets the benchmark gates.

## Sources and evidence

- [Fast, Verified Computation for HOL ITPs](https://research.chalmers.se/publication/545343/file/545343_Fulltext.pdf)
- [HOL4 release history](https://github.com/HOL-Theorem-Prover/HOL/releases)
- [HOL4 `cv_compute` source at the paper-era revision](https://github.com/HOL-Theorem-Prover/HOL/tree/718d989/src/num/theories/cv_compute)
- [CakeML/Candle verified compute sources](https://github.com/CakeML/cakeml/tree/v2523/candle/prover/compute)
- local HOL4 implementation: `/project/repos/HOL/src/num/theories/cv_compute`
- active wrapper: `/project/worktrees/candle-action165-invf-v61/candle/compute.ml`
- compiled kernel contract:
  `/project/worktrees/cakeml-flyspeck-frontend-batch-v13/candle/prover/compute/computeScript.sml`
- LP workload evidence:
  `/project/flyspeck-candle-project/docs/progress/2026-09-17-v1.5-real-lp-certificate-probe.md`

The paper's large speedups for pure logical evaluation establish plausibility,
not a Flyspeck forecast.  The unresolved empirical question is how much of the
observed Flyspeck wall time can be moved behind one coarse, proved logical
checker rather than remaining in decoding and fine-grained theorem assembly.

## 2026-09-22 implementation addendum

The staged work has now passed the feasibility boundary and is an active
development project.  The repaired computation wrapper passes in the late
Flyspeck state, proof-producing exact arithmetic and staged native-float
prototypes preserve assumption-free HOL theorem interfaces, and the first real
LP-terminal phase split is complete.  All results in this addendum remain
**DEVELOPMENT / NON-RELEASE**.

### Real LP terminal split

The profiled target was terminal 15 of the real `hard_2.dat` certificate.  It
used 402 constraint rows, 282 selected auxiliary rows, 424 variables, and
returned a contradiction theorem with 106 hypotheses.  The legacy complete
terminal took 14.05 CPU seconds.  The first dense reflected implementation took
256.69 CPU seconds, explaining the previously observed 16.48x slowdown.

Within the reflected implementation:

| Phase | CPU seconds | Share of reflected total |
|---|---:|---:|
| source normalization and variable discovery | 0.97 | 0.4% |
| dense source-number conversion and row reification | 142.09 | 55.4% |
| pre-compute proof preparation | 24.22 | 9.4% |
| `Kernel.compute` | 80.28 | 31.3% |
| theorem reconstruction | 9.03 | 3.5% |
| publication plus final contradiction handoff | 0.10 | <0.1% |

Thus approximately 69% is surrounding representation/proof work and 31% is
verified evaluation.  This materially changes the LP plan: merely tuning the
evaluator cannot make the current dense adapter competitive.  The next target
is a sparse, reusable source encoding plus a complete numerical-certificate
verdict and one general soundness theorem.  Source-to-encoding correspondence
must still be proved, but immutable row preparation should be amortized across
terminals and intermediate arithmetic theorems should not be reconstructed.
The encoded fold itself also needs improvement because 80.28 seconds is not a
negligible residual.

The evidence is preserved under
`/project/flyspeck-candle-runs/cv-lp-phase-hard2-terminal15-v3`.  Its
`candle.log` SHA-256 is
`3b59a533371208960c05ce9757f52b2e088add650487928def64f9ab3053cb8b`;
its `profile.json` SHA-256 is
`7c4a79af13e3868305230a1305cb6d6aeafc4e7abb1d8b8e917569f7ac21ffa5`.

### Nonlinear one-shot checker direction

Candle now has a generic one-shot soundness theorem for a complete staged
nonnegative polynomial plan.  A separate verified validity computation checks
the untrusted host plan, `Kernel.compute` evaluates the plan, and the generic
theorem connects the symbolic source polynomial directly to the computed
bound.  This is the intended coarse-verdict shape: host planning is not trusted,
and per-factor arithmetic bounds need not be reconstructed after evaluation.

The Flyspeck-side adapter has now passed exact theorem-interface comparison on
the authenticated six-monomial Taylor fixture and on the 21-monomial/78-factor
Hessian fixture.  In one checkpoint-isolated comparison process, the two
legacy calls used 17.85 CPU seconds while the two coarse reflected calls used
0.15 CPU seconds, a 119x aggregate improvement.  The reflected Hessian call
accounted for approximately 0.11 seconds (0.02 source planning, 0.03
representation proof, less than 0.01 measured evaluator time, and 0.06 theorem
handoff), versus approximately 15.91 seconds in the earlier legacy phase
profile, about a 145x improvement for that call.

This validates the one-verdict architecture for the isolated numerical
polynomial workload; it does not yet measure a complete nonlinear leaf.  The
real nonlinear closure reload is proceeding independently, after which the
same architecture must be exercised through the exact leaf and partition
reconstruction interfaces.  The passing profile is preserved at
`/project/flyspeck-candle-runs/cv-staged-reflected-phase-profile-v1`; its log
SHA-256 is
`7bce7cbfc464275a2d5b92fe0b9bd8214dd8e42f84d00367b3dafae319b21e3d`.

### LP reuse and coarse-verdict follow-up

An exact-basis reification cache has now been measured on the same real
`hard_2.dat` terminal 15. Replacing the first association-list prototype with
exact-key hash tables reduced the warm source/number conversion phase from
76.29 to 60.44 CPU seconds. The warm reflected terminal took 183.30 seconds:
60.44 conversion, 25.14 proof preparation, 85.20 `Kernel.compute`, 11.38
theorem reconstruction, and about 0.10 publication. Relative to the original
uncached 256.69-second reflected terminal, exact reuse saves 73.39 seconds
(28.6%), but the result is still about 11.4x the colocated 16.08-second legacy
terminal. Caching is therefore useful preparation, not the final LP design.

The complete sparse numerical-verdict core is now proved and tested on an
isolated Candle branch. It encodes rows as sorted `(variable-index,
signed-integer)` maps, merges and scales all weighted rows inside
`Kernel.compute`, checks complete coefficient cancellation and a negative rhs,
and returns only a one-bit infeasibility verdict. Assumption-free theorems prove
representation correctness for insert, add, scale, accumulation, fold, zero
checking, and the complete verdict. Both a fresh `hol.ml` test and a
checkpoint-isolated test pass. This is the intended arithmetic core for
avoiding reconstruction of intermediate arithmetic proofs.

The remaining proof-critical LP step is explicit: connect authenticated
Flyspeck source inequalities and their sparse row encodings to one general
real soundness theorem, then measure the complete source conversion,
`Kernel.compute`, and theorem handoff on terminal 15. Until that bridge is
proved, the sparse result is DEVELOPMENT / NON-RELEASE and is not substituted
for the existing checker.

Evidence:

- hashed cache run:
  `/project/flyspeck-candle-runs/cv-lp-cache-hard2-terminal15-v2`;
- cache `profile.json` SHA-256:
  `16029536f8eb71114bf35278077c25e45a18f8fef397d473419c13adbfb7e754`;
- cache implementation commit: `71cd644d08571cf4406c85e8ae74551c244434e6`;
- sparse verdict implementation commit:
  `110a44bfda946f5fcc0260ba73b71bcefc75d608`;
- accepted sparse checkpoint log SHA-256:
  `5120310c23f16c146bf19d8aa958a96226cb18972c13585e42cd07218811efd1`.

### Real sparse bridge result and revised LP direction

The remaining source bridge is now implemented and has passed on the unchanged
real `hard_2.dat` terminal 15. It proves all 684 authenticated source rows
denote their sparse encodings, calls `Kernel.compute` once for the complete
infeasibility verdict, and invokes one generic soundness theorem to derive the
legacy contradiction. Successful runs match the legacy conclusion, hypotheses,
theorem digest, and axiom set exactly.

The initial bridge exposed why inclusive measurement matters. Its sparse
evaluator took only 9.27 seconds, versus 85.20 seconds for the earlier dense
evaluator, and final theorem handoff was effectively zero. However, explicit
construction and expansion of `ALL (MAP ...)` over 684 rows took 111.81
seconds, making the first total 191.14 seconds or 12.21x the colocated legacy
terminal.

Replacing that expansion with direct `ALL` construction and one proved
`ALL_MAP` equivalence reduced proof preparation to 4.46 seconds and total time
to 84.71 seconds. A basis-scoped cache of validated `EL_CONV` theorems then
reduced source conversion from 69.66 to 54.21 seconds. The current complete
split is:

| Phase | Wall seconds |
|---|---:|
| colocated legacy terminal | 16.93 |
| source normalization / discovery | 0.81 |
| source/number conversion | 54.21 |
| source-row proof preparation | 5.88 |
| complete sparse `Kernel.compute` verdict | 8.66 |
| generic soundness handoff | 0.56 |
| sparse complete terminal | 70.12 |

This is a 2.61x improvement over the earlier 183.30-second warm dense path and
a 3.66x improvement over the original 256.69-second dense path, but remains
4.14x slower than legacy. The numerical checker and one-theorem handoff are no
longer the obstacle. Repeated whole-basis traversal while proving each sparse
row/source correspondence now consumes 77% of total sparse time.

The LP plan should therefore retain the sparse complete-verdict evaluator and
generic soundness theorem, but replace depth normalization with a structural
row-correspondence theorem builder using once-proved basis selectors. Reusable
immutable row preparation should then be measured across terminals and
certificates. Additional evaluator tuning or another cache layer is lower
priority until that source bridge is made sublinear in the full basis size per
row.

Full measurements, evidence hashes, late-state compatibility findings, and
the nonlinear closure status are recorded in
`docs/progress/2026-09-22-v1.30-real-lp-sparse-verdict.md`.

## 2026-09-22 addendum: structural preparation and real batch reuse

The structural source-row builder, finer conversion profile, complete
17-terminal inventory, and first real shared-preparation batch are complete.
The main new result is that reuse is both safe and material, but is not yet
sufficient for an overall win.

On real `hard_2.dat` terminal 15, selector theorem preparation costs 11.01
seconds and the remaining 684-row reconstruction costs 52.91 seconds. Reusing
exact integer theorems produced 2,043 hits and only 74 misses but barely changed
the total, so integer encoding is not the dominant surrounding cost. Checking
and indexing the 424-variable basis once reduced row reconstruction to 45.61
seconds and the complete sparse terminal to 72.80 seconds, versus 16.80 seconds
legacy.

The 17-terminal inventory found that every terminal has a distinct full
variable basis, but normalized source inequalities overlap substantially.
Terminals 8 and 10 share 469 exact source rows. A checked 502-variable union
context reused 470 exact LHS denotation theorems on terminal 10 and reduced its
row phase from the cold terminal's 63.44 seconds to 26.85 seconds. The complete
two-terminal computed batch took 160.06 seconds versus 49.68 seconds legacy,
or 3.22x slower. Both terminal theorems matched legacy exactly.

This makes the next design boundary concrete. External code may construct an
untrusted canonical basis, deduplicated sparse source-row table, and terminal
index/multiplier plans. Candle should verify the master table once against the
authenticated source theorems, retain the exact denotation theorems, and check
terminal selection through a general soundness interface. Numerical plans and
the final `Kernel.compute` verdict remain per-terminal. Care is required not to
import assumptions from master rows unused by a terminal.

Detailed timings, trust-boundary analysis, evidence hashes, and commits are in
`docs/progress/2026-09-22-v1.31-lp-shared-preparation-batch.md`.

## 2026-09-22 addendum: indexed master plans and steady-state LP wins

The proposed external-plan/reusable-verification split now has a proof-producing
prototype. A deduplicated master table is verified once against exact source
conclusions. Untrusted terminal plans name master rows by integer index; Candle
requires the indexed source conclusion to match the supplied terminal theorem
exactly. Master entries carry hypothesis-free denotation theorems generalized
over the certificate weight, while terminal assumptions and multipliers remain
fresh.

On real `hard_2.dat` terminals 8 and 10, post-preparation computed verification
now beats the colocated legacy checker: 20.22 versus 20.93 seconds on terminal
8 and 19.23 versus 21.54 seconds on terminal 10. Both final theorem interfaces
match legacy exactly. Indexed row denotation fell to 1.12 and 0.76 seconds;
the remaining recurring source-proof cost is dominated by 5.13 and 5.38
seconds of `ALL` list construction.

Cold preparation is not yet competitive. Source-plan reconstruction, the
502-variable shared context, and verification of 1,017 master rows cost 117.28
seconds before terminal proofs. The complete two-terminal computed batch took
156.78 seconds versus 52.08 seconds legacy. This is therefore a genuine
steady-state terminal speedup, not yet a total cold-run speedup.

A generic-rule rewrite was also measured and rejected: despite preserving exact
theorems, repeated generic `MATCH_MP` over the growing `ALL` tail more than
doubled terminal time. The faster rewrite-based constructors were restored.

Detailed phases, the negative result, trust boundary, evidence hashes, and
next targets are recorded in
`docs/progress/2026-09-22-v1.32-lp-indexed-master-steady-state.md`.

## 2026-09-22 addendum: preparation trust split and lighter NL loop

The external-preparation boundary has now been measured rather than only
designed. External code may supply canonical variable indices, deduplicated
sparse encodings, and terminal plans as untrusted data. Candle checks each
master encoding against the exact source theorem, proves its reusable
weight-general denotation, then checks every terminal index/source pair before
the complete numerical verdict. On the real terminal-8/10 master,
deduplication took only 0.31 seconds while authenticated reusable row theorems
took 86.31 seconds. External preprocessing alone therefore does not solve cold
cost; a proved computed table-correspondence boundary is the material next
target.

A one-shot `ALL` expansion and a two-pass master-proof schedule were both
tested and rejected. The former made row-list construction about ten times
slower; the latter increased cold master time by retaining too many
intermediate proof objects. The fast interleaved schedule was restored.

The nonlinear arithmetic/Taylor experiment loop now uses a fresh-copy restore
from the existing post-Taylor checkpoint. A real certificate endpoint fixture
reproduced its exact assumption-free theorem in 14.23 seconds end-to-end,
versus 155.46 seconds from the shallower checkpoint, while the calculation
remained 0.58 CPU seconds. This state is suitable for representation,
whole-calculation, and handoff experiments; complete leaf and partition claims
remain gated by the full nonlinear closure.

Implementation, timings, evidence hashes, and limitations are in
`docs/progress/2026-09-22-v1.33-lp-preparation-and-light-nl-harness.md`.

## 2026-09-22 addendum: disposable NL experiments and clean closure boundary

The lightweight nonlinear separation is now the default development loop.
Exact inputs captured from native HOL Light or an archived certificate are
treated as untrusted fixture data and run through a fresh copy of the stable
post-Taylor checkpoint. This supports number-representation, whole arithmetic
plan, `Kernel.compute`, and theorem-handoff measurements without loading the
complete verifier. A real endpoint fixture already demonstrates a 14.23-second
end-to-end edit loop. The full closure is reserved for capturing genuine leaf
payloads and for fresh integration confirmation of coherent candidates.

The previous full closure load completed its expensive segmented prerequisites
but exposed a frontend grouping failure in `m_taylor.hl`. A faithful minimized
probe and four-pattern positive batch localized it to generated string names
inside `mk_var` tuple arguments. The minimal two-file repair is now isolated on
top of the previously authenticated Flyspeck source, and a new 90-node closure
bundle has been generated from committed source identities. The corrected v12
load is running; on success its checkpoint will become the clean predecessor
for genuine leaf experiments.

Detailed failure preservation, source and controller commits, receipt hashes,
and validation scope are recorded in
`docs/progress/2026-09-22-v1.34-light-nl-loop-and-closure-restart.md`.

## 2026-09-22 addendum: genuine first-leaf predecessor boundary

The full-closure development boundary has been moved three source nodes later.
A closure-only snapshot cannot safely add `prove_by_refinement`, `Definitions`,
and `Break_case` after Candle's authenticated loader tables have been sealed.
The replacement controller therefore authenticates and loads those exact
support modules and binds the exact real target before checkpointing, while
still stopping before reconstruction, certificate search, Taylor construction,
or proof. All 50 focused tests pass, and the active input is tied to committed
Candle and Flyspeck heads with 93 authenticated source nodes.

A second reusable tier is prepared for the stable reflected Taylor/split
adapters. It will be built from one fresh predecessor restore and will stop
immediately before experimental target work. The first genuine-leaf capture
then separates reconstruction, search, adaptive validation, Taylor theorem,
native leaf proof, reflected planning, `Kernel.compute`, and theorem handoff,
and emits the exact derivative/Hessian inputs as untrusted reusable fixtures.
This makes the expensive closure and adapter costs one-time development costs
while preserving fresh-state end-to-end confirmation for coherent candidates.

Implementation, hashes, safety boundary, and current direct-run status are in
`docs/progress/2026-09-22-v1.35-first-leaf-predecessor-checkpoint.md`.

## 2026-09-22 addendum: measured LP reuse break-even

Replacing the nested generic sparse-row implication matching with direct
kernel congruence was repeated twice on real `hard_2.dat` terminals 8 and 10.
It preserved exact theorem identities and all hypothesis/axiom gates. The two
computed terminal proofs average 38.93 seconds, versus 48.70 seconds in the
control, while the reusable master-plus-selector preparation rises by 11.83
seconds. The measured break-even is therefore three terminals. This is a
useful many-certificate optimization, not a cold single-terminal win.

The nonlinear development split remains intentionally small: genuine first
leaf numerical terms are captured once from the full authenticated
predecessor and then treated as untrusted fixtures by the existing 14.23-second
fresh-copy arithmetic harness. Full closure restores are reserved for capture
and coherent end-to-end confirmation. Details and evidence hashes are in
`docs/progress/2026-09-22-v1.36-lp-reuse-break-even-and-nl-fixture-loop.md`.

## 2026-09-22 correction: five-terminal LP evidence and list correspondence

The preceding three-terminal break-even statement is withdrawn. It was an
extrapolation from two terminals and did not replicate on the exact
five-terminal family from `hard_2.dat`. With terminals 8--12, the original
direct-congruence prototype spent 99.26 seconds in the five computed terminal
proofs versus 103.30 seconds in the corresponding legacy terminal phases. A
fresh controlled run spent 97.69 seconds computed versus 94.44 seconds legacy.
The change of sign is consistent with run-scale allocation/GC variation and
does not support a dependable steady-state terminal advantage.

A new proof architecture does produce a real structural improvement. It
proves once that a recursively decoded sparse entry list has the same `lin_f`
denotation, then constructs only list/pair congruences for each authenticated
source row. On the same 1,662-row master this reduces authenticated master-row
theorem construction from 219.31 to 183.41 seconds, a 35.90-second (16.4%)
reduction. The complete computed cold path falls from 389.20 to 350.59
seconds, a 9.9% reduction, but remains 2.97 times the 117.91-second legacy
batch. Exact theorem, hypothesis, source, and axiom checks pass for all five
terminals.

The measurement redirects LP work away from claims of amortizing the current
per-row bridge. The material next boundary is a general soundness theorem
whose computed premise checks the complete encoded master/source
correspondence, so that Candle need not construct 1,662 individual arithmetic
denotation proofs. External sparse/index planning remains untrusted data; the
correspondence, hashes, selected rows, numerical verdict, and final theorem
interface must all be checked inside Candle.

The genuine nonlinear capture remains independent. The first leaf stays on
the shortest path; only after its authenticated result exists will a fresh
checkpoint copy capture leaves 4, 8, and 15 from the same 16-leaf certificate.
That follow-up shares one search/plan preparation and records exact Taylor
inputs plus native/staged timings for generalization tests.

Full timings, commits, and evidence hashes are in
`docs/progress/2026-09-22-v1.37-lp-five-terminal-correction-and-varied-nl-capture.md`.
