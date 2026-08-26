# Bootstrap report — 2026-08-26

## Outcome

The roadmap was extracted and read in full.  Its default L2 claim and gaps
G1–G12 have been converted into an acceptance ledger.  Candle, CakeML, HOL4,
Flyspeck, and HOL Light were cloned; audited commits are retained and current
upstream movement is recorded in the lock manifest.

The Candle `pft` branch was rebased onto Candle master as
`codex/flyspeck-pft`.  The only conflict was an older `Sys.command`
implementation; master already contains the newer `Bytes`-based code, which was
kept.  The rebased PFT loader successfully loads in the downloaded CakeML
Candle runtime.

HOL4 replay commit `427496c4...` is checked out on
`codex/flyspeck-pft-producer`.  Poly/ML's Debian multiarch library location was
supplied through the ignored local configuration file and the HOL4 build was
started with four jobs.

## Confirmed Phase 1 defects

- Candle expects a numeric version `1`; the writer emits string `0.1.0`.
- Candle expects four footer counters; the current footer has three plus its
  two-byte length.
- Candle models compute contexts as ID-addressed objects; the ruleset has one
  ambient `COMPUTE_INIT` state.
- Candle shells out to `extract_footer`, creates a side file, and does not quote
  the trace path.
- Object arrays contain valid-looking placeholder values, so dead/out-of-range
  IDs are not uniformly rejected.
- `AXIOM` is unrestricted and checked only by the Candle kernel's type rule,
  not a release policy.
- The replay entry point is hard-coded to one uncommitted filename and has no
  committed golden/corruption harness.

These are implementation defects, not merely documentation drift, and define
the next commits on the Candle branch.
