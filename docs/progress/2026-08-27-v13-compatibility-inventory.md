# 2026-08-27 — v1.3 compatibility inventory foundation

## Outcome

Phase 0/1 now has a deterministic, source-located compatibility inventory for
the pinned Candle and Flyspeck repository snapshots plus a project ledger schema
and component-ledger import contract.  This closes the inventory plumbing task;
it does not close any P0 semantic compatibility class or prove S1/S2 source
reachability.

The current corpus result is 1,347 files, 100,751,549 bytes, and 6,049 findings:
5,020 open forms, 810 module constructs, 217 `==`/`!=` tokens classified by
syntactic role, and two literal-command custom FFI calls.  One pre-existing
truncated jHOLLight test file is retained as an explicit lexical note.

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

Two measured full regenerations used one CPU, completed in 77.23 and 78.76
seconds, and peaked at 123,900 KiB RSS.  Their three output files were
byte-for-byte identical.  The final artifact hashes are:

- findings JSONL:
  `29bf0bf9bb9c23b0ba4e77b271e1fc82282023c16e703dcd0cb5ac027a5e75e7`;
- lexical notes:
  `5dbf6debb9b58c8e83c38d085444f1f3f9591a4e098436e32ab8610332b1546e`;
- summary:
  `bbcd41eef9ce6be52bdbb4208e630146edde1edb93339ac99f53c11c438108b4`.

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
