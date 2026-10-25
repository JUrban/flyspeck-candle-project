#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
scripts=$project/scripts
run=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001
output=$run/postaction49-v669
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
driver=$project/tools/fast_nl_v668_action49_overlay_partition.ml
marker='CANDLE_FLYSPECK_V668_ACTION49_CHECKPOINT_READY actions=50 passed=50 normalizations=95'
setup=$project/tools/fast_nl_v665_setup.ml
identity_extension=$project/tools/fast_nl_v665_verifier_data.ml

[[ -f $run/CHECKPOINT-READY ]]
[[ ! -f $run/CHECKPOINT-FAILED ]]
[[ ! -e $output ]]
driver_sha256=$(sha256sum "$driver" | awk '{print $1}')
grep -Fxq 'authenticated_fast_nl_source_count=283' "$run/checkpoint.receipt"
grep -Fxq \
  "$(sha256sum "$setup" | awk '{print $1}')  $setup" \
  "$run/input-files.sha256"
grep -Fxq \
  "$(sha256sum "$identity_extension" | awk '{print $1}')  $identity_extension" \
  "$run/input-files.sha256"

partition_audit=$($scripts/audit-fast-nl-v668-action-overlay-partition.py)
grep -Fxq 'status=0' <<<"$partition_audit"
grep -Fxq 'base_normalization_count=56' <<<"$partition_audit"
grep -Fxq 'verifier_normalization_count=29' <<<"$partition_audit"
grep -Fxq 'post_action_direct_normalization_count=66' <<<"$partition_audit"
grep -Fxq 'post_action_combined_normalization_count=95' <<<"$partition_audit"
grep -Fxq 'normalization_overlap_count=0' <<<"$partition_audit"
grep -Fxq 'historical_action_status=50/50' <<<"$partition_audit"
grep -Fxq "wrapper_sha256=$driver_sha256" <<<"$partition_audit"

nonce=$(printf '%s' 'fast-nl-v669-action49-overlay-transition-parser' |
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
export FAST_NL_PHASE_TIMEOUT_SECONDS=2700
export FAST_NL_PHASE_DRIVER_MODE=direct
"$scripts/run-fast-nl-restored-checkpoint-phase-v1.sh" \
  "$run" "$output" "$driver" "$marker" \
  development-fast-nl-v669-post-action49-checkpoint-v1
