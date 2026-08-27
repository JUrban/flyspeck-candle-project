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
| G2 language/runtime compatibility | in progress | Closed compatibility ledger for required numeric, float, bytes/string, comparison, exception, mutation, module, parser-state, and I/O behavior; differential and negative tests. |
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

The project is not complete until every S3-required row and promotion gate is
proved by current artifacts.  PFT replay success, source parsing alone, a
partial corpus, or one full direct run is insufficient.
