#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
scripts=$project/scripts
source_configuration=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001
base=$source_configuration/postaction49-v669
output=$source_configuration/posttaylor-interval-v671
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
driver=$project/tools/fast_nl_v671_taylor_interval_stage.ml
marker=CANDLE_FLYSPECK_V671_TAYLOR_INTERVAL_CHECKPOINT_READY

[[ -f $base/CHECKPOINT-READY ]]
[[ ! -f $base/CHECKPOINT-FAILED ]]
[[ ! -e $output ]]
sha256sum -c "$base/checkpoint.sha256"

segmentation=$($scripts/audit-fast-nl-v671-support-segmentation.py)
grep -Fxq 'status=0' <<<"$segmentation"
grep -Fxq 'required_checkpoint_stage_count=2' <<<"$segmentation"
grep -Fxq 'historical_checkpoint_reusable_count=0' <<<"$segmentation"
preflight=$($scripts/preflight-fast-nl-v665-support.sh)
grep -Fxq 'status=0' <<<"$preflight"

nonce=$(printf '%s' 'fast-nl-v671-taylor-interval-stage-parser' |
  sha256sum | awk '{print $1}')
set +e
parser_result=$(sed '/^#use /d' "$driver" |
  "$runtime/cake" --candle-parser-diagnostic-v1 "$nonce" 2>&1)
parser_status=$?
set -e
[[ $parser_status -eq 0 ]]
[[ $parser_result == \
  "CANDLE_CAMLPARSER_DIAGNOSTIC_V1"$'\t'"$nonce"$'\t'"OK" ]]

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_PHASE_TIMEOUT_SECONDS=3300
export FAST_NL_PHASE_DRIVER_MODE=direct
"$scripts/run-fast-nl-restored-checkpoint-phase-v1.sh" \
  "$base" "$output" "$driver" "$marker" \
  development-fast-nl-v671-taylor-interval-checkpoint-v1
