#!/usr/bin/env bash
set -euo pipefail

worktree=/project/worktrees/cakeml-direct-fast-nl-integration-v1
compute=$worktree/candle/prover/compute
scratch=$compute/tag10_probe_scratch
objects=$compute/.hol/objs
holmake=/project/worktrees/HOL-cakeml-dopen-v13/bin/Holmake
run=/project/flyspeck-candle-runs/v683-fast-nl-tag10-parent-relocation-dev-001
head=839017e696dea5fbbb2e03bfeff02c6679724e00
maximum_seconds=180
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
done

targets=()
for theory in "${theories[@]}"; do
  targets+=("${theory}Theory.uo")
done

set -o pipefail
(
  cd "$compute"
  /usr/bin/time -v timeout --signal=TERM --kill-after=20s \
    "${maximum_seconds}s" \
    "$holmake" --relocbuild --no-project --no_prereqs --heap-size=4096 \
      -I tag10_probe_scratch -I "$worktree/misc" \
      --rebuild=mtime -j1 "${targets[@]}"
) 2>&1 | tee "$run/parent-relocation.log"

grep -Fq 'Exit status: 0' "$run/parent-relocation.log"
if grep -Eq 'Building ([5-9]|[1-9][0-9]+) theory files' \
    "$run/parent-relocation.log"; then
  printf 'unexpected_theory_expansion\n' >&2
  exit 1
fi
for theory in "${theories[@]}"; do
  parent=$objects/${theory}Theory
  isolated=$scratch/.hol/objs/${theory}Theory
  [[ -f $parent.ui && -f $parent.uo && -f $parent.cachekey ]]
  cmp -s "$parent.cachekey" "$isolated.cachekey"
  for suffix in sml sig dat; do
    cmp -s "$parent.$suffix" "$isolated.$suffix"
  done
done

{
  printf 'receipt_kind=development-fast-nl-tag10-parent-relocation-v1\n'
  printf 'release_evidence=false\n'
  printf 'status=0\n'
  printf 'candidate_head=%s\n' "$head"
  printf 'relocated_theory_count=4\n'
  printf 'maximum_seconds=%s\n' "$maximum_seconds"
  printf 'jobs=1\n'
  printf 'log_sha256=%s\n' \
    "$(sha256sum "$run/parent-relocation.log" | awk '{print $1}')"
  printf 'completed_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >"$run/PARENT-RELOCATION.receipt"
