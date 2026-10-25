#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
scripts=$project/scripts
run=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001
output=$run/postaction49
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
driver=/project/flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001/action0-through49.ml
marker='CANDLE_FLYSPECK_V656_ACTION49_CHECKPOINT_READY actions=50 passed=50'
setup=/project/flyspeck-candle-project/tools/fast_nl_v665_setup.ml
identity_extension=/project/flyspeck-candle-project/tools/fast_nl_v665_verifier_data.ml

[[ -f $run/CHECKPOINT-READY ]]
[[ ! -f $run/CHECKPOINT-FAILED ]]
[[ ! -e $output ]]
grep -Fxq 'authenticated_fast_nl_source_count=283' "$run/checkpoint.receipt"
grep -Fxq \
  "$(sha256sum "$setup" | awk '{print $1}')  $setup" \
  "$run/input-files.sha256"
grep -Fxq \
  "$(sha256sum "$identity_extension" | awk '{print $1}')  $identity_extension" \
  "$run/input-files.sha256"

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_PHASE_TIMEOUT_SECONDS=2700
"$scripts/run-fast-nl-restored-checkpoint-phase-v1.sh" \
  "$run" "$output" "$driver" "$marker" \
  development-fast-nl-v666-post-action49-checkpoint-v1
