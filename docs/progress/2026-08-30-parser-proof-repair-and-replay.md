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
