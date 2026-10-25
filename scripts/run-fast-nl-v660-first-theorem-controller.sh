#!/usr/bin/env bash
set -euo pipefail

run=/project/flyspeck-candle-runs/v660-fast-nl-compiler64-artifact-auth-dev-001
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-aa7ffbc-0f9690d-bc47e65-attempt-003
receipt=$run/x64-link-v2-controller.receipt
scripts=/project/flyspeck-candle-project/scripts

[[ -f $receipt ]]
grep -Fxq 'status=0' "$receipt"
grep -Fxq 'last_phase=complete' "$receipt"
[[ -x $runtime/cake ]]

export FAST_NL_RUN_DIR=$run
export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_X64_RECEIPT=$receipt

"$scripts/build-fast-nl-poststrictbuild-checkpoint-v1.sh"
"$scripts/run-fast-nl-first-original-theorem-gate-v1.sh"
