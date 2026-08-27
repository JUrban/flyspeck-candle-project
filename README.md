# Flyspeck in Candle

This repository coordinates the implementation needed for Candle/CakeML to
execute the pinned Flyspeck/HOL Light source workload.  The governing v1.3
release target is S3: direct source execution plus HOL-side nonlinear/LP
evidence closure, with no HOL Light runtime in the production path and with the
Isabelle tame-graph classification retained as an explicit premise.  S2 is the
decisive source-substitution milestone and S4 is tracked separately.

The parallel PFT validation architecture is specifically
`Flyspeck source -> HOL Light producer -> hostile PFT -> compiled Candle`.
It can prove that Candle reconstructs the complete HOL-side proof and evidence,
but it does **not** satisfy S2 or S3.  It is retained as an independent checker,
differential oracle, and distribution artifact while verified Dopen, OCaml
compatibility, the direct loader, and source-driven evidence closure form the
primary critical path.

The upstream repositories are checked out as sibling directories under
`../repos/`.  Development happens on `codex/*` branches in those repositories;
this repository holds the locked manifest, cross-repository tooling, acceptance
criteria, and progress reports.

The direct S3 stream is active in parallel across the verified Dopen rebuild,
the actual 65-load Great 100 source inventory, and the manifest-rooted full
Flyspeck loader.  The current direct manifest freezes 297 build entries, 400
source nodes, 706 selected dependency edges, exact loader actions,
generated-input hashes, and eight build
strata.  Compatibility work is call-site-specific and fail-closed: for
example, the selected LP verifier's one immediate-int `==` has an exact
hash-bound, semantics-proved normalization.  The twelve allocated-value
identity sites now have a separate exact, site-specific source remedy with
local differential, callback/exception-order, sharing, and zero-residual-
operator tests.  The compiled loader now authenticates and selects those four
outputs plus strictbuild and two parser-path normalizations, for seven exact
authenticated outputs in total, but the remedy remains
`regression_pending` until a full selected run closes its non-use and
fingerprint gates and Flyspeck-scale performance is accepted.  Exact static
`#load`, `#flyspeck_needs`, and always-evaluate `#flyspeck_loadt` actions are
active and fail-closed.  Phrase-start recognition, module-item separators, and
loaded-file EOF are covered by compiled regressions.  The clean direct loader
now completes normalized `general/parser_verbose.hl` and stops at the exact
`open Parser_verbose` declaration in `general/debug.hl`, pending integration of
the verified Dopen work.
The first baseline is deliberately
allowed to expose and retain compatibility failures; fixture theorem counts,
parser-only successes, and broad source patching do not promote a gate.

The v1.3 source-substitution work now also has a conservative compatibility
inventory and aggregate ledger foundation.  See
`docs/compatibility-inventory.md`.  It inventories tracked Candle/Flyspeck
OCaml-family syntax without treating repository presence as production load
closure, and imports the authoritative Candle-native compatibility ledger by
immutable git coordinates instead of copying component entries.

The PFT validation stream is substantially further along.  Its compiled Candle
endpoint consumes both official HOL4-writer traces and direct HOL Light
bootstrap traces, rejects malformed and unauthorized input, enforces exact
standard-axiom identities, and returns deterministic replay evidence.  The
bounded producer has a tested DMTCP checkpoint/kill/restore boundary and a
head-locked supervisor for the real Flyspeck `main` and `full` sequences.  The
complete LP archive inventory is pinned, long LP/nonlinear phases have internal
restart boundaries, and the validation target leaves only the explicit
Isabelle tame-classification premise.  These results remain useful P1 evidence
but do not advance S2 or S3 until independently matched by direct source
execution.

## Layout

- `manifest.lock.toml`: immutable source and toolchain identities.
- `docs/requirements-v1.3.md`: governing source-substitution gates and evidence.
- `docs/requirements.md`: superseded v1.2 PFT-validation ledger retained for
  the independent replay lane.
- `docs/full-l2-runbook.md`: fresh/resume operation, evidence outputs, and the
  DMTCP trust boundary for the full PFT-validation run; “L2” in this historical
  filename is not a v1.3 S2/S3 claim.
- `docs/progress/`: dated, evidence-backed interim reports.
- `scripts/verify-lock.sh`: checks local source identities and roadmap hash.
- `scripts/update-compatibility-inventory.sh`: regenerates the pinned v1.3
  syntax inventory deterministically.
- `scripts/check-compatibility-ledger.sh`: validates schemas, lifecycle rules,
  generated evidence, and authoritative component imports.
- `scripts/test-producer-resume.sh`: destructive-process restart smoke test.
- `scripts/run-restartable-flyspeck-export.sh`: resumable real-build exporter
  and compiled replay supervisor.

New supervised runs default to uncompressed DMTCP images because the producer
retains only its latest image and the installed DMTCP documents substantially
lower checkpoint latency in this mode.  Set `CANDLE_PFT_DMTCP_GZIP=1` to opt
into compression.  The setting is locked in the run state; state directories
created before this option was added retain their historical gzip mode, which
the supervisor adopts automatically on resume unless an explicit conflicting
override is supplied.

Nothing in the producer, translator, merger, or orchestration repository is in
the logical trust boundary.  Release traces are hostile input to the compiled
Candle checker.
