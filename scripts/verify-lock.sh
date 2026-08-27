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

"$project_dir/scripts/check-compatibility-ledger.sh" "$repos_dir" >/dev/null
printf 'ok: direct compatibility ledger (6070 findings, 240 pointer reviews, 0 selected-source FFI calls)\n'

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

direct_clean_root="$workspace_dir/worktrees/candle-clean-build-v13"
direct_clean_binary="$direct_clean_root/candle/build/cake"
direct_clean_binary_sha=$(sha256sum "$direct_clean_binary" | cut -d' ' -f1)
[[ "$direct_clean_binary_sha" == \
  c20b3ec65fc01b6f50a0101c706e18271920530030aa3c381a36ff0fdbd3b23f ]]
[[ $("$direct_clean_binary" --version 2>&1 | sed -n 's/^CakeML: //p') == \
  4e312c0f7e18b9c5789c8ac4e0af257bff895cf5 ]]
for locked_file in \
  'candle/build/cake.S:b55547fb4a7e4586a5503b7e7c2cb65fd850a82fe7ca2504d30fb31f7d350327' \
  'candle/build/basis_ffi.c:04da4d58c97ad7ea649bf94c9d6f1af8313913078330442a901b501d5289c735' \
  'candle/build/candle_boot.ml:55a0e08b515a06e9b047ccedb62eb98eb4808f3b45e9c4b11e13eac7f7abba94' \
  'candle/build/config_enc_str.txt:162ea59dac4c00177530ecbdb7a5ad72a03460825c5160a8c596dd4f53a5f3cb' \
  'candle/build/cake-x64-64.tar.gz:4e074090eb04d8fdfb62536457adb31c98e1b17f6cd66c9483806601251053b7'
do
  path=${locked_file%%:*}
  expected=${locked_file#*:}
  actual=$(sha256sum "$direct_clean_root/$path" | cut -d' ' -f1)
  [[ "$actual" == "$expected" ]]
done
archive_basis_sha=$(
  tar -xOf "$direct_clean_root/candle/build/cake-x64-64.tar.gz" \
    cake-x64-64/basis_ffi.c | sha256sum | cut -d' ' -f1
)
[[ "$archive_basis_sha" == \
  04da4d58c97ad7ea649bf94c9d6f1af8313913078330442a901b501d5289c735 ]]
! rg -q 'chdir|system\(|customFFI' \
  "$direct_clean_root/candle/build/basis_ffi.c"
! nm -D "$direct_clean_binary" 2>/dev/null | \
  rg -q ' (chdir|system)(@|$)'
printf 'ok: clean no-custom-FFI direct binary %s (pristine basis %s)\n' \
  "$direct_clean_binary_sha" "$archive_basis_sha"

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
[[ "$direct_manifest_sha" == 220bd2c6ecbb4ae85a4af552ee8ccd58d4917d29c1f82b7e9491428bcc6832fc ]]
python3 "$project_dir/scripts/check-direct-dopen-corpus.py" \
  --manifest "$direct_manifest" \
  --findings "$project_dir/compatibility/generated/inventory-findings.jsonl" \
  >/dev/null
direct_closure="$project_dir/compatibility/generated/direct-closure-summary.json"
[[ $(sha256sum "$direct_closure" | cut -d' ' -f1) == \
  84a8c61c639a061f17ba73c519d20e7da91fe394dc335297fd1eaad25ae3ecfc ]]
jq -e '
  .manifest.sha256 ==
    "220bd2c6ecbb4ae85a4af552ee8ccd58d4917d29c1f82b7e9491428bcc6832fc" and
  .manifest.source_node_count == 400 and
  .manifest.normalization_source_count == 9 and
  .inventory.sha256 ==
    "4dc7dc7789334e066d12a53565c96b53ee905bc9f6868555b6c22e413aca9159" and
  .selected.finding_count == 3689 and
  .selected.source_files_with_findings == 329 and
  .selected.non_dopen_review_occurrences == 509 and
  .selected.site_sha256 ==
    "ca232c3110c20a4dda2a34c366526e66a6984b687e59547ca03ea39c22b10f42" and
  .selected.by_category["open.declaration"] == 3180 and
  .selected.by_category["open.local_let"] == 0 and
  .selected.by_category["open.local_parenthesized"] == 79 and
  .selected.local_parenthesized_body_forms == {"operator_reference": 79} and
  (.selected.local_parenthesized_operators | values | add) == 79 and
  .selected.by_category["pointer_equality.infix_use"] == 12 and
  .selected.by_category["pointer_equality.operator_binding"] == 1 and
  .selected.by_category["pointer_equality.operator_reference"] == 2 and
  .selected.by_category["ffi.custom_call"] == 0
' "$direct_closure" >/dev/null
jq -e '
  .repositories.flyspeck.commit ==
    "1ce0353008eba83d3c76ae9a25c3c242e4802d53" and
  .source_node_count == 400 and
  .source_edge_count == 706 and
  (.generated_inputs | length) == 43 and
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
  .dopen_corpus_contract.activation_status ==
    "inventory-complete-pending-verified-dopen" and
  .dopen_corpus_contract.occurrence_count == 3180 and
  .dopen_corpus_contract.source_file_count == 234 and
  .dopen_corpus_contract.module_path_count == 193 and
  .dopen_corpus_contract.path_form_counts == {"dotted": 0, "simple": 3180} and
  .dopen_corpus_contract.override_warning_suppression_count == 0 and
  .dopen_corpus_contract.site_sha256 ==
    "bce30814051df12ea23c14f2918a55e6b839b72760fd58b8996e32f1c05bf282" and
  [.dopen_corpus_contract.earliest_stratum_counts[].name] ==
    ["base", "arithmetic", "nonlinear_support", "analysis", "geometry",
     "lp_support", "text_formalization", "final_assembly"] and
  [.dopen_corpus_contract.earliest_stratum_counts[].occurrence_count] ==
    [29, 22, 13, 35, 841, 177, 2048, 15] and
  .static_full_build_contract.activation_status ==
    "exact-action-and-overlay-active-pending-full-run" and
  .static_full_build_contract.generated_source ==
    "candle:candle/flyspeck_full_build.ml" and
  .static_full_build_contract.generated_source_sha256 ==
    "e12c1af9d51a52b05193a1352e1b55d3063d1c8e65b3792d07489171a0815660" and
  .static_full_build_contract.generated_source_md5 ==
    "f2eeca4d26e3fa91309c7aff8821a83e" and
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
  (.source_normalization_contract.runtime_selection_source |
    contains("candle_boot.ml@1b17732f")) and
  .source_normalization_contract.contract_sha256 ==
    "ea38ed5b4515af81eaace1ab83859695d052f42579d8eb0c0689234fbf268067" and
  .source_normalization_contract.entry_count == 9 and
  ([.source_normalization_contract.entries[].operation_count] | add) == 19 and
  .source_normalization_contract.reference_implementation.commit ==
    "99cb5d93fc30f1a6f3e69f5aa5d2063994d33a93" and
  [.source_normalization_contract.entries[].id] ==
    ["PROJECT-POINTER-S3-IMMEDIATE-001",
     "PROJECT-POINTER-S3-ALLOCATED-LIB-001",
     "PROJECT-POINTER-S3-UNSUPPRESS-001",
     "PROJECT-POINTER-S3-RELABEL-001",
     "PROJECT-TOPLOOP-S3-USE-FILE-B-001",
     "PROJECT-PARSER-S3-LET-OR-PATTERN-001",
     "PROJECT-PARSER-S3-TRAILING-SEMI-001",
     "PROJECT-FFI-S3-LP-SHELL-ELIMINATION-001",
     "PROJECT-FFI-S3-LP-STATIC-INVENTORY-001"] and
  [.source_normalization_contract.entries[].source_sha256] ==
    ["8ed592aa6515b9fe76cef8f101c98953bfe53b21d0cf023ccb45aaa62f97cc3f",
     "a429247955e1e095e5663813e9609c43697d83d80f357c7855af3b76a3145865",
     "193abcdff7657f421398203c67e67d32ce5204ce4ba5a04adad53f37fd161ae6",
     "3af61cf6961097eae9b67f3f3aaeef8fbd8c9a2ec2dfef1e95594561bac58ebe",
     "c5238451804b274b8feab8ce9a60eb481a13e1015c3a3d9ad2037beba5e42c6a",
     "c999e6428ff402a781db826ca3b4c3e4b7ad400c9f549b6e964b4798e4981ba5",
     "b19e1e179b0863e551671688d76c24b13498965b460c0f514b9065a1bb8a8483",
     "256ad729d3e4138da4ee911d03d98ce04fac42f2df360252bf6a9c6badd52709",
     "c81f340edda820f06c3f2db753e192fdd6288abb7b3c410c1c4a97299e76df95"] and
  [.source_normalization_contract.entries[].normalized_sha256] ==
    ["243a2031e595efa9bf0b85b552f9620f4ab45cbca8dcebef821f2eae68c3bba4",
     "d1ae25218cce2f2f510966d574d48d283c04748a1b6c8d8dfc0c2ca52438a60f",
     "cb6ab239f202554f204188a3feac089cd2cc69645088e0d95659aeabb304b6de",
     "e34517f72ed00eeb30275f1dca01210604665a43d96aa1d759c9f6890f0312e5",
     "e8678c01ebb0ddcd647b0155f05caee931be482161f1d34319c1c6cb3fdf74c3",
     "1af4e5bc6e7fc7a95c3ae9d12a6a721e17575451573d595f015c1c6a2ef461d1",
     "a456dba39b239cfbe135ec10c9acfebcade7857fbfc36e1d52487f7856cfa187",
     "79ef91c2192a39566ffc9dc2b5064b6f5c04defb5db9074447f1043495b2122c",
     "f64bf35f3d1cfff43ab8117ee632e625b219390e416d31a463ad7d2fea2e55d0"] and
  (.source_normalization_contract.gates |
    contains(["candle:candle/test_flyspeck_parser_orpattern_normalization.sh"])) and
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
  .source_nodes["flyspeck:text_formalization/general/parser_verbose.hl"].execution_normalization.id ==
    "PROJECT-PARSER-S3-LET-OR-PATTERN-001" and
  .source_nodes["flyspeck:text_formalization/general/debug.hl"].execution_normalization.id ==
    "PROJECT-PARSER-S3-TRAILING-SEMI-001" and
  .source_nodes["flyspeck:formal_lp/hypermap/main/lp_certificate.hl"].execution_normalization.id ==
    "PROJECT-FFI-S3-LP-SHELL-ELIMINATION-001" and
  .source_nodes["flyspeck:formal_lp/hypermap/verify_all.hl"].execution_normalization.id ==
    "PROJECT-FFI-S3-LP-STATIC-INVENTORY-001" and
  ([.source_nodes[] | select(has("execution_normalization"))] | length) == 9 and
  .lp_archive_preparation_contract.activation_status ==
    "materializer-ready-pending-direct-runtime-leaf" and
  .lp_archive_preparation_contract.contract_sha256 ==
    "fdebe3aca0b693f367ac284c28d2b2e01f1b00b5342a4366d4cdd093016f5024" and
  .lp_archive_preparation_contract.archive.sha256 ==
    "7056e306a03d7eb02db3c0bed898f3eef6f84f06556c040ac38ba93eb0a12453" and
  .lp_archive_preparation_contract.members ==
    [{"archive_name":"hard_7.dat","bytes":119855733,
      "kind":"regular-file","mode":420,
      "output_path":"formal_lp/glpk/binary/hard_7.dat",
      "sha256":"0ca1b5b6ceba53537ac5d95ffddd883bb297e7d48c30ac241de4f3ec71ab5526"}] and
  (.lp_archive_preparation_contract.runtime_certificate_basenames | length) == 39 and
  .lp_archive_preparation_contract.runtime_certificate_basenames_sha256 ==
    "4a4f95cbb6ad331c12945097645dfaf011567ebcb2309b603887b60a12d3eeec" and
  .lp_archive_preparation_contract.policy.runtime_shell_or_extraction ==
    "forbidden" and
  ([.generated_inputs[] | select(.class == "lp-certificate-prepared")] | length) == 1 and
  .loader.configuration_bindings ==
    ["candle_hollight_root","candle_flyspeck_root",
     "candle_flyspeck_overlay_root","candle_flyspeck_generated_root",
     "candle_flyspeck_build_mode"] and
  (.source_nodes | has("flyspeck:load_flyspeck.ml") | not) and
  .source_digest_contract.activation_status ==
    "preflight-before-strictbuild" and
  .source_digest_contract.entry_count == 399 and
  .source_digest_contract.bootstrap_exclusions ==
    ["candle:candle/flyspeck_loader.ml"] and
  .source_digest_contract.generated_source ==
    "candle:candle/flyspeck_source_digests.ml" and
  .source_digest_contract.generated_source_md5 ==
    "067af2ac1c0e0757f8f29b4831a7ccba" and
  .source_digest_contract.generated_source_sha256 ==
    "52bbed3bed822f772c1718ac6ee4eb96091f58356aa2549db821d4bee4efe129" and
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
  (.ocaml_compatibility_contract.qualified_uses | length) == 23 and
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
  .loader_action_contract.static_action_source ==
    "cakeml:candle/prover/candle_boot.ml@1b17732f" and
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
[[ "$direct_digest_program_sha" == 52bbed3bed822f772c1718ac6ee4eb96091f58356aa2549db821d4bee4efe129 ]]
direct_full_build="$workspace_dir/worktrees/candle-loader-v13/candle/flyspeck_full_build.ml"
direct_full_build_sha=$(sha256sum "$direct_full_build" | cut -d' ' -f1)
[[ "$direct_full_build_sha" == e12c1af9d51a52b05193a1352e1b55d3063d1c8e65b3792d07489171a0815660 ]]
[[ $(rg -c '^#flyspeck_needs ' "$direct_full_build") == 297 ]]
for normalization_marker in \
  'normalization=PROJECT-POINTER-S3-IMMEDIATE-001 normalized_sha256=243a2031e595efa9bf0b85b552f9620f4ab45cbca8dcebef821f2eae68c3bba4' \
  'normalization=PROJECT-POINTER-S3-ALLOCATED-LIB-001 normalized_sha256=d1ae25218cce2f2f510966d574d48d283c04748a1b6c8d8dfc0c2ca52438a60f' \
  'normalization=PROJECT-POINTER-S3-UNSUPPRESS-001 normalized_sha256=cb6ab239f202554f204188a3feac089cd2cc69645088e0d95659aeabb304b6de' \
  'normalization=PROJECT-POINTER-S3-RELABEL-001 normalized_sha256=e34517f72ed00eeb30275f1dca01210604665a43d96aa1d759c9f6890f0312e5' \
  'normalization=PROJECT-FFI-S3-LP-SHELL-ELIMINATION-001 normalized_sha256=79ef91c2192a39566ffc9dc2b5064b6f5c04defb5db9074447f1043495b2122c' \
  'normalization=PROJECT-FFI-S3-LP-STATIC-INVENTORY-001 normalized_sha256=f64bf35f3d1cfff43ab8117ee632e625b219390e416d31a463ad7d2fea2e55d0'
do
  rg -Fq "$normalization_marker" "$direct_full_build"
done
direct_normalization_contract="$workspace_dir/worktrees/candle-loader-v13/candle/flyspeck_normalizations.json"
[[ $(sha256sum "$direct_normalization_contract" | cut -d' ' -f1) == \
  ea38ed5b4515af81eaace1ab83859695d052f42579d8eb0c0689234fbf268067 ]]
direct_candle="$workspace_dir/worktrees/candle-loader-v13/candle"
(
  cd "$direct_candle"
  python3 -m unittest \
    test_flyspeck_normalize test_check_flyspeck_normalized_identity \
    test_flyspeck_prepare_inputs test_flyspeck_manifest >/dev/null
)
python3 "$direct_candle/flyspeck_normalize.py" \
  --flyspeck-root "$workspace_dir/worktrees/flyspeck-v13-source" --check >/dev/null
python3 "$direct_candle/check_flyspeck_normalized_identity.py" \
  --flyspeck-root "$workspace_dir/worktrees/flyspeck-v13-source" >/dev/null
direct_overlay="$workspace_dir/flyspeck-candle-runs/v13-normalized-overlay-ea38ed5b4515af81"
[[ $(sha256sum "$direct_overlay/flyspeck_normalization_receipt.json" | \
  cut -d' ' -f1) == \
  6558c61c8ff707ef0cf24eb1a526daaf5883b2abb51967119178d006fbf2e61c ]]
[[ $(jq '.entries | length' \
  "$direct_overlay/flyspeck_normalization_receipt.json") == 9 ]]
python3 "$direct_candle/flyspeck_prepare_inputs.py" \
  --flyspeck-root "$workspace_dir/worktrees/flyspeck-v13-source" --check >/dev/null
lp_generated_root="$workspace_dir/flyspeck-candle-runs/v13-generated-lp-0ca1b5b6"
[[ $(sha256sum \
  "$lp_generated_root/formal_lp/glpk/binary/hard_7.dat" | cut -d' ' -f1) == \
  0ca1b5b6ceba53537ac5d95ffddd883bb297e7d48c30ac241de4f3ec71ab5526 ]]
[[ $(sha256sum "$lp_generated_root/flyspeck_lp_archive_receipt.json" | \
  cut -d' ' -f1) == \
  77d099cb5035c20645f83f5ab5e19abd77b28eb2b32292e8f3314d4867366841 ]]
direct_boot="$direct_candle/build/candle_boot.ml"
[[ $(sha256sum "$direct_boot" | cut -d' ' -f1) == \
  55a0e08b515a06e9b047ccedb62eb98eb4808f3b45e9c4b11e13eac7f7abba94 ]]
static_load_source_sha=$(sha256sum \
  "$workspace_dir/worktrees/cakeml-flyspeck-actions-v13/candle/prover/candle_boot.ml" |
  cut -d' ' -f1)
[[ "$static_load_source_sha" == \
  55a0e08b515a06e9b047ccedb62eb98eb4808f3b45e9c4b11e13eac7f7abba94 ]]
[[ $(wc -c <"$direct_boot") == 38504 ]]
cmp \
  "$workspace_dir/worktrees/cakeml-flyspeck-actions-v13/candle/prover/candle_boot.ml" \
  "$direct_boot"
[[ $(readlink "$workspace_dir/worktrees/candle-loader-v13/candle_boot.ml") == \
  candle/build/candle_boot.ml ]]
[[ $(readlink "$workspace_dir/worktrees/candle-loader-v13/config_enc_str.txt") == \
  candle/build/config_enc_str.txt ]]
! rg -q '(^|[^A-Za-z0-9_.])(Cake\.)?Runtime\.customFFI' \
  "$workspace_dir/worktrees/candle-loader-v13" -g '*.ml' -g '*.hl'
! rg -q '(^|[^A-Za-z0-9_.])(Cake\.)?Runtime\.customFFI' \
  "$workspace_dir/worktrees/cakeml-flyspeck-actions-v13/candle/prover/candle_boot.ml" \
  "$direct_clean_root/candle/build/candle_boot.ml"
! rg -q 'basis_ffi\.c\.patch|chdir_to_root\.ml' \
  "$workspace_dir/worktrees/candle-loader-v13/build-instructions.sh"
direct_clean_candle="$direct_clean_root/candle.sh"
"$direct_candle/test_static_load_directive.sh" "$direct_clean_candle" >/dev/null
CANDLE_BINARY="$direct_clean_candle" \
  "$direct_candle/test_flyspeck_needs_directive.sh" >/dev/null
CANDLE_BINARY="$direct_clean_candle" \
  "$direct_candle/test_filename_compat.sh" >/dev/null
"$direct_candle/test_flyspeck_parser_orpattern_normalization.sh" \
  "$direct_clean_candle" >/dev/null
"$direct_candle/test_unix_metadata.sh" "$direct_clean_candle" >/dev/null
"$project_dir/scripts/test-local-open-compatibility.sh" \
  "$direct_clean_candle" >/dev/null
# The older seven-overlay frontier log remains immutable historical evidence.
direct_frontier_log="$workspace_dir/flyspeck-candle-runs/v13-direct-overlay-frontier-dopen-2.log"
[[ $(sha256sum "$direct_frontier_log" | cut -d' ' -f1) == \
  cc75153644c72a85bd0ee6acb88e66288e903f08a5aa3cd28f462d29d4b3b5c7 ]]
shell_free_frontier_log="$workspace_dir/flyspeck-candle-runs/v13-direct-overlay-frontier-shell-free.log"
[[ $(sha256sum "$shell_free_frontier_log" | cut -d' ' -f1) == \
  69fd5740657dcd06f0639a93f4f5802848a0ab4432e1e320a15c1d8d7414dc03 ]]
rg -Fq 'val candle_flyspeck_lp_certificate_files = [' \
  "$shell_free_frontier_log"
rg -Fq -- '- Flyspeck source action complete: general/parser_verbose.hl' \
  "$shell_free_frontier_log"
rg -Fq 'open-declarations are not supported (yet)' "$shell_free_frontier_log"
rg -Fq 'Parsing failed at line 16' "$shell_free_frontier_log"
! rg -q 'CANDLE_FLYSPECK_DIRECT_FULL_OK|Flyspeck source action complete: general/debug.hl' \
  "$shell_free_frontier_log"
clean_noffi_frontier_log="$workspace_dir/flyspeck-candle-runs/v13-direct-clean-noffi-frontier.log"
[[ $(sha256sum "$clean_noffi_frontier_log" | cut -d' ' -f1) == \
  ffa64df26d4fbf015d67dc189fb8b8f509686c364a26d5c9b6e0cf8bb0eb8d3b ]]
rg -Fq 'val candle_flyspeck_lp_certificate_files = [' \
  "$clean_noffi_frontier_log"
rg -Fq -- '- Flyspeck source action complete: general/parser_verbose.hl' \
  "$clean_noffi_frontier_log"
rg -Fq 'open-declarations are not supported (yet)' "$clean_noffi_frontier_log"
rg -Fq 'Parsing failed at line 16' "$clean_noffi_frontier_log"
! rg -q 'CANDLE_FLYSPECK_DIRECT_FULL_OK|Flyspeck source action complete: general/debug.hl' \
  "$clean_noffi_frontier_log"
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
  a08e551a4398907776112eb72db1573f65cf2012
check_worktree candle-clean-build \
  "$workspace_dir/worktrees/candle-clean-build-v13" \
  codex/flyspeck-v13-clean-build \
  bb5fb495c8e850d525f58f25a13a51ebbc974a10 \
  a08e551a4398907776112eb72db1573f65cf2012
check_worktree cakeml-flyspeck-actions \
  "$workspace_dir/worktrees/cakeml-flyspeck-actions-v13" \
  codex/flyspeck-v13-actions \
  14856fcfddeb3fdafdf8a1080e567a55d3102698 \
  1b17732f902fde2efd985905d277a972da73ae0f
check_development hol-light codex/flyspeck-pft-producer \
  433477862bb90b328a593e012e09390e99b2439b \
  a2674c3005da788bb6f1ac9046444edbc70983aa
check_development hol-light-flyspeck codex/flyspeck-pft-compat \
  d8366986e22555c4e4c8ff49667d646d15c35f14 \
  1ea3b9a8c614ffee4116789e23a6dcaa03bdc0b9
