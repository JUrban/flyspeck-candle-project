#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
workspace_dir=$(cd -- "$project_dir/.." && pwd)
repos_dir="$workspace_dir/repos"

check_head() {
  local repo=$1
  local expected=$2
  local actual
  actual=$(git -C "$repos_dir/$repo" rev-parse HEAD)
  if [[ "$actual" != "$expected" ]]; then
    printf 'mismatch: %s HEAD is %s, expected %s\n' "$repo" "$actual" "$expected" >&2
    return 1
  fi
  printf 'ok: %s %s\n' "$repo" "$actual"
}

roadmap_actual=$(sha256sum "$workspace_dir/Flyspeck_in_Candle_Gap_Analysis.docx" | cut -d' ' -f1)
roadmap_expected=713b97d2d8b873504ea428d014a142acb066ff5d27263dd5be6a9c0135444e3b
[[ "$roadmap_actual" == "$roadmap_expected" ]]
printf 'ok: roadmap %s\n' "$roadmap_actual"

check_head cakeml dcc03f2866f05b1db18b9f45c731ce45c3a3133e
check_head HOL 427496c4b6d9796b0d02167715ac7412f5f83a44
check_head flyspeck 1ce0353008eba83d3c76ae9a25c3c242e4802d53
check_head hol-light 433477862bb90b328a593e012e09390e99b2439b

printf 'note: Candle is a development branch; verify its base and branch separately.\n'
git -C "$repos_dir/candle" merge-base --is-ancestor \
  5b1888b9a0c1da7ca0ef2e80526b726f2e27df9d HEAD
git -C "$repos_dir/candle" branch --show-current | rg -x 'codex/flyspeck-pft'
printf 'ok: Candle development branch %s\n' "$(git -C "$repos_dir/candle" rev-parse HEAD)"
