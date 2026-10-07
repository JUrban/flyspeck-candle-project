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
result_analyzer="$repo_root/scripts/analyze-nl-case10173-fixed-result-pair.py"
historical_direct_seconds=0.060959726

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$program" && -f "$jobs" && -f "$expected" && -f "$source_file" ]]
[[ -x "$payload_verifier" && -x "$result_analyzer" ]]
[[ $(wc -l <"$jobs") -eq 4173 ]]
[[ $(wc -l <"$expected") -eq 4173 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

"$payload_verifier" "$program" >"$output_dir/payload-identities.txt"

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_INT128=1 "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-int128"
build_end=$(date +%s%N)

base_options=(
  --specialized-angle-polynomials
  --direct-delta-x4
  --skip-exact-zero-products
  --symmetric-hessian-ops
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
  --prepared-simple-polynomials
  --prepared-coordinate-sqrt-terms
  --precompute-tight-sqrt-certificates
  --count-fixed-quotients
)

lane_options() {
  local lane=$1
  case "$lane" in
    historical-decimal)
      printf '%s\0' --decimal-scale=10000000 \
        --historical-dihedral --historical-block-rounding \
        --historical-center-tangent
      ;;
    direct-decimal)
      printf '%s\0' --decimal-scale=10000000 \
        --historical-dihedral --historical-block-rounding \
        --historical-center-tangent --direct-specialized-function
      ;;
    historical-dyadic)
      printf '%s\0' --binary-scale-bits=23 --dyadic-shift-fixed-quotient \
        --historical-dihedral --historical-block-rounding \
        --historical-center-tangent
      ;;
    direct-dyadic)
      printf '%s\0' --binary-scale-bits=23 --dyadic-shift-fixed-quotient \
        --historical-dihedral --historical-block-rounding \
        --historical-center-tangent --direct-specialized-function
      ;;
    generic-dyadic-deferred)
      printf '%s\0' --binary-scale-bits=23 --dyadic-shift-fixed-quotient \
        --fuse-consecutive-adds --defer-additive-leaf-completion
      ;;
    *)
      printf 'unknown lane: %s\n' "$lane" >&2
      exit 2
      ;;
  esac
}

summaries="$output_dir/summaries.txt"
: >"$summaries"
run_lane() {
  local lane=$1
  local repetition=$2
  local -a options=("${base_options[@]}")
  mapfile -d '' -t lane_specific < <(lane_options "$lane")
  options+=("${lane_specific[@]}")
  "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${options[@]}" \
    | rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ lane=$lane repetition=$repetition/" >>"$summaries"
}

lanes=(
  historical-decimal direct-decimal historical-dyadic direct-dyadic
  generic-dyadic-deferred
)
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
  options=("${base_options[@]}")
  mapfile -d '' -t lane_specific < <(lane_options "$lane")
  options+=("${lane_specific[@]}")
  /usr/bin/time -f '%M' -o "$output_dir/$lane-peak-rss-kb.txt" \
    "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${options[@]}" >"$output_dir/$lane-results.txt"
  rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=4173 .*accepted=4173' \
    "$output_dir/$lane-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
  printf '%s\t%s\n' "$lane" \
    "$(cat "$output_dir/$lane-peak-rss-kb.txt")" \
    >>"$output_dir/peak-rss-kb.tsv"
done

cmp "$output_dir/historical-decimal-bounds.txt" \
  "$output_dir/direct-decimal-bounds.txt"
cmp "$output_dir/historical-dyadic-bounds.txt" \
  "$output_dir/direct-dyadic-bounds.txt"
"$result_analyzer" "$output_dir/direct-decimal-results.txt" \
  "$output_dir/direct-dyadic-results.txt" \
  >"$output_dir/direct-decimal-vs-dyadic.json"
"$result_analyzer" "$output_dir/generic-dyadic-deferred-results.txt" \
  "$output_dir/direct-dyadic-results.txt" \
  >"$output_dir/generic-vs-direct-dyadic.json"

awk -v hardware="$historical_direct_seconds" '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    lane = ""; preparation = 0; evaluation = 0; accepted = 0;
    quotients = 0; completed = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "lane") lane = field[2];
      if (field[1] == "preparation_seconds") preparation = field[2] + 0;
      if (field[1] == "evaluation_seconds") evaluation = field[2] + 0;
      if (field[1] == "evaluation_floor_quotients") quotients += field[2] + 0;
      if (field[1] == "evaluation_ceil_quotients") quotients += field[2] + 0;
      if (field[1] == "completed_results") completed = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
    }
    preparation_sum[lane] += preparation;
    evaluation_sum[lane] += evaluation;
    quotient_sum[lane] += quotients;
    completed_sum[lane] += completed;
    count[lane] += 1;
    if (count[lane] == 1 || accepted < minimum_accepted[lane]) {
      minimum_accepted[lane] = accepted;
    }
  }
  function mean_preparation(lane) { return preparation_sum[lane] / count[lane]; }
  function mean_evaluation(lane) { return evaluation_sum[lane] / count[lane]; }
  function mean_batch(lane) { return mean_preparation(lane) + mean_evaluation(lane); }
  END {
    print "lane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tmean_evaluation_quotients\tmean_completed_results\tminimum_accepted";
    lane_name[1] = "historical-decimal";
    lane_name[2] = "direct-decimal";
    lane_name[3] = "historical-dyadic";
    lane_name[4] = "direct-dyadic";
    lane_name[5] = "generic-dyadic-deferred";
    for (lane_index = 1; lane_index <= 5; ++lane_index) {
      lane = lane_name[lane_index];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%.0f\t%.0f\t%d\n", lane, count[lane], mean_preparation(lane), mean_evaluation(lane), mean_batch(lane), quotient_sum[lane] / count[lane], completed_sum[lane] / count[lane], minimum_accepted[lane];
    }
    printf "direct_decimal_evaluation_speedup\t%d\t0\t%.9f\t0\t0\t0\t%d\n", count["direct-decimal"], mean_evaluation("historical-decimal") / mean_evaluation("direct-decimal"), minimum_accepted["direct-decimal"];
    printf "direct_decimal_batch_speedup\t%d\t0\t0\t%.9f\t0\t0\t%d\n", count["direct-decimal"], mean_batch("historical-decimal") / mean_batch("direct-decimal"), minimum_accepted["direct-decimal"];
    printf "direct_dyadic_evaluation_speedup\t%d\t0\t%.9f\t0\t0\t0\t%d\n", count["direct-dyadic"], mean_evaluation("historical-dyadic") / mean_evaluation("direct-dyadic"), minimum_accepted["direct-dyadic"];
    printf "direct_dyadic_batch_speedup\t%d\t0\t0\t%.9f\t0\t0\t%d\n", count["direct-dyadic"], mean_batch("historical-dyadic") / mean_batch("direct-dyadic"), minimum_accepted["direct-dyadic"];
    printf "direct_arithmetic_evaluation_speedup\t%d\t0\t%.9f\t0\t0\t0\t%d\n", count["direct-dyadic"], mean_evaluation("direct-decimal") / mean_evaluation("direct-dyadic"), minimum_accepted["direct-dyadic"];
    printf "direct_arithmetic_batch_speedup\t%d\t0\t0\t%.9f\t0\t0\t%d\n", count["direct-dyadic"], mean_batch("direct-decimal") / mean_batch("direct-dyadic"), minimum_accepted["direct-dyadic"];
    printf "direct_over_generic_evaluation\t%d\t0\t%.9f\t0\t0\t0\t%d\n", count["direct-dyadic"], mean_evaluation("generic-dyadic-deferred") / mean_evaluation("direct-dyadic"), minimum_accepted["direct-dyadic"];
    printf "direct_over_generic_batch\t%d\t0\t0\t%.9f\t0\t0\t%d\n", count["direct-dyadic"], mean_batch("generic-dyadic-deferred") / mean_batch("direct-dyadic"), minimum_accepted["direct-dyadic"];
    printf "direct_dyadic_over_outward_double\t%d\t0\t%.9f\t0\t0\t0\t%d\n", count["direct-dyadic"], mean_evaluation("direct-dyadic") / hardware, minimum_accepted["direct-dyadic"];
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v build_begin="$build_begin" -v build_end="$build_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build_int128\t%.9f\n", (build_end - build_begin) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$payload_verifier" "$result_analyzer" \
  "$program" "$jobs" "$expected" "$output_dir/payload-identities.txt" \
  "$output_dir/nl-native-int128" "$summaries" \
  "$output_dir"/*-results.txt "$output_dir"/*-bounds.txt \
  "$output_dir/direct-decimal-vs-dyadic.json" \
  "$output_dir/generic-vs-direct-dyadic.json" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  "$output_dir/peak-rss-kb.tsv" >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_DIRECT_SPECIALIZED_FACTORIAL_OK DEVELOPMENT_NON_RELEASE'
