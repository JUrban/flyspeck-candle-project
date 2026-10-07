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
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_INT256=1 -I"$boost_include" "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-fixed-scale-fixed256"
build_end=$(date +%s%N)

summaries="$output_dir/summaries.txt"
: >"$summaries"

run_lane() {
  local symmetric=$1
  local repetition=$2
  local -a options=(
    --specialized-angle-polynomials
    --direct-delta-x4
    --skip-exact-zero-products
  )
  if [[ "$symmetric" == 1 ]]; then
    options+=(--symmetric-hessian-ops)
  fi
  "$output_dir/nl-native-fixed-scale-fixed256" \
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

"$output_dir/nl-native-fixed-scale-fixed256" \
  "$program" "$jobs" "$expected" \
  --specialized-angle-polynomials --direct-delta-x4 \
  --skip-exact-zero-products \
  | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
  >"$output_dir/dense-results.txt"
"$output_dir/nl-native-fixed-scale-fixed256" \
  "$program" "$jobs" "$expected" \
  --specialized-angle-polynomials --direct-delta-x4 \
  --skip-exact-zero-products --symmetric-hessian-ops \
  | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
  >"$output_dir/symmetric-results.txt"
cmp "$output_dir/dense-results.txt" "$output_dir/symmetric-results.txt"
total_end=$(date +%s%N)

awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    symmetric = "";
    seconds = 0;
    accepted = 0;
    matched = 0;
    products = 0;
    skipped = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "symmetric_hessian_ops") symmetric = field[2];
      if (field[1] == "evaluation_seconds") seconds = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
      if (field[1] == "matched") matched = field[2] + 0;
      if (field[1] == "interval_products") products = field[2] + 0;
      if (field[1] == "skipped_zero_products") skipped = field[2] + 0;
    }
    sum[symmetric] += seconds;
    count[symmetric] += 1;
    product_sum[symmetric] += products;
    skipped_sum[symmetric] += skipped;
    if (accepted < min_accepted[symmetric] || count[symmetric] == 1) {
      min_accepted[symmetric] = accepted;
    }
    if (matched < min_matched[symmetric] || count[symmetric] == 1) {
      min_matched[symmetric] = matched;
    }
  }
  END {
    dense = sum["0"] / count["0"];
    symmetric = sum["1"] / count["1"];
    print "symmetric_hessian_ops\trepetitions\tmean_evaluation_seconds\tmin_matched\tmin_accepted\tmean_products\tmean_skipped_products";
    printf "0\t%d\t%.9f\t%d\t%d\t%.0f\t%.0f\n",
      count["0"], dense, min_matched["0"], min_accepted["0"],
      product_sum["0"] / count["0"], skipped_sum["0"] / count["0"];
    printf "1\t%d\t%.9f\t%d\t%d\t%.0f\t%.0f\n",
      count["1"], symmetric, min_matched["1"], min_accepted["1"],
      product_sum["1"] / count["1"], skipped_sum["1"] / count["1"];
    printf "speedup\t%d\t%.9f\t%d\t%d\t%.0f\t%.0f\n",
      count["0"], dense / symmetric, min_matched["1"],
      min_accepted["1"], product_sum["1"] / count["1"],
      skipped_sum["1"] / count["1"];
    printf "time_reduction_percent\t%d\t%.6f\t%d\t%d\t%.0f\t%.0f\n",
      count["0"], 100 * (dense - symmetric) / dense,
      min_matched["1"], min_accepted["1"],
      product_sum["1"] / count["1"], skipped_sum["1"] / count["1"];
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
  "$output_dir/nl-native-fixed-scale-fixed256" "$summaries" \
  "$output_dir/phase-times.tsv" "$output_dir/wall-times.tsv" \
  "$output_dir/dense-results.txt" "$output_dir/symmetric-results.txt" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIXED_SCALE_CASE10173_FIXED256_SYMMETRIC_HESSIAN_PAIRED_OK DEVELOPMENT_NON_RELEASE'
