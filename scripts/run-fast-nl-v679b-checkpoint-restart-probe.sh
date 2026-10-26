#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-historical-production-contract-v679b
output=/project/flyspeck-candle-runs/v679b-fast-nl-historical-production-contract-restart-probe-dev-001
marker=CANDLE_FLYSPECK_V679B_HISTORICAL_PRODUCTION_CONTRACT_RESTART_PROBE_OK

exec "$project/scripts/run-fast-nl-checkpoint-restart-probe-v1.sh" \
  "$base" "$output" "$marker"
