#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
scripts=$project/scripts
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-direct-source-interface-v678
output=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-historical-checked-sound-v679a
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
driver=$project/tools/fast_nl_v679_historical_checked_sound_stage.ml
marker=CANDLE_FLYSPECK_V679A_HISTORICAL_CHECKED_SOUND_CHECKPOINT_READY

[[ -f $base/CHECKPOINT-READY ]]
[[ ! -f $base/CHECKPOINT-FAILED ]]
[[ ! -e $output ]]
[[ -f $driver && ! -L $driver ]]
[[ -x $runtime/cake ]]
sha256sum -c "$base/checkpoint.sha256"

stage=$($scripts/audit-fast-nl-v679-historical-checked-sound-stage.py)
grep -Fxq 'status=0' <<<"$stage"
grep -Fxq 'planned_source_count=5' <<<"$stage"

nonce=$(printf '%s\n%s\n' "$0" "$(sha256sum "$driver")" |
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
export FAST_NL_PHASE_TIMEOUT_SECONDS=1200
export FAST_NL_PHASE_DRIVER_MODE=direct

"$scripts/run-fast-nl-restored-checkpoint-phase-v1.sh" \
  "$base" "$output" "$driver" "$marker" \
  development-fast-nl-v679a-historical-checked-sound-checkpoint-v1
