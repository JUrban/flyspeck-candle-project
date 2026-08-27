# Roadmap and claim-boundary re-evaluation — 2026-08-27

An independent audit correctly distinguished two architectures: compiled
Candle replay of a hostile trace produced while HOL Light executes Flyspeck,
and direct execution of the Flyspeck source by Candle/CakeML.  The current full
run establishes only the first architecture.  Reports and release markers must
therefore call it a full `HOL Light -> PFT -> Candle` L2 replay and must not
call it direct source execution or HOL Light replacement.

The audit attributes a different critical path and S2/S3 terminology to a
roadmap version 1.3.  The only roadmap supplied and locked in this workspace is
version 1.2 (`713b97d2...`), which selects PFT as the primary L2 route and
tracks Dopen and wider source compatibility separately.  No unseen roadmap is
silently treated as release authority.  If version 1.3 is later supplied or
explicitly adopted, the PFT run will become its independent validation lane
and the completion plan will be revised to source substitution.

The audit also exposed a valid evidence shortcut: 119 saved theorems across
PFT fixtures are not a substitute for Candle's actual Great 100 source suite.
The separate Candle worktree now has machine-readable per-test timing and RSS
reporting at commit `110a18d`; the 65-file Great 100 suite is running with one
worker.  Its results will be recorded independently of the full PFT run.

The full PFT computation is retained because it remains required by the
supplied v1.2 roadmap and will provide exact final theorem, assumption,
certificate, restart, and resource evidence even under the alternate source
substitution program.
