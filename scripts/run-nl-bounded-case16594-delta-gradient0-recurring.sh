#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 8 || $# -gt 9 ]]; then
  printf 'usage: %s BINARY INSTRUCTION-SOURCE PROGRAM-SOURCE BENCHMARK-SOURCE COMPILE-SOURCE ASSEMBLY JOBS.tsv RUN-DIRECTORY [RUNS]\n' "$0" >&2
  exit 2
fi

binary=$1
instruction_source=$2
program_source=$3
benchmark_source=$4
compile_source=$5
assembly=$6
jobs=$7
run_directory=$8
runs=${9:-7}
expected_jobs_sha=236c4ffa1773b92c80584defa24beeddfb20b59811bc287a4f4770da87ac8e80

[[ -x "$binary" ]]
for input in "$instruction_source" "$program_source" "$benchmark_source" \
    "$compile_source" "$assembly" "$jobs"; do
  [[ -f "$input" ]]
done
[[ "$runs" =~ ^[1-9][0-9]*$ ]]
[[ $(sha256sum "$jobs" | cut -d' ' -f1) == "$expected_jobs_sha" ]]
[[ $(wc -l <"$jobs") -eq 875 ]]
[[ ! -e "$run_directory" ]]
mkdir "$run_directory"

{
  printf 'status=DEVELOPMENT_NON_RELEASE_NON_AUTHORITATIVE\n'
  printf 'issued_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'runs=%s\n' "$runs"
  printf 'batches_per_run=1000\n'
  printf 'authenticated_cells_per_batch=875\n'
  printf 'logical_instruction=delta_gradient_component_0\n'
  printf 'expected_count=875\n'
  printf 'expected_digest=111527807236922\n'
  printf 'checks_per_run=1000\n'
  printf 'source_jobs_sha256=%s\n' "$expected_jobs_sha"
  printf 'cml_heap_mib=128\n'
  printf 'cml_stack_mib=64\n'
  sha256sum "$binary" "$instruction_source" "$program_source" \
    "$benchmark_source" "$compile_source" "$assembly" "$jobs"
} >"$run_directory/manifest.txt"

printf 'run\twall_seconds\tuser_seconds\tsystem_seconds\tmaximum_rss_kib\texit\n' \
  >"$run_directory/runs.tsv"

# Untimed warm-up validates all 1,000 count/digest checks.
CML_HEAP_SIZE=128 CML_STACK_SIZE=64 "$binary"
for run in $(seq 1 "$runs"); do
  timing_file="$run_directory/.timing-$run"
  start_ns=$(date +%s%N)
  CML_HEAP_SIZE=128 CML_STACK_SIZE=64 \
    /usr/bin/time -f '%U\t%S\t%M\t%x' -o "$timing_file" "$binary"
  end_ns=$(date +%s%N)
  wall_seconds=$(awk -v start="$start_ns" -v end="$end_ns" \
    'BEGIN {printf "%.9f", (end - start) / 1000000000}')
  printf '%s\t%s\t' "$run" "$wall_seconds" >>"$run_directory/runs.tsv"
  sed -n '1p' "$timing_file" >>"$run_directory/runs.tsv"
  rm "$timing_file"
done

awk -F '\t' '
  NR > 1 {
    count += 1; wall += $2; user += $3; system_time += $4; rss += $5;
    if ($6 != 0) bad += 1;
  }
  END {
    print "runs\tmean_run_seconds\tmean_batch_seconds\tmean_user_seconds\tmean_system_seconds\tmean_rss_kib\tnonzero_exits";
    printf "%d\t%.9f\t%.9f\t%.9f\t%.9f\t%.3f\t%d\n", count,
      wall / count, wall / count / 1000, user / count,
      system_time / count, rss / count, bad + 0;
  }
' "$run_directory/runs.tsv" >"$run_directory/summary.tsv"

sha256sum "$run_directory/manifest.txt" "$run_directory/runs.tsv" \
  "$run_directory/summary.tsv" >"$run_directory/SHA256SUMS"
cat "$run_directory/summary.tsv"
