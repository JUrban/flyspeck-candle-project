#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
scripts=/project/flyspeck-candle-project/scripts
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-matan-v676
output=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-fixed-scale-v677
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
driver=/project/flyspeck-candle-project/tools/fast_nl_v677_fixed_scale_stage.ml
preflight=/project/flyspeck-candle-runs/v677-fast-nl-fixed-scale-preflight-dev-001
marker=CANDLE_FLYSPECK_V677_FIXED_SCALE_CHECKPOINT_READY

[[ -f $base/CHECKPOINT-READY ]]
[[ ! -f $base/CHECKPOINT-FAILED ]]
[[ ! -e $output ]]
[[ ! -e $preflight ]]

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_PHASE_TIMEOUT_SECONDS=3300
export FAST_NL_PHASE_DRIVER_MODE=direct

"$scripts/check-long-run-hazards.py" \
  --scope fast-nl-first-original-theorem \
  --profile support-stage \
  --controller "$0" \
  --receipt "$preflight/hazard-preflight.receipt"
grep -Fxq 'status=0' "$preflight/hazard-preflight.receipt"
grep -Fxq 'profile=support-stage' "$preflight/hazard-preflight.receipt"
export FAST_NL_HAZARD_PREFLIGHT_RECEIPT=$preflight/hazard-preflight.receipt
export FAST_NL_HAZARD_CONTROLLER=$0
export FAST_NL_HAZARD_PROFILE=support-stage

stage=$("$scripts/audit-fast-nl-v677-fixed-scale-stage.py")
grep -Fxq 'status=0' <<<"$stage"
"$scripts/audit-fast-nl-support-source-closure.py" | grep -Fxq 'status=0'
"$scripts/audit-fast-nl-support-module-closure.py" | grep -Fxq 'status=0'

"$scripts/run-fast-nl-restored-checkpoint-phase-v1.sh" \
  "$base" "$output" "$driver" "$marker" \
  development-fast-nl-v677-fixed-scale-checkpoint-v1
