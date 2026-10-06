#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  printf 'usage: %s NATIVE-INPUT-RUN-DIR OUTPUT-DIR REPETITIONS\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
input_dir=$1
output_dir=$2
repetitions=$3
source_file="$repo_root/tools/nl_native_fixed_scale_case10173.cc"
program="$input_dir/case10173-program.cval"
jobs="$input_dir/case10173-native-jobs-prefix128.tsv"
expected=/project/flyspeck-candle-runs/cv-case10173-bound-tightness-prefix128-v3-16g-dev-001/case10173-reflected-bounds-prefix128.tsv

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$source_file" ]]
[[ -f "$program" ]]
[[ -f "$jobs" ]]
[[ -f "$expected" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

total_begin=$(date +%s%N)
build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-fixed-scale-case10173"
build_end=$(date +%s%N)

summaries="$output_dir/summaries.txt"
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  "$output_dir/nl-native-fixed-scale-case10173" \
    "$program" "$jobs" "$expected" \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ repetition=$repetition/" >>"$summaries"
  "$output_dir/nl-native-fixed-scale-case10173" \
    "$program" "$jobs" "$expected" --specialized-angle-polynomials \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ repetition=$repetition/" >>"$summaries"
done
total_end=$(date +%s%N)

awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    mode = "";
    seconds = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "mode") mode = field[2];
      if (field[1] == "evaluation_seconds") seconds = field[2] + 0;
    }
    sum[mode] += seconds;
    count[mode] += 1;
  }
  END {
    baseline = sum["baseline"] / count["baseline"];
    candidate = sum["specialized-angle-polynomials"] / count["specialized-angle-polynomials"];
    print "lane\trepetitions\tmean_evaluation_seconds";
    printf "baseline\t%d\t%.9f\n", count["baseline"], baseline;
    printf "specialized-angle-polynomials\t%d\t%.9f\n",
      count["specialized-angle-polynomials"], candidate;
    printf "speedup\t%d\t%.9f\n", count["baseline"], baseline / candidate;
    printf "time_reduction_percent\t%d\t%.6f\n",
      count["baseline"], 100 * (baseline - candidate) / baseline;
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v build_begin="$build_begin" -v build_end="$build_end" \
    -v total_begin="$total_begin" -v total_end="$total_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build\t%.9f\n", (build_end - build_begin) / 1000000000;
    printf "total\t%.9f\n", (total_end - total_begin) / 1000000000;
  }
' >"$output_dir/wall-times.tsv"

sha256sum "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/nl-native-fixed-scale-case10173" "$summaries" \
  "$output_dir/phase-times.tsv" "$output_dir/wall-times.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIXED_SCALE_CASE10173_SPECIALIZED_ANGLE_PAIRED_OK DEVELOPMENT_NON_RELEASE'
