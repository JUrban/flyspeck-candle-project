# Roadmap acceptance ledger

Status values are `open`, `in progress`, `proved`, or `not required` for the
selected claim.  A green unit test is not enough to mark a broad item proved;
the evidence column names the release-level artifact that is required.

| Gap | Status | Required evidence |
| --- | --- | --- |
| G1 Candle PFT consumer | in progress | Compiled checker; pinned schema/ruleset/policy; positive and per-command corruption tests; exact theorem/assumption result; soundness-export connection. |
| G2 PFT scale | in progress | Bounded streaming and proved process restart are implemented; full-sequence target reachability and measured trace/resource envelope remain. |
| G3 HOL Light/Flyspeck producer | proved | Direct producer; ordinary clean-manifest source leaf; digest-checked list/refinement and real-arithmetic/refinement leaves; all replayed exactly by compiled Candle. |
| G4 Dopen | open (source track) | Current-master parser, inferencer/CV, soundness and completeness proof integration, layered corpus. |
| G5 pointer equality | open (source/performance track) | End-to-end source/backend/runtime semantics and measured Candle/Flyspeck need. |
| G6 custom FFI | open (source/tooling track) | Versioned ABI, bounds/error behavior, deterministic tests, and explicit untrusted-input policy. |
| G7 OCaml compatibility | open (source track) | Rebased fix-top100 changes and machine-readable whole-suite results. |
| G8 loader/build | in progress | Pinned source order, deterministic paths, resume semantics, and explicit main/full driver are implemented; completed full-build evidence remains. |
| G9 nonlinear/LP evidence | in progress | The complete certificate/archive inventory is pinned and the four-theorem L2 connection is implemented; completed compiled replay remains. |
| G10 Isabelle tame graphs | not required for L2 | For L3 only: checked export/bridge or reproof with theorem correspondence. |
| G11 end-to-end regression | open | 100 theorems, representative leaves, full L2 build, theorem/axiom/resource audit. |
| G12 release manifest | in progress | Commits and hashes; policy; target fingerprint; expected assumptions; executable identity and resource record. |

## Gates

1. A compiled Candle executable reconstructs representative current-format PFT
   traces, rejects malformed and unauthorized variants, and is covered by the
   intended Candle/CakeML theorem.
2. A real ordinary, compute-heavy, or certificate-heavy Flyspeck leaf replays
   from a clean manifest with exact theorem and assumption equality; three
   leaves are used to select the producer route.
3. The full trace fits the recorded resource envelope, is checkpoint-restartable,
   and has deterministic theorem fingerprints.
4. Nonlinear and LP artifacts are pinned and checked inside Candle; the full
   `build_to_full`-equivalent theorem and assumption audit are reproduced.

The full objective is complete only when every L2-required row and Gate 1–4 is
proved by current artifacts.  Source-as-is compatibility and optional L3 remain
separately labelled and cannot be used to overstate the L2 result.

For claim discipline, the resulting release is called a full
`HOL Light -> PFT -> Candle` L2 replay.  It must not be called direct Flyspeck
source execution or HOL Light replacement.  The supplied roadmap is version
1.2; a source-substitution criterion from another roadmap would change which
rows are on the critical path and requires that roadmap to be separately
adopted and pinned.

## Current gate evidence

The first Gate 2 artifact is
`candle/pft/tests/fixtures/flyspeck-hol-library.pft.bin`, locked in the manifest.
It reconstructs Flyspeck's `IMAGE_DELETE_INJ_COMPAT` and `HAS_SIZE_2_EXISTS`
with exact empty assumptions and exact conclusions.  This satisfies the
ordinary-leaf and clean-manifest parts of G3, but not the three-leaf route
selection or full-build parts of Gates 2–4.  The companion
`flyspeck-refinement-leaves.pft.bin` now supplies the other two route-selection
classes.  It closes G3, but it remains deliberately distinct from the
compute-heavy, certificate-heavy, and full-build evidence required by G2, G9,
and G11.  `compute-zero.pft.bin` separately proves that the 62 equations from
the corrected Candle source initialize the verified compute context and that a
positive `COMPUTE` result passes exact `EXPECT` checking.  This closes the
source/release equation mismatch but is intentionally not counted as a
Flyspeck-specific compute-heavy Gate 2 leaf.

The producer restart fixture and `test-producer-resume.sh` additionally prove
that a killed proof-recording process can resume the same logical PFT stream,
truncate a stale post-checkpoint tail, retain an earlier theorem dependency,
and produce bytes identical to an uninterrupted run.  The real-build driver
uses the same boundary for the checked-in `main` and `full` sequences.  This
implements G2/G8 restart semantics but does not supply the full-trace resource
measurement or final theorem replay needed to mark either row proved.

The live locked full run has also crossed exporter-managed source boundaries
20 and 30.  Boundary 20 restored with exact byte offset, command count, and
type/term/theorem counters before proof production continued.  The coordinator
discovery repair and the rejected mid-proof snapshot are recorded in
`docs/progress/2026-08-27-full-l2-run.md`.  This is stronger operational
evidence for G2/G8, but remains interim until export and compiled replay finish.

The full-input audit decodes all 39 LP certificate shards and matches their
19,715 unique graph identifiers bijectively with the 19,715-entry tame archive.
The full target script saves the LP theorem, nonlinear theorem, prior
conditional theorem, and a primitive-inference combination proving
`import_tame_classification ==> the_kepler_conjecture`.  LP shards and groups
of serialized nonlinear cases now expose restart boundaries.  These facts move
G9 into progress, but no full-build claim is made until the resulting trace has
completed and replayed in the compiled checker.
