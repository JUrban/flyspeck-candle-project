# Response to `2026-09-08-speedup.md`

## Decision

The central recommendation is correct and should guide the next phase: a
runner, corpus, expected-result, or reporting change is not by itself a reason
to reconstruct the CakeML compiler.  The compiler product and the run contract
must be versioned and authenticated separately.

The current canonical bootstrap for Candle
`5e6362f4df4979d9a35e99c4673d177f32eb3145` should finish unchanged.  Its
resulting schema-6 compiler should be validated, linked, and used for both
independent clean Great100 executions.  There is no requirement that the two
Great100 runs use two separately bootstrapped compilers; their independence is
at the execution/evidence level.  Rebuilding between them would add roughly
eight hours without adding relevant evidence.

The proposal is therefore adopted in principle, with one important limit:
the present schema-7 transition is explicitly diagnostic-only.  A reused
compiler must not be presented as schema-6/S1 promotion evidence merely by
renaming the mode or adding a build key.  Promotion across Candle revisions
requires the proposed boundary to be implemented, reviewed independently, and
authorized.  Until that happens, reuse is valid for diagnostics and focused
development, while the live final-head schema-6 build remains the formal S1
qualification path.

## What already exists

Much of the mechanism proposed by the note is already implemented, although
it is not exposed as a general `compiler_build_key`.

The schema-6 canonical receipt currently binds and revalidates:

- clean exact Candle, CakeML, and HOL4 revisions;
- the canonical launcher and provenance-controller bytes;
- the exact `Holmake -j1 cake.S` target, order, environment, and complete
  18-theory transcript;
- the HOL runtime, proof artifacts, ancestor artifacts, dependency artifacts,
  bootstrap heap, preimages, forced output transitions, and final bootstrap
  inputs;
- native patch/link inputs, commands, host-tool identities, output hashes,
  runtime ELF closure, and compiler version output.

The schema-7 transition already reconstructs a byte-identical Candle-side
closure across two clean commits and reuses the canonical bootstrap only when
these files agree:

- `build-local-cakeml-bootstrap.sh`;
- `candle/cakeml_artifact_provenance.py`;
- `candle/flyspeck_manifest.json`;
- `candle/cake.S.patch`; and
- `candle/insulate.py`.

It deliberately excludes `candle/regression.py` and ordinary runner changes.
Its tests reject changed closure inputs, dirty trees, missing or altered
records, wrong roots/heads, grafts, replacements, hidden index flags,
controller substitution, and attempts to downgrade schema 7 to schema 6.
The linked binary is freshly reproduced from the retained bootstrap inputs and
byte-compared during validation.

Thus the immediate runner-only reuse path is real, not hypothetical.  It was
kept diagnostic-only because the authority had approved final-head fresh
schema 6, not because the binary was expected to differ.

## The actual over-invalidation gap

The largest present defect is that `candle/flyspeck_manifest.json` is both a
compiler pin source and a very large Flyspeck run/corpus contract.  It contains
the CakeML/HOL4 integration pins, but also the 400-source graph, generated
inputs, normalization contracts, build strata, LP preparation, loader policy,
and other direct-source evidence.  Hashing the whole file in the bootstrap
receipt and transition closure means that a corpus-only manifest update can
invalidate compiler reuse even when the extracted compiler pins and every
output-capable compiler input are unchanged.

That is exactly the category error identified by the proposal.  The fix should
not be an ad hoc exception for one filename.  It should establish independent
keys and make their roles explicit:

1. **Compiler product key.** A canonical hash of inputs capable of changing
   the linked compiler product: the CakeML/HOL source and proof boundary,
   relevant heaps/runtime and host toolchain, architecture, exact build and
   native-link commands/flags, generated-code patch, and other
   output-affecting build inputs.  The CakeML and HOL pins should be represented
   as a small canonical integration object, not by hashing the entire Flyspeck
   corpus manifest.
2. **Qualification-policy identity.** The exact controllers and validation
   policy used to establish the receipt.  A policy-controller edit need not
   imply that the compiler bytes changed, but it can change which evidence is
   acceptable.  It must therefore be bound and reviewed separately rather
   than being silently omitted from both the product key and the authority.
3. **Run-contract key.** The runner, selected source corpus, normalization
   ledger, expected theorem/state identities, limits, and reporting/finalizer
   contract.  This key must change for runner or corpus changes even though the
   compiler product key remains stable.

Every Great100/Flyspeck report should bind all applicable identities.  The
build mode should be an explicit field with one of `FRESH`, `REUSED`, or
`INCREMENTAL`, plus a separate promotion status.  In particular, `REUSED` must
not imply either `promotion-authorized` or `diagnostic-only`; those are
different facts.

## How to define the compiler closure safely

The proposal is right to ask for a machine-readable closure, but a narrowly
guessed transitive source list would be less trustworthy than the present
conservative model.  CakeML/HOL build scripts can load ML sources dynamically,
and Holmake dependency metadata alone is not proof that an omitted file cannot
affect the result.

The first implementation should therefore be conservative:

- retain the current exact clean CakeML and HOL revision/source boundary and
  all recorded runtime, heap, proof-artifact, command, and tool identities;
- split the small CakeML/HOL integration pin object out of the mixed Flyspeck
  manifest for build-key purposes;
- model the bootstrap-product inputs and native-link inputs explicitly;
- exclude only inputs with a clear non-influence argument, beginning with
  runner, target corpus, expected results, reports, and documentation; and
- narrow the CakeML/HOL repository closure later only if an instrumented and
  independently reviewed dependency analysis proves that doing so is
  complete.

This conservative first version captures the high-value case—Candle-side
runner and Flyspeck-corpus evolution—without betting formal evidence on an
incomplete dependency graph.  Documentation-only changes inside the upstream
CakeML/HOL repositories may initially continue to over-invalidate the key;
that is tolerable because those pins are stable during the current direct
Flyspeck campaign.

The key must be a canonical digest over structured records with an explicit
schema/domain tag, not a concatenation of filenames and hashes.  A key is an
index into authenticated evidence, not evidence by itself.  Reuse must still
validate the original immutable receipt, exact compiler/output hashes, the
live consumer revision and run contract, and the relationship between them.

## Build-mode assessment

### Reuse

This is the highest-value mode and should be the default whenever the compiler
product key is unchanged.  It is especially appropriate for:

- `regression.py` and timeout/resource-controller fixes;
- Great100/Flyspeck manifests and expected-result updates that do not change
  the compiler integration pins;
- source normalization and compatibility-ledger changes applied to the input
  corpus at runtime; and
- comparison, reporting, stratum-planning, and finalizer corrections.

The reused compiler must be re-linked/revalidated only when a linked-product
input changed; a pure runner change should not require even a native compiler
relink if the authenticated linked binary is already available and validates.

### Incremental development build

This is valid for focused, non-promotable compiler development, but it is not
the main speed opportunity here.  The 18 translation targets on the current
x64 bootstrap frontier form an almost completely serial extension chain.  A
frontend change can therefore invalidate most descendants.  Existing
same-worktree Holmake reuse already provides much of the safe incremental
benefit.  Any new `INCREMENTAL` mode should record the reused predecessor
artifacts, affected subgraph, exact outputs, and diagnostic-only status; it
should not be allowed to emit S1/S2/S3 promotion evidence.

### Fresh canonical build

Use this when an output-capable compiler input, toolchain identity,
architecture, or canonical build configuration changes, and at an explicitly
required release boundary.  The active `5e6362f` build is the required fresh
final-head build.  No second fresh build is needed merely because a second
clean Great100 execution is required.

## Required fail-closed tests

The proposed test matrix should be implemented before any promotion-authorized
reuse:

- changes to `regression.py`, reports, documentation, target sources, expected
  identities, or non-pin Flyspeck manifest fields leave the compiler product
  key unchanged but change the run-contract identity where applicable;
- changes to extracted CakeML/HOL pins, compiler/proof sources, heaps,
  architecture, build target/argv/environment, native patch/link inputs,
  flags, or relevant tool identities change the product key;
- missing, duplicate, untracked, symlinked, mode-drifted, or source-drifted
  closure entries fail closed;
- a reused artifact passes the same bootstrap-receipt, binary-hash, native
  derivation, ELF/runtime, and live-root checks applicable to a fresh one;
- a report cannot claim `FRESH`, `REUSED`, or `INCREMENTAL` inconsistently with
  its bound receipt and transition evidence;
- a stable product key cannot suppress a changed qualification-policy identity
  or run-contract identity; and
- old schema-7 diagnostic evidence cannot be relabeled as promotion-authorized
  evidence.

At least one integration test should construct two real clean Candle commits
that differ only in runner/corpus material, demonstrate an identical compiler
product key, validate the same compiler hash against both, and demonstrate
different run-contract keys.  A complementary compiler-input mutation must
force a different product key and reject reuse.

## Recommended redirection

1. Let the active cache-disabled schema-6 bootstrap finish untouched.
2. Independently run `check-bootstrap`, perform the ordinary exact-root
   schema-6 link, and independently run `check-linked`.
3. Use that single authenticated compiler for both independent clean Great100
   executions at frozen head `5e6362f`; do not rebuild between runs.
4. If a runner-only defect is found before S1, use the existing schema-7 path
   to diagnose and verify the fix quickly.  Either obtain independent approval
   for the new product-key reuse authority or retain the current requirement
   for a fresh final-head schema-6 build before promotion.  Do not improvise a
   promotion exception.
5. Implement the explicit product/policy/run-key separation on a new branch
   after the current S1 evidence is secured, or at the first corpus-only change
   that would otherwise request another bootstrap.  This work should not delay
   the two current Great100 executions.
6. Seek independent review of the closure, canonical encoding, negative and
   positive mutation tests, report semantics, and promotion rule.  Only after
   that approval should reused evidence become eligible for formal S1/S2/S3
   closure.
7. Keep incremental builds diagnostic-only and low priority unless measured
   compiler-source iteration, rather than runner/corpus iteration, again
   dominates the schedule.

## Bottom line

The note identifies a real and important optimization.  The project has
already built most of the safe reuse machinery, but it currently over-binds a
mixed Flyspeck manifest and intentionally withholds promotion authority from
transitions.  The right redirection is to finish the one active fresh build,
reuse its binary for both final Great100 runs, then generalize the existing
transition into an independently approved compiler-product/run-contract split.
That should eliminate nearly all future eight-hour rebuilds caused only by
runner or corpus evolution without weakening the mathematical or provenance
requirements.
