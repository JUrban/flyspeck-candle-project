#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/nl-case10173-registered-ledger-input-checkpoint-v2-dev-001
input=/project/flyspeck-candle-runs/v679k-fast-nl-prepared-input-flat-input-dev-001
output=/project/flyspeck-candle-runs/v679k-fast-nl-prepared-input-flat-dev-001
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
codec=$project/tools/fast_nl_registered_input_flat_codec.ml
exporter=$project/tools/fast_nl_v679k_export_prepared_input_flat.ml
marker=CANDLE_FLYSPECK_V679K_PREPARED_INPUT_FLAT_OK

[[ -f $base/CHECKPOINT-READY && ! -f $base/CHECKPOINT-FAILED ]]
[[ ! -e $input && ! -e $output ]]
[[ -f $codec && ! -L $codec && -f $exporter && ! -L $exporter ]]
grep -Fxq \
  'checkpoint_sha256=ad2f4c804a67a798df82ce999c5add60633cecca0a9c2257d82865c2359fb801' \
  "$base/checkpoint-seal.receipt"
sha256sum -c "$base/checkpoint.sha256"

mkdir -p "$input" "$output"
printf '(* codec sha256=%s *)\n' "$(sha256sum "$codec" | awk '{print $1}')" \
  >"$input/driver.ml"
sed -n '1,$p' "$codec" >>"$input/driver.ml"
printf '(* exporter sha256=%s *)\n' "$(sha256sum "$exporter" | awk '{print $1}')" \
  >>"$input/driver.ml"
sed -n '1,$p' "$exporter" >>"$input/driver.ml"
sha256sum "$codec" "$exporter" "$input/driver.ml" >"$input/fragments.sha256"
rmdir "$output"

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_INPUT_PROBE_TIMEOUT_SECONDS=900
"$project/scripts/run-fast-nl-restored-input-probe-v1.sh" \
  "$base" "$output" "$input/driver.ml" "$marker"

sha256sum \
  "$output/source-program.cvdata" \
  "$output/encoded-jobs.cvdata" \
  "$output/roots.cvdata" \
  >"$output/prepared-input-flat.sha256"
