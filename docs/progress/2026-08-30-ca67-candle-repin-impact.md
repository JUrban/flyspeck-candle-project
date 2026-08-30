# CakeML `ca67ffaa` Candle repin impact (2026-08-30)

## Gate

This is a preparation checklist, not authority to repin.  Do not mutate Candle
or materialize new plans until the repaired CakeML replay at
`cakeml-parser-diagnostic-proof-ca67ffaa8-attempt-001` has completed all four
stages with zero-exit receipts and its required postconditions pass.

The intended CakeML target is
`ca67ffaa831845c20c905bf94924b457951f8968`.  The old Candle authority is clean
at `688d9d1738a7021501f95b6f0ed788e014fa726f`.  Preserve its worktree and create
a separately named branch/worktree for the new pin.

## Candle mutation closure

The committed repin cascade covers exactly these eight existing files:

1. `candle/flyspeck_manifest.py` — source CakeML pin;
2. `candle/flyspeck_manifest.json` — generated manifest;
3. `candle/flyspeck_parser_diagnostic_pilot.json` — manifest-bound descriptor;
4. `candle/flyspeck_parser_diagnostic_all_inventory.json` — manifest-bound
   descriptor;
5. `candle/flyspeck_all_inventory_sources.py` — exact generated authority byte
   counts and hashes;
6. `candle/test_flyspeck_manifest.py` — exact pin fixture;
7. `candle/test_cakeml_artifact_provenance.py` — exact pin fixture;
8. `candle/FLYSPECK_PARSER_DIAGNOSTIC.md` — current operational pin and gate.

Run the manifest generator so that `candle/flyspeck_source_digests.ml` and
`candle/flyspeck_full_build.ml` are regenerated and checked.  Their bytes are
expected to remain identical because neither the source graph nor action order
changed.  A byte change in either file is therefore a stop-and-diagnose event.

Do not repin the normalization contract or controller code merely to make
hashes change.  Do not rewrite historical compatibility-ledger authorities.

## Regeneration and tests

The required order inside the fresh Candle worktree is:

1. change the source pin and exact fixtures/documentation;
2. regenerate and check the manifest;
3. regenerate both parser descriptors from that manifest;
4. update `EXPECTED_AUTHORITIES` with the new manifest and all-inventory
   descriptor byte/hash records;
5. run the manifest, descriptor, all-inventory source, parser-controller, and
   bootstrap-provenance focused suites;
6. require the exact all-inventory invariants: 400 inputs partitioned into 382
   original plus 18 normalized sources, and 727 actions partitioned into 721
   masked plus 6 embedded actions;
7. run the full lightweight Candle test discovery and commit a clean new
   Candle authority.

## Artifact cascade

After the Candle commit, create fresh roots for both parser plans and the
direct stratum plan/schedule/prefixes.  Their source input sequences should be
stable, but their Candle/manifest authorities and receipts necessarily change.

The normalized overlay `v13-normalized-overlay-688d9d1` and generated LP input
tree `v13-generated-lp-688d9d1` bind Flyspeck and their own contracts rather
than the Candle/CakeML pin.  They may be reused only after exact revalidation;
rematerializing them is optional naming hygiene.

Never relabel or overwrite these historical authorities:

- the failed `cakeml-parser-diagnostic-proof-964406486` replay;
- either generation of old pilot/all-inventory parser plan roots;
- either old direct stratum plan root and its schedule/prefix files.

There is no old canonical bootstrap, linked runtime provenance, linked binary,
or linked compatibility result to migrate.  The previously planned result
roots remain absent.  The new Candle head requires a fresh canonical bootstrap
and fresh schema-6 link even if some generated executable bytes later match.

## Post-repin execution order

Supersede, rather than silently reinterpret, the live canonical-bootstrap,
linked-compatibility, and direct-result handoffs with exact new heads, roots,
PIDs, plan hashes, and result names.  Keep dated historical reports unchanged.

The clean generic gate authorities at project commits `aaeb533...` and
`9a79224...` contain no hard-coded old CakeML pin and accept explicit heads;
reuse their reviewed code without advancing their frozen worktrees.

The remaining order is strict:

1. repaired four-stage replay pass;
2. Candle repin, regeneration, tests, and clean commit;
3. fresh parser and direct plan materializations;
4. reviewed live handoffs and canonical prelaunch gate;
5. fresh canonical bootstrap and schema-6 link;
6. 20-input parser pilot plus independent consumer;
7. 400-input parser inventory plus independent consumer;
8. linked compatibility gates;
9. diagnostic direct cutpoints, then cumulative direct boundaries with the
   independent result consumer.
