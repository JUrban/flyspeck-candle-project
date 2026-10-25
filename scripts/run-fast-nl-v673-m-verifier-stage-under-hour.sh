#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
scripts=$project/scripts
source_configuration=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001
base=$source_configuration/posttaylor-multivariate-v672
output=$source_configuration/post-m-verifier-v673
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
driver=$project/tools/fast_nl_v673_m_verifier_stage.ml
marker=CANDLE_FLYSPECK_V673_M_VERIFIER_CHECKPOINT_READY

[[ -f $base/CHECKPOINT-READY ]]
[[ ! -f $base/CHECKPOINT-FAILED ]]
[[ ! -e $output ]]
sha256sum -c "$base/checkpoint.sha256"

finalization=$($scripts/audit-fast-nl-v672-checkpoint-finalization.py)
grep -Fxq 'status=0' <<<"$finalization"
stage=$($scripts/audit-fast-nl-v673-m-verifier-stage.py)
grep -Fxq 'status=0' <<<"$stage"
$scripts/audit-fast-nl-v670-runtime-symbol-surface.py | grep -Fxq 'status=0'
$scripts/audit-fast-nl-support-source-closure.py | grep -Fxq 'status=0'
$scripts/audit-fast-nl-support-module-closure.py | grep -Fxq 'status=0'

nonce=$(printf '%s' 'fast-nl-v673-m-verifier-stage-parser' |
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
  development-fast-nl-v673-m-verifier-checkpoint-v1
