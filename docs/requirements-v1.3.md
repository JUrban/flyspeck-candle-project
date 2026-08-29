# Governing v1.3 S3 acceptance ledger

The locked v1.3 roadmap supersedes v1.2 for the release claim.  The target is
S3: pinned Flyspeck source and generated inputs are parsed, typed, executed,
and audited by compiled CakeML/Candle without a HOL Light runtime in the
production path; nonlinear and LP evidence is checked in that run.  The
Isabelle tame-graph classification remains an explicit premise.  PFT is a
parallel validation lane and cannot satisfy any source-execution gate.

Status values are `open`, `in progress`, `proved`, or `not required` for S3.
A row is proved only by the named release evidence, not by a narrower smoke
test or implementation commit.

| Gap | Status | Required S3 evidence |
| --- | --- | --- |
| G1 OCaml-compatible open | in progress | OCaml oracle pack; current AST semantics/parser/elaboration; `infer_open` and `infer_d`; state/stamp invariants; CV correctness; soundness, canonicalization, completeness; compiled open-heavy Candle slice. |
| G2 language/runtime compatibility | in progress (repository inventory projected onto exact 400-node closure: 3,689 findings/329 files; selected local-open and ordinary-module subsets resolved; sole selected `Set.Make` application normalized; four selected timing-only `Unix.gettimeofday` calls use manifest-audited deterministic zero telemetry; the 32-site historical GLPK process chain is locked, has no selected external lexical caller, and remains fail-closed pending complete-run evidence; other runtime remedies and semantic regressions remain open) | Closed compatibility ledger for required numeric, float, bytes/string, comparison, exception, mutation, module, parser-state, and I/O behavior; differential and negative tests. |
| G3 pointer identity | in progress (immediate-int remedy/proof complete; allocated-site source remedy locally tested; compiled integration, exact full-run fingerprints, and scale performance open) | Corpus call-site classification and either verified end-to-end identity/GC semantics or justified transformations with representative performance evidence. |
| G4 custom FFI contract | not required for the pinned selected route (authenticated elimination) | Selected source and generated boot contain zero custom-FFI calls; the build recipe applies no custom C patch; clean executable `c20b3ec...` uses the pristine compiler-archive `basis_ffi.c` and passes the compiled suite plus authenticated direct frontier. Repository-root launch, fail-closed `Sys.command`, offline exact LP preparation, and the static 39-certificate inventory replace the historical calls. Any reintroduction reopens G4. |
| G5 Candle regression baseline | in progress | All 65 Great-100 load entries covering the pinned 100 theorems from clean state; exact theorem/definition/assumption fingerprints; no skips/new axioms; two semantic matches; timing/RSS bundle. |
| G6 loader/build system | in progress (exact manifest/actions/normalization/generated-input contracts active; full-run, relocation, checkpoint, and corruption/reorder matrices open) | Manifest-rooted dependency DAG and generated inputs; build-mode guard; structured strata; relocation; versioned atomic checkpoints; clean, resume, corruption, and reorder tests. |
| G7 Flyspeck mathematics/data | in progress (exact LP archive preparation and 39-certificate runtime inventory active; direct LP/nonlinear execution and evidence closure open) | Direct Candle nonlinear and LP paths, exact artifact hashes/schema/linkage, complete evidence, negative mutations, and explicit Isabelle premise. |
| G8 scale | open | Small-server lanes and cumulative prefixes; allocation/retention data; deterministic cache policy; measured capacity/headroom; bounded diagnostics and materially cheaper resume. |
| G9 assurance/release | in progress | One manifest connecting source, tools, executable theorem, assumptions, generated inputs, tests, checkpoints, resource envelope, deviations, and machine-code soundness boundary. |
| G10 PFT | in progress (parallel P1) | Hardened complete replay and differential artifact; explicitly not S2/S3 evidence. |
| G11 Isabelle boundary | not required for S3 | Exact named premise and canonical statement; transport/reproof only for S4. |

## Milestone claims

| Level | Required result |
| --- | --- |
| S0 | Pinned HOL Light base accepted by compiled Candle with clean provenance. |
| S1 | Complete pinned Great 100 source corpus with exact semantic fingerprints. |
| S2 | Full pinned Flyspeck HOL-side source build executes through CakeML/Candle without HOL Light. |
| S3 | S2 plus nonlinear and LP evidence closure inside that direct Candle run. |
| S4 | S3 plus checked Isabelle tame-graph proof transport or reproof. |

## Promotion gates

1. **G0 target:** exact source, build mode, final theorem, assumptions, tools,
   profiles, and manifests are pinned.
2. **G1 harness:** every failure is deterministic, localized, categorized,
   fingerprinted, and suitable for minimization.
3. **G2 Dopen:** the verified inference stack builds and a real open-dependent
   compiled Candle slice matches OCaml/HOL Light reference fingerprints.
4. **G3 S1:** the whole Great 100 inventory is green and audited with no hidden
   skips.  Broad Flyspeck patching cannot substitute for this gate.
5. **G4 Flyspeck slices:** every declared stratum has a direct Candle leaf,
   including nonlinear and LP samples.
6. **G5 prefix scale:** cumulative prefixes fit the calibrated envelope or
   carry a documented larger-server qualification with retention evidence.
7. **G6 release:** two clean S3 runs have identical semantic artifacts, one
   declared-boundary resume matches them, and input/checkpoint/certificate
   mutations are rejected.

## Mandatory release artifacts

- Compatibility ledger entries with reproducer, OCaml result, Candle result,
  category, remedy, proof obligation, regression ID, affected files, and status.
- Canonical fingerprints for final theorem, definitions/types, hypotheses,
  assumptions, and every Great 100 target.
- Complete ordered source/generated-input/certificate manifest and build-mode
  identifier, plus exact compiler/runtime/OS/locale/environment policy.
- Structured logs, checkpoint index and hashes, wall/RSS/disk high-water,
  positive/negative/relocation/resume matrices, and known deviations proved
  outside the pinned dependency closure.

For Great 100 S1 promotion, archive exactly two completed schema-4 reports with:

```sh
python3 scripts/finalize-top100-report.py \
  /path/to/run-1/report.json \
  /path/to/run-2/report.json \
  /new/path/to/s1-archive \
  --external-receipt /path/to/reviewed-finalization-authorization.json \
  --external-receipt-sha256 SHA256_FROM_AN_OUT_OF_BAND_CHANNEL
```

The destination must be fresh and outside both Git checkouts. Schema 3 is
unconditionally non-promotable: it cannot retrospectively prove two distinct
runs or the exact runtime/provenance bytes observed by each process. Schema 4
must bind distinct suite and process nonces to exact transcript bytes, line
offsets for suite/start/linked/complete markers, the schema-6 linked-record hash
seen by every process, and exact V2 theorem and post-state wire records. The
finalizer reparses those records and requires them to equal the manifest,
report, second run, and independently reviewed OCaml approval projection.

The report must also bind the exact committed provenance helper, runner,
Great100 manifest, serializer, and launcher; the canonical 65-target,
66-source-file, 97-request live source closure; identical clean pre/post runtime
states; and complete process/timing/RSS sampling. The finalizer executes only a
captured committed copy of the provenance helper, archives the exact validated
reports, transcripts, source files, approval/provenance files, executable,
linked outputs, controllers, finalizer, and Python/Git tool bytes, and emits a
closed SHA-256 inventory. An externally supplied receipt digest additionally
binds the two exact report bytes and nonces, semantic/source/approval/link
identities, finalizer project commit and bytes, and tool identities.

The independent approval must be the committed
`candle-s1-identity-approval-v1` artifact: 65 manifest-ordered targets, two
distinct reference-session nonces per target, one identical canonical
`{serializer_sha256,theorems,post_state}` identity, the reviewed three-file
reference-source delta policy, and exact candidate/plan/request/transcript/
source-contract attachment records. The finalizer resolves every attachment as
an ordinary Candle-root-relative file, rehashes it, enforces distinct run
artifacts, and retains its exact bytes. It also captures the committed
`candle/reference_fingerprints.py` validator and replays every staged schema-v6
candidate from its exact staged plan, generated request, and transcript under
the captured compatible regression/serializer semantics. The replay must bind
the target, selected source hashes, reference head, session nonce, and source
contract and derive exactly the independently approved identity projection;
arbitrary text and legacy candidate formats are not evidence.

The external authorization JSON has exact top-level keys `schema`, `kind`,
`issued_utc`, `authority`, `reports`, `suite_nonces`,
`linked_record_sha256`, `source_closure_sha256`,
`semantic_projection_sha256`, `independent_approval`, `project`, and `tools`.
It uses schema 1 and kind `candle-great100-finalization-authorization`;
`reports` contains the two ordered `{bytes,sha256}` records, `project` binds
the finalizer Git head and committed script record, and `tools` binds the
resolved Python and Git paths and records. Its digest must be conveyed outside
the receipt itself and supplied literally on the command line. The finalizer
does not generate or self-approve this receipt.

No current report is made promotable by this requirement. Promotion remains
blocked until Candle emits the complete schema-4 contract and a separately
reviewed independent OCaml approval artifact and external authorization receipt
exist. The receipt authority, kernel/filesystem/process semantics, pre-exec
dynamic-loader behavior, and semantics of the archived tools remain explicit
trusted boundaries.

The project is not complete until every S3-required row and promotion gate is
proved by current artifacts.  PFT replay success, source parsing alone, a
partial corpus, or one full direct run is insufficient.
