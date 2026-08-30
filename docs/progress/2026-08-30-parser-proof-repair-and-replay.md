# Parser proof repair and replay checkpoint (2026-08-30)

## Status

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
they must be regenerated against `ca67ffaa...` after, and only after, this
replay passes.
