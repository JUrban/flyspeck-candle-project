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
  -DCANDLE_NL_FIXED_INT256=1 -I"$boost_include" "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-fixed-scale-fixed256"
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
  local backend=$1
  local repetition=$2
  "$output_dir/nl-native-fixed-scale-$backend" \
    "$program" "$jobs" "$expected" "${common_options[@]}" \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ repetition=$repetition/" >>"$summaries"
}

run_lane fixed256 warmup
run_lane checked128 warmup
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    run_lane fixed256 "$repetition"
    run_lane checked128 "$repetition"
  else
    run_lane checked128 "$repetition"
    run_lane fixed256 "$repetition"
  fi
done

"$output_dir/nl-native-fixed-scale-fixed256" \
  "$program" "$jobs" "$expected" "${common_options[@]}" \
  | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
  >"$output_dir/fixed256-results.txt"
"$output_dir/nl-native-fixed-scale-checked128" \
  "$program" "$jobs" "$expected" "${common_options[@]}" \
  | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
  >"$output_dir/checked128-results.txt"
cmp "$output_dir/fixed256-results.txt" "$output_dir/checked128-results.txt"

set +e
"$output_dir/nl-native-fixed-scale-checked128" \
  "$program" "$jobs" "$expected" \
  --specialized-angle-polynomials --direct-delta-x4 \
  --skip-exact-zero-products --symmetric-hessian-ops \
  --decimal-scale=1000000000000 \
  >"$output_dir/checked128-scale1e12.stdout" \
  2>"$output_dir/checked128-scale1e12.stderr"
scale1e12_status=$?
set -e
[[ "$scale1e12_status" -ne 0 ]]
rg -x 'native fixed-scale comparison failed: overflow in multiplication' \
  "$output_dir/checked128-scale1e12.stderr" >/dev/null
printf '%d\n' "$scale1e12_status" \
  >"$output_dir/checked128-scale1e12.exit-status"
total_end=$(date +%s%N)

awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    backend = "";
    preparation = 0;
    seconds = 0;
    accepted = 0;
    matched = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "backend") backend = field[2];
      if (field[1] == "preparation_seconds") preparation = field[2] + 0;
      if (field[1] == "evaluation_seconds") seconds = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
      if (field[1] == "matched") matched = field[2] + 0;
    }
    sum[backend] += seconds;
    preparation_sum[backend] += preparation;
    count[backend] += 1;
    if (accepted < min_accepted[backend] || count[backend] == 1) {
      min_accepted[backend] = accepted;
    }
    if (matched < min_matched[backend] || count[backend] == 1) {
      min_matched[backend] = matched;
    }
  }
  END {
    fixed256 = sum["fixed-int256"] / count["fixed-int256"];
    checked128 = sum["checked-int128"] / count["checked-int128"];
    fixed256_preparation = preparation_sum["fixed-int256"] / count["fixed-int256"];
    checked128_preparation = preparation_sum["checked-int128"] / count["checked-int128"];
    print "backend\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tmin_matched\tmin_accepted";
    printf "fixed-int256\t%d\t%.9f\t%.9f\t%.9f\t%d\t%d\n",
      count["fixed-int256"], fixed256_preparation, fixed256,
      fixed256_preparation + fixed256,
      min_matched["fixed-int256"], min_accepted["fixed-int256"];
    printf "checked-int128\t%d\t%.9f\t%.9f\t%.9f\t%d\t%d\n",
      count["checked-int128"], checked128_preparation, checked128,
      checked128_preparation + checked128,
      min_matched["checked-int128"], min_accepted["checked-int128"];
    printf "checked-int128-evaluation-speedup\t%d\t0\t%.9f\t0\t%d\t%d\n",
      count["fixed-int256"], fixed256 / checked128,
      min_matched["checked-int128"], min_accepted["checked-int128"];
    printf "checked-int128-batch-speedup\t%d\t0\t0\t%.9f\t%d\t%d\n",
      count["fixed-int256"],
      (fixed256_preparation + fixed256) / (checked128_preparation + checked128),
      min_matched["checked-int128"], min_accepted["checked-int128"];
    printf "evaluation_time_reduction_percent\t%d\t0\t%.6f\t0\t%d\t%d\n",
      count["fixed-int256"], 100 * (fixed256 - checked128) / fixed256,
      min_matched["checked-int128"], min_accepted["checked-int128"];
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
  "$output_dir/nl-native-fixed-scale-fixed256" \
  "$output_dir/nl-native-fixed-scale-checked128" "$summaries" \
  "$output_dir/phase-times.tsv" "$output_dir/wall-times.tsv" \
  "$output_dir/fixed256-results.txt" "$output_dir/checked128-results.txt" \
  "$output_dir/checked128-scale1e12.stdout" \
  "$output_dir/checked128-scale1e12.stderr" \
  "$output_dir/checked128-scale1e12.exit-status" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIXED_SCALE_CASE10173_CHECKED128_PAIRED_OK DEVELOPMENT_NON_RELEASE'
