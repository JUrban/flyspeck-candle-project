#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
candle=${1:-"$project_root/../worktrees/candle-clean-build-v13/candle.sh"}
ocaml=${OCAML_414:-/project/repos/hol-light/_opam/bin/ocaml}
supported="$project_root/compatibility/oracles/module_selected_supported.ml"
functor="$project_root/compatibility/oracles/module_functor_application.ml"
replacement="$project_root/compatibility/oracles/module_functor_replacement.ml"
temporary=$(mktemp -d)
cleanup() {
  local status=$?
  trap - EXIT
  if [[ $status != 0 ]]; then
    for log in "$temporary"/*.log; do
      printf '%s\n' "--- $log" >&2
      tail -n 80 "$log" >&2 2>/dev/null || true
    done
  fi
  rm -rf -- "$temporary"
  exit "$status"
}
trap cleanup EXIT

"$ocaml" -noinit -noprompt <"$supported" >"$temporary/ocaml-supported.log" 2>&1
timeout 300 "$candle" <"$supported" >"$temporary/candle-supported.log" 2>&1
rg -Fq 'module_selected_supported_oracle_ok' "$temporary/ocaml-supported.log"
rg -Fq 'module_selected_supported_oracle_ok' "$temporary/candle-supported.log"
! rg -q 'EXCEPTION:|Parsing failed|ERROR:|Undefined (variable|module):' \
  "$temporary/candle-supported.log"

"$ocaml" -noinit -noprompt <"$functor" >"$temporary/ocaml-functor.log" 2>&1
timeout 300 "$candle" <"$functor" >"$temporary/candle-functor.log" 2>&1 || true
rg -Fq 'module_functor_application_ocaml_ok' "$temporary/ocaml-functor.log"
! rg -Fq 'module_functor_application_ocaml_ok' "$temporary/candle-functor.log"
rg -q 'functor|Functor|Set\.Make|Undefined module: Set|Parsing failed|ERROR:' \
  "$temporary/candle-functor.log"

"$ocaml" -noinit -noprompt <"$replacement" \
  >"$temporary/ocaml-replacement.log" 2>&1
timeout 300 "$candle" <"$replacement" \
  >"$temporary/candle-replacement.log" 2>&1
rg -Fq 'module_functor_replacement_oracle_ok' \
  "$temporary/ocaml-replacement.log"
rg -Fq 'module_functor_replacement_oracle_ok' \
  "$temporary/candle-replacement.log"
! rg -q 'EXCEPTION:|Parsing failed|ERROR:|Undefined (variable|module):' \
  "$temporary/candle-replacement.log"

printf 'PASS: selected module forms match OCaml; functor application is pinned divergent; explicit set replacement passes\n'
