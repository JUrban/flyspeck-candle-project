#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
candidate=/project/worktrees/candle-fast-nl-historical-tag10-v1
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-direct-source-interface-v678
input=/project/flyspeck-candle-runs/v679l-fast-nl-prepared-input-flat-input-dev-001
output=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-tag10-flat-input-v679l
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
preamble=$project/tools/fast_nl_v679l_import_prepared_input_preamble.ml
codec=$project/tools/fast_nl_registered_input_flat_codec.ml
importer=$project/tools/fast_nl_v679l_import_prepared_input_flat.ml
audit=$project/scripts/audit-fast-nl-v679l-import-prepared-input-flat.py
marker='CANDLE_FLYSPECK_V679L_PREPARED_INPUT_FLAT_CHECKPOINT_READY DEVELOPMENT_NON_RELEASE cells=4173 numerical_compute=0 assumptions=0 axiom_growth=0'

sources=(
  "$candidate/candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_compute.ml"
  "$candidate/candle/cv_compute_analytic_expr_fixed_scale_historical_root_certificate_sound.ml"
  "$candidate/candle/cv_compute_analytic_expr_fixed_scale_historical_root_certificate_compute.ml"
  "$candidate/candle/cv_compute_analytic_expr_case10173_historical_dihedral_checked_compute.ml"
)
fragments=("$preamble" "${sources[@]}" "$codec" "$importer")

[[ ! -e $input && ! -e $output ]]
preflight=$($audit --preflight)
grep -Fxq 'status=0' <<<"$preflight"
grep -Fxq 'cells=4173' <<<"$preflight"
grep -Fxq 'numerical_compute=0' <<<"$preflight"

mkdir -p "$input"
sha256sum "${fragments[@]}" >"$input/fragments.sha256"

skip_needs=''
for source in "${sources[@]}"; do
  skip_needs+="candle/$(basename "$source")"$'\n'
done

: >"$input/driver.ml"
for fragment in "${fragments[@]}"; do
  printf '(* CANDLE_V679L_FRAGMENT_BEGIN sha256=%s file=%s *)\n' \
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
  printf '(* CANDLE_V679L_FRAGMENT_END file=%s *)\n' \
    "$(basename "$fragment")" >>"$input/driver.ml"
done
sha256sum "$input/driver.ml" >"$input/driver.sha256"

nonce=$(printf '%s\n%s\n' "$0" "$(sha256sum "$preamble")" |
  sha256sum | awk '{print $1}')
parser=$("$runtime/cake" --candle-parser-diagnostic-v1 "$nonce" \
  <"$preamble" 2>&1)
[[ $parser == \
  "CANDLE_CAMLPARSER_DIAGNOSTIC_V1"$'\t'"$nonce"$'\t'"OK" ]]

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_PHASE_TIMEOUT_SECONDS=1200
export FAST_NL_PHASE_DRIVER_MODE=direct

"$project/scripts/run-fast-nl-restored-checkpoint-phase-v1.sh" \
  "$base" "$output" "$input/driver.ml" "$marker" \
  development-fast-nl-v679l-tag10-flat-input-checkpoint-v1

postflight=$($audit)
grep -Fxq 'status=0' <<<"$postflight"
grep -Fxq 'cells=4173' <<<"$postflight"
grep -Fxq 'numerical_compute=0' <<<"$postflight"
