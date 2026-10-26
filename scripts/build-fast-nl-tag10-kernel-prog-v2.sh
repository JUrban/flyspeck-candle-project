#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' \
  'retired: v681 exposed the parent-cache path defect; use the v3 controller' >&2
exit 2

project=/project/flyspeck-candle-project
worktree=/project/worktrees/cakeml-direct-fast-nl-integration-v1
prover=$worktree/candle/prover
scratch=$prover/compute/tag10_probe_scratch
holmake=/project/worktrees/HOL-cakeml-dopen-v13/bin/Holmake
run=/project/flyspeck-candle-runs/v681-fast-nl-tag10-kernel-prog-dev-001
maximum_seconds=3000
head=839017e696dea5fbbb2e03bfeff02c6679724e00
prior_log=$prover/tag10-kernel-prog-build-v1.log

/project/flyspeck-candle-project/scripts/require-long-run-hazard-preflight.sh \
  "$maximum_seconds"

[[ ! -e $run ]]
[[ $(git -C "$worktree" rev-parse HEAD) == "$head" ]]
[[ -z $(git -C "$worktree" status --porcelain --untracked-files=no) ]]
grep -Fq 'nsLookup_candle_kernelProg_env_419_pfun_eqs' "$prior_log"
grep -Fq 'Elapsed (wall clock) time (h:mm:ss or m:ss): 30:00.03' "$prior_log"
grep -Fq 'Exit status: 124' "$prior_log"

mkdir -p "$run"
set -o pipefail
(
  cd "$prover"
  /usr/bin/time -v timeout --signal=TERM --kill-after=30s \
    "${maximum_seconds}s" \
    "$holmake" --no-project --no_prereqs --heap-size=65536 \
      -I compute/tag10_probe_scratch -I compute \
      -I "$worktree/basis" -I "$worktree/basis/pure" \
      -I "$worktree/candle/standard/ml_kernel" \
      -I "$worktree/misc" -I "$worktree/semantics" \
      -I "$worktree/translator" -I "$worktree/translator/monadic" \
      --rebuild=cachekey -j1 candle_kernelProgTheory.uo
) 2>&1 | tee "$run/kernel-prog.log" "$prover/tag10-kernel-prog-build-v2.log"

grep -Fq 'Holmake: [1/1] candle_kernelProg' "$run/kernel-prog.log"
grep -Fq 'Exit status: 0' "$run/kernel-prog.log"
artifact=$prover/.hol/objs/candle_kernelProgTheory.uo
[[ -f $artifact && ! -L $artifact ]]

{
  printf 'receipt_kind=development-fast-nl-tag10-kernel-prog-v1\n'
  printf 'release_evidence=false\n'
  printf 'status=0\n'
  printf 'candidate_head=%s\n' "$head"
  printf 'maximum_seconds=%s\n' "$maximum_seconds"
  printf 'target=candle_kernelProgTheory.uo\n'
  printf 'target_count=1\n'
  printf 'jobs=1\n'
  printf 'artifact_sha256=%s\n' "$(sha256sum "$artifact" | awk '{print $1}')"
  printf 'artifact_size=%s\n' "$(stat -c %s "$artifact")"
  printf 'log_sha256=%s\n' "$(sha256sum "$run/kernel-prog.log" | awk '{print $1}')"
  printf 'completed_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >"$run/KERNEL-PROG.receipt"
