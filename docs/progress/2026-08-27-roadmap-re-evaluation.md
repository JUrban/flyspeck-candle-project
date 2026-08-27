# Roadmap and claim-boundary re-evaluation — 2026-08-27

An independent audit correctly distinguished two architectures: compiled
Candle replay of a hostile trace produced while HOL Light executes Flyspeck,
and direct execution of the Flyspeck source by Candle/CakeML.  The current full
run establishes only the first architecture.  Reports and release markers must
therefore call it a full `HOL Light -> PFT -> Candle` L2 replay and must not
call it direct source execution or HOL Light replacement.

The audit attributed a different critical path and S2/S3 terminology to
roadmap version 1.3.  That roadmap has now been supplied, explicitly adopted,
and locked at SHA-256 `13fc3a6209787e9fa9c1879cb482fef6837252ec96b3ae506d312646c898863f`.
It supersedes the v1.2 critical path: S3 direct source execution is now the
release target, and the PFT run is its independent validation lane.

The audit also exposed a valid evidence shortcut: 119 saved theorems across
PFT fixtures are not a substitute for Candle's actual Great 100 source suite.
The separate Candle worktree now has machine-readable per-test timing and RSS
reporting at commit `110a18d`; the 65-file Great 100 suite is running with one
worker.  Its results will be recorded independently of the full PFT run.

The full PFT computation is retained because it will provide exact final
theorem, assumption, certificate, restart, and resource evidence for
differential validation of the source-substitution program.  Its completion
cannot close the governing S2/S3 gates.
