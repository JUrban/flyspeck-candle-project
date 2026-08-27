#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 REPOS_ROOT" >&2
  exit 2
fi

project_root=$(cd "$(dirname "$0")/.." && pwd)
python3 "$project_root/scripts/validate_compatibility_ledger.py" \
  --ledger "$project_root/compatibility/ledger.json" \
  --schema "$project_root/compatibility/schema/ledger.schema.json" \
  --finding-schema "$project_root/compatibility/schema/inventory-finding.schema.json" \
  --summary-schema "$project_root/compatibility/schema/inventory-summary.schema.json" \
  --repos-root "$1" \
  --inventory-dir "$project_root/compatibility/generated" \
  --pointer-triage-schema "$project_root/compatibility/schema/pointer-triage.schema.json" \
  --ffi-triage-schema "$project_root/compatibility/schema/ffi-triage.schema.json" \
  --pointer-rules "$project_root/compatibility/pointer-triage-rules.json" \
  --ffi-review "$project_root/compatibility/ffi-review.json" \
  --pin-contract "$project_root/compatibility/inventory-pin-contract.json" \
  --pin-delta-schema "$project_root/compatibility/schema/inventory-pin-delta.schema.json"

exec python3 "$project_root/scripts/direct-compatibility-closure.py" \
  --manifest "$project_root/../worktrees/candle-loader-v13/candle/flyspeck_manifest.json" \
  --findings "$project_root/compatibility/generated/inventory-findings.jsonl" \
  --output "$project_root/compatibility/generated/direct-closure-summary.json" \
  --check
