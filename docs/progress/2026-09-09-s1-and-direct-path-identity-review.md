# S1 and direct-loader path-identity review — 2026-09-09

## Scope and invariant

This was the requested bounded review of path identity in the S1 finalizer and
the direct Flyspeck runner.  The durable authority is artifact role, repository
or source identity, logical relative path, and content hash.  Absolute
collection, worktree, attempt, and snapshot paths are retained only as
run-local observations.

No qualified S1 report, runtime, source, transcript, semantic evidence, or
identity byte was changed.

## S1 finalizer

Branch and exact implementation:

- branch: `codex/s1-finalizer-logical-relocation-v16`
- commit: `413860a6eff70e2e1cc48ac5184dcfc93067ab79`
- `scripts/finalize-top100-report.py` SHA-256:
  `1b3f78cd41ef288116e77d70f88e46f8b33a0bac4206c3d7df2ac8a64c08a54e`
- `scripts/dry-run-finalize-top100-report.py` SHA-256:
  `fea22bd9cb35a956100491b3a17e393ac2eb4bd3ff1bf8dca4dec5f3afbe32b4`

The finalizer now accepts a controller/validator artifact observation below a
different absolute root only when both outputs agree and the exact approved
logical relative path remains unchanged.  Role prefixes remain exact.  Path
syntax must be canonical absolute syntax.  Artifact capture still binds the
ordinary-file identity and hashes, and unauthorized hard-link/path/symlink,
changed-byte, and cross-artifact inode reuse cases remain rejected.

The complete finalizer test suite passed: 79 tests in 463.962 seconds.

### Actual two-run dry-run result: failed closed

The non-authorizing replay used the two unchanged reports:

- run 1 report SHA-256:
  `e7e840b36ac3a5901649dca97671c940c46b403510a6c72e658938760f0e9b37`
- run 2 report SHA-256:
  `402aaabdf47b528a5ab5e45c265deb91a3033e8b6920b8698e95d50793332ecc`

Preserved failure report:

- `/project/flyspeck-candle-runs/great100-schema4-5e6362f-finalizer-dry-run-v3-attempt-002.json`
- SHA-256:
  `95e969b43f7544e8687fab91e366ecb5dd61c794d1579c7ec6422d486f06b67a`

It failed before record replay with:

`ValidationError: malformed schema-4 Great100 report`

The precise mismatch is that each qualified report has the top-level key
`promotion`, while this exact finalizer's closed `REPORT_KEYS` set omits
`promotion`.  There are no missing report keys and `promotion` is the sole
extra key.  The dry-run result is null, so no 130-record success is claimed.
The intercepted destination is absent and no staging directory remains.

Per the stop rule, no further finalizer correction was attempted.  No
authorization v3 was requested.

## Direct-loader development

Separate Candle development branch:

- branch: `codex/v13-direct-logical-path-authority-v14`
- implementation commit: `1b75ff7c746dcfe9e71a3a5a3994b4ab20f0f367`
  (`Bind direct loader paths by logical source identity`)
- dry-run harness commit: `5b5a955f9077e8680fdbedc2afdb299b7e3a07b7`
  (`Add real-plan direct loader relocation dry run`)
- `candle/flyspeck_stratum_runtime.py` SHA-256:
  `4b9117a549f3a45e1b3468ec86d83503ab27ad0b2cb91927ee1b029b5653c8bb`
- relocation harness SHA-256:
  `c291b918e0ab3c74ae9bfc677fcf722da9ecb4bb42a336c9860195e1613f6cb5`

The runner now derives exact lexical source requests from the authenticated
runtime setup and manifest source graph, resolves them through the loader/search
context active at that source position, and binds the selected manifest node by
logical repository, relative path, source key, role, hashes, normalization, and
request context.  The runtime trace still checks exact run-local
resolved/canonical/selected observations, but binding IDs no longer depend on
absolute roots.  No basename lookup or arbitrary alias fallback was added.

Adversarial tests reject unexpected relative requests, changed bytes, final
symlink substitution, hard-link substitution, and an unrelated same-basename
file in another repository root.  Focused results:

- physical source-trace tests: 6/6 passed;
- direct stratum runtime tests: 45/45 passed;
- direct stratum plan tests: 10/10 passed.

### Actual-plan relocation dry run: passed, nonpromotable

The relocation harness consumed the actual prior 00-base-through-029 plan and
failed development attempt, reauthenticated all 400 manifest source records,
derived 404 exact loader resolutions, and built the 131 bindings required by
that boundary.  It copied authenticated source/control/normalization bytes
under a distinct temporary root and rebuilt the contract there.

Preserved report:

- `/project/flyspeck-candle-runs/v14-direct-loader-real-plan-relocation-dry-run-attempt-002.json`
- SHA-256:
  `47f24a26e698e786a518b42614e18d982385ec6414eb18ab00f566cc3eea8e0d`
- logical projection SHA-256:
  `b278e7d570c6e4f5510d1813f4d22a2b7c7c165ce609b21407a0d3e6faad5ff6`

The absolute observation digests changed while every logical binding identity
remained identical.  The lexical request `hol.ml` resolved specifically to
`candle:hol.ml`.  This report explicitly forbids promotion and is not Candle
execution or S2/S3 evidence.

## Gate outcome

The direct relocation test is ready, but the complete S1 finalizer dry-run gate
did not pass.  Therefore authorization v3 was not requested and
00-base-through-029 was not rerun.  No new actual Flyspeck action result is
claimed in this cycle.
