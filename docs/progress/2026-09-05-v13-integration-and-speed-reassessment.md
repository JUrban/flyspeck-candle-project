# v1.3 integration and speed reassessment — 2026-09-05

## Scope and claim boundary

This is an implementation and planning checkpoint, not S1, S2, S3, or release
evidence.  The governing path remains direct execution of the pinned Flyspeck
source by the verified CakeML/Candle stack.  HOL Light, pristine-reference
execution, and PFT are development oracles only and cannot be counted as
direct-source evidence.

No PFT process or artifact was inspected or modified for this checkpoint.

## Disposition of `audit1.md`

The audit's central distinction is correct: a complete
`HOL Light -> PFT -> Candle` replay does not satisfy v1.3 S2 or S3.  The project
had already adopted that correction in the 2026-08-27 roadmap re-evaluation
and in the repository introduction.  The active critical path is now:

1. exact CakeML/Candle compatibility and verified Dopen;
2. the real source-driven Great-100 gate;
3. deterministic direct Flyspeck strata;
4. direct nonlinear/LP closure; and
5. two clean whole-source runs plus resume/corruption qualification.

The current direct inventory contains 400 selected source nodes and 297 build
actions.  PFT and pristine HOL Light results may later be compared against the
direct result, but cannot produce or promote it.

## Disposition of the external speed advice

The advice is directionally useful, but the repository's measurements narrow
how it should be applied.

- The 20-then-400 frontend gate and batching of parser fixes are accepted as
  the highest-value optimization.  They already prevented repeated blind
  compiler bootstraps.
- `Holmake -j2` remains a development-only experiment.  Measured affected
  theory builds averaged only 108--120% CPU, and one earlier overlap killed a
  large target.  The canonical release controller therefore remains a clean,
  cache-disabled `Holmake -j1 cake.S` build.
- Native cache experimentation is limited to exact toolchain/source/dependency
  namespaces.  `scripts/describe-hol-cache-namespace.py` creates only a
  fail-closed development preflight; it neither creates a cache nor changes
  release qualification.
- An x64-only verified specialization and splitting large CakeML theories are
  larger proof-architecture projects.  They remain deferred while cheap corpus
  gates and small proof batches give more immediate benefit.
- The ordinary working envelope remains below ten CPUs and 60--80 GiB RAM.
  The user-authorized 120-GiB exception is available only for measured heavy
  stages when host headroom permits it.

## Consolidated direct-evidence plumbing

The clean integration worktree is
`/project/worktrees/flyspeck-project-v13-integration` on branch
`codex/flyspeck-v13-project-integration`.  It starts from parser-result consumer
commit `642ad428487e3dfe5d3f146cc141c7bbfc856a7a` and now contains two previously
isolated, non-promotable implementation slices:

- continuous fork/vfork/clone/exec/exit tracing with `PTRACE_O_EXITKILL`,
  credentialled `SOCK_SEQPACKET` observations, pidfd identity checks, and
  hostile lifecycle tests; and
- the reviewed pristine semantic-v3 decoder and session state machine,
  including strict frame order, source bindings, and empty-stream rejection.

The trace remains explicitly unapproved because a same-UID local controller is
not a protected external authority.  The pristine semantic protocol remains
oracle plumbing and cannot become S2/S3 evidence.

At tested code head `36f28be47c6809761f18d274393e964373b48e23`, all
22 `scripts/test-*.py` programs passed.  Their 336 test methods include:

- 8 checkpoint trace-controller tests;
- 10 pristine protocol and 32 pristine output-parser tests;
- 49 direct-release protocol tests;
- 67 hostile S1 finalizer tests; and
- 14 top-100 sweep-controller tests.

The full suite ran with:

```text
set -e
for test_path in scripts/test-*.py; do
  python3 -I -S "$test_path"
done
```

## Current canonical and parser state

The untouched canonical current-head build remains at:

`/project/flyspeck-candle-runs/cakeml-canonical-bootstrap-8a8926906-419a96e37-attempt-002`

It binds Candle `419a96e374dba147d21fc6547f7025d6d14e5ff0`, CakeML
`8a8926906ec97204eeec961496d191103cda3229`, and HOL4
`a390cbabd3a4521bab4ee20281e3e42933a8a3ae`.  At this checkpoint it had
completed 8/18 targets through `basis_defProg` and was building
`printingProg`.  This live build was not rescheduled, parallelized, or otherwise
modified in response to the speed advice.

The fresh host-only 20-input parser materialization is sealed read-only at:

`/project/flyspeck-candle-runs/parser-pilot-materialization-419a96e-attempt-001`

It has exactly 20 ready inputs, zero unsupported inputs, plan SHA-256
`c1136be4afa2fba86b6949d4f6ad2e7fd368fefe8158c18088a74d4703ef494d`,
and host-materialization SHA-256
`4134cfbf35edfcc08755e8b203264f804fa9f5d54bb9fb78e70bb307e6675e96`.
Materialization is not parser evidence.  Execution still waits for successful
canonical receipt validation and the ordinary schema-6 link.  The 400-input
materialization remains gated on independent acceptance of this pilot.

## Rejected development-binary shortcut

The older native development executable has the same pinned CakeML frontend
commit and predates the current Candle head only in host-side manifest,
provenance, and parser-descriptor commits.  It was therefore considered as a
possible way to expose an early d0 compatibility failure while the canonical
bootstrap continued.

That shortcut was not executed.  The 923-byte d0 prefix is not a standalone
runtime input: the direct runner first validates an ordinary same-head link,
copies every runtime-consumed byte into a disjoint read-only snapshot, writes
the exact source/normalization/generated-input configuration, instruments each
action with a nonce-bound ledger check, and adds source-trace and semantic
observation postludes.  Feeding the raw prefix to the development executable
would omit those controls and could produce a misleading success or an
irrelevant setup failure.  Fabricating linked provenance merely to reach the
formal runner would be worse.  No diagnostic result root was created and no
gate was weakened; d0 remains queued after the canonical link and both parser
consumer gates.

## Next exact sequence

1. Let the current canonical build finish untouched and validate its external
   receipt against the committed controller and clean repositories.
2. Create and independently validate the ordinary schema-6 link.
3. Execute and independently consume the 20-input parser pilot, then repeat
   for all 400 inputs.
4. Execute and consume d0 and d1 direct-source diagnostics.
5. Run the schema-7 Great-100 transition diagnostic without promotion.
6. Freeze the actual final Candle head and repeat a fresh clean bootstrap before
   ordinary S1 and broader direct-source execution.
