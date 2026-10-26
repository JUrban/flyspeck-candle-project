#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
integration=/project/worktrees/cakeml-direct-fast-nl-integration-v1
compute=$integration/candle/prover/compute
objects=$compute/.hol/objs
scratch_objects=$compute/tag10_probe_scratch/.hol/objs
base_objects=/project/worktrees/cakeml-direct-fast-nl-tag10-v1/candle/prover/compute/.hol/objs
run=/project/flyspeck-candle-runs/v686-fast-nl-tag10-cache-recovery-dev-001
audit=$project/scripts/audit-fast-nl-tag10-cache-recovery-inputs.py
suffixes=(sml sig dat cachekey)
theories=(
  compute_evalPure
  compute_registeredCase10173Tag10HistItemCongruence
  compute_registeredCase10173Tag10OrdinaryReachable
)

[[ ! -e $run ]]
input_receipt=$(mktemp)
trap 'rm -f "$input_receipt"' EXIT
"$audit" >"$input_receipt"
grep -Fxq 'status=0' "$input_receipt"
grep -Fxq 'damaged_theory_count=3' \
  "$input_receipt"
grep -Fxq 'missing_artifact_count=12' \
  "$input_receipt"

mkdir -p "$run/donors" "$run/retained-manifests"
install -m 0644 "$input_receipt" \
  "$run/INPUT-AUDIT.receipt"

for theory in "${theories[@]}"; do
  for suffix in ui uo; do
    source=$objects/${theory}Theory.$suffix
    install -m 0644 "$source" \
      "$run/retained-manifests/${theory}Theory.$suffix"
  done
  if [[ $theory == compute_evalPure ]]; then
    donor=$base_objects
  else
    donor=$scratch_objects
  fi
  for suffix in "${suffixes[@]}"; do
    source=$donor/${theory}Theory.$suffix
    staged=$run/donors/${theory}Theory.$suffix
    target=$objects/${theory}Theory.$suffix
    [[ ! -e $target ]]
    install -m 0644 "$source" "$staged"
    cmp -s "$source" "$staged"
    install -m 0644 "$staged" "$target"
    cmp -s "$staged" "$target"
  done
done

for theory in "${theories[@]}"; do
  for suffix in ui uo; do
    cmp -s "$objects/${theory}Theory.$suffix" \
      "$run/retained-manifests/${theory}Theory.$suffix"
  done
  for suffix in "${suffixes[@]}"; do
    cmp -s "$objects/${theory}Theory.$suffix" \
      "$run/donors/${theory}Theory.$suffix"
  done
done
[[ -z $(git -C "$integration" status --porcelain --untracked-files=no) ]]

{
  printf 'receipt_kind=development-fast-nl-tag10-cache-recovery-v1\n'
  printf 'release_evidence=false\n'
  printf 'status=0\n'
  printf 'restored_theory_count=3\n'
  printf 'restored_artifact_count=12\n'
  printf 'retained_manifest_count=6\n'
  printf 'retained_manifests_changed=false\n'
  for theory in "${theories[@]}"; do
    for suffix in "${suffixes[@]}"; do
      target=$objects/${theory}Theory.$suffix
      printf 'artifact=%sTheory.%s sha256=%s\n' \
        "$theory" "$suffix" "$(sha256sum "$target" | awk '{print $1}')"
    done
  done
  printf 'completed_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >"$run/CACHE-RECOVERY.receipt"
