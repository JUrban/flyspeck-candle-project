# Response to `2026-09-06-audit2.md`

Date: 2026-09-06 UTC

## Executive response

The audit's principal criticism is accepted.  The project has reached the
point where further work on adversarial checkpoint supervision has lower
expected value than closing the functional path:

```text
current bootstrap -> parser 20/400 -> cheap direct cutpoints ->
complete diagnostic Great 100 -> final bootstrap/S1 -> Flyspeck strata -> S2/S3
```

The fs-verity, ptrace, seccomp, PID-namespace, and mount-projection work is not
being discarded.  It has exposed real lifecycle and identity bugs and now
exists on an isolated, explicitly nonpromotable experimental branch.  The
right prospective decision is to freeze that branch after the already-started
single bounded DMTCP smoke attempt, keep it out of the functional integration
head, and resume it only after the Great-100 and direct-prefix gates are green
or if a concrete functional blocker requires it.

The audit is also right that the project needs two visibly separate
dashboards.  Passing another hundred provenance tests is assurance progress;
it is not a substitute for passing another theorem or Flyspeck action.

There are, however, several factual and sequencing corrections:

* the two independent HOL Light Great-100 reference sweeps are already closed
  at 130/130 and have been independently audited, so they should not be
  launched again;
* G0 is not fully closed because the final Candle head cannot be frozen until
  diagnostic compatibility repairs stop moving it;
* G2 is not a completed runtime gate until the current canonical bootstrap,
  exact schema-6 link, and compiled parser/direct handoff pass;
* d0 and d1 are three- and nineteen-action diagnostic cutpoints, not ordinary
  G4 strata.  Running them once, with a strict time cap, before the 65-target
  Great-100 diagnostic can cheaply reveal shared loader/runtime failures and
  reduce reruns.  They must not become a detour; if they are not cheap, the
  Great-100 sweep takes priority; and
* pausing PFT is a user/owner decision.  The direct lane must not inspect,
  signal, checkpoint, or otherwise control that independent oracle.  Its
  alleged current 40-GiB footprint is not independently established by this
  response.

Subject to those corrections, a functional-first redirect is recommended.

## What the audit gets right

### 1. The marginal priority had become wrong

The recent checkpoint branch developed a much stronger threat model than is
needed to discover the next Candle compatibility failure.  Same-UID pathname
races, task identity across nonleader `exec`, namespace teardown, credentialled
packet transport, and protected publication are legitimate systems questions,
but none tells us whether the current compiled Candle accepts all 65 Great-100
targets or even the first 19 Flyspeck actions.

That work should have been bounded earlier.  The completed task-aware
controller is a reasonable experimental stopping point, not a reason to keep
extending G6 while G3 is open.

### 2. Reproducibility and active-host tamper resistance were conflated

The release path must reliably reject wrong commits, changed input bytes,
stale artifacts, partial results, corrupted checkpoints, skipped actions, and
semantic disagreement.  It does not presently need to claim safety against an
active malicious peer with the same UID and access to the same host.

Those are different threat models.  If an active same-UID adversary is in
scope, ptrace and mount hardening alone do not close the model: the kernel,
dynamic linker, tool executables, filesystem, observer, and output channel are
still trusted.  A credible stronger claim would require an independently
administered protection boundary, not indefinitely more same-UID receipts.

For the current S3 objective, the appropriate development trust model is:

* host kernel, local account, and ordinary tool execution are trusted;
* source commits, all runtime-consumed bytes, compiler/runtime binaries,
  configuration, and generated inputs are content-bound;
* each functional run is fresh and its complete action/theorem/state evidence
  is checked independently;
* stale, malformed, partial, reordered, and corrupted artifacts fail closed;
* active same-UID hostile interference is explicitly out of scope.

The stronger experimental work can later be evaluated as defense in depth,
without silently changing that claim.

### 3. Functional and assurance progress need separate accounting

The governing dashboard should report at least:

| Functional gate | Current state at this response | Next evidence |
| --- | --- | --- |
| Canonical current-head compiler | 16/18 build targets complete; `compiler64Prog` running | validated bootstrap receipt and schema-6 link |
| Parser pilot | sealed 20-input plan, 20 ready, 0 unsupported | 20/20 compiled parse pass plus independent consumer |
| Parser all-inventory | static 400/400 selection check passes; runtime plan deliberately not yet materialized | fresh 400/400 compiled parse pass plus independent consumer |
| Direct cutpoints | d0=3 and d1=19 actions planned, not run | independently consumed diagnostic passes or complete failure sets |
| Great-100 reference | complete | retained audited 130/130 reference authority; no rerun |
| Great-100 Candle diagnostic | implementation prepared, not run | schema-7 65/65 diagnostic pass with complete fingerprints |
| Great-100 S1 | open | final schema-6 runtime, two clean matching runs, independent finalization |
| Ordinary Flyspeck strata | not run on current direct path | sequentially consumed cumulative boundaries |
| Whole Flyspeck S2/S3 | open | two clean matching full runs, nonlinear/LP closure, then resume/corruption matrix |

Assurance work should be reported separately: source/provenance coverage,
negative tests, checkpoint integrity, hostile lifecycle tests, and remaining
trusted boundaries.  Neither table may be summarized as the other.

### 4. Full assurance suites were run too often

Focused tests belong in the inner development loop.  The complete hostile
suite belongs at a merge candidate, a changed shared protocol, or a milestone
handoff.  Repeating every expensive consumer/finalizer regression after small
isolated edits created latency without moving a functional gate.

The proposed rule is:

* edit loop: smallest directly affected tests;
* coherent commit: focused subsystem suite;
* integration/authority change: affected consumers plus cross-boundary tests;
* release milestone: full suite.

Any exception should identify the specific cross-component risk that justifies
the cost.

### 5. The branch and authority model should be simplified prospectively

The suggested three-role model is sound:

1. one functionality integration head;
2. one frozen bootstrap/release head while an expensive replay is active; and
3. experimental side branches with no authority until explicitly reviewed and
   merged.

Existing frozen consumer and historical authority worktrees should not be
destructively collapsed in place.  They remain necessary to validate already
published artifacts.  The simplification should apply to new work and should
retire old roots only through an explicit supersession record.

## Where the audit needs qualification

### 1. The checkpoint work was premature, not wholly irrelevant

The roadmap does require atomic checkpoints, stale-resume rejection,
corruption/reorder tests, relocation, and final-fingerprint equality.  Earlier
checkpoint experiments exposed real problems: incomplete publication,
uncontrolled descendant lifetimes, descriptor inheritance, and path aliasing
can make even an accidental-staleness claim unreliable.

Therefore the lesson is not "checkpoint integrity is unnecessary."  It is:

> implement the minimum integrity needed by an observed functional resume,
> and postpone active-host hardening until functional scale makes the actual
> failure modes measurable.

The current experimental branch should be preserved as a source of later
components, but it should not be merged into or delay the S1/S2 path now.

### 2. Absolute paths should be observations, not portable authority

The audit correctly identifies path coupling as a relocation hazard, but two
uses must be separated:

* During one live execution, resolving an exact canonical root and rejecting a
  symlink/alias swap is a useful run-local check.
* Across machines or relocated worktrees, the durable authority should be the
  repository role, commit, logical relative path, content hash, mode, build
  configuration, binary hash, and semantic fingerprint—not the old absolute
  pathname.

A relocation test may create a new run-local receipt for a new canonical root
and then require identical content and semantic projections.  It should not
need to recreate an obsolete historical absolute pathname.  New schemas should
make this distinction explicit.  Existing result consumers should not be
weakened mid-campaign merely to retrofit portability.

### 3. PFT resource policy requires an explicit authority decision

The audit's prioritization argument is reasonable conditionally: if the PFT
oracle is preventing a functional job from fitting safely, a restartable P1
oracle should yield to the S1/S2 critical path at a verified safe boundary.

This response does not verify or act on the claimed 40-GiB usage.  The direct
lane has an explicit noninterference boundary and must not enumerate, debug,
signal, checkpoint, or stop PFT.  Aggregate host checks during the current
MIPS stage showed ample available memory and no sustained swap traffic, so an
emergency intervention is not established merely by the audit text.

If the user chooses to pause PFT, that instruction should go to its designated
owner, which must use its own authenticated safe-boundary/checkpoint procedure.
The direct lane should consume neither the checkpoint nor any PFT state.

### 4. The independent reference work is already complete

The audit recommends running two HOL Light reference sweeps in parallel.  The
current repository state already records the schema-v9 CSDP reference artifact
`s1-reference-v9-csdp-two-sweep-652a18a-95bb84f` as closed at 130/130 and
independently audited.  Repeating it would spend resources without adding the
missing Candle-side S1 evidence.  The correct next use of that artifact is the
schema-7 diagnostic comparison and, later, final S1 finalization.

### 5. G0 and G2 should not be marked complete yet

Most identities and the selected source closure are pinned, but the final
Candle commit is intentionally not frozen before compatibility triage.  G0 is
therefore nearly complete rather than complete.

The verified Dopen source/proof chain is substantial, but the current compiled
handoff still depends on the in-flight bootstrap, linked-provenance check, and
compiled corpus diagnostics.  G2 remains in progress until those runtime facts
exist.

## Recommended redirect

This is the proposed operating order if the user adopts the audit's
functional-first recommendation.

### Phase A: finish the already-running handoff

1. Let canonical attempt 002 finish without changing its inputs or scheduling.
2. Validate the bootstrap receipt independently.
3. Build and validate the ordinary schema-6 link.
4. Run and consume the sealed 20-input parser pilot.
5. Only on that pass, freshly materialize, run, and consume all 400 parser
   inputs.  The controller must retain the complete ordered failure set rather
   than stop at the first input failure.

Two scope details matter when interpreting that gate.  The controller's
current `7200`-second CPU/wall limits and 1-MiB stdout/stderr limits apply to
each child, not to the profile as a whole.  They are per-input containment,
not a claim that the 400-input campaign has a two-hour global deadline.  The
operator should therefore watch the aggregate run and stop scheduling follow-up
work if observed throughput makes the campaign unreasonable; changing this
host-side controller now would move the Candle head and waste the in-flight
bootstrap.  Also, 400/400 means the exact manifest source-node inventory (90
Candle and 310 Flyspeck source nodes).  The 43 generated inputs are
identity-bound but intentionally outside this parser-only diagnostic; their
consumption belongs to the later direct strata.

### Phase B: obtain one complete compatibility failure batch

6. Run d0 (three actions) and d1 (nineteen actions) only as bounded diagnostic
   reconnaissance.  They do not authorize an ordinary stratum.  If either is
   unexpectedly long, stop scheduling the next cutpoint and prioritize the
   Great-100 diagnostic; preserve any published result.
7. Create the schema-7 transition link at the existing Great-100 candidate
   head and run all 65 targets, continuing after individual failures.
8. Use measured memory and target timings before increasing concurrency.  A
   small measured shard count is acceptable; unmeasured `-j4` or a new build
   architecture is not.
9. Classify the union of parser, d0/d1, and Great-100 failures by root cause.
   Batch repairs and exercise them with the cheapest faithful reproducer.
10. Repeat the complete diagnostic matrix until it is 65/65.  A schema-7 pass
    remains nonpromotable.

The small d0/d1 exception to the audit's literal order is deliberate.  These
are not G4 scale runs; they are already-prepared, very small probes that may
expose a shared base-loader defect before a 65-process sweep.  They receive no
right to delay Great 100 or expand into ordinary strata.

### Phase C: pay the release cost once

11. Freeze the actual final Candle head only after the diagnostic matrix is
    green.
12. Perform a fresh cache-disabled schema-6 bootstrap at that final head.
13. Run two clean full Great-100 Candle executions and the independent S1
    finalizer against the already-closed 130/130 reference artifact.

### Phase D: drive the direct Flyspeck path

14. Run the eight cumulative direct-source strata sequentially, beginning each
    from action zero and consuming each result independently.
15. At each failing boundary, collect the complete available failure set,
    minimize and batch by compatibility class, then rerun the smallest faithful
    prefix before a larger boundary.
16. Record wall time, peak RSS, retained data, and semantic fingerprints as
    functional scale evidence.  Do not add a new provenance schema merely
    because a timing is inconvenient.
17. Close the nonlinear and LP paths in the direct Candle run, including exact
    generated-input/certificate identities and negative mutations.

### Phase E: return to the minimum required checkpoint/release work

18. Once a meaningful cumulative direct boundary exists, implement the
    simplest cooperative checkpoint/resume that provides atomic publication,
    content hashes, boundary identity, stale/corrupt/reordered rejection, and
    final-fingerprint equality.
19. Run the required relocation and resume/corruption matrix under the declared
    trusted-host model.
20. Only then decide whether the experimental fs-verity/PID-namespace design
    materially improves the release claim enough to justify integration.

## Immediate freeze boundary

At the moment this audit arrived, the task-aware namespace experiment had just
completed on isolated branch `codex/flyspeck-v13-pidns-projection` at
`2b0255c`; its focused 12/12 and base OS-authenticator 31/31 tests passed.  One
fresh, harmless, low-thread-count DMTCP 4.1.0 smoke attempt had already been
started.  It has now finished as a retained negative result: the deliberately
short-lived fresh coordinator exited before the projected restart joined it,
so `dmtcp_restart` exited nonzero, the controller rejected the root exit, no
resumed marker was produced, and projection cleanup was empty.  It was not
retried.

An independent static review of the task-aware milestone then found no P0 but
two P1 limitations.  First, the code treated pidfd `fstat` metadata as a unique
process identity even though this host's Linux 6.8 pidfds are created through
[`anon_inode_getfile`](https://github.com/torvalds/linux/blob/v6.8/kernel/fork.c#L2006-L2025)
and therefore share the
[singleton anonymous inode](https://github.com/torvalds/linux/blob/v6.8/fs/anon_inodes.c#L118-L140);
that does not distinguish a stale authority after numeric TGID reuse.  Second,
the outer observer validates packets individually but does not independently
reconstruct the complete process/task lifecycle before accepting the
manager's reported zero-active closure.  The review also noted a fail-closed
process-authority delivery race and the numeric-PID cleanup fallback as P2
limitations.

These findings strengthen the freeze decision.  The branch is an incomplete
diagnostic experiment, not authority.  Its reports must record the findings,
and it must not be integrated, consumed, retried, or extended into another
hardening cycle without a new post-G3/G4 priority decision.

No new checkpoint-security feature, receipt schema, hostile-host mechanism,
cache architecture, or proof-translation optimization should be started while
Phases A and B are open unless it is the smallest demonstrated fix for a
current functional blocker.

## Proposed decision record

If adopted, the redirect can be summarized as follows:

```text
Decision: functional-first until diagnostic Great 100 is 65/65.

In scope:
  current bootstrap/link; parser 20/400; bounded d0/d1; schema-7 Great 100;
  batched compatibility repair; final schema-6 bootstrap and S1; then strata.

Frozen:
  new checkpoint security, same-UID hostile-host hardening, cache architecture,
  x64-only specialization, large-theory splitting, and new assurance schemas.

Already complete and reused:
  the audited 130/130 reference artifact.

Separate owner decision:
  whether PFT should checkpoint and pause at its own verified safe boundary.

Success metric for the next phase:
  parser 400/400 and diagnostic Great 100 65/65, not aggregate test count.
```

## Overall verdict

The audit is substantially correct about priority and should trigger a
prospective redirect, not a project restart.  The direct-source architecture,
verified Dopen work, parser batching, reference authority, and diagnostic
Great-100 transition path are valuable and should be retained.  The recent
checkpoint-security branch should be preserved but frozen.

The best next evidence is functional: a validated current compiler, 400 parsed
sources, 65 matching Great-100 targets, and the first consumed direct actions.
Everything else should be judged by whether it helps reach those facts sooner.
