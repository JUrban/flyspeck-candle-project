#!/usr/bin/env bash
set -euo pipefail

run=/project/flyspeck-candle-runs/v663-fast-nl-current-normalization-dev-001
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
x64_receipt=/project/flyspeck-candle-runs/v662-fast-nl-x64-cv-rep-dev-001/x64-link-v2-controller.receipt
scripts=/project/flyspeck-candle-project/scripts
setup=/project/flyspeck-candle-project/tools/fast_nl_v663_setup.ml

[[ ! -e $run ]]
grep -Fxq 'status=0' "$x64_receipt"
grep -Fxq 'last_phase=complete' "$x64_receipt"
[[ -x $runtime/cake ]]

mkdir -p "$run"
set +e
"$scripts/preflight-fast-nl-v663-normalization.sh" \
  >"$run/normalization-preflight.receipt" 2>"$run/normalization-preflight.stderr"
preflight_status=$?
set -e
printf '%s\n' "$preflight_status" >"$run/normalization-preflight.status"
[[ $preflight_status -eq 0 ]]
grep -Fxq 'status=0' "$run/normalization-preflight.receipt"
grep -Fxq 'entry_count=56' "$run/normalization-preflight.receipt"
grep -Fxq 'rewrite_count=3' "$run/normalization-preflight.receipt"
grep -Fxq 'stale_entry_count=2' "$run/normalization-preflight.receipt"
grep -Fxq 'missing_count=0' "$run/normalization-preflight.receipt"
grep -Fxq 'mismatch_count=0' "$run/normalization-preflight.receipt"

export FAST_NL_RUN_DIR=$run
export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_X64_RECEIPT=$x64_receipt
export FAST_NL_CAKE_HEAD=b3fb54e9f822fd462b929843e816d1fa1dd46cfd
export FAST_NL_SETUP=$setup
export FAST_NL_SETUP_SHA256=157355611cf40d119c8f7bc85ffd06befbdef04d5251b1f4746434359e299a16
export FAST_NL_READY_MARKER=CANDLE_FLYSPECK_V663_FAST_NL_POSTSTRICTBUILD_CHECKPOINT_READY

"$scripts/build-fast-nl-poststrictbuild-checkpoint-v1.sh"
"$scripts/run-fast-nl-first-original-theorem-gate-v1.sh"
