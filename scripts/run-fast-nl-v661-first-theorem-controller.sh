#!/usr/bin/env bash
set -euo pipefail

run=/project/flyspeck-candle-runs/v661-fast-nl-x64-cv-rep-dev-001
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-004
receipt=$run/x64-link-v2-controller.receipt
scripts=/project/flyspeck-candle-project/scripts

[[ -f $receipt ]]
grep -Fxq 'status=0' "$receipt"
grep -Fxq 'last_phase=complete' "$receipt"
[[ -x $runtime/cake ]]

export FAST_NL_RUN_DIR=$run
export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_X64_RECEIPT=$receipt
export FAST_NL_CAKE_HEAD=b3fb54e9f822fd462b929843e816d1fa1dd46cfd

"$scripts/build-fast-nl-poststrictbuild-checkpoint-v1.sh"
"$scripts/run-fast-nl-first-original-theorem-gate-v1.sh"
