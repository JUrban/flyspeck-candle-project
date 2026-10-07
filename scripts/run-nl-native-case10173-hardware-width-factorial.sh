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
  -DCANDLE_NL_FIXED_LONG_DOUBLE=1 "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-long-double"
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
  --unsafe-unrounded-hardware
)
historical_options=(
  --historical-dihedral
  --historical-block-rounding
  --historical-center-tangent
)

lane_backend() {
  case "$1" in
    long-generic|long-historical) printf '%s\n' long-double ;;
    double-generic|double-historical) printf '%s\n' double ;;
    *) return 2 ;;
  esac
}

summaries="$output_dir/summaries.txt"
: >"$summaries"
run_lane() {
  local lane=$1
  local repetition=$2
  local backend
  backend=$(lane_backend "$lane")
  local options=("${common_options[@]}")
  if [[ "$lane" == *-historical ]]; then
    options+=("${historical_options[@]}")
  fi
  "$output_dir/nl-native-$backend" "$program" "$jobs" "$expected" \
    "${options[@]}" \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ lane=$lane repetition=$repetition/" >>"$summaries"
}

lanes=(long-generic double-generic long-historical double-historical)
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

: >"$output_dir/peak-rss-kb.tsv"
printf 'lane\tpeak_rss_kb\n' >>"$output_dir/peak-rss-kb.tsv"
for lane in "${lanes[@]}"; do
  backend=$(lane_backend "$lane")
  options=("${common_options[@]}")
  if [[ "$lane" == *-historical ]]; then
    options+=("${historical_options[@]}")
  fi
  /usr/bin/time -f '%M' -o "$output_dir/$lane-peak-rss-kb.txt" \
    "$output_dir/nl-native-$backend" "$program" "$jobs" "$expected" \
    "${options[@]}" >"$output_dir/$lane-results.txt"
  rg -q 'cells=4173 .*accepted=4173' "$output_dir/$lane-results.txt"
  printf '%s\t%s\n' "$lane" \
    "$(cat "$output_dir/$lane-peak-rss-kb.txt")" \
    >>"$output_dir/peak-rss-kb.tsv"
done

"$bound_analyzer" "$output_dir/long-generic-results.txt" \
  "$output_dir/double-generic-results.txt" \
  >"$output_dir/double-vs-long-generic-bounds.json"
"$bound_analyzer" "$output_dir/long-historical-results.txt" \
  "$output_dir/double-historical-results.txt" \
  >"$output_dir/double-vs-long-historical-bounds.json"
"$bound_analyzer" "$output_dir/double-generic-results.txt" \
  "$output_dir/double-historical-results.txt" \
  >"$output_dir/historical-vs-generic-double-bounds.json"

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
    for (lane_index = 1; lane_index <= 4; ++lane_index) {
      lane = lane_index == 1 ? "long-generic" : lane_index == 2 ? "double-generic" : lane_index == 3 ? "long-historical" : "double-historical";
      p = preparation_sum[lane] / count[lane];
      e = evaluation_sum[lane] / count[lane];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%.0f\t%.0f\t%d\n", lane, count[lane], p, e, p + e, quotient_sum[lane] / count[lane], product_sum[lane] / count[lane], minimum_accepted[lane];
    }
    lg = evaluation_sum["long-generic"] / count["long-generic"];
    dg = evaluation_sum["double-generic"] / count["double-generic"];
    lh = evaluation_sum["long-historical"] / count["long-historical"];
    dh = evaluation_sum["double-historical"] / count["double-historical"];
    printf "double_over_long_generic_speedup\t%d\t0\t%.9f\t0\t0\t0\t%d\n", count["double-generic"], lg / dg, minimum_accepted["double-generic"];
    printf "double_over_long_historical_speedup\t%d\t0\t%.9f\t0\t0\t0\t%d\n", count["double-historical"], lh / dh, minimum_accepted["double-historical"];
    printf "generic_over_historical_double_speedup\t%d\t0\t%.9f\t0\t0\t0\t%d\n", count["double-historical"], dg / dh, minimum_accepted["double-historical"];
    printf "double_generic_over_cpp_specialized\t%d\t0\t%.9f\t0\t0\t0\t%d\n", count["double-generic"], dg / historical, minimum_accepted["double-generic"];
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v build_begin="$build_begin" -v build_end="$build_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build_two_hardware_backends\t%.9f\n", (build_end - build_begin) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$source_file" "$payload_verifier" "$bound_analyzer" \
  "$program" "$jobs" "$expected" "$output_dir/payload-identities.txt" \
  "$output_dir/nl-native-long-double" "$output_dir/nl-native-double" \
  "$summaries" "$output_dir/long-generic-results.txt" \
  "$output_dir/double-generic-results.txt" \
  "$output_dir/long-historical-results.txt" \
  "$output_dir/double-historical-results.txt" \
  "$output_dir/double-vs-long-generic-bounds.json" \
  "$output_dir/double-vs-long-historical-bounds.json" \
  "$output_dir/historical-vs-generic-double-bounds.json" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  "$output_dir/peak-rss-kb.tsv" >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_HARDWARE_WIDTH_FACTORIAL_OK DEVELOPMENT_NON_RELEASE'
