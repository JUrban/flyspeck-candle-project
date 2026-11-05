# Response to Audit 3: Candle NL first fast theorem gate map

Date: 2026-11-05 UTC (responding to the 2026-11-04 audit)

Status: **DEVELOPMENT / NON-RELEASE**

Post-response implementation update: the replacement whole-call contract
skeleton now typechecks, and the live gate map has been expanded through the
runtime build, prepared-state, and fresh-repeat gates described below.  On
2026-11-05, focused G2 work closed both the negative-delta and product-delta
families for arbitrary valid inputs, including all six specialized dispatch
adapters.  G2 is therefore **complete**.  G3 has also gained (1) a generic
joint evaluator/semantic trace kernel for a list of dispatch steps and (2) a
mechanically authenticated refinement from the exact 167-instruction
case-16594 source program to its prepared specialized plan.  The one-cell
structural clock obligation is now also closed: the authenticated code list
has length 167 and the complete trace requires 524,741 ticks, below the
1,000,000,000 default clock (commit `c9bd89e1e`).  The remaining G3 work is
the concrete 167-step joint evaluator/semantic trace and the final leaf
`m_cell_pass` result.  The runtime
dispatch-code/source-CV plan and the actual authenticated cell-0 payload have
now both been mechanically identified with that exact 167-step plan.  This
does not change the public first-theorem metric: it remains **0/1**.  G3--G9
are not closed.

Further bounded work after the first draft has closed the reusable per-step
join needed by that concrete trace.  The genuine certificate packet ledger is
authenticated, all 42 production arctangent guards in its seven packets are
proved, and exact joint fixed-word/object/production-evaluator adapters now
cover square root, inverse, and arctangent (commits `a2061dc78` through
`91bc66d0e`).  A separate joint theorem covers the six certificate-free
ordinary families--polynomial, negation, addition, multiplication, square,
and pi-half--at the same 524,405 step floor (commit `fd56a5670`).  Thus the
next bounded test is a genuine 0--9 prefix, which exercises every ordinary
and certificate-consuming family before the first specialized delta at
position 34.  This is stronger than the state reviewed by the audit, but it
still is not the concrete 167-step trace, `m_cell_pass`, a whole 875-cell
verdict, or the original theorem.

A bounded clean-replay probe on 2026-11-05 also sharpened the build-closure
claim.  The immediate G1 target exposed a 12-theory frontier, not 186; 11 of
those theories exported cleanly.  The final theory then failed because its
certified-atan ancestor had been proved/exported only in a warm development
state and its committed source chain was absent from that scratch snapshot.
Restoring those committed sources made Holmake propose a 58-theory transitive
rebuild through stale/missing generated artifacts.  That expansion was
stopped rather than accepted as necessary work.  The affected certified
inverse, square-root, and arctangent cones were then rebuilt in fresh,
bounded, single-theory processes; one missing static `preamble` include was
identified and made explicit.  The old stack adapter was regenerated, the
previously omitted pi-half clock adapter was added, and all nine ordinary
case-16594 dispatch operations now export through one uniform clock-floor
interface (commits `21d81278b` and `c9bd89e1e`).  Thus the 186-theory figure
remains discredited, and the immediate source/artifact hygiene defect is now
repaired.  This does not discharge the later clean-build obligation for the
concrete 167-step trace or whole-call callback.

## Executive assessment

The audit is materially useful.  Its central criticism is correct: the
audited gate map accurately described the local evaluator/semantic proof work,
but compressed or omitted several later end-to-end obligations.  In
particular, it was not a complete map from the 9-second numerical checker to a
theorem produced by a newly built Candle runtime.  The live map has since been
expanded to make those later gates explicit; they are not thereby complete.

The current public status remains:

- direct Flyspeck: **297/297**, green and checkpointed;
- LP: complete and checkpointed;
- genuine case-16594 numerical checker: **167/167 positions** and **875/875
  cells** accepted;
- first original Flyspeck NL theorem through the fast production route:
  **0/1**;
- highest completed logic gate: **G2**; all six specialized coordinate
  adapters are generically closed;
- current local proof gate: **G3**, where the generic trace composition and
  exact source-to-prepared-plan/runtime-payload refinement are complete and
  all nine ordinary/certificate-consuming dispatch operations have both a
  uniform clock-floor theorem and a joint fixed-word/object/evaluator step,
  and its exact default-clock capacity is proved, but the concrete
  167-position trace and leaf semantics remain.

The audit is also right that the **3--7 focused day** range in the gate map
must not be read as an end-to-end estimate for the first installed theorem.
It was intended to cover the current proof joins through the semantic and
fast-correspondence layer, excluding the runtime rebuild.  Because the map's
headline is the first theorem, that exclusion is misleading.  The estimate
will be relabelled as a local proof-stack estimate, and no replacement
end-to-end calendar estimate should be issued until the whole-call skeleton,
runtime target, and new-binary prepared-state cost are explicit.

No runtime rebuild or hour-scale run is justified by this response.

## What the audit gets right

### 1. The production runtime is missing from the gate sequence

Confirmed from source.  The currently installed privileged `compute` path in
`prover/candle_kernelProgScript.sml` ends in the case-10173-specific
`compute_case10173_tag10_genuine_fast_def` chain.  It does not contain the
case-16594 plan-driven callback now being proved.

The genuine case-16594 prefix therefore misses the installed specialized
branches and enters the generic translated evaluator, as reported in v4.313.
The 16 GiB failure is not a failure of the 9-second fixed checker, but it does
prove that the present binary cannot perform the intended final run.

Plan v2 already gives a prior **20--36 elapsed hour** range for the complete
verified kernel/REPL/compiler/bootstrap rebuild cone.  That number has not
been revalidated for the exact final callback and must not be silently
excluded from a first-theorem schedule.

There is one wording nuance.  A conditional Candle-side theorem of the form

```text
whole_call = T ==> original_case16594_statement
```

can be stated and typechecked before a new runtime exists.  But the current
G5 wording says it *yields the literal original theorem*.  That unconditional
result needs the `Kernel.compute` equation, hence the new installed callback
and runtime.  The revised map must either call the earlier artifact a
conditional handoff or put the runtime gate before the unconditional theorem.

### 2. Jobs, topology, and their cross-correspondence are missing

Confirmed.  v4.321 and v4.324 correctly record the required whole-call roles:

- 875 numerical jobs;
- 1,749 topology tokens (875 leaves and 874 glues);
- exact source/program identity; and
- correspondence between the jobs consumed by the ordinary Candle call and
  the packed cells accepted by the fixed checker.

These obligations were not explicit in the audited G0--G6 sequence.  G0
proves that all 875 packed cells numerically accept; it does not prove that
they form the authenticated root domain.  The live map now assigns this work
to G4.

The source audit makes the omission concrete.  The current
`registered_case16594_external_witnessed_checker` still requires its job and
root payloads to be `Num 0`.  The explicit-radius export used by the evaluator
proofs is the **cell-0, 175-equation** entry, not a whole 875-cell plus topology
entry.

The older 1,749-token handoff is reusable mathematical machinery, but its
immediate executable premise is the old
`candle_cv_q_dim_taylor_model_fixed_outer_variable_complete_check` equation.
It is not already a theorem that an arbitrary new explicit-radius batch
verdict can be substituted for that premise.  Either that equivalence or an
alternative adapter from the new per-leaf `m_cell_pass` results must be
proved.

### 3. The default-clock theorem is a real omitted obligation

Confirmed.  `compute_fast_eval_ok` is defined against
`compute_default_clock`, which is exactly **1,000,000,000**.  The local step
theorems with floors such as 32, 4096, or 65537 do not by themselves prove
that the whole authenticated call fits that clock.

The complete-call clock must be derived structurally, not inferred from wall
time and not discharged by increasing a runtime timeout.  It belongs in the
whole-call ordinary-semantics gate and in the callback's
`compute_fast_eval_ok` exit criterion.

### 4. The end-to-end theorem skeleton was promised and not maintained

Confirmed.  Response1 adopted a conditional composition skeleton as its first
step.  The subsequent switch from the case-10173 decimal route to the
case-16594 explicit-radius object route invalidated the old composition
target, and no current report records a replacement skeleton typechecked
against the new definitions.

This is the clearest process failure exposed by the audit.  The gate map was a
good status reset, but it should have been generated from a typechecked
end-to-end skeleton rather than used as a substitute for one.

### 5. The negative-delta status was too broad at audit time

Confirmed with a qualification.  At audit time there was already a generic
fixed-word to exact-object theorem,
`bounded_delta64_neg_derivative_covers_object_q`, but the evaluator evidence
in `2d899e860` was closed computation on the three genuine cell-0 inputs.  It
did not establish the input-quantified evaluator-to-object/dispatch join
needed for arbitrary accepted cells.

That exact negative-delta omission has since been closed.  Candle commit `b13034302` exports
`bounded_case16594_object_delta_neg_source_state_eval_refines_word`, deriving
the production source-state evaluation and runtime/object equivalence from
word/object coverage and fixed-word success for any coordinate below six.
The analogous product-delta evaluator-to-semantic result and all six exact
specialized dispatch adapters have now also been composed and exported in
commits `eee7b1c06` and `26010c41e`.  G2 as a whole is therefore closed.

### 6. Runtime and integration risk are tested too late

Confirmed in substance.  No case-16594 call can hit a specialized branch in
the current installed binary because that branch is absent.  Waiting until a
final verified build to discover exact dispatcher, payload, or theorem-shape
problems would repeat the failure pattern that motivated the agile gates.

The appropriate early test is not automatically a 20--36-hour untrusted
kernel rebuild.  The direct compiled plan checker has already established the
9-second numerical execution.  The next useful development test is the exact
whole-call callback and dispatcher, with all four payload roles, compiled by
the lightest faithful route (including direct `cake` compilation if it can
exercise the real callback representation).  It must record an exact branch
hit and mutations.  If that test cannot be produced within a bounded packet,
the reason becomes a gate failure before the verified runtime investment.

### 7. The schedule needs per-gate controls

Confirmed.  Every remaining gate needs:

- a logic/repository/representation label;
- a predicted focused effort and build/run cap;
- actual elapsed time and peak RSS on completion; and
- an explicit estimate revision when the cap is exceeded.

A two-times estimate stop is useful as a review trigger, not as permission to
declare an uncertain proof impossible.  The existing under-three-minute edit
loop remains binding for local proof development.

## Corrections and qualifications to the audit

### The repeated Hessian work is not the same theorem proved three times

The audit correctly observes that the delta Hessian appears repeatedly, but
the layers are not redundant copies:

1. fixed-word execution refines an exact object-rational result in HOL4;
2. exact object-rational delta jets satisfy the analytic invariant;
3. the exported Candle `compute` equations evaluate to that object result;
4. the ordinary evaluator result is eligible for a proved fast callback.

Crossing these representation and logic boundaries is necessary.  The
planning defect was failing to state their final composition early enough,
not that the same mathematical Hessian identity should only have been proved
once.

### The 186-theory rebuild is not yet established as required work

The 186-theory request was produced by an incoherent/stale generated cache
whose children named different `compute_exec` identities.  It was correctly
stopped.  The exact missing certified-operation artifacts have now been
reconstructed in bounded, isolated builds rather than by accepting that
monolithic schedule.

There is still a real integration-build gate: the final G3/G4 source closure
must build under one identity.  But **186 theories was an observed bad-cache
schedule, not the measured clean closure size**.  The repaired immediate cone
is evidence for the bounded approach, not a waiver of the final closure test.

### “The mathematics is not the problem” is slightly too strong

No new analytic idea is presently known to be required.  The universal
Taylor/analytic results, the exact delta identities, and the old original
statement/topology adapters are substantial positive evidence.  Nevertheless
G3--G5 have not exported on the exact new whole-call representation, so it
would be premature to guarantee that every remaining obligation is merely
syntactic composition.

## Answers to the audit's eight questions

1. **Which runtime will run the final theorem, and what will it cost?**  It
   must be a newly rebuilt Candle runtime containing the frozen generic
   plan-driven callback.  The current binary is insufficient.  The only
   current build range is the older **20--36 elapsed hour** R4 forecast; it
   must be re-preflighted against the exact frozen source.  Prepared-state
   reconstruction is additional and is not yet measured.

2. **Case-specific or generic callback?**  Generic and plan-driven.  A
   case-16594 exact-call registration would be throwaway architecture and is
   forbidden by plan v2 unless the project owner explicitly changes that
   decision.  Case-16594 may be the first instantiated theorem, but family
   data must remain input data.

3. **What state will the fresh run use?**  Not yet specified tightly enough.
   A DMTCP image of the old binary cannot validate the new callback.  The
   revised plan must name the minimal Flyspeck/NL predecessor state required
   for the original theorem and measure its cold construction on a compatible
   development binary before the long verified build is admitted.

4. **What does the 1,749-token adapter consume?**  The preserved complete-root
   adapter immediately consumes the old complete-check compute equation and
   then derives the singleton root/source theorem.  Its internal soundness
   does derive `m_cell_pass`, but the adapter is not presently a drop-in
   consumer of the new explicit-radius batch result.  A bridge or a different
   per-leaf topology adapter is required.

5. **Does a whole-call explicit-radius entry exist?**  No.  The authenticated
   exported entry currently used by G1/G2 is the cell-0 175-equation closure.
   The whole-call explicit-radius entry, with jobs and topology, is a missing
   deliverable.

6. **What is the whole-call clock requirement?**  Unknown today.  The
   production target is at most `compute_default_clock = 10^9`, but no
   complete structural bound for the new call has been exported.  This is a
   gate, not an assumption.

7. **Which theorem covers negative delta for arbitrary inputs?**  The generic
   fixed-word/object refinement is
   `bounded_delta64_neg_derivative_covers_object_q`.  The formerly missing
   exported-evaluator/runtime join is now
   `bounded_case16594_object_delta_neg_source_state_eval_refines_word` in
   Candle commit `b13034302`.  The earlier `2d899e860` results remain closed
   genuine probes rather than the universal join.

8. **Does G3 require 186 theories?**  No evidence supports that number.  The
   bad-cache schedule has been replaced by bounded isolated rebuilds of the
   certified inverse, square-root, arctangent, and ordinary-dispatch cones,
   ending in all nine ordinary clock-floor wrappers.  The concrete trace and
   final callback will still require their own coherent one-identity closure;
   its exact size and cost must be measured rather than inferred from 186.

## Revised control structure

The next gate-map revision should retain G0--G2 but replace the compressed
tail with the following explicit gates.  The typechecked skeleton is a
control artifact to create immediately, not a final gate.

| Gate | Required exit evidence |
|---|---|
| S0. End-to-end skeleton | HOL4 `compute_fast_eval_ok` target and Candle `whole_call = T ==> original_statement` target typecheck against the real equation set.  Every temporary hypothesis or uncommitted `cheat` is counted and assigned to a gate. |
| G2. Specialized operations | All six specialized evaluator results are related to exact object states for arbitrary valid inputs; the three genuine coordinate instantiations follow. |
| G3. One-cell ordinary semantics | The authenticated 167-position explicit-radius program has an ordinary evaluator theorem, exact stack/certificate preservation, final Boolean meaning, and a derived structural clock bound. |
| G4. Whole batch and topology | A concrete whole-call entry authenticates source/program, 875 jobs, packed-cell correspondence, 1,749 tokens, singleton root, and the adapter premise.  Job/topology/source/certificate mutations reject. |
| G5. Fast callback and generality | The generic plan-driven callback has `compute_fast_eval_ok` at the default clock.  A lightweight compiled exact-dispatch test hits the intended branch.  A second structurally different family passes without callback-source change. |
| G6. Conditional analytic/original handoff | The actual whole-call equality is the sole computational premise needed to obtain the literal case-16594 statement; assumptions and axiom delta are audited. |
| G7. Freeze and verified runtime build | Exact callback/proof bytes, dependency cone, stage caps, predicted elapsed/RSS, and long-run receipt are frozen; one verified runtime is built. |
| G8. New-binary prepared state and theorem | The minimal compatible state is constructed, the fast branch is observed, and `Kernel.compute` produces the original theorem.  Preparation, checking, decoding, handoff, total time, RSS, assumptions, and axioms are recorded. |
| G9. Fresh repeat | A second clean run reproduces the literal theorem and conclusion digest. |

The public metric remains **0/1** until G8.  G2 has completed in bounded proof
loops.  Within G3, the reusable trace composition theorem, exact
source-to-prepared plan authentication, runtime dispatch-code identity,
actual payload identity, and uniform clock-floor plus joint semantic/evaluator
wrappers for all nine ordinary/certificate-consuming operations are complete.
Completion must not be described as
leaving only a compressed G3--G6 tail: the concrete trace and the expanded
G4--G9 production chain remain.

## Disposition of the requested changes

- **A, end-to-end skeleton: adopt.**  Time-box it to one or two focused days.
  Temporary cheats are acceptable only in an isolated, uncommitted theorem-
  shape probe and must be enumerated; production artifacts remain cheat-free.
- **B, early runtime test: adopt in bounded form.**  First compile and run the
  exact callback/dispatcher outside a full verified rebuild.  Do not spend the
  full R4 cost on a cheated kernel merely to reproduce the already-known
  numerical timing.  If a lightweight faithful branch-hit test is impossible,
  record that as a blocker before R4.
- **C, jobs/topology gate: adopt.**
- **D, default-clock exit criterion: adopt.**
- **E, estimates and caps: adopt**, with actual-versus-predicted logging and
  review at two times the estimate.
- **F, stop-loss: adopt.**  A new representation layer or a two-times overrun
  of the revised proof gates triggers an architecture review rather than
  another appended correction.

The suggested one-kernel-call-per-cell fallback should remain an explicitly
measured fallback, not the default architecture.  It could simplify clock and
callback proofs, but 875 theorem-producing calls and a separate topology fold
may lose much of the intended compact-verdict advantage.

## Schedule conclusion

The audit's **two-to-three calendar week** figure is a reasonable conservative
risk envelope, but it is not yet an evidence-based project estimate because
the whole-call proof closure, exact runtime cone, and new-binary state
construction have not all been measured.

The defensible statement today is narrower:

- G2 is complete; G3 is the active bounded local target, with its generic
  composition, exact 167-instruction prepared-plan/runtime-payload identity,
  all nine ordinary/certificate-consuming joint step adapters complete, and
  the one-cell structural clock discharged, but its concrete runtime/source
  trace and leaf result still open;
- the numerical and analytic architecture has strong positive evidence;
- the first fast theorem remains **0/1**;
- the previous **3--7 focused day** range applies only to the local proof
  composition under assumptions that the audit has shown to be incomplete;
  it is withdrawn as an end-to-end implication; and
- the next reliable first-theorem estimate comes after S0, the whole-call
  contract/clock ledger, and the prepared-state measurement.

This does not imply restarting the NL work.  The current G1/G2 theorems,
partial G3 trace machinery, fixed checker, analytic soundness, old topology machinery, and
original-source adapter remain valuable.  It means the remaining work must
now be managed against the complete chain rather than discovered one boundary
at a time.
