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
printf 'ok: direct compatibility ledger (6074 findings, 240 pointer reviews, 0 selected-source FFI calls)\n'

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
[[ "$direct_manifest_sha" == ea7a3e50fa1063d3b2ea82dd288c5a17adcb5d067a4c13089ea961ec47108eaf ]]
python3 "$project_dir/scripts/check-direct-dopen-corpus.py" \
  --manifest "$direct_manifest" \
  --findings "$project_dir/compatibility/generated/inventory-findings.jsonl" \
  >/dev/null
direct_closure="$project_dir/compatibility/generated/direct-closure-summary.json"
[[ $(sha256sum "$direct_closure" | cut -d' ' -f1) == \
  2a4bbe8f5e212f99b95e62f73106262b6901a908dda7d7dfecf27784445bb3c1 ]]
jq -e '
  .manifest.sha256 ==
    "ea7a3e50fa1063d3b2ea82dd288c5a17adcb5d067a4c13089ea961ec47108eaf" and
  .manifest.source_node_count == 400 and
  .manifest.normalization_source_count == 13 and
  .inventory.sha256 ==
    "8095917929b90b2edcbd8afb87d21ab8b0c96614ff894b94feb920a1540eca82" and
  .selected.finding_count == 3689 and
  .selected.source_files_with_findings == 329 and
  .selected.non_dopen_review_occurrences == 509 and
  .selected.site_sha256 ==
    "659c7a21819f0bdd14b0b08c1ebea5c0d4ea3ac2556ae4bcc772ff3fe79865cd" and
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
    "verified-source-stack-integration-pending-compiler-rebuild-and-corpus-run" and
  .dopen_corpus_contract.verified_cakeml_integration ==
    {"branch":"codex/flyspeck-v13-integration",
     "commit":"c006dc4998c354f820d652ce619c0714918a5ed4",
     "dopen_proof_target":"compiler/inference/tests/dopenTestsTheory.uo",
     "dopen_proof_theories":39,
     "ocaml_parser_target":"compiler/parsing/ocaml/camlTestsTheory.uo",
     "proof_hol4_commit":"a390cbabd3a4521bab4ee20281e3e42933a8a3ae"} and
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
    "58859b468dbd0f45c5197ee4b9b32f081125a78c70fe3baba957f7d3ff83acfc" and
  .static_full_build_contract.generated_source_md5 ==
    "441e01a66fabf8e2fb15677e2be6c567" and
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
    "46499f442c741cf9d2c8e4adfeb442b0c4d8fdeb705c6cea8afffbced2e450b8" and
  .source_normalization_contract.entry_count == 13 and
  ([.source_normalization_contract.entries[].operation_count] | add) == 25 and
  .source_normalization_contract.reference_implementation.commit ==
    "99cb5d93fc30f1a6f3e69f5aa5d2063994d33a93" and
  [.source_normalization_contract.entries[].id] ==
    ["PROJECT-POINTER-S3-IMMEDIATE-001",
     "PROJECT-POINTER-S3-ALLOCATED-LIB-001",
     "PROJECT-POINTER-S3-UNSUPPRESS-001",
     "PROJECT-POINTER-S3-RELABEL-001",
     "PROJECT-MODULE-S3-SET-MAKE-001",
     "PROJECT-TOPLOOP-S3-UPDATE-DATABASE-001",
     "PROJECT-TOPLOOP-S3-EVAL-COMMAND-001",
     "PROJECT-TOPLOOP-S3-SSREFLECT-LOOKUP-001",
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
     "fe7f414d6e72a2c838a81b59af15494a1e9f6a5118f9ec0cd1f6ade11a939eed",
     "f1d0a45a0ce2ec54a57bf017989d6960124fd9bbfeb0a8a3ad24a3ffac268467",
     "602d1d0e3e224d742fb412e0fb7bd88b4c176a1aa713bb4f6dc7d6ff350eae15",
     "9fefd64395673d3813762b90f0c99e86942a29fd2b80d0725dab3ba15aba9ed9",
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
     "93343a90863d775f0a09257859553aacb7ad5b885ed95f21517ba0402ce253a3",
     "3fe52ade9303ab0ae0839cadac09995254d5dce553fe949bb5cda558ed8aefbe",
     "5a4175e6542ccee003418bfe6528b3d54d481970c3cff9b564ebda6c7301c117",
     "43e8a264534ce3974bf73e1d376f1e98eb32518205fe0fbee5319a37cdfb414e",
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
  .source_nodes["flyspeck:text_formalization/general/serialization.hl"].execution_normalization.id ==
    "PROJECT-MODULE-S3-SET-MAKE-001" and
  .source_nodes["flyspeck:text_formalization/general/update_database_400.ml"].execution_normalization.id ==
    "PROJECT-TOPLOOP-S3-UPDATE-DATABASE-001" and
  .source_nodes["flyspeck:text_formalization/general/flyspeck_eval_4.14.hl"].execution_normalization.id ==
    "PROJECT-TOPLOOP-S3-EVAL-COMMAND-001" and
  .source_nodes["flyspeck:jHOLLight/caml/ssreflect.hl"].execution_normalization.id ==
    "PROJECT-TOPLOOP-S3-SSREFLECT-LOOKUP-001" and
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
  ([.source_nodes[] | select(has("execution_normalization"))] | length) == 13 and
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
    "95907c7c39b82a246c321ebf49b75b3b" and
  .source_digest_contract.generated_source_sha256 ==
    "59d62c666c1f427c43e569d82b2bfea23babf4fcc61635f17cd767725c69a470" and
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
    "startup-metadata-and-zero-telemetry-explicit-fail-otherwise" and
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
  .static_library_contract.binding_evidence["unix.cma"]
    .process_filesystem_route.glpk_generator_chain.reviewed_occurrence_count == 32 and
  .static_library_contract.binding_evidence["unix.cma"]
    .process_filesystem_route.glpk_generator_chain.external_qualified_uses == [] and
  .static_library_contract.binding_evidence["unix.cma"]
    .process_filesystem_route.glpk_generator_chain.route_root ==
    "Lpproc.execute" and
  .static_library_contract.binding_evidence["unix.cma"]
    .process_filesystem_route.lp_mkdir_disposition.normalization ==
    "PROJECT-FFI-S3-LP-SHELL-ELIMINATION-001" and
  (.static_library_contract.binding_evidence["unix.cma"].telemetry_policy |
    contains("gettimeofday returns deterministic Float.zero")) and
  .static_library_contract.binding_evidence["unix.cma"].telemetry_uses ==
    [
      {"library":"unix.cma","line":43,"member":"gettimeofday","module":"Unix",
       "source":"flyspeck:formal_ineqs/misc/misc_functions.hl"},
      {"library":"unix.cma","line":48,"member":"gettimeofday","module":"Unix",
       "source":"flyspeck:formal_ineqs/misc/misc_functions.hl"},
      {"library":"unix.cma","line":65,"member":"gettimeofday","module":"Unix",
       "source":"flyspeck:formal_lp/hypermap/verify_all.hl"},
      {"library":"unix.cma","line":67,"member":"gettimeofday","module":"Unix",
       "source":"flyspeck:formal_lp/hypermap/verify_all.hl"}
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
    "partial-exact-static-normalizations-active-pending-full-run" and
  .toplevel_interface_contract.selected_execution_disposition.update_database_dead_effect ==
    "PROJECT-TOPLOOP-S3-UPDATE-DATABASE-001" and
  (.toplevel_interface_contract.selected_execution_disposition.definition_only_fail_closed |
    length) == 3 and
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
[[ "$direct_digest_program_sha" == 59d62c666c1f427c43e569d82b2bfea23babf4fcc61635f17cd767725c69a470 ]]
direct_full_build="$workspace_dir/worktrees/candle-loader-v13/candle/flyspeck_full_build.ml"
direct_full_build_sha=$(sha256sum "$direct_full_build" | cut -d' ' -f1)
[[ "$direct_full_build_sha" == 58859b468dbd0f45c5197ee4b9b32f081125a78c70fe3baba957f7d3ff83acfc ]]
[[ $(rg -c '^#flyspeck_needs ' "$direct_full_build") == 297 ]]
for normalization_marker in \
  'normalization=PROJECT-POINTER-S3-IMMEDIATE-001 normalized_sha256=243a2031e595efa9bf0b85b552f9620f4ab45cbca8dcebef821f2eae68c3bba4' \
  'normalization=PROJECT-POINTER-S3-ALLOCATED-LIB-001 normalized_sha256=d1ae25218cce2f2f510966d574d48d283c04748a1b6c8d8dfc0c2ca52438a60f' \
  'normalization=PROJECT-POINTER-S3-UNSUPPRESS-001 normalized_sha256=cb6ab239f202554f204188a3feac089cd2cc69645088e0d95659aeabb304b6de' \
  'normalization=PROJECT-POINTER-S3-RELABEL-001 normalized_sha256=e34517f72ed00eeb30275f1dca01210604665a43d96aa1d759c9f6890f0312e5' \
  'normalization=PROJECT-MODULE-S3-SET-MAKE-001 normalized_sha256=93343a90863d775f0a09257859553aacb7ad5b885ed95f21517ba0402ce253a3' \
  'normalization=PROJECT-TOPLOOP-S3-SSREFLECT-LOOKUP-001 normalized_sha256=43e8a264534ce3974bf73e1d376f1e98eb32518205fe0fbee5319a37cdfb414e' \
  'normalization=PROJECT-FFI-S3-LP-SHELL-ELIMINATION-001 normalized_sha256=79ef91c2192a39566ffc9dc2b5064b6f5c04defb5db9074447f1043495b2122c' \
  'normalization=PROJECT-FFI-S3-LP-STATIC-INVENTORY-001 normalized_sha256=f64bf35f3d1cfff43ab8117ee632e625b219390e416d31a463ad7d2fea2e55d0'
do
  rg -Fq "$normalization_marker" "$direct_full_build"
done
direct_normalization_contract="$workspace_dir/worktrees/candle-loader-v13/candle/flyspeck_normalizations.json"
[[ $(sha256sum "$direct_normalization_contract" | cut -d' ' -f1) == \
  46499f442c741cf9d2c8e4adfeb442b0c4d8fdeb705c6cea8afffbced2e450b8 ]]
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
direct_overlay="$workspace_dir/flyspeck-candle-runs/v13-normalized-overlay-46499f442c741cf9"
[[ $(sha256sum "$direct_overlay/flyspeck_normalization_receipt.json" | \
  cut -d' ' -f1) == \
  e151c1a33fb5cc975d3c8a8c44f916162d1c7c2af0e82a7c1d1ca65cba422e9d ]]
[[ $(jq '.entries | length' \
  "$direct_overlay/flyspeck_normalization_receipt.json") == 13 ]]
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
FLYSPECK_ROOT="$workspace_dir/worktrees/flyspeck-v13-source" \
  CANDLE_BINARY="$direct_clean_candle" \
  "$direct_candle/test_flyspeck_set_make_normalization.sh" >/dev/null
"$direct_candle/test_unix_metadata.sh" "$direct_clean_candle" >/dev/null
"$project_dir/scripts/test-unix-telemetry-compatibility.sh" \
  "$direct_clean_candle" >/dev/null
"$project_dir/scripts/test-local-open-compatibility.sh" \
  "$direct_clean_candle" >/dev/null
"$project_dir/scripts/test-module-compatibility.sh" \
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
clean_noffi_frontier_log="$workspace_dir/flyspeck-candle-runs/v13-direct-clean-noffi-frontier-telemetry.log"
[[ $(sha256sum "$clean_noffi_frontier_log" | cut -d' ' -f1) == \
  ddd78faff4adb56cece0c3bb76e0048dba287a26ad9192a42af3a442bc3668c0 ]]
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
  ba90c9151e3340432740aad39c091a5cf123584c
check_worktree candle-flyspeck-integration \
  "$workspace_dir/worktrees/candle-integration-v13" \
  codex/flyspeck-v13-candle-integration \
  bb5fb495c8e850d525f58f25a13a51ebbc974a10 \
  e78571105b92e12977a3c35a847f2cd60ddb9168
integration_candle="$workspace_dir/worktrees/candle-integration-v13/candle"
[[ $(sha256sum "$integration_candle/flyspeck_manifest.json" | cut -d' ' -f1) == \
  8e10b3f6089363ef97cbed9f84468ff46c5c87b24d0e505fed106faa2ff23b76 ]]
[[ $(sha256sum "$integration_candle/flyspeck_normalizations.json" | cut -d' ' -f1) == \
  37d01c189c718ecda9f6ec18560c0eb93053a288c16421b873377cdec9a40e92 ]]
[[ $(sha256sum "$integration_candle/flyspeck_full_build.ml" | cut -d' ' -f1) == \
  1cdc2cac0a7815e3c9bd04d9ec8330293aa7ef47db9b2757aa1f0f8f411d1307 ]]
[[ $(sha256sum "$integration_candle/flyspeck_source_digests.ml" | cut -d' ' -f1) == \
  8423946c0c61e7ff7ec8c64c87aa9cd56654038c757d3f4a6eecc7101f387b1d ]]
integration_overlay="$workspace_dir/flyspeck-candle-runs/v13-normalized-overlay-37d01c189c718ecd"
[[ $(sha256sum "$integration_overlay/flyspeck_normalization_receipt.json" | \
  cut -d' ' -f1) == \
  e2ba5848bb95b0eac668f44e99ccb20b12e691c43fb31335106d1c665dbb99a2 ]]
[[ $(jq '.entries | length' \
  "$integration_overlay/flyspeck_normalization_receipt.json") == 14 ]]
integration_plan="$workspace_dir/flyspeck-candle-runs/v13-stratum-plan-e785711/plan.json"
[[ $(sha256sum "$integration_plan" | cut -d' ' -f1) == \
  9973466f1ad64f0193403f1a6dc8ac24c312bd18fadd1472b2bcd0ff314df946 ]]
jq -e '
  .schema == 1 and
  (.actions | length) == 297 and
  (.boundaries | length) == 8 and
  .ordered_action_sha256 ==
    "7337a106b431c06723d6b0d04bf5be8deec0cbb288e3534aa40b671e726bc082" and
  .normalization_overlay.entry_count == 14 and
  .normalization_overlay.ordered_binding_sha256 ==
    "bb99d79b85f403b41646f1173040aa6a5c1abba97679a2d975bfd29ff2e94264" and
  .claim ==
    "authenticated host-side action plan only; not Candle execution or S2/S3 evidence" and
  .evidence_boundary.host_status_cannot_upgrade_assurance == true
' "$integration_plan" >/dev/null
check_worktree candle-clean-build \
  "$workspace_dir/worktrees/candle-clean-build-v13" \
  codex/flyspeck-v13-clean-build \
  bb5fb495c8e850d525f58f25a13a51ebbc974a10 \
  87f1fd965313c090fd4d87bcfcc493a3ad7bc79f
check_worktree cakeml-flyspeck-actions \
  "$workspace_dir/worktrees/cakeml-flyspeck-actions-v13" \
  codex/flyspeck-v13-actions \
  14856fcfddeb3fdafdf8a1080e567a55d3102698 \
  1b17732f902fde2efd985905d277a972da73ae0f
check_worktree cakeml-flyspeck-dopen \
  "$workspace_dir/worktrees/cakeml-dopen-v13" \
  codex/flyspeck-v13-dopen \
  dcc03f2866f05b1db18b9f45c731ce45c3a3133e \
  8267fcc5bdd81acb4aba906d33f030f59ff3abb9
check_worktree cakeml-flyspeck-integration \
  "$workspace_dir/worktrees/cakeml-flyspeck-v13-integration" \
  codex/flyspeck-v13-integration \
  dcc03f2866f05b1db18b9f45c731ce45c3a3133e \
  936219bbc3021fa20418d62e85155f2d0092b9f9
check_worktree HOL-cakeml-dopen \
  "$workspace_dir/worktrees/HOL-cakeml-dopen-v13" \
  master \
  a390cbabd3a4521bab4ee20281e3e42933a8a3ae \
  a390cbabd3a4521bab4ee20281e3e42933a8a3ae
check_development hol-light codex/flyspeck-pft-producer \
  433477862bb90b328a593e012e09390e99b2439b \
  a2674c3005da788bb6f1ac9046444edbc70983aa
check_development hol-light-flyspeck codex/flyspeck-pft-compat \
  d8366986e22555c4e4c8ff49667d646d15c35f14 \
  1ea3b9a8c614ffee4116789e23a6dcaa03bdc0b9
