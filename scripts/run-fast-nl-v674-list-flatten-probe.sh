#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/posttaylor-multivariate-v672
output=/project/flyspeck-candle-runs/v674-fast-nl-list-flatten-probe-dev-001
driver=$project/tools/fast_nl_v674_list_flatten_probe.ml
marker=CANDLE_FLYSPECK_V674_LIST_FLATTEN_PROBE_OK

exec "$project/scripts/run-fast-nl-restored-input-probe-v1.sh" \
  "$base" "$output" "$driver" "$marker"
