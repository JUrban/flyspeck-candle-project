#!/usr/bin/env bash
set -euo pipefail

run=${FAST_NL_RUN_DIR:-/project/flyspeck-candle-runs/v658-fast-nl-compiler64-final-stage-dev-001}
fixture=/project/flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001
scripts=/project/flyspeck-candle-project/scripts
action49_timeout_seconds=${FAST_NL_ACTION49_TIMEOUT_SECONDS:-21600}
support_timeout_seconds=${FAST_NL_SUPPORT_TIMEOUT_SECONDS:-21600}

[[ $action49_timeout_seconds =~ ^[1-9][0-9]*$ ]]
[[ $support_timeout_seconds =~ ^[1-9][0-9]*$ ]]

[[ $(sha256sum "$fixture/action0-through49.ml" | awk '{print $1}') == \
   0174c32fd75dd9db8027c9dddfef46cd6a98afd58c4f48345203800158ab03ce ]]
[[ $(sha256sum "$fixture/support.ml" | awk '{print $1}') == \
   c1933e76dab724e7ea85199e306c4cf91d5f2a4dafbc246d0b469f17493c9d9b ]]
[[ $(sha256sum "$fixture/exact-one-call.ml" | awk '{print $1}') == \
   e2129e131a7ce4df7f1d5792f4799c98f111a6ecf54dfab181ba95a8455e8cd8 ]]

FAST_NL_PHASE_TIMEOUT_SECONDS=$action49_timeout_seconds \
  "$scripts/run-fast-nl-restored-checkpoint-phase-v1.sh" \
  "$run" "$run/postaction49" "$fixture/action0-through49.ml" \
  'CANDLE_FLYSPECK_V656_ACTION49_CHECKPOINT_READY actions=50 passed=50' \
  development-fast-nl-post-action49-checkpoint-v1

FAST_NL_PHASE_TIMEOUT_SECONDS=$support_timeout_seconds \
  "$scripts/run-fast-nl-restored-checkpoint-phase-v1.sh" \
  "$run/postaction49" "$run/postsupport" "$fixture/support.ml" \
  CANDLE_FLYSPECK_V656_FAST_NL_SUPPORT_CHECKPOINT_READY \
  development-fast-nl-post-support-checkpoint-v1

"$scripts/run-fast-nl-exact-one-call-v1.sh" theorem
"$scripts/run-fast-nl-exact-one-call-v1.sh" theorem-repeat

first_result=$(rg -a -F \
  'CANDLE_CV_CASE10173_HISTORICAL_REGISTERED_FULL_CALL_ORIGINAL_PROVE_TEST_OK' \
  "$run/theorem/runtime.log" | tail -1)
repeat_result=$(rg -a -F \
  'CANDLE_CV_CASE10173_HISTORICAL_REGISTERED_FULL_CALL_ORIGINAL_PROVE_TEST_OK' \
  "$run/theorem-repeat/runtime.log" | tail -1)
first_digest=$(printf '%s\n' "$first_result" |
  rg -o 'theorem_digest=[0-9a-f]+')
repeat_digest=$(printf '%s\n' "$repeat_result" |
  rg -o 'theorem_digest=[0-9a-f]+')
first_call_digest=$(printf '%s\n' "$first_result" |
  rg -o 'call_digest=[0-9a-f]+')
repeat_call_digest=$(printf '%s\n' "$repeat_result" |
  rg -o 'call_digest=[0-9a-f]+')

[[ $first_digest == 'theorem_digest=48c97d39af116042909b7896d0d83123' ]]
[[ $repeat_digest == "$first_digest" ]]
[[ -n $first_call_digest ]]
[[ $repeat_call_digest == "$first_call_digest" ]]
[[ $first_result == *'cells=4173 chunks=1 equations=344 assumptions=0 axiom_growth=0'* ]]
[[ $repeat_result == *'cells=4173 chunks=1 equations=344 assumptions=0 axiom_growth=0'* ]]
grep -Fxq 'fast_timing_ok=1' "$run/theorem/result-validation.txt"
grep -Fxq 'fast_timing_ok=1' "$run/theorem-repeat/result-validation.txt"

{
  printf 'receipt_kind=development-first-fast-original-nl-theorem-v1\n'
  printf 'release_evidence=false\n'
  printf 'status=0\n'
  printf 'original_theorems_proved=1\n'
  printf 'cells=4173\n'
  printf 'equations=344\n'
  printf 'assumptions=0\n'
  printf 'axiom_growth=0\n'
  printf '%s\n' "$first_digest"
  printf '%s\n' "$first_call_digest"
  printf 'first_numerical_seconds=%s\n' \
    "$(sed -n 's/^numerical_seconds=//p' "$run/theorem/result-validation.txt")"
  printf 'repeat_numerical_seconds=%s\n' \
    "$(sed -n 's/^numerical_seconds=//p' "$run/theorem-repeat/result-validation.txt")"
  printf 'completed_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >"$run/FIRST-FAST-ORIGINAL-THEOREM-REPRODUCED.receipt"
touch "$run/FIRST-FAST-ORIGINAL-THEOREM-REPRODUCED"
