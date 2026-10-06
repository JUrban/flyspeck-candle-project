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

run_lane() {
  local arithmetic=$1
  local repetition=$2
  local -a options=(--specialized-angle-polynomials)
  if [[ "$arithmetic" == dyadic-2^40 ]]; then
    options+=(--dyadic-scale)
  fi
  "$output_dir/nl-native-fixed-scale-case10173" \
    "$program" "$jobs" "$expected" "${options[@]}" \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ repetition=$repetition/" >>"$summaries"
}

# Do not charge first-touch library/runtime effects to either measured lane.
run_lane decimal-1e12 warmup
run_lane dyadic-2^40 warmup
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    run_lane decimal-1e12 "$repetition"
    run_lane dyadic-2^40 "$repetition"
  else
    run_lane dyadic-2^40 "$repetition"
    run_lane decimal-1e12 "$repetition"
  fi
done
total_end=$(date +%s%N)

awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    arithmetic = "";
    seconds = 0;
    accepted = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "arithmetic") arithmetic = field[2];
      if (field[1] == "evaluation_seconds") seconds = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
    }
    sum[arithmetic] += seconds;
    count[arithmetic] += 1;
    if (accepted < min_accepted[arithmetic] || count[arithmetic] == 1) {
      min_accepted[arithmetic] = accepted;
    }
  }
  END {
    decimal = sum["decimal-1e12"] / count["decimal-1e12"];
    dyadic = sum["dyadic-2^40"] / count["dyadic-2^40"];
    print "arithmetic\trepetitions\tmean_evaluation_seconds\tmin_accepted";
    printf "decimal-1e12\t%d\t%.9f\t%d\n",
      count["decimal-1e12"], decimal, min_accepted["decimal-1e12"];
    printf "dyadic-2^40\t%d\t%.9f\t%d\n",
      count["dyadic-2^40"], dyadic, min_accepted["dyadic-2^40"];
    printf "dyadic_speedup\t%d\t%.9f\t%d\n",
      count["decimal-1e12"], decimal / dyadic, min_accepted["dyadic-2^40"];
    printf "time_reduction_percent\t%d\t%.6f\t%d\n",
      count["decimal-1e12"], 100 * (decimal - dyadic) / decimal,
      min_accepted["dyadic-2^40"];
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
  'CANDLE_NL_NATIVE_FIXED_SCALE_CASE10173_SPECIALIZED_ANGLE_DYADIC_PAIRED_OK DEVELOPMENT_NON_RELEASE'
