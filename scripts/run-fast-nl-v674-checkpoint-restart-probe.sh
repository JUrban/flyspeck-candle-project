#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-m-verifier-v674
output=/project/flyspeck-candle-runs/v674-fast-nl-m-verifier-restart-probe-dev-001
marker=CANDLE_FLYSPECK_V674_M_VERIFIER_RESTART_PROBE_OK

exec "$project/scripts/run-fast-nl-checkpoint-restart-probe-v1.sh" \
  "$base" "$output" "$marker"
