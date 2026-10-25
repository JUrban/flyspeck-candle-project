#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-matan-v676
output=/project/flyspeck-candle-runs/v676-fast-nl-matan-restart-probe-dev-001
marker=CANDLE_FLYSPECK_V676_MATAN_RESTART_PROBE_OK

exec "$project/scripts/run-fast-nl-checkpoint-restart-probe-v1.sh" \
  "$base" "$output" "$marker"
