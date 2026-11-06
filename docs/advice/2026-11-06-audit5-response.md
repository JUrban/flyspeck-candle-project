# Response to Audit 5: stop the redundant exact lift and measure the stock route now

Date: 2026-11-06 UTC

Status: **DEVELOPMENT / NON-RELEASE**

## Verdict

Both course corrections are accepted.  The first is a genuine sequencing
error in the current work, and the second corrects a factual error in the gate
map and the Audit 4 response.

The first fast original Flyspeck NL theorem remains **0/1**.  Direct Flyspeck
remains **297/297** and LP remains complete and checkpointed.

## 1. The closed 875-cell HOL4 lift is not a production gate

The audit's reading of the post-G3 architecture is correct.

The generic theorem in CakeML/HOL4 commit `63ee21818` is quantified over
arbitrary valid runtime/semantic radii, center and outer boxes, certificate
packets, successful fixed-word traces, and accepted results.  It derives the
ordinary production-entry evaluation; it contains no genuine cell constant.
Commit `ddeb76b1e` identifies the generic 167-action code/source payload with
the canonical case-16594 dispatcher payload.

Therefore the production callback should:

1. authenticate/decode the four payload roles of the actual whole call;
2. execute the fixed checker on those runtime payloads;
3. use G3 generically for each accepted cell and the generic jobs/topology
   theorem for the complete structured result; and
4. expose that result through a generic `compute_fast_eval_ok` proof.

It does not need a separately saved closed HOL4 theorem for every genuine
cell.  The complete verdict consumed in HOL Light is produced by
`Kernel.compute` through that callback.

The exact lift is stopped at committed cells 0--348: **349/875 (39.9%)**.  It
was not valueless.  The distinct genuine instances found a converter-theory
identity conflict and a stale non-clock-aware helper, and they provide a
substantial regression oracle for G3.  But no current production decision
depends on extending it, so it is now classified as **PARKED / NON-GATING**.
The next cells' data-only theories were built before this review completed;
their authentication was not launched and they are not counted as evidence.

The corrected first-theorem sequence is:

1. G4: instantiate the generic HOL Light whole-jobs/topology theorem on the
   genuine 875 packed cells, 875 jobs, and 1,749 tokens; prove the lockstep
   geometry contracts and singleton root identity.
2. G5: implement the plan-driven runtime-payload callback and prove
   `compute_fast_eval_ok` from G3 plus generic whole-list/topology composition.
3. G6: compile and run the exact callback with hit, role mutation, truncation,
   and topology/source substitution tests.
4. G7: typecheck the existing case-16594 root-to-original-statement adapter.
5. Only after those gates pass, preflight and launch one frozen verified
   runtime build.

The exact-identity cell-0 witnessed callback remains useful vertical-slice
evidence.  It is explicitly not the production design.

## 2. The v3.15 baseline was misclassified and mismeasured

Audit 5 is correct here as well.  The proved v3.15 run used a general
fixed-nonlinear checker with ordinary untrusted boxes, certificates, and
topology under general soundness theorems.  On the genuine 4,173-cell
case-10173 certificate it measured:

| Phase | Wall time |
|---|---:|
| complete numerical/topology `Kernel.compute` | 434.364 s |
| theorem handoff | 46.468 s |
| final source reconstruction | 0.101 s |
| through exact source theorem | **480.933 s** |

Peak sampled RSS was about **17.15 GiB**.  The 401.740-second number was the
earlier unproved raw-only run.  The gate map and Audit 4 response are corrected
accordingly.

This establishes a credible general fallback/reference route, but one case is
not a corpus projection.  Case 10173 has 4,173 numerical cells inside one
production leaf; the complete corpus has 7,814 selected production leaves and
widely varying certificate forests.

## 3. Projection lane starts now

The build capacity released by parking the per-cell lift is reassigned to a
bounded stock-route projection.  Existing sealed evidence already supplies:

- 812 source IDs and 771 formula digests;
- 23,242 serialized parameter records;
- 7,814 selected production leaves;
- expanded-language support for 731 source IDs / 7,517 selected leaves; and
- 297 structural residual leaves: `hminus` 250, `matan` 42, and five
  `asn`/`acs`/`arc_hhn` leaves.

Those are language/inventory counts, not certificate-size or runtime data.
The bounded work packet is:

1. Join each selected inequality with source family, chosen disjunct,
   certificate numerical-cell count, and topology-token/depth size.
2. Audit the stock checker against the prepared instruction families.  Record
   separately unsupported source normalization (`hminus`, `matan`, `asn`,
   `acs`, `arc_hhn`) and any missing numerical operations or delta shortcuts;
   do not infer one from the other.
3. Select about 20--30 inequalities stratified by family, numerical-cell
   count, topology size, and residual-operation class.
4. Measure reusable/cold preparation, recurring `Kernel.compute`, theorem
   handoff, final reconstruction, and peak RSS for every sample.
5. Publish a one-page projection with weighted CPU-hour and per-process-memory
   estimates, uncertainty intervals, unsupported workload fraction, and the
   decision whether the fast route is required for all NL or primarily for
   high-cost families.

The lane is capped at **1--2 focused days**, mostly unattended.  It must not
delay bounded G4/G5 proof work and must not turn a partial supported-family
sample into an all-NL claim.

## 4. G8 build estimate

The old 20--36-hour figure is withdrawn.  The next preflight starts from the
externally reported **8--10-hour** stock CakeML build from a fresh checkout.
The exact local callback/runtime closure may differ; the preflight must explain
that difference from the build graph and measured cache state before one
frozen production build is authorized.

## Immediate state change

- exact per-cell lift: **PARKED at 349/875; NON-GATING**;
- production first-theorem lane: **G4 real-data representation/root
  instantiation + G5 generic runtime-payload callback**;
- projection lane: **STARTED from existing sealed corpus inventories**;
- verified runtime rebuild: **still forbidden until G4--G7 and the measured
  preflight are green**.
