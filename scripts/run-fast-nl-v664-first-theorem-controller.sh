#!/usr/bin/env bash
set -euo pipefail

run=/project/flyspeck-candle-runs/v664-fast-nl-complete-support-closure-dev-001
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
x64_receipt=/project/flyspeck-candle-runs/v662-fast-nl-x64-cv-rep-dev-001/x64-link-v2-controller.receipt
project=/project/flyspeck-candle-project
scripts=$project/scripts
setup=$project/tools/fast_nl_v664_setup.ml
extension=$project/tools/fast_nl_v664_support_identity_extension.ml

[[ ! -e $run ]]
grep -Fxq 'status=0' "$x64_receipt"
grep -Fxq 'last_phase=complete' "$x64_receipt"
[[ -x $runtime/cake ]]
[[ $(sha256sum "$setup" | awk '{print $1}') == \
  e201fed172fceaadb02e56aaeb468cc881979c67bfc98fffeec831279bb0eab2 ]]
[[ $(sha256sum "$extension" | awk '{print $1}') == \
  46f3e938cc2f975a7ba38b59b343c435d05e34146c39633d8258450591e26036 ]]

mkdir -p "$run"
set +e
"$scripts/preflight-fast-nl-v664-support-closure.sh" \
  >"$run/support-closure-preflight.receipt" \
  2>"$run/support-closure-preflight.stderr"
preflight_status=$?
set -e
printf '%s\n' "$preflight_status" >"$run/support-closure-preflight.status"
[[ $preflight_status -eq 0 ]]
grep -Fxq 'status=0' "$run/support-closure-preflight.receipt"
grep -Fxq 'support_resolved_node_count=245' \
  "$run/support-closure-preflight.receipt"
grep -Fxq 'support_resolved_edge_count=398' \
  "$run/support-closure-preflight.receipt"
grep -Fxq 'support_missing_identity_count=0' \
  "$run/support-closure-preflight.receipt"
grep -Fxq 'support_identity_extension_count=11' \
  "$run/support-closure-preflight.receipt"
grep -Fxq 'parser_status=OK' "$run/support-closure-preflight.receipt"

export FAST_NL_RUN_DIR=$run
export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_X64_RECEIPT=$x64_receipt
export FAST_NL_CAKE_HEAD=b3fb54e9f822fd462b929843e816d1fa1dd46cfd
export FAST_NL_SETUP=$setup
export FAST_NL_SETUP_SHA256=e201fed172fceaadb02e56aaeb468cc881979c67bfc98fffeec831279bb0eab2
export FAST_NL_IDENTITY_EXTENSION=$extension
export FAST_NL_IDENTITY_EXTENSION_SHA256=46f3e938cc2f975a7ba38b59b343c435d05e34146c39633d8258450591e26036
export FAST_NL_AUTHENTICATED_SOURCE_COUNT=218
export FAST_NL_READY_MARKER=CANDLE_FLYSPECK_V664_FAST_NL_POSTSTRICTBUILD_CHECKPOINT_READY
# This is an integration replay, not an open-ended debugging build.  These
# caps bound the complete run to 4h15m; measured predecessor phases were
# 47m35s and 17m14s, while v663 reached the support identity defect in 5m08s.
export FAST_NL_BASE_TIMEOUT_SECONDS=5400
export FAST_NL_ACTION49_TIMEOUT_SECONDS=2700
export FAST_NL_SUPPORT_TIMEOUT_SECONDS=7200
export FAST_NL_CALL_TIMEOUT_SECONDS=1800

"$scripts/build-fast-nl-poststrictbuild-checkpoint-v1.sh"
"$scripts/run-fast-nl-first-original-theorem-gate-v1.sh"
