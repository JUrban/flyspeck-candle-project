# Candle NL first fast theorem implementation plan v2

Date: 2026-10-26 UTC

Status: **DEVELOPMENT / NON-RELEASE**

## Decision and present status

The first fast original Flyspeck NL theorem remains **0/1**.  The mathematical
and checker proof stack for case 10173 is substantial and real, but the
runtime integration chosen in the first plan is not an acceptable production
architecture.

The rejected implementation embeds the exact 4,707,156-byte case-10173
certificate as a literal in `candle_kernelProg`.  A complete manifest-graph
audit found that changing this theory invalidates **44 downstream theories**,
or **45 affected theories including `candle_kernelProg`**.  The cone reaches
the REPL safety translation, `compiler64Prog`, and the x64 bootstrap proofs.
The nominal 50-minute kernel target would therefore be only the first stage of
another roughly day-scale verified runtime rebuild.  Paying that cost for a
one-certificate runtime would not advance the all-NL production design.

The v3 kernel controller is retired and mechanically blocked.  No long build
is running.

## Evidence that is retained

The architecture correction does not invalidate these results:

- the exact case-10173 certificate is 4,707,156 bytes;
- all 4,173 genuine records pass the authenticated specialized checker;
- four independent mutation/rejection theorems pass;
- the specialized numerical executable completes the genuine workload in
  about 7.35 seconds;
- the ordinary default-clock semantics and registered fast-evaluator
  refinement are proved for the current case-10173 checker;
- the analytic, topology, and literal original-statement theorem adapters
  exist; and
- the complete relocated parent cache loads in 148 seconds with about 8.5 GiB
  peak RSS, no scratch dependency, and no object-tree mutation.

These facts are strong evidence that the numerical algorithm and semantic
proof chain can support the first theorem.  They are not evidence that the
case-specific runtime build is scalable, nor are they the missing theorem.

## Production design rule

Certificate bytes, jobs, roots, source descriptors, and other per-inequality
evidence must be **input data in the theorem term**, not literals baked into
the Candle runtime.  The verified runtime may contain a generally proved
checker and dispatch mechanism.  A new certificate must not require changing
`candle_kernelProg`, `compiler64Prog`, or the compiled CakeML binary.

The likely smallest interface is a four-payload call, or an equivalent
three-payload call with one explicitly decoded bundle:

1. certificate bytes;
2. authenticated source/program descriptor;
3. encoded jobs; and
4. encoded roots.

The ordinary semantics of the same generic wrapper must check those values.
The registered fast evaluator may return acceptance only after the proved
checker accepts them.  The existing `compute_payload3Fast` soundness pattern,
default-clock theorem, complete stream proof, and analytic handoff should be
reused.  Basename aliases, ambient runtime literals, and case-specific global
evaluation lemmas are forbidden.

## Bounded milestones

### R0. Revoke the case-specific build — complete

Exit evidence:

- `audit-fast-nl-kernel-rebuild-scope.py` reproduces the exact 44-theory
  downstream cone from generated object manifests;
- hazard LR-075 blocks a case-specific kernel rebuild;
- the old v3 controller exits before preflight or resource allocation; and
- its former admission receipt is stale because the controller and ledger
  bytes changed.

Elapsed implementation and testing: under one hour.  Long-run cost: zero.

### R1. Prove a data-driven dispatch seam

Deliverables:

1. literal extraction for four payloads, or one documented equivalent bundle;
2. a general refinement theorem from checker acceptance to ordinary
   default-clock `compute_eval` success;
3. exact equation-set and entry-point authentication;
4. rejection tests for a missing/extra payload, wrong entry, wrong equation
   set, changed certificate byte, changed source descriptor, changed job, and
   changed root; and
5. no case-10173 certificate literal or theorem in the runtime environment.

Exit test: a focused HOL build passes from the existing authenticated parent
cache and the seam's source/API audit is green.  No runtime or compiler rebuild
is allowed in R1.

Estimated focused work: **4–10 hours**.  Each edit/test loop is capped at
**10 minutes**; a test requiring more must be split or justified before it is
run.

### R2. Put genuine case 10173 through the data-driven seam

Deliverables:

1. the unchanged 4,707,156 bytes occur only as theorem input data;
2. the same 4,173 records, roots, guards, and source program pass;
3. all existing mutation tests plus the new interface-boundary mutations
   reject;
4. a direct compiled development executable runs the exact generic interface;
   and
5. the theorem ledger identifies the exact remaining assumptions between its
   accepted verdict and the original Flyspeck statement.

Exit test: the exact dynamic call has an assumption-free ordinary-semantics
refinement theorem and a successful fast executable result.  Static inspection
must show that neither `candle_kernelProg` nor `compiler64Prog` contains the
certificate.

Estimated focused work: **4–12 hours** after R1.  Focused proof builds are
capped at **30 minutes** and executable tests at **10 minutes**.

### R3. Establish that the runtime interface is reusable

Before paying for a verified runtime rebuild, run one structurally different
genuine Flyspeck family through the same data interface.  It need not yet have
the complete original-theorem adapter, but the checker must consume its real
descriptor and evidence without a source change to the runtime interface.

In parallel, classify the remaining selected-language gap: 250 `hminus`, 42
`matan`, and five inverse-trigonometric leaves.  Decide explicitly which are
covered by added general instructions and which use a proved fallback.  This
gate may reveal that the case-10173 checker is still too specialized; if so,
the interface changes before, not after, the runtime build.

Exit test: two structurally different genuine inputs pass unchanged runtime
source; their data identities and timings are recorded; every unsupported
class has a named implementation/proof route.

Estimated effort: **1–3 focused days**, with high uncertainty because this is
the first real generality test.  A discovered new expression family causes a
written re-estimate rather than an automatic long build.

### R4. Freeze once and rebuild the reusable verified runtime

Only after R1–R3 pass:

1. freeze and hash the generic checker interface and its proof dependencies;
2. remove the case-specific certificate literal and the
   `compiler64_global_eval_thms` patch;
3. rerun the full reverse-dependency and source-identity audits;
4. enumerate every required target in dependency order and record a predicted
   elapsed/RSS range from prior builds;
5. run bounded loaders and at most one-hour stage probes; and
6. admit one checkpointed full rebuild through the long-run hazard gate.

The present evidence says this is not a 50-minute task.  The planning range is
**20–36 elapsed hours** for the complete kernel/REPL/compiler/bootstrap chain,
subject to revision after the exact target ledger and stage probes.  This is a
one-time investment only if the checker interface has passed the reusability
gate.  A failed stage is preserved and diagnosed; its cap is not merely
increased.

### R5. Produce and repeat the first fast original theorem

Use the rebuilt generic runtime to compute the exact dynamic case-10173 term,
then apply the existing analytic/topology/original-statement chain.  Record
checker execution, payload decoding, theorem handoff, total elapsed time,
peak RSS, conclusion digest, assumptions, and axiom delta separately.

Exit test: two fresh runs produce the same literal original theorem with no
additional assumptions or axioms, take the registered fast path, and do not
perform the roughly 200-second generic per-cell evaluation.

Estimated post-runtime effort: **2–8 hours**, excluding the R4 rebuild.

## Stop/go rules

- No run over 30 minutes starts without a fresh receipt covering the exact
  controller, hazard ledger, source identities, reverse dependency cone, and
  target ledger.
- A green local target does not admit a run until its complete downstream
  invalidation cone is known.
- No timeout is increased in response to silence.  First obtain a progress
  marker, current phase, memory trend, and remaining-work estimate.
- A change to checker representation or call shape returns to R1.  A change to
  supported expression semantics returns to R3.  Neither may be smuggled into
  R4 as a build fix.
- The exact first theorem remains 0/1 until R5 passes.  “Close” and “almost”
  are not status values.

## What this plan does and does not claim

The proof evidence justifies continuing: the exact numerical workload passes,
the semantic refinement is proved, and the original theorem adapters exist.
The missing work is a trustworthy, reusable runtime boundary and its one-time
verified build.  The new plan is designed to determine cheaply whether that
boundary generalizes before paying the build cost.

It does **not** yet justify an all-NL runtime estimate.  That estimate requires
R3, the first repeated fast theorem, and a representative batch with shared
preparation charged once.
