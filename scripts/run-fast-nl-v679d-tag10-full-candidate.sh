#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
candidate=/project/worktrees/candle-fast-nl-historical-tag10-v1
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-direct-source-interface-v678
input=/project/flyspeck-candle-runs/v679d-fast-nl-tag10-full-input-v2-dev-001
output=/project/flyspeck-candle-runs/v679d-fast-nl-tag10-full-candidate-v2-dev-001
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
preamble=$project/tools/fast_nl_v679d_tag10_full_preamble.ml
batch=$project/tools/fast_nl_v679d_tag10_full_batch.ml
postcheck=$project/tools/fast_nl_v679d_tag10_full_postcheck.ml
marker=CANDLE_FLYSPECK_V679D_TAG10_FULL_CANDIDATE_OK

fragments=(
  "$preamble"
  "$candidate/candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_compute.ml"
  "$candidate/candle/cv_compute_analytic_expr_fixed_scale_historical_root_certificate_sound.ml"
  "$candidate/candle/cv_compute_analytic_expr_fixed_scale_historical_root_certificate_compute.ml"
  "$candidate/candle/cv_compute_analytic_expr_case10173_historical_dihedral_checked_compute.ml"
  "$candidate/candle/benchmark_cv_compute_analytic_expr_case10173_historical_registered_input.ml"
  "$batch"
  "$candidate/candle/cv_compute_analytic_expr_case10173_historical_dihedral_checked_sound.ml"
  "$candidate/candle/cv_compute_analytic_expr_case10173_historical_dihedral_item_sound.ml"
  "$candidate/candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_logical_sound.ml"
  "$candidate/candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_sound.ml"
  "$candidate/candle/cv_compute_analytic_expr_case10173_historical_dihedral_item_invariant.ml"
  "$candidate/candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_analytic_sound.ml"
  "$candidate/candle/cv_compute_analytic_expr_fixed_scale_historical_dihedral_first_order_reference_sound.ml"
  "$candidate/candle/cv_compute_analytic_expr_case10173_historical_dihedral_production_contract_sound.ml"
  "$postcheck"
)

[[ -f $base/CHECKPOINT-READY && ! -f $base/CHECKPOINT-FAILED ]]
[[ ! -e $input && ! -e $output ]]
[[ -x $runtime/cake ]]
for fragment in "${fragments[@]}"; do
  [[ -f $fragment && ! -L $fragment ]]
done
sha256sum -c "$base/checkpoint.sha256"

preflight=$($project/scripts/audit-fast-nl-v679d-tag10-full-candidate.py --preflight)
grep -Fxq 'status=0' <<<"$preflight"
grep -Fxq 'planned_fragment_count=16' <<<"$preflight"

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
  printf '(* CANDLE_V679D_FRAGMENT_BEGIN sha256=%s file=%s *)\n' \
    "$(sha256sum "$fragment" | awk '{print $1}')" \
    "$(basename "$fragment")" >>"$input/driver.ml"
  awk -v skip_needs="$skip_needs" '
    BEGIN {
      count = split(skip_needs, paths, "\n")
      for (i = 1; i <= count; i++) if (paths[i] != "") skip[paths[i]] = 1
    }
    {
      candidate = $0
      if (candidate ~ /^needs "[^"]+";;$/) {
        sub(/^needs "/, "", candidate)
        sub(/";;$/, "", candidate)
        if (candidate in skip) next
      }
      print
    }
  ' "$fragment" >>"$input/driver.ml"
  printf '(* CANDLE_V679D_FRAGMENT_END file=%s *)\n' \
    "$(basename "$fragment")" >>"$input/driver.ml"
done
sha256sum "$input/driver.ml" >"$input/driver.sha256"

for parse_source in "$preamble" "$postcheck"; do
  nonce=$(printf '%s\n%s\n' "$0" "$(sha256sum "$parse_source")" |
    sha256sum | awk '{print $1}')
  parser=$("$runtime/cake" --candle-parser-diagnostic-v1 "$nonce" \
    <"$parse_source" 2>&1)
  [[ $parser == \
    "CANDLE_CAMLPARSER_DIAGNOSTIC_V1"$'\t'"$nonce"$'\t'"OK" ]]
done

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_INPUT_PROBE_TIMEOUT_SECONDS=1200

"$project/scripts/run-fast-nl-restored-input-probe-v1.sh" \
  "$base" "$output" "$input/driver.ml" "$marker"

postflight=$($project/scripts/audit-fast-nl-v679d-tag10-full-candidate.py)
grep -Fxq 'status=0' <<<"$postflight"
grep -Fxq 'full_batch_cells=4173' <<<"$postflight"
