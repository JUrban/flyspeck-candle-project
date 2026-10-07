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
historical_specialized_seconds=0.082490265

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$program" && -f "$jobs" && -f "$expected" && -f "$source_file" ]]
[[ -x "$payload_verifier" ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

"$payload_verifier" "$program" >"$output_dir/payload-identities.txt"
[[ $(wc -l <"$jobs") -eq 4173 ]]
[[ $(wc -l <"$expected") -eq 4173 ]]

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_INT128=1 "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-int128"
build_end=$(date +%s%N)

common_options=(
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
    decimal-division)
      printf '%s\0' --decimal-scale=10000000
      ;;
    dyadic-shift)
      printf '%s\0' --binary-scale-bits=23 --dyadic-shift-fixed-quotient
      ;;
    dyadic-shift-fused)
      printf '%s\0' --binary-scale-bits=23 --dyadic-shift-fixed-quotient \
        --fuse-consecutive-adds
      ;;
    *)
      return 2
      ;;
  esac
}

summaries="$output_dir/summaries.txt"
: >"$summaries"
run_lane() {
  local lane=$1
  local repetition=$2
  local -a options=()
  while IFS= read -r -d '' option; do
    options+=("$option")
  done < <(lane_options "$lane")
  "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${common_options[@]}" "${options[@]}" \
    | rg 'CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ lane=$lane repetition=$repetition/" >>"$summaries"
}

for lane in decimal-division dyadic-shift dyadic-shift-fused; do
  run_lane "$lane" warmup
done
: >"$summaries"

lanes=(decimal-division dyadic-shift dyadic-shift-fused)
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  offset=$(((repetition - 1) % 3))
  for step in 0 1 2; do
    run_lane "${lanes[$(((offset + step) % 3))]}" "$repetition"
  done
done

for lane in "${lanes[@]}"; do
  options=()
  while IFS= read -r -d '' option; do
    options+=("$option")
  done < <(lane_options "$lane")
  "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${common_options[@]}" "${options[@]}" \
    >"$output_dir/$lane-results.txt"
  rg -q 'cells=4173 .*accepted=4173' "$output_dir/$lane-results.txt"
  rg 'CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
done
cmp "$output_dir/dyadic-shift-bounds.txt" \
  "$output_dir/dyadic-shift-fused-bounds.txt"

awk -v historical="$historical_specialized_seconds" '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    lane = ""; preparation = 0; evaluation = 0; accepted = 0;
    floor_quotients = 0; ceil_quotients = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "lane") lane = field[2];
      if (field[1] == "preparation_seconds") preparation = field[2] + 0;
      if (field[1] == "evaluation_seconds") evaluation = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
      if (field[1] == "evaluation_floor_quotients") floor_quotients = field[2] + 0;
      if (field[1] == "evaluation_ceil_quotients") ceil_quotients = field[2] + 0;
    }
    preparation_sum[lane] += preparation;
    evaluation_sum[lane] += evaluation;
    quotient_sum[lane] += floor_quotients + ceil_quotients;
    count[lane] += 1;
    if (count[lane] == 1 || accepted < minimum_accepted[lane]) {
      minimum_accepted[lane] = accepted;
    }
  }
  END {
    print "lane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tevaluation_quotients\tminimum_accepted";
    for (lane_index = 1; lane_index <= 3; ++lane_index) {
      lane = lane_index == 1 ? "decimal-division" : lane_index == 2 ? "dyadic-shift" : "dyadic-shift-fused";
      preparation = preparation_sum[lane] / count[lane];
      evaluation = evaluation_sum[lane] / count[lane];
      quotients = quotient_sum[lane] / count[lane];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%.0f\t%d\n", lane, count[lane], preparation, evaluation, preparation + evaluation, quotients, minimum_accepted[lane];
    }
    decimal_evaluation = evaluation_sum["decimal-division"] / count["decimal-division"];
    fused_evaluation = evaluation_sum["dyadic-shift-fused"] / count["dyadic-shift-fused"];
    decimal_batch = (preparation_sum["decimal-division"] + evaluation_sum["decimal-division"]) / count["decimal-division"];
    fused_batch = (preparation_sum["dyadic-shift-fused"] + evaluation_sum["dyadic-shift-fused"]) / count["dyadic-shift-fused"];
    printf "decimal_over_composed_evaluation\t%d\t0\t%.9f\t0\t0\t%d\n", count["dyadic-shift-fused"], decimal_evaluation / fused_evaluation, minimum_accepted["dyadic-shift-fused"];
    printf "decimal_over_composed_batch\t%d\t0\t0\t%.9f\t0\t%d\n", count["dyadic-shift-fused"], decimal_batch / fused_batch, minimum_accepted["dyadic-shift-fused"];
    printf "composed_over_historical_specialized_evaluation\t%d\t0\t%.9f\t0\t0\t%d\n", count["dyadic-shift-fused"], fused_evaluation / historical, minimum_accepted["dyadic-shift-fused"];
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v build_begin="$build_begin" -v build_end="$build_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build\t%.9f\n", (build_end - build_begin) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$source_file" "$payload_verifier" "$program" "$jobs" \
  "$expected" "$output_dir/payload-identities.txt" \
  "$output_dir/nl-native-int128" "$summaries" \
  "$output_dir/decimal-division-results.txt" \
  "$output_dir/dyadic-shift-results.txt" \
  "$output_dir/dyadic-shift-fused-results.txt" \
  "$output_dir/decimal-division-bounds.txt" \
  "$output_dir/dyadic-shift-bounds.txt" \
  "$output_dir/dyadic-shift-fused-bounds.txt" \
  "$output_dir/phase-times.tsv" "$output_dir/one-time-costs.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_ROUNDING_COMPOSED_PAIRED_OK DEVELOPMENT_NON_RELEASE'
