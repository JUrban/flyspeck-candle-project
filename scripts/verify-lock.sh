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

check_development() {
  local repo=$1
  local branch=$2
  local base=$3
  local expected=$4
  local actual_branch
  local actual_head
  actual_branch=$(git -C "$repos_dir/$repo" branch --show-current)
  actual_head=$(git -C "$repos_dir/$repo" rev-parse HEAD)
  if [[ "$actual_branch" != "$branch" ]]; then
    printf 'mismatch: %s branch is %s, expected %s\n' \
      "$repo" "$actual_branch" "$branch" >&2
    return 1
  fi
  git -C "$repos_dir/$repo" merge-base --is-ancestor "$base" HEAD
  if [[ "$actual_head" != "$expected" ]]; then
    printf 'mismatch: %s development HEAD is %s, expected checkpoint %s\n' \
      "$repo" "$actual_head" "$expected" >&2
    return 1
  fi
  printf 'ok: %s %s at %s (base %s)\n' \
    "$repo" "$actual_branch" "$actual_head" "$base"
}

roadmap_actual=$(sha256sum "$workspace_dir/Flyspeck_in_Candle_Gap_Analysis.docx" | cut -d' ' -f1)
roadmap_expected=713b97d2d8b873504ea428d014a142acb066ff5d27263dd5be6a9c0135444e3b
[[ "$roadmap_actual" == "$roadmap_expected" ]]
printf 'ok: roadmap %s\n' "$roadmap_actual"

check_head cakeml dcc03f2866f05b1db18b9f45c731ce45c3a3133e
check_development candle codex/flyspeck-pft \
  5b1888b9a0c1da7ca0ef2e80526b726f2e27df9d \
  754f727a307e9e6cdd0155ce67b9561103c3f8b4
check_development HOL codex/flyspeck-pft-producer \
  427496c4b6d9796b0d02167715ac7412f5f83a44 \
  162ebb3ba685add636f5241acf53ddc7136857ab
check_development flyspeck codex/candle-replay \
  1ce0353008eba83d3c76ae9a25c3c242e4802d53 \
  1ce0353008eba83d3c76ae9a25c3c242e4802d53
check_development hol-light codex/flyspeck-pft-producer \
  433477862bb90b328a593e012e09390e99b2439b \
  433477862bb90b328a593e012e09390e99b2439b
