# Current parser and direct-source handoff — 2026-09-02

## Authorities and status

The active frontend controller is Candle
`ac15ba0` (`codex/flyspeck-v13-parser-quotation-prep`) at
`/project/worktrees/candle-parser-quotation-prep-v13`. It descends from the
canonical-bootstrap dependency repair `f2f50a44...`. The other pinned sources
remain:

- CakeML `c2e26f43c35080d57fc18aba42d4023590b6daba`;
- HOL4 `a390cbabd3a4521bab4ee20281e3e42933a8a3ae`; and
- Flyspeck `1ce0353008eba83d3c76ae9a25c3c242e4802d53`.

The authenticated pristine-cold CakeML proof replay passed. Canonical attempt
003 rebuilt all 18 forced targets and exited zero after 7:31:54, but correctly
failed final publication because its dependency transition model omitted 238
lazily materialized ancestor depfiles and expected 36 generated-theory
depfiles to reappear. Candle `f2f50a44...` repairs that model and passes its
full 340-test lightweight suite.

Canonical attempt 004 is active at
`/project/flyspeck-candle-runs/cakeml-canonical-bootstrap-f2f50a4-attempt-004`.
It remains valuable bootstrap authority for `f2f50a44...` and, after successful
publication, as a non-promotable transition base. It cannot create an ordinary
schema-6 link for `ac15ba0...`, because the canonical record binds the older
Candle head. Do not stop or relabel it.

The quotation-aware Candle head passes the expanded full lightweight suite,
346/346. No parser-only result in this report is S1, S2, S3, theorem, or
release evidence.

## Why the old parser plans are superseded

The first development pilot fed raw HOL Light source directly to
`caml_parser$run`. It reported lexer errors at backticks in `bool.ml`,
`drule.ml`, and `tactics.ml`. That was a diagnostic-model defect: Candle's real
loader tokenizes `T_quote` and applies `Cakeml.unquote`, with `system.ml`
installing `quotexpander`, before invoking the parser.

Candle `ac15ba0...` now reproduces that exact byte transformation after
normalization and standalone-loader masking. Its contract is bound to the
exact pinned `candle/prover/candle_boot.ml`, Candle `system.ml`, and controller
implementation. The authenticated corpus contains:

- 318,855 loader-visible quotations in 344 of 400 inputs;
- 318,180 term quotations and 675 type quotations; and
- 104 term quotations in three of the 20 pilot inputs.

Backticks inside nested comments, strings, and character literals remain
unchanged. Empty/unclosed quotations and lexically unclosed comments, strings,
or character literals fail closed. Pilot plan/receipt schemas are now 2/6;
all-inventory schemas are 3/7. Raw-source plan schemas 1/2 and receipt schemas
4/5 cannot be relabelled.

The old roots `parser-pilot-materialization-f2f50a4` and
`all-inventory-materialization-f2f50a4` are therefore historical source plans,
not inputs for a current gate.

## Current quotation-aware source plans

| Plan | Root | Plan SHA-256 | Host SHA-256 |
| --- | --- | --- | --- |
| pilot 20/20 | `parser-pilot-materialization-ac15ba0` | `7e3e15ab463e11794a414ae9a12e3e79c18c76d84d375541dce92d4a1f662320` | `8e8bda7504459791d95c4fe4ba21cf71cf829e9986629adf13da15c2c6d9c46b` |
| all 400/400 | `all-inventory-materialization-ac15ba0` | `42281a3bf749c94d7261030d41edfa5352b2fbe73cb5f507a79ed5ce06dcaf9a` | `29f698e2e5c9311c6b02f78d7d3b1b75c5be1766f0f6ae440213acf8bc38b3be` |

The older direct cumulative plan
`/project/flyspeck-candle-runs/v13-stratum-plan-f2f50a4` remains a useful
297-action shape check but is stale for execution at the new Candle head.
Regenerate overlay, generated-input, and direct plans only after the frontend
batch selects its final Candle/CakeML commits.

## Development-only parser results

The immutable development binary at
`nonpromotable-dev-link-f2f50a4-attempt-001/cake` is not ordinary current-head
schema-6 authority. It was used only to avoid another expensive proof build
while classifying frontend input.

The corrected pilot is 20/20 parse-ok in 6.3 seconds. Its summary is
`nonpromotable-dev-parser-pilot-ac15ba0-attempt-001/DEVELOPMENT-NONPROMOTABLE.json`,
SHA-256
`c2588211c8a43d205295729c61653e27139024d5fff3b7114b5d8b3b6a4198d7`.
The three former backtick failures all pass.

The first corrected all-inventory sweep took 1,042.623 seconds and retained:

| Outcome | Count |
| --- | ---: |
| `parse-ok` | 349 |
| canonical parser error (exit 65) | 50 |
| noncanonical runtime failure | 1 |

Its immutable summary is
`nonpromotable-dev-parser-all-ac15ba0-attempt-001/DEVELOPMENT-NONPROMOTABLE.json`,
SHA-256
`9c3d30e761985792adaa59854c2502b65916921387c049f344c9e2d39f73b0be`.
Every attempt has separate stdout/stderr bytes and an exact prepared-input
identity. The lone runtime failure is the 9,099,782-byte
`formal_graph/archive/archive_all.ml`: it consumed about 258 seconds, then
exited 1 with the generic nonzero-exit message. Treat it separately from the
50 canonical parser errors.

The PEG often reports a failed structure at its opening `module`, so the raw
locations do not mean general module declarations are unsupported. Project
commit `32cf9a1...` adds a reproducible lexical-item localizer. It binds the
schema-3 plan, the non-promotable sweep, the exact executable, and OCaml
4.14.1; retains candidate/stdout/stderr bytes; and makes no parser or release
claim. Two immutable runs are retained:

| Localization | Reduction | Candidates | Parser calls | Summary SHA-256 |
| --- | --- | ---: | ---: | --- |
| `nonpromotable-parser-localization-ac15ba0-attempt-001` | none | 50 | 2,326 | `9bc0c70be151e1b5d63a9ec56acf82a42a7cc7f0cb16ea56a1b68a242ce23dd9` |
| `nonpromotable-parser-localization-ac15ba0-attempt-002` | OCaml-valid line ddmin | 50 | 2,499 | `7079983091e3a946f2478722dc285d007f12cfb1b271b5c78328022806a83ee2` |

Every failed input has an independently non-passing outer-structure item.
Forty initial items parse under plain OCaml 4.14.1 and were line-reduced while
preserving both that fact and Candle exit 65. Ten are HOL Light/Camlp dialect
items and were deliberately not reduced under the wrong plain-OCaml oracle.
The localized batch separates into several real candidate families:

- record type declarations, record construction, and lowercase field access;
- `include` and signature-constrained module bodies;
- annotated/parenthesized recursive bindings and optional arguments;
- tuple/list/record patterns and expression-sequence edge cases;
- large generated expressions and theorem declarations containing HOL Light
  infix/dialect syntax that need a matching dialect oracle; and
- a layered case in `ineq.hl`: whole-file lexing first exposes the unsupported
  string escape `\_`, while chunk isolation also exposes an earlier parser
  gap in an assignment expression.

Focused in-memory probes confirm that ordinary tuple bindings, array indexing,
`try`, trailing list separators, and mutually bound lets already parse. Small
counterexamples remain for structural records, unqualified field projection,
path-only `include`, optional/parenthesized recursive arguments, trailing
sequences before `)`/`end`/`done`, and several constructor-pattern forms.
This prevents treating all 50 files as one speculative grammar repair.

These are candidates, not yet approved parser extensions. Each must be
minimized against OCaml 4.14.1 and the real Candle loader. Prefer a narrow
source normalization when the construct is isolated and semantics permit it;
prefer a parser/conversion repair when the selected corpus uses a genuine
general OCaml form. Batch all accepted CakeML frontend changes before the next
proof/cold/bootstrap cycle.

## Critical path from here

1. Preserve and finish canonical attempt 004. If it publishes, validate its
   dependency-transition repair and retain it as `f2f50a44...` authority.
2. Finish semantic classification of the minimized batch and implement the
   first bounded frontend repairs on the isolated CakeML branch
   `codex/flyspeck-v13-frontend-batch`. Record corpus counts and use
   authenticated source normalization only for genuinely isolated dialect
   forms where a general parser/semantic extension is not justified.
3. Re-run the development 20/400 gates after each coherent batch and require
   20/20 then 400/400 before another final CakeML proof replay.
4. At the final CakeML frontend head, replay focused parser tests, translated
   dependents, the pristine cold qualification, and then a fresh canonical
   bootstrap. A transition link is diagnostic only; final current-binary
   evidence needs an ordinary same-head schema-6 link.
5. Materialize fresh current-head pilot/all/direct plans. Run and independently
   consume the formal 20-input gate before the formal 400-input gate.
6. Continue with linked compatibility, diagnostic direct cutpoints, the
   approved Great-100 comparison, and eight cumulative direct boundaries
   through nonlinear/LP final assembly.

PFT remains an independent oracle and never advances direct S2 or S3. The
approved 130/130 Great-100 reference artifact remains separate; integrate the
retry-consumer repair from `2026-09-02-s1-reference-retry-consumer.md` only at
the final current-head consumer stage.

## Resource note

The parser sweep used one fresh process at a time and roughly 1 GiB RSS for the
largest observed active parser. Canonical attempt 004 and the PFT oracle
continued concurrently with ample headroom. Keep ordinary work below ten CPUs
and 60--80 GiB when practical; the user-authorized 120 GiB ceiling remains
available for measured proof/bootstrap peaks, not as a reason to overlap
unnecessary heavyweight builds.
