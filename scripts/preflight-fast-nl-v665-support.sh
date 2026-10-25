#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005/cake
renderer=$project/scripts/render-fast-nl-v665-inputs.py
audit=$project/scripts/audit-fast-nl-support-module-closure.py
runtime_surface_audit=$project/scripts/audit-fast-nl-v670-runtime-symbol-surface.py
data=$project/tools/fast_nl_v665_verifier_data.ml
compat=$project/tools/fast_nl_v665_verifier_runtime_compat.ml
setup=$project/tools/fast_nl_v665_setup.ml
support=$project/tools/fast_nl_v665_support.ml
runtime_surface=$project/tools/fast_nl_v670_runtime_surface_support.ml

[[ -x $runtime ]]
[[ -x $renderer ]]
for path in "$audit" "$runtime_surface_audit" "$data" "$compat" "$setup" \
  "$support" "$runtime_surface"; do
  [[ -f $path ]]
done

runtime_surface_result=$($runtime_surface_audit)
grep -Fxq 'status=0' <<<"$runtime_surface_result"
grep -Fxq 'runtime_identifier_count=9' <<<"$runtime_surface_result"
grep -Fxq 'runtime_identifier_use_count=94' <<<"$runtime_surface_result"
grep -Fxq 'raw_runtime_missing_float_of_string_count=1' \
  <<<"$runtime_surface_result"
grep -Fxq 'raw_runtime_replacement_probe_count=1' \
  <<<"$runtime_surface_result"

render_result=$($renderer check)
grep -Fxq 'status=0' <<<"$render_result"
grep -Fxq 'failure_count=0' <<<"$render_result"
grep -Fxq 'combined_identity_count=283' <<<"$render_result"
grep -Fxq 'combined_normalization_count=85' <<<"$render_result"
grep -Fxq 'combined_duplicate_count=0' <<<"$render_result"

module_result=$($audit)
for expectation in \
  'status=0' \
  'prerequisite_entry_count=14' \
  'support_entry_count=4' \
  'planned_load_path_count=304' \
  'literal_edge_count=529' \
  'missing_module_count=0' \
  'missing_identity_count=0' \
  'stale_identity_count=0' \
  'dynamic_request_count=0' \
  'unresolved_loaded_path_count=0' \
  'unresolved_request_count=0' \
  'parse_error_count=0' \
  'normalization_mismatch_count=0' \
  'verifier_closure_error_count=0' \
  'normalization_conflict_count=0' \
  'identity_conflict_count=0'; do
  grep -Fxq "$expectation" <<<"$module_result"
done

nonce=$(printf '%s' 'fast-nl-v665-exact-static-parser-preflight' |
  sha256sum | awk '{print $1}')
set +e
parser_result=$(
  {
    sed '/^#use /d' "$data"
    sed '/^#use /d' "$compat"
    sed '/^#use /d' "$setup"
    sed '/^#use /d' "$support"
    sed '/^#use /d' "$runtime_surface"
  } | "$runtime" --candle-parser-diagnostic-v1 "$nonce" 2>&1
)
parser_status=$?
set -e
[[ $parser_status -eq 0 ]]
[[ $parser_result == \
  "CANDLE_CAMLPARSER_DIAGNOSTIC_V1"$'\t'"$nonce"$'\t'"OK" ]]

printf '%s\n' \
  'receipt_kind=development-fast-nl-v665-static-preflight-v1' \
  'release_evidence=false' \
  'status=0' \
  'verifier_source_count=90' \
  'verifier_normalization_count=29' \
  'generated_identity_extension_count=76' \
  'complete_extra_identity_count=283' \
  'complete_normalization_count=85' \
  'planned_load_path_count=304' \
  'literal_edge_count=529' \
  'missing_module_count=0' \
  'missing_identity_count=0' \
  'unresolved_request_count=0' \
  'dynamic_request_count=0' \
  'parser_status=OK' \
  'runtime_symbol_surface_status=OK' \
  'runtime_identifier_count=9' \
  'runtime_identifier_use_count=94' \
  "parser_nonce=$nonce" \
  "data_sha256=$(sha256sum "$data" | awk '{print $1}')" \
  "compat_sha256=$(sha256sum "$compat" | awk '{print $1}')" \
  "setup_sha256=$(sha256sum "$setup" | awk '{print $1}')" \
  "support_sha256=$(sha256sum "$support" | awk '{print $1}')" \
  "runtime_surface_sha256=$(sha256sum "$runtime_surface" | awk '{print $1}')"
