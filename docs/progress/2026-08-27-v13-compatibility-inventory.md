# 2026-08-27 — v1.3 compatibility inventory foundation

## Outcome

Phase 0/1 now has a deterministic, source-located compatibility inventory for
the pinned Candle and Flyspeck repository snapshots plus a project ledger schema
and component-ledger import contract.  This closes the inventory plumbing task;
it does not close any P0 semantic compatibility class or prove S1/S2 source
reachability.

The corrected direct-S3 corpus result is 1,339 files, 100,736,789 bytes, and
6,044 findings: 5,019 open forms, 806 module constructs, 217 `==`/`!=` tokens classified by
syntactic role, and two literal-command custom FFI calls.  One pre-existing
truncated jHOLLight test file is retained as an explicit lexical note.

This result comes from the dedicated clean worktree at upstream Flyspeck
`1ce0353008eba83d3c76ae9a25c3c242e4802d53`.  The original result in this
report used PFT development head `2ea440e9...`; it is now retained only as an
immutable comparison, not selected-route evidence.

## Design decisions and re-evaluation

- The scan covers the complete tracked OCaml-family repository snapshots first,
  while labelling dependency-closure membership unknown.  Silently equating a
  repository checkout with the S2 loader DAG would overstate evidence.
- HOL quotations and Camlp quotations are masked before detection.  A first
  pass revealed that legacy `pa_j` backticks are lexer tokens rather than HOL
  quotations; the dialect-specific rule was added and six false lexical
  anomalies disappeared.
- A first pass also described every `==` as physical equality.  Corpus evidence
  contradicted that shortcut because the operator is rebound.  The final schema
  separates infix use, operator binding, and operator reference and leaves name
  resolution and semantic purpose unresolved.
- A review of the provisional pointer list found fourteen `.vhl` examples in
  `--` comments.  Findings now carry a source-dialect field and the VHL masker
  applies its line-comment rule before classification.
- The first scanner implementation used suffix copies in the lexical loop and
  was quadratic on large generated sources.  Indexed regex matching reduced a
  non-terminating-scale pass to about 77 seconds on one CPU and modest memory.
- Candle's parallel source-baseline work already owns
  `CANDLE-OCAML-FLOAT-LITERAL-001`; the project ledger imports that exact blob
  rather than copying it.  Schema gaps are recorded at the import boundary.

## Evidence commands

```sh
scripts/update-compatibility-inventory.sh /project/repos
scripts/check-compatibility-ledger.sh /project/repos
python3 scripts/test-inventory-compatibility.py
python3 scripts/test-compatibility-ledger.py
```

The original two measured PFT-head regenerations used one CPU, completed in
77.23 and 78.76 seconds, and peaked at 123,900 KiB RSS.  The corrected direct
run also uses one CPU and is reproducible through the same command.  Current
artifact hashes are:

- findings JSONL:
  `bfb6e369eb2f0b02b0e58febcb0bcf466f66e1aee3ea30fe8e9665212be4d67c`;
- lexical notes:
  `6ef2f63144e7f3c7a2ed240b968228466f71b0210b7e369ae4c5d76465e2c7f3`;
- summary:
  `ec490b8c40cfe2351c6dce3af49b9da70403df82537f7ead836b473e268927b5`;
- pin-delta report:
  `b930b78521dd4f47347e9471e268298cea2e61fbc65080212ec91904881944d9`.

The exact direct-minus-PFT delta is eight files, 14,760 bytes, and five
findings: four module structures and one declaration `open`, all from PFT-added
`text_formalization/candle` files.  Stable comparison matches all 6,044 direct
findings and finds no direct-only occurrence.  All 217 pointer and two FFI
triage records match after excluding only pin-derived identifiers and commit
coordinates.

The validator checks JSON Schema when `jsonschema` is available, always checks
lifecycle invariants, verifies generated JSONL count/digest, rederives all
aggregate counts and source digests from the pinned clean repositories, and
reads imported ledger/Great 100 artifacts directly from their pinned git commit.  Unit tests
cover masking, nested comments, both local-open forms, module forms, custom FFI,
pointer classification, deterministic output, ignored untracked files, and
ledger promotion requirements.

## Remaining limitations

- Exact S1/S2 dependency-closure and stratum annotations are not yet available.
- The inventory is lexical rather than a full OCaml/Camlp AST and leaves 39
  module declarations as `unparsed_expression`.
- Pointer operator name resolution and semantic purpose require review.
- FFI call locations do not establish the C/runtime contract.
- The imported Candle ledger needs stable regression IDs and finer lifecycle
  fields at its authoritative source.
