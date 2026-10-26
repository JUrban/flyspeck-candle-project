#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-tag10-flat-input-v679l
output=/project/flyspeck-candle-runs/v680-fast-nl-tag10-hol4-data-export-dev-002
generated=/project/flyspeck-candle-runs/v680-fast-nl-tag10-hol4-data-generated-dev-002
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
driver=$project/tools/fast_nl_export_tag10_hol4_data.ml
predecessor_audit=$project/scripts/audit-fast-nl-v679l-import-prepared-input-flat.py
marker='CANDLE_FAST_NL_TAG10_HOL4_DATA_EXPORTED DEVELOPMENT_NON_RELEASE cells=16 equations='

[[ ! -e $output && ! -e $generated ]]
[[ -f $driver && ! -L $driver ]]
preflight=$($predecessor_audit)
[[ $(grep -Fxc 'status=0' <<<"$preflight") -eq 2 ]]
mkdir -p "$generated"

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_INPUT_PROBE_TIMEOUT_SECONDS=600

"$project/scripts/run-fast-nl-restored-input-probe-v1.sh" \
  "$base" "$output" "$driver" "$marker"

data=$generated/compute_registeredCase10173HistoricalChunk16DataScript.sml
[[ -s $data && ! -L $data ]]
[[ $(grep -Fc 'Num 10' "$data") -ge 3 ]]
[[ $(grep -Fc 'Num 9' "$data") -ge 1 ]]
[[ $(grep -Fc 'registered_case10173_historical_chunk16_ceqs' "$data") -ge 1 ]]
equations=$(sed -n \
  's/^.*CANDLE_FAST_NL_TAG10_HOL4_DATA_EXPORTED DEVELOPMENT_NON_RELEASE cells=16 equations=\([0-9][0-9]*\) numerical_compute=0.*$/\1/p' \
  "$output/runtime.log" | tail -1)
[[ $equations =~ ^[0-9]+$ && $equations -ge 344 ]]
sha256sum "$data" >"$generated/data.sha256"
wc -c -l "$data" >"$generated/data.size"
printf 'equations=%s\n' "$equations" >"$generated/export.receipt"
