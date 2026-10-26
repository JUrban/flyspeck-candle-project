#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-direct-source-interface-v678
output=/project/flyspeck-candle-runs/v678-fast-nl-direct-source-interface-restart-probe-dev-001
marker=CANDLE_FLYSPECK_V678_DIRECT_SOURCE_INTERFACE_RESTART_PROBE_OK

exec "$project/scripts/run-fast-nl-checkpoint-restart-probe-v1.sh" \
  "$base" "$output" "$marker"
