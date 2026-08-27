#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
candle=${1:-"$project_root/../worktrees/candle-clean-build-v13/candle.sh"}
candle_root=$(cd -- "$(dirname -- "$candle")" && pwd)
ocaml=${OCAML_414:-/project/repos/hol-light/_opam/bin/ocaml}
oracle="$project_root/compatibility/oracles/unix_gettimeofday.ml"
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

"$ocaml" -noinit -noprompt unix.cma "$oracle" \
  >"$temporary/ocaml.log" 2>&1
rg -Fq 'UNIX_GETTIMEOFDAY_POSITIVE' "$temporary/ocaml.log"
! rg -Fq 'UNIX_GETTIMEOFDAY_ZERO' "$temporary/ocaml.log"

(
  cd -- "$candle_root"
  {
    printf '#use "candle/build/insulate.ml";;\n'
    printf '#use "candle/nums.ml";;\n'
    printf '#use "candle/pretty.ml";;\n'
    printf '#use "candle/ocaml.ml";;\n'
    printf '#use "%s";;\n' "$oracle"
  } | timeout 300 "$candle"
) >"$temporary/candle.log" 2>&1
rg -Fq 'UNIX_GETTIMEOFDAY_ZERO' "$temporary/candle.log"
! rg -Fq 'UNIX_GETTIMEOFDAY_POSITIVE' "$temporary/candle.log"
! rg -q 'EXCEPTION:|Parsing failed|ERROR:|Undefined (variable|module):' \
  "$temporary/candle.log"

printf 'PASS: OCaml wall clock is positive; selected Candle telemetry is deterministic zero\n'
