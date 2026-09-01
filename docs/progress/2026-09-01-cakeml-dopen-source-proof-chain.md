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

The remaining P0 pointer-shadowing review is also closed at commit `1c76332`.
The selected Flyspeck source defines `add_eq`, `mul_eq`, and `eq_eq`, then
simultaneously binds `(+)`, `(*)`, `(!)`, and `(==)` to those functions and
`REFL` before using `(==)` to construct a theorem.  The strengthened typed
oracle mirrors that simultaneous binding and requires its local `(==)` to
return a theorem-like pair `(3,12)`.  This cannot be supplied by either host
OCaml's boolean physical equality or Candle's reference-only primitive.  The
oracle passes under pinned OCaml 4.14.1 and under the clean compiled Candle at
commit `87f1fd965313c090fd4d87bcfcc493a3ad7bc79f` (executable SHA-256
`c20b3ec65fc01b6f50a0101c706e18271920530030aa3c381a36ff0fdbd3b23f`), in
both its default and explicit-executable modes.  `verify-lock.sh` now invokes
the same regression against its selected clean Candle executable.  The ledger
therefore records five resolved entries, seven regression-pending entries,
two deferred entries, and only one proof-pending entry: the Dopen qualification
that remains subject to the pristine-cold replay and final linked runtime.

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
- **Benchmark parallelism only in development:** `Holmake -j2` may shorten
  independent portions of a future traversal, but it cannot provide the
  headline speed-up on the dominant translation chain.  The exact sources
  make `arm8Prog` extend `x64Prog`, `riscvProg` extend `arm8Prog`, `mipsProg`
  extend `riscvProg`, and `compiler64Prog` extend `mipsProg`; those large
  targets are deliberately serial dependencies, not schedulable siblings.
  A single large HOL process is serial as well.  The accepted cold controller
  is frozen at `-j1 --mt=1`; changing it during this replay would destroy the
  authority of the run.  Any parallel release controller needs its own
  measured memory envelope and independent review.
- **Use the existing cache mechanism only in a bounded development pilot:**
  pinned HOL4 already provides opt-in `Holmake --use-cache`/`--cache-dir`
  theory-product caching, recursive content keys, staged fetches, and
  fail-safe parent-hash validation.  There is no reason to invent another
  cache.  Its internal key is centered on theory inputs and `.dat` parent
  hashes, however, and does not visibly bind every HOL4/Poly/ML/host-tool/build
  flag identity required by this project.  A pilot must therefore put each
  exact toolchain and command envelope in a separate externally named cache
  root, exercise clean misses and cross-worktree hits, and remain diagnostic.
  Same-worktree incremental products remain the lowest-risk near-term gain;
  no shared-cache hit is release evidence.
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

## Checkpoint/resume protocol critical review

Commit `dd067a2` introduced pure record constructors and validators for a
checkpoint-attempt plan, a process checkpoint, and a resume attempt.  Its
45/45 focused tests, the unchanged 18/18 published-result tests, bytecode
compilation, and diff checks pass.  All new schemas keep promotion, S2, S3,
release, and PFT-evidence flags false.  This is useful design work, but it is
**not accepted checkpoint qualification**.

An independent hostile review found no direct promotion bypass, but did find
P1 acceptance gaps.  Process and resume validation trusted shallow envelopes,
so coherently rehashed mutations could bypass full plan and checkpoint
semantics.  The two clean baselines were not fully authenticated as distinct
schema-6 executions.  Expected authorities and controller challenges were
mutually self-consistent rather than externally supplied.  Restart records did
not yet reauthenticate images or bind complete restart/process-tree and raw
suffix-event evidence.  Address-space and sampling-cadence claims were also
declared rather than measured.  Concrete counterexamples included a changed
boundary-action hash, `origin_process.reaped=false`, and a second "clean"
capture distinguished only by a fabricated receipt hash.

Follow-up commit `0aa0dd9` closes those P1 paths in the fail-closed value
protocol.  Process and resume records now invoke the full plan/checkpoint
source-chain validators.  Each clean candidate carries a raw schema-6 receipt,
authenticated plan, expected external authority, predeclared attempt nonce,
and challenge-bound controller measurement; the two receipt, capture, and
attempt identities must all differ.  The externally supplied challenge also
precommits the plan, diagnostic pilot, DMTCP authority, resource limits,
environments, nonces, and tokens.  Restart, image, coordinator/process,
zero-prefix-replay, raw suffix-event, READY/RESUMED, address-space, RSS, disk,
and sampling-cadence records are now bound through the comparison.

The expanded protocol suite passes 49/49 in both `C.UTF-8` and exact
production `C` locales (73.101 and 72.081 seconds); the unchanged published
result suite passes 18/18.  Bytecode and diff checks pass.  A second hostile
review reran five focused coherent-splice/escalation tests and found no
remaining P0/P1 in this deliberately unapproved protocol.

This still does **not** qualify checkpoint/resume.  A pure record can clone one
physical run into two nonce-distinct assertions, and the current DMTCP,
filesystem, process, measurement, and suffix facts are controller assertions.
The schemas therefore require `runtime_qualified=false`,
`os_evidence_authenticated=false`, and anchored no-follow claims false, as
well as all promotion and PFT flags false.  A separate OS authenticator must
bind challenges to distinct live process identities and immutable raw logs,
authenticate DMTCP/ELF/kernel/image inputs through anchored file descriptors,
and supply raw cadence/restart/process-tree evidence before a finalizer may
qualify the result.  The user-authorized 120-GiB exceptional memory allowance
does not relax any evidence requirement or the parser consumers' exact
16-GiB limit.

### OS-observation scaffold and hostile review

Commits `b6b40c3`, `f8ed7c2`, `859e065`, and `a9ed233` develop the next
checkpoint layer, but the resulting module is deliberately an **unapproved
observation candidate**, not the separate trusted OS authenticator requested
above.  The first live companion was rejected after independent review found
that its in-process token seal was forgeable; tracing stopped after the first
exec; READY and action receipts were cooperative; process-tree membership was
caller-selected; restart paths were subject to pathname replacement; and
mount/proc namespace, coordinator-port, loaded-ELF, resource, and resumed-exec
continuity were not independently closed.  No release used that result.

The accepted scaffold now reports those limits rather than hiding them.  Its
wire decoder is explicitly named a schema/layout checker; its checksum is
self-reported and detects accidental corruption only.  Coherent edits to
ordinary observation values are intentionally not called integrity failures,
because an unkeyed self-contained record cannot authenticate its author.  The
candidate enumerates the missing external precommit/signing or trusted-source
validator, the forgeable in-process seal and mutable dictionaries, and the
remaining kernel/runtime boundaries.  Exactly eight release-sensitive keys
(`lifecycle_complete`, OS authentication, runtime/checkpoint qualification,
S2/S3 approval, release promotion, and PFT use) may occur only once at the
top level and must be the literal value `false`; recursive validation rejects
the same keys at every nested location.

The publisher now consumes the direct protocol's exact, strictly path-sorted
seven-field DMTCP image records, including ordinary-file type, mode `0444`,
and link count one.  It hashes the same record list as the direct protocol,
publishes by no-replace rename to
`checkpoints/<ordered-file-sha256>`, retains and rehashes the selected file
descriptors, and supplies restart argv in the local DMTCP 4.1.0 form:

`dmtcp_restart --join-coordinator --coord-port PORT IMAGE...`

The integration test passes that publication through the public
`build_process_checkpoint` entrypoint rather than a self-agreeing low-level
helper.  Candidate paths, argv, environments, nested keys, and values reject
any case-insensitive `pft` substring and every Unicode `Cc` control character,
including the C1 range.  Controller-local receipt, reap, cadence, and restart
labels no longer claim independent parent authentication.

At final scaffold head `a9ed233886026d76fabc83ba989dfcac27a3d453`, the
companion suite passes 23/23 under exact `LC_ALL=C`; an independent run took
4.22 seconds and 33,264 KiB maximum RSS.  The unchanged direct protocol suite
passes 49/49, and the published-result, compatibility, and pristine-reference
suites pass 18/18, 3/3, and 10/10.  A final independent read-only review found
no P0/P1 in this narrowed contract.  Nevertheless all authentication,
qualification, approval, promotion, and PFT-use flags remain categorically
false.  Building the external trusted controller and continuously binding the
enumerated OS lifecycle remains mandatory before checkpoint qualification.

### Trusted-controller host feasibility decision

An independent read-only feasibility audit confirms that another same-process
candidate record would not advance authentication.  The host does provide a
useful unprivileged kernel subset: nested user/mount/PID/network namespaces,
private procfs and tmpfs, held-FD read-only bind mounts, parent ptrace, pidfds
including `pidfd_getfd`, subreaping, and Btrfs fs-verity support.  Focused live
pidfd parent/reap and ptrace exec-gate tests passed.  These facilities are
enough for an isolated prototype, but not for the accepted release threat
model in which arbitrary same-UID ancestors and peers are untrusted.

The decisive host gaps are concrete.  The session is UID 1001 with no
capabilities, `NoNewPrivs=1`, no passwordless sudo, no visible/delegated cgroup
v2 controller, and no protected service identity, signing key, or evidence
spool.  The current ptrace gate detaches immediately after its first exec;
resource evidence periodically scans one process group; READY/action records
are cooperative JSON; and the process-tree list is caller-predeclared.  None
of those mechanisms continuously binds fork/clone/setsid activity, the DMTCP
restore boundary, short resource peaks, or resumed execution before user code.

DMTCP 4.1.0 also accepts checkpoint images by `.dmtcp` pathname rather than by
already authenticated file descriptor: it checks the pathname and later
opens it.  Holding and rehashing an FD is therefore insufficient.  A viable
design must fs-verity-seal each closed image, bind-mount every held image FD
over its exact relative pathname in a private read-only mirror, protect
`mtcp_restart` and optional decompression helpers, and continuously trace the
restart/plugin gate.  A read-only directory alone does not protect the
owner-controlled backing in another namespace.

Checkpoint qualification is consequently **not deployable in this session as
currently provisioned**.  It requires a protected external launcher/finalizer
with a one-use signed challenge, a delegated cgroup (plus quota-backed disk
enforcement), continuous ptrace/pidfd lifecycle collection, a credentialed
kernel action channel, and a new signed attestation overlay over the existing
hard-false records.  The smallest meaningful implementation slice begins by
establishing that external trust root; adding more untrusted observations
first would only enlarge the scaffold.  This blocks checkpoint-based release
acceleration, not the active pristine replay or ordinary two-clean-run S3
path, so no current process was interrupted and no qualification flag changed.

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

An integration audit then found that the host-refresh branch and the direct
schema-6 consumption branch were siblings, not ancestor and descendant.  The
host-only `6fad64c` therefore was not a valid final repin base: it lacked the
LP-certificate consumption closure implemented through direct-consumption
commit `5e75cb9047136ffcb3a3a659ba546c93965bfeda`.  The reviewed integration
branch `codex/flyspeck-v13-schema6-host-runtime-base` starts at that schema-6
head and replays the two exact host-refresh patches.  Their patch IDs are
unchanged at integration commits `bd0b5ac` and `4ab444a`.

That integration correctly invalidated the previously generated 20-input
pilot descriptor.  Its fail-closed check identified four stale authority
fields: the full-build source hash, loader source hash, manifest byte count,
and manifest hash.  Regeneration changed only those four fields.  Commit
`c2f7888d1cc25a3a6de4c159d36f111d6a613790` records the repaired fixed point
and is now the exact pre-repin Candle base.  At that clean commit:

- the manifest closes 297 roots, 400 source nodes, and 43 generated inputs;
- the exact 20-input pilot and 400-input all-inventory checks pass;
- the focused and broad suites pass 96/96 and 227/227 respectively;
- sanitized and ordinary complete discoveries both pass 339/339, in 160.499
  and 160.720 seconds, with about 326 MiB maximum RSS and no swap; and
- the generated manifest, pilot, and all-inventory SHA-256 values are
  `e928b7aa8fc6712822e29987cc2f68e39fac1e77a6d0b62d0d4b7c35ccf84fe7`,
  `60485ad5e32dbc80f6bbca183f0b603ff6fe2e2798bbc3e15f0dd059fc95b761`,
  and `d5b282bac746bca86d9a6d139c3964c8f1ced0a514df3d167eb1cb2c55e2f84b`.

These checks establish source-plan and host-tool consistency, not compiler
qualification or a compiled parser result.  The final Candle repin must use a
fresh branch from `c2f7888`, after the cold replay publishes its authenticated
terminal authority.  Neither host-only `6fad64c`, old `688d9d1`, nor stale
prepared commit `103691ef` may be promoted.

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

The frozen replay is now active at
`/project/flyspeck-candle-runs/cakeml-dopen-cold-c2e26f43c-attempt-001` in a
product-empty detached CakeML worktree.  It binds CakeML `c2e26f43c...`, HOL4
`a390cbabd...`, frozen controller project `5ef9419cc...`, one Holmake job and
one HOL worker thread under the recorded 112.5-GiB virtual-address-space
ceiling.  The base CakeML heap passed in 2m16.27s at 978,608 KiB maximum RSS;
`cake_compile_heap` passed in 1h43m04s at 5,520,316 KiB maximum RSS.

At this report revision, the cold `compiler64Prog` stage has rebuilt and
exported `to_closProg` (11m23s), `to_bvlProg` (8m37s), `to_dataProg`
(4m21s), `lexerProg` (4m28s), generic `parserProg` (14m01s), `caml_lexProg`
(11m02s), the large `caml_parserProg` (36m45s), `pancake_lexProg` (3m53s),
`pancake_parseProg` (4m47s), and `reg_allocProg` (26m42s).  The remaining
dependency count has since fallen from 25 to 12.  `inferProg` passed in
41m29s, saving the cold `open_ienv_v_thm` and `infer_open_v_thm` before the
declaration-inference translation and theory export.  `explorerProg`,
`decodeProg`, `sexp_parserProg`, `basis_defProg`, and `printingProg` then
exported in 8m49s, 8m43s, 7m07s, 15m14s, and 3m54s.  `to_word64Prog` then
exported successfully in 48m15s, reducing the dependency count from nine to
eight.  `to_target64Prog` and `from_pancake64Prog` subsequently exported in
22m48s and 27m32s.  The serial architecture chain then exported `x64Prog`,
`arm8Prog`, `riscvProg`, and `mipsProg` in 10m50s, 11m38s, 11m48s, and
13m44s.  The previously overlooked `repl_init_types` dependency exported in
50.6s; the dependency count is now one and the final `compiler64Prog`
translation is active.  The large parser peaked near 31 GiB RSS;
combined cold replay plus the separate PFT oracle remained near or below
70 GiB, so the exceptional 120-GiB allowance was not needed.  This is a live
interim milestone only: stage 2, the x64 bootstrap, the x64 proof, the terminal
manifest, and the public gate all remain pending.

### Post-terminal repin handoff audit

An independent read-only adversarial audit conditionally accepts the planned
repin **only after** the controller-printed terminal-manifest digest and empty
replay process group exist.  It confirms that a fresh branch directly from
`c2f7888d1cc25a3a6de4c159d36f111d6a613790` closes over exactly eight tracked
paths and no hidden ninth artifact.  Five primary pin sites occur in the
manifest generator, generated manifest, two tests, and diagnostic document;
regeneration then changes the pilot descriptor, all-inventory descriptor, and
the two corresponding hashes in `flyspeck_all_inventory_sources.py`.

The equal-length `964406...` to `c2e26f43...` substitution predicts these
fixed-point identities.  They are stop-on-mismatch expectations, not a
substitute for actual regeneration:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| manifest | 821,669 | `ea6d061cdb23327e41e85387eec82ca5a88d51647c985f67f80eabf80fc65740` |
| pilot | 14,715 | `1ed2cf50bafc057d16eb8358fd6396103004c0f12f36783a4f3b279437720e3e` |
| all inventory | 206,558 | `e368343e85a844219e73403b21e1683554766ff87d3a9f8a797d6186d720a705` |

The manifest writer also rewrites two generated ML files even though the pin
does not affect their source graph.  They must remain byte-identical to the
current `c2f7888` baselines:

- `flyspeck_source_digests.ml`:
  `ccd3784a1d6a9c8ca29aac1e881fca6d97ac68d593a34a64901da74ad776ae02`;
- `flyspeck_full_build.ml`:
  `62f3400d87d28f1e0cdd7f02dd6b0b7adedb7cfede7a0bac6f511298e5b1dacf`.

The final procedure must generate both descriptors to fresh temporary files,
verify their exact identities, replace them atomically, and then require the
exact eight-file diff before committing.  Runtime parser plans are materialized
only after that commit and the public gate.  Prepared commit `103691ef` is
categorically not reusable: it has the wrong parent and old pin, and differs
from `c2f7888` in twenty paths.  The final fresh worktree and reserved branch
remain absent during the active cold replay.
