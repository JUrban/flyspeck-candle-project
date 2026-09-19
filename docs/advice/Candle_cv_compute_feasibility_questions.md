# HOL4 translation support for fast computation in Candle

While the current LP verification continues, could you assess the feasibility of bringing HOL4’s `cv_trans` / `cv_eval` capabilities to Candle and using them for expensive Flyspeck computations? An initial outcome could be a short plan and a proposed benchmark, with implementation depth guided by what you find.

The aim is to support the longer-term goal of a full Flyspeck-capable HOL Light substitute while keeping the current functional run moving. Please use your judgment about timing, resources, and whether a small prototype would resolve an uncertainty more cheaply than further planning.

## Background

The published work describes a verified fast-computation primitive in Candle, with additional proof-producing translation automation in HOL4. This suggests a useful starting point, but the capabilities exposed by our exact branch and executable need checking. See [Fast, Verified Computation for HOL ITPs](https://link.springer.com/article/10.1007/s10817-025-09719-8).

HOL4’s translator operates on logical function definitions. Applying it to existing Flyspeck ML tactics therefore needs an explicit integration strategy; a translator port alone does not establish a speedup for those tactics. [HOL4’s release documentation](https://github.com/HOL-Theorem-Prover/HOL/releases) describes the relationship between `cv_trans`, `cv_eval`, and `cv_compute`.

## 1. What already exists in this Candle branch?

- Which fast-computation primitives are available in the current source and actually exposed by the running executable?
- Which parts of HOL4’s translation and evaluation automation could be reused, and which depend on HOL4-specific theorem APIs, definitions, or libraries?
- What supporting theories and data encodings would a useful first version require—for example, lists, integers, rationals, recursive functions, and datatype conversions?
- Could the initial work stay outside the verified kernel, using its existing computation facility?

## 2. Which real Flyspeck costs could benefit?

- On representative LP and nonlinear checks, how much time is spent in arithmetic evaluation, theorem construction, certificate decoding, and frontend processing?
- Which measured operations are suitable for evaluation as logical functions? Possible candidates include exact arithmetic, linear-combination checks, or interval-bound checks, subject to inspection of the actual code.
- Would accelerating existing arithmetic conversions be sufficient, or would the larger benefit require a logical certificate checker with a proved correctness theorem?
- Which substantial costs would remain unaffected?

## 3. What is the smallest useful prototype?

- Could one expensive operation or one certificate-checking component demonstrate the approach before a general translator port?
- Would a small manually prepared set of computation equations be a cheaper way to test the potential benefit first?
- What is the minimum dependency set, and which translation, termination, or precondition obligations would need proving?
- What result would justify extending the prototype to broader LP or nonlinear coverage?

## 4. How does the computation produce the required Candle theorem?

- How would inputs be represented, evaluated, and connected back to the existing Flyspeck statement?
- Which translation or checker-correctness theorems must be established in Candle, and how would the port construct them?
- How would the resulting proof preserve the required conclusions and hypotheses, without assuming unchecked results from a separate HOL4 run or an external computation?
- How could the accelerated path fit behind existing conversions or verifier interfaces so that ordinary Flyspeck proofs can use it?

## 5. Does it improve end-to-end performance enough to justify the work?

- Which real workload would provide a fair baseline and a useful first comparison?
- Could measurements include input conversion, computation, theorem construction, memory use, and reusable setup costs, rather than timing only the evaluator?
- How would the effort and likely benefit compare with parallel verification of independent certificates, including the cost of combining their results soundly? Could both approaches complement each other?
- What evidence would support proceeding, narrowing the scope, or deferring the port?

## Suggested initial response

A concise assessment could identify the existing capabilities, missing dependencies, best first target, benchmark design, proof obligations, and rough implementation effort. A staged proposal with clear decision points would be useful. Please distinguish measured results from expected benefits and unresolved questions; no Flyspeck speedup is assumed in advance.
