#!/usr/bin/env bash
set -euo pipefail

worktree=/project/worktrees/cakeml-direct-fast-nl-integration-v1
compute=$worktree/candle/prover/compute
scratch=$compute/tag10_probe_scratch
holmake=/project/worktrees/HOL-cakeml-dopen-v13/bin/Holmake
run=/project/flyspeck-candle-runs/v682-fast-nl-tag10-parent-cache-dev-001
head=839017e696dea5fbbb2e03bfeff02c6679724e00
maximum_seconds=600
theories=(
  compute_registeredCase10173HistoricalChunk16Tag10Data
  compute_registeredCase10173Tag10DataIdentity
  compute_registeredCase10173Tag10DispatchProbe
  compute_registeredCase10173Tag10HistStepEval
)

[[ ! -e $run ]]
[[ $(git -C "$worktree" rev-parse HEAD) == "$head" ]]
[[ -z $(git -C "$worktree" status --porcelain --untracked-files=no) ]]
for theory in "${theories[@]}"; do
  [[ $(sha256sum "$compute/${theory}Script.sml" | awk '{print $1}') == \
     $(sha256sum "$scratch/${theory}Script.sml" | awk '{print $1}') ]]
  [[ -f $scratch/.hol/objs/${theory}Theory.ui ]]
  [[ -f $scratch/.hol/objs/${theory}Theory.uo ]]
done

mkdir -p "$run"
targets=()
for theory in "${theories[@]}"; do
  targets+=("${theory}Theory.uo")
done

set -o pipefail
(
  cd "$compute"
  /usr/bin/time -v timeout --signal=TERM --kill-after=20s \
    "${maximum_seconds}s" \
    "$holmake" --no-project --no_prereqs --heap-size=16384 \
      -I tag10_probe_scratch -I "$worktree/misc" \
      --rebuild=cachekey -j1 "${targets[@]}"
) 2>&1 | tee "$run/parent-cache.log"

grep -Fq 'Holmake: [4/4] compute_registeredCase10173Tag10HistStepEval' \
  "$run/parent-cache.log"
grep -Fq 'Exit status: 0' "$run/parent-cache.log"
for theory in "${theories[@]}"; do
  parent=$compute/.hol/objs/${theory}Theory
  isolated=$scratch/.hol/objs/${theory}Theory
  [[ -f $parent.ui && -f $parent.uo && -f $parent.cachekey ]]
  cmp -s "$parent.cachekey" "$isolated.cachekey"
done

{
  printf 'receipt_kind=development-fast-nl-tag10-parent-cache-v1\n'
  printf 'release_evidence=false\n'
  printf 'status=0\n'
  printf 'candidate_head=%s\n' "$head"
  printf 'normalized_theory_count=4\n'
  printf 'maximum_seconds=%s\n' "$maximum_seconds"
  printf 'jobs=1\n'
  printf 'log_sha256=%s\n' "$(sha256sum "$run/parent-cache.log" | awk '{print $1}')"
  printf 'completed_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >"$run/PARENT-CACHE.receipt"
