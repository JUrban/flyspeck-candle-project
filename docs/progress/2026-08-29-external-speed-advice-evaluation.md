# External build-speed advice: local evaluation

Date: 2026-08-29 UTC

## Verdict

The advice in `docs/advice/external-advice-speed.md` is directionally sound,
but it mixes immediate low-risk development improvements with speculative
proof-architecture work.  The recommended order for this project is:

1. add an explicit parser-only gate over all 400 authenticated source nodes;
2. batch frontend repairs before another bootstrap;
3. use HOL4's native content-addressed cache for development after validating
   its exact cache keys and relocation behavior;
4. benchmark `Holmake -j2 --mt=1` against the current clean `-j1 --mt=1`
   baseline under the existing memory/swap monitor;
5. defer `-j4`, x64 specialization of the shared translation heap, and theory
   splitting until measurements show that the simpler measures are
   insufficient.

The file's `[GitHub][1]` through `[GitHub][4]` references have no link
definitions, so those citations are not independently auditable as written.
The important operational claims were checked against the pinned local tools
and sources instead.

## Locally confirmed facts

- The pinned HOL4 `Holmake` supports `-j`, `--mt`, `--cache-dir`,
  `--cachekey`, `--use-cache`, and cache-key rebuild decisions.  A new custom
  cache should not be invented before the native cache is tested.
- The running clean proof replay deliberately uses `-j1 --mt=1`.  This gives a
  trustworthy serial timing and peak-memory baseline; changing it mid-run
  would destroy that comparison.
- `cv_translator/cake_compile_heap` has two explicit prerequisites,
  `eval_cake_compile_x64Lib.uo` and `eval_cake_compile_arm8Lib.uo`.  This is a
  real opportunity for two-job scheduling.  Later requested stages are already
  x64-specific: `compiler64ProgTheory.uo`, `x64BootstrapTheory.uo`, and
  `x64BootstrapProofTheory.uo`.
- The authenticated direct manifest has 297 ordered actions and 400 source
  nodes.  The existing parser diagnostic is intentionally only a 20-node core
  pilot.  Its own contract says the first-discovery traversal reaches 392
  nodes and binds eight exclusions; an all-inventory diagnostic must therefore
  select all 400 explicitly rather than relabeling the 392-node traversal.
- At the latest review point the serial replay itself used only a few GiB,
  total relevant project RSS was roughly 27 GiB, and available RAM was above
  180 GiB.  The user's temporary 120 GiB allowance is therefore available but
  is not currently needed.

## Decisions by suggestion

### Whole-corpus frontend gates — accept, highest priority

Once the current proof-built diagnostic compiler is linked, run the existing
20-node capability/pilot gate first, then add and run an explicit 400-node
parser-only plan before authorizing another expensive bootstrap.  A later
parse-plus-inference diagnostic is useful only if its translated entrypoint
can preserve an equally narrow, non-promotable claim boundary.  Neither gate
is theorem or release evidence.

This cannot replace the bootstrap currently in flight: that bootstrap is what
provides the new proved parser-diagnostic entrypoint.  It can prevent repeated
bootstraps after the first corpus-wide failures are observed.

### Batch frontend repairs — accept

Parser, normalization, and inference failures found by the 400-node gate
should be triaged as one batch.  Rebuild only after the static inventory and
cheap translated-frontend gates are quiet.  A clean release bootstrap remains
mandatory after the final source change.

### Native theory cache — accept for development, conditional

Test the pinned HOL4 native cache in a disposable exact checkout.  Promotion
requires evidence that a cache key binds the complete theory dependency
closure, HOL4/kernel identity, relevant CakeML source, and build options, and
that restored artifacts work across worktree paths.  Cached builds may be used
for development iteration but cannot be the sole release evidence.

### `Holmake -j2` — benchmark after the serial baseline

Two jobs are plausible; four are not yet justified.  Use a disposable exact
checkout, retain per-stage `/usr/bin/time -v` results, keep `--mt=1`, and stop
on sustained swapping, low available memory, or aggregate project RSS near the
agreed ceiling.  The PFT oracle already retains about 23 GiB, so scheduling
must account for it.  Do not extrapolate the advice's suggested 2–3 hour build
time until this benchmark exists.

### x64-only specialization — defer

The requested release tail is already x64-only, but the shared compiler heap
explicitly contains x64 and arm8 evaluators.  Removing arm8 is a proof and heap
interface change, not a build flag.  Its cost and effect should be derived from
the completed dependency/timing baseline before implementation.

### Splitting large theories — defer

This may help a months-long upstream compiler project, but it creates a large
proof-maintenance and cache-invalidation surface.  Corpus gates, native cache,
and a two-job benchmark are lower risk and more likely to pay back first.

## Reference-sweep caveat

The advice concerns the CakeML/HOL4 build and does not address the other long
critical path: the immutable 130-run schema-v9 reference sweep.  Its current
contract intentionally permits one target runtime at a time.  The live sweep
must not be restarted or silently parallelized.  A future controller could be
designed and reviewed for two concurrent targets, but that would be a new
evidence protocol and would require a fresh collection.

