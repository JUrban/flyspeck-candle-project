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

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$program" && -f "$jobs" && -f "$expected" && -f "$source_file" ]]
[[ -x "$payload_verifier" ]]
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

common_options=(
  --specialized-angle-polynomials
  --direct-delta-x4
  --skip-exact-zero-products
  --symmetric-hessian-ops
  --binary-scale-bits=23
  --dyadic-shift-fixed-quotient
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
  --count-fixed-quotients
)

lane_options() {
  local lane=$1
  case "$lane" in
    four-endpoint) ;;
    sign-specialized) printf '%s\0' --sign-specialized-interval-products ;;
    *)
      printf 'unknown lane: %s\n' "$lane" >&2
      exit 2
      ;;
  esac
}

run_lane() {
  local lane=$1
  local repetition=$2
  local destination=$3
  local -a options=("${common_options[@]}")
  mapfile -d '' -t lane_specific < <(lane_options "$lane")
  options+=("${lane_specific[@]}")
  "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${options[@]}" \
    | rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' \
    | sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

lanes=(four-endpoint sign-specialized)
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

awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    lane = ""; preparation = evaluation = endpoints = accepted = 0;
    products = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "lane") lane = field[2];
      if (field[1] == "preparation_seconds") preparation = field[2] + 0;
      if (field[1] == "evaluation_seconds") evaluation = field[2] + 0;
      if (field[1] == "interval_products") products = field[2] + 0;
      if (field[1] == "interval_endpoint_products") endpoints = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
    }
    preparation_sum[lane] += preparation;
    evaluation_sum[lane] += evaluation;
    product_sum[lane] += products;
    endpoint_sum[lane] += endpoints;
    count[lane] += 1;
    if (count[lane] == 1 || accepted < minimum_accepted[lane]) {
      minimum_accepted[lane] = accepted;
    }
  }
  END {
    print "lane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tmean_interval_products\tmean_endpoint_products\tminimum_accepted";
    lanes[1] = "four-endpoint";
    lanes[2] = "sign-specialized";
    for (lane_index = 1; lane_index <= 2; ++lane_index) {
      lane = lanes[lane_index];
      preparation = preparation_sum[lane] / count[lane];
      evaluation = evaluation_sum[lane] / count[lane];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%.0f\t%.0f\t%d\n", lane, count[lane], preparation, evaluation, preparation + evaluation, product_sum[lane] / count[lane], endpoint_sum[lane] / count[lane], minimum_accepted[lane];
    }
    control_preparation = preparation_sum["four-endpoint"] / count["four-endpoint"];
    control_evaluation = evaluation_sum["four-endpoint"] / count["four-endpoint"];
    candidate_preparation = preparation_sum["sign-specialized"] / count["sign-specialized"];
    candidate_evaluation = evaluation_sum["sign-specialized"] / count["sign-specialized"];
    printf "sign_evaluation_speedup\t%d\t0\t%.9f\t0\t0\t0\t%d\n", count["sign-specialized"], control_evaluation / candidate_evaluation, minimum_accepted["sign-specialized"];
    printf "sign_batch_speedup\t%d\t0\t0\t%.9f\t0\t0\t%d\n", count["sign-specialized"], (control_preparation + control_evaluation) / (candidate_preparation + candidate_evaluation), minimum_accepted["sign-specialized"];
  }
' "$summaries" >"$output_dir/phase-times.tsv"

printf 'lane\tpeak_rss_kb\n' >"$output_dir/peak-rss-kb.tsv"
for lane in "${lanes[@]}"; do
  options=("${common_options[@]}")
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

  profile_options=("${options[@]}" --direct-stage-profile)
  "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${profile_options[@]}" >"$output_dir/$lane-profile-results.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_DIRECT_PROFILE' \
    "$output_dir/$lane-profile-results.txt" \
    >"$output_dir/$lane-stage-profile.txt"
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-profile-results.txt" \
    >"$output_dir/$lane-profile-bounds.txt"
  cmp "$output_dir/$lane-bounds.txt" "$output_dir/$lane-profile-bounds.txt"
done
cmp "$output_dir/four-endpoint-bounds.txt" \
  "$output_dir/sign-specialized-bounds.txt"

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
  FNR == NR { read_record("four-endpoint"); next }
  { read_record("sign-specialized") }
  END {
    print "stage\tfour_endpoint_seconds\tsign_specialized_seconds\tspeedup\tsemantic_products\tfour_endpoint_products\tsign_endpoint_products\tquotients";
    stages[1] = "job_setup";
    stages[2] = "coordinate_sqrt_leaves";
    stages[3] = "source_constants";
    stages[4] = "angle_tangent";
    stages[5] = "angle_hessian";
    stages[6] = "angle_scale_and_add";
    stages[7] = "final_completion";
    for (stage_index = 1; stage_index <= 7; ++stage_index) {
      stage = stages[stage_index];
      candidate = time["sign-specialized", stage];
      speedup = candidate == 0 ? 0 : time["four-endpoint", stage] / candidate;
      printf "%s\t%.9f\t%.9f\t%.9f\t%.0f\t%.0f\t%.0f\t%.0f\n", stage, time["four-endpoint", stage], candidate, speedup, product["four-endpoint", stage], endpoint["four-endpoint", stage], endpoint["sign-specialized", stage], quotient["sign-specialized", stage];
    }
  }
' "$output_dir/four-endpoint-stage-profile.txt" \
  "$output_dir/sign-specialized-stage-profile.txt" \
  >"$output_dir/stage-comparison.tsv"

awk -v build_begin="$build_begin" -v build_end="$build_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build_int128\t%.9f\n", (build_end - build_begin) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$payload_verifier" \
  "$program" "$jobs" "$expected" "$output_dir/payload-identities.txt" \
  "$output_dir/nl-native-int128" "$summaries" \
  "$output_dir/phase-times.tsv" "$output_dir/stage-comparison.tsv" \
  "$output_dir"/*-results.txt "$output_dir"/*-bounds.txt \
  "$output_dir"/*-stage-profile.txt "$output_dir/peak-rss-kb.tsv" \
  "$output_dir/one-time-costs.tsv" >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_SIGN_PRODUCTS_PAIRED_OK DEVELOPMENT_NON_RELEASE'
