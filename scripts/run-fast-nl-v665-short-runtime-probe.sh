#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
scripts=$project/scripts
run=/project/flyspeck-candle-runs/v665-fast-nl-support-probe-dev-001
base=/project/flyspeck-candle-runs/v664-fast-nl-complete-support-closure-dev-001/postaction49
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
support=$project/tools/fast_nl_v665_support.ml
required_files=(
  "$project/tools/fast_nl_v665_verifier_data.ml"
  "$project/tools/fast_nl_v665_verifier_runtime_compat.ml"
  "$project/tools/fast_nl_v665_setup.ml"
  "$support"
)
marker=CANDLE_FLYSPECK_V665_FAST_NL_SUPPORT_CHECKPOINT_READY
maximum_seconds=3600

[[ ! -e $run ]]
[[ -x $runtime/cake ]]
[[ -f $base/CHECKPOINT-READY ]]
[[ ! -f $base/CHECKPOINT-FAILED ]]
sha256sum -c "$base/checkpoint.sha256"

preflight=$(mktemp)
cleanup() {
  rm -f "$preflight"
}
trap cleanup EXIT
"$scripts/preflight-fast-nl-v665-support.sh" >"$preflight"
grep -Fxq 'status=0' "$preflight"

started_epoch=$(date +%s)
export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_PHASE_TIMEOUT_SECONDS=$maximum_seconds
"$scripts/run-fast-nl-restored-checkpoint-phase-v1.sh" \
  "$base" "$run" "$support" "$marker" \
  development-fast-nl-v665-post-support-checkpoint-v1
finished_epoch=$(date +%s)
elapsed_seconds=$((finished_epoch - started_epoch))
[[ $elapsed_seconds -le $maximum_seconds ]]

cp "$preflight" "$run/static-preflight.receipt"
ready_marker_count=$(rg -a -Foc "$marker" "$run/runtime.log" || true)
source_error_count=$(rg -a -c \
  'ERROR:|EXCEPTION:|Parsing failed|Program exited|Fatal error|Out of memory' \
  "$run/runtime.log" || true)
[[ $ready_marker_count -eq 1 ]]
[[ $source_error_count -eq 0 ]]

input_manifest_sha256=$(
  for path in "${required_files[@]}"; do
    printf '%s\t%s\n' "$(realpath "$path")" \
      "$(sha256sum "$path" | awk '{print $1}')"
  done | sha256sum | awk '{print $1}'
)
runtime_sha256=$(sha256sum "$runtime/cake" | awk '{print $1}')
predecessor_checkpoint_sha256=$(
  sed -n 's/^checkpoint_sha256=//p' "$base/checkpoint.receipt"
)
[[ -n $predecessor_checkpoint_sha256 ]]

printf '%s\n' \
  'receipt_kind=development-fast-nl-short-runtime-probe-v1' \
  'release_evidence=false' \
  'status=0' \
  "runtime_sha256=$runtime_sha256" \
  "predecessor_checkpoint_sha256=$predecessor_checkpoint_sha256" \
  "input_manifest_sha256=$input_manifest_sha256" \
  "ready_marker_count=$ready_marker_count" \
  "source_error_count=$source_error_count" \
  'pending_source_id_count=0' \
  "elapsed_seconds=$elapsed_seconds" \
  "completed_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  >"$run/SHORT-RUNTIME-PROBE.receipt"
