# Candle NL first fast theorem implementation plan v2

Date: 2026-10-26 UTC

Status: **DEVELOPMENT / NON-RELEASE**

## R3 execution update — 2026-10-26

The empirical two-family part of R3 is green.  CakeML commit `e49324121`
builds one four-payload executable that accepts the unchanged genuine
case-10173 certificate and the structurally different genuine case-16594
certificate twice each.  The same binary rejects certificate, source, job,
root, and cross-family substitutions.  No runtime/compiler rebuild was used.

The experiment also found the intended architectural discriminator: although
the command-line interface is shared, the checker body still contains an
explicit disjunction of the case-10173 and case-16594 checkers.  Adding a third
family would therefore change verified runtime source.  This is evidence that
the interface shape is viable, but it is not yet the general all-NL runtime
required by the production design rule below.  R4 remains **not admitted**.

The replacement bounded gate is to move family identity out of runtime
dispatch: decode an arbitrary supported source program and versioned evidence
plan, prove checker acceptance sound for that decoded program, and keep each
Flyspeck source-to-program correspondence theorem outside the runtime.  The
two current family-specific checkers remain exact regression oracles.  The
same generic source must reproduce both positive runs and all substitutions
before this plan advances to R4.

The selected-language routes are now explicit but not yet all present in that
generic checker:

- `hminus` uses the already-proved extra-coordinate/interval-parameter
  fallback and the general append-parameter theorem;
- `matan` becomes a general checked instruction using the existing exact
  series, dimension-jet soundness, fixed-scale handoff, and genuine original
  theorem evidence; and
- the five `asn`/`acs`/`arc_hhn` leaves use guarded formal normalization
  through `ASN_ATN`/`ACS_ATN`, with `arc_hhn` unfolded, into the existing
  `atan`/`sqrt` language.

This classification is not a claim that all 7,814 selected leaves have run.
It prevents those operations from being introduced as case-specific branches
during a long runtime build.

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

#### R3 result and correction, 2026-10-26

The stable four-payload executable accepted two structurally different
genuine families twice each, but inspection found that its implementation was
an explicit disjunction of the two named family checkers.  The call shape is
reusable; the runtime implementation is not yet an all-NL checker.  R3
therefore remains open and R4 remains forbidden.

The first corrective slice is complete at CakeML commit `6b3c5b0fc`:

- the packed input parser is parameterized by dimension and certificate count;
- the header and traversal are parameterized by cell and certificate counts;
- the numerical evaluator takes an explicit prepared analytic program;
- a HOL theorem proves the specialization at `(6,875,31)` and the current
  case-16594 prepared program exactly equals the established 875-cell checker;
  and
- the complete generic core translates to CakeML in one focused 3m03s build.

This removes the family name from the cell-evaluation and streaming layer.  It
does not yet authenticate an arbitrary decoded source program or evidence
plan.  The remaining R3 work is a versioned plan decoder and checked generic
source-to-prepared-program compiler, followed by both genuine fixtures through
that single implementation.  The current case-specific checkers remain
regression oracles.  If the first plan schema cannot represent both fixtures
within eight focused development hours, stop for a schema/proof-gap review;
do not compensate with a longer runtime build.

The next source-to-plan slice is complete at CakeML commit `3b1f875aa`:

- every source rational is rounded outward at 2^40 by one total, checked
  compiler rather than a finite case-16594 constant table;
- overflow and out-of-dimension variables reject;
- the six proved delta optimizations are recognized only by exact source
  polynomial identity;
- the compiler reproduces the entire established case-16594 prepared program
  and specialization ledger exactly;
- version-1 plan metadata carries only dimension and cell count, while the
  certificate-record count is derived from the compiled program; and
- the genuine case-16594 source CV plus its versioned metadata is proved
  equivalent to the established complete checker, with the whole path
  translated without side conditions.

The remaining proof obligation before promoting this compiler into the
original-theorem handoff is the general rational-enclosure/source-semantics
lemma.  After that, the next runtime experiment is one direct genuine payload
through this plan-driven wrapper, followed by the second family/schema test.

The rational-enclosure half is complete at CakeML commit `e6ce0e051`.  A
general theorem now proves that every successfully compiled positive, zero,
or negative source rational is enclosed by its valid stored scale-2^40
interval.  The remaining trusted proof boundary is the source-program
semantic induction and its composition with the universal analytic checker;
the runtime experiment remains gated on that result.

The structural compiler induction is complete at CakeML commit `e5d168e7d`.
It proves that successful compilation preserves constants through the general
rational-enclosure theorem, preserves variable indices and ordinary operator
constructors, and admits a specialized delta instruction only through the
existing exact source-recognition predicate.  This is deliberately a
**structural** relation.  It is not the still-missing theorem that execution
of every prepared instruction encloses the value and derivatives of the
source analytic expression.

CakeML commit `8f04e4baa` fixes the resulting plan-driven executable interface.
The direct compiled program accepts the unchanged genuine 875-cell case-16594
certificate in 9.18 seconds and rejects wrong version, dimension, cell count,
source, and certificate inputs.  This closes the behavioral regression for
the first generic-plan family.  It does not close R3: a second genuine family
has not yet passed this same plan compiler, and executable acceptance is not
an analytic soundness theorem.

The next bounded proof gate is therefore explicit:

1. state the operation-level invariant relating a prepared scale-2^40 jet to
   the value, gradient, Hessian, and domain of its source instruction;
2. prove the constant, variable, negation, addition, multiplication, square,
   and polynomial cases from existing interval/jet lemmas;
3. prove `sqrt`, inverse, and `atan`, and discharge the exact-recognized delta
   specializations using their existing general soundness contracts;
4. lift the invariant through program evaluation and packed-cell acceptance;
   and
5. compose it with the universal Taylor/checker theorem before any runtime
   rebuild is admitted.

Within the first eight focused hours, the target invariant and at least the
ordinary polynomial/arithmetic slice must build, or the exact representation
or theorem mismatch must be reported and this estimate revised.  Every proof
iteration remains capped at ten minutes.  There is no responsible calendar
estimate for the first fast theorem until that first semantic slice and one
nonlinear operation pass.

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
the rational and structural compiler refinements are proved, and the original
theorem adapters exist.  The general operation-level analytic refinement is
**not** yet proved.  After that proof, the missing work is a trustworthy,
reusable runtime boundary and its one-time verified build.  The new plan is
designed to determine cheaply whether that boundary generalizes before paying
the build cost.

It does **not** yet justify an all-NL runtime estimate.  That estimate requires
R3, the first repeated fast theorem, and a representative batch with shared
preparation charged once.
