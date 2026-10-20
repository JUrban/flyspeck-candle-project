# Candle NL first fast theorem implementation plan

Date: 2026-10-20 UTC

Status: **DEVELOPMENT / NON-RELEASE**

## Purpose and success criterion

This plan covers one milestone only: obtain the literal original Flyspeck
case-10173 theorem through the authenticated fast decimal route.  It does not
claim that all nonlinear verification is ready.

The milestone is complete only when one fresh run produces a Candle theorem
whose conclusion is the original case-10173 statement and satisfies all of
the following:

1. the theorem has no additional assumptions and no axiom growth;
2. the unchanged Flyspeck source program, all 4,173 genuine jobs, roots,
   guards, and topology are authenticated;
3. the accepted numerical verdict is produced by the specialized checker,
   not by the generic source evaluator or a precomputed answer;
4. the registered fast-evaluator theorem connects that verdict to ordinary
   Candle compute semantics;
5. the existing analytic, topology, and original-statement adapter derives
   the literal source theorem;
6. an execution trace proves that the fast branch was taken and no generic
   per-cell replay occurred; and
7. preparation, recurring checker execution, decoding, and theorem handoff
   are timed separately.

Until those conditions hold, the project must report **zero literal original
theorems from the fast case-10173 route**.

## Fixed baseline

The following work is already complete and is not part of the estimate below:

- direct Flyspeck source: 297/297 actions green;
- LP: complete and checkpointed;
- case-10173 numerical checker: 4,173/4,173 genuine cells accepted in 7.35
  seconds;
- generic analytic/Taylor soundness and original-theorem adapter;
- registered evaluator seams and the fast `compute_thm` dispatch theorem;
- exact source boxes, roots, source-program shape, packet, and guard
  contracts;
- authenticated source sqrt values and first derivatives; and
- direct source/certificate comparison for all 25,038 coordinate sqrt
  second derivatives, with zero mismatches.

The previously reported 7.14-second “source-contract executable” did not call
the authenticated source-contract checker.  That claim is withdrawn.  The
export now fails closed until work packet 4 below installs a real closed main.

## Critical path

| Packet | Deliverable and exit test | Depends on | Focused effort | Expected build/run elapsed | Risk |
|---|---|---|---:|---:|---|
| 1. Exact sqrt-Hessian bridge | HOL accepts ordered endpoint selection, normalization-invariant product identity, negative outward conversion, and the registered `q_dim_jet_sqrt_dd` result | fixed baseline | 3–8 h | 1–3 h across focused rebuilds | medium |
| 2. Six-coordinate source composition | The real sqrt instruction for each of six coordinates evaluates to the authenticated decimal result from a clean prepared state | packet 1 | 4–10 h | 1–4 h | medium |
| 3. Genuine 4,173-job recursion | The authenticated generic item theorem folds over the unchanged complete job/root streams and yields the checked-jobs verdict | packet 2 | 3–8 h | 1–4 h | medium |
| 4. Real fast execution boundary | A closed exported checker consumes the actual authenticated source jobs and roots, takes the registered fast branch, rejects mutations/truncation, and returns acceptance | packet 3 | 4–12 h | 2–6 h including translation/export | medium-high |
| 5. Literal theorem handoff | Existing source/topology adapter consumes packet 4's assumption-free equality and yields the original theorem; digest, assumptions, axioms, path, time, and memory are recorded | packet 4 | 2–6 h | 1–3 h | low-medium |

These are engineering ranges, not promises.  They include expected local
proof correction cycles but not a new architectural mismatch.

The resulting aggregate estimate from the current state is:

- optimistic: 16 focused hours plus builds, about 2–3 calendar days;
- working estimate: 25–40 focused hours plus builds, about 4–7 calendar days;
- high-confidence allowance: up to 7–10 calendar days.

If another source/packet semantic mismatch is found, these estimates become
invalid.  The project will preserve the reproducer, report the exact failed
contract, and re-estimate before extending the architecture.  It will not
continue describing the theorem as imminent.

## Packet 1: exact sqrt-Hessian bridge

### Subgoals

1. Prove that multiplication of two ordered positive rational intervals
   selects lower/lower and upper/upper from the four endpoint products.
2. Prove that rational normalization preserves the endpoint order and product
   identity, independently of the GCD selected by the unchanged source.
3. Prove that conversion of the negative reciprocal product gives exactly the
   authenticated packet reciprocal with endpoints negated and reversed.
4. Compose those lemmas with the registered evaluator theorem for
   `candle_cv_q_dim_jet_sqrt_dd`.

### Exit test

A parameterized theorem evaluates
`fs_interval_of_q (q_dim_jet_sqrt_dd root input)` to the decimal object for
`bounded_interval64_neg reciprocal` from the authenticated direct endpoint
contract.  No case-10173 closed arithmetic and no generic evaluator replay
may occur in the theorem.

### Current state

The four proof layers are drafted.  A bounded dependency rebuild is in
progress after an exploratory foundational build changed a HOL theory
identity; source bytes were restored.  Drafts do not count as complete until
their focused HOL builds pass.

## Packet 2: six-coordinate source composition

### Subgoals

1. Combine the already-green sqrt value and first-derivative results with the
   packet-1 second-derivative result.
2. Discharge source sqrt domain/nonzero guards from the authenticated packet.
3. Connect the derivative and Hessian intervals to the existing compact
   decimal sqrt trace.
4. Prove the recursive six-certificate prefix theorem once, then instantiate
   it for each job rather than duplicating six closed proofs per cell.
5. Rebuild the authenticated historical-item/program theorem on that generic
   result.

### Exit test

For an arbitrary authenticated case-10173 packet, the literal source sqrt
instructions evaluate to the bounded object result used by the specialized
checker.  The first and last genuine records are instantiated as regression
tests, and at least one mutated certificate is rejected.

## Packet 3: complete job recursion

### Subgoals

1. Feed the generic item result into the already-proved ordinary-prefix and
   source-program trace.
2. Produce the checked-job head contract from the exact program result and
   final Taylor verdict.
3. Apply the existing recursive theorem to the complete 4,173-record job and
   root streams.
4. Confirm exact stream consumption: no missing, extra, reordered, or trailing
   record is accepted.

### Exit test

An assumption-free theorem states that the complete authenticated case-10173
checked-jobs call returns acceptance on the unchanged evidence.  Truncated,
extended, byte-changed, and root/job-misaligned fixtures reject.

## Packet 4: real registered fast execution

### Subgoals

1. Replace the current fail-closed placeholder main with a closed call that
   supplies the actual authenticated source jobs, historical roots, program,
   and packed certificates.
2. Register the exact equation-set and call identity expected by the existing
   fast `compute_thm` seam.
3. Prove the specialized result refines the ordinary compute result for that
   schema.
4. Export with `./cake`, run the unchanged full payload, and record branch
   selection, decode time, checker time, and memory.
5. Run focused adversarial mutations at each authenticated input boundary.

### Exit test

The exported program accepts the exact full evidence through the authenticated
checker, rejects the mutation suite, and records a registered fast-branch hit.
No call to the generic per-cell evaluator appears in the production trace.

The initial performance gate is deliberately generous: complete recurring
execution should remain below 60 seconds and theorem handoff below five
minutes after reusable preparation.  Missing either target does not invalidate
soundness, but it blocks the “fast production route” claim and triggers a
measured performance review before broader rollout.

## Packet 5: original theorem and audit record

### Subgoals

1. Invoke the existing analytic and topology theorem on the complete accepted
   source verdict.
2. Apply the existing literal original-statement adapter.
3. Compare the conclusion identity/digest with the original Flyspeck theorem.
4. Record assumptions, axiom delta, fast-branch evidence, all timings, peak
   memory, source/runtime commits, and immutable fixture identities.
5. Repeat once from a clean prepared state to rule out accidental dependence
   on a partial failed session.

### Exit test

Two clean executions produce the same assumption-free literal theorem and
the same semantic evidence, with the registered fast branch taken both times.

## Control rules

- “Close to the first fast theorem” is no longer a progress metric.  Reports
  will name the last completed packet and the exact failing exit test.
- Each packet is capped at twice its working estimate.  At that point the
  lane pauses for a written root-cause review and revised estimate.
- A newly exposed source/packet mismatch stops composition at that boundary;
  it is not patched with an unauthenticated alias or precomputed answer.
- Focused proof builds and saved stable prerequisites are used during edits.
  The full 4,173-job run occurs only at packet 3 and later integration gates.
- Preparation, recurring execution, and theorem handoff are always reported
  separately.
- No all-NL schedule will be inferred from case 10173.  After this milestone,
  a second structurally different genuine family is the next estimation gate.

## Beyond the first theorem

All-NL still requires a representative second family and coverage or a
faithful fallback for 250 selected `hminus`, 42 selected `matan`, and five
selected inverse-trigonometric leaves.  Prepared source-language coverage is
currently 7,517/7,814 selected leaves (96.2%).  A credible all-NL effort
estimate will be made only after the first fast theorem and that second-family
run reveal how much of packets 1–4 is genuinely reusable.
