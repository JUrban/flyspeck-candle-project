#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 5 ]]; then
  printf 'usage: %s PROGRAM.cval JOBS.tsv EXPECTED.tsv OUTPUT-DIR REPETITIONS\n' "$0" >&2
  exit 2
fi

repo_root=$(cd "$(dirname "$0")/.." && pwd)
program=$1
jobs=$2
expected=$3
output_dir=$4
repetitions=$5
source_file="$repo_root/tools/nl_native_fixed_scale_case10173.cc"
payload_verifier="$repo_root/scripts/verify-nl-case10173-angle-payloads.py"
bound_analyzer="$repo_root/scripts/analyze-nl-case10173-fixed-result-pair.py"
historical_specialized_seconds=0.082490265

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$program" && -f "$jobs" && -f "$expected" && -f "$source_file" ]]
[[ -x "$payload_verifier" && -x "$bound_analyzer" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

"$payload_verifier" "$program" >"$output_dir/payload-identities.txt"
[[ $(wc -l <"$jobs") -eq 4173 ]]
[[ $(wc -l <"$expected") -eq 4173 ]]

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_DOUBLE=1 "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-double"
build_end=$(date +%s%N)

common_options=(
  --specialized-angle-polynomials
  --direct-delta-x4
  --symmetric-hessian-ops
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
  --prepared-simple-polynomials
  --prepared-coordinate-sqrt-terms
  --precompute-tight-sqrt-certificates
  --count-fixed-quotients
  --decimal-scale=10000000
  --fuse-consecutive-adds
  --defer-additive-leaf-completion
)

summaries="$output_dir/summaries.txt"
: >"$summaries"
run_lane() {
  local lane=$1
  local repetition=$2
  local options=("${common_options[@]}")
  if [[ "$lane" == unrounded-double ]]; then
    options+=(--unsafe-unrounded-hardware)
  elif [[ "$lane" != padded-double ]]; then
    printf 'unknown lane: %s\n' "$lane" >&2
    exit 2
  fi
  "$output_dir/nl-native-double" "$program" "$jobs" "$expected" \
    "${options[@]}" \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ lane=$lane repetition=$repetition/" >>"$summaries"
}

lanes=(padded-double unrounded-double)
for lane in "${lanes[@]}"; do
  run_lane "$lane" warmup
done
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_lane "$lane" "$repetition"
  done
done

for lane in "${lanes[@]}"; do
  options=("${common_options[@]}")
  if [[ "$lane" == unrounded-double ]]; then
    options+=(--unsafe-unrounded-hardware)
  fi
  "$output_dir/nl-native-double" "$program" "$jobs" "$expected" \
    "${options[@]}" >"$output_dir/$lane-results.txt"
  rg -q 'cells=4173 .*accepted=4173' "$output_dir/$lane-results.txt"
done

"$bound_analyzer" "$output_dir/padded-double-results.txt" \
  "$output_dir/unrounded-double-results.txt" \
  >"$output_dir/unrounded-vs-padded-bounds.json"

awk -v historical="$historical_specialized_seconds" '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    lane = ""; preparation = 0; evaluation = 0; accepted = 0;
    quotients = 0; products = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "lane") lane = field[2];
      if (field[1] == "preparation_seconds") preparation = field[2] + 0;
      if (field[1] == "evaluation_seconds") evaluation = field[2] + 0;
      if (field[1] == "evaluation_floor_quotients" ||
          field[1] == "evaluation_ceil_quotients") quotients += field[2] + 0;
      if (field[1] == "interval_products") products = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
    }
    preparation_sum[lane] += preparation;
    evaluation_sum[lane] += evaluation;
    quotient_sum[lane] += quotients;
    product_sum[lane] += products;
    count[lane] += 1;
    if (count[lane] == 1 || accepted < minimum_accepted[lane]) {
      minimum_accepted[lane] = accepted;
    }
  }
  END {
    print "lane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tmean_quotients\tmean_interval_products\tminimum_accepted";
    for (lane_index = 1; lane_index <= 2; ++lane_index) {
      lane = lane_index == 1 ? "padded-double" : "unrounded-double";
      p = preparation_sum[lane] / count[lane];
      e = evaluation_sum[lane] / count[lane];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%.0f\t%.0f\t%d\n", lane, count[lane], p, e, p + e, quotient_sum[lane] / count[lane], product_sum[lane] / count[lane], minimum_accepted[lane];
    }
    pe = evaluation_sum["padded-double"] / count["padded-double"];
    ue = evaluation_sum["unrounded-double"] / count["unrounded-double"];
    pp = preparation_sum["padded-double"] / count["padded-double"];
    up = preparation_sum["unrounded-double"] / count["unrounded-double"];
    printf "unrounded_evaluation_speedup\t%d\t0\t%.9f\t0\t0\t0\t%d\n", count["unrounded-double"], pe / ue, minimum_accepted["unrounded-double"];
    printf "unrounded_batch_speedup\t%d\t0\t0\t%.9f\t0\t0\t%d\n", count["unrounded-double"], (pp + pe) / (up + ue), minimum_accepted["unrounded-double"];
    printf "padded_double_over_cpp_specialized\t%d\t0\t%.9f\t0\t0\t0\t%d\n", count["padded-double"], pe / historical, minimum_accepted["padded-double"];
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v build_begin="$build_begin" -v build_end="$build_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build_double\t%.9f\n", (build_end - build_begin) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$source_file" "$payload_verifier" "$bound_analyzer" \
  "$program" "$jobs" "$expected" "$output_dir/payload-identities.txt" \
  "$output_dir/nl-native-double" "$summaries" \
  "$output_dir/padded-double-results.txt" \
  "$output_dir/unrounded-double-results.txt" \
  "$output_dir/unrounded-vs-padded-bounds.json" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_DOUBLE_ROUNDING_PAIRED_OK DEVELOPMENT_NON_RELEASE'
