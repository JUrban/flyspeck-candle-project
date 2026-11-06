# Response to Audit 4: preserve the vertical slice, expose the remaining integration risk

Date: 2026-11-05 UTC

Status: **DEVELOPMENT / NON-RELEASE**

## Post-audit generic whole-call closure (2026-11-06 UTC)

The audit's warning about the 875-leaf/topology lift has now been reduced to a
bounded real-data instantiation, but it is not yet closed.  Candle/HOL Light
commits `abd5726e` through `5bcce532` prove the following reusable chain:

- the generalized topology contract from the replay invariants;
- certificate-erased source identity for any two successful executions of the
  same planned 167-action program, including all ordinary, polynomial, and six
  specialized instruction families;
- one `m_cell_pass` theorem for every exact accepted packed job;
- lockstep recursion over packed cells and topology jobs, with length mismatch
  and any per-job result other than exactly `Cexp_num 1` rejected; and
- root `m_cell_pass` from a successful complete numerical/topology call.

The diagnostics-free proof probe took 113 seconds from the authenticated
prepared checkpoint and introduced no runtime rebuild or cumulative Flyspeck
replay.  Its checkpoint SHA-256 was
`5d69e6e41e3603e72b1a74d65d72a83be88e5e912f42849a42f16e204e9003db`;
the exact four-source set SHA-256 was
`a5e0c2e2c3ab116cef00994e5fc5707b4d715c1f1dc183e7931c51074a2c2f27`.

This materially answers the audit's concern that topology might conceal an
unbounded new mathematical proof.  It does **not** yet close G4 or produce the
original theorem.  The remaining G4 obligation is to instantiate the generic
theorem on the authenticated 875 packed cells, 875 jobs, and 1,749 topology
tokens, prove their lockstep input contract, and establish the exact singleton
root returned by that genuine whole call.  The public metric remains first
fast original theorem **0/1**.

## Post-audit arbitrary-cell leaf closure (2026-11-06 UTC)

The audit's cell-0-versus-arbitrary-cell warning has now been discharged at
the logical G3 boundary.  HOL4/CakeML commit `63ee21818` proves, for arbitrary
valid runtime and semantic radii, center and outer boxes, packet contracts,
and accepted packed result, that the actual object-dispatch entry evaluates to
`M_success (Num 1)` under its structural clock bound.  Its clean focused build
took 1m47.71s and peaked at 2,636,380 KiB RSS.

Commit `ddeb76b1e` then proves by exact evaluation that the generic complete
167-action code and source payloads are the canonical case-16594 dispatcher
payloads.  That clean build took 1m48.99s and peaked at 4,108,892 KiB RSS.
Together with the existing generic HOL Light entry-success theorem, these
results turn every accepted entry satisfying the correspondence and plan
premises into the required `m_cell_pass` leaf theorem.  The proof is no longer
specialized to the genuine cell-0 constants.

This closes **G3**.  It does not prove the 875-leaf/1,749-token topology
composition, install the callback in a rebuilt Candle runtime, or produce the
original Flyspeck theorem.  **G4 topology is now the active gate**, and the
public first-fast-original-theorem metric remains **0/1**.  No runtime rebuild,
verifier prefix, or hour-scale run was used for this closure.

## Post-audit arbitrary 167-step trace closure (2026-11-06 04:20 UTC)

The most important cell-0 qualification in the audit is now resolved at the
trace level.  HOL4/CakeML commit `3454acc3f` proves
`bounded_case16594_object_joint_complete_trace` for quantified runtime radii,
semantic radii, center and outer boxes, word state, semantic state, runtime
stack, certificate trace, and packet contracts.  It is not a replay theorem
specialized to the genuine cell-0 constants.  Its companion identity theorem
proves that the assembled 167 source and prepared instructions are exactly the
canonical case-16594 programs and that the remaining suffix is empty.

This closure was reached in seven small commits: the three generic specialized
pairs, then cumulative boundaries through actions 35, 78, 121, and 166.  The
clean final theory build took 1m47.62s and peaked at 2,800,704 KiB RSS.  No
runtime rebuild, verifier prefix, or hour-scale run was used.

This closes the arbitrary-input **G3e trace**, but not the whole G3 exit
criterion.  Follow-up commit `cc4444c85` now also proves the accepted-result
endpoint: an accepted fixed-word singleton yields the six-field packed runtime
object and its semantic source-accept contract.  Its clean focused build took
1m50.85s and peaked at 3,508,292 KiB RSS.  The failure found before that build
was only a missing unfold of the singleton list encoding; it was isolated and
repaired in the restored HOL proof session, without extending a timeout.

The generic HOL Light theorem that turns such a successful entry into
`m_cell_pass` already exists, but the exact HOL4-to-entry handoff and final
composition are not yet committed.  Topology G4, whole-call callback/clock
composition, the verified runtime, and the original theorem remain open.  The
public metric is still **0/1**.

## Post-audit tight-box closure (2026-11-06 UTC)

The concrete cell-0 callback chain has now been regenerated around the one
outer box that satisfies both sides of the contract.  The previously guarded
box passed the numerical checker but exceeded the analytic Taylor radii; the
unguarded box missed one exact source endpoint.  The repaired box changes only
the required coordinate-5 upper endpoint.

The tight fixture now has all of the following green on the frozen source
branches: exact source and radius correspondence in HOL Light, the complete
167-step fixed checker and 134-packet ledger, the full HOL4 semantic/callback
closure, independent equality to the regenerated HOL Light constructor term,
translation, and a directly compiled standalone callback executable.  The
executable compiled in 2.56 seconds, linked in 0.32 seconds, and exited zero
immediately with empty output.  Details and artifact hashes are in
`docs/progress/2026-11-06-v4.365-nl-tight-outer-box-bridge.md`.

This materially reduces the concrete vertical-slice integration risk, but it
does not change the public first-theorem metric: **0/1**.  The callback is not
yet installed in a Candle runtime, and arbitrary-cell generalization,
875-cell topology, and the original theorem remain open.  No runtime rebuild
or hour-scale run was started.

## Post-audit executable-probe result (2026-11-06 01:28 UTC)

The exact cell-0 callback has now passed its standalone pre-bootstrap
executable probe.  CakeML/HOL4 commit `be56fc840` repairs the supposedly
literal entry so its executable definition contains constructor data rather
than latent payload assemblers, translates the exact callback over the small
`mlbasicsProg` state, and exports a closed program.

The linked program exited zero after checking the exact hit, an altered
equation-environment miss, six independent entry-argument mutations, a wrong
entry root, and unchanged fallback behavior.  Direct `cake` compilation took
2.20s, linking 0.26s, and execution less than 0.01s.  The source, measurements,
artifact identities, and bounded failures are recorded in
`docs/progress/2026-11-06-v4.364-nl-authenticated-fast-callback-executable-probe.md`.

This result closes the audit's bounded pre-bootstrap representation question.
It still does **not** install a changed Candle runtime, establish an
arbitrary-cell callback, close 875-cell topology, or produce the original
Flyspeck theorem.  The public metric therefore remains first fast original NL
theorem **0/1**.

## Post-audit frozen-chain update (2026-11-06 00:53 UTC)

Two further bounded source commits address the audit's concern that a cheap
compiled probe could be confused with an installed Candle runtime:

- `9f5c3cebe` proves a small generic callback-prepend theorem, including exact
  hit, miss/fallback, and conditional `compute_fast_eval_ok` preservation; and
- `86e27ade9` evaluates the authenticated semantic entry once to a literal
  `compute_exp`, proves the literal identical to that entry, and defines the
  exact literal callback that the pre-bootstrap probe will compile.

Both theories cleanly rebuilt in under two minutes (1m50.44s and 1m51.69s),
with peak RSS 3,615,584 KiB and 3,614,424 KiB.  They do not install a changed
runtime and do not close arbitrary-cell G3 or topology G4.

The first attempt to prepare the standalone `basisProg` executable probe
exposed abandoned HOL build locks and was stopped rather than allowed to wait
silently.  After removing only locks owned by the verified-dead process, a
bounded resume completed 23 of 44 missing generic CakeML translator/basis
theories before the remaining 18-minute cap fired.  It peaked at 2,230,692
KiB RSS.  The reusable prerequisites remain built, but the project-specific
probe itself has **not** yet been compiled or run.  This is therefore recorded
as incomplete one-time preparation under cap, not as callback evidence and not
as a checker failure.  No timeout extension, Candle rebuild, or Flyspeck replay
was started.

## Post-audit entry/callback update (23:53 UTC)

The complete cell-0 trace has now crossed two more bounded integration
boundaries on the isolated HOL4/CakeML branch:

- `77773c9c7` proves the structural dispatcher-entry control semantics and
  instantiates them for a **new exact entry expression containing the checked
  fast certificate stream**; and
- `b0467f294` registers a fail-closed fast evaluator for exactly that equation
  environment and entry expression, with `compute_fast_eval_ok` proved from
  the complete evaluator result.

The entry proof cleanly rebuilt in 1m45s with 2,974,800 KiB peak RSS.  The
registration proof rebuilt in 1m47s with 2,872,396 KiB peak RSS.  Neither
build replayed the numerical checker, rebuilt Candle, or ran a verifier
prefix.

This boundary caught and resolved an important representation issue before a
runtime investment: the older exported entry embeds the legacy 134-item
certificate field, while the successful trace consumes the distinct checked
fast certificate stream.  The proof therefore does not attach the fast result
to the old entry by aliasing the two lists.  It defines and authenticates a
fresh entry whose exact bytes match the proved result.

This is still a **cell-0 vertical-slice callback**, not the arbitrary-cell G3
exit criterion, the generic whole-call G5 callback, or a callback installed in
a rebuilt Candle runtime.  It also does not close G4 topology.  The public
metric remains first original theorem **0/1**.

## Post-audit progress update (22:17 UTC)

The audit and the initial response were written while the authenticated
cell-0 trace was still being assembled.  Since then, the isolated HOL4/CakeML
proof branch has completed and cleanly rebuilt the entire **167/167-action
joint trace for genuine cell 0**.  The five new source commits are:

- `96d5735da`: ordinary actions through 76;
- `0621c40eb`: the second specialized pair, actions 77--78;
- `4bb05651b`: ordinary actions through 119;
- `a4c34d164`: the final specialized pair, actions 120--121; and
- `9cff95635`: the ordinary tail through action 166.

The final theorem,
`bounded_case16594_cell0_authenticated_object_prefix0_through166_trace`,
jointly carries the authenticated fixed-word certificate state, exact-object
semantics, production evaluator state, and all six specialized delta actions.
The five clean focused builds took 1:46--1:57 each and peaked between 2.88 and
4.15 GiB RSS.  No long runtime build or cumulative replay was used.

This materially advances G3d/G3e for the concrete vertical slice, but it does
**not** close G3.  The theorem is still specialized to cell 0.  The next proof
boundary is the exact dispatcher-entry/result handoff for that trace, followed
by the reusable arbitrary-accepted-cell leaf theorem (G3f).  The 875-job,
1,749-token topology composition remains G4, and the first fast original
Flyspeck NL theorem remains **0/1**.

## Executive assessment

Audit 4 is useful and mostly directionally correct.  Its most important
warnings are:

1. preserve the typechecked whole-call skeleton rather than leaving it in an
   untracked worktree;
2. do not confuse the genuine cell-0 vertical slice with the arbitrary-cell
   G3 exit criterion;
3. treat the generalized topology proof as a real, potentially material G4
   obligation; and
4. do not describe a cheap pre-bootstrap executable probe as though it were a
   newly installed Candle runtime.

Those points change the working record.  The two whole-call skeleton sources
have now been committed on their isolated Candle branch as `0ad3bf38`.  The
live gate map is also being tightened so that the cheap G6 activity is a
**pre-bootstrap callback/dispatcher probe**, while the first actual runtime
containing the changed kernel remains in G8 and requires the verified build.

The audit is not fully current.  It inspected the HOL4/CakeML proof branch
through `91bc66d0e` at 17:23 UTC.  The Audit 3 response was committed at 17:43
UTC (`6c883ad` in the project repository), and the source branch subsequently
added the generic certificate-free join (`fd56a5670`) and the proof that the
fast and legacy certificate payloads are distinct (`5b4117f84`).  The statement
that the Audit 3 response was absent and that no relevant source commits had
landed since November 3 therefore describes the audit's snapshot, not the
current repositories.

At the time of the initial response, the public result was:

- direct Flyspeck: **297/297**, green and checkpointed;
- LP: complete and checkpointed;
- fixed numerical checker: **167/167 instructions**, **875/875 cells**;
- first original Flyspeck NL theorem through the fast route: **0/1**;
- highest closed logic gate: **G2**;
- active gate: **G3**.

The post-audit updates above supersede only those last two gate labels: G3 is
now closed and G4 is active.  The result metric remains **0/1**.

No runtime rebuild or hour-scale run is justified yet.

## Response to the six findings

### 1. The skeleton was not committed

Correct.  The report accurately named a process hazard: two files had passed a
109-second prepared-state typecheck but remained untracked in
`codex/fast-nl-object-entry-v1`.  That made the evidence reproducible only by
the surviving worktree and repeated the preservation failure criticized in
Audit 3.

The exact recorded files are now committed as `0ad3bf38`:

- `candle/cv_compute_analytic_expr_packed_source_object_whole_compute.ml`;
- `candle/cv_compute_analytic_expr_packed_source_object_whole_skeleton_sound.ml`.

Their source hashes remain:

- whole executable: `2cce4f9ad828ef2e83379a85f0fbd8b50228e64f02b3afea1c99741d70808f76`;
- conditional skeleton: `3f5e26c2ec1962dc8f2473eecd8711290e7522cd037d12dcfbb21d205650adcd`.

This preserves the Candle half of S0; it does not complete the generalized
topology theorem or the HOL4 callback/clock half.

The claim that the "Candle repo has no commits since Nov 3" needs a repository
qualification.  It was true of the separate Candle skeleton branch before
`0ad3bf38`.  It was not true of the active HOL4/CakeML proof worktree, where the
`candle/prover/compute` theories had many scoped commits on November 5.

### 2. G6 must not imply a cheap changed-kernel runtime

Correct in substance.  Direct `./cake` compilation is a valuable executable
prototype route for the checker and callback representation.  It does **not**
install a modified callback into the trusted Candle kernel, does not exercise
the final `compute_fast_eval_ok` theorem in a new Candle process, and does not
remove the verified bootstrap requirement.

The useful distinction is therefore:

- **G6: pre-bootstrap callback/dispatcher probe.**  Freeze the exact callback
  source and exercise its four payload roles, branch selection, and mutation
  failures through the lightest faithful compiled representation.  This is a
  bounded bug-finding gate, not a runtime claim.
- **G8: verified build, actual runtime, and prepared state.**  Build the new
  kernel/runtime from the frozen bytes, then reconstruct a compatible state.

Merging the two concepts would lose a useful cheap gate, but calling G6 a
"development runtime" was misleading.  The live map now uses the first
wording.  The structural one-cell evaluator bound is already known:
**524,741 ticks**, below the default **1,000,000,000**.  The whole-call callback
bound remains to be proved.

### 3. Topology is still open

Correct.  The executable layout and conditional contract establish that the
numerical and topology halves consume the same job value.  They do not yet
prove that the 1,749-token run combines the new explicit-radius leaf theorems
to the authenticated singleton root.

The older compact topology invariant is strong evidence and reusable
machinery, but its immediate premise is the legacy per-job accept predicate.
The new generalized theorem must replace that premise with the exact leaf
`m_cell_pass` facts.  The earlier attempt was stopped because its proof became
tactic-fragile; it was not proved impossible and it must not silently remain
parked.

The sequence remains deliberate: finish the bounded G3 step/trace theorem now
in progress, then make G4 topology the next proof lane before callback or
bootstrap work.  A topology failure changes the estimate; it may not be hidden
as "one more adapter."

### 4. Cell 0 is evidence, not the arbitrary-cell exit criterion

Correct.  Current evidence has three different levels that must remain
separate:

1. the genuine cell-0 data, fixed-word execution, and 134-field packet ledger;
2. generic per-instruction semantic/evaluator theorems whose inputs are
   quantified; and
3. the still-open trace theorem for an arbitrary accepted explicit-radius
   cell, followed by the 875-cell batch/topology composition.

The cell-0 ledger is intentionally the first vertical slice because its first
ten operations exercise polynomial, pi-half, square root, inverse,
multiplication, and arctangent before the first specialized delta.  It catches
representation and certificate-cursor errors cheaply.  It does not close G3.

The current finite G3 checklist, updated after the audit snapshot, is:

| Subgate | Status on this response | Exit criterion |
|---|---|---|
| G3a. Cell-0 semantic source result | **DONE** | Exact 167-step fixed-word result, exact-object analytic meaning, and source acceptance. |
| G3b. Unified general-code joint step | **DONE** | One theorem joins all nine ordinary/certificate-consuming families while preserving the packet suffix. |
| G3c. Specialized delta joins | **DONE** | Six generic delta adapters, three positive and three negative. |
| G3d. Authenticated concrete prefix | **DONE FOR CELL 0** | The genuine trace crosses every general family and leaves the exact expected states and packet suffix. |
| G3e. Full 167-step joint trace | **DONE GENERICALLY** | The quantified complete trace covers all 167 canonical actions, all six specialized positions, runtime refinement, semantic evaluation, and packet contracts. |
| G3f. Arbitrary-cell leaf theorem | **IN PROGRESS** | The accepted-result runtime/source endpoint is done; the exact HOL4-to-entry handoff and composition to `m_cell_pass` remain. |

No G3 completion claim is permitted at G3a or G3d.

### 5. Per-gate estimates, caps, and actuals were too coarse

Correct.  The earlier **3--7 focused days** label is a risk range for a group
of proof gates, not a controllable execution plan.  It should not be used as a
delivery promise.

The working controls are now:

| Work packet | Planning effort | Individual feedback cap | Escalation rule |
|---|---:|---:|---|
| G3b--G3d joint step and prefix | 0.5--1.5 focused days | 3 minutes per exact theory build | Reduce to the failing family/position before any longer run. |
| G3e--G3f trace and leaf | 1--3 focused days | 10 minutes for a bounded concrete trace; 3 minutes for local theorem edits | If the induction needs a new invariant, revise G3 before extending the timeout. |
| G4 topology adapter | 1--3 focused days, high uncertainty | 10 minutes per focused proof probe | After one focused day without a stable invariant, publish the exact failing goal and re-estimate. |
| S0 HOL4 callback skeleton and G5 | 1--3 focused days after G3/G4 shapes stabilize | 10 minutes for callback/clock probes | Any payload-shape change returns to S0; no bootstrap. |
| G6 pre-bootstrap executable probe | 0.5--1 focused day | 30 minutes per exact compiled integration probe | A fallback branch or representation mismatch blocks G8. |
| G7 original-statement adapter | 0.5--2 focused days | 10 minutes per focused handoff probe | New mathematics, assumptions, or axiom growth forces a plan revision. |
| G8 verified build/runtime | old measured planning range 20--36 elapsed hours, to be re-preflighted | one frozen build attempt only | No start until G3--G7 and exact source closure are green. |
| G8 prepared state and G9 fresh run | not yet responsibly estimated | measured preflight required before launch | Do not reuse an old-binary checkpoint as evidence for the new runtime. |

Actual elapsed time and peak RSS remain required in each completion report.
These figures are engineering estimates, not guarantees.

### 6. The existing case-10173 result should be an explicit baseline

Useful correction, with an important terminology distinction.  The project
does already have an original case-10173 theorem through a fixed nonlinear
route.  The complete 4,173-cell numerical certificate was measured at
**401.740 seconds** in v3.10, and the later handoff produced the original
theorem without hypotheses or axiom growth.  That deserves an explicit place
in the gate map as a fallback/reference baseline.

It is not the generic stock rational evaluator that failed on the case-16594
prefix after about eight minutes and 16 GiB.  The installed runtime contains a
case-10173-specific fast branch.  Extending that architecture with one branch
per inequality is precisely the non-scalable route rejected by plan v2.

An all-NL CPU-hour estimate cannot honestly be obtained by multiplying one
case-10173 wall time by the paper's roughly 23,000 inequalities.  The units do
not match: case-10173 itself contains 4,173 subdivided cells, while the 23,000
figure counts formal inequality tasks whose certificate sizes and expression
families vary.  Two deliberately naive normalizations illustrate the problem:

- 23,000 copies of the complete 401.740-second certificate would be about
  **2,567 CPU-hours**; but this assumes every inequality is a case-10173-sized
  certificate.
- 23,000 cells at case-10173's mean numerical rate would be under one CPU-hour;
  but this incorrectly treats every paper-level inequality as one comparable
  cell and excludes preparation/handoff.

Neither is a forecast.  A defensible projection needs an inventory grouped by
source program/family, cell count, and topology size, followed by a small
representative batch on the same runtime.  That projection is useful before
G8, but it must not interrupt the current G3/G4 theorem path or be presented as
proof that the case-specific route scales.

## What the audit changes in the plan

The immediate sequence is now explicit.  Steps 1--4 below are complete both
for the concrete cell-0 vertical slice and for the reusable quantified
167-action/accepted-entry path.  Step 5 is the current boundary:

1. finish and commit the unified general-code step theorem;
2. prove the genuine 0--9 prefix;
3. scale the induction through all 167 positions, including the six known
   specialized deltas;
4. obtain the arbitrary-cell `m_cell_pass` leaf theorem;
5. immediately resume the generalized topology proof against the now-committed
   whole-call skeleton;
6. typecheck the HOL4 callback/clock skeleton and freeze the exact callback;
7. run the bounded pre-bootstrap branch/mutation probe;
8. only then authorize one preflighted verified build and compatible-state
   reconstruction.

This is finite but not yet a calendar claim of "close."  Audit 4's suggested
two-to-three-week outcome is a plausible risk scenario, not a result supported
by completed G4--G9 evidence.  The honest public status remains **first fast
original theorem 0/1** until the literal theorem is produced.
