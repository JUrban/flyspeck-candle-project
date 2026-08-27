# v1.3 compatibility inventory and ledger

This is the Phase 0/1 inventory foundation required by sections 4–8 of
`Flyspeck_in_Candle_Gap_Analysis_v1.3.docx`.  It answers a deliberately narrow
question: which compatibility-sensitive syntax occurs in the two pinned source
repositories, and where?  It does not claim that every occurrence is on the
production load path or that lexical syntax establishes semantic intent.

## Reproduce and validate

From this repository:

```sh
scripts/update-compatibility-inventory.sh /project/repos
scripts/check-compatibility-ledger.sh /project/repos
python3 scripts/test-inventory-compatibility.py
python3 scripts/test-compatibility-ledger.py
python3 scripts/test-compatibility-triage.py
```

The generator refuses a different repository HEAD or tracked dirty state.  It
uses `git ls-files`, so untracked build products cannot enter the result.  Output
ordering, JSON encoding, finding IDs, and summaries are deterministic.  The
checked-in result is tied to:

- selected direct-source Candle branch
  `7db8e182d8cd9a92eef386365584009d63f5959b`, read from
  `worktrees/candle-loader-v13`;
- clean direct-S3 Flyspeck
  `1ce0353008eba83d3c76ae9a25c3c242e4802d53`, read from the dedicated
  `worktrees/flyspeck-v13-source` worktree;
- roadmap v1.3 SHA-256
  `13fc3a6209787e9fa9c1879cb482fef6837252ec96b3ae506d312646c898863f`.

The PFT development head
`2ea440e9f7c55734d1e47738e44a6129ce0ecf5a` is deliberately excluded from
the direct inventory.  `compatibility/inventory-pin-contract.json` and the
ledger provenance keep the two roles separate.

The complete machine-readable coordinates are in
`compatibility/inventory-scope.toml`.  The result artifacts are:

- `compatibility/generated/inventory-findings.jsonl`: one source-located,
  source-hashed record per finding;
- `compatibility/generated/inventory-summary.json`: counts, pins, artifact
  digest, and the evidence boundary;
- `compatibility/generated/inventory-lexical-notes.json`: inputs that the
  conservative masker could not close;
- `compatibility/generated/pointer-triage.json`: one reviewed G3 record for
  every pointer-token finding, with name resolution, intent, selected-route
  status, evidence, and ledger disposition;
- `compatibility/generated/ffi-triage.json`: the selected-source custom-FFI
  result (zero calls) and its explicit clean-binary elimination boundary;
- `compatibility/generated/inventory-pin-delta.json`: reproducible, stable-
  occurrence comparison with the earlier PFT-head inventory;
- `compatibility/schema/*.schema.json`: JSON Schema for findings, summary, and
  project ledger entries/imports.

## Snapshot result

The scan covers 1,364 tracked OCaml-family files (100,857,485 source bytes): 704
in Candle and 660 in Flyspeck.  It records 6,074 findings.

| Syntax family | Count | Source-level classification |
|---|---:|---|
| Declaration `open` | 4,925 | path form plus `open!` flag |
| `let open ... in` | 3 | local let-open |
| `M.(...)` | 89 | 82 operator references; seven general expressions |
| Module structures | 611 | `module M ... = struct` |
| Module aliases | 6 | simple, dotted, or functor-application right side |
| Module functor declarations | 1 | parameter/functor syntax |
| Other module declarations | 39 | deliberately left unparsed for AST review |
| `include` | 95 | path form |
| Module type declarations | 65 | declaration syntax |
| First-class module pack/unpack | 0 | lexical absence in this repository snapshot only |
| `==`/`!=` infix uses | 232 | token and operand shape; name resolution unresolved |
| `==`/`!=` operator bindings | 4 | operator-definition syntax |
| `==`/`!=` operator references | 4 | parenthesized operator-as-value syntax |
| `customFFI` calls | 0 | lexical absence in the selected source snapshot |
| OCaml `external` declarations | 0 | lexical absence after quotation masking |

The module-path inventory contains 5,081 simple, 29 dotted, eight
functor-application, zero anonymous-structure, and 39 unparsed-expression
forms.  Counts include explicit zeros so absence is distinguishable from an
unimplemented classifier.

### Direct-pin correction from the PFT evidence

The prior checked-in inventory combined Candle `177a9c1e...` with PFT
development Flyspeck `2ea440e9...`.  The machine-readable comparison pins that
evidence at project commit `5d620bcdd3412f3e4a9ed3d9dcb3ed9ae71c22ff` and
compares stable occurrences without confusing commit-derived IDs with source
changes.  The new selected snapshot has 17 more files, 105,936 more bytes, and
25 more findings in total: Candle contributes 30 net findings while the clean
direct Flyspeck pin removes five PFT-only findings.  There are 114 old-only and
139 new-only stable occurrences.  The apparent stable-occurrence churn includes
all 91 historical and 89 current `M.(...)` records because generator v2 adds
the body-shape classification; category-coordinate identity and the aggregate
source delta remain separately visible.  The 23 new pointer records are host regression
oracles and are explicitly outside the generated direct boot; all 217 earlier
pointer reviews still match.  Both historical FFI records disappear from the
selected source, leaving zero selected FFI calls.  The current findings digest
is `e713ab19cfd207a8cd4db191436df467db763ba73f2799a288f6a50fa4c71b02`.

The removed calls were the former startup `chdir` bridge and the former
`Sys.command` `system` bridge.  Their ledger entries remain as deferred
outside-closure history.  The clean executable `c20b3ec...` uses
`basis_ffi.c` SHA-256 `04da4d58...`, byte-identical to the compiler archive
member, and reaches the authenticated direct frontier without the old patch.

### Exact direct-manifest projection

`compatibility/generated/direct-closure-summary.json` projects this broad
snapshot onto the 400-node direct manifest by exact repository path and source
SHA-256.  It selects 3,689 findings in 329 files with site digest
`28a1cc07d6c9e34f8fc979f75a1421c7101ecf1c585c271a22faf57c1360e372`.
Of those, 3,180 are the separately governed Dopen corpus and 509 are other
compatibility-sensitive occurrences.

The projection turns several broad queues into exact facts:

- selected `let open ... in`: zero;
- selected parenthesized local opens: 79 operator references in 23 files (78
  in the base stratum, one in LP support), with zero selected general-expression
  bodies;
- selected pointer tokens: 15 (12 infix uses, one binding, and two
  operator-as-value references), matching the separately reviewed G3 set;
- selected custom-FFI calls and external declarations: zero;
- selected module syntax: 389 structures, one alias, 15 scanner-other
  declarations, one include, and nine module-type declarations.  All 15
  scanner-other sites are multiline ordinary or signature-constrained
  structures.  The alias is the sole selected functor application,
  `Set.Make(String_compare)`, and is handled by an exact source contract.

The artifact also records every source path by category and occurrence counts
by earliest build stratum.  This is exact source-membership evidence, not a
claim that an occurrence executes or that its semantics already match OCaml.
The generator rejects a selected source hash mismatch, and the release lock
recomputes the artifact byte-for-byte.

## G3/G4 source-backed triage

The reviewed overlay covers all 240 pointer-token findings exactly once.  On
the explicitly selected S3 source route, it finds 15 tokens:

- 12 built-in physical-identity uses: ten structural-sharing controls in
  `text_formalization/general/lib.hl`, plus two identity-filter predicates in
  `general/print_types.hl` and `jordan/tactics_jordan.hl` whose higher-level
  intent remains deliberately medium-confidence.  Direct oracles confirm a
  Candle incompatibility: non-reference `==` is rejected because Candle types
  it as reference-only, while non-reference `!=` reaches the unsupported
  `nRelOp` parser path;
- one built-in immediate-int comparison, `n == 1`, in the selected LP
  certificate verifier.  OCaml accepts the minimized form; Candle rejects the
  int operand because its `==` expects references;
- a local operator binding and its use in
  `list_hypermap_computations.hl`; source context proves that `(==)` is the
  theorem-producing function `eq_eq`, so these two tokens are not pointer
  identity after name resolution.

The remaining 225 tokens are classified and excluded from this selected route:
alternative Azure, Proofrecording, and kernel trees; host-side `pa_j` build
inputs; the 23 exact-normalization host oracles; and optional, test, or informal
sources.  The exclusion means only
"not selected by the pinned S3 route".  It is not a global dead-code claim.
Every record retains its source coordinate, evidence, confidence, and reviewed
rule ID.  The generator rejects gaps, overlaps, unused rules, or moved FFI
sites.

The selected source and build recipe now contain no custom FFI call.  Startup
uses a repository-root launcher with relative boot/config links.  `Sys.command`
fails closed; the one tracked compressed LP certificate is prepared outside
the proof runtime under an exact archive/member/hash contract, and the selected
runtime receives a fixed sorted inventory of 39 authenticated `.dat` paths.
The clean compiled frontier reaches the unchanged Dopen failure after loading
that inventory.  Its executable SHA-256 is `c20b3ec...`; its generated boot
also contains zero custom-FFI calls, and its C basis is byte-identical to the
pinned compiler archive member.  G4 is therefore not required for this exact
selected route.  The historical entries are fail-closed guards: any source,
boot, recipe, C-basis, or manifest change that reintroduces a call or handler
reopens G4.

There is one lexical note.  Flyspeck
`jHOLLight/Tests/test-compiled.hl:1` starts an unterminated string (`needs
"/home/monad/`) and the final quote at line 151 is consequently reported as an
unclosed string.  This is a pre-existing truncated jHOLLight test input, not a
scanner repair or a claim about the audited HOL-side load path.  The scanner
keeps the note visible instead of silently dropping or guessing at the file.

## Static evidence boundary

Each finding also carries an explicit source-dialect label derived from its
tracked path/extension.  The scanner masks nested OCaml comments, strings, character literals, OCaml raw
strings, Camlp quotation bodies, and HOL Light backtick quotations while
preserving line/column offsets.  Legacy `pa_j/` lexer sources use backticks as
lexer tokens, so that path has an explicit dialect rule disabling HOL-quotation
masking.  `.vhl` inputs have a separate rule for `--` line comments.  Tests
cover all three behaviors.

In particular, a `==` token is not automatically labelled pointer identity.
The corpus can rebind the operator—for example `(==) =
Big_int.eq_big_int`—so each record states that operator resolution is unknown
without name resolution.  For infix syntax, the scanner records only an operand
shape such as identifier/identifier or identifier/immediate.  Optional lexical
review hints (`hash`, `memo`, `cycle`, and similar words) are explicitly not
semantic classifications.  Correctness-sensitive identity, optimization,
hash-consing, cycle detection, and dead code require manual or semantic review.

Likewise, repository-snapshot presence is not dependency-closure membership.
The scope includes tracked `.ml`, `.mli`, `.hl`, `.vhl`, `.cml`, `.mll`, and
`.mly` files, including historical/generated tools.  It excludes Isabelle
uppercase `.ML` sources, C/runtime implementations, Java, data, and certificate
formats.  The repository snapshot alone cannot establish production-closure
membership.  The direct-closure artifact now supplies exact node/hash and
stratum annotations; the warning remains applicable to the broader snapshot
itself.

## Ledger ownership and import contract

`compatibility/ledger.json` is a project index, not a competing copy of a
component ledger.  Candle commit
`2306980c0c76f9e5c9a30e259694d4044110fab1` owns the authoritative
`candle/compatibility/ledger.json` and its first live failure,
`CANDLE-OCAML-FLOAT-LITERAL-001`.  The project index imports that immutable git
blob by commit, path, SHA-256, entry ID, and field mapping; it does not repeat the
entry body.  The same contract references Candle's 65-target/66-source Great
100 manifest at `candle/top100_manifest.json`.

The validator reads both artifacts directly from the named git object, verifies
their hashes and declared counts/IDs, rejects duplicate IDs across imported and
local ledgers, and records three current source-schema gaps: stable regression
IDs, separate remedy/proof lifecycle status, and repository-qualified affected
locations.  Those gaps are explicit follow-up work, not synthesized fields.
It also rejects any ledger/inventory drift between the clean direct source pin,
the separately named PFT development pin, and all six generated/configuration
artifact digests.  It rechecks inventory repository HEAD/dirty state, tracked file and byte
counts, every referenced source digest, every aggregate category/path/operator
count, the JSONL digest, and all ledger selectors against the current artifacts.

The thirteen local entries comprise the remaining syntax-review queues, concrete
selected-route pointer/name-resolution and exact-normalization obligations,
and the retained historical `chdir`/`system` elimination obligations.  Each
contains all
v1.3 lifecycle fields: minimal reproducer, OCaml outcome, Candle outcome,
semantic category, remedy, proof obligation, regression IDs, affected files,
and status.  Empty/pending values are honest because an inventory hit is not a
confirmed divergence.  The validator prevents a confirmed or resolved entry
from retaining those weak states; resolution requires observed outcomes,
enumerated affected files, an implemented remedy, discharged/documented proof
obligation, stable regression IDs, and evidence.

## Next ledger work

1. Semantically group the remaining exact selected non-Dopen occurrences,
   prioritizing runtime members and parser-state behavior not traversed by the
   current clean frontier; the selected local-open and module subsets are now
   closed by differential gates and one exact `Set.Make` normalization.
2. Turn each actual failure into a minimized OCaml/Candle oracle before marking
   it a confirmed divergence.
3. Close the full-run fingerprint and scale gates for the implemented exact
   pointer normalizations; retain medium-confidence filter intent as an
   explicit review item.
4. Keep the zero-custom-FFI source/boot/build/binary checks in the release lock;
   execute the 39-certificate/full-source regression as G7/G9 evidence.
5. Move stable regression IDs and lifecycle fields into the authoritative
   Candle-native ledger, then advance the immutable import coordinate.
