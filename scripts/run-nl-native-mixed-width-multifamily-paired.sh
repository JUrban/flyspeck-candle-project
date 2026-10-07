#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 9 ]]; then
  printf 'usage: %s CASE16594-PROGRAM CASE16594-JOBS CASE16594-EXPECTED CASE10173-PROGRAM CASE10173-JOBS CASE10173-EXPECTED OUTPUT-DIR CASE16594-REPETITIONS CASE10173-REPETITIONS\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
case16594_program=$1
case16594_jobs=$2
case16594_expected=$3
case10173_program=$4
case10173_jobs=$5
case10173_expected=$6
output_dir=$7
case16594_repetitions=$8
case10173_repetitions=$9
source_file="$repo_root/tools/nl_native_fixed_scale_case10173.cc"
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}

for input in "$case16594_program" "$case16594_jobs" \
  "$case16594_expected" "$case10173_program" "$case10173_jobs" \
  "$case10173_expected" "$source_file"; do
  [[ -f "$input" ]]
done
[[ "$case16594_repetitions" =~ ^[1-9][0-9]*$ ]]
[[ "$case10173_repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ $(wc -l <"$case16594_jobs") -eq 875 ]]
[[ $(wc -l <"$case10173_jobs") -eq 4173 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

common=(-std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include")
case16594_defines=(
  -DCANDLE_NL_CASE_ID=16594
  -DCANDLE_NL_SQRT_SLOTS=10
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167
)

build_begin=$(date +%s%N)
for backend in mixed checked256; do
  if [[ "$backend" == mixed ]]; then
    define=-DCANDLE_NL_MIXED_INT128_192=1
  else
    define=-DCANDLE_NL_CHECKED_INT256=1
  fi
  g++ "${common[@]}" "$define" "${case16594_defines[@]}" "$source_file" \
    -lgmpxx -lgmp -o "$output_dir/case16594-$backend"
  eval "build_case16594_${backend}_end=$(date +%s%N)"
  g++ "${common[@]}" "$define" "$source_file" -lgmpxx -lgmp \
    -o "$output_dir/case10173-$backend"
  eval "build_case10173_${backend}_end=$(date +%s%N)"
done

case16594_options=(
  --accept-only
  --count-fixed-quotients
  --binary-scale-bits=40
  --dyadic-shift-fixed-quotient
)
case10173_options=(
  --accept-only
  --count-fixed-quotients
  --binary-scale-bits=23
  --dyadic-shift-fixed-quotient
  --skip-exact-zero-products
  --symmetric-hessian-ops
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
  --prepared-simple-polynomials
  --prepared-coordinate-sqrt-terms
  --computed-tight-sqrt-certificates
  --specialized-angle-polynomials
  --direct-delta-x4
)

summaries="$output_dir/summaries.txt"
: >"$summaries"

run_lane() {
  local family=$1 backend=$2 repetition=$3 destination=$4
  local binary program jobs expected
  local -a options
  if [[ "$family" == case16594 ]]; then
    binary="$output_dir/case16594-$backend"
    program=$case16594_program
    jobs=$case16594_jobs
    expected=$case16594_expected
    options=("${case16594_options[@]}")
  else
    binary="$output_dir/case10173-$backend"
    program=$case10173_program
    jobs=$case10173_jobs
    expected=$case10173_expected
    options=("${case10173_options[@]}")
  fi
  "$binary" "$program" "$jobs" "$expected" "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ family=$family lane=$backend repetition=$repetition/" \
      >>"$destination"
}

for family in case16594 case10173; do
  for backend in mixed checked256; do
    run_lane "$family" "$backend" warmup /dev/null
  done
  if [[ "$family" == case16594 ]]; then
    repetitions=$case16594_repetitions
  else
    repetitions=$case10173_repetitions
  fi
  for ((repetition = 1; repetition <= repetitions; ++repetition)); do
    if ((repetition % 2 == 1)); then
      order=(mixed checked256)
    else
      order=(checked256 mixed)
    fi
    for backend in "${order[@]}"; do
      run_lane "$family" "$backend" "$repetition" "$summaries"
    done
  done
done

for family in case16594 case10173; do
  if [[ "$family" == case16594 ]]; then
    program=$case16594_program
    jobs=$case16594_jobs
    expected=$case16594_expected
    options=("${case16594_options[@]}")
  else
    program=$case10173_program
    jobs=$case10173_jobs
    expected=$case10173_expected
    options=("${case10173_options[@]}")
  fi
  for backend in mixed checked256; do
    /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M' \
      -o "$output_dir/$family-$backend-resource.txt" \
      "$output_dir/$family-$backend" "$program" "$jobs" "$expected" \
      "${options[@]}" >"$output_dir/$family-$backend-results.txt"
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
      "$output_dir/$family-$backend-results.txt" \
      >"$output_dir/$family-$backend-bounds.txt"
  done
  cmp "$output_dir/$family-mixed-bounds.txt" \
      "$output_dir/$family-checked256-bounds.txt"
done

rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=mixed-checked-int128-192 .*mixed_wide_taylor_completions=483000 mixed_wide_narrowings=966000 .*accepted=875' \
  "$output_dir/case16594-mixed-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=checked-int256 .*accepted=875' \
  "$output_dir/case16594-checked256-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=4173 .*backend=mixed-checked-int128-192 .*mixed_wide_taylor_completions=150228 mixed_wide_narrowings=300456 .*accepted=4173' \
  "$output_dir/case10173-mixed-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=4173 .*backend=checked-int256 .*accepted=4173' \
  "$output_dir/case10173-checked256-results.txt"

awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    family = lane = ""; preparation = evaluation = accepted = 0;
    for (i = 1; i <= NF; ++i) {
      split($i, field, "=");
      if (field[1] == "family") family = field[2];
      if (field[1] == "lane") lane = field[2];
      if (field[1] == "preparation_seconds") preparation = field[2] + 0;
      if (field[1] == "evaluation_seconds") evaluation = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
    }
    key = family SUBSEP lane;
    preparation_sum[key] += preparation;
    evaluation_sum[key] += evaluation;
    count[key]++;
    if (count[key] == 1 || accepted < minimum_accepted[key])
      minimum_accepted[key] = accepted;
  }
  END {
    print "family\tlane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted";
    families[1] = "case16594";
    families[2] = "case10173";
    lanes[1] = "mixed";
    lanes[2] = "checked256";
    for (f = 1; f <= 2; ++f) {
      family = families[f];
      for (l = 1; l <= 2; ++l) {
        lane = lanes[l];
        key = family SUBSEP lane;
        p = preparation_sum[key] / count[key];
        e = evaluation_sum[key] / count[key];
        printf "%s\t%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n", family, lane,
          count[key], p, e, p + e, minimum_accepted[key];
      }
      mixed_key = family SUBSEP "mixed";
      checked_key = family SUBSEP "checked256";
      mixed = evaluation_sum[mixed_key] / count[mixed_key];
      checked = evaluation_sum[checked_key] / count[checked_key];
      printf "%s\tchecked256_over_mixed\t%d\t0\t%.9f\t0\t0\n",
        family, count[mixed_key], checked / mixed;
    }
  }
' "$summaries" >"$output_dir/phase-times.tsv"

{
  printf 'metric\tseconds\n'
  awk -v begin="$build_begin" \
      -v a="$build_case16594_mixed_end" \
      -v b="$build_case10173_mixed_end" \
      -v c="$build_case16594_checked256_end" \
      -v d="$build_case10173_checked256_end" '
    BEGIN {
      printf "build_case16594_mixed\t%.9f\n", (a - begin) / 1000000000;
      printf "build_case10173_mixed\t%.9f\n", (b - a) / 1000000000;
      printf "build_case16594_checked256\t%.9f\n", (c - b) / 1000000000;
      printf "build_case10173_checked256\t%.9f\n", (d - c) / 1000000000;
    }
  '
} >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$case16594_program" "$case16594_jobs" \
  "$case16594_expected" "$case10173_program" "$case10173_jobs" \
  "$case10173_expected" "$output_dir/summaries.txt" \
  "$output_dir"/*-results.txt "$output_dir"/*-bounds.txt \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  >"$output_dir/result-files.sha256"

printf '%s\n' \
  'CANDLE_NL_NATIVE_MIXED_WIDTH_MULTIFAMILY_PAIRED_OK DEVELOPMENT_NON_RELEASE'
