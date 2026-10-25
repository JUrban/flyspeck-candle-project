#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-matan-v676
probe=/project/flyspeck-candle-runs/v676-fast-nl-matan-restart-probe-dev-001

exec "$project/scripts/audit-fast-nl-checkpoint-finalization-v1.py" \
  --base "$base" \
  --receipt-kind development-fast-nl-v676-matan-checkpoint-v1 \
  --driver-sha256 4df318a9f9d752c834a193b59b9581aaf26f987cb9a6e694b1d66d9e95697eb2 \
  --marker CANDLE_FLYSPECK_V676_MATAN_CHECKPOINT_READY \
  --required-log='- Finished loading candle/cv_compute_exact_interval_matan_series.ml' \
  --required-log='- Finished loading candle/cv_compute_exact_interval_matan_series_program.ml' \
  --probe "$probe" \
  --probe-marker CANDLE_FLYSPECK_V676_MATAN_RESTART_PROBE_OK
