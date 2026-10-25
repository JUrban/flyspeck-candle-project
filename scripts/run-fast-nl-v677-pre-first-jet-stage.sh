#!/usr/bin/env bash
set -euo pipefail

scripts=/project/flyspeck-candle-project/scripts
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-matan-v676
output=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-pre-first-jet-v677g
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
driver=/project/flyspeck-candle-project/tools/fast_nl_v677_pre_first_jet_checkpoint.ml
marker=CANDLE_FLYSPECK_V677_PRE_FIRST_JET_CHECKPOINT_READY

[[ -f $base/CHECKPOINT-READY ]]
[[ ! -f $base/CHECKPOINT-FAILED ]]
[[ ! -e $output ]]
[[ -f $driver ]]
[[ -x $runtime/cake ]]

"$scripts/audit-fast-nl-v677-pre-first-jet-stage.py" |
  tee /tmp/fast-nl-v677-pre-first-jet-stage-audit.txt
grep -Fxq 'status=0' /tmp/fast-nl-v677-pre-first-jet-stage-audit.txt

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_PHASE_TIMEOUT_SECONDS=1500
export FAST_NL_PHASE_DRIVER_MODE=direct

"$scripts/run-fast-nl-restored-checkpoint-phase-v1.sh" \
  "$base" "$output" "$driver" "$marker" \
  development-fast-nl-v677-pre-first-jet-checkpoint-v1
