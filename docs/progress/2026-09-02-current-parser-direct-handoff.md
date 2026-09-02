# Current parser and direct-source handoff — 2026-09-02

## Authorities and status

This handoff binds:

- Candle `cb3bbcb7127b04154536b6f8ca6e8b8498d62774` at
  `/project/worktrees/candle-runtime-pin-c2e26f43-final-v13`;
- CakeML `c2e26f43c35080d57fc18aba42d4023590b6daba` at
  `/project/worktrees/cakeml-flyspeck-runtime-stack-cold-c2e26f43c-v13`;
- HOL4 `a390cbabd3a4521bab4ee20281e3e42933a8a3ae`; and
- Flyspeck `1ce0353008eba83d3c76ae9a25c3c242e4802d53`.

The authenticated cold proof replay and attempt-003 public prelaunch gate have
passed.  Canonical bootstrap attempt 003 is active at
`/project/flyspeck-candle-runs/cakeml-canonical-bootstrap-c2e26f43-attempt-003`.
Everything below is **HOLD** until that attempt atomically publishes a valid
`bootstrap-provenance.json`.  A partial log or zero Holmake exit alone is not
authority to link or parse.

## Current source-only plans

| Plan | Root | Plan SHA-256 | Host SHA-256 |
| --- | --- | --- | --- |
| pilot 20/20 | `parser-pilot-materialization-cb3bbcb` | `77b72a8d192d310bce95a822f428706e7679f801ae1e0c5c87e20a43cdce9b93` | `699ae69e691c2f0338723f2f1c09015d091f5d8af5bca8d0ca967686232c63d6` |
| all 400/400 | `all-inventory-materialization-cb3bbcb` | `f042b108b6770f669a93da91d4a7bc6970e1e9c17919d15f759573f65102d118` | `2d0c346464e660ce9aedb93e841dc9abf952c96f52d219221b0b7126bc22382c` |

The current direct plan root is
`/project/flyspeck-candle-runs/v13-stratum-plan-cb3bbcb`; its plan SHA-256 is
`c325833e96dbb4f41fc0a3c2ba5b6512be94bf16b0b74128f5c0b1f42d179904`.
It binds the fresh overlay `v13-normalized-overlay-cb3bbcb` and generated-input
tree `v13-generated-lp-cb3bbcb`, 297 actions, 400 source nodes, 43 generated
inputs, eight cumulative boundaries, and two diagnostic cutpoints.  None of
these host plans is parser, inference, theorem, S2, or S3 evidence.

## Canonical link gate

After bootstrap publication, require all four repositories clean and exact,
then use only the ordinary two-argument same-head linker:

```sh
/project/worktrees/candle-runtime-pin-c2e26f43-final-v13/build-local-cakeml.sh \
  /project/worktrees/cakeml-flyspeck-runtime-stack-cold-c2e26f43c-v13 \
  /project/flyspeck-candle-runs/cakeml-canonical-bootstrap-c2e26f43-attempt-003/bootstrap-provenance.json

/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S \
  /project/worktrees/candle-runtime-pin-c2e26f43-final-v13/candle/cakeml_artifact_provenance.py \
  check-linked \
  --candle-root /project/worktrees/candle-runtime-pin-c2e26f43-final-v13
```

Do not use the five-argument transition linker.  Require ordinary linked
schema 6 and a clean tracked Candle tree before every retained run.

## Parser pilot and inventory

Run the pilot into a fresh result root:

```sh
/usr/bin/env -i PATH=/usr/bin:/bin LC_ALL=C \
  /usr/bin/python3 -I -S \
  /project/worktrees/candle-runtime-pin-c2e26f43-final-v13/candle/flyspeck_parser_diagnostic.py \
  run --profile pilot \
  --plan-root /project/flyspeck-candle-runs/parser-pilot-materialization-cb3bbcb \
  --candle-root /project/worktrees/candle-runtime-pin-c2e26f43-final-v13 \
  --candle-head cb3bbcb7127b04154536b6f8ca6e8b8498d62774 \
  --flyspeck-root /project/worktrees/flyspeck-v13-source \
  --flyspeck-head 1ce0353008eba83d3c76ae9a25c3c242e4802d53 \
  --output-root /project/flyspeck-candle-runs/parser-pilot-result-cb3bbcb-attempt-001 \
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
  --plan-root /project/flyspeck-candle-runs/parser-pilot-materialization-cb3bbcb \
  --result-root /project/flyspeck-candle-runs/parser-pilot-result-cb3bbcb-attempt-001 \
  --candle-root /project/worktrees/candle-runtime-pin-c2e26f43-final-v13 \
  --candle-head cb3bbcb7127b04154536b6f8ca6e8b8498d62774 \
  --flyspeck-root /project/worktrees/flyspeck-v13-source \
  --flyspeck-head 1ce0353008eba83d3c76ae9a25c3c242e4802d53
```

Require `published-parser-result-pass`, top-level `parse-pass`, exactly 20
fresh attempts, and every attempt `parse-ok`.  Only then run the analogous
all-inventory command, changing profile to `all-inventory`, plan root to
`all-inventory-materialization-cb3bbcb`, and result root to
`parser-all-inventory-result-cb3bbcb-attempt-001`.  Apply the same substitutions
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
current `cb3bbcb...` parser gates first: a later Candle approval/consumer commit
changes the source head and therefore requires fresh link provenance and fresh
direct-source plans rather than retroactively changing these retained parser
results.
