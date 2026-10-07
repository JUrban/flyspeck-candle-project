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
payload_verifier="$repo_root/scripts/verify-nl-case10173-angle-payloads.py"
program="$input_dir/case10173-program.cval"
jobs="$input_dir/case10173-native-jobs-prefix128.tsv"
expected=/project/flyspeck-candle-runs/cv-case10173-bound-tightness-prefix128-v3-16g-dev-001/case10173-reflected-bounds-prefix128.tsv
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}
comparison_scale=10000000000

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$source_file" && -x "$payload_verifier" ]]
[[ -f "$program" && -f "$jobs" && -f "$expected" ]]
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

"$payload_verifier" "$program" >"$output_dir/payload-identities.txt"
total_begin=$(date +%s%N)
build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_CHECKED_INT128=1 -I"$boost_include" "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-fixed-scale-checked128"
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_INT256=1 -I"$boost_include" "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-fixed-scale-fixed256"
build_end=$(date +%s%N)

common_options=(
  --specialized-angle-polynomials
  --direct-delta-x4
  --skip-exact-zero-products
  --symmetric-hessian-ops
  --decimal-scale="$comparison_scale"
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
  --prepared-simple-polynomials
)

summaries="$output_dir/summaries.txt"
: >"$summaries"
run_lane() {
  local lane=$1
  local repetition=$2
  local options=("${common_options[@]}")
  if [[ "$lane" == coordinate-sqrt ]]; then
    options+=(--prepared-coordinate-sqrt-terms)
  fi
  "$output_dir/nl-native-fixed-scale-checked128" \
    "$program" "$jobs" "$expected" "${options[@]}" \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ lane=$lane repetition=$repetition/" >>"$summaries"
}

run_lane prepared-simple warmup
run_lane coordinate-sqrt warmup
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  if ((repetition % 2 == 1)); then
    run_lane prepared-simple "$repetition"
    run_lane coordinate-sqrt "$repetition"
  else
    run_lane coordinate-sqrt "$repetition"
    run_lane prepared-simple "$repetition"
  fi
done

"$output_dir/nl-native-fixed-scale-checked128" \
  "$program" "$jobs" "$expected" "${common_options[@]}" \
  | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
  >"$output_dir/prepared-simple-results.txt"
"$output_dir/nl-native-fixed-scale-checked128" \
  "$program" "$jobs" "$expected" "${common_options[@]}" \
  --prepared-coordinate-sqrt-terms \
  | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
  >"$output_dir/coordinate-sqrt-results.txt"
cmp "$output_dir/prepared-simple-results.txt" \
    "$output_dir/coordinate-sqrt-results.txt"

"$output_dir/nl-native-fixed-scale-checked128" \
  "$program" "$jobs" "$expected" "${common_options[@]}" \
  --prepared-coordinate-sqrt-terms --verify-fixed-kernel-enclosures \
  >"$output_dir/coordinate-sqrt-crosscheck.txt"
rg -q 'verify_fixed_kernel_enclosures=1 .*prepared_coordinate_sqrt_term_count=6 .*accepted=128' \
  "$output_dir/coordinate-sqrt-crosscheck.txt"

fixed256_options=(
  --specialized-angle-polynomials
  --direct-delta-x4
  --skip-exact-zero-products
  --symmetric-hessian-ops
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
  --prepared-simple-polynomials
)
"$output_dir/nl-native-fixed-scale-fixed256" \
  "$program" "$jobs" "$expected" "${fixed256_options[@]}" \
  | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
  >"$output_dir/fixed256-control-results.txt"
"$output_dir/nl-native-fixed-scale-fixed256" \
  "$program" "$jobs" "$expected" "${fixed256_options[@]}" \
  --prepared-coordinate-sqrt-terms --verify-fixed-kernel-enclosures \
  >"$output_dir/fixed256-coordinate-sqrt-crosscheck.txt"
rg -q 'verify_fixed_kernel_enclosures=1 .*prepared_coordinate_sqrt_term_count=6 .*accepted=128' \
  "$output_dir/fixed256-coordinate-sqrt-crosscheck.txt"
rg 'CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
  "$output_dir/fixed256-coordinate-sqrt-crosscheck.txt" \
  >"$output_dir/fixed256-coordinate-sqrt-results.txt"
cmp "$output_dir/fixed256-control-results.txt" \
    "$output_dir/fixed256-coordinate-sqrt-results.txt"

awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    lane = ""; preparation = 0; seconds = 0; accepted = 0; terms = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "lane") lane = field[2];
      if (field[1] == "preparation_seconds") preparation = field[2] + 0;
      if (field[1] == "evaluation_seconds") seconds = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
      if (field[1] == "prepared_coordinate_sqrt_term_count") terms = field[2] + 0;
    }
    preparation_sum[lane] += preparation; sum[lane] += seconds; count[lane] += 1;
    if (accepted < min_accepted[lane] || count[lane] == 1) min_accepted[lane] = accepted;
    if (terms > max_terms[lane]) max_terms[lane] = terms;
  }
  END {
    bp = preparation_sum["prepared-simple"] / count["prepared-simple"];
    be = sum["prepared-simple"] / count["prepared-simple"];
    cp = preparation_sum["coordinate-sqrt"] / count["coordinate-sqrt"];
    ce = sum["coordinate-sqrt"] / count["coordinate-sqrt"];
    print "lane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tmin_accepted\tprepared_coordinate_sqrt_terms";
    printf "prepared-simple\t%d\t%.9f\t%.9f\t%.9f\t%d\t%d\n", count["prepared-simple"], bp, be, bp + be, min_accepted["prepared-simple"], max_terms["prepared-simple"];
    printf "coordinate-sqrt\t%d\t%.9f\t%.9f\t%.9f\t%d\t%d\n", count["coordinate-sqrt"], cp, ce, cp + ce, min_accepted["coordinate-sqrt"], max_terms["coordinate-sqrt"];
    printf "evaluation-speedup\t%d\t0\t%.9f\t0\t%d\t%d\n", count["coordinate-sqrt"], be / ce, min_accepted["coordinate-sqrt"], max_terms["coordinate-sqrt"];
    printf "batch-speedup\t%d\t0\t0\t%.9f\t%d\t%d\n", count["coordinate-sqrt"], (bp + be) / (cp + ce), min_accepted["coordinate-sqrt"], max_terms["coordinate-sqrt"];
  }
' "$summaries" >"$output_dir/phase-times.tsv"

total_end=$(date +%s%N)
awk -v build_begin="$build_begin" -v build_end="$build_end" \
    -v total_begin="$total_begin" -v total_end="$total_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build\t%.9f\n", (build_end - build_begin) / 1000000000;
    printf "total\t%.9f\n", (total_end - total_begin) / 1000000000;
  }
' >"$output_dir/wall-times.tsv"

sha256sum "$source_file" "$payload_verifier" "$program" "$jobs" \
  "$expected" "$output_dir/payload-identities.txt" \
  "$output_dir/nl-native-fixed-scale-checked128" \
  "$output_dir/nl-native-fixed-scale-fixed256" "$summaries" \
  "$output_dir/phase-times.tsv" "$output_dir/wall-times.tsv" \
  "$output_dir/prepared-simple-results.txt" \
  "$output_dir/coordinate-sqrt-results.txt" \
  "$output_dir/coordinate-sqrt-crosscheck.txt" \
  "$output_dir/fixed256-control-results.txt" \
  "$output_dir/fixed256-coordinate-sqrt-results.txt" \
  "$output_dir/fixed256-coordinate-sqrt-crosscheck.txt" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_FIXED_SCALE_CASE10173_COORDINATE_SQRT_OK DEVELOPMENT_NON_RELEASE'
