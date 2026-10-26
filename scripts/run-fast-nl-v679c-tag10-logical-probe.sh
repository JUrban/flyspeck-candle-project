#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
base=/project/flyspeck-candle-runs/cv-historical-checked-stable-5aa38ffb-checkpoint-v1-dev-001
output=/project/flyspeck-candle-runs/v679c-fast-nl-tag10-logical-probe-dev-001
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
driver=$project/tools/fast_nl_v679c_tag10_logical_probe.ml
marker=CANDLE_FLYSPECK_V679C_TAG10_LOGICAL_PROOF_OK

preflight=$($project/scripts/audit-fast-nl-v679-tag10-candidate.py)
grep -Fxq 'status=0' <<<"$preflight"
grep -Fxq 'changed_source_count=4' <<<"$preflight"

nonce=$(printf '%s\n%s\n' "$0" "$(sha256sum "$driver")" |
  sha256sum | awk '{print $1}')
parser=$(sed '/^#use /d' "$driver" |
  "$runtime/cake" --candle-parser-diagnostic-v1 "$nonce" 2>&1)
[[ $parser == \
  "CANDLE_CAMLPARSER_DIAGNOSTIC_V1"$'\t'"$nonce"$'\t'"OK" ]]

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_INPUT_PROBE_TIMEOUT_SECONDS=600

exec "$project/scripts/run-fast-nl-restored-input-probe-v1.sh" \
  "$base" "$output" "$driver" "$marker"
