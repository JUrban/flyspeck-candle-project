#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
candidate=/project/worktrees/candle-fast-nl-historical-tag10-v1
base=/project/flyspeck-candle-runs/v666-fast-nl-canonical-verifier-predecessor-dev-001/post-direct-source-interface-v678
input=/project/flyspeck-candle-runs/v679c-fast-nl-tag10-logical-fragment-input-v2-dev-001
output=/project/flyspeck-candle-runs/v679c-fast-nl-tag10-logical-fragment-probe-v2-dev-001
runtime=/project/flyspeck-candle-runs/nonpromotable-dev-link-direct-fast-nl-b3fb54e-0f9690d-bc47e65-attempt-005
preamble=$project/tools/fast_nl_v679c_tag10_fragment_preamble.ml
postcheck=$project/tools/fast_nl_v679c_tag10_fragment_postcheck.ml
marker=CANDLE_FLYSPECK_V679C_TAG10_FRAGMENT_LOGICAL_PROOF_OK

fragments=(
  "$preamble"
  "$candidate/candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_compute.ml"
  "$candidate/candle/cv_compute_analytic_expr_case10173_historical_dihedral_item_sound.ml"
  "$candidate/candle/cv_compute_analytic_expr_case10173_historical_dihedral_program_logical_sound.ml"
  "$postcheck"
)

[[ -f $base/CHECKPOINT-READY && ! -f $base/CHECKPOINT-FAILED ]]
[[ ! -e $input && ! -e $output ]]
[[ -x $runtime/cake ]]
for fragment in "${fragments[@]}"; do
  [[ -f $fragment && ! -L $fragment ]]
done
sha256sum -c "$base/checkpoint.sha256"

candidate_audit=$($project/scripts/audit-fast-nl-v679-tag10-candidate.py)
grep -Fxq 'status=0' <<<"$candidate_audit"
probe_audit=$($project/scripts/audit-fast-nl-v679c-fragment-probe-contract.py)
grep -Fxq 'status=0' <<<"$probe_audit"

mkdir -p "$input"
sha256sum "${fragments[@]}" >"$input/fragments.sha256"
: >"$input/driver.ml"
for fragment in "${fragments[@]}"; do
  printf '(* CANDLE_V679C_FRAGMENT_BEGIN sha256=%s file=%s *)\n' \
    "$(sha256sum "$fragment" | awk '{print $1}')" \
    "$(basename "$fragment")" >>"$input/driver.ml"
  awk '!/^needs "[^"]+";;$/' "$fragment" >>"$input/driver.ml"
  printf '(* CANDLE_V679C_FRAGMENT_END file=%s *)\n' \
    "$(basename "$fragment")" >>"$input/driver.ml"
done
sha256sum "$input/driver.ml" >"$input/driver.sha256"

# The boot-time parser diagnostic intentionally does not implement HOL term
# quotations.  Parse the quotation-free probe glue here; the 10-minute
# restored run is the bounded parser/proof discriminator for the exact source
# fragments.
for parse_source in "$preamble" "$postcheck"; do
  nonce=$(printf '%s\n%s\n' "$0" "$(sha256sum "$parse_source")" |
    sha256sum | awk '{print $1}')
  parser=$("$runtime/cake" --candle-parser-diagnostic-v1 "$nonce" \
    <"$parse_source" 2>&1)
  [[ $parser == \
    "CANDLE_CAMLPARSER_DIAGNOSTIC_V1"$'\t'"$nonce"$'\t'"OK" ]]
done

export FAST_NL_DEV_RUNTIME=$runtime
export FAST_NL_INPUT_PROBE_TIMEOUT_SECONDS=600

"$project/scripts/run-fast-nl-restored-input-probe-v1.sh" \
  "$base" "$output" "$input/driver.ml" "$marker"
