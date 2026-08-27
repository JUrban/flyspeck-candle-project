#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 REPOS_ROOT" >&2
  exit 2
fi

project_root=$(cd "$(dirname "$0")/.." && pwd)
exec python3 "$project_root/scripts/inventory_compatibility.py" \
  --scope "$project_root/compatibility/inventory-scope.toml" \
  --repos-root "$1" \
  --output-dir "$project_root/compatibility/generated"
