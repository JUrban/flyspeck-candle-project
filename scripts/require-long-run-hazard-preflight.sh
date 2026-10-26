#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! $1 =~ ^[1-9][0-9]*$ ]]; then
  printf 'usage: %s DECLARED_MAXIMUM_SECONDS\n' "$0" >&2
  exit 2
fi

project=/project/flyspeck-candle-project
ledger=$project/docs/long-run-hazard-ledger.json
gate=$project/scripts/check-long-run-hazards.py
declared_maximum_seconds=$1
threshold_seconds=$(jq -er '.policy.long_run_threshold_seconds' "$ledger")
[[ $threshold_seconds =~ ^[1-9][0-9]*$ ]]

if (( declared_maximum_seconds <= threshold_seconds )); then
  exit 0
fi

receipt=${FAST_NL_HAZARD_PREFLIGHT_RECEIPT:-}
controller=${FAST_NL_HAZARD_CONTROLLER:-}
profile=${FAST_NL_HAZARD_PROFILE:-}
[[ -n $receipt && -f $receipt && ! -L $receipt ]]
[[ -n $controller && -f $controller && ! -L $controller ]]
[[ $profile == theorem || $profile == support-stage || $profile == kernel-build ]]

receipt=$(realpath "$receipt")
controller=$(realpath "$controller")
gate_sha256=$(sha256sum "$gate" | awk '{print $1}')
ledger_sha256=$(sha256sum "$ledger" | awk '{print $1}')
controller_sha256=$(sha256sum "$controller" | awk '{print $1}')

grep -Fxq 'receipt_kind=development-long-run-hazard-preflight-v1' "$receipt"
grep -Fxq 'release_evidence=false' "$receipt"
grep -Fxq 'status=0' "$receipt"
grep -Fxq 'scope=fast-nl-first-original-theorem' "$receipt"
grep -Fxq "profile=$profile" "$receipt"
grep -Fxq "gate_sha256=$gate_sha256" "$receipt"
grep -Fxq "ledger_sha256=$ledger_sha256" "$receipt"
grep -Fxq "controller=$controller" "$receipt"
grep -Fxq "controller_sha256=$controller_sha256" "$receipt"
grep -Fxq 'failed_check_count=0' "$receipt"
grep -Fxq 'schema_error_count=0' "$receipt"
