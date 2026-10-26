#!/usr/bin/env bash
set -euo pipefail

project=/project/flyspeck-candle-project
worktree=/project/worktrees/cakeml-direct-fast-nl-integration-v1
prover=$worktree/candle/prover
holmake=/project/worktrees/HOL-cakeml-dopen-v13/bin/Holmake
run=/project/flyspeck-candle-runs/v691-fast-nl-tag10-kernel-prog-dev-001
maximum_seconds=3000
head=839017e696dea5fbbb2e03bfeff02c6679724e00
prior_log=$prover/tag10-kernel-prog-build-v1.log
loader_receipt=/project/flyspeck-candle-runs/v690-fast-nl-tag10-kernel-loader-dev-001/LOADER-PROBE.receipt
loader_receipt_sha256=05ddc47ff130bf2cf695c7b36a148f13e2eaa1d8af2afd0e60a0bc21275c1692
relocation_receipt=/project/flyspeck-candle-runs/v687-fast-nl-tag10-parent-cache-relocation-dev-001/PARENT-CACHE-RELOCATION.receipt
relocation_receipt_sha256=7e14d409f60c555c900e684e0bfd24845bb372d8798c4c2882c596d8df276196

/project/flyspeck-candle-project/scripts/require-long-run-hazard-preflight.sh \
  "$maximum_seconds"

[[ ! -e $run ]]
[[ $(git -C "$worktree" rev-parse HEAD) == "$head" ]]
[[ -z $(git -C "$worktree" status --porcelain --untracked-files=no) ]]
printf '%s  %s\n' "$loader_receipt_sha256" "$loader_receipt" | sha256sum -c -
printf '%s  %s\n' "$relocation_receipt_sha256" "$relocation_receipt" | sha256sum -c -
grep -Fxq 'status=0' "$loader_receipt"
grep -Fxq 'actual_loader_probe_authenticated=true' \
  <($project/scripts/audit-fast-nl-tag10-kernel-loader-result.py)
grep -Fq 'nsLookup_candle_kernelProg_env_419_pfun_eqs' "$prior_log"
grep -Fq 'Elapsed (wall clock) time (h:mm:ss or m:ss): 30:00.03' "$prior_log"
grep -Fq 'Exit status: 124' "$prior_log"

mkdir -p "$run"
status=1
finish() {
  rc=$?
  if [[ ! -e $run/KERNEL-PROG.receipt ]]; then
    {
      printf 'receipt_kind=development-fast-nl-tag10-kernel-prog-v2\n'
      printf 'release_evidence=false\n'
      printf 'status=1\n'
      printf 'exit_status=%s\n' "$rc"
      [[ -f $run/kernel-prog.log ]] && \
        printf 'log_sha256=%s\n' "$(sha256sum "$run/kernel-prog.log" | awk '{print $1}')"
      printf 'completed_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    } >"$run/KERNEL-PROG.receipt"
  fi
}
trap finish EXIT

set -o pipefail
(
  cd "$prover"
  /usr/bin/time -v timeout --signal=TERM --kill-after=30s \
    "${maximum_seconds}s" \
    "$holmake" --no-project --no_prereqs --heap-size=65536 \
      -I compute \
      -I "$worktree/basis" -I "$worktree/basis/pure" \
      -I "$worktree/candle/standard/ml_kernel" \
      -I "$worktree/misc" -I "$worktree/semantics" \
      -I "$worktree/translator" -I "$worktree/translator/monadic" \
      --rebuild=cachekey -j1 candle_kernelProgTheory.uo
) 2>&1 | tee "$run/kernel-prog.log" "$prover/tag10-kernel-prog-build-v3.log"

grep -Fq 'Holmake: [1/1] candle_kernelProg' "$run/kernel-prog.log"
grep -Fq 'Exit status: 0' "$run/kernel-prog.log"
artifact=$prover/.hol/objs/candle_kernelProgTheory.uo
[[ -f $artifact && ! -L $artifact ]]

{
  printf 'receipt_kind=development-fast-nl-tag10-kernel-prog-v2\n'
  printf 'release_evidence=false\n'
  printf 'status=0\n'
  printf 'candidate_head=%s\n' "$head"
  printf 'maximum_seconds=%s\n' "$maximum_seconds"
  printf 'target=candle_kernelProgTheory.uo\n'
  printf 'target_count=1\n'
  printf 'jobs=1\n'
  printf 'loader_receipt_sha256=%s\n' "$loader_receipt_sha256"
  printf 'relocation_receipt_sha256=%s\n' "$relocation_receipt_sha256"
  printf 'artifact_sha256=%s\n' "$(sha256sum "$artifact" | awk '{print $1}')"
  printf 'artifact_size=%s\n' "$(stat -c %s "$artifact")"
  printf 'log_sha256=%s\n' "$(sha256sum "$run/kernel-prog.log" | awk '{print $1}')"
  printf 'completed_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >"$run/KERNEL-PROG.receipt"
trap - EXIT
