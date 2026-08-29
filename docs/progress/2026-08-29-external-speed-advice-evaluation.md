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
- `--cache-dir` enables native cache fetch/upload but leaves ordinary
  timestamp rebuild decisions in place; `--use-cache` additionally selects
  cache-key rebuild decisions and the default cache directory.  An experiment
  must pass a dedicated `--cache-dir` explicitly rather than sharing the
  user's default cache implicitly.
- A native cache key SHA-1-hashes the target's hashable dependency inputs.  It
  maps theory `.uo`/`.ui` dependencies to `.dat`, walks through non-theory
  dependencies, and excludes other `.uo`/`.ui` files and the HOL heap.  The
  key does **not** bind the `Holmake`/`hol` executables, `hol.state`, kernel ID,
  Poly/ML/toolchain, build options, or target platform.  Fetch-time validation
  compares every cached theory's recorded parent hashes with the current
  parent `.dat` files and rejects partial or stale hits, but this does not add
  the missing toolchain identity to the key.
- The pinned fetch path is not an authenticated content-addressed restore.  It
  trusts manifest `name` and `url` strings, does not re-hash staged bytes
  against the SHA-1 in `/data/<sha1>`, and ignores per-file commit/rename
  failures while still reporting a hit.  An unexpected manifest name can also
  select a destination outside the intended three theory products.  A private
  cache produced in the same disposable experiment reduces the threat, but
  these are hard blockers for reuse in a valuable worktree or for treating a
  cache hit as evidence.
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
- The cold serial `cake_compile_heap` stage completed in 1:42:57 with maximum
  RSS 6,399,540 KiB, 101% CPU, and zero swaps.  After the transition to
  `compiler64ProgTheory.uo`, total relevant project RSS remained roughly
  27 GiB and available RAM remained above 180 GiB.  The user's temporary
  120 GiB allowance is therefore available but was not needed for this stage.

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

Implementation has begun with a separate exact 392-plus-8 selection
descriptor.  A measured dry preparation also showed why this cannot be a
count-only expansion: existing pilot handling prepares only 381 of 400 nodes.
The runtime profile must authenticate 18 normalized effective inputs and the
effective post-normalization loader-action projection, as well as require and
retain exactly 400 ordered parser attempts.  The existing pilot receipt has
already been hardened to exact attempt/transcript cardinality so that the
larger profile cannot inherit a zero-attempt or partial-attempt pass.

### Batch frontend repairs — accept

Parser, normalization, and inference failures found by the 400-node gate
should be triaged as one batch.  Rebuild only after the static inventory and
cheap translated-frontend gates are quiet.  A clean release bootstrap remains
mandatory after the final source change.

### Native theory cache — defer execution pending fetch hardening

The native machinery remains the right implementation base, but the pinned
fetcher must not yet be enabled in a valuable checkout.  First patch or wrap it
so that it accepts only the exact expected theory product names, accepts only
`/data/<40-lowercase-hex>` URLs, verifies each staged file's SHA-1 before any
commit, rejects duplicates/extras, and reports success only if every atomic
commit succeeds.  Retain the existing current-parent `.dat` validation.  Then
test the hardened path in a disposable exact checkout, including corrupt
content, traversal names/URLs, duplicates, partial commit failure, stale
parents, and cross-worktree relocation.

Even after transport hardening, the native entry key cannot by itself satisfy
the earlier proposed identity condition: local source and theory dependencies
are content-bound, but the producing executable, heap, kernel, platform, and
invocation are not.

Therefore each experiment must use a physically separate cache namespace
derived from a canonical preflight receipt that binds at least:

- the exact clean HOL4 and CakeML commits;
- SHA-256 hashes of `Holmake`, `hol`, `hol.state`, and `.kernelidstr`;
- the Poly/ML executable/version and relevant dynamically linked libraries;
- architecture/OS identity, `--mt`, job count, target, and the effective build
  environment (`HOLDIR`, `CAKEMLDIR`, locale, and controlled `PATH`);
- the cache schema and experiment protocol versions.

The receipt and its SHA-256 namespace digest must be retained with timing and
cache-hit logs.  A mismatch creates a new empty namespace; it must never reuse
or overwrite a namespace under a different identity.  Give `--cache-dir` and
`--use-cache --cache-dir=...` separate invocation namespaces so caching and
rebuild-strategy effects are measured independently.  Both modes remain
development acceleration only.  Final release qualification still requires
an empty-tree, cache-disabled replay.

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
