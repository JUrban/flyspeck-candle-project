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
