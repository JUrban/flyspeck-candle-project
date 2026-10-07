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
  --count-fixed-quotients
)

lane_options() {
  local lane=$1
  case "$lane" in
    evaluation-conversion) ;;
    reusable-preparation) printf '%s\0' --direct-prepared-inputs ;;
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
  local profile=$4
  local -a options=("${common_options[@]}")
  mapfile -d '' -t lane_specific < <(lane_options "$lane")
  options+=("${lane_specific[@]}")
  if [[ "$profile" == profile ]]; then
    options+=(--direct-stage-profile)
  elif [[ "$profile" != no-profile ]]; then
    printf 'unknown profile mode: %s\n' "$profile" >&2
    exit 2
  fi
  "$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
    "${options[@]}" \
    | rg '^CANDLE_NL_NATIVE_FIXED_SCALE_(SUMMARY|DIRECT_PROFILE)' \
    | sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

lanes=(evaluation-conversion reusable-preparation)
for lane in "${lanes[@]}"; do
  run_lane "$lane" warmup /dev/null no-profile
  run_lane "$lane" profile-warmup /dev/null profile
done

summaries="$output_dir/summaries.txt"
profile_records="$output_dir/profile-records.txt"
: >"$summaries"
: >"$profile_records"
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_lane "$lane" "$repetition" "$summaries" no-profile
  done
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_lane "$lane" "$repetition" "$profile_records" profile
  done
done

awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    lane = ""; preparation = 0; evaluation = 0; accepted = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "lane") lane = field[2];
      if (field[1] == "preparation_seconds") preparation = field[2] + 0;
      if (field[1] == "evaluation_seconds") evaluation = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
    }
    preparation_sum[lane] += preparation;
    evaluation_sum[lane] += evaluation;
    count[lane] += 1;
    if (count[lane] == 1 || accepted < minimum_accepted[lane]) {
      minimum_accepted[lane] = accepted;
    }
  }
  END {
    print "lane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted";
    lanes[1] = "evaluation-conversion";
    lanes[2] = "reusable-preparation";
    for (lane_index = 1; lane_index <= 2; ++lane_index) {
      lane = lanes[lane_index];
      preparation = preparation_sum[lane] / count[lane];
      evaluation = evaluation_sum[lane] / count[lane];
      printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n", lane, count[lane], preparation, evaluation, preparation + evaluation, minimum_accepted[lane];
    }
    control_preparation = preparation_sum["evaluation-conversion"] / count["evaluation-conversion"];
    control_evaluation = evaluation_sum["evaluation-conversion"] / count["evaluation-conversion"];
    prepared_preparation = preparation_sum["reusable-preparation"] / count["reusable-preparation"];
    prepared_evaluation = evaluation_sum["reusable-preparation"] / count["reusable-preparation"];
    printf "prepared_evaluation_speedup\t%d\t0\t%.9f\t0\t%d\n", count["reusable-preparation"], control_evaluation / prepared_evaluation, minimum_accepted["reusable-preparation"];
    printf "prepared_batch_speedup\t%d\t0\t0\t%.9f\t%d\n", count["reusable-preparation"], (control_preparation + control_evaluation) / (prepared_preparation + prepared_evaluation), minimum_accepted["reusable-preparation"];
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_DIRECT_PROFILE/ {
    lane = label = ""; nanoseconds = quotients = products = 0;
    observations = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "lane") lane = field[2];
      if (field[1] == "label") label = field[2];
      if (field[1] == "observations") observations = field[2] + 0;
      if (field[1] == "nanoseconds") nanoseconds = field[2] + 0;
      if (field[1] == "total_quotients") quotients = field[2] + 0;
      if (field[1] == "interval_products") products = field[2] + 0;
    }
    key = lane SUBSEP label;
    nanosecond_sum[key] += nanoseconds;
    quotient_sum[key] += quotients;
    product_sum[key] += products;
    observation_sum[key] += observations;
    record_count[key] += 1;
    lane_nanosecond_sum[lane] += nanoseconds;
  }
  END {
    print "lane\tstage\trepetitions\tmean_seconds\tpercent_profiled_time\tmean_observations\tmean_quotients\tmean_interval_products";
    lanes[1] = "evaluation-conversion";
    lanes[2] = "reusable-preparation";
    stages[1] = "job_setup";
    stages[2] = "coordinate_sqrt_leaves";
    stages[3] = "source_constants";
    stages[4] = "angle_tangent";
    stages[5] = "angle_hessian";
    stages[6] = "angle_scale_and_add";
    stages[7] = "final_completion";
    for (lane_index = 1; lane_index <= 2; ++lane_index) {
      lane = lanes[lane_index];
      for (stage_index = 1; stage_index <= 7; ++stage_index) {
        stage = stages[stage_index];
        key = lane SUBSEP stage;
        printf "%s\t%s\t%d\t%.9f\t%.3f\t%.0f\t%.0f\t%.0f\n", lane, stage, record_count[key], nanosecond_sum[key] / record_count[key] / 1000000000, 100 * nanosecond_sum[key] / lane_nanosecond_sum[lane], observation_sum[key] / record_count[key], quotient_sum[key] / record_count[key], product_sum[key] / record_count[key];
      }
    }
  }
' "$profile_records" >"$output_dir/stage-times.tsv"

rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' "$profile_records" \
  >"$output_dir/profile-summaries.txt"
awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    lane = ""; evaluation = 0;
    for (field_index = 1; field_index <= NF; ++field_index) {
      split($field_index, field, "=");
      if (field[1] == "lane") lane = field[2];
      if (field[1] == "evaluation_seconds") evaluation = field[2] + 0;
    }
    sum[lane] += evaluation; count[lane] += 1;
  }
  END {
    print "lane\trepetitions\tmean_profiled_evaluation_seconds";
    printf "evaluation-conversion\t%d\t%.9f\n", count["evaluation-conversion"], sum["evaluation-conversion"] / count["evaluation-conversion"];
    printf "reusable-preparation\t%d\t%.9f\n", count["reusable-preparation"], sum["reusable-preparation"] / count["reusable-preparation"];
  }
' "$output_dir/profile-summaries.txt" \
  >"$output_dir/profile-evaluation-times.tsv"

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
done
cmp "$output_dir/evaluation-conversion-bounds.txt" \
  "$output_dir/reusable-preparation-bounds.txt"

options=("${common_options[@]}" --direct-stage-profile \
  --direct-prepared-inputs)
"$output_dir/nl-native-int128" "$program" "$jobs" "$expected" \
  "${options[@]}" >"$output_dir/reusable-preparation-profile-results.txt"
rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
  "$output_dir/reusable-preparation-profile-results.txt" \
  >"$output_dir/reusable-preparation-profile-bounds.txt"
cmp "$output_dir/reusable-preparation-bounds.txt" \
  "$output_dir/reusable-preparation-profile-bounds.txt"

awk -v build_begin="$build_begin" -v build_end="$build_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build_int128\t%.9f\n", (build_end - build_begin) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$payload_verifier" \
  "$program" "$jobs" "$expected" "$output_dir/payload-identities.txt" \
  "$output_dir/nl-native-int128" "$summaries" "$profile_records" \
  "$output_dir/profile-summaries.txt" "$output_dir/phase-times.tsv" \
  "$output_dir/stage-times.tsv" "$output_dir/profile-evaluation-times.tsv" \
  "$output_dir"/*-results.txt "$output_dir"/*-bounds.txt \
  "$output_dir/peak-rss-kb.tsv" "$output_dir/one-time-costs.tsv" \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE10173_DIRECT_PREPARATION_PAIRED_OK DEVELOPMENT_NON_RELEASE'
