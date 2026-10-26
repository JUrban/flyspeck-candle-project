#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
candidate=/project/worktrees/candle-fast-nl-historical-tag10-v1
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-direct-source-interface-v678
input=/project/flyspeck-candle-runs/v679f-fast-nl-registered-input-preparation-probe-input-dev-001
output=/project/flyspeck-candle-runs/v679f-fast-nl-registered-input-preparation-probe-dev-001
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
preamble=$project/tools/fast_nl_v679d_tag10_full_preamble.ml
runtime_compat=$project/tools/fast_nl_v679f_direct_verifier_runtime_compat.ml
verifier_compat=/project/flyspeck-candle-runs/v455-direct-verifier-mk-funs-overlay-dev-001/flyspeck/formal_ineqs/verifier/m_verifier_main.hl
program_compute=$candidate/candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_compute.ml
root_sound=$candidate/candle/cv_compute_analytic_expr_fixed_scale_historical_root_certificate_sound.ml
root_compute=$candidate/candle/cv_compute_analytic_expr_fixed_scale_historical_root_certificate_compute.ml
checked_compute=$candidate/candle/cv_compute_analytic_expr_case10173_historical_dihedral_checked_compute.ml
registered_input=$candidate/candle/benchmark_cv_compute_analytic_expr_case10173_historical_registered_input.ml
postcheck=$project/tools/fast_nl_v679f_registered_input_postcheck.ml
marker=CANDLE_FLYSPECK_V679F_REGISTERED_INPUT_PREPARATION_OK

fragments=(
  "$preamble"
  "$runtime_compat"
  "$verifier_compat"
  "$program_compute"
  "$root_sound"
  "$root_compute"
  "$checked_compute"
  "$registered_input"
  "$postcheck"
)

[[ -f $base/CHECKPOINT-READY && ! -f $base/CHECKPOINT-FAILED ]]
[[ ! -e $input && ! -e $output ]]
for fragment in "${fragments[@]}"; do
  [[ -f $fragment && ! -L $fragment ]]
done
[[ $(sha256sum "$verifier_compat" | awk '{print $1}') == \
   19b069069caa6dd3d49cf84a3699588dd76ab77fc3b16c394cf50209dfa74706 ]]
sha256sum -c "$base/checkpoint.sha256"

mkdir -p "$input"
sha256sum "${fragments[@]}" >"$input/fragments.sha256"
skip_needs=''
for fragment in "${fragments[@]}"; do
  if [[ $(basename "$(dirname "$fragment")") == candle ]]; then
    skip_needs+="candle/$(basename "$fragment")"$'\n'
  fi
done

: >"$input/driver.ml"
for fragment in "${fragments[@]}"; do
  printf '(* CANDLE_V679F_FRAGMENT_BEGIN sha256=%s file=%s *)\n' \
    "$(sha256sum "$fragment" | awk '{print $1}')" \
    "$(basename "$fragment")" >>"$input/driver.ml"
  awk -v skip_needs="$skip_needs" -v strip_all="$([[ $fragment == "$verifier_compat" ]] && printf 1 || printf 0)" '
    BEGIN {
      count = split(skip_needs, paths, "\n")
      for (i = 1; i <= count; i++) if (paths[i] != "") skip[paths[i]] = 1
    }
    {
      candidate = $0
      if (candidate ~ /^needs "[^"]+";;$/) {
        if (strip_all == "1") next
        sub(/^needs "/, "", candidate)
        sub(/";;$/, "", candidate)
        if (candidate in skip) next
      }
      print
    }
  ' "$fragment" >>"$input/driver.ml"
  printf '(* CANDLE_V679F_FRAGMENT_END file=%s *)\n' \
    "$(basename "$fragment")" >>"$input/driver.ml"
done
sha256sum "$input/driver.ml" >"$input/driver.sha256"

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_INPUT_PROBE_TIMEOUT_SECONDS=900
"$project/scripts/run-fast-nl-restored-input-probe-v1.sh" \
  "$base" "$output" "$input/driver.ml" "$marker"

runtime_log_sha256=$(sha256sum "$output/runtime.log" | awk '{print $1}')
elapsed_seconds=$(sed -n 's/^elapsed_seconds=//p' "$output/input-probe.receipt")
printf '%s\n' \
  'status=0' \
  'release_evidence=false' \
  'cells=4173' \
  'numerical_compute=0' \
  "elapsed_seconds=$elapsed_seconds" \
  "runtime_log_sha256=$runtime_log_sha256" \
  >"$output/preparation-probe.receipt"

"$project/scripts/audit-fast-nl-v679f-registered-input-preparation.py"
