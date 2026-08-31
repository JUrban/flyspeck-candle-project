# Parser proof repair and replay checkpoint (2026-08-30)

## Status

> Update at 03:08 UTC: the `ca67ffaa...` replay described below exposed a
> second, narrower proof obligation and is now retained as a failed attempt.
> The current repair is CakeML `586e06883d44f5c447793597bdaf0aa76e7a9952`,
> and its fresh replay is recorded in the final section of this report.  No
> Candle repin is authorized until that replay passes all four stages.

The first exact four-stage replay at CakeML
`964406486a52e1a53a94eade4cf86a666dc8055a` failed in
`compiler64ProgTheory.uo`.  This was a deterministic HOL source failure, not a
resource exhaustion or concurrency failure.  The failed run is retained at:

`/project/flyspeck-candle-runs/cakeml-parser-diagnostic-proof-964406486`

Its controller PID was `2270138`.  It remains at stage
`compiler64ProgTheory.uo` and intentionally has no `finished_utc` marker.

The repair is CakeML commit
`ca67ffaa831845c20c905bf94924b457951f8968` (`proof: avoid stdio overload
capture`) on `codex/flyspeck-v13-runtime-stack`.  A fresh exact replay is active
at:

`/project/flyspeck-candle-runs/cakeml-parser-diagnostic-proof-ca67ffaa8-attempt-001`

Its controller PID and process group are both `3291501`.  The replay is serial
(`Holmake -j1 --mt=1`) and has a `117964800` KiB address-space ceiling.  This
checkpoint does not claim replay success; all four zero-exit time receipts and
all six postconditions remain required before the Candle pin may move.

## Exact failure

The retained receipts establish:

- `cake_compile_heap`: exit 0, elapsed `1:42:57`, maximum RSS `6399540` KiB,
  zero swaps;
- `compiler64ProgTheory.uo`: exit 1, elapsed `11:10:50`, maximum RSS
  `39814640` KiB, zero swaps.

The latter elapsed time includes its dependency chain.  At the final
`compiler64ProgScript.sml` build, HOL reported that the argument named
`stdout` had type `IO_fs -> mlstring -> bool`, rather than `mlstring`, in:

`add_stdout (fastForwardFD fs 0) stdout`

The local pattern variables `stdout` and `stderr` collided with imported stdio
overloads.  Earlier parser-diagnostic translations and reply lemmas had already
been saved; the failure occurred when defining the filesystem transformer at
lines 721--728 of the pre-repair source.

## Repair and checks

The repair alpha-renames the HOL variables to `reply_out` and `reply_err` in
the reply definitions and every downstream specification/theorem.  It does not
change the executable CakeML locals that are legitimately named `stdout` and
`stderr`.  A structural regression extracts both affected definitions and all
nine downstream theorem blocks, and rejects a bare `stdout` or `stderr` token
in any of them.

The focused x64 parser-diagnostic suite passes 6/6.  An independent exact-diff
review classified the patch as alpha-only and found no P0, P1, or P2 issue.
The old names can be mechanically restored to reproduce the pre-repair SML
source byte-for-byte.

## Replay discipline

The repaired replay uses clean exact heads:

- CakeML `ca67ffaa831845c20c905bf94924b457951f8968`;
- HOL4 `a390cbabd3a4521bab4ee20281e3e42933a8a3ae`.

It requests, in order:

1. `cv_translator/cake_compile_heap`;
2. `compiler/bootstrap/translation/compiler64ProgTheory.uo`;
3. `compiler/bootstrap/compilation/x64/64/x64BootstrapTheory.uo`;
4. `compiler/bootstrap/compilation/x64/64/proofs/x64BootstrapProofTheory.uo`.

No other `Holmake` may run concurrently.  The long PFT trace remains a P1-only
oracle and is not proof evidence.  The reference sweep remains serial and is
not restarted.  The old CakeML/Candle pin, linked runtime, parser plans, and
gate handoffs remain authoritative only as historical/preparation artifacts;
at that launch they were expected to be regenerated against `ca67ffaa...`
only after this replay passed.  The following section supersedes that target.

## Second proof frontier and repair

The `ca67ffaa...` replay proved that the overload-capture repair was effective:
the parser-diagnostic definitions and translations were saved through
`compiler64Prog_env_316`, and the original `stdout` type error did not recur.
It then failed at the top-level theorem
`run_candle_parser_diagnostic_ok_spec`.  The exact remaining goal required the
final `TextIOProof.print_spec` application to establish stdout state with the
semantic string `reply_out`; the generic `xapp \\ xsimpl` sequence had not
provided that existential witness.

CakeML commit `586e06883d44f5c447793597bdaf0aa76e7a9952` (`proof: bind
parser diagnostic print replies`) replaces that final application with
`xapp_spec print_spec`, `qexists_tac reply_out`, and `xsimpl`.  It makes the
same witness explicit for the corresponding first print in the error proof.
This changes proof scripts only; it neither weakens a theorem nor changes the
translated runtime definition.  The regression requires exactly one ordered,
adjacent witness sequence in each theorem block and passes 7/7.  Independent
review of exact diff SHA-256
`e1aafed8d6b60524276a3b893c95556557a84392ba4ac794aad060c988c44903`
reported no P0, P1, or P2 finding.

The retained failed attempt is:

`/project/flyspeck-candle-runs/cakeml-parser-diagnostic-proof-ca67ffaa8-attempt-001`

Stage 1 reused the authenticated dependency products and passed in 24.60
seconds with zero swaps.  Stage 2 printed the terminal proof failure at
02:49:45 UTC.  HOL then consumed CPU without log or receipt progress for more
than the announced 15-minute unwind window.  After exact identity checks, one
`SIGINT` was sent at 03:06:31 UTC to authenticated replay process group
`3291501` only.  The controller and sole Holmake exited, the timing receipt
closed as signal 2 after 1:06:44, and no `finished_utc` was created.  The PFT,
reference sweep, and sampler were in other process groups and were not
signalled.  `intervention.txt` records the decision.  The committed sampler
auto-sealed mode 0444 with 119 samples, no alerts, and a terminal
`controller-exited` record.

## Current exact replay

The cached clean build worktree was fast-forwarded to `586e06883...` only
after the failed controller closed.  A fresh replay now runs at:

`/project/flyspeck-candle-runs/cakeml-parser-diagnostic-proof-586e06883-attempt-001`

Its controller PID/process group is `3395323`, with `/proc` start ticks
`317525210`.  The clean pinned HOL4 head remains
`a390cbabd3a4521bab4ee20281e3e42933a8a3ae`.  The four targets, serial
`Holmake -j1 --mt=1` discipline, and `117964800` KiB address-space ceiling are
unchanged.  The committed fail-closed sampler is PID `3395459` and also
observes, but cannot control, the PFT and reference scopes.  At launch the
host had about 190 GiB available; tracked scopes had zero swap I/O.  The host
swap device remained mostly allocated by unrelated historical state, so live
page-in/page-out and available-memory conditions remain authoritative.

This is an active proof replay, not a pass.  Candle must be repinned to
`586e06883...`, not `ca67ffaa...`, only after all four exact stages and six
postconditions succeed.

## Resumable-heap diagnosis and third repair

The later `68946a69f...` replay again reached
`run_candle_parser_diagnostic_ok_spec` and failed deterministically.  Its
stage-2 receipt closed normally after `1:13:34`, with maximum RSS
`40335900` KiB, zero swaps, and exit 1.  This was not a resource failure.  HOL
saved a native proof heap at the failed goal; a copy is retained outside the
CakeML worktree at:

`/project/flyspeck-candle-runs/cakeml-parser-diagnostic-proof-68946a69f-attempt-001/compiler64Prog.run_candle_parser_diagnostic_ok_spec.dumpedheap`

Its SHA-256 is
`059bc3779aefde87cd44969500caeafe1c1ed68bceb980079210434b8bb83da1`.
Loading that heap made it possible to diagnose and prove both run-level
theorems interactively without repeating the expensive translation prefix.
The successful compact source-form tactics were then replayed a second time
inside the resumed state to check tactic-combinator precedence.

The exact source defects were:

- `rename` did not select the existential `stdin` assumption;
- the translated leading unit `let` required `xcon \\ xsimpl`, followed by a
  distinct `openStdIn` step;
- the success `inputAll` frame required the explicit `emp` witness;
- the error stdout and stderr calls required complete, ordered witnesses for
  the semantic reply string, residual `RUNTIME`, and filesystem state.

CakeML commit `9e1bd759fe0e1d4f4afc91bd25601423131a7d28`
(`proof: repair parser diagnostic stdio frames`) contains only those proof and
focused-regression repairs.  The focused suite passes 7/7.  Both theorem
statements were proved unchanged in the resumed exact theory state.

This also validates one immediately useful point from the external speed
advice: native failed-goal heaps are a practical proof-development cache.  They
do not replace a clean replay or authorize a pin, but they remove repeated
hour-long prefixes from local theorem repair.

## Current replay at `9e1bd759f...`

The reusable committed controller at project commit `075857e` launched a
fresh serial four-stage replay at:

`/project/flyspeck-candle-runs/cakeml-parser-diagnostic-proof-9e1bd759f-attempt-001`

The controller PID/process group is `3469592`, with `/proc` start ticks
`318581076`; the read-only sampler PID is `3469958`.  CakeML is pinned to
`9e1bd759fe0e1d4f4afc91bd25601423131a7d28` and HOL4 remains pinned to
`a390cbabd3a4521bab4ee20281e3e42933a8a3ae`.  Stage 1 passed and stage 2 is
active.  The controller is serial (`-j1 --mt=1`) and its address-space limit is
`117964800` KiB.  This is an active replay, not a success claim; Candle remains
unrepinned until all four receipts and all six postconditions pass.

## Capability/main-frame checkpoint repair and replay at `d5d7ae8cc...`

The `9e1bd759f...` replay closed normally in stage 2 with exit 1 after
`1:16:59`, maximum RSS `32029000` KiB, and zero swaps.  It saved both repaired
run-level theorems, then failed at
`main_candle_parser_diagnostic_capability_spec`.  This was another proof
failure, not a resource failure.  The exact failed-goal heap is retained at:

`/project/flyspeck-candle-runs/cakeml-parser-diagnostic-proof-9e1bd759f-attempt-001/compiler64Prog.main_candle_parser_diagnostic_capability_spec.dumpedheap`

The retained 12,131,483,840-byte heap has SHA-256
`496cfc2eea94a132fdcf68a7a823beb1289ddf9a4a8202ca5d4fa7dd54c5db24`.
It exposed two successive defects without another hour-long translation:

- the extended `main` evaluates the new capability predicate in a third
  translated `let`, but all four `main_v` proofs still attempted `xif` after
  only the unit and command-line `let`s;
- the capability `print_spec` and both diagnostic-run specs required their
  residual `COMMANDLINE` frames and semantic/filesystem witnesses explicitly.

The compact capability, successful-run, and error-run tactics were proved in
the resumed heap.  The capability tactic was then replayed from the untouched
saved goal in one complete source-form command.  The ordinary `main_spec`
received the same generated-prefix repair; an independent no-edit review found
no P0/P1 defect and confirmed that source-local `fetch "-"` is correct during
the `compiler64Prog` theory build.  Focused structural tests now pass 9/9 and
hostile-mutate the capability branch, all ordered frames, the error nonce
conjunction, and the ordinary third-`let` prefix.

CakeML commit `d5d7ae8cc69050da41984d61fd65b0d46e6b4f2e`
(`proof: repair parser diagnostic main frames`) contains the proof and focused
regression changes.  A fresh serial four-stage replay is active at:

`/project/flyspeck-candle-runs/cakeml-parser-diagnostic-proof-d5d7ae8cc-attempt-001`

Its controller PID/process group is `3519885`, with `/proc` start ticks
`319205058`; sampler PID is `3520157`.  Stage 1 passed in 8.77 seconds and
stage 2 is active.  The sampler initially observed about 23.8 GiB across the
canonical, PFT, and reference scopes, about 188 GiB available, no swap I/O,
and no alerts.  The replay remains `-j1 --mt=1` under the user-authorized
`117964800` KiB address-space limit.  It is not a success claim and does not
authorize a Candle repin.

## Success-witness and ordinary-dispatch frontiers

The `d5d7ae8cc...` replay saved both run-level specifications and the
capability branch, then failed at
`main_candle_parser_diagnostic_ok_spec`.  Stage 2 closed normally after
`1:13:22`, with maximum RSS `31369484` KiB, zero swaps, and exit 1.  The exact
12,131,528,096-byte failed-goal heap is retained under that attempt with
SHA-256
`65d220133a2514b3ee41e6960aad70eafa8779b8ab9b6e4d7ff5e5c8af7232e7`.

The resumed goal showed that the diagnostic-success application needed an
`xsimpl` step before the already explicit command-line, reply, filesystem,
input, and nonce witnesses.  CakeML commit
`2c3f20f536d54f4c981c2195d4d6636ff3203e9b` adds only that step.  Its fresh
replay saved the success and error main specifications, then failed later at
the legacy ordinary `main_spec`.  Stage 2 again closed normally after
`1:14:58`, with maximum RSS `35343440` KiB, zero swaps, and exit 1.  Its exact
12,131,625,616-byte `main_spec` heap is retained with SHA-256
`e0cf64eac971fbe17a5a20c9134b0a9cee6a735cb4e9999ccddd45064801afcf`.

That checkpoint exposed a source-shape change in the ordinary dispatch proof:
the new capability predicate's false branch required the explicit boolean
witness `F`, while a duplicated legacy `xlet_auto` no longer corresponded to
the translated program.  CakeML commit
`a054e700c600905ea4051221037e5062a2f8f1d6` makes those two proof-only
repairs.  Its replay saved `main_spec`, proving that the ordinary path was
repaired, plus the capability and success whole-program specifications.  It
then reached a still narrower failure at
`main_candle_parser_diagnostic_error_whole_prog_spec`.

## Error whole-program repair at `9383815a3...`

The `a054e700c...` stage-2 receipt closed after `1:16:06`, maximum RSS
`35905504` KiB, zero swaps, and exit 1.  Its 12,131,750,936-byte failed-goal
heap is retained at:

`/project/flyspeck-candle-runs/cakeml-parser-diagnostic-proof-a054e700c-attempt-001/compiler64Prog.main_candle_parser_diagnostic_error_whole_prog_spec.dumpedheap`

The retained heap has SHA-256
`4bc789b913a6f755af5c217ac8638ab3b7ce9de7c6996c40fc02011cdc9b9c6b`;
the same artifact root contains closed failure and repair-proof receipts.  The
old abbreviation tactic expected an equality whose left side was a filesystem
variable, but the unfolded goal directly exposed the filesystem expression.
Supplying the exact expected
`add_stderr (add_stdout (fastForwardFD ...))` witness proves the unchanged
goal.  The saved-heap replay printed `Initial goal proved` in 25.15 seconds,
used maximum RSS `12003392` KiB, and had zero swaps.

CakeML commit `9383815a3e3c4feb94b4a95b20183567fe13a3a4`
(`Prove parser diagnostic error whole-program spec`) contains only that
direct-witness proof repair.  A fresh canonical four-stage replay is active
at:

`/project/flyspeck-candle-runs/cakeml-parser-diagnostic-proof-9383815a3-attempt-001`

Its controller/process group is `3623260`; HOL4 remains exact commit
`a390cbabd3a4521bab4ee20281e3e42933a8a3ae`.  Stage 1 passed and stage 2 is
active under serial `Holmake -j1 --mt=1`.  At the recorded checkpoint the
proof process used about 20 GiB RSS and the host still had about 170 GiB
available.  This remains an active development replay, not proof success or
compiler qualification.  Candle stays pinned to its prior compiler until all
four stages and the controller's six postconditions pass.

## Eval-state FFI-divergence repair at `0e75b7e42...`

The `9383815a3...` stage 2 saved the repaired diagnostic-error whole-program
specification and the ordinary semantic theorem, then failed in the custom
reuse helper with `raw_match_term: different constructors`.  Its receipt
closed after `1:02:29`, maximum RSS `42632364` KiB, zero swaps, and exit 1.
Stages 3 and 4 were not launched, and no Candle repin was made.

Two read-only retained-heap diagnostics separated theorem selection from code
reuse.  The declaration conclusion was alpha-equivalent before and after the
ordinary `prove_sem_thm`.  Capability and successful diagnostic modes matched
only `whole_prog_spec_IMP'`, and an explicit capability replay then passed
every conversion through SNOC removal, reuse of `compiler64_prog`, LET
elimination, namespace lookup, FFI equality and basis-reference discharge.
The error mode alone failed: its declaration state has the translated
eval-state override, while CakeML exposed only the non-overridden
`whole_prog_spec_ffidiv_IMP`.  The general semantics theorem already supports
an arbitrary eval state; the missing link was its exported implication.

CakeML commit `0e75b7e423294fad11320cb26cbcf137a3b3d5d7`
(`Support eval-state FFI-divergence semantics`) adds
`whole_prog_spec_ffidiv_IMP'`, teaches the common and source-local semantic
helpers to select it, and changes no generated program or runtime behavior.
A single-theory qualification rebuilt `basis_ffiTheory.uo` successfully in
`2:34.28`, maximum RSS `3216844` KiB, zero swaps; the updated library target
also passed in `8.48` seconds.  The retained logs have SHA-256
`16c0705ef43f053a1e5b02178ee39150fdf3b2a82406c250061c08425b8c3417`
and `65fbd434510d9988add24a3d3361fa00f2329084dd4f627f2e39625c13ed9e11`.

A fresh serial four-stage replay is active at:

`/project/flyspeck-candle-runs/cakeml-parser-diagnostic-proof-0e75b7e42-attempt-001`

HOL4 remains exact commit
`a390cbabd3a4521bab4ee20281e3e42933a8a3ae`.  Stage 1 passed and stage 2 is
active under `-j1 --mt=1` and the `117964800` KiB address-space limit.  This
is still development evidence, not compiler qualification; Candle remains on
the prior compiler pin unless all four stages and the postflight gate pass.

## Dopen reverse-dependency proof frontier at `77b769a99...`

The `0e75b7e42...` replay completed the first three stages and failed normally
in stage 4.  The exact receipts are:

- stage 1: pass in `0:08.08`, maximum RSS `144508` KiB;
- stage 2: pass in `4:51:01`, maximum RSS `47587112` KiB;
- stage 3: pass in `1:02:38`, maximum RSS `80940752` KiB; and
- stage 4: fail in `13:43.93`, maximum RSS `3355712` KiB.

Every receipt records zero swaps.  The first stage-4 failure was the previously
omitted `Dopen` case of `candle_prover_evaluate.evaluate_v_ok`; therefore the
artifact remains immutable failed development evidence and does not authorize
a compiler or Candle repin.

Three proof-only CakeML checkpoints now close the discovered Dopen gaps:

- `672e533bc` proves that opening a declaration environment preserves the
  Candle `env_ok` invariant and discharges the `evaluate_v_ok` Dopen case;
- `6436326ce` exports the environment-opening invariant and discharges the
  corresponding `candle_basis_evaluate` case; and
- `77b769a99` proves the source evaluator's environment relation is equivalent
  to the exported namespace `nsAll2` relation, transports it through
  `nsAll2_after_nsOpen`, and discharges `source_evalProof.eval_simulation`.

Focused builds passed unchanged theorem statements: `candle_prover_evaluate`
in about 2m10s, `candle_basis_evaluate` in about 1m21s,
`candle_prover_semantics` in about 3m15s, and `source_evalProof` in 1m58s.  The
last used maximum RSS `757320` KiB and zero swaps.  None of these proofs uses
an admission, omitted proof, or new axiom.

The first separately labelled warm reverse-dependency replay is retained at:

`/project/flyspeck-candle-runs/cakeml-parser-dopen-warm-proof-6436326ce-attempt-001`

It preserved the exact stage-3 `cake.S`, configuration and x64-bootstrap
theory hashes before and after the run, built through dependency 95 of the
110-theory countdown, and then exposed the `source_evalProof` Dopen case.  It
failed after `11:05.67`, maximum RSS `1410248` KiB, zero swaps.  Its receipt
classifies it explicitly as a warm incremental regression, not qualification.

After the focused `source_evalProof` pass, warm attempt 002 was launched at:

`/project/flyspeck-candle-runs/cakeml-parser-dopen-warm-proof-77b769a99-attempt-002`

It is serial (`-j1 --mt=1`), capped at `117964800` KiB virtual address space,
and hashes the same four reused stage-3 artifacts before and after execution.
At this checkpoint it has passed the repaired source-evaluation dependency and
is traversing the remaining 93-theory static backlog.  This remains an active
developer replay.  A final qualifying result still requires a new clean
worktree and a fresh four-stage cold replay at the eventual final head.

## Source-to-flat exact-domain frontier after warm attempt 002

Warm attempt 002 is now sealed as failed development evidence.  Its immutable
artifact is:

`/project/flyspeck-candle-runs/cakeml-parser-dopen-warm-proof-77b769a99-attempt-002`

The run exited 1 after `1:10:02`, used at most `2410580` KiB RSS, and recorded
zero swaps.  All four reused stage-3 hashes were identical before and after
the run.  The log SHA-256 is
`4752aa07f9a147f395fa8e4cf018d6275ad71d4f45f558a04323bfa19e8f98b0` and
the timing-record SHA-256 is
`f39b9e7ec87df810e27f7eae7a5eeabc1dd3c5d20f540db8f64ae9ad1a1eff12`.

The repaired source-evaluator theorem passed.  The replay then completed 43 of
the 93 remaining theories, through `flat_elim`, before
`source_to_flatProofScript.sml` failed while rebuilding `compile_correct`.
The unsolved declaration case is `Dopen`: source evaluation successfully opens
the named module, compilation emits no flat declarations, but the proof cannot
recover the required flat environment relation after the open.

This is not just a missing tactic branch.  The existing `global_env_inv` is a
one-way lookup invariant, so the compiler namespace may contain names absent
from the semantic namespace selected by `open_dec_env`.  Such extra names can
also incorrectly shadow later outer bindings.  A sound repair therefore needs
an exact environment-domain premise, its preservation through namespace open,
and propagation through suspended dynamic-evaluation environments and the
initial global environment.  The saved failing heap is retained at:

`/project/worktrees/cakeml-flyspeck-runtime-stack-v13/compiler/backend/proofs/source_to_flatProof.compile_correct.dumpedheap`

That proof repair is active on a separate development branch.  No admission,
compiler qualification, Candle repin, or 20/400 gate is claimed from this
failure.  The next warm replay will start only after the focused
`source_to_flatProof` target passes at a committed CakeML head; final
qualification still requires the clean cold four-stage replay.

## Isolated proof-worktree metadata incident

While preparing a focused `source_to_flatProof` build, a development-only
cache copy accidentally included the source worktree's `.git` indirection
file.  The isolated directory consequently pointed at the main
`codex/flyspeck-v13-runtime-stack` worktree metadata even though Git's worktree
registry still held a separate `codex/flyspeck-v13-source-to-flat-dopen`
entry.  This was detected before accepting a proof result.

The build wrapper and its surviving HOL child were terminated.  The main
runtime-stack worktree was verified clean at `77b769a99`; the isolated
directory contained only the intended uncommitted `source_to_flatProofScript`
change.  Its `.git` pointer was restored to the registered isolated gitdir,
after which its branch, head and diff were rechecked.  The interrupted build
is discarded as evidence.  A new focused developer build may proceed only
after an immediate preflight branch-pointer check and must recheck that pointer
after completion.  No generated cache copy may include `.git` or other
repository metadata.

## Focused exact-domain proof propagation

The exact-domain repair is being developed and checked in the restored
isolated worktree before it is eligible for integration.  Five labelled
focused runs have so far produced the following development evidence:

- attempt 001 failed in `open_env_invs` after `1:31.08`, maximum RSS
  `1131868` KiB and zero swaps.  The proof had left an existential source
  namespace after `irule`; a direct relational consequence closes it;
- attempt 002 progressed within `open_env_invs` and failed after `1:32.70`,
  maximum RSS `961932` KiB and zero swaps.  It exposed that
  `global_env_inv` is one outer conjunction whose value and constructor
  relations form an inner conjunction, rather than two outer conjuncts;
- attempt 003 passed the open-environment and stored-environment lookup
  lemmas, then failed at the strengthened exact-domain conclusion of
  `do_eval` after `1:55.02`, maximum RSS `1097164` KiB and zero swaps.  The
  existing `src_orac_env_invs_lookup_env` result supplies that conclusion;
- attempt 004 is excluded from proof evidence: it was a zero-second setup
  failure caused by invoking `Holmake` without its required `PATH`; and
- attempt 005 passed both `open_env_invs` and the strengthened `do_eval`
  proof, then failed in `declare_env_store_env_id` after `2:05.50`, maximum
  RSS `1117000` KiB and zero swaps.  The stored suspended environment now
  legitimately needs the exact-domain relation in addition to the existing
  global-environment invariant.

The relevant immutable log SHA-256 values for attempts 001, 002, 003 and 005
are respectively
`d84b8b10879ea303f8baeccfdde20003557f410a346c08a62d1aa8134e58af79`,
`d84b8b10879ea303f8baeccfdde20003557f410a346c08a62d1aa8134e58af79`,
`198179653626ebac47a5ba210a10dae0e8a7b3d7b17fdab8bdc207dce8cb3f65`
and
`3878b7e68564ecb746274a0329064a213c0dfb0bea3ba995f3d174e592a9b57b`.
Their timing-record hashes are
`b9b714eb4332fc3b78f158b3e04f08305dfbc04bdc63b92e1bb1fe63ce7e0420`,
`30236007e05b1af246e0dd64bc4a054778ae433c43187b6da3289627855`,
`fb75e6b0117683e2469b8d956ed1768a382f6e878da92000ab844aac5dcda6c9`
and
`5fa392bb3d9508af900b7e6c5a803509b08c596656afc5e95bfab77224f295dc`.

The strengthened `declare_env_store_env_id` theorem itself now verifies in
the saved heap when its successful declaration result requires both
`global_env_inv` and `env_domain_eq`.  Its evaluator consumer still has to
join the initial and successful-result exact-domain facts through environment
append, alongside the pre-existing global-invariant append/weakening proof.
That consumer repair and a fresh focused target are still in progress.  None
of these attempts is compiler qualification or authorizes a Candle repin.

Focused attempt 006 passed all of those earlier proof frontiers and saved the
strengthened `declare_env_store_env_id` theorem.  It then failed while
composing the two already-verified App consumer children: the tactic used one
selected-child branch followed by a trailing all-goals combinator, which left
`FIRST_ASSUM` with no matching assumption.  The printed parent was the
declaration-result conjunct, not a new semantic obligation.  The run failed
normally after `2:23.92`, maximum RSS `1118224` KiB and zero swaps; its log and
timing-record SHA-256 values are
`232abb446b093c032cf21e999dcb64ff98d943f7175dd9f5a1d5e0d4719685ed` and
`b89cbf1f62e8c51523010199f0d1ee69dbbf5bd10f867bf366c21bfa86593021`.
The isolated branch, head and `.git` pointer passed the postflight check.  A
deterministic two-selected-child composition was verified in the saved App
state and focused attempt 007 is replaying that exact proof text.

## App proof replay after exact-domain propagation

Focused attempts 007 through 018 are retained under the corresponding
`/project/flyspeck-candle-runs/cakeml-source-to-flat-dopen-focused-77b769a99-attempt-NNN`
directories.  Every executable proof replay used one HOL worker, recorded zero
swaps and stayed between `943056` and `1709088` KiB maximum RSS.  The ordinary
replays took between `2:05.36` and `2:27.16`; attempt 008 was a diagnostic SML
marker setup error and is excluded from proof evidence.

These runs first established that the strengthened suspended-environment
theorem and both exact-domain append children replay completely.  The later
failures were all pre-existing order-dependent `FIRST_ASSUM` searches in the
large App proof after its declaration induction hypothesis acquired the new
premise.  Diagnostic attempts 009--012 localized and printed the normalized
Opapp state.  Attempts 013--015 then replaced the ambiguous search with the
exact normalized expression-evaluation induction hypothesis; markers in 015
proved selection, all three premises, clock simplification, application of the
IH result and completion of the entire Opapp branch.

Attempts 016--017 similarly showed that the first five Force `sv_rel` lookups
complete and printed the sixth unevaluated-error state.  Its intended premise
is the exact universal relation between `st'.refs` and `TL s'_i1.refs`, at the
known reference index; attempt 018 passed the resulting full-shape selector.
It then exposed one later order-dependent search after that witness.  Focused
attempt 019 is localizing only that next operation.  No theorem statement,
semantic definition, axiom set or abort case has been weakened during this
tactic hardening.

For the last four completed replays, the immutable log/timing SHA-256 pairs
are: attempt 015
`7d940ddef0c6204521b36ab77ea048481f35acad97ffee41409baae0a35a89a2` /
`8a0d2358af7dc882c4e1d01b824bbfd76c688154d4b3307ad18383ec2ec4118f`;
attempt 016
`793f1a931989c6f7faef6e0637b02303246481c3c2035aa18c030465114a3162` /
`ece25ac1eb243655ea8aeacbdf35cb5323e210a9c7d46ea3f325c1a0c72f4611`;
attempt 017
`843ec790cefc2933879d8b9da2f6b5db375519d3e925c305d52a304903423356` /
`ea59d4fbf59a9a0a9882de33803a6eb8a6c34239844a57165d36a6b842558179`;
and attempt 018
`232abb446b093c032cf21e999dcb64ff98d943f7175dd9f5a1d5e0d4719685ed` /
`7e677ff3c6cb52dac84a7e694a1cff262d004773fe219122a61fa6855286c353`.
None is qualification or authorizes a compiler/Candle repin.

## App closure and normalized Log frontier

Focused attempts 019 through 027 continued in the restored isolated proof
worktree at exact base `77b769a99`.  Each run used one HOL worker, recorded
zero swaps, failed normally without changing repository metadata, and is
retained below the corresponding
`cakeml-source-to-flat-dopen-focused-77b769a99-attempt-NNN` artifact root.
Wall times ranged from `2:16.70` to `2:30.06`; maximum RSS ranged from
`1112700` to `2109672` KiB.

Attempts 019--021 proved the remaining Force error witness, recursive
expression IH, result-relation split, entire Force branch and generic App
application/state facts.  They then progressed through the generic App
existential witness and its immediate result children.  Attempts 022--023
isolated the remaining invariant projection and replaced its ambiguous
assumption search with the exact `invariant interp g gen genv2 ...` premise.
The targeted simplification closed App's sole remaining goal: attempt 024
entered `Resume compile_correct[Log]`, conclusively establishing complete App
replay under the strengthened theorem.

The first Log failure was again an old order-dependent `first_x_assum`: its
state contained both the conditional second-expression IH and the ordinary
first-expression IH.  Attempt 024 printed both; attempt 025 selected the
ordinary five-antecedent source-state shape and passed it.  The later
conditional-expression selector then failed.  Attempt 026 deliberately tested
and rejected an over-specific guessed shape.  Attempt 027 printed the exact
normalized theorem: after the abort premise has already been discharged, the
conditional IH has four antecedents--the invariant at `st'`, environment
relation, length equality and eval-state generation relation.  The next
replay uses that exact shape and also batch-hardens the corresponding
evidence-matched If and Let selectors.  Mat's pattern IH and Letrec remain
unchanged because their theorem shapes differ.

The immutable log/timing SHA-256 pairs are:

```text
019 02e8ae1796a6df91eeaedd6db404ebbbc9d195c6bc032a8134150a2d86f2dc87 / ed5900c03ba8b3c2a0ad56dfefc8eab148c1d92b8c17bf5adb9c8e6f5d4eb69a
020 5dc7480847f87aa3b157794aee1d096534e430ccac0b39b9f1f7e417941ebbd0 / e35196584b7dc93f6e4362fb4f1d225711e385dd0cbac1fe83bb9b373425c9e7
021 22f4e1d8803d3ee28004011797f6a1a6ee3034dbb222fbe65ca64dbcc967c504 / 1b832d4fc393f6abf312687afad5b6825a3f998632509cd55946b2b1e85e7b93
022 b0ed36a937d18f70ded507fb14e1c8bee627affc8cfe342f5f635cb2e5546937 / 2d5f51b0e29e9767a5703afd7089c0fe7f5d98c84c798e2b4883e67b0c81f2ea
023 22f4e1d8803d3ee28004011797f6a1a6ee3034dbb222fbe65ca64dbcc967c504 / d8bd2f1a461dc5b1b4bdbf5bc231d87b080a8578aef409409e209cb41523c8e6
024 07456b5c912e4d48afecb51a750fb2710c1b942c9a48d2acb277c9fc255a86b4 / dc9f503f2337bbfcfb00ad4b4c83d335dd3cc86fb05988723472424e5e71bcf9
025 ee9d308e740f48d9b64e483da21e5788b12c31c3fe27d69415e50462738481e9 / 0806724ad3cc0a9fb37d18518b1577d0e3165d0979b9adf2f06aadf88b257def
026 4619e34299a223cc9dbd3447a80011105023d9c764c31fa0be4817af9c453a6d / 7a22ffe49ef0bfab070118a8905d4f8dc13512e555399f267d1f784afd8f235f
027 f1c49df38e59712ce8181471b03888d2624caa98df12d3a689b81ec8cce034bc / af6a3e6af2863284cb9afe5890a235ac22ecd12b02185c077a42811d8216458d
```

No proof admission, theorem weakening, compiler qualification, Candle repin or
20/400 corpus result is claimed by these failed development replays.

## Dopen proof closure and declaration-sequence frontier

Focused attempts 028 through 038 continued from the same isolated worktree and
base `77b769a99`.  All executable replays used one HOL worker, recorded zero
swaps, and failed normally.  Wall times were `2:19.27`--`2:28.99`; maximum RSS
was `1039960`--`2092564` KiB.

Attempt 028 proved the exact conditional Log induction-hypothesis selection
and installed matching explicit selectors in If, Mat and Let, then stopped at
a later implicit search.  Attempt 029 conclusively replayed complete Log, If,
Mat (including its pattern IH), Let, Letrec, pattern and empty-declaration
branches and reached the new Dopen branch.  Attempts 030--034 successively
proved the open-environment invariant application, normalized the successful
source-open case, supplied the exact compiled state and global-environment
witnesses, and reduced Dopen's only residual to the flat-semantics identity
`evaluate_decs s_i1 [] = (s_i1,NONE)`.

Attempts 035--037 were definition-qualification refinements at that final
identity.  The unqualified name was unavailable; `evaluateTheory` selected
the wrong evaluator and left the equation; and flat semantics exposes the
mutual `evaluate`, `evaluate_dec` and `evaluate_decs` clauses through
`flatSemTheory.evaluate_def`, not a separate `evaluate_decs_def` theorem.
Attempt 038 used that exact definition, completed Dopen, and entered
`compile_correct[cons_decs]`.  This is the first replay evidence beyond Dopen:
the source-to-flat Dopen proof obligation is now closed without changing the
theorem statement, semantics, abort exclusions or axiom set.  The remaining
focused frontier is the declaration-sequence induction proof and its newly
explicit exact-domain result child.

The immutable log/timing SHA-256 pairs are:

```text
028 232abb446b093c032cf21e999dcb64ff98d943f7175dd9f5a1d5e0d4719685ed / 326cdf77d34d486e56a0b7a32a41273e0a3dc235cddeae7e9bd77498e6f0bc8a
029 119a07da2843753506f19bbd49e308fdb8c05888c0f5ba36bda0badef1b9ec3e / cc5e93f6c11d83d54cc2635def080bff9fc6ef34abb09fbcf1bbbfb321db5a3e
030 daf89e291c2ae9ec9c7623e68dcc42c3a1b556e4f4d91d0fac7aec9e4e59b581 / 48f46127cb4c59c29edda5872940a990bf23bd948b0b4f22da2f00e0813596c9
031 c99c945c1d01ed8dfd492647a70a10fd7c22ce32694140ada42c4beb4d75a5e2 / 2b8cd7d15e17eef811345e65476867d3536fea54576906a6a696c96390275a9d
032 7d475f26a9d64bc4bef49115f5037590ba62502b96432cc5e93df6aa68a1c651 / 95d1cd497bc4229e04e0a05195a6b7e96161a5e4e6575683bb4882b247633b98
033 92605f97dfd29ce968ba7a808cb638cd9016a5d65cae010d1e89e1f49a761772 / eecf0d88414203a927bdc5c3128f6974ec0f5ddd9ad6d7fb84c5c6e5640641bd
034 64479c603d0df5395bbe9a74030763c6d825c36d54c46dbffbd07200a2999253 / 8d41b1954ac1c056d424a604550edd8a99e475916e28fcf656d24d8bcdb37734
035 977e027c11490fc743b5d23e2496a71bb6db2cbf476b89b35f68e56b5d55889d / 7094b97f2c50660e59e62325d8b1cd0c50f2ef245cfcea9bb44c2b90093f649a
036 64479c603d0df5395bbe9a74030763c6d825c36d54c46dbffbd07200a2999253 / 1afbbd6c1bcc6c70ca9ab381128e161a4664df1fca21710dfe0cbfcab406779a
037 63a713601c5722b4d1929b7f5ea67cfd136ce7a7046d019d4aedaa93f0741afb / 331410d24dda1122c9e920a42583f1fd27be26a0bb8647b98e7d0ae761f5a6ae
038 d626be295510a14a3da1d9bda1830b3b9fa99f8cee53d687cf27248bf6d04593 / f9335f878711a05b81c6c790f5a9e4f57eec48413e46d6f447e866edc10316cb
```

Attempt 038 remains focused failed development evidence because the complete
target has not yet replayed.  It does not qualify a compiler or authorize a
Candle repin or corpus gate.
