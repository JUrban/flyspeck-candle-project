#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 || $# -gt 6 ]]; then
  printf 'usage: %s PROGRAM.cval JOBS.tsv EXPECTED.tsv OUTPUT-DIR [BENCH-REPETITIONS] [RUNS]\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
program=$1
jobs=$2
expected=$3
output_dir=$4
benchmark_repetitions=${5:-10000}
runs=${6:-7}
source_file="$repo_root/tools/nl_native_fixed_scale_case10173.cc"
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}

for input in "$program" "$jobs" "$expected" "$source_file"; do
  [[ -f "$input" ]]
done
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ "$benchmark_repetitions" =~ ^[1-9][0-9]*$ ]]
[[ "$runs" =~ ^[1-9][0-9]*$ ]]
[[ $(wc -l <"$jobs") -eq 875 ]]
[[ $(wc -l <"$expected") -eq 875 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include" \
  -DCANDLE_NL_FIXED_INT128=1 -DCANDLE_NL_MIXED_NATIVE_INT128_192=1 \
  -DCANDLE_NL_CASE_ID=16594 -DCANDLE_NL_SQRT_SLOTS=10 \
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167 \
  "$source_file" -lgmpxx -lgmp -o "$output_dir/nl-native"
build_end=$(date +%s%N)

options=(--binary-scale-bits=40 --dyadic-shift-fixed-quotient \
  "--delta-gradient0-benchmark-repetitions=$benchmark_repetitions")

# Untimed warm-up also verifies the complete 875-result digest.
"$output_dir/nl-native" "$program" "$jobs" "$expected" \
  "${options[@]}" >/dev/null

: >"$output_dir/summaries.txt"
printf 'run\twall_seconds\tuser_seconds\tsystem_seconds\tmaximum_rss_kib\texit\n' \
  >"$output_dir/runs.tsv"
for run in $(seq 1 "$runs"); do
  timing_file="$output_dir/.timing-$run"
  start_ns=$(date +%s%N)
  /usr/bin/time -f '%U\t%S\t%M\t%x' -o "$timing_file" \
    "$output_dir/nl-native" "$program" "$jobs" "$expected" \
    "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_DELTA_GRADIENT0_SUMMARY' |
    sed "s/$/ run=$run/" >>"$output_dir/summaries.txt"
  end_ns=$(date +%s%N)
  wall_seconds=$(awk -v start="$start_ns" -v end="$end_ns" \
    'BEGIN {printf "%.9f", (end - start) / 1000000000}')
  printf '%s\t%s\t' "$run" "$wall_seconds" >>"$output_dir/runs.tsv"
  sed -n '1p' "$timing_file" >>"$output_dir/runs.tsv"
  rm "$timing_file"
done

awk '
  function value(name, i, field) {
    for (i = 1; i <= NF; ++i) {
      split($i, field, "="); if (field[1] == name) return field[2]
    }
  }
  {
    count += 1
    preparation += value("preparation_seconds")
    evaluation += value("mean_evaluation_seconds")
    if (value("cells") != 875 || value("digest") != 111527807236922) bad += 1
  }
  END {
    print "runs\tbenchmark_repetitions\tmean_preparation_seconds\tmean_batch_evaluation_seconds\tbad_results"
    printf "%d\t%d\t%.9f\t%.9f\t%d\n", count, '"$benchmark_repetitions"',
      preparation / count, evaluation / count, bad + 0
  }
' "$output_dir/summaries.txt" >"$output_dir/summary.tsv"

awk -v begin="$build_begin" -v end="$build_end" 'BEGIN {
  print "phase\tseconds"
  printf "native_build\t%.9f\n", (end - begin) / 1000000000
}' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/nl-native" "$output_dir/summaries.txt" \
  "$output_dir/runs.tsv" "$output_dir/summary.tsv" \
  "$output_dir/one-time-costs.tsv" >"$output_dir/result-files.sha256"

cat "$output_dir/summary.tsv"
