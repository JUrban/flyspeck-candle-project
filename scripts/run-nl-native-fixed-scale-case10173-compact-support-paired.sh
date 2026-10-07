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
comparison_scale=10000000000

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
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_CHECKED_INT128=1 -I"$boost_include" "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-fixed-scale-checked128"
build_end=$(date +%s%N)

common_options=(
  --specialized-angle-polynomials
  --direct-delta-x4
  --skip-exact-zero-products
  --symmetric-hessian-ops
  --decimal-scale="$comparison_scale"
)

summaries="$output_dir/summaries.txt"
: >"$summaries"

run_lane() {
  local compact=$1
  local repetition=$2
  local options=("${common_options[@]}")
  if [[ "$compact" == 1 ]]; then
    options+=(--compact-support-jets)
  fi
  "$output_dir/nl-native-fixed-scale-checked128" \
    "$program" "$jobs" "$expected" "${options[@]}" \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ repetition=$repetition/" >>"$summaries"
}

run_lane 0 warmup
run_lane 1 warmup
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    run_lane 0 "$repetition"
    run_lane 1 "$repetition"
  else
    run_lane 1 "$repetition"
    run_lane 0 "$repetition"
  fi
done

"$output_dir/nl-native-fixed-scale-checked128" \
  "$program" "$jobs" "$expected" "${common_options[@]}" \
  | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
  >"$output_dir/dense-results.txt"
"$output_dir/nl-native-fixed-scale-checked128" \
  "$program" "$jobs" "$expected" "${common_options[@]}" \
  --compact-support-jets \
  | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
  >"$output_dir/compact-results.txt"
cmp "$output_dir/dense-results.txt" "$output_dir/compact-results.txt"
total_end=$(date +%s%N)

awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    compact = "";
    preparation = 0;
    seconds = 0;
    accepted = 0;
    products = 0;
    skipped = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "compact_support_jets") compact = field[2];
      if (field[1] == "preparation_seconds") preparation = field[2] + 0;
      if (field[1] == "evaluation_seconds") seconds = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
      if (field[1] == "interval_products") products = field[2] + 0;
      if (field[1] == "skipped_zero_products") skipped = field[2] + 0;
    }
    sum[compact] += seconds;
    preparation_sum[compact] += preparation;
    count[compact] += 1;
    product_sum[compact] += products;
    skipped_sum[compact] += skipped;
    if (accepted < min_accepted[compact] || count[compact] == 1) {
      min_accepted[compact] = accepted;
    }
  }
  END {
    dense = sum["0"] / count["0"];
    compact = sum["1"] / count["1"];
    dense_preparation = preparation_sum["0"] / count["0"];
    compact_preparation = preparation_sum["1"] / count["1"];
    print "lane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tmin_accepted\tmean_products\tmean_skipped_zero_products";
    printf "dense-symmetric\t%d\t%.9f\t%.9f\t%.9f\t%d\t%.0f\t%.0f\n",
      count["0"], dense_preparation, dense,
      dense_preparation + dense, min_accepted["0"],
      product_sum["0"] / count["0"], skipped_sum["0"] / count["0"];
    printf "compact-support\t%d\t%.9f\t%.9f\t%.9f\t%d\t%.0f\t%.0f\n",
      count["1"], compact_preparation, compact,
      compact_preparation + compact, min_accepted["1"],
      product_sum["1"] / count["1"], skipped_sum["1"] / count["1"];
    printf "compact-evaluation-speedup\t%d\t0\t%.9f\t0\t%d\t0\t0\n",
      count["0"], dense / compact, min_accepted["1"];
    printf "compact-batch-speedup\t%d\t0\t0\t%.9f\t%d\t0\t0\n",
      count["0"],
      (dense_preparation + dense) / (compact_preparation + compact),
      min_accepted["1"];
    printf "evaluation-time-reduction-percent\t%d\t0\t%.6f\t0\t%d\t0\t0\n",
      count["0"], 100 * (dense - compact) / dense,
      min_accepted["1"];
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
  "$output_dir/nl-native-fixed-scale-checked128" "$summaries" \
  "$output_dir/phase-times.tsv" "$output_dir/wall-times.tsv" \
  "$output_dir/dense-results.txt" "$output_dir/compact-results.txt" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIXED_SCALE_CASE10173_COMPACT_SUPPORT_PAIRED_OK DEVELOPMENT_NON_RELEASE'
