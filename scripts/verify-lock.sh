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
[[ "$direct_manifest_sha" == 47a0f9e1c3588f4032c02a9b9a122018a68ffef05997d858b2fd9c6c00375b75 ]]
jq -e '
  .repositories.flyspeck.commit ==
    "1ce0353008eba83d3c76ae9a25c3c242e4802d53" and
  .source_node_count == 400 and
  .source_edge_count == 706 and
  .bootstrap_roots ==
    ["candle:hol.ml", "flyspeck:text_formalization/build/strictbuild.hl"] and
  [.build_strata[].name] ==
    ["base", "arithmetic", "nonlinear_support", "analysis", "geometry",
     "lp_support", "text_formalization", "final_assembly"] and
  [.build_strata[].entry_count] == [30, 8, 12, 11, 91, 33, 106, 6] and
  [.build_strata[].start_index] == [0, 30, 38, 50, 61, 152, 185, 291] and
  [.build_strata[].end_index] == [29, 37, 49, 60, 151, 184, 290, 296] and
  (.source_node_strata | length) == 400 and
  ([.source_node_strata[] | select(length == 0)] | length) == 0 and
  (.source_node_strata["candle:candle/flyspeck_l2_target.ml"] |
    contains(["final_assembly"])) and
  .static_full_build_contract.activation_status ==
    "exact-action-and-overlay-active-pending-full-run" and
  .static_full_build_contract.generated_source ==
    "candle:candle/flyspeck_full_build.ml" and
  .static_full_build_contract.generated_source_sha256 ==
    "44ae6acc8b43e9408694f64457e0c1fe8b481865abc9afdd2921fcf981094b4a" and
  .static_full_build_contract.generated_source_md5 ==
    "fa440c6eae11574a55adab1f881fd834" and
  .static_full_build_contract.directive == "#flyspeck_needs" and
  .static_full_build_contract.entry_count == 297 and
  .static_full_build_contract.unique_target_count == 287 and
  (.static_full_build_contract.required_loader_action |
    contains("neutralize_state exactly once")) and
  (.static_full_build_contract.failure_policy |
    contains("must not be erased")) and
  (.static_full_build_contract.preload_authentication |
    contains("before strictbuild")) and
  .source_normalization_contract.activation_status ==
    "exact-overlay-selection-active-pending-full-run" and
  .source_normalization_contract.contract_sha256 ==
    "f356deaafcaf066eb8060f1475dd8a1ab51d2b500f99b2679622c03cd24682c1" and
  .source_normalization_contract.entry_count == 5 and
  ([.source_normalization_contract.entries[].operation_count] | add) == 13 and
  .source_normalization_contract.reference_implementation.commit ==
    "99cb5d93fc30f1a6f3e69f5aa5d2063994d33a93" and
  [.source_normalization_contract.entries[].id] ==
    ["PROJECT-POINTER-S3-IMMEDIATE-001",
     "PROJECT-POINTER-S3-ALLOCATED-LIB-001",
     "PROJECT-POINTER-S3-UNSUPPRESS-001",
     "PROJECT-POINTER-S3-RELABEL-001",
     "PROJECT-TOPLOOP-S3-USE-FILE-B-001"] and
  [.source_normalization_contract.entries[].source_sha256] ==
    ["8ed592aa6515b9fe76cef8f101c98953bfe53b21d0cf023ccb45aaa62f97cc3f",
     "a429247955e1e095e5663813e9609c43697d83d80f357c7855af3b76a3145865",
     "193abcdff7657f421398203c67e67d32ce5204ce4ba5a04adad53f37fd161ae6",
     "3af61cf6961097eae9b67f3f3aaeef8fbd8c9a2ec2dfef1e95594561bac58ebe",
     "c5238451804b274b8feab8ce9a60eb481a13e1015c3a3d9ad2037beba5e42c6a"] and
  [.source_normalization_contract.entries[].normalized_sha256] ==
    ["243a2031e595efa9bf0b85b552f9620f4ab45cbca8dcebef821f2eae68c3bba4",
     "d1ae25218cce2f2f510966d574d48d283c04748a1b6c8d8dfc0c2ca52438a60f",
     "cb6ab239f202554f204188a3feac089cd2cc69645088e0d95659aeabb304b6de",
     "e34517f72ed00eeb30275f1dca01210604665a43d96aa1d759c9f6890f0312e5",
     "e8678c01ebb0ddcd647b0155f05caee931be482161f1d34319c1c6cb3fdf74c3"] and
  .source_normalization_contract.selected_graph_non_use_bindings.identifiers ==
    ["qmap", "unsuppress", "use_file_b"] and
  .source_nodes["flyspeck:formal_lp/hypermap/main/prove_flyspeck_lp.hl"].execution_normalization.id ==
    "PROJECT-POINTER-S3-IMMEDIATE-001" and
  .source_nodes["flyspeck:text_formalization/general/lib.hl"].execution_normalization.id ==
    "PROJECT-POINTER-S3-ALLOCATED-LIB-001" and
  .source_nodes["flyspeck:text_formalization/general/print_types.hl"].execution_normalization.id ==
    "PROJECT-POINTER-S3-UNSUPPRESS-001" and
  .source_nodes["flyspeck:text_formalization/jordan/tactics_jordan.hl"].execution_normalization.id ==
    "PROJECT-POINTER-S3-RELABEL-001" and
  .source_nodes["flyspeck:text_formalization/build/strictbuild.hl"].execution_normalization.id ==
    "PROJECT-TOPLOOP-S3-USE-FILE-B-001" and
  ([.source_nodes[] | select(has("execution_normalization"))] | length) == 5 and
  (.source_nodes | has("flyspeck:load_flyspeck.ml") | not) and
  .source_digest_contract.activation_status ==
    "preflight-before-strictbuild" and
  .source_digest_contract.entry_count == 399 and
  .source_digest_contract.bootstrap_exclusions ==
    ["candle:candle/flyspeck_loader.ml"] and
  .source_digest_contract.generated_source ==
    "candle:candle/flyspeck_source_digests.ml" and
  .source_digest_contract.generated_source_md5 ==
    "795a2a1a28ab69e7a4ec8cf4b4d24dce" and
  .source_digest_contract.generated_source_sha256 ==
    "ec87812b2121d8a4671ce3bf2262abc7e1151d18c6a8305f66fa1a5d1451637b" and
  .source_digest_contract.gate ==
    "candle:candle/test_flyspeck_source_digests.sh" and
  (.generated_dependency_contracts | length) == 3 and
  .diagnostics.unsupported_runtime_libraries == [] and
  .diagnostics.unsupported_runtime_members == [] and
  .diagnostics.unsupported_compatibility_members == [] and
  .static_library_contract.activation_status ==
    "exact-static-link-selection-active-member-compatibility-partial" and
  .static_library_contract.activation_source ==
    "cakeml:candle/prover/candle_boot.ml" and
  .static_library_contract.activation_gate ==
    "candle:candle/test_static_load_directive.sh" and
  (.static_library_contract.directives | length) == 5 and
  (.static_library_contract.qualified_uses | length) == 39 and
  (.static_library_contract.opened_module_uses | length) == 3 and
  (.static_library_contract.capability_uses | length) == 42 and
  (.static_library_contract.module_opens | length) == 2 and
  .static_library_contract.binding_evidence["str.cma"].status ==
    "partial-pure-source-differential-gate" and
  .static_library_contract.binding_evidence["unix.cma"].status ==
    "startup-metadata-only-explicit-fail-otherwise" and
  .static_library_contract.binding_evidence["unix.cma"].source ==
    "candle:candle/ocaml.ml" and
  .static_library_contract.binding_evidence["unix.cma"].gate ==
    "candle:candle/test_unix_metadata.sh" and
  .static_library_contract.binding_evidence["unix.cma"].deterministic_process_inputs ==
    [
      {
        "bytes": 21,
        "command": "date",
        "sha256": "8f2148c336b70d69d770cd80e0f3decc5a1c9716fac2fc7961f7a5b2d57701e8",
        "source": "candle:candle/flyspeck_metadata/date.txt"
      },
      {
        "bytes": 16,
        "command": "whoami",
        "sha256": "ad29b534dd27882add87d6996aa4ccf39bf1e5b15ccfd08804636905e8b8d864",
        "source": "candle:candle/flyspeck_metadata/user.txt"
      }
    ] and
  .ocaml_compatibility_contract.activation_status ==
    "partial-source-bindings" and
  .ocaml_compatibility_contract.selected_members.Digest ==
    ["file", "string", "t", "to_hex"] and
  (.ocaml_compatibility_contract.qualified_uses | length) == 21 and
  .ocaml_compatibility_contract.module_opens == [] and
  .ocaml_compatibility_contract.opened_module_uses == [] and
  .ocaml_compatibility_contract.binding_evidence.Digest.status ==
    "pure-source-differential-gate" and
  .ocaml_compatibility_contract.binding_evidence.Digest.gate ==
    "candle:candle/test_digest_compat.sh" and
  (.ocaml_compatibility_contract.binding_evidence.Digest.assurance_limit |
    contains("not yet formally linked")) and
  .toplevel_interface_contract.activation_status ==
    "blocked-no-dummy-or-no-op" and
  ([.toplevel_interface_contract.qualified_uses[] | select(.module == "Format")] | length) == 106 and
  ([.toplevel_interface_contract.qualified_uses[] | select(.module == "Toploop")] | length) == 19 and
  ([.toplevel_interface_contract.qualified_uses[] | select(.module == "Lexing")] | length) == 5 and
  ([.toplevel_interface_contract.qualified_uses[] | select(.module == "Obj")] | length) == 3 and
  .toplevel_interface_contract.unbound_members.Format ==
    ["formatter_of_buffer", "pp_set_margin", "sprintf", "std_formatter"] and
  .toplevel_interface_contract.conditional_source_selection.pinned_ocaml_version ==
    "4.14.1" and
  .toplevel_interface_contract.conditional_source_selection.selected ==
    "flyspeck:text_formalization/general/update_database_400.ml" and
  (.toplevel_interface_contract.dynamic_source_payloads | length) == 4 and
  (.toplevel_interface_contract.consumer_inventory.reviewed_occurrences | length) == 20 and
  .toplevel_interface_contract.consumer_inventory.typed_theorem_lookup.occurrences == 23810 and
  .toplevel_interface_contract.consumer_inventory.typed_theorem_lookup.source_files == 22 and
  .loader_action_contract.activation_status ==
    "partial-exact-static-actions-active" and
  .loader_action_contract.source_site_count == 731 and
  .loader_action_contract.generated_static_root_directives == 297 and
  ([.loader_action_contract.syntax_position_counts[] |
    select(.position == "standalone-phrase") | .count] | add) == 720 and
  ([.loader_action_contract.syntax_position_counts[] |
    select(.position == "embedded-expression") | .count] | add) == 11 and
  (.loader_action_contract.required_actions.flyspeck_needs |
    contains("neutralize state exactly once")) and
  (.loader_action_contract.required_actions["#flyspeck_loadt"] |
    contains("evaluate on every occurrence")) and
  (.loader_action_contract.ordinary_directive_boundary_status |
    contains("exact phrase-start recognition"))
' "$direct_manifest" >/dev/null
direct_digest_program="$workspace_dir/worktrees/candle-loader-v13/candle/flyspeck_source_digests.ml"
direct_digest_program_sha=$(sha256sum "$direct_digest_program" | cut -d' ' -f1)
[[ "$direct_digest_program_sha" == ec87812b2121d8a4671ce3bf2262abc7e1151d18c6a8305f66fa1a5d1451637b ]]
direct_full_build="$workspace_dir/worktrees/candle-loader-v13/candle/flyspeck_full_build.ml"
direct_full_build_sha=$(sha256sum "$direct_full_build" | cut -d' ' -f1)
[[ "$direct_full_build_sha" == 44ae6acc8b43e9408694f64457e0c1fe8b481865abc9afdd2921fcf981094b4a ]]
[[ $(rg -c '^#flyspeck_needs ' "$direct_full_build") == 297 ]]
for normalization_marker in \
  'normalization=PROJECT-POINTER-S3-IMMEDIATE-001 normalized_sha256=243a2031e595efa9bf0b85b552f9620f4ab45cbca8dcebef821f2eae68c3bba4' \
  'normalization=PROJECT-POINTER-S3-ALLOCATED-LIB-001 normalized_sha256=d1ae25218cce2f2f510966d574d48d283c04748a1b6c8d8dfc0c2ca52438a60f' \
  'normalization=PROJECT-POINTER-S3-UNSUPPRESS-001 normalized_sha256=cb6ab239f202554f204188a3feac089cd2cc69645088e0d95659aeabb304b6de' \
  'normalization=PROJECT-POINTER-S3-RELABEL-001 normalized_sha256=e34517f72ed00eeb30275f1dca01210604665a43d96aa1d759c9f6890f0312e5'
do
  rg -Fq "$normalization_marker" "$direct_full_build"
done
direct_normalization_contract="$workspace_dir/worktrees/candle-loader-v13/candle/flyspeck_normalizations.json"
[[ $(sha256sum "$direct_normalization_contract" | cut -d' ' -f1) == \
  f356deaafcaf066eb8060f1475dd8a1ab51d2b500f99b2679622c03cd24682c1 ]]
direct_candle="$workspace_dir/worktrees/candle-loader-v13/candle"
(
  cd "$direct_candle"
  python3 -m unittest \
    test_flyspeck_normalize test_check_flyspeck_normalized_identity >/dev/null
)
python3 "$direct_candle/flyspeck_normalize.py" \
  --flyspeck-root "$workspace_dir/worktrees/flyspeck-v13-source" --check >/dev/null
python3 "$direct_candle/check_flyspeck_normalized_identity.py" \
  --flyspeck-root "$workspace_dir/worktrees/flyspeck-v13-source" >/dev/null
direct_boot="$direct_candle/build/candle_boot.ml"
[[ $(sha256sum "$direct_boot" | cut -d' ' -f1) == \
  c19c392bc76e969b3a34a59932f2ee67f4b781ab707b75259c57a8b551ded675 ]]
static_load_source_sha=$(sha256sum \
  "$workspace_dir/worktrees/cakeml-flyspeck-actions-v13/candle/prover/candle_boot.ml" |
  cut -d' ' -f1)
[[ "$static_load_source_sha" == \
  ec202123865b131038b7038dc2c8191f67d816146b8d063b9590f346c317b8b3 ]]
"$direct_candle/test_static_load_directive.sh" \
  "$workspace_dir/worktrees/candle-loader-v13/candle.sh" >/dev/null
CANDLE_BINARY="$workspace_dir/worktrees/candle-loader-v13/candle.sh" \
  "$direct_candle/test_flyspeck_needs_directive.sh" >/dev/null
CANDLE_BINARY="$workspace_dir/worktrees/candle-loader-v13/candle.sh" \
  "$direct_candle/test_filename_compat.sh" >/dev/null
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
check_head ocaml-4.14 99cb5d93fc30f1a6f3e69f5aa5d2063994d33a93
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
  e700e269bcd4b8266347fd4e4bb49f6a5eb7b073
check_worktree cakeml-flyspeck-actions \
  "$workspace_dir/worktrees/cakeml-flyspeck-actions-v13" \
  codex/flyspeck-v13-actions \
  14856fcfddeb3fdafdf8a1080e567a55d3102698 \
  0e749990546e2c8108851360585667a8e173f48c
check_development hol-light codex/flyspeck-pft-producer \
  433477862bb90b328a593e012e09390e99b2439b \
  a2674c3005da788bb6f1ac9046444edbc70983aa
check_development hol-light-flyspeck codex/flyspeck-pft-compat \
  d8366986e22555c4e4c8ff49667d646d15c35f14 \
  1ea3b9a8c614ffee4116789e23a6dcaa03bdc0b9
