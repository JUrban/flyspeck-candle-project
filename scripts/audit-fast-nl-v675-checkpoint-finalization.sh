#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-foundation-v675
probe=/project/flyspeck-candle-runs/v675-fast-nl-foundation-restart-probe-dev-001

exec "$project/scripts/audit-fast-nl-checkpoint-finalization-v1.py" \
  --base "$base" \
  --receipt-kind development-fast-nl-v675-foundation-checkpoint-v1 \
  --driver-sha256 b7dec827383704fafb4b8652c2fa4c5d1a4d96a168efa8993f05da27459de43c \
  --marker CANDLE_FLYSPECK_V675_FOUNDATION_CHECKPOINT_READY \
  --required-log='- Finished loading candle/cv_compute_polynomial_expr_dim_jet_semantics.ml' \
  --required-log='- Finished loading candle/cv_compute_exact_interval_square_core.ml' \
  --required-log='- Finished loading candle/cv_compute_exact_rational_inv.ml' \
  --probe "$probe" \
  --probe-marker CANDLE_FLYSPECK_V675_FOUNDATION_RESTART_PROBE_OK
