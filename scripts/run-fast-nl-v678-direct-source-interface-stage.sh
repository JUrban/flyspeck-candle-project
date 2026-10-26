#!/usr/bin/env bash
set -euo pipefail

scripts=/project/flyspeck-candle-project/scripts
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-compact-support-v677x
output=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-direct-source-interface-v678
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
driver=/project/flyspeck-candle-project/tools/fast_nl_v678_direct_source_interface_stage.ml
marker=CANDLE_FLYSPECK_V678_DIRECT_SOURCE_INTERFACE_CHECKPOINT_READY

[[ -f $base/CHECKPOINT-READY ]]
[[ ! -f $base/CHECKPOINT-FAILED ]]
[[ ! -e $output ]]
[[ -f $driver ]]
[[ -x $runtime/cake ]]

"$scripts/audit-fast-nl-v678-direct-source-interface.py" |
  tee /tmp/fast-nl-v678-direct-source-interface-audit.txt
grep -Fxq 'status=0' /tmp/fast-nl-v678-direct-source-interface-audit.txt

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_PHASE_TIMEOUT_SECONDS=1200
export FAST_NL_PHASE_DRIVER_MODE=direct

"$scripts/run-fast-nl-restored-checkpoint-phase-v1.sh" \
  "$base" "$output" "$driver" "$marker" \
  development-fast-nl-v678-direct-source-interface-checkpoint-v1
