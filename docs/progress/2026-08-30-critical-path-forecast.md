# Whole-Flyspeck critical-path forecast (2026-08-30 03:12 UTC)

> Historical forecast snapshot.  Its `586e...` head and 48/130 sweep count
> have been superseded.  Current launch dependencies and live counts are in
> `2026-08-30-v1.3-parser-gate-readiness.md`.

## Scope

Yes: the governing target is a whole pinned Flyspeck S3 check by direct
compiled CakeML/Candle source execution, including nonlinear and LP evidence.
The concurrent HOL Light-to-PFT run is retained as a P1 oracle and differential
cross-check; completing it is not the meaning of "Candle checks Flyspeck" and
cannot close S2 or S3.

Two milestones must therefore be distinguished:

1. a linked Candle usable for the exact 20- and 400-source parser diagnostics;
2. a release-qualified whole-Flyspeck S3 result with direct execution,
   nonlinear/LP closure, two identical clean runs, and one matching resume.

## Measured critical path

The active exact proof replay is pinned to CakeML
`586e06883d44f5c447793597bdaf0aa76e7a9952` and HOL4
`a390cbabd3a4521bab4ee20281e3e42933a8a3ae`.  It must complete the translation,
x64 bootstrap, and x64 bootstrap proof before the Candle source pin may move.
The earlier engineering x64 bootstrap required 7:55:55 at a different CakeML
head and about 72 GiB peak RSS.  The current source-proof iteration has already
shown that a final translation proof error can consume roughly an hour even
after dependencies are cached.  A fresh canonical, provenance-capturing
bootstrap and link is separately required after the proof replay; proof
products cannot simply be relabelled as the canonical runtime.

If the current repair is green, the earliest plausible sequence is:

- exact four-stage proof replay: roughly another 8--16 hours, with a wider
  6--24 hour uncertainty band because the final proof stage has no current-head
  measurement;
- Candle repin, regeneration, focused/full tests, and fresh plans: 2--4 hours;
- canonical cache-disabled bootstrap, provenance record, and schema-6 link:
  roughly 8--12 hours from the prior serial measurement;
- 20-source then 400-source parser diagnostics and independent consumption:
  roughly 1--6 hours if the corpus is clean.

This supports an optimistic 1--2 day estimate for the first current linked
parser-capable Candle.  Any new proof or corpus-wide parser failure extends it;
repairs are deliberately batched before another bootstrap.

## Whole S3 duration

There is not yet an honest fixed ETA for a release-qualified whole check.  The
400-source parser gate removes syntax failures early, but it does not measure
incremental inference, runtime compatibility, full theorem execution, the
nonlinear/LP tail, retention at scale, or checkpoint behavior.  Those are the
dominant unknowns.  After parser qualification the project must still run
diagnostic direct cutpoints, cumulative boundaries, compatibility batches,
the final nonlinear/LP path, two clean matching full attempts, and one matching
checkpoint/resume attempt, all through independent consumers and approval.

The current planning range is therefore:

- first end-to-end direct diagnostic result: several days after the linked
  runtime, if compatibility repair is modest;
- fully qualified S3 evidence: at least several days and more realistically
  1--3 weeks or longer.  The range will be narrowed only after the 400-source
  parser result and first direct cumulative timings exist.

Quoting an hours-only completion date now would hide the main engineering
uncertainty rather than accelerate it.

## Parallel lanes and acceleration

The immutable Great-100 reference sweep is 48/130 with no failures.  Its first
47 completion intervals average 18.75 minutes; a simple unchanged-rate
extrapolation gives about 25.6 hours for the remaining 82 runs.  This is a
capacity forecast, not a deadline, because target costs vary widely.  It runs
in parallel and is not restarted or silently parallelized.

The PFT oracle is at source boundary 170 of 297 and has continued emitting a
large trace from a long-running source.  Per-source costs are too skewed for a
credible finish estimate.  It is restartable and valuable, but it is not on
the direct S3 critical path.

The useful parts of `external-advice-speed.md` are already adopted: use the
20/400 corpus diagnostics before another frontend rebuild and batch failures.
Native theory caching and a measured two-job build may reduce development
iteration time after hardening, but neither can replace the serial,
cache-disabled release replay.  Four jobs, an x64-only compiler fork, and
theory splitting remain unmeasured or high-risk and are not part of this ETA.

Resource policy remains normally below ten CPUs and 60--80 GiB.  The user's
120 GiB exception is available for measured proof/bootstrap stages with fresh
headroom checks.  Tiny isolated host page-ins are monitored; sustained swap
I/O, less than 32 GiB available memory, or approach to the 120 GiB tracked RSS
ceiling remains a stop-and-diagnose condition.
