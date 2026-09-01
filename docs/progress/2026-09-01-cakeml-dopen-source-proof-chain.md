# CakeML Dopen source proof chain completion

Date: 2026-09-01 UTC

## Outcome

The CakeML Dopen source proof chain now reaches and passes the top-level
compiler correctness theory, its repaired REPL proof consumer, and the exact
head warm x64 bootstrap-proof regression on branch
`codex/flyspeck-v13-runtime-stack` at:

- commit `c2e26f43c35080d57fc18aba42d4023590b6daba`;
- HOL4 commit `a390cbabd3a4521bab4ee20281e3e42933a8a3ae`;
- clean tracked CakeML and HOL4 worktrees; and
- no admissions, omitted proofs, or new axioms.

This closes the focused parser/inference/evaluator/backend/compiler source
proof repair and its first downstream bootstrap-proof consumer.  It does
**not** qualify a new compiler binary.  The pristine-cold four-stage replay
remains mandatory, and the Candle repin remains on HOLD until its authenticated
terminal manifest passes.

## `audit1.md` current-state reassessment

The audit's strategic criticism remains correct: a full
HOL-Light-to-PFT-to-Candle replay is P1 validation and cannot establish direct
S2 or S3.  Its more detailed corrective checklist now maps to current evidence
as follows:

1. The CakeML `Dopen` parser, inference, semantics, evaluator, backend,
   compiler and downstream REPL proof chain is complete at the source level,
   with the cold compiler qualification in progress below.
2. The conservative OCaml compatibility inventory and generated 400-source
   projection exist, while compiled compatibility remains gated on the new
   linked runtime.
3. The independently audited Great-100 reference artifact closes 130/130
   runs (two sweeps of 65 targets) with identical cross-sweep fingerprints,
   but remains deliberately `candidates_unapproved`; it can be approved only
   by comparison with the qualified current direct Candle binary.
4. Direct 20/400 parser execution, linked compatibility, d0/d1 and cumulative
   Flyspeck strata are still pending and are not replaced by source-plan,
   reference-HOL, or PFT evidence.
5. The active full PFT run remains untouched as an oracle only.  Project
   README status labels explicitly state that it cannot advance S2 or S3.

Thus the audit's direction has been corrected, but its final direct-source
requirements are not yet complete.  The current critical path is the cold
qualification, deliberate Candle repin/link, consumed 20/400 gates, current
binary Great-100 comparison, and then direct nonlinear/LP cumulative S2/S3.

The roadmap-level relocation rereview also found and repaired a project
wrapper defect.  `check-compatibility-ledger.sh` previously located the direct
manifest relative to the project checkout, producing a doubled
`worktrees/worktrees` path from a normal Git worktree.  Commit `c18755b`
derives the workspace from the explicit repository root and permits an
explicit direct-manifest override.  Default and override modes now both close
the 6,074-entry ledger and the 3,689-finding/329-file direct projection; the
inventory, ledger and triage suites pass 8/8, 6/6 and 4/4 respectively.

## Final proof commits

The commits after the previously prepared CakeML parent `480a9f4fc...` are:

1. `32580b0b7` -- prove backend initial Dopen environment domains;
2. `731f386bc` -- prove the open environment relation efficiently;
3. `32ec37ea3` -- generalize declaration inference soundness for open;
4. `1aeb11019` -- include open in declaration parser first sets;
5. `4816371bc` -- preserve evaluator relation across open declarations;
6. `2c0fafa71` -- restore the canonical typing proof for open;
7. `504cbdffd` -- preserve initialization invariants across open declarations;
8. `1b0c9065f` -- use canonical inference soundness in REPL typing proofs;
9. `a0dff58f9` -- finalize the canonical declaration typing proof;
10. `2ca34642f` -- restore inference completeness for open declarations;
11. `3fce40602` -- prove parser soundness for open declarations;
12. `d93c024fa` -- complete open token-parser first-set exclusions; and
13. `715553067` -- prove parser completeness for open declarations; and
14. `c2e26f43c` -- repair the REPL proof after parser diagnostics.

The final parser work covers both accepted `open` forms: the recursive
`nStructName` production and the direct long-identifier constructor.  It also
adds `OpenT` to the required expression/value/constructor non-first-set
lemmas and the declaration-list stopper set.

## Focused exact-source evidence

Serial `Holmake -j1` checks under a 16-GiB address-space ceiling passed as
follows:

| Theory/target | Wall time | Maximum RSS |
| --- | ---: | ---: |
| `type_dCanonTheory.uo` | 56.75 s | 865,408 KiB |
| `inferCompleteTheory.uo` | 45.56 s | 1,056,272 KiB |
| `pegSoundTheory.uo` | 1m34.64s | 1,144,488 KiB |
| `cmlNTPropsTheory.uo` | 35.28 s | 696,164 KiB |
| `pegCompleteTheory.uo` | 2m30.24s | 1,720,424 KiB |

The top-level request
`compiler/proofs: Holmake -j1 compilerProofTheory.uo` then built two theory
files, saved `parse_prog_correct0`, `parse_prog_correct`, the compiler
parse/infer/compile correctness results including `compile_correct`, and
exited zero in 2m21.75s with 3,509,148 KiB maximum RSS.  This is an
exact-head developer proof regression over the current worktree cache; the
cold bootstrap replay below remains the release qualification.

The repaired downstream consumer was then checked with
`Holmake -j1 --mt=1 replProofTheory.uo` under a 40-GiB address-space ceiling.
It saved `evaluate_decs_compiler64_prog` and
`semantics_prog_compiler64_prog`, exported the theory, and exited zero in
18m53.76s with 17,882,648 KiB maximum RSS and no swaps.  An immediate second
request was a clean no-op.  The source diff scan found no added admissions,
cheats, omitted proofs, or axioms.

## Diagnostic lessons

Two failures were evidence-quality issues rather than deep theorem failures.

First, `type_d_type_d_canon` proved successfully in the theory body but was
not exported because the script lacked the required `Finalise
type_d_type_d_canon;`.  The exact rebuild now visibly saves the theorem.  A
green theory process alone is insufficient when a downstream consumer needs a
named theorem; exported-signature visibility is part of the focused gate.

Second, an unrestricted `metis` attempt in the Dopen completeness branch ran
for more than an hour because the restored proof referred to the stale binder
name `path`, while the generated induction case binds the path as `l0`.
Explicit theorem applications and witnesses both fixed the name error and
reduced the clean target to 45.56 seconds.  This validates the external speed
advice to instrument the actual frontier, use cheap 20/400-file gates, batch
small frontend repairs, and reuse exact-head worktree products during
development.  It also shows the limit of broad build parallelism here: the
roughly 4,000-constant bootstrap proof phase is internally serial, and
parallel retries would only have multiplied a malformed search.  The release
gate therefore remains a pristine cold replay even though warm products are
useful for diagnosis.

## External speed-advice assessment

The supplied `docs/advice/external-advice-speed.md` (SHA-256
`01b0a59abe465d10113e5370926784ef1526eff609304a42e2b687830fc48288`)
contains useful engineering advice, but its proposals do not all have the
same evidence or fit the current qualification boundary:

- **Adopt now:** keep the 20-input pilot ahead of the 400-input inventory,
  batch frontend failures before another release build, and reuse exact-head
  products in the same development worktree.  These measures avoid expensive
  iterations without weakening the final clean replay.
- **Benchmark only in development:** `Holmake -j2` or `-j4` may shorten the
  independent portions of a future traversal.  It cannot accelerate a single
  large HOL process, and the accepted cold controller is deliberately frozen
  at `-j1 --mt=1`; changing it during this replay would destroy the authority
  of the run.  Any parallel release controller needs its own measured memory
  envelope and independent review.
- **Defer cross-worktree caching:** a content-addressed cache is attractive,
  but a trustworthy key must close over theory sources, generated products,
  the complete dependency graph, HOL4, Poly/ML, host tools, and build flags.
  Same-worktree incremental products already provide the safe near-term gain;
  an unauthenticated shared cache is not release evidence.
- **Use frontend gates at the earliest honest point:** source-plan and static
  checks can run before the bootstrap, but the new compiled CakeML
  parser/inferencer does not exist until the first parser-capable runtime is
  bootstrapped and linked.  Thereafter the 20/400 gates should protect every
  later expensive whole-corpus iteration.
- **Defer x64-only specialization and theory splitting:** the present
  `compiler64Prog` closure deliberately includes shared multi-target compiler
  definitions, while the x64 bootstrap/proof targets are already
  architecture-specific.  Proving a smaller verified compiler or refactoring
  giant theories may pay off over months, but each is a separate proof project
  and is not on the shortest path to the first usable Flyspeck runtime.

The suggested two-to-three-hour clean build is therefore a hypothesis worth a
later controlled benchmark, not a planning assumption.  Current measurements
show a 4h51m warm translation traversal and a prior cold traversal that reached
a final source error after 11h10m; the serial critical path dominates both.

## Candle host-runtime identity refresh

A sanitized baseline test of the prepared Candle pin exposed two independent
host-contract failures before the CakeML repin.  The fail-closed checks were
working as designed: `/lib/x86_64-linux-gnu/libz.so.1.3` retained its path and
113,000-byte size but changed SHA-256 from `9b64150b...` to `86200da3...`, and
the regenerated `/etc/ld.so.cache` changed SHA-256 from `0971c6df...` to
`98c3f425...`.  In addition, the exact documented `env -i ... LC_ALL=C`
Python launch observes `utf8_mode=1`; the direct-stratum and float-performance
controllers incorrectly pinned `0`.  The parser-diagnostic controller already
pinned the observed value correctly.

The independent Candle branch `codex/flyspeck-v13-host-runtime-refresh`, based
on clean authority `688d9d1738a7021501f95b6f0ed788e014fa726f`, deliberately
refreshes those four bounded host records at commit
`b5aa0eb` (`Refresh pinned host runtime identities`).  Exact validation of all
three Python ELF closures and the OCaml lexer toolchain passes.  Under
`PATH=/usr/bin:/bin`, `LC_ALL=C`, and an otherwise empty environment:

- the two originally failing direct-stratum regressions pass 2/2;
- focused Python/float compatibility tests pass 41/41;
- the main lightweight Candle discovery passes 330/330 in 160.393 seconds,
  maximum RSS 324,224 KiB, zero swaps; and
- the compatibility discovery passes 63/63 in 6.043 seconds, maximum RSS
  46,076 KiB, zero swaps.

A follow-up critical check found that the direct-runner unit test inherited
the developer shell's locale even though production requires exact
`LC_ALL=C`.  It now supplies the production environment to every child
interpreter at commit `6fad64c` (`Test stratum CLI under its exact locale`).
The exact test passes from both ordinary and already-sanitized parents, and a
fresh ordinary full discovery passes 330/330 in 161.277 seconds, maximum RSS
328,200 KiB, zero swaps.

The unchanged generated corpus authorities also pass their cheap pre-repin
fixed-point gates on this branch: the manifest closes 297 roots, 400 source
nodes and 43 generated inputs; the isolated parser controller validates the
exact 20-input pilot and 400-input all-inventory descriptors.  These checks
establish source-plan consistency only, not a compiled parser result.

This is a host-tool authority repair, not compiler qualification and not a
CakeML pin.  The final Candle repin must be based on `6fad64c` (or an exact
reviewed descendant), rather than promoting either the old `688d9d1` authority
unchanged or stale prepared commit `103691ef`.

## Warm attempt 004 and consumer-proof repair

Warm regression attempt 004 ran at:

`/project/flyspeck-candle-runs/cakeml-parser-dopen-warm-proof-715553067-attempt-004`

It bound the exact CakeML/HOL4 heads above, ran
`x64BootstrapProofTheory.uo` with `-j1 --mt=1`, and used a 117,964,800-KiB
(112.5-GiB) virtual-address-space ceiling.  The sealed receipt records failure
after 28m22.34s with 25,582,872 KiB maximum RSS and no swaps.  All four reused
stage-3 product hashes were unchanged.  Receipt and log hashes are:

- receipt: `b0072965a6ce8817eeafe6879f3c1430afe4650f3cfe251eb84f6b3684745f96`;
- log: `44a34cfe005ebca1125b274df40ecbc3c5a2e21320f4c58cb1b0dfd1d102163e`; and
- time: `cbb16de50cde53ca90d534fc6f50a80b22f1852af51073ecdfc88b67d3b346a2`.

`repl_init` passed.  `replProof` then reached its final theorem,
`evaluate_decs_compiler64_prog`, before failing; the x64 proof target was not
reached.  The failure exposed a stale proof consumer: `main` now evaluates the
parser-diagnostic capability and run-argument dispatches before
`compiler_has_repl_flag`, but this REPL evaluator proof still modeled the old
control-flow prefix.

A replay from the emitted 8.70-GB theorem heap proved that, under the existing
`has_repl_flag (TL cl)` hypothesis, those two new calls return false and
`NONE`; carrying their evaluator clock/reference effects through the old proof
then closes the entire theorem, including its unchanged backend-config and
REPL tail.  The first patch used generated result names and accidentally split
an unrelated `res'`; the final proof instead anchors the two dispatches through
their exact `do_opapp` and `evaluate` facts before case-splitting their result
variables.  This removes fresh-name brittleness.  No runtime or
compiler-semantics source changed.  The focused result is recorded above and
the proof-only synchronization is commit `c2e26f43c`.

## Warm attempt 005

The replacement exact-head warm regression passed at:

`/project/flyspeck-candle-runs/cakeml-parser-dopen-warm-proof-c2e26f43c-attempt-005`

It bound CakeML `c2e26f43c35080d57fc18aba42d4023590b6daba` and HOL4
`a390cbabd3a4521bab4ee20281e3e42933a8a3ae`, then ran
`x64BootstrapProofTheory.uo` with `-j1 --mt=1` under the same 117,964,800-KiB
(112.5-GiB) virtual-address-space ceiling.  It exited zero after 30m10.49s,
with 46,161,420 KiB maximum RSS and no swaps.  The log records the compiled
parser-diagnostic results, Candle soundness, axiom-free consistency, the
explicit no-cheats check, and successful theory export.  Pre/post hashes of
the repaired `replProof` products and all reused stage-3 products are equal.

The sealed evidence hashes are:

- receipt: `b1af333466df6c17b11273d10fa64b8559124f8f45838a46296ce9c4a6cfb160`;
- runner: `03b249804094592ab153e57a4b0d63f1e0ae0d31a63859878ff831b53366b9d0`;
- log: `d91e79cf6808c2685222530926a47a1f3cc75eb9bcd378e47144a94611631a2e`;
  and
- time: `d1fe61a337d75c5e4dbc10407d412a1343583067b52894e91a6e7f59d82ad0d7`.

The runner, log, time record, and receipt are read-only.  This is deliberately
classified as a warm developer regression, not as the cold release proof.

## Remaining cold qualification

The next release gate is the frozen pristine-cold controller's base-heap plus
four-stage replay in a new product-empty worktree at exact commit
`c2e26f43c35080d57fc18aba42d4023590b6daba`:

1. `misc/cakeml-heap`;
2. `cv_translator/cake_compile_heap`;
3. `compiler/bootstrap/translation/compiler64ProgTheory.uo`;
4. `compiler/bootstrap/compilation/x64/64/x64BootstrapTheory.uo`; and
5. `compiler/bootstrap/compilation/x64/64/proofs/x64BootstrapProofTheory.uo`.

Only the authenticated terminal manifest from that replay can authorize a
Candle pin refresh.  Prepared Candle commit `103691ef...` still names the old
CakeML head and must not be promoted.  The PFT process continues separately as
an oracle only and contributes no S2/S3 proof evidence.
