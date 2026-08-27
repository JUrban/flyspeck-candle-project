#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 REPOS_ROOT" >&2
  exit 2
fi

project_root=$(cd "$(dirname "$0")/.." && pwd)
python3 "$project_root/scripts/inventory_compatibility.py" \
  --scope "$project_root/compatibility/inventory-scope.toml" \
  --repos-root "$1" \
  --output-dir "$project_root/compatibility/generated"
python3 "$project_root/scripts/triage_compatibility.py" \
  --findings "$project_root/compatibility/generated/inventory-findings.jsonl" \
  --pointer-rules "$project_root/compatibility/pointer-triage-rules.json" \
  --ffi-review "$project_root/compatibility/ffi-review.json" \
  --output-dir "$project_root/compatibility/generated"
exec python3 "$project_root/scripts/compare-compatibility-inventory-pins.py" \
  --project-root "$project_root" \
  --repos-root "$1" \
  --inventory-dir "$project_root/compatibility/generated" \
  --contract "$project_root/compatibility/inventory-pin-contract.json" \
  --output "$project_root/compatibility/generated/inventory-pin-delta.json"
