# CakeML Dopen source proof chain completion

Date: 2026-09-01 UTC

## Outcome

The CakeML Dopen source proof chain now reaches and passes the top-level
compiler correctness theory on branch `codex/flyspeck-v13-runtime-stack` at:

- commit `715553067b9152debd9e3067a56d9f916809b82e`;
- HOL4 commit `a390cbabd3a4521bab4ee20281e3e42933a8a3ae`;
- clean tracked CakeML and HOL4 worktrees; and
- no admissions, omitted proofs, or new axioms.

This closes the focused parser/inference/evaluator/backend/compiler source
proof repair.  It does **not** qualify a new compiler binary.  The exact-head
warm x64 bootstrap-proof regression is now active, the pristine-cold
four-stage replay remains mandatory afterward, and the Candle repin remains
on HOLD.

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
13. `715553067` -- prove parser completeness for open declarations.

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
advice to instrument the actual frontier and batch small frontend repairs,
but it also shows why proof-critical replay remains serial: parallel retries
would only have multiplied a malformed search.

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
REPL tail.  A source patch implementing that proof-only synchronization is
under a focused serial `replProofTheory.uo` rebuild with a 40-GiB address-space
ceiling.  No runtime or compiler-semantics source is changed.  The repaired
CakeML commit, focused result, and replacement warm receipt will be recorded
here after they exist; no bootstrap success is claimed yet.

## Remaining cold qualification

If the warm gate passes, the next release gate is the frozen pristine-cold
controller's base-heap plus four-stage replay in a new product-empty worktree:

1. `misc/cakeml-heap`;
2. `cv_translator/cake_compile_heap`;
3. `compiler/bootstrap/translation/compiler64ProgTheory.uo`;
4. `compiler/bootstrap/compilation/x64/64/x64BootstrapTheory.uo`; and
5. `compiler/bootstrap/compilation/x64/64/proofs/x64BootstrapProofTheory.uo`.

Only the authenticated terminal manifest from that replay can authorize a
Candle pin refresh.  Prepared Candle commit `103691ef...` still names the old
CakeML head and must not be promoted.  The PFT process continues separately as
an oracle only and contributes no S2/S3 proof evidence.
