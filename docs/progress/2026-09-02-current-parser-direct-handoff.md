# Current parser and direct-source handoff — 2026-09-02

## Authorities and status

This handoff now binds:

- Candle `f2f50a44b438385031d75041c9bae35b94b01eae` at
  `/project/worktrees/candle-bootstrap-dependency-fix-v13`;
- CakeML `c2e26f43c35080d57fc18aba42d4023590b6daba` at
  `/project/worktrees/cakeml-flyspeck-runtime-stack-cold-c2e26f43c-v13`;
- HOL4 `a390cbabd3a4521bab4ee20281e3e42933a8a3ae`; and
- Flyspeck `1ce0353008eba83d3c76ae9a25c3c242e4802d53`.

The authenticated cold proof replay passed.  Canonical attempt 003 rebuilt all
18 targets and exited zero after 7:31:54, but final publication correctly
failed: the preflight controller had omitted 238 lazily materialized ancestor
make-dependency files and incorrectly required 36 generated-`Theory` depfiles
to reappear.  Its log, preflight, preimage archive, and immutable
non-promotable development snapshot remain under
`cakeml-canonical-bootstrap-c2e26f43-attempt-003`; they are not canonical
bootstrap authority.

Candle commit `f2f50a44...` fixes and tests that transition: it pins the stable
2,015-file CakeML ancestor dependency set, requires 18 target `Script.sml.d`
postimages to be fresh, and requires the 36 stale generated-`Theory` depfiles
to remain absent.  The full lightweight suite passes 340/340.  Canonical
attempt 004 is active at
`/project/flyspeck-candle-runs/cakeml-canonical-bootstrap-f2f50a4-attempt-004`.
Everything below is **HOLD** until that attempt atomically publishes a valid
`bootstrap-provenance.json`.  A partial log or zero Holmake exit alone is not
authority to link or parse.

## Current source-only plans

| Plan | Root | Plan SHA-256 | Host SHA-256 |
| --- | --- | --- | --- |
| pilot 20/20 | `parser-pilot-materialization-f2f50a4` | `ca95a55e3980d7b530f17075c8cfd2099376e582bbde7abd69540839be69e93f` | `2580221c8731b51def9f51e06386e341759d31d77b359b6c855c3c8dced71b5b` |
| all 400/400 | `all-inventory-materialization-f2f50a4` | `2ce5cdacdff876b3ab06d478f9f40c079787f5fa01630c796c43a218fb8db4e0` | `95773062546b535b29eea481ebaff86f5f09f63c4d6e2dd5dee6b9b5e01f35b5` |

The current direct plan root is
`/project/flyspeck-candle-runs/v13-stratum-plan-f2f50a4`; its plan SHA-256 is
`229492470f06114478647b05ec7c89bd995971a56ac7dc1e225eea0afb140626`.
It binds the fresh overlay `v13-normalized-overlay-cb3bbcb` and generated-input
tree `v13-generated-lp-cb3bbcb`, 297 actions, 400 source nodes, 43 generated
inputs, eight cumulative boundaries, and two diagnostic cutpoints.  None of
these host plans is parser, inference, theorem, S2, or S3 evidence.

## Canonical link gate

After bootstrap publication, require all four repositories clean and exact,
then use only the ordinary two-argument same-head linker:

```sh
/project/worktrees/candle-bootstrap-dependency-fix-v13/build-local-cakeml.sh \
  /project/worktrees/cakeml-flyspeck-runtime-stack-cold-c2e26f43c-v13 \
  /project/flyspeck-candle-runs/cakeml-canonical-bootstrap-f2f50a4-attempt-004/bootstrap-provenance.json

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S \
  /project/worktrees/candle-bootstrap-dependency-fix-v13/candle/cakeml_artifact_provenance.py \
  check-linked \
  --candle-root /project/worktrees/candle-bootstrap-dependency-fix-v13
```

Do not use the five-argument transition linker.  Require ordinary linked
schema 6 and a clean tracked Candle tree before every retained run.

## Parser pilot and inventory

Run the pilot into a fresh result root:

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S \
  /project/worktrees/candle-bootstrap-dependency-fix-v13/candle/flyspeck_parser_diagnostic.py \
  run --profile pilot \
  --plan-root /project/flyspeck-candle-runs/parser-pilot-materialization-f2f50a4 \
  --candle-root /project/worktrees/candle-bootstrap-dependency-fix-v13 \
  --candle-head f2f50a44b438385031d75041c9bae35b94b01eae \
  --flyspeck-root /project/worktrees/flyspeck-v13-source \
  --flyspeck-head 1ce0353008eba83d3c76ae9a25c3c242e4802d53 \
  --output-root /project/flyspeck-candle-runs/parser-pilot-result-f2f50a4-attempt-001 \
  --timeout-seconds 600 --max-cpu-seconds 600 \
  --max-address-space-gib 16 --max-output-mib 1
```

Immediately consume it with the independent frozen gate:

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S \
  /project/worktrees/flyspeck-project-runtime-gates-aaeb533/scripts/check-published-parser-result.py \
  --project-root /project/worktrees/flyspeck-project-runtime-gates-aaeb533 \
  --project-head aaeb533d7a8c6faccedac63f1f979e74db6674b4 \
  --profile pilot \
  --plan-root /project/flyspeck-candle-runs/parser-pilot-materialization-f2f50a4 \
  --result-root /project/flyspeck-candle-runs/parser-pilot-result-f2f50a4-attempt-001 \
  --candle-root /project/worktrees/candle-bootstrap-dependency-fix-v13 \
  --candle-head f2f50a44b438385031d75041c9bae35b94b01eae \
  --flyspeck-root /project/worktrees/flyspeck-v13-source \
  --flyspeck-head 1ce0353008eba83d3c76ae9a25c3c242e4802d53
```

Require `published-parser-result-pass`, top-level `parse-pass`, exactly 20
fresh attempts, and every attempt `parse-ok`.  Only then run the analogous
all-inventory command, changing profile to `all-inventory`, plan root to
`all-inventory-materialization-f2f50a4`, and result root to
`parser-all-inventory-result-f2f50a4-attempt-001`.  Apply the same substitutions
to the independent consumer and require exactly 400 fresh `parse-ok` attempts.

If either profile fails, preserve the result root and classify the complete
ordered failure set before changing code.  Any Candle commit invalidates all
three current plans and requires new materializations and result roots.

## Post-parser order

After both independent consumers pass, the strict order is linked
compatibility, diagnostic direct cutpoints d0/d1, current-binary Great-100
comparison against the accepted 130/130 reference artifact, and then the
eight cumulative direct boundaries through nonlinear/LP final assembly.  PFT
remains an independent oracle and cannot advance S2 or S3.

Before the Great-100 comparison, integrate the separately tested retry-consumer
repair recorded in `2026-09-02-s1-reference-retry-consumer.md`.  The reference
root legitimately selects one `attempt-0002` after preserving an interrupted
attempt, while the pre-repair consumers hard-code `attempt-0001`.  Keep the
current `f2f50a44...` parser gates first: a later Candle approval/consumer commit
changes the source head and therefore requires fresh link provenance and fresh
direct-source plans rather than retroactively changing these retained parser
results.
