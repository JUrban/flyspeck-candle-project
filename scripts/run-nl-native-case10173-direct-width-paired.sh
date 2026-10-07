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

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$program" && -f "$jobs" && -f "$expected" && -f "$source_file" ]]
[[ -x "$payload_verifier" && -x "$bound_analyzer" ]]
[[ $(wc -l <"$jobs") -eq 4173 ]]
[[ $(wc -l <"$expected") -eq 4173 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

"$payload_verifier" "$program" >"$output_dir/payload-identities.txt"

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_INT128=1 "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-int128"
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_DOUBLE=1 "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-double"
build_end=$(date +%s%N)

common_options=(
  --specialized-angle-polynomials
  --direct-delta-x4
  --skip-exact-zero-products
  --symmetric-hessian-ops
  --binary-scale-bits=23
  --fixed-sqrt-inverse-kernels
  --fixed-atan-kernel
  --prepared-simple-polynomials
  --prepared-coordinate-sqrt-terms
  --precompute-tight-sqrt-certificates
  --historical-dihedral
  --historical-block-rounding
  --historical-center-tangent
  --direct-specialized-function
  --direct-prepared-inputs
  --sign-specialized-interval-products
  --count-fixed-quotients
)

lane_backend() {
  case "$1" in
    exact-int128) printf '%s\n' int128 ;;
    padded-double) printf '%s\n' double ;;
    *) return 2 ;;
  esac
}

run_lane() {
  local lane=$1
  local repetition=$2
  local destination=$3
  local backend
  local -a options=("${common_options[@]}")
  backend=$(lane_backend "$lane")
  if [[ "$lane" == exact-int128 ]]; then
    options+=(--dyadic-shift-fixed-quotient)
  fi
  "$output_dir/nl-native-$backend" "$program" "$jobs" "$expected" \
    "${options[@]}" \
    | rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

lanes=(exact-int128 padded-double)
for lane in "${lanes[@]}"; do
  run_lane "$lane" warmup /dev/null
done

summaries="$output_dir/summaries.txt"
: >"$summaries"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_lane "$lane" "$repetition" "$summaries"
  done
done

printf 'lane\tpeak_rss_kb\n' >"$output_dir/peak-rss-kb.tsv"
for lane in "${lanes[@]}"; do
  backend=$(lane_backend "$lane")
  options=("${common_options[@]}")
  if [[ "$lane" == exact-int128 ]]; then
    options+=(--dyadic-shift-fixed-quotient)
  fi
  /usr/bin/time -f '%M' -o "$output_dir/$lane-peak-rss-kb.txt" \
    "$output_dir/nl-native-$backend" "$program" "$jobs" "$expected" \
    "${options[@]}" >"$output_dir/$lane-results.txt"
  rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=4173 .*accepted=4173' \
    "$output_dir/$lane-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
  printf '%s\t%s\n' "$lane" \
    "$(cat "$output_dir/$lane-peak-rss-kb.txt")" \
    >>"$output_dir/peak-rss-kb.tsv"

  profile_options=("${options[@]}" --direct-stage-profile)
  "$output_dir/nl-native-$backend" "$program" "$jobs" "$expected" \
    "${profile_options[@]}" >"$output_dir/$lane-profile-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_DIRECT_PROFILE' \
    "$output_dir/$lane-profile-results.txt" \
    >"$output_dir/$lane-stage-profile.txt"
done

"$bound_analyzer" "$output_dir/exact-int128-results.txt" \
  "$output_dir/padded-double-results.txt" \
  >"$output_dir/padded-double-vs-exact-bounds.json"

awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    lane = ""; preparation = evaluation = accepted = 0;
    products = endpoints = quotients = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "lane") lane = field[2];
      if (field[1] == "preparation_seconds") preparation = field[2] + 0;
      if (field[1] == "evaluation_seconds") evaluation = field[2] + 0;
      if (field[1] == "interval_products") products = field[2] + 0;
      if (field[1] == "interval_endpoint_products") endpoints = field[2] + 0;
      if (field[1] == "evaluation_floor_quotients" ||
          field[1] == "evaluation_ceil_quotients") quotients += field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
    }
    preparation_sum[lane] += preparation;
    evaluation_sum[lane] += evaluation;
    product_sum[lane] += products;
    endpoint_sum[lane] += endpoints;
    quotient_sum[lane] += quotients;
    count[lane] += 1;
    if (count[lane] == 1 || accepted < minimum_accepted[lane]) {
      minimum_accepted[lane] = accepted;
    }
  }
  END {
    print "lane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tmean_interval_products\tmean_endpoint_products\tmean_quotients\tminimum_accepted";
    lanes[1] = "exact-int128";
    lanes[2] = "padded-double";
    for (lane_index = 1; lane_index <= 2; ++lane_index) {
      lane = lanes[lane_index];
      preparation = preparation_sum[lane] / count[lane];
      evaluation = evaluation_sum[lane] / count[lane];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%.0f\t%.0f\t%.0f\t%d\n", lane, count[lane], preparation, evaluation, preparation + evaluation, product_sum[lane] / count[lane], endpoint_sum[lane] / count[lane], quotient_sum[lane] / count[lane], minimum_accepted[lane];
    }
    exact_preparation = preparation_sum["exact-int128"] / count["exact-int128"];
    exact_evaluation = evaluation_sum["exact-int128"] / count["exact-int128"];
    double_preparation = preparation_sum["padded-double"] / count["padded-double"];
    double_evaluation = evaluation_sum["padded-double"] / count["padded-double"];
    printf "double_evaluation_speedup\t%d\t0\t%.9f\t0\t0\t0\t0\t%d\n", count["padded-double"], exact_evaluation / double_evaluation, minimum_accepted["padded-double"];
    printf "double_batch_speedup\t%d\t0\t0\t%.9f\t0\t0\t0\t%d\n", count["padded-double"], (exact_preparation + exact_evaluation) / (double_preparation + double_evaluation), minimum_accepted["padded-double"];
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk '
  function read_record(lane) {
    label = ""; nanoseconds = products = endpoints = quotients = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "label") label = field[2];
      if (field[1] == "nanoseconds") nanoseconds = field[2] + 0;
      if (field[1] == "total_quotients") quotients = field[2] + 0;
      if (field[1] == "interval_products") products = field[2] + 0;
      if (field[1] == "interval_endpoint_products") endpoints = field[2] + 0;
    }
    time[lane, label] = nanoseconds / 1000000000;
    quotient[lane, label] = quotients;
    product[lane, label] = products;
    endpoint[lane, label] = endpoints;
  }
  FNR == NR { read_record("exact-int128"); next }
  { read_record("padded-double") }
  END {
    print "stage\texact_int128_seconds\tpadded_double_seconds\tspeedup\tsemantic_products\tendpoint_products\tquotients";
    stages[1] = "job_setup";
    stages[2] = "coordinate_sqrt_leaves";
    stages[3] = "source_constants";
    stages[4] = "angle_tangent";
    stages[5] = "angle_hessian";
    stages[6] = "angle_scale_and_add";
    stages[7] = "final_completion";
    for (stage_index = 1; stage_index <= 7; ++stage_index) {
      stage = stages[stage_index];
      candidate = time["padded-double", stage];
      speedup = candidate == 0 ? 0 : time["exact-int128", stage] / candidate;
      printf "%s\t%.9f\t%.9f\t%.9f\t%.0f\t%.0f\t%.0f\n", stage, time["exact-int128", stage], candidate, speedup, product["exact-int128", stage], endpoint["exact-int128", stage], quotient["exact-int128", stage];
    }
  }
' "$output_dir/exact-int128-stage-profile.txt" \
  "$output_dir/padded-double-stage-profile.txt" \
  >"$output_dir/stage-comparison.tsv"

awk -v build_begin="$build_begin" -v build_end="$build_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build_two_backends\t%.9f\n", (build_end - build_begin) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$payload_verifier" "$bound_analyzer" \
  "$program" "$jobs" "$expected" "$output_dir/payload-identities.txt" \
  "$output_dir/nl-native-int128" "$output_dir/nl-native-double" \
  "$summaries" "$output_dir/phase-times.tsv" \
  "$output_dir/stage-comparison.tsv" \
  "$output_dir/padded-double-vs-exact-bounds.json" \
  "$output_dir"/*-results.txt "$output_dir"/*-bounds.txt \
  "$output_dir"/*-stage-profile.txt "$output_dir/peak-rss-kb.tsv" \
  "$output_dir/one-time-costs.tsv" >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_DIRECT_WIDTH_PAIRED_OK DEVELOPMENT_NON_RELEASE'
