#!/usr/bin/env bash
set -euo pipefail

scripts=/project/flyspeck-candle-project/scripts
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-fixed-outer-nonlinear-compile-sound-v677s
output=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-historical-sound-v677t
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
driver=/project/flyspeck-candle-project/tools/fast_nl_v677_historical_sound_stage.ml
marker=CANDLE_FLYSPECK_V677_HISTORICAL_SOUND_CHECKPOINT_READY

[[ -f $base/CHECKPOINT-READY ]]
[[ ! -f $base/CHECKPOINT-FAILED ]]
[[ ! -e $output ]]
[[ -f $driver ]]
[[ -x $runtime/cake ]]

"$scripts/audit-fast-nl-v677-historical-sound-stage.py" |
  tee /tmp/fast-nl-v677-historical-sound-stage-audit.txt
grep -Fxq 'status=0' /tmp/fast-nl-v677-historical-sound-stage-audit.txt

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_PHASE_TIMEOUT_SECONDS=1200
export FAST_NL_PHASE_DRIVER_MODE=direct

"$scripts/run-fast-nl-restored-checkpoint-phase-v1.sh" \
  "$base" "$output" "$driver" "$marker" \
  development-fast-nl-v677-historical-sound-checkpoint-v1
