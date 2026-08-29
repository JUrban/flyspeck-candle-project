# Parser-only diagnostic gate — 2026-08-29

## Scoped result

The host-side 20-node parser diagnostic controller has passed independent
review at Candle commit
`807ee93ed988449a8497c90384a497c726256456` on branch
`codex/flyspeck-parser-diagnostic-v1`.  It remains categorically
nonpromotable: it checks only direct parser acceptance and cannot establish
source-action execution, inference, evaluation, theorem identity, S1, S2, or
S3.

The repaired controller uses one captured, Git-authenticated byte image for
the manifest and pilot semantics.  It archives the exact original Git blob
for each of the 20 prepared inputs.  It captures the linked `cake` bytes into
one anonymous mode-0500 memfd, seals it against write, growth, shrinkage, and
seal changes, and executes that same inherited descriptor for the capability
handshake and every parser request.  The mutable runtime pathname is only
revalidated after capture and is never selected again for execution.

The wire protocol now has an exact three-field parse-error record and exit
status 65.  UTF-8 stderr is captured separately; the host computes the
domain-separated SHA-256 over those exact bytes.  This changed contract is
explicitly `parser_runtime_protocol.schema = 2`.  The strengthened result,
which includes the sealed execution identity and all 20 original sources in a
closed snapshot, is receipt schema 4.

## Review history

The first independent review rejected the controller for a split-image
manifest/pilot time-of-check/time-of-use defect, omission of the original
selected blobs, and execution through a mutable runtime pathname.  The next
review accepted those security repairs but rejected reuse of protocol schema 1
and receipt schema 3.  The final review of `807ee93` found no remaining
P0/P1/P2 issue in the scoped host gate.

Independent focused tests passed 41/41.  The author and parent lightweight
Candle suites passed 273/273, and the commit-bound 20-node pilot check passed.
No `cake` process was launched.

## Remaining release blockers

The CakeML branch still needs its dedicated `caml_parser$run` modes carried
through mode-specific x64 compile-correctness theorems.  That final source
must be pinned by Candle, proof-built in the canonical environment,
bootstrapped, linked under authenticated provenance, and then accepted by the
exact capability handshake.  Until all of those steps pass, the retained
materialized plan is development evidence only.
