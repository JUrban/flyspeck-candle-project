#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
failed=/project/flyspeck-candle-runs/v663-fast-nl-current-normalization-dev-001/postsupport
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005/cake
setup=$project/tools/fast_nl_v664_setup.ml
extension=$project/tools/fast_nl_v664_support_identity_extension.ml

[[ -f $failed/CHECKPOINT-FAILED ]]
grep -Fxq 'restored runtime reported an error before the requested boundary' \
  "$failed/CHECKPOINT-FAILED"
[[ $(rg -a -Fc \
  'EXCEPTION: Failure "unauthenticated Candle source action: /project/worktrees/flyspeck-strictbuild-bootstrap-v1/formal_ineqs/trig/series.hl"' \
  "$failed/runtime.log") -eq 1 ]]
[[ $(rg -a -c 'ERROR:|EXCEPTION:|Parsing failed|Program exited|Fatal error|Out of memory' \
  "$failed/runtime.log") -eq 1 ]]

normalization=$($project/scripts/preflight-fast-nl-v663-normalization.sh)
grep -Fxq 'status=0' <<<"$normalization"
grep -Fxq 'entry_count=56' <<<"$normalization"
grep -Fxq 'rewrite_count=3' <<<"$normalization"
grep -Fxq 'missing_count=0' <<<"$normalization"
grep -Fxq 'mismatch_count=0' <<<"$normalization"

closure=$($project/scripts/audit-fast-nl-support-source-closure.py)
grep -Fxq 'status=0' <<<"$closure"
grep -Fxq 'entry_count=4' <<<"$closure"
grep -Fxq 'resolved_node_count=245' <<<"$closure"
grep -Fxq 'resolved_edge_count=398' <<<"$closure"
grep -Fxq 'authority_path_count=645' <<<"$closure"
grep -Fxq 'missing_identity_count=0' <<<"$closure"
grep -Fxq 'unresolved_request_count=0' <<<"$closure"
grep -Fxq 'dynamic_request_count=0' <<<"$closure"
grep -Fxq 'stale_authority_count=0' <<<"$closure"

[[ $(sha256sum "$setup" | awk '{print $1}') == \
  e201fed172fceaadb02e56aaeb468cc881979c67bfc98fffeec831279bb0eab2 ]]
[[ $(sha256sum "$extension" | awk '{print $1}') == \
  46f3e938cc2f975a7ba38b59b343c435d05e34146c39633d8258450591e26036 ]]
[[ $(sha256sum "$project/scripts/audit-fast-nl-support-source-closure.py" |
  awk '{print $1}') == \
  8d2e21b5f930d9509f4cc8a38f7eb5ebee1cc29cbb74afd19c8da4add225ab87 ]]
[[ -x $runtime ]]

nonce=$(printf '%s' 'fast-nl-v664-setup-parser-preflight' |
  sha256sum | awk '{print $1}')
set +e
parser_result=$(
  {
    sed '/^#use /d' "$setup"
    sed '/^#use /d' "$extension"
  } | "$runtime" --candle-parser-diagnostic-v1 "$nonce" 2>&1
)
parser_status=$?
set -e
[[ $parser_status -eq 0 ]]
[[ $parser_result == \
  "CANDLE_CAMLPARSER_DIAGNOSTIC_V1"$'\t'"$nonce"$'\t'"OK" ]]

printf '%s\n' \
  'receipt_kind=development-fast-nl-v664-support-closure-preflight-v1' \
  'release_evidence=false' \
  'status=0' \
  'normalization_entry_count=56' \
  'normalization_rewrite_count=3' \
  'support_entry_count=4' \
  'support_resolved_node_count=245' \
  'support_resolved_edge_count=398' \
  'support_missing_identity_count=0' \
  'support_unresolved_request_count=0' \
  'support_dynamic_request_count=0' \
  'support_stale_authority_count=0' \
  'support_identity_extension_count=11' \
  'parser_status=OK' \
  "parser_nonce=$nonce" \
  'failed_v663_class=omitted-authenticated-support-closure'
