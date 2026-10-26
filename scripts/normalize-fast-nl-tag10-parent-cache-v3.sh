#!/usr/bin/env bash
set -euo pipefail

worktree=/project/worktrees/cakeml-direct-fast-nl-integration-v1
compute=$worktree/candle/prover/compute
scratch=$compute/tag10_probe_scratch
objects=$compute/.hol/objs
run=/project/flyspeck-candle-runs/v684-fast-nl-tag10-parent-manifests-dev-001
head=839017e696dea5fbbb2e03bfeff02c6679724e00
theories=(
  compute_registeredCase10173HistoricalChunk16Tag10Data
  compute_registeredCase10173Tag10DataIdentity
  compute_registeredCase10173Tag10DispatchProbe
  compute_registeredCase10173Tag10HistStepEval
)

[[ ! -e $run ]]
[[ $(git -C "$worktree" rev-parse HEAD) == "$head" ]]
[[ -z $(git -C "$worktree" status --porcelain --untracked-files=no) ]]
mkdir -p "$run" "$objects"

for theory in "${theories[@]}"; do
  [[ $(sha256sum "$compute/${theory}Script.sml" | awk '{print $1}') == \
     $(sha256sum "$scratch/${theory}Script.sml" | awk '{print $1}') ]]
  for suffix in sml sig dat cachekey; do
    source=$scratch/.hol/objs/${theory}Theory.$suffix
    target=$objects/${theory}Theory.$suffix
    [[ -f $source && ! -L $source ]]
    install -m 0644 "$source" "$target"
    cmp -s "$source" "$target"
  done
  for suffix in ui uo; do
    source=$scratch/.hol/objs/${theory}Theory.$suffix
    target=$objects/${theory}Theory.$suffix
    [[ -f $source && ! -L $source ]]
    sed 's#/tag10_probe_scratch/#/#g' "$source" >"$target"
    cmp -s "$target" <(sed 's#/tag10_probe_scratch/#/#g' "$source")
    ! grep -Fq '/tag10_probe_scratch/' "$target"
    grep -Fq \
      "\$(CAKEMLDIR)/candle/prover/compute/${theory}Theory" "$target"
  done
done

{
  printf 'receipt_kind=development-fast-nl-tag10-parent-manifests-v1\n'
  printf 'release_evidence=false\n'
  printf 'status=0\n'
  printf 'candidate_head=%s\n' "$head"
  printf 'relocated_theory_count=4\n'
  printf 'proof_data_changed=false\n'
  printf 'rewritten_field=logical_object_path_only\n'
  for theory in "${theories[@]}"; do
    printf 'theory=%s dat_sha256=%s uo_sha256=%s\n' \
      "$theory" \
      "$(sha256sum "$objects/${theory}Theory.dat" | awk '{print $1}')" \
      "$(sha256sum "$objects/${theory}Theory.uo" | awk '{print $1}')"
  done
  printf 'completed_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >"$run/PARENT-MANIFESTS.receipt"
