#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/nl-case10173-registered-ledger-input-checkpoint-v2-dev-001
input=/project/flyspeck-candle-runs/v679j-fast-nl-prepared-input-chunks-input-dev-001
output=/project/flyspeck-candle-runs/v679j-fast-nl-prepared-input-chunks-dev-001
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
driver_source=$project/tools/fast_nl_v679j_export_prepared_input_chunks.ml
marker=CANDLE_FLYSPECK_V679J_PREPARED_INPUT_CHUNKS_OK

[[ -f $base/CHECKPOINT-READY && ! -f $base/CHECKPOINT-FAILED ]]
[[ ! -e $input && ! -e $output ]]
[[ -f $driver_source && ! -L $driver_source ]]
grep -Fxq \
  'checkpoint_sha256=ad2f4c804a67a798df82ce999c5add60633cecca0a9c2257d82865c2359fb801' \
  "$base/checkpoint-seal.receipt"
sha256sum -c "$base/checkpoint.sha256"

mkdir -p "$input" "$output"
cp "$driver_source" "$input/driver.ml"
sha256sum "$input/driver.ml" >"$input/driver.sha256"
rmdir "$output"

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_INPUT_PROBE_TIMEOUT_SECONDS=900
"$project/scripts/run-fast-nl-restored-input-probe-v1.sh" \
  "$base" "$output" "$input/driver.ml" "$marker"

mapfile -t terms < <(find "$output" -maxdepth 1 -type f -name '*.term' -print | sort -V)
[[ ${#terms[@]} -eq 523 ]]
sha256sum "${terms[@]}" >"$output/prepared-input-chunks.sha256"
