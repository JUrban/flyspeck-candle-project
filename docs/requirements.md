# Roadmap acceptance ledger

Status values are `open`, `in progress`, `proved`, or `not required` for the
selected claim.  A green unit test is not enough to mark a broad item proved;
the evidence column names the release-level artifact that is required.

| Gap | Status | Required evidence |
| --- | --- | --- |
| G1 Candle PFT consumer | in progress | Compiled checker; pinned schema/ruleset/policy; positive and per-command corruption tests; exact theorem/assumption result; soundness-export connection. |
| G2 PFT scale | in progress | Streaming/segmented merge and replay; effective deletion/reuse; checkpoints; target reachability; measured full-trace resource envelope. |
| G3 HOL Light/Flyspeck producer | in progress | Direct HOL Light instrumentation or semantics-preserving bridge; three representative leaves; one clean-manifest Flyspeck leaf replayed exactly in Candle. |
| G4 Dopen | open (source track) | Current-master parser, inferencer/CV, soundness and completeness proof integration, layered corpus. |
| G5 pointer equality | open (source/performance track) | End-to-end source/backend/runtime semantics and measured Candle/Flyspeck need. |
| G6 custom FFI | open (source/tooling track) | Versioned ABI, bounds/error behavior, deterministic tests, and explicit untrusted-input policy. |
| G7 OCaml compatibility | open (source track) | Rebased fix-top100 changes and machine-readable whole-suite results. |
| G8 loader/build | in progress | Pinned source order and generated inputs; deterministic paths; resume semantics; explicit full-versus-short build. |
| G9 nonlinear/LP evidence | open | Pinned certificates/traces and Candle-checked theorem connections for the full path. |
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
