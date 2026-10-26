#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
candidate=/project/worktrees/candle-fast-nl-historical-tag10-v1
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-direct-source-interface-v678
input=/project/flyspeck-candle-runs/v679f-fast-nl-verification-function-bind-probe-input-dev-001
output=/project/flyspeck-candle-runs/v679f-fast-nl-verification-function-bind-probe-dev-001
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
preamble=$project/tools/fast_nl_v679d_tag10_full_preamble.ml
fixture=$candidate/candle/cv_compute_analytic_expr_action296_fixture.ml
probe=$project/tools/fast_nl_v679f_verification_function_bind_probe.ml
marker=CANDLE_FLYSPECK_V679F_BIND_PROBE_COMPLETE

fragments=("$preamble" "$fixture" "$probe")

[[ -f $base/CHECKPOINT-READY && ! -f $base/CHECKPOINT-FAILED ]]
[[ ! -e $input && ! -e $output ]]
for fragment in "${fragments[@]}"; do
  [[ -f $fragment && ! -L $fragment ]]
done
sha256sum -c "$base/checkpoint.sha256"

mkdir -p "$input"
sha256sum "${fragments[@]}" >"$input/fragments.sha256"
: >"$input/driver.ml"
for fragment in "${fragments[@]}"; do
  printf '(* CANDLE_V679F_FRAGMENT_BEGIN sha256=%s file=%s *)\n' \
    "$(sha256sum "$fragment" | awk '{print $1}')" \
    "$(basename "$fragment")" >>"$input/driver.ml"
  if [[ $fragment == "$fixture" ]]; then
    sed '/^needs "candle\/cv_compute_flyspeck_direct_source_compat.ml";;$/d' \
      "$fragment" >>"$input/driver.ml"
  else
    sed '/^needs "candle\/cv_compute_analytic_expr_action296_fixture.ml";;$/d' \
      "$fragment" >>"$input/driver.ml"
  fi
  printf '(* CANDLE_V679F_FRAGMENT_END file=%s *)\n' \
    "$(basename "$fragment")" >>"$input/driver.ml"
done
sha256sum "$input/driver.ml" >"$input/driver.sha256"

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_INPUT_PROBE_TIMEOUT_SECONDS=600
"$project/scripts/run-fast-nl-restored-input-probe-v1.sh" \
  "$base" "$output" "$input/driver.ml" "$marker"
