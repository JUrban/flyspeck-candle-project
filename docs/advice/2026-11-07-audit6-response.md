# Response to Audit 6: distinguish the first-case callback from the all-NL runtime

Date: 2026-11-07 UTC

Status: **DEVELOPMENT / NON-RELEASE**

## Verdict

The main scope correction is valid.  The current G5 theorem is generic over
the case-16594 call's certificate bytes, packed cells, jobs, boxes, radii and
runtime certificate values, but it is not generic over arbitrary Flyspeck
nonlinear source programs.  Its checker still authenticates:

- the case-16594 canonical 167-position code/source streams;
- a `875 x 31` certificate header;
- the case-16594 prepared fixed-word program and certificate-packet shape; and
- the corresponding ordinary equation environment.

Consequently, calling this the completed **generic production callback** is
misleading.  The accurate label is **case-16594 callback: payload-generic,
program-fixed**.  It is sufficient for a first-theorem demonstrator, but it
does not satisfy plan v2's all-NL rule that another supported inequality must
not require a changed verified runtime.

The first original fast theorem remains **0/1**.  G6 and G7 remain useful and
non-wasted: they test the exact representation and theorem handoff needed by
either callback scope.  No G8 verified build has started.

## 1. Corrected gate interpretation

The live map should distinguish two gates:

| Gate | Status | Meaning |
|---|---|---|
| G5C. Case-16594 callback | **DONE in HOL4 logic** | Runtime payloads vary, but the authenticated program, header shape and cell count are fixed to case 16594. |
| G5P. Plan-generic callback | **PENDING** | Decode and compile an arbitrary supported versioned source/evidence plan, execute variable-length cells and certificates, and prove the same ordinary-evaluator refinement without changing runtime source. |

G5C does not close G5P.  G6 is currently exercising G5C as a bounded vertical
slice.  G7 is the case-16594 root-to-original-statement adapter.  Neither
authorizes G8 by itself.

Audit 6 is also right that the build-scope choice must be explicit.  My
recommendation is to finish G6 and G7, finish the bounded generalization
discriminator and projection, and then ask the owner to choose between:

1. an 8--10-hour verified build whose new branch proves the first case only;
   or
2. completing G5P first and paying the verified build once for the reusable
   all-NL runtime.

Absent a contrary owner decision, plan v2 makes option 2 the production
default.  A case-only G8 build would be a deliberately labelled demonstrator,
not completion of the production architecture.

## 2. Bounded plan-generic estimate

Important foundations already exist:

- commit `3b1f875aa` supplies the checked source-to-plan compiler, including
  outward fixed-scale rational conversion and exact delta recognition;
- commit `e5d168e7d` supplies its structural compiler induction;
- the subsequent operation, program, packed-cell, G3 and whole-topology
  theorems supply most of the semantic components; and
- the present G5C implementation supplies fail-closed byte decoding,
  streaming matching, topology evaluation and `compute_fast_eval_ok` proof
  structure.

The remaining work is not just replacing three literals with parameters.  It
has four bounded parts:

1. **Definition/translation discriminator (up to 4 focused hours).** Decode a
   versioned supported plan, compile its source program, derive the certificate
   count, and parameterize the header/cell traversal.  The existing case-16594
   fixture must remain byte-for-byte behaviorally green.
2. **Generic trace and ordinary-evaluator refinement (1--3 focused days).**
   Replace the canonical 167-action trace premise with the checked compiled
   program relation, lift the existing instruction and delta theorems over
   that trace, and prove the variable-length clock/result theorem.
3. **Variable topology/header integration (0.5--1 focused day).** Make cell and
   certificate counts checked data, preserve exact job/token lockstep, and
   retain fail-closed rejection of trailing, substituted or inconsistent
   payloads.
4. **Second-family gate and mutations (0.5--1 focused day).** Run a structurally
   distinct genuine supported family through unchanged callback source and
   cover plan, program, header, count, certificate, job and topology
   substitutions.

The planning range is therefore **2--5 focused days after the discriminator**,
with high uncertainty concentrated in part 2.  Each proof iteration remains
under ten minutes where possible; compiled integration probes remain under
30 minutes.  If the first day cannot state and prove one arbitrary compiled
ordinary step through the actual evaluator representation, stop and report
the exact semantic mismatch.  Do not compensate with a verified build or a
new family-specific branch.

The main risk is not byte decoding.  It is whether the existing G3
source/prepared-program semantics can be generalized from the canonical
case-16594 trace to the plan compiler's relation without introducing a second
ordinary evaluator representation.  The discriminator above tests that risk
before any long build.

## 3. Projection status and cheap heuristic

The audit understates the work already completed but correctly identifies the
missing measured part.  The existing sealed inventory has:

- 812 source IDs;
- 7,814 production-selected leaves;
- 30,244 production partition nodes;
- a 24-leaf provisional stratified sample; and
- a summed historical `Iarg_leaf` estimate of **11,367,810 ms = 3.157725 h**.

It does not yet join those leaves to numerical certificate cell counts and
internal topology sizes, and it has not run the matched 20--30-leaf stock
sample.  Those are real open items.  The sample must report cold/reusable
preparation, `Kernel.compute`, theorem handoff, final reconstruction, peak
RSS, unsupported fraction and uncertainty; historical partition depth is not
a substitute for certificate topology.

For the requested rough sanity check, the inventory entry for
`prep-8657368829` records a historical estimate of **1.311 seconds**.  Using
the proved case-10173 stock-route total gives:

```text
480.933 s / 1.311 s = 366.84
366.84 * 3.157725 h = 1,158.4 CPU-hours
```

This is only a heuristic ratio between one unusually well-studied case and
old untrusted C++ sampling coordinates.  It is not a confidence interval or a
corpus runtime forecast.  It nevertheless makes the likely scale explicit
and provides a useful consistency check for the forthcoming stratified
sample.

## 4. Sequencing decision

The accepted near-term order is:

1. finish the bounded G6 executable hit/mutation probe;
2. typecheck G7 and audit the original theorem's assumptions;
3. in parallel, complete the certificate/topology inventory join, matched
   stock sample and one-page projection;
4. run the bounded G5P definition/semantic discriminator and publish the
   resulting effort/risk estimate; and
5. obtain an explicit owner decision on case-only demonstrator versus
   plan-generic production runtime before G8.

This correction does not invalidate G3, G4, G5C, the 875-cell evidence, or the
current G6/G7 work.  It prevents the first case-specific success from being
mistaken for the all-NL runtime architecture.
