# S1 reference-v9 two-sweep independent audit

Date: 2026-08-31 UTC

## Outcome

Independent read-only review accepts the closed reference-oracle collection
with no P0, P1, or P2 finding.  This accepts the evidence as a stable
two-sweep reference input; it does **not** approve a candidate, promote a
binary, or substitute PFT/HOL Light evidence for direct Candle execution.

The frozen artifact root is:

`/project/flyspeck-candle-runs/s1-reference-v9-csdp-two-sweep-652a18a-95bb84f`

## Exact audit facts

- The final receipt closes 130 of 130 target runs: two sweeps of 65 targets,
  with zero pending targets and zero publication interruptions.
- All 65 cross-sweep pairs have identical source, theorem,
  hypothesis/global-axiom, and post-kernel-state fingerprints.  Each sweep
  records 97 theorem identities.
- All 66 live source files match the hashes bound by the contract.
- The stable runtime/tool projections agree across all 130 successful runs.
  Raw ASLR addresses differ as expected; normalized ELF observations and
  file digests agree.
- Project `95bb84f`, Candle `652a18a`, and reference HOL Light `1258c12`
  remain clean, with no replacement objects, grafts, or index exceptions.
- Sweep 2 target 036 attempt 0001 is preserved as interrupted evidence and
  is not selected as success.  Attempt 0002 is the selected authenticated
  successful retry with a fresh nonce.
- The sealed layout contains 1,178 read-only single-link files and 264
  mode-0700 directories, with no symlinks or pending publication files.

The independently recomputed SHA-256 identities are:

| Object | SHA-256 |
| --- | --- |
| final receipt | `93a4d84fca182ca72dff3d0ffdad7b70abc91d7a33bcbc0855f82cb8d76010a3` |
| raw contract | `8270f75b348fe166bde87804b628e92974cac4bc5e43f8400be958beb699e3d7` |
| compact contract | `9ce6adff5a24f9634180232351e41fd170a2ed9cdfe3a57d8ea80d9949d2bf66` |
| status | `f482fc9027ba60b0ef9d30775688c33c5ffab4e125ed70a859f45f07653cd049` |

## Boundary and next use

The evidence is deliberately still `candidates_unapproved`, with promotion
disabled.  Its next legitimate use is the independent approval comparison
against a qualified current direct Candle binary.  The critical path to that
binary remains:

1. finish the exact-head CakeML warm reverse-dependency gate;
2. pass the pristine-cold canonical bootstrap replay at the same head;
3. repin Candle and rebuild/link under authenticated provenance;
4. run the direct 20/400 parser gates, linked compatibility, and d0/d1;
5. advance to current-binary S1 and then whole pinned Flyspeck S2/S3.

No HOL, Holmake, Candle, parser, or candidate-approval run was performed by
the independent audit.
