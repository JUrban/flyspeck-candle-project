#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
candle=${1:-"$project_root/../worktrees/candle-clean-build-v13/candle.sh"}
ocaml=${OCAML_414:-/project/repos/hol-light/_opam/bin/ocaml}
oracle="$project_root/compatibility/oracles/open_local_parenthesized.ml"
general_oracle="$project_root/compatibility/oracles/open_local_parenthesized_general.ml"
temporary=$(mktemp -d)
cleanup() {
  local status=$?
  trap - EXIT
  if [[ $status != 0 ]]; then
    tail -n 100 "$temporary/candle.log" >&2 2>/dev/null || true
  fi
  rm -rf -- "$temporary"
  exit "$status"
}
trap cleanup EXIT

"$ocaml" -noinit -noprompt <"$oracle" >"$temporary/ocaml.log" 2>&1
timeout 300 "$candle" <"$oracle" >"$temporary/candle.log" 2>&1
rg -Fq 'open_local_parenthesized_oracle_ok' "$temporary/ocaml.log"
rg -Fq 'open_local_parenthesized_oracle_ok' "$temporary/candle.log"
! rg -q 'EXCEPTION:|Parsing failed|ERROR:|Undefined variable:' \
  "$temporary/candle.log"

"$ocaml" -noinit -noprompt <"$general_oracle" \
  >"$temporary/ocaml-general.log" 2>&1
set +e
timeout 300 "$candle" <"$general_oracle" \
  >"$temporary/candle-general.log" 2>&1
general_status=$?
set -e
rg -Fq 'open_local_parenthesized_general_ocaml_ok' \
  "$temporary/ocaml-general.log"
! rg -Fq 'open_local_parenthesized_general_ocaml_ok' \
  "$temporary/candle-general.log"
rg -Fq 'Undefined variable: Array.get' "$temporary/candle-general.log"
if [[ $general_status == 124 ]]; then
  printf 'FAIL: Candle timed out on the bounded general-expression oracle\n' >&2
  exit 1
fi

printf 'PASS: selected operator-reference local opens match OCaml; broader general-expression divergence remains fail-closed\n'
