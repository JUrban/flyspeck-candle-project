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

check_worktree() {
  local label=$1
  local path=$2
  local branch=$3
  local base=$4
  local expected=$5
  local actual_branch
  local actual_head
  actual_branch=$(git -C "$path" branch --show-current)
  actual_head=$(git -C "$path" rev-parse HEAD)
  [[ "$actual_branch" == "$branch" ]]
  [[ "$actual_head" == "$expected" ]]
  git -C "$path" merge-base --is-ancestor "$base" HEAD
  [[ -z $(git -C "$path" status --porcelain) ]]
  printf 'ok: %s %s at %s (base %s, clean)\n' \
    "$label" "$actual_branch" "$actual_head" "$base"
}

roadmap_v12_actual=$(
  sha256sum "$workspace_dir/Flyspeck_in_Candle_Gap_Analysis.docx" |
    cut -d' ' -f1
)
roadmap_v12_expected=713b97d2d8b873504ea428d014a142acb066ff5d27263dd5be6a9c0135444e3b
[[ "$roadmap_v12_actual" == "$roadmap_v12_expected" ]]
printf 'ok: superseded roadmap v1.2 %s\n' "$roadmap_v12_actual"

roadmap_v13_actual=$(
  sha256sum "$workspace_dir/Flyspeck_in_Candle_Gap_Analysis_v1.3.docx" |
    cut -d' ' -f1
)
roadmap_v13_expected=13fc3a6209787e9fa9c1879cb482fef6837252ec96b3ae506d312646c898863f
[[ "$roadmap_v13_actual" == "$roadmap_v13_expected" ]]
printf 'ok: governing roadmap v1.3 %s\n' "$roadmap_v13_actual"

cake_binary="$repos_dir/candle/candle/build/cake"
cake_binary_sha=$(sha256sum "$cake_binary" | cut -d' ' -f1)
[[ "$cake_binary_sha" == d361be3839f31811328d5a0da1ecea15a8a73f369c77e34a288355f16bb930d3 ]]
cake_source=$($cake_binary --version 2>&1 | sed -n 's/^CakeML: //p')
[[ "$cake_source" == 4e312c0f7e18b9c5789c8ac4e0af257bff895cf5 ]]
printf 'ok: compiled CakeML/Candle %s (source %s)\n' \
  "$cake_binary_sha" "$cake_source"

for locked_file in \
  'candle/build/cake.S:b55547fb4a7e4586a5503b7e7c2cb65fd850a82fe7ca2504d30fb31f7d350327' \
  'candle/build/basis_ffi.c:fcf6d21c3dededac23ea3f905c45223265ed75c33001fda42a5d6b361dbe8bab' \
  'candle/build/candle_boot.ml:6a4cf654617d5709ab1e0c50beccb395c17b7ffb18d13a00e40d54ceb4acc144' \
  'candle/build/config_enc_str.txt:162ea59dac4c00177530ecbdb7a5ad72a03460825c5160a8c596dd4f53a5f3cb'
do
  path=${locked_file%%:*}
  expected=${locked_file#*:}
  actual=$(sha256sum "$repos_dir/candle/$path" | cut -d' ' -f1)
  [[ "$actual" == "$expected" ]]
  printf 'ok: %s %s\n' "$path" "$actual"
done

flyspeck_leaf="$repos_dir/candle/candle/pft/tests/fixtures/flyspeck-hol-library.pft.bin"
flyspeck_leaf_sha=$(sha256sum "$flyspeck_leaf" | cut -d' ' -f1)
[[ "$flyspeck_leaf_sha" == c64751d819bffa16d4e7abe7c31bb1836ba3958dd60c5bfbe545495f99dec025 ]]
printf 'ok: Flyspeck ordinary leaf %s\n' "$flyspeck_leaf_sha"

refinement_leaf="$repos_dir/candle/candle/pft/tests/fixtures/flyspeck-refinement-leaves.pft.bin"
refinement_leaf_sha=$(sha256sum "$refinement_leaf" | cut -d' ' -f1)
[[ "$refinement_leaf_sha" == acc76842744d52667c42fd9831bb370e8a812f77668fa7a6ce5f2b6fbefef101 ]]
printf 'ok: Flyspeck refinement leaves %s\n' "$refinement_leaf_sha"

compute_fixture="$repos_dir/candle/candle/pft/tests/fixtures/compute-zero.pft.bin"
compute_fixture_sha=$(sha256sum "$compute_fixture" | cut -d' ' -f1)
[[ "$compute_fixture_sha" == 5f63f5ca8e280bf83e1c9838884130199891569b48912a85b2042a791e0b46cc ]]
compute_source_sha=$(sha256sum "$repos_dir/candle/candle/compute.ml" | cut -d' ' -f1)
[[ "$compute_source_sha" == be24fa596eb4a53986bad69c4540e845279c01d3257d487c40dc76ec5e68468c ]]
printf 'ok: source-aligned compute %s (source %s)\n' \
  "$compute_fixture_sha" "$compute_source_sha"

resume_fixture="$repos_dir/candle/candle/pft/tests/fixtures/producer-resume.pft.bin"
resume_fixture_sha=$(sha256sum "$resume_fixture" | cut -d' ' -f1)
[[ "$resume_fixture_sha" == 7a3c7cefe5649bd70ddb8fa6a8c6c18443068c9e1e522385c9dce2d767aa0dc2 ]]
[[ $(dmtcp_launch --version | sed -n '1s/.* //p') == 4.1.0 ]]
printf 'ok: restartable producer %s (DMTCP 4.1.0)\n' "$resume_fixture_sha"

direct_manifest="$workspace_dir/worktrees/candle-loader-v13/candle/flyspeck_manifest.json"
direct_manifest_sha=$(sha256sum "$direct_manifest" | cut -d' ' -f1)
[[ "$direct_manifest_sha" == 68befe85d08a470f1aa84796704f864103490773c60eb5ff7e2d63b6df418c46 ]]
printf 'ok: direct-source manifest %s\n' "$direct_manifest_sha"

certificate_inventory_sha=$(
  cd "$repos_dir/flyspeck/formal_lp/glpk/binary"
  find . -maxdepth 1 -type f \( -name 'easy*' -o -name 'hard*' \) -print0 |
    sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1
)
[[ "$certificate_inventory_sha" == f42a7a2ddf81f2cf6e217e95c9b59df49dc834ab606684f54df0d68aba5071ca ]]
archive_sha=$(sha256sum \
  "$repos_dir/flyspeck/formal_graph/archive/archive_all.ml" | cut -d' ' -f1)
[[ "$archive_sha" == 703ea865a124aa69f0ee12d94df7065bbbf5701a3085776e24632d14493474db ]]
nonlinear_prep_sha=$(sha256sum \
  "$repos_dir/flyspeck/text_formalization/nonlinear/prep.hl" | cut -d' ' -f1)
[[ "$nonlinear_prep_sha" == 3ccef1bf65b13ca02e7ab1f409ebb49c979862ed5ea6ff1d57ed1e4e4761723d ]]
nonlinear_log_sha=$(sha256sum \
  "$repos_dir/flyspeck/text_formalization/nonlinear/break_case_log.hl" |
  cut -d' ' -f1)
[[ "$nonlinear_log_sha" == 2b3c74156a5ee9a6b3b5b6905ff28a7fb21e7c50052ad37887b90b9ed3d5e499 ]]
printf 'ok: full LP/nonlinear inputs %s (archive %s)\n' \
  "$certificate_inventory_sha" "$archive_sha"

check_head cakeml dcc03f2866f05b1db18b9f45c731ce45c3a3133e
check_development candle codex/flyspeck-pft \
  5b1888b9a0c1da7ca0ef2e80526b726f2e27df9d \
  177a9c1e759355a325842650d224b56a3d4437dd
check_development HOL codex/flyspeck-pft-producer \
  427496c4b6d9796b0d02167715ac7412f5f83a44 \
  6dc37788c18e3404294bf137067046bae5904ad0
check_development flyspeck codex/candle-replay \
  1ce0353008eba83d3c76ae9a25c3c242e4802d53 \
  2ea440e9f7c55734d1e47738e44a6129ce0ecf5a
check_worktree flyspeck-direct \
  "$workspace_dir/worktrees/flyspeck-v13-source" \
  codex/flyspeck-v13-source \
  1ce0353008eba83d3c76ae9a25c3c242e4802d53 \
  1ce0353008eba83d3c76ae9a25c3c242e4802d53
check_worktree candle-loader \
  "$workspace_dir/worktrees/candle-loader-v13" \
  codex/flyspeck-v13-loader \
  bb5fb495c8e850d525f58f25a13a51ebbc974a10 \
  980f96a007c22efe0dcb76988137c2755ab57ce9
check_development hol-light codex/flyspeck-pft-producer \
  433477862bb90b328a593e012e09390e99b2439b \
  a2674c3005da788bb6f1ac9046444edbc70983aa
check_development hol-light-flyspeck codex/flyspeck-pft-compat \
  d8366986e22555c4e4c8ff49667d646d15c35f14 \
  1ea3b9a8c614ffee4116789e23a6dcaa03bdc0b9
