#!/usr/bin/env bash
set -euo pipefail

overlay=/project/flyspeck-candle-runs/v355-postsetup-checkpoint-dev-001/overlay-data-v355.ml
direct=/project/worktrees/flyspeck-direct-action296-643bfd12
strict_base=/project/worktrees/flyspeck-strictbuild-checkpoint-base-9ae969df

[[ $(sha256sum "$overlay" | awk '{print $1}') == \
   93ff62d9dc4b0842bda3a1aaf3fc9fe4c71e944ee31950c737e5ad36d07f7d1c ]]
[[ $(git -C "$direct" rev-parse HEAD) == \
   d8adac7fe1dbb1e07d417995f786fa77fa1c80a5 ]]
[[ -z $(git -C "$direct" status --short) ]]
[[ $(git -C "$strict_base" rev-parse HEAD) == \
   9ae969dfaca95e223d44b50f7cae00df3d2ab949 ]]
[[ -z $(git -C "$strict_base" status --short) ]]

old_strict=/project/worktrees/flyspeck-strictbuild-bootstrap-v1/text_formalization/build/strictbuild.hl
base_strict=$strict_base/text_formalization/build/strictbuild.hl
serialization=$direct/text_formalization/general/serialization.hl
mk_all_ineq=$direct/text_formalization/nonlinear/mk_all_ineq.hl

entry_count=0
rewrite_count=0
while IFS=$'\t' read -r target expected; do
  entry_count=$((entry_count + 1))
  case $target in
    "$old_strict")
      [[ $expected == 88364c468334ed91b661cc2ecc8a484a ]]
      target=$base_strict
      rewrite_count=$((rewrite_count + 1))
      ;;
    "$serialization")
      [[ $expected == f8460ac2a26b291b113ffa2ad2ffaace ]]
      expected=e0766072204d441da563dd688cfe1a7b
      rewrite_count=$((rewrite_count + 1))
      ;;
    "$mk_all_ineq")
      [[ $expected == 3076e3e4143397c5764911906732abb7 ]]
      expected=e335cb02c223ba4a0f748a62e7b48d87
      rewrite_count=$((rewrite_count + 1))
      ;;
  esac
  [[ -f $target ]]
  [[ $(md5sum "$target" | awk '{print $1}') == "$expected" ]]
done < <(awk -F'"' '/^  \(/{print $4 "\t" $6}' "$overlay")

[[ $entry_count -eq 56 ]]
[[ $rewrite_count -eq 3 ]]

printf '%s\n' \
  'receipt_kind=development-fast-nl-v663-normalization-preflight-v1' \
  'release_evidence=false' \
  'status=0' \
  "entry_count=$entry_count" \
  "rewrite_count=$rewrite_count" \
  'stale_entry_count=2' \
  'missing_count=0' \
  'mismatch_count=0' \
  'direct_flyspeck_commit=d8adac7fe1dbb1e07d417995f786fa77fa1c80a5' \
  'strictbuild_commit=9ae969dfaca95e223d44b50f7cae00df3d2ab949'
