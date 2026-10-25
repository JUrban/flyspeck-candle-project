#!/usr/bin/env bash
set -euo pipefail

run=/project/flyspeck-candle-runs/v658-fast-nl-compiler64-final-stage-dev-001
prior=/project/flyspeck-candle-runs/v656-fast-nl-production-integration-dev-001
cake=/project/worktrees/cakeml-direct-fast-nl-integration-v1
hol=/project/worktrees/HOL-cakeml-dopen-v13
candle=/project/worktrees/candle-direct-fast-nl-runtime-v1
trans=$cake/compiler/bootstrap/translation

cake_head=aa7ffbc3a5e30c0f78acfe883f39476d0a3f035a
hol_head=bc47e6586a87ac538a71b10206a83c169c171d1a
candle_head=0f9690d3683efca78a60d4607596815245e37578

log=$run/compiler64-final-stage-v1.log
status_file=$run/compiler64-final-stage-v1.status
receipt=$run/compiler64-final-stage-v1.receipt
source_hashes=$run/source-identities-v1.sha256

mkdir -p "$run"
[[ ! -e $log ]]
[[ ! -e $status_file ]]
[[ ! -e $receipt ]]

[[ $(git -C "$cake" rev-parse HEAD) == "$cake_head" ]]
[[ $(git -C "$hol" rev-parse HEAD) == "$hol_head" ]]
[[ $(git -C "$candle" rev-parse HEAD) == "$candle_head" ]]
[[ -z $(git -C "$cake" status --short) ]]
[[ -z $(git -C "$hol" status --short) ]]
[[ -z $(git -C "$candle" status --short) ]]
[[ $(git -C "$cake" diff --name-only d4aaf4a18c8e4f8863297b4092c57d20de16a226..HEAD) == \
   compiler/bootstrap/translation/compiler64ProgScript.sml ]]

# Authenticate every reused predecessor from the stopped 25-stage run.  The
# sole source change is downstream in compiler64ProgScript.sml.
for number in $(seq -w 1 24); do
  prior_receipt=$(find "$prior" -maxdepth 1 -type f \
    -name "verified-suffix-current-v1-${number}-*.receipt" -print -quit)
  [[ -n $prior_receipt ]]
  stage=$(sed -n 's/^stage=//p' "$prior_receipt")
  expected_dat_sha=$(sed -n 's/^theory_dat_sha256=//p' "$prior_receipt")
  expected_theory_hash=$(sed -n 's/^theory_hash=//p' "$prior_receipt")
  theory_dat=$trans/.hol/objs/${stage}Theory.dat
  theory_sml=$trans/.hol/objs/${stage}Theory.sml
  [[ -s $theory_dat ]]
  [[ -s $theory_sml ]]
  [[ $(sha256sum "$theory_dat" | awk '{print $1}') == "$expected_dat_sha" ]]
  [[ $(sed -n 's/.*hash = "\([0-9a-f]*\)".*/\1/p' "$theory_sml" | head -1) == \
     "$expected_theory_hash" ]]
done

available_kib=$(awk '/^MemAvailable:/{print $2}' /proc/meminfo)
[[ $available_kib -ge 180000000 ]]
available_disk_kib=$(df --output=avail -k "$run" | tail -1)
[[ $available_disk_kib -ge 500000000 ]]

sha256sum \
  "$trans/compiler64ProgScript.sml" \
  "$cake/candle/prover/candle_kernelProgScript.sml" \
  "$candle/compute.ml" \
  >"$source_hashes"

started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
set +e
(
  cd "$trans"
  /usr/bin/time -v "$hol/bin/Holmake" \
    --heap-size=150000 --no_prereqs -j1 compiler64ProgTheory.uo
) >"$log" 2>&1
rc=$?
set -e
printf '%s\n' "$rc" >"$status_file"

finished_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
{
  printf 'receipt_kind=development-fast-nl-compiler64-final-stage-v1\n'
  printf 'release_evidence=false\n'
  printf 'status=%s\n' "$rc"
  printf 'cake_head=%s\n' "$cake_head"
  printf 'hol_head=%s\n' "$hol_head"
  printf 'candle_head=%s\n' "$candle_head"
  printf 'reused_verified_stages=24\n'
  printf 'started_utc=%s\n' "$started_utc"
  printf 'finished_utc=%s\n' "$finished_utc"
  printf 'log_sha256=%s\n' "$(sha256sum "$log" | awk '{print $1}')"
  if [[ $rc -eq 0 ]]; then
    theory_sml=$trans/.hol/objs/compiler64ProgTheory.sml
    theory_dat=$trans/.hol/objs/compiler64ProgTheory.dat
    printf 'theory_hash=%s\n' \
      "$(sed -n 's/.*hash = "\([0-9a-f]*\)".*/\1/p' "$theory_sml" | head -1)"
    printf 'theory_dat_size=%s\n' "$(stat -c '%s' "$theory_dat")"
    printf 'theory_dat_sha256=%s\n' \
      "$(sha256sum "$theory_dat" | awk '{print $1}')"
  fi
} >"$receipt"

exit "$rc"
