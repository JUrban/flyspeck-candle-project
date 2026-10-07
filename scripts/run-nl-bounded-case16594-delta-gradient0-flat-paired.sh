#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 9 || $# -gt 10 ]]; then
  printf 'usage: %s BASELINE-BINARY FLAT-BINARY FLAT-THEORY FLAT-PROGRAM-SOURCE FLAT-COMPILE-SOURCE BASELINE-ASSEMBLY FLAT-ASSEMBLY JOBS.tsv RUN-DIRECTORY [PAIRS]\n' "$0" >&2
  exit 2
fi

baseline_binary=$1
flat_binary=$2
flat_theory=$3
flat_program_source=$4
flat_compile_source=$5
baseline_assembly=$6
flat_assembly=$7
jobs=$8
run_directory=$9
pairs=${10:-7}
expected_jobs_sha=236c4ffa1773b92c80584defa24beeddfb20b59811bc287a4f4770da87ac8e80

[[ -x "$baseline_binary" && -x "$flat_binary" ]]
for input in "$flat_theory" "$flat_program_source" "$flat_compile_source" \
    "$baseline_assembly" "$flat_assembly" "$jobs"; do
  [[ -f "$input" ]]
done
[[ "$pairs" =~ ^[1-9][0-9]*$ ]]
[[ $(sha256sum "$jobs" | cut -d' ' -f1) == "$expected_jobs_sha" ]]
[[ $(wc -l <"$jobs") -eq 875 ]]
[[ ! -e "$run_directory" ]]
mkdir "$run_directory"

{
  printf 'status=DEVELOPMENT_NON_RELEASE_NON_AUTHORITATIVE\n'
  printf 'issued_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'pairs=%s\n' "$pairs"
  printf 'batches_per_lane_run=1000\n'
  printf 'authenticated_cells_per_batch=875\n'
  printf 'expected_count=875\n'
  printf 'expected_digest=111527807236922\n'
  printf 'source_jobs_sha256=%s\n' "$expected_jobs_sha"
  printf 'cml_heap_mib=128\n'
  printf 'cml_stack_mib=64\n'
  sha256sum "$baseline_binary" "$flat_binary" "$flat_theory" \
    "$flat_program_source" "$flat_compile_source" \
    "$baseline_assembly" "$flat_assembly" "$jobs"
} >"$run_directory/manifest.txt"

printf 'pair\tposition\tlane\twall_seconds\tuser_seconds\tsystem_seconds\tmaximum_rss_kib\texit\n' \
  >"$run_directory/runs.tsv"

# Each warm-up checks all 1,000 complete batch digests.
CML_HEAP_SIZE=128 CML_STACK_SIZE=64 "$baseline_binary"
CML_HEAP_SIZE=128 CML_STACK_SIZE=64 "$flat_binary"

run_lane() {
  local pair=$1 position=$2 lane=$3 binary=$4
  local timing_file="$run_directory/.timing-$pair-$position-$lane"
  local start_ns end_ns wall_seconds
  start_ns=$(date +%s%N)
  CML_HEAP_SIZE=128 CML_STACK_SIZE=64 \
    /usr/bin/time -f '%U\t%S\t%M\t%x' -o "$timing_file" "$binary"
  end_ns=$(date +%s%N)
  wall_seconds=$(awk -v start="$start_ns" -v end="$end_ns" \
    'BEGIN {printf "%.9f", (end - start) / 1000000000}')
  printf '%s\t%s\t%s\t%s\t' "$pair" "$position" "$lane" "$wall_seconds" \
    >>"$run_directory/runs.tsv"
  sed -n '1p' "$timing_file" >>"$run_directory/runs.tsv"
  rm "$timing_file"
}

for pair in $(seq 1 "$pairs"); do
  if (( pair % 2 == 1 )); then
    run_lane "$pair" 1 baseline "$baseline_binary"
    run_lane "$pair" 2 flat "$flat_binary"
  else
    run_lane "$pair" 1 flat "$flat_binary"
    run_lane "$pair" 2 baseline "$baseline_binary"
  fi
done

awk -F '\t' '
  NR > 1 {
    count[$3] += 1; wall[$3] += $4; user[$3] += $5;
    system_time[$3] += $6; rss[$3] += $7;
    if ($8 != 0) bad[$3] += 1;
  }
  END {
    print "lane\truns\tmean_run_seconds\tmean_batch_seconds\tmean_user_seconds\tmean_system_seconds\tmean_rss_kib\tnonzero_exits";
    names[1] = "baseline"; names[2] = "flat";
    for (lane_index = 1; lane_index <= 2; ++lane_index) {
      lane = names[lane_index];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%.9f\t%.3f\t%d\n", lane,
        count[lane], wall[lane] / count[lane],
        wall[lane] / count[lane] / 1000, user[lane] / count[lane],
        system_time[lane] / count[lane], rss[lane] / count[lane],
        bad[lane] + 0;
    }
    baseline_mean = wall["baseline"] / count["baseline"];
    flat_mean = wall["flat"] / count["flat"];
    speedup = baseline_mean / flat_mean;
    printf "baseline_over_flat_speedup\t%d\t%.9f\t%.9f\t0\t0\t0\t0\n",
      count["baseline"], speedup, speedup;
  }
' "$run_directory/runs.tsv" >"$run_directory/summary.tsv"

sha256sum "$run_directory/manifest.txt" "$run_directory/runs.tsv" \
  "$run_directory/summary.tsv" >"$run_directory/SHA256SUMS"
cat "$run_directory/summary.tsv"
