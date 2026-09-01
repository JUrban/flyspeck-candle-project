#!/usr/bin/env bash
set -euo pipefail

if [[ $# -gt 1 ]]; then
  echo "usage: $0 [CANDLE]" >&2
  exit 2
fi

project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
workspace_root=$(cd -- "$project_root/.." && pwd)
if [[ ! -d "$workspace_root/worktrees/candle-clean-build-v13" ]]; then
  workspace_root=$(cd -- "$workspace_root/.." && pwd)
fi
candle=${1:-"$workspace_root/worktrees/candle-clean-build-v13/candle.sh"}
ocaml=${OCAML_414:-"$workspace_root/repos/hol-light/_opam/bin/ocaml"}
oracle="$project_root/compatibility/oracles/pointer_identity_shadowing.ml"
temporary=$(mktemp -d)
cleanup() {
  local status=$?
  trap - EXIT
  if [[ $status != 0 ]]; then
    for log in "$temporary"/*.log; do
      printf '%s\n' "--- $log" >&2
      tail -n 100 "$log" >&2 2>/dev/null || true
    done
  fi
  rm -rf -- "$temporary"
  exit "$status"
}
trap cleanup EXIT

"$ocaml" -noinit -noprompt <"$oracle" >"$temporary/ocaml.log" 2>&1
timeout 30 "$candle" <"$oracle" >"$temporary/candle.log" 2>&1
for log in "$temporary/ocaml.log" "$temporary/candle.log"; do
  rg -q 'pointer_identity_shadowing_oracle_ok.*true' "$log"
  ! rg -q 'EXCEPTION:|Parsing failed|ERROR:|Type mismatch|Undefined (variable|module):' \
    "$log"
done

printf 'PASS: simultaneous local (==) resolves to the theorem-like binding\n'
