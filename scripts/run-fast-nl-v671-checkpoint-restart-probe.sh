#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/posttaylor-interval-v671
output=/project/flyspeck-candle-runs/v671-fast-nl-taylor-interval-restart-probe-dev-003
marker=CANDLE_FLYSPECK_V671_RESTART_PROBE_OK

exec "$project/scripts/run-fast-nl-checkpoint-restart-probe-v1.sh" \
  "$base" "$output" "$marker"
