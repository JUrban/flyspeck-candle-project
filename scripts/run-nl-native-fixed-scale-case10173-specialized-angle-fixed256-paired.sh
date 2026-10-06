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
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$source_file" ]]
[[ -f "$program" ]]
[[ -f "$jobs" ]]
[[ -f "$expected" ]]
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

total_begin=$(date +%s%N)
build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-fixed-scale-mpz"
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_INT256=1 -I"$boost_include" "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-fixed-scale-fixed256"
build_end=$(date +%s%N)

summaries="$output_dir/summaries.txt"
: >"$summaries"

run_lane() {
  local backend=$1
  local repetition=$2
  "$output_dir/nl-native-fixed-scale-$backend" \
    "$program" "$jobs" "$expected" --specialized-angle-polynomials \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ repetition=$repetition/" >>"$summaries"
}

# Warm both binaries before the alternating paired measurement.
run_lane mpz warmup
run_lane fixed256 warmup
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    run_lane mpz "$repetition"
    run_lane fixed256 "$repetition"
  else
    run_lane fixed256 "$repetition"
    run_lane mpz "$repetition"
  fi
done
total_end=$(date +%s%N)

awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    backend = "";
    seconds = 0;
    accepted = 0;
    matched = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "backend") backend = field[2];
      if (field[1] == "evaluation_seconds") seconds = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
      if (field[1] == "matched") matched = field[2] + 0;
    }
    sum[backend] += seconds;
    count[backend] += 1;
    if (accepted < min_accepted[backend] || count[backend] == 1) {
      min_accepted[backend] = accepted;
    }
    if (matched < min_matched[backend] || count[backend] == 1) {
      min_matched[backend] = matched;
    }
  }
  END {
    mpz = sum["mpz"] / count["mpz"];
    fixed = sum["fixed-int256"] / count["fixed-int256"];
    print "backend\trepetitions\tmean_evaluation_seconds\tmin_matched\tmin_accepted";
    printf "mpz\t%d\t%.9f\t%d\t%d\n",
      count["mpz"], mpz, min_matched["mpz"], min_accepted["mpz"];
    printf "fixed-int256\t%d\t%.9f\t%d\t%d\n",
      count["fixed-int256"], fixed,
      min_matched["fixed-int256"], min_accepted["fixed-int256"];
    printf "fixed-int256-speedup\t%d\t%.9f\t%d\t%d\n",
      count["mpz"], mpz / fixed,
      min_matched["fixed-int256"], min_accepted["fixed-int256"];
    printf "time_reduction_percent\t%d\t%.6f\t%d\t%d\n",
      count["mpz"], 100 * (mpz - fixed) / mpz,
      min_matched["fixed-int256"], min_accepted["fixed-int256"];
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
  "$output_dir/nl-native-fixed-scale-mpz" \
  "$output_dir/nl-native-fixed-scale-fixed256" "$summaries" \
  "$output_dir/phase-times.tsv" "$output_dir/wall-times.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIXED_SCALE_CASE10173_SPECIALIZED_ANGLE_FIXED256_PAIRED_OK DEVELOPMENT_NON_RELEASE'
