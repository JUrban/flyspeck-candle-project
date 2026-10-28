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

#### R3 semantic-proof update — 2026-10-27

The reusable operation layer now includes complete object-rational Taylor
state refinements for square root, inverse, and arctangent.  In particular,
CakeML commit `fc7c944721` composes the general signed arctangent range theorem
with the generic unary Taylor constructor and preserves domain, center value
and gradient, whole-box value and gradient bounds, and the complete symmetric
Hessian.  The same theory separately proves that the returned center interval
contains mathematical `atn` whenever the input center contains its source
value.

This closes the nonlinear-operation slice of item 3; it does not close R3.
CakeML commit `2a8ca0b40f` also packages the completed negation, addition,
multiplication, and square paths behind the same full-state interface.  The
remaining bounded proof work is therefore to assemble those operation
theorems and the already-proved constant/variable cases into one stack
invariant, discharge the recognized delta instructions, lift the invariant
through generic program evaluation and packed acceptance, and compose the
accepted result with the existing analytic/Taylor theorem.  No runtime or
compiler build is admitted at this point.

Within the first eight focused hours, the target invariant and at least the
ordinary polynomial/arithmetic slice must build, or the exact representation
or theorem mismatch must be reported and this estimate revised.  Every proof
iteration remains capped at ten minutes.  There is no responsible calendar
estimate for the first fast theorem until that first semantic slice and one
nonlinear operation pass.

CakeML commit `c913c9e59` closes the first half of that bounded stack slice.
It defines the exact object-rational Taylor state, lifts the word/object
relation pointwise to evaluator stacks, gives object semantics for constants,
variables, negation, addition, multiplication, and square, and proves each
primitive wrapper from the existing full operation refinements.  Its final
one-theory build took 36.87 seconds and 819,248 KiB peak RSS.  The next child
must combine this stack relation with the source-to-prepared instruction
relation and prove one executable polynomial step preserves it, followed by
program-list induction.  This is measurable semantic-bridge progress, not the
program theorem, packed acceptance, multi-family gate, or first original
theorem; those remain open and no long build is admitted.

CakeML commit `29b46c86e` closes the one-step half of the source/prepared
polynomial gate.  For every related constant, variable, negation, addition,
multiplication, or square instruction, successful execution of the real word
step now yields an object step and a related successor stack.  The proof uses
the general rational-enclosure contract and preserves exact postfix operand
order and failure behavior.  The final one-child build took 30.14 seconds and
782,864 KiB peak RSS.  The remaining polynomial slice is list induction over
complete program execution and extraction of its singleton result; nonlinear
instructions, recognized delta instructions, packed acceptance, and the
multi-family gate remain open.  No runtime build is admitted by this result.

CakeML commit `3baad580b` completes the ordinary polynomial slice.  A list
induction now lifts the step theorem through arbitrary related postfix
programs, and an evaluator corollary proves that a successful singleton word
result has an exact singleton object-rational counterpart.  The final
one-child build took 31.44 seconds and 968,516 KiB peak RSS.  The enclosing
analytic instruction proof can therefore treat each polynomial block as one
semantic unit.  Its ordinary nonlinear constructors and pi/2 remain to be
assembled from the existing operation refinements, while recognized delta
instructions remain a separate explicit gate.  Packed acceptance,
multi-family evidence, and the original theorem are still open; no long build
is admitted.

CakeML commits `25d181bb4` and `4a40b317a` package the remaining ordinary nonlinear
operation conclusions into the same object-rational Taylor-state vocabulary.
Successful square-root, inverse, and arctangent executions now produce named
complete object states while preserving their explicit certificate contracts;
the concrete pi/2 constant has the corresponding valid exact-endpoint state.
The final one-child build took 36.57 seconds and 734,844 KiB peak RSS.  The
next child is the ordinary outer-instruction stack dispatcher.  Recognized
delta instructions, full program induction, packed acceptance, multi-family
evidence, and the original theorem remain separate open gates.  No runtime
build is admitted.

CakeML commit `57f689f93` closes the per-constructor ordinary outer-step
slice.  A successful actual step for any related polynomial, arithmetic,
square-root, inverse, arctangent, or pi/2 instruction now constructs an exact
object-rational successor stack and preserves the unconsumed certificate
suffix.  The final one-child build took 32.81 seconds and 896,832 KiB peak
RSS.  The next proof is a shallow source/prepared dispatcher over these nine
named theorems.  The two recognized delta instructions remain the explicit
separate gate before program induction; packed acceptance, multi-family
evidence, and the original theorem remain open.  No runtime build is admitted.

CakeML commit `0bcbb58f3` closes the ordinary source/prepared dispatcher.  The
nine constructor-specific theorems are now exposed through one shallow theorem
over the authenticated instruction relation, and the predicate explicitly
excludes both recognized delta implementations.  The final one-child build
took 33.78 seconds and 1,018,400 KiB peak RSS.  The next bounded gate is the two
exact recognized-delta refinements, followed by analytic-program induction.
Packed acceptance, the genuine multi-family gate, and the original theorem
remain open; no runtime build is admitted.

The subsequent recognized-delta audit found that the optimized executors have
exact source identities and successful-result well-formedness, but not the
general object-rational semantic refinements assumed by the earlier estimate.
Only six instructions in the current 167-instruction family use these
optimizations, so an ordinary-polynomial fallback remains a legitimate option.
The first no-op-source discriminator rejected but changed interval completion;
the proper unchanged-source experiment stopped on missing translation-parent
artifacts before execution.  Neither result decides the architecture.  The
next bounded gate is now to state the smallest honest specialized helper
contract and compare its proof scope against a correctly preflighted ordinary
fallback benchmark.  No hour-scale build is admitted by this finding.

CakeML commit `62b82c20b` closes the first specialized-helper slice.  Exact
object-rational refinements now cover successful interval sums,
scale-by-four, list scale-by-four, nested sums, and indexed updates, preserving
the executable association order.  The final isolated build took 32.68
seconds and 830,984 KiB peak RSS.  The next short target is the multiplication
and fixed delta product/value layer, then the gradient and Hessian assemblies;
the two complete delta Taylor states, analytic-program induction, packed
acceptance, multi-family gate, and first original theorem remain open.  No
runtime or compiler build is admitted.

CakeML commits `3db000f70` and `d333a5f41` close pairwise and three-factor
products, the fixed 21 delta products, and the complete compact delta-value
calculation.  The final isolated builds took 31.56 and 35.69 seconds, with
less than 0.9 GiB peak RSS.  The remaining specialized slice is now the signed
gradient, fixed Hessian, product Hessian, and the two complete Taylor-state
compositions for the six authenticated instructions.  Program induction,
packed acceptance, the multi-family gate, and the first original theorem
remain open; no runtime/compiler build is admitted.

CakeML commits `72ac9892d` and `2d70505fb` close the compact delta Hessian and
all six gradient components.  The final proofs use one coordinate-index table
and generic list-relation lifting rather than duplicated 21-element case
trees.  Their final isolated builds took 28.59 and 36.15 seconds, with less
than 1 GiB peak RSS.  The remaining specialized work is the coordinate-product
Hessian and composition through the two complete Taylor constructors for the
six authenticated instructions.  Program induction, packed acceptance, the
multi-family gate, and the first original theorem remain open; no
runtime/compiler build is admitted.

CakeML commits `fc3f6db6d` and `d5a7dc5ac` close that specialized numerical
slice.  All three negative-derivative and all three four-coordinate delta
instructions now refine successful word execution to complete exact
object-rational Taylor states.  The decisive four-coordinate proof reproduced
from source in a focused child of about 31 seconds; no long build was used.
The next bounded target is one combined source/prepared instruction theorem,
then analytic-program induction and packed-acceptance composition.  The
two-family semantic gate, reusable runtime build, and first original theorem
remain open; the first theorem is still **0/1**.

CakeML commits `c4e41c3f3` and `d45b757e0` then compose the ordinary and
authenticated-delta cases into one exact object-step relation and lift it
through arbitrary complete analytic programs.  Successful evaluation now
produces a related singleton exact object-rational Taylor result while
preserving the certificate suffix.  The remaining R3 proof boundary starts
at packed-cell input validity and acceptance, followed by the universal
analytic/Taylor handoff and the genuine two-family semantic test.  This does
not admit R4, and the first original theorem remains **0/1**.

CakeML commit `3434d4b749` closes the packed-input refinement boundary. The
plan-driven production wrapper now fails closed unless box, center, and radius
vectors are exactly six-dimensional and every decoded box/center interval has
ordered endpoints. Accepted cells refine to complete exact object-rational
source runs, and an induction lifts that result through every cell in an
accepted packed stream. The source decoder and checked compiler compose with
that all-cell theorem. The current genuine 875-cell fixture passes the
freshly compiled validated checker in 9.05 seconds; a reversed first box
interval rejects in 0.08 seconds. The remaining R3 proof is the universal
analytic/Taylor and original-statement handoff plus the genuine second-family
semantic gate. R4 remains forbidden and the first theorem remains **0/1**.

CakeML commit `6a9272048` closes the missing internal geometry guard. Every
packed center interval must lie inside its whole-box interval, and expansion
by the supplied radius must cover that interval without signed-word overflow.
The guard is proved to imply exact integer coverage inequalities, which are
retained in every accepted-cell object witness. The genuine case-16594
fixture satisfies exact expansion in all 5,250 coordinates, passes in 7.92
seconds, and rejects a one-unit-too-small first radius in 0.08 seconds.

The handoff audit also separates two obligations that the phrase “universal
analytic/Taylor handoff” previously hid. First, the packed geometry and a
per-family source-box correspondence must establish the arbitrary-center
`m_cell_domain` premises of the existing theorem
`candle_fs_result_complete_proxy_analytic_contains_box`. Second, the accepted
leaf batch must be consumed by the authenticated subdivision topology; 875
accepted cells and a matching count do not alone prove root-domain coverage.
Both are proof-only short-loop gates before the genuine second-family gate or
R4. The first original theorem remains **0/1**.

#### R3 trust-boundary correction — 2026-10-27

The scale-independent Taylor work closes more of the mathematics but also
exposes a boundary that the preceding paragraph described too loosely.  The
generic checker's theorem is presently a HOL4 theorem about an exact
object-rational execution.  The analytic and original-statement theorems are
HOL Light theorems.  A theorem in one logic is not an assumption-free premise
in the other merely because their rational encodings agree.  Therefore
“universal analytic/Taylor handoff” is not complete until a registered Candle
computation connects the two sides.

The established pieces are:

- Candle commits `4a511339`, `dde18e16`, `5f5b7426`, `c5c6bc72`, and
  `5eda2024` prove the scale-independent exact Taylor bound, expand the packed
  21-entry Hessian, connect it to analytic second partials, and derive
  pointwise negativity conditionally from the exact result fields;
- CakeML commits `230004466` and `c6dfafb8c` prove that an accepted packed
  cell has a complete exact object-rational result, a true domain flag, and a
  strictly negative exact upper endpoint; and
- the final `c6dfafb8c` theory reproduced from the prepared parent cache in
  39.30 seconds with 1,164,408 KiB peak RSS.  No runtime/compiler build was
  used.

The missing trusted composition is now its own R3 gate:

1. Fix one ordinary HOL/Candle entry point whose equation set represents the
   exact object-rational cell computation.  The preferred discriminator is a
   generic refinement to the existing exact-rational Taylor program and
   `candle_cv_q_dim_taylor_model_certified_finish`; the old decimal
   case-10173 checker is not the target, and a new packed ordinary checker is
   the fallback only if that refinement cannot express the optimized source
   instructions.
2. Prove in HOL4 that generic packed acceptance refines default-clock
   `compute_eval` of that exact entry point for literal input payloads.  This
   theorem must be source- and cell-parametric; a case-16594 identity theorem
   is only a test instance.
3. Consume the resulting ordinary HOL equality in HOL Light and discharge the
   premises of `candle_q_packed_hessian6_exact_cell_negative` for one genuine
   case-16594 cell, with no assumptions or new axioms.
4. Repeat the same route for all 875 cells and then consume the existing
   authenticated topology.  Cell count is not topology evidence.
5. Repeat the semantic route on a structurally different genuine family
   without changing the entry point or registered evaluator source.

The first discriminator is capped at 4 focused hours, with each build capped
at 10 minutes.  Its output must be the exact entry-point signature, equation
set, result representation, and residual proof obligations.  If the existing
exact evaluator cannot represent a recognized optimized instruction, stop
and compare a proved expansion against a small new ordinary wrapper; do not
fall back to another family-specific `compute_eval` chain.  R4 remains
forbidden until this gate is green.  In particular, the present evidence
justifies continued short proof work but does not yet justify the 20–36-hour
runtime investment.

#### R3 full-source-entry correction — 2026-10-28

The first packed-entry discriminator is now cleanly rebuilt but does **not**
close the gate above.  CakeML commits `14caf5de4`, `470b5156b`, and
`9869926fb` promote its complete 81-theory closure into production source and
remove every scratch dependency.  A clean build completed in 34 minutes 42
seconds across two capped segments and a repeat dry run scheduled zero
theories.

The proof establishes a valid but narrower result: an authenticated accepted
packed source cell has exact result payloads for which
`candle_cv_q_packed_object_accept6` succeeds.  That five-argument ordinary
entry checks the final Taylor formula only.  Its HOL Light correctness theorem
does not by itself establish that the supplied center value, gradient, and
packed Hessian enclose the original analytic expression and derivatives.
Those facts occur in the HOL4 hypothesis
`bounded_packed_analytic_object_cell`; they are not transported into HOL Light
by the final acceptance equality.

Accordingly, the R3 trusted-composition gate is refined as follows:

1. the ordinary entry must represent the **full source evaluation**, or a
   checked decode into the existing full exact evaluator, rather than only
   the final Taylor suffix;
2. its HOL Light correctness theorem must derive the analytic containment
   premises used by the cell-negativity theorem;
3. generic packed acceptance must refine default-clock `compute_eval` of that
   full entry for the same source, box, and certificate identities; and
4. one genuine closed HOL Light cell must pass before the 875-cell topology is
   attempted.

The preferred implementation is a Boolean acceptance wrapper around the
existing fixed nonlinear certified checker.  Returning only the Boolean
avoids requiring the fast callback to reproduce the exact evaluator's upper
endpoint.  If the existing call cannot represent the separated packed
certificate stream, one small ordinary decode-and-check wrapper is allowed;
a case-specific result table is not.

Until this theorem exists, `bounded_case16594_packed_cell_entry_eval` is
reported as **1/1 conditional source-contract refinement**, while the first
fast HOL Light cell and first fast original theorem both remain **0/1**.  No
run over 30 minutes and no R4 runtime build is admitted by the suffix theorem.

#### R3 certificate-driven full-source entry update — 2026-10-28

A static comparison ruled out the superficially cheapest wrapper.  The
existing `candle_cv_fsn_variable_raw_jobs_check` is a genuine full exact
source checker, but it recomputes `sqrt`, reciprocal, and `atan` by different
exact interval algorithms.  The fast packed checker instead consumes
outward-rounded certificates and specialized delta instructions.  Packed
acceptance therefore does not generically imply acceptance by that exact
checker; treating it as a Boolean-equivalent wrapper would merely hide the
unproved semantic join.

The bounded replacement is an ordinary certificate-driven source entry.  It
checks each supplied nonlinear result against an exact rational semantic
predicate, then reuses the existing analytic theorems.  The first production
slice is committed at Candle `4b47c08d`:

- exact interval-widening and reciprocal-certificate predicates;
- an executable Candle encoding of both predicates;
- assumption-free correctness of those encodings; and
- an assumption-free theorem that an accepted reciprocal certificate
  encloses the mathematical reciprocal of every input value.

The proof body passed from the prepared analytic checkpoint in 99 seconds,
including restore.  This is the first reusable component of the corrected
full-source entry, not a cell theorem.  The remaining joins are: propagate
the reciprocal certificate through the Taylor object, connect existing
square-root certificates, add the exact `atan` certificate predicate, prove
the authenticated delta instructions' ordinary semantics, lift the result
through source-program evaluation, and finally prove packed acceptance
refines this full ordinary entry.  The first fast HOL Light cell and first
original theorem remain **0/1**; no long runtime build is admitted.

Candle commit `06e42c5b` now closes the reciprocal propagation join named in
that list.  Under the executable reciprocal certificate, one general theorem
proves that the supplied interval propagates soundly through the value, every
gradient component, and the complete Hessian of the reciprocal chain rule.
The final focused proof passed in 102 seconds including checkpoint restore.
The next nonlinear join is the corresponding square-root certificate route,
reusing its existing value theorem and the same generic unary structure;
arctangent and authenticated delta instructions follow.  This remains
operation-level progress: the complete source-program induction, full entry,
first genuine cell, and first original theorem are still open.

That square-root join is complete at Candle commit `e3e7c35a`.  One generic
certified-unary constructor now propagates supplied value, first-derivative,
and second-derivative intervals through every gradient and Hessian component.
Its square-root instance checks the root certificate and the same three
reciprocal facts used by the packed checker, then proves the exact square-root
chain rule for every source jet.  The final proof passed in 100 seconds from
the new reusable post-reciprocal checkpoint.  The next operation-level target
is arctangent; after it, the plan must connect authenticated delta operations
and perform the complete source-program induction.  The first genuine fast
cell and original theorem remain **0/1**.

The ordinary arctangent join is complete at Candle commit `993751f0`.  Its
executable certificate requires the supplied fixed-scale value interval to
enclose the existing exact rational arctangent range and requires the supplied
derivative interval to enclose `1 / (1 + x^2)`.  A general theorem constructs
`-2*x/(1+x^2)^2` and proves the arctangent value, every gradient component,
and the complete Hessian through the same certified-unary constructor.  The
final focused proof passed in 98 seconds from the reusable post-analytic-atan
checkpoint.  This closes the ordinary HOL Light nonlinear-operation list; it
does not yet prove that the fixed-word arctangent result satisfies the exact
certificate.  That fact remains part of the fast-to-full-entry refinement.
The next bounded target is the six authenticated delta operations, followed
by complete source-program induction.  The first genuine fast cell and
original theorem remain **0/1**, and no long runtime build is admitted.

Candle commit `bb735c94` closes the common delta-value subproblem. The
ordinary HOL Light operation now uses exactly the same unnormalised rational
sum/product association as the established HOL4 object witness, has an
executable Candle encoding, and proves that its result encloses the exact
Flyspeck delta polynomial for arbitrary contained inputs. The focused proof
passed in about 100 seconds including checkpoint restore. The remaining delta
work is the compact gradient, fixed 21-entry Hessian, product Hessian, and the
two complete Taylor-state families. Only then can the combined instruction
theorem and source-program induction begin. The first genuine fast cell and
original theorem remain **0/1**; no long runtime build is admitted.

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
