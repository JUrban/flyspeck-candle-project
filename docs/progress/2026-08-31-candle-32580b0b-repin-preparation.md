# Candle repin preparation for CakeML `32580b0b7` — 2026-08-31

## Decision

**PREPARED / HOLD.**  Candle now has a clean additive candidate pinning exact
CakeML `32580b0b76434f69ab545232b25a4b892173f1ae`.  It remains explicitly
non-promotable pending a complete exact-head warm reverse-dependency replay
and a separately accepted pristine-cold replay at that same CakeML commit.
It does not authorize bootstrap, link, plan materialization, or parser-gate
execution.

This report supersedes the current-candidate status in
`2026-08-31-candle-480a9f4-repin-preparation.md`; that report and its Candle
commit remain unchanged as historical preparation evidence.

## Exact identities and ancestry

- Historical prepared Candle commit:
  `d22ad5ed1dd8f3004983034059b5f71c7262bde4`, tree
  `51204d91a5dd35d4aeb1bcea3e3d5172148d2680`.
- Additive prepared Candle commit:
  `103691ef9b26662bef7feacc86201862b1c5dfd8`, tree
  `08e74bdb5c01e2b0e979c4589adad0c6fa5cc2a7`.
- Candle worktree:
  `/project/worktrees/candle-runtime-pin-480a9f4-prep-v13`.
- Candle branch: `codex/flyspeck-v13-runtime-pin-480a9f4-prep`.
- CakeML target: `32580b0b76434f69ab545232b25a4b892173f1ae`,
  tree `d2423910af63189c956e7d2f936c7190ec1924ae`, sole parent
  `480a9f4fcdeaea0d50ed2b6e1fc7998371610ded`.
- Manifest Flyspeck source: `1ce0353008eba83d3c76ae9a25c3c242e4802d53`,
  tree `57de864e0bbe417e3099ed8a34137fbc3134a143`.

The CakeML advance is proof-only: relative to `480a9f4fc...`, it changes only
`compiler/backend/proofs/backendProofScript.sml`, adding 34 proof-script lines
that discharge the strengthened initial namespace-domain obligations.  See
`2026-08-31-cakeml-backend-dopen-repair.md`.  This source classification is
not a substitute for either exact-head qualification replay.

## Bounded mutation closure

The additive Candle commit changes exactly the established eight files:

1. `candle/flyspeck_manifest.py`;
2. `candle/flyspeck_manifest.json`;
3. `candle/flyspeck_parser_diagnostic_pilot.json`;
4. `candle/flyspeck_parser_diagnostic_all_inventory.json`;
5. `candle/flyspeck_all_inventory_sources.py`;
6. `candle/test_flyspeck_manifest.py`;
7. `candle/test_cakeml_artifact_provenance.py`;
8. `candle/FLYSPECK_PARSER_DIAGNOSTIC.md`.

There are no controller, normalization, compatibility-ledger, build, runtime,
or source-graph changes.  The old `480a9f4fc...` literal has no occurrence in
the new eight-file closure.

The regenerated authorities are:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `flyspeck_manifest.json` | 820,818 | `6aae8e36e8ab7ac7ad5d6326d15065b14ff7c9feffe8541a23a92d6568701e5c` |
| `flyspeck_parser_diagnostic_pilot.json` | 14,715 | `dd9c0c119e9c10751b1dc50f32def1d667748f3dfe43f576649ccc13bfbcfd92` |
| `flyspeck_parser_diagnostic_all_inventory.json` | 206,558 | `845c894436c07ec6f44208d4270c8219e40c23630218588d6db9e5922ca34782` |

Regeneration left both manifest-derived ML programs byte-for-byte identical
to `d22ad5e` and the original `688d9d1` base:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `flyspeck_source_digests.ml` | 34,704 | `343ac5686f3163eb4fe6512bdbfe316999aba500d60d40cca4209d7d4263e562` |
| `flyspeck_full_build.ml` | 56,616 | `712f569228009af1067231f77548d2cafb216051cc26f2abd2b24b4440445932` |

The required `git diff --exit-code` check passed for both ML files.  Any byte
change would have stopped the repin rather than being committed.

## Static validation

Only host-side generation, static validation, and lightweight tests ran:

- manifest regeneration and independent `--check`: PASS, 297 roots, 400
  source nodes, 43 generated inputs;
- `check-pilot`: PASS, exactly 20 manifest nodes;
- `check-all-inventory`: PASS, exactly 400 manifest nodes;
- focused manifest, parser-controller, all-inventory-source,
  artifact-provenance, and bootstrap-transition suites: 159/159 PASS in
  143.732 seconds;
- full Python `unittest` discovery under the required inherited `C.UTF-8`
  environment: 330/330 PASS in 161.965 seconds;
- `git diff --check`: PASS; final Candle worktree: clean.

The all-inventory tests re-established 400 inputs = 382 exact originals + 18
normalized sources, and 727 loader actions = 721 whole-line masked + 6
embedded retained actions.

## Work deliberately not performed

This repin invoked no `Holmake`, bootstrap, link, linked-provenance recorder,
plan materializer, parser runtime, or parser-result consumer.  It consumed no
warm products and relabelled no historical root.  The pristine cold worktree
and prospective launch authority pinned to `480a9f4fc...` are obsolete for
this new head and must not be launched or cited as `32580b0b7` evidence.

## Remaining gated order

1. Complete a fresh warm reverse-dependency replay of all 50 targets at exact
   CakeML `32580b0b7`; require its sealed zero-exit completion evidence.
2. Only after warm PASS, freeze a new product-free CakeML worktree at exact
   `32580b0b7` and run the accepted pristine-cold controller.  Require all five
   zero-exit timing receipts, terminal `stage=complete`, `finished_utc`, all
   seven output postconditions, no live replay process, and exact retained
   hashes.
3. Independently review this Candle commit against the exact-head cold receipt.
   Until then retain **prepared/non-promotable**.
4. From a fresh clean checkout of the accepted Candle head, re-run the static
   checks and materialize new pilot, all-inventory, and direct-stratum plan
   roots.  Do not reuse historical plan roots.
5. Replace and independently review the canonical handoff with the exact
   accepted heads, roots, hashes, and fresh destinations; pass prelaunch.
6. Run the cache-disabled canonical bootstrap, ordinary schema-6 link, and
   `check-linked`.
7. Run and consume the 20-input pilot; only after consumed PASS run and consume
   the 400-input inventory.
8. Only then proceed to linked compatibility and direct cutpoint/boundary
   execution.

Literal launch commands remain withheld because the qualifying warm/cold
receipts and their fresh exact-head roots do not yet exist.
