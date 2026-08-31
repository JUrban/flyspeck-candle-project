# Candle repin preparation for CakeML `480a9f4fc` — 2026-08-31

## Decision

**PREPARED / HOLD.**  A clean, bounded Candle candidate now pins CakeML
`480a9f4fcdeaea0d50ed2b6e1fc7998371610ded`, but it is deliberately
non-promotable.  It does not authorize a canonical bootstrap, a linked
runtime, parser-plan materialization, or either the 20-input or 400-input
runtime parser gate.  Promotion still requires the pristine-cold CakeML replay
and its terminal receipts at that exact CakeML head.

No active CakeML proof, reference sweep, or PFT process was inspected, changed,
restarted, or used as input to this preparation.

## Exact identities

- Candle base: `688d9d1738a7021501f95b6f0ed788e014fa726f`, tree
  `8ab2848430a95a173724a12ed5ce05128b1da945`.
- Prepared Candle worktree:
  `/project/worktrees/candle-runtime-pin-480a9f4-prep-v13`.
- Prepared Candle branch: `codex/flyspeck-v13-runtime-pin-480a9f4-prep`.
- Prepared Candle commit: `d22ad5ed1dd8f3004983034059b5f71c7262bde4`,
  tree `51204d91a5dd35d4aeb1bcea3e3d5172148d2680`.
- CakeML target: `480a9f4fcdeaea0d50ed2b6e1fc7998371610ded`,
  tree `c81371cd44e1a09bcadd14866bdefc3e4bb56c06`.
- Manifest Flyspeck source: `1ce0353008eba83d3c76ae9a25c3c242e4802d53`,
  tree `57de864e0bbe417e3099ed8a34137fbc3134a143`.

## Bounded mutation closure

The Candle commit changes exactly the eight files prescribed by
`2026-08-30-ca67-candle-repin-impact.md`:

1. `candle/flyspeck_manifest.py`;
2. `candle/flyspeck_manifest.json`;
3. `candle/flyspeck_parser_diagnostic_pilot.json`;
4. `candle/flyspeck_parser_diagnostic_all_inventory.json`;
5. `candle/flyspeck_all_inventory_sources.py`;
6. `candle/test_flyspeck_manifest.py`;
7. `candle/test_cakeml_artifact_provenance.py`;
8. `candle/FLYSPECK_PARSER_DIAGNOSTIC.md`.

There are no controller, normalization-contract, compatibility-ledger, build,
or runtime changes.  The old CakeML pin has no occurrence in this eight-file
closure.

The regenerated authorities are:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `flyspeck_manifest.json` | 820,818 | `ba2342e4a515c926f408527bfed38e0b8b06d40a5b3187a879395e241905cb15` |
| `flyspeck_parser_diagnostic_pilot.json` | 14,715 | `d08f9122c5790b90e26157bd51ea4300600f686f522b32636ff5d4bf550341a0` |
| `flyspeck_parser_diagnostic_all_inventory.json` | 206,558 | `f9bbcb1ee6ff9b3f7852747112b44ece8cd08d175761555fcbd40382818e47e1` |

As required, regeneration left both manifest-derived ML programs byte-for-byte
identical to the base commit:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `flyspeck_source_digests.ml` | 34,704 | `343ac5686f3163eb4fe6512bdbfe316999aba500d60d40cca4209d7d4263e562` |
| `flyspeck_full_build.ml` | 56,616 | `712f569228009af1067231f77548d2cafb216051cc26f2abd2b24b4440445932` |

`git diff --exit-code` against the base passed for both ML files.  A byte drift
would have stopped this preparation.

## Static validation

Only host-side generation, static validation, and lightweight tests ran:

- manifest regeneration and an independent `--check`: PASS, 297 roots, 400
  source nodes, 43 generated inputs;
- `check-pilot`: PASS, exactly 20 manifest nodes;
- `check-all-inventory`: PASS, exactly 400 manifest nodes;
- the focused manifest, parser-controller, all-inventory-source,
  artifact-provenance, and bootstrap-transition suites: 159/159 PASS;
- full Python `unittest` discovery in the repository's documented inherited
  `C.UTF-8` environment: 330/330 PASS in 160.468 seconds;
- `git diff --check`: PASS; final Candle worktree: clean.

The all-inventory suite re-established all exact cardinalities: 400 inputs =
382 byte-identical originals + 18 normalized sources, and 727 classified
loader actions = 721 whole-line masked + 6 embedded retained actions.

A preliminary full-discovery invocation forced `LC_ALL=C` around the test
harness and obtained 329/330 because that locale makes isolated Python report
`utf8_mode=1`, while the independent stratum-runner contract intentionally
pins `utf8_mode=0`.  The single test passed alone and in the complete rerun
under the documented inherited `C.UTF-8` environment.  This was a harness
precondition mismatch, not a Candle or repin failure.

## Work deliberately not performed

This preparation did **not** invoke `Holmake`, consume warm proof products,
run or link a CakeML compiler, execute a canonical bootstrap, create schema-6
linked provenance, materialize new parser or direct plans, or launch any
parser input.  It also did not relabel any historical artifact root.

## Remaining gated commands and order

1. Finish the warm reverse-dependency traversal, then run and accept the
   pristine-cold replay at CakeML `480a9f4fc...`.  Require all five zero-exit
   timing receipts, terminal `stage=complete`, `finished_utc`, all seven output
   postconditions, no live replay process, and exact retained hashes.
2. Independently review this Candle commit against the cold receipt.  Until
   then, retain the label **prepared/non-promotable**.
3. From a fresh clean checkout of the accepted Candle head, re-run the
   manifest/descriptor checks and materialize fresh pilot, all-inventory, and
   direct-stratum plan roots.  Never reuse or rename historical plan roots.
4. Replace and independently review the historical canonical handoff with the
   exact accepted CakeML/Candle heads, cold attempt root, plan roots, hashes,
   and fresh destinations; pass its prelaunch gate.
5. Run the fresh cache-disabled canonical bootstrap, ordinary schema-6 link,
   and `check-linked`.  A diagnostic transition link is not release authority.
6. Run and independently consume the 20-input pilot from a fresh result root.
   Require schema 4, top-level `parse-pass`, and exactly 20 fresh `parse-ok`
   attempts.
7. Only after consumed pilot PASS, run and independently consume the 400-input
   profile.  Require schema 5 and exactly 400 fresh `parse-ok` attempts.
8. Only then proceed to linked compatibility and direct cutpoint/boundary
   execution.

Literal launch commands remain withheld here because their fresh roots and
accepted authorities do not exist yet.  The reviewed post-cold handoff must
bind those values before any of steps 3–8 is invoked.
