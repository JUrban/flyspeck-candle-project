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
boost_include=${CANDLE_NL_BOOST_INCLUDE:-/project/flyspeck-candle-runs/deps/boost-1.83/usr/include}

[[ "$repetitions" =~ ^[1-9][0-9]*$ ]]
[[ -f "$program" && -f "$jobs" && -f "$expected" && -f "$source_file" ]]
[[ -f "$boost_include/boost/multiprecision/cpp_int.hpp" ]]
[[ $(wc -l <"$jobs") -eq 875 ]]
[[ $(wc -l <"$expected") -eq 875 ]]
[[ ! -e "$output_dir" ]]
mkdir -p "$output_dir"

common_defines=(
  -DCANDLE_NL_CASE_ID=16594
  -DCANDLE_NL_SQRT_SLOTS=10
  -DCANDLE_NL_PROGRAM_INSTRUCTIONS=167
)

build_begin=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$boost_include" \
  -DCANDLE_NL_CHECKED_INT256=1 "${common_defines[@]}" "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-checked256"
build_checked_end=$(date +%s%N)
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -DCANDLE_NL_FIXED_DOUBLE=1 "${common_defines[@]}" "$source_file" \
  -lgmpxx -lgmp -o "$output_dir/nl-native-double"
build_double_end=$(date +%s%N)

lane_binary() {
  local lane=$1
  case "$lane" in
    checked-baseline|checked-prepared)
      printf '%s\n' "$output_dir/nl-native-checked256" ;;
    double-baseline|double-prepared)
      printf '%s\n' "$output_dir/nl-native-double" ;;
    *)
      printf 'unknown lane: %s\n' "$lane" >&2
      exit 2
      ;;
  esac
}

lane_options() {
  local lane=$1
  case "$lane" in
    checked-baseline)
      printf '%s\0' --accept-only --binary-scale-bits=40 \
        --dyadic-shift-fixed-quotient ;;
    checked-prepared)
      printf '%s\0' --accept-only --binary-scale-bits=40 \
        --dyadic-shift-fixed-quotient --prepared-polynomial-pair=34 ;;
    double-baseline)
      printf '%s\0' --accept-only ;;
    double-prepared)
      printf '%s\0' --accept-only --prepared-polynomial-pair=34 ;;
    *)
      printf 'unknown lane: %s\n' "$lane" >&2
      exit 2
      ;;
  esac
}

run_lane() {
  local lane=$1 repetition=$2 destination=$3 binary
  local -a options
  binary=$(lane_binary "$lane")
  mapfile -d '' -t options < <(lane_options "$lane")
  "$binary" "$program" "$jobs" "$expected" "${options[@]}" |
    rg '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY' |
    sed "s/$/ lane=$lane repetition=$repetition/" >>"$destination"
}

summaries="$output_dir/summaries.txt"
: >"$summaries"
lanes=(checked-baseline checked-prepared double-baseline double-prepared)
for lane in "${lanes[@]}"; do run_lane "$lane" warmup /dev/null; done
for ((repetition = 1; repetition <= repetitions; ++repetition)); do
  rotation=$(((repetition - 1) % ${#lanes[@]}))
  for ((offset = 0; offset < ${#lanes[@]}; ++offset)); do
    lane=${lanes[$(((rotation + offset) % ${#lanes[@]}))]}
    run_lane "$lane" "$repetition" "$summaries"
  done
done

for lane in "${lanes[@]}"; do
  binary=$(lane_binary "$lane")
  mapfile -d '' -t options < <(lane_options "$lane")
  "$binary" "$program" "$jobs" "$expected" "${options[@]}" \
    >"$output_dir/$lane-results.txt"
done

rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=checked-int256 .*prepared_polynomial_pair_index=-1 .*case_id=16594 .*accepted=875' \
  "$output_dir/checked-baseline-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=checked-int256 .*prepared_polynomial_pair_index=34 prepared_polynomial_instruction_count=124 .*case_id=16594 .*accepted=875' \
  "$output_dir/checked-prepared-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=double-integer .*prepared_polynomial_pair_index=-1 .*case_id=16594 .*accepted=875' \
  "$output_dir/double-baseline-results.txt"
rg -q '^CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY cells=875 .*backend=double-integer .*prepared_polynomial_pair_index=34 prepared_polynomial_instruction_count=124 .*case_id=16594 .*accepted=875' \
  "$output_dir/double-prepared-results.txt"

for lane in "${lanes[@]}"; do
  rg '^CANDLE_NL_NATIVE_FIXED_SCALE_RESULT' \
    "$output_dir/$lane-results.txt" >"$output_dir/$lane-bounds.txt"
done
cmp "$output_dir/checked-baseline-bounds.txt" \
  "$output_dir/checked-prepared-bounds.txt"
cmp "$output_dir/double-baseline-bounds.txt" \
  "$output_dir/double-prepared-bounds.txt"

for lane in "${lanes[@]}"; do
  binary=$(lane_binary "$lane")
  mapfile -d '' -t options < <(lane_options "$lane")
  "$binary" "$program" "$jobs" "$expected" "${options[@]}" --profile \
    >"$output_dir/$lane-profile.txt"
done

{
  printf 'lane\touter_index\tlabel\tnanoseconds\tinterval_products\n'
  for lane in "${lanes[@]}"; do
    awk -v lane="$lane" '
      /^CANDLE_NL_NATIVE_FIXED_SCALE_PROFILE/ {
        outer = label = ""; nanoseconds = products = 0;
        for (i = 1; i <= NF; ++i) {
          split($i, field, "=");
          if (field[1] == "index") outer = field[2];
          if (field[1] == "label") label = field[2];
          if (field[1] == "nanoseconds") nanoseconds = field[2];
          if (field[1] == "interval_products") products = field[2];
        }
        if (outer == 34 || outer == 35)
          printf "%s\t%s\t%s\t%s\t%s\n", lane, outer, label,
                 nanoseconds, products;
      }
    ' "$output_dir/$lane-profile.txt"
  done
} >"$output_dir/pair-profile.tsv"

for lane in "${lanes[@]}"; do
  binary=$(lane_binary "$lane")
  mapfile -d '' -t options < <(lane_options "$lane")
  /usr/bin/time -f 'wall_seconds=%e maximum_rss_kib=%M' \
    -o "$output_dir/$lane-resource.txt" \
    "$binary" "$program" "$jobs" "$expected" "${options[@]}" >/dev/null
done

awk '
  /CANDLE_NL_NATIVE_FIXED_SCALE_SUMMARY/ {
    lane = ""; preparation = evaluation = accepted = 0;
    for (i = 1; i <= NF; ++i) {
      split($i, field, "=");
      if (field[1] == "lane") lane = field[2];
      if (field[1] == "preparation_seconds") preparation = field[2] + 0;
      if (field[1] == "evaluation_seconds") evaluation = field[2] + 0;
      if (field[1] == "accepted") accepted = field[2] + 0;
    }
    preparation_sum[lane] += preparation;
    evaluation_sum[lane] += evaluation;
    count[lane]++;
    if (count[lane] == 1 || accepted < minimum_accepted[lane])
      minimum_accepted[lane] = accepted;
  }
  function emit(lane) {
    p = preparation_sum[lane] / count[lane];
    e = evaluation_sum[lane] / count[lane];
    printf "%s\t%d\t%.9f\t%.9f\t%.9f\t%d\n", lane, count[lane],
           p, e, p + e, minimum_accepted[lane];
  }
  END {
    print "lane\trepetitions\tmean_preparation_seconds\tmean_evaluation_seconds\tmean_batch_seconds\tminimum_accepted";
    emit("checked-baseline"); emit("checked-prepared");
    emit("double-baseline"); emit("double-prepared");
    cb = evaluation_sum["checked-baseline"] / count["checked-baseline"];
    cp = evaluation_sum["checked-prepared"] / count["checked-prepared"];
    db = evaluation_sum["double-baseline"] / count["double-baseline"];
    dp = evaluation_sum["double-prepared"] / count["double-prepared"];
    printf "checked_prepared_speedup\t%d\t0\t%.9f\t0\t0\n", count["checked-baseline"], cb / cp;
    printf "double_prepared_speedup\t%d\t0\t%.9f\t0\t0\n", count["double-baseline"], db / dp;
  }
' "$summaries" >"$output_dir/phase-times.tsv"

awk -v begin="$build_begin" -v checked="$build_checked_end" \
    -v double="$build_double_end" '
  BEGIN {
    print "metric\tseconds";
    printf "build_checked256\t%.9f\n", (checked - begin) / 1000000000;
    printf "build_double\t%.9f\n", (double - checked) / 1000000000;
  }
' >"$output_dir/one-time-costs.tsv"

sha256sum "$0" "$source_file" "$program" "$jobs" "$expected" \
  "$output_dir/summaries.txt" "$output_dir/phase-times.tsv" \
  "$output_dir/one-time-costs.tsv" "$output_dir/pair-profile.tsv" \
  "$output_dir"/*-bounds.txt "$output_dir"/*-resource.txt \
  >"$output_dir/result-files.sha256"
printf '%s\n' \
  'CANDLE_NL_NATIVE_CASE16594_PREPARED_PAIR_PAIRED_OK DEVELOPMENT_NON_RELEASE'
