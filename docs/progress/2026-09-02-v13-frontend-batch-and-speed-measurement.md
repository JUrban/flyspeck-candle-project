# v1.3 quotation-aware frontend batch and speed measurement

Date: 2026-09-02 UTC

## Scope and claim boundary

The quotation-aware all-inventory diagnostic ran the old proof-built Candle
runtime over all 400 authenticated prepared inputs.  It reported 349 parser
passes, 50 parser exits, and one distinct runtime exit on the 9.1 MB
`archive_all.ml` input.  These are development diagnostics only.  They are not
S1, S2, or S3 evidence, and the PFT oracle is not counted toward any direct
Candle release gate.

The minimized failure evidence remains immutable at:

- `nonpromotable-parser-localization-ac15ba0-attempt-002`;
- 50 independently non-passing lexical chunks;
- 2,499 Candle parser invocations; and
- localization record SHA-256
  `7079983091e3a946f2478722dc285d007f12cfb1b271b5c78328022806a83ee2`.

The localizer deliberately does not claim that every independently failing
chunk is the first causal error in its complete source.  Forty chunks parse as
OCaml 4.14.1 and were line-minimized under that oracle.  Ten use the HOL
Light/Camlp dialect and were retained without applying an inappropriate modern
OCaml reduction oracle.

## First proved frontend repairs

CakeML worktree:
`/project/worktrees/cakeml-flyspeck-frontend-batch-v13`

Branch: `codex/flyspeck-v13-frontend-batch`

The first three independently committed repairs are:

| Commit | Repair | Exact boundary |
|---|---|---|
| `a5690401e` | path-only `include` declarations | lowers `include M.N` to the already proved `Dopen` declaration; no general module-expression include |
| `14f25006e` | trailing sequence semicolons | accepts `;` only before `)`, `end`, or `done`; rejects the invalid annotated form `(x : int;)` |
| `bffa9107e` | parenthesized annotated recursive binder | accepts `let rec (f : ty) = ...` and lowers it exactly like the existing `let rec f : ty = ...` form |

The `include` conversion uses `Dopen` because CakeML evaluation, declarative
typing, and inference all return the opened declaration environment.  Inside a
`Dmod`, that returned environment is lifted into the module, which supplies
the export behaviour needed by the path-only OCaml form.

OCaml 4.14.1 was used as an independent local syntax oracle for the semicolon
and annotated-recursive forms.  It accepts `(x;)`, `begin x; end`, trailing
semicolons in `while`/`for` bodies, and `let rec (f : int -> int) = ...`; it
rejects `(x : int;)`.  The committed grammar has the same boundary.

## Focused proof/test measurements

All commands used the pinned HOL4 tree and `Holmake -j2`; none is release
evidence.

| Head/change | Result | Wall time | Peak RSS | CPU | Swap |
|---|---:|---:|---:|---:|---:|
| path-only include, relocated seeded worktree | 17/17 theories | 23:29.27 | 4,774,300 KiB | 120% | 0 |
| final semicolon test-only replay after prerequisites | 1/1 theory | 3:53.34 | 1,384,792 KiB | 110% | 0 |
| annotated recursive binder | 3/3 theories | 9:25.79 | 3,365,632 KiB | 108% | 0 |

The semicolon work also included a successful 3/3 grammar/conversion/test
rebuild of the narrowed implementation before a test expectation was
corrected.  The failed assertion concerned the printed normal form of
`build_funapp`, not parsing or conversion.  After correcting that assertion,
the complete test theory passed as recorded above.

## Evaluation of the external speed advice

The advice in `docs/advice/external-advice-speed.md` remains directionally
useful, with the following measured qualifications.

1. **Accept the 20-then-400 cheap gate and batch frontend repairs.**  This has
   already prevented a blind full bootstrap after each of the 50 initial
   parser exits.  It is the highest-value recommendation.
2. **Use `-j2` only as a measured development option.**  The relocated
   17-theory run averaged only 120% CPU, and the two warm affected-theory runs
   averaged 108--110%.  These parser dependencies are mostly serial.  The
   advice's suggested 2--3 hour clean bootstrap is not established by these
   measurements.
3. **Do not treat copied theory products as a relocatable cache.**  Generated
   products copied from an exact-head sibling worktree did not avoid the
   17-theory rebuild because the ordinary HOL dependency state was bound to
   the old absolute paths.  Same-worktree warm products were useful.  A native
   cache experiment still requires the previously documented fetch hardening
   and toolchain-identity namespace.
4. **Keep release qualification clean and serial.**  The canonical controller
   remains cache-disabled and pins `Holmake -j1 cake.S`; no development result
   above changes that contract.
5. **Defer x64-only specialization and theory splitting.**  Both remain
   proof-architecture projects.  The corpus gate and small frontend batches
   are paying back immediately without expanding the trusted or proof surface.

## Critical next issue: structural records

Structural records are not another one-token grammar repair.  The selected
corpus contains immutable construction/projection/update, mutually recursive
record types, mutable fields, field reads, and field assignment.  In
particular, prepared inputs 066 and 257 contain mutable fields, and input 257
contains direct field assignments.  Treating mutable fields as immutable would
parse more files but would be semantically wrong.

CakeML's existing OCaml conversion supports constructor-qualified fake records
such as `C {field = value}` and `x.C.field`.  A structural-record extension can
reuse its generated constructor/projection/update functions, but it must also:

- synthesize stable constructors for unqualified `{field = value}` records;
- keep field helpers scoped consistently with OCaml modules;
- audit duplicate field labels before relying on field-only projection names;
- translate mutable cells through CakeML references;
- make reads dereference those cells and assignments update them; and
- preserve record-copy/update semantics rather than sharing mutable cells by
  accident.

The next implementation step is therefore a reproducible field/type/use audit
over the exact 400 prepared inputs, followed by immutable structural records
and mutable semantics as separately tested changes.  A new full `cake.S`
bootstrap should wait until this coherent frontend batch is quiet.

## Independent canonical build

The older Candle/CakeML canonical bootstrap attempt
`cakeml-canonical-bootstrap-f2f50a4-attempt-004` remains isolated from this
new CakeML branch.  At the report checkpoint it had passed 8/18 targets through
`basis_defProg`.  It is still useful for qualifying the f2 bootstrap dependency
repair and transition base, but it cannot qualify or ordinary-link the newer
frontend commits.

Direct whole-Flyspeck S2 and S3 remain open.
