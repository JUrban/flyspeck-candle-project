#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
workspace_root=$(cd -- "$project_root/.." && pwd)
candle_root="$workspace_root/worktrees/candle-loader-v13"
candle_script=${1:-"$workspace_root/worktrees/candle-clean-build-v13/candle.sh"}
manifest="$candle_root/candle/flyspeck_manifest.json"

ocaml -noinit -noprompt \
  "$project_root/compatibility/oracles/sys_chdir.ml" 2>&1 |
  rg -q 'SYS_CHDIR_REFERENCE_OK'

"$candle_root/candle/test_unix_metadata.sh" "$candle_script"

jq -e '
  .static_library_contract.binding_evidence["unix.cma"]
    .process_filesystem_route as $route |
  $route.status ==
    "selected-proof-route-static-nonuse-with-fail-closed-bindings-pending-complete-run" and
  $route.lp_mkdir_disposition.normalization ==
    "PROJECT-FFI-S3-LP-SHELL-ELIMINATION-001" and
  $route.glpk_generator_chain.reviewed_occurrence_count == 32 and
  $route.glpk_generator_chain.external_qualified_uses == [] and
  $route.glpk_generator_chain.route_root == "Lpproc.execute" and
  ($route.glpk_generator_chain.assurance_limit |
    contains("complete compiled run"))
' "$manifest" >/dev/null

printf 'PASS: selected process route is exact, fail-closed, and reference-bounded\n'
