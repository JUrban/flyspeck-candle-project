#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
runtime=${1:?usage: test-module-open-export-semantics.sh RUNTIME_ROOT_OR_CAKE}
ocaml=${OCAML_414:-/project/repos/hol-light/_opam/bin/ocaml}
open_oracle="$project_root/compatibility/oracles/module_open_export_scope.ml"
include_oracle="$project_root/compatibility/oracles/module_include_export_scope.ml"

if [[ -d $runtime ]]; then
  runtime_root=$(cd -- "$runtime" && pwd)
  cake="$runtime_root/cake"
else
  cake=$(realpath -- "$runtime")
  runtime_root=$(dirname -- "$cake")
fi
[[ -x $cake ]]

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

set +e
"$ocaml" -noinit -noprompt <"$open_oracle" \
  >"$temporary/ocaml-open.log" 2>&1
ocaml_open_status=$?
set -e
[[ $ocaml_open_status == 0 ]]
rg -Fq 'val module_open_visible_oracle : int = 7' \
  "$temporary/ocaml-open.log"
rg -Fq 'Unbound value Module_open_consumer.x' "$temporary/ocaml-open.log"

set +e
(
  cd -- "$runtime_root"
  timeout 300 env -i PATH=/usr/bin:/bin LC_ALL=C CML_HEAP_SIZE=1024 \
    "$cake" --candle <"$open_oracle"
) >"$temporary/candle-open.log" 2>&1
candle_open_status=$?
set -e
[[ $candle_open_status == 0 ]]
rg -Fq 'val Module_open_consumer.y = 7: int' \
  "$temporary/candle-open.log"
! rg -Fq 'val Module_open_consumer.x = 7: int' \
  "$temporary/candle-open.log"
rg -Fq 'val module_open_visible_oracle = 7: int' \
  "$temporary/candle-open.log"
rg -Fq 'ERROR: Undefined variable: Module_open_consumer.x' \
  "$temporary/candle-open.log"

"$ocaml" -noinit -noprompt <"$include_oracle" \
  >"$temporary/ocaml-include.log" 2>&1
rg -Fq 'val module_include_x_oracle : int = 7' \
  "$temporary/ocaml-include.log"
rg -Fq 'val module_include_y_oracle : int = 7' \
  "$temporary/ocaml-include.log"

(
  cd -- "$runtime_root"
  timeout 300 env -i PATH=/usr/bin:/bin LC_ALL=C CML_HEAP_SIZE=1024 \
    "$cake" --candle <"$include_oracle"
) >"$temporary/candle-include.log" 2>&1
rg -Fq 'val Module_include_consumer.x = 7: int' \
  "$temporary/candle-include.log"
rg -Fq 'val Module_include_consumer.y = 7: int' \
  "$temporary/candle-include.log"
rg -Fq 'val module_include_x_oracle = 7: int' \
  "$temporary/candle-include.log"
rg -Fq 'val module_include_y_oracle = 7: int' \
  "$temporary/candle-include.log"
! rg -q 'EXCEPTION:|Parsing failed|ERROR:|Undefined (variable|module):' \
  "$temporary/candle-include.log"

printf '%s\n' \
  'PASS: module open stays lexical and module include remains exporting'
