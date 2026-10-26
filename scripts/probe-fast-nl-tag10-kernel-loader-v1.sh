#!/usr/bin/env bash
set -euo pipefail

worktree=/project/worktrees/cakeml-direct-fast-nl-integration-v1
prover=$worktree/candle/prover
compute=$prover/compute
holmake=/project/worktrees/HOL-cakeml-dopen-v13/bin/Holmake
run=/project/flyspeck-candle-runs/v685-fast-nl-tag10-kernel-loader-probe-dev-001
parent_receipt=/project/flyspeck-candle-runs/v684-fast-nl-tag10-parent-manifests-dev-001/PARENT-MANIFESTS.receipt
head=839017e696dea5fbbb2e03bfeff02c6679724e00
maximum_seconds=420
theories=(
  compute_registeredCase10173HistoricalChunk16Tag10Data
  compute_registeredCase10173Tag10DataIdentity
  compute_registeredCase10173Tag10DispatchProbe
  compute_registeredCase10173Tag10HistStepEval
)

[[ ! -e $run ]]
[[ $(git -C "$worktree" rev-parse HEAD) == "$head" ]]
[[ -z $(git -C "$worktree" status --porcelain --untracked-files=no) ]]
grep -Fxq 'status=0' "$parent_receipt"
grep -Fxq 'proof_data_changed=false' "$parent_receipt"
grep -Fxq 'rewritten_field=logical_object_path_only' "$parent_receipt"
for theory in "${theories[@]}"; do
  for suffix in ui uo; do
    object=$compute/.hol/objs/${theory}Theory.$suffix
    [[ -f $object && ! -L $object ]]
    ! grep -Fq '/tag10_probe_scratch/' "$object"
  done
done

mkdir -p "$run"
set +e
set -o pipefail
(
  cd "$prover"
  /usr/bin/time -v timeout --signal=TERM --kill-after=20s \
    "${maximum_seconds}s" \
    "$holmake" --no-project --no_prereqs --heap-size=65536 \
      -I compute/tag10_probe_scratch -I compute \
      -I "$worktree/basis" -I "$worktree/basis/pure" \
      -I "$worktree/candle/standard/ml_kernel" \
      -I "$worktree/misc" -I "$worktree/semantics" \
      -I "$worktree/translator" -I "$worktree/translator/monadic" \
      --rebuild=cachekey -j1 candle_kernelProgTheory.uo
) 2>&1 | tee "$run/kernel-loader.log"
build_status=${PIPESTATUS[0]}
set -e

[[ $build_status == 124 ]]
grep -Fq 'Created theory "candle_kernelProg"' "$run/kernel-loader.log"
grep -Fq 'nsLookup_candle_kernelProg_env_50_pfun_eqs' \
  "$run/kernel-loader.log"
grep -Fq 'Exit status: 124' "$run/kernel-loader.log"
if grep -Eq 'Cannot find file|Uncaught exception|Holmake: Failed script build' \
    "$run/kernel-loader.log"; then
  printf 'kernel_loader_error\n' >&2
  exit 1
fi

{
  printf 'receipt_kind=development-fast-nl-tag10-kernel-loader-probe-v1\n'
  printf 'release_evidence=false\n'
  printf 'status=0\n'
  printf 'candidate_head=%s\n' "$head"
  printf 'former_missing_object_boundary=passed\n'
  printf 'minimum_environment=50\n'
  printf 'expected_timeout=true\n'
  printf 'maximum_seconds=%s\n' "$maximum_seconds"
  printf 'jobs=1\n'
  printf 'log_sha256=%s\n' \
    "$(sha256sum "$run/kernel-loader.log" | awk '{print $1}')"
  printf 'completed_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >"$run/KERNEL-LOADER-PROBE.receipt"
